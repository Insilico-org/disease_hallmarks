from typing import List, Dict, Tuple, Any
import time
import math
import requests
import random
import numpy as np
import pandas as pd
import statistics
from scipy import stats
from statsmodels.stats.multitest import fdrcorrection

from disease_hallmarks.analysis import DiseaseAnalyzer
from disease_hallmarks.api_callers import OpenTargetsAPI
from disease_hallmarks.models import DiseaseAnnotation

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def get_disease_targets_with_scores(ot_api: OpenTargetsAPI, efo_id: str) -> List[Dict[str, Any]]:
    """
    Get all target genes for a disease from OpenTargets with their association scores.
    Handles pagination to retrieve all targets.
    """
    cache_key = f"ot_all_disease_targets_with_scores_{efo_id}"
    if ot_api.cache:
        cached_result = ot_api.cache.get(cache_key)
        if cached_result:
            print(f"Loaded {len(cached_result)} targets from cache for EFO ID {efo_id}")
            return cached_result

    all_targets = []
    page_size = 1000  # Max page size for OpenTargets GraphQL API
    current_page = 0
    total_count = -1

    while True:
        query = """
        query diseaseAssociations($efoId: String!, $index: Int!, $size: Int!) {
          disease(efoId: $efoId) {
            associatedTargets(page: { index: $index, size: $size }) {
              count
              rows {
                target {
                  approvedSymbol
                }
                score
              }
            }
          }
        }
        """
        variables = {"efoId": efo_id, "index": current_page, "size": page_size}
        
        for _ in range(ot_api.max_retries):
            try:
                response = requests.post(f"{ot_api.BASE_URL}/graphql", json={"query": query, "variables": variables})
                if response.ok:
                    data = response.json()
                    rows = data.get("data", {}).get("disease", {}).get("associatedTargets", {}).get("rows", [])
                    
                    if total_count == -1:
                        total_count = data.get("data", {}).get("disease", {}).get("associatedTargets", {}).get("count", 0)
                        print(f"Found {total_count} total targets for disease {efo_id}.")

                    for row in rows:
                        all_targets.append({"gene": row["target"]["approvedSymbol"], "score": row["score"]})
                    
                    if not rows or len(all_targets) >= total_count:
                        break  # Exit retry loop and outer while loop
                    
                    current_page += 1
                    break # Exit retry loop to fetch next page
                
                elif response.status_code == 503: # Retry on 503
                    time.sleep(ot_api.retry_delay)
                else: # Don't retry on other errors
                    break
            except requests.RequestException:
                time.sleep(ot_api.retry_delay)
        else:
            # All retries failed for a page
            print(f"Warning: Failed to fetch all targets for {efo_id} after multiple retries.")
            break
        
        if total_count != -1 and len(all_targets) >= total_count:
            break

    if ot_api.cache:
        ot_api.cache.set(cache_key, all_targets)
    
    print(f"Retrieved {len(all_targets)} targets for EFO ID {efo_id}")
    return all_targets


def analyze_with_resampling(
    analyzer: DiseaseAnalyzer,
    disease_name: str,
    n_iterations: int = 1000,
    verbose: bool = False,
    sampling_pool_multiplier: float = None,
    seed: int = 28
) -> Tuple[DiseaseAnnotation, Dict[str, List[float]]]:
    """
    Perform resampling analysis of a disease.
    Now tracks individual hallmark scores in addition to total scores.
    """
    print(f"Analyzing {disease_name}...")
    random.seed(seed)
    np.random.seed(seed)
    
    original_annotation = analyzer.analyze_disease(disease_name, verbose=verbose)
    if original_annotation is None:
        raise ValueError(f"Disease '{disease_name}' not found")

    original_genes = original_annotation.target_genes
    sample_size = len(original_genes)
    print(f"Found {sample_size} genes for {disease_name} with default threshold.")

    print("Fetching all disease-associated genes from OpenTargets...")
    if not hasattr(analyzer, 'ot_api'):
        analyzer.ot_api = OpenTargetsAPI(cache=analyzer.cache)
    
    all_disease_targets = get_disease_targets_with_scores(analyzer.ot_api, original_annotation.efo_id)
    
    # Filter all_disease_targets to ensure valid genes (non-empty strings) and scores (numbers)
    valid_targets_for_processing = []
    for item in all_disease_targets:
        gene_name = item.get('gene')
        assoc_score = item.get('score')
        if isinstance(gene_name, str) and gene_name.strip() and isinstance(assoc_score, (int, float)):
            valid_targets_for_processing.append({'gene': gene_name, 'score': float(assoc_score)})
        else:
            if verbose:
                print(f"Info: Skipping invalid target from OpenTargets: gene='{gene_name}', score='{assoc_score}'")

    if not valid_targets_for_processing:
        raise ValueError("No valid gene-score pairs found in OpenTargets results after filtering. Cannot proceed with resampling.")

    # If a multiplier is provided, restrict the sampling pool to the top N genes
    if sampling_pool_multiplier is not None and sampling_pool_multiplier > 0:
        print(f"Restricting sampling pool based on multiplier: {sampling_pool_multiplier}")
        valid_targets_for_processing.sort(key=lambda x: x.get('score', 0), reverse=True)
        pool_size = int(sample_size * sampling_pool_multiplier)
        valid_targets_for_processing = valid_targets_for_processing[:pool_size]
        print(f"New sampling pool size: {len(valid_targets_for_processing)} genes (top {pool_size} from OpenTargets)")

    genes = [item['gene'] for item in valid_targets_for_processing]
    weights = [item['score'] for item in valid_targets_for_processing]
    
    genes_array = np.array(genes, dtype=str) 
    weights_array = np.array(weights, dtype=float)

    num_available_genes = genes_array.size
    actual_sample_size = min(sample_size, num_available_genes)

    if actual_sample_size > 0 and num_available_genes == 0:
         raise ValueError(f"Cannot sample {actual_sample_size} genes, no genes available.")

    # Initialize resampling results with total_scores AND individual hallmark scores
    resampling_results = {"total_scores": []}
    
    # Get hallmark names from original annotation to initialize storage
    original_hallmark_names = list(original_annotation.hallmark_scores.keys())
    for hallmark_name in original_hallmark_names:
        resampling_results[f"hallmark_{hallmark_name}"] = []

    print(f"Performing {n_iterations} resampling iterations (sampling {actual_sample_size} unique genes each time)...")
    start_time = time.time()
    for i in range(n_iterations):
        if verbose and (i + 1) % 100 == 0:
            print(f"Resampling iteration {i+1}/{n_iterations}")

        if actual_sample_size == 0:
            resampled_genes = []
        elif num_available_genes == 0:
             resampled_genes = []
        elif np.sum(weights_array) <= 1e-9:
            if i == 0:
                print("Warning: Sum of weights is effectively zero. Falling back to uniform sampling for all iterations.")
            resampled_genes_np = np.random.choice(genes_array, size=actual_sample_size, replace=False)
            resampled_genes = list(resampled_genes_np)
        else:
            probabilities = weights_array / np.sum(weights_array)
            resampled_genes_np = np.random.choice(genes_array, size=actual_sample_size, replace=False, p=probabilities)
            resampled_genes = list(resampled_genes_np)

        enriched_pathways = analyzer._analyze_pathways(resampled_genes)
        hallmark_scores = analyzer._calculate_hallmark_scores(resampled_genes, enriched_pathways, verbose=False)
        
        # Store total score
        total_score = sum(score.total_score for score in hallmark_scores.values())
        resampling_results["total_scores"].append(total_score)
        
        # Store individual hallmark scores
        for hallmark_name in original_hallmark_names:
            if hallmark_name in hallmark_scores:
                hallmark_score = hallmark_scores[hallmark_name].total_score
            else:
                hallmark_score = 0.0  # If hallmark not found in this iteration
            resampling_results[f"hallmark_{hallmark_name}"].append(hallmark_score)

    duration = time.time() - start_time
    print(f"Resampling finished in {duration:.2f} seconds.")
    
    return original_annotation, resampling_results


def calculate_resampling_statistics(resampling_results: Dict[str, List[float]]) -> Dict[str, Any]:
    """
    Calculate statistics for resampling results.
    """
    stats = {}
    total_scores = resampling_results["total_scores"]
    
    stats['mean'] = statistics.mean(total_scores)
    stats['std_dev'] = statistics.stdev(total_scores)
    stats['median'] = statistics.median(total_scores)
    
    # 95% confidence interval
    total_scores_sorted = sorted(total_scores)
    lower_bound = np.percentile(total_scores_sorted, 2.5)
    upper_bound = np.percentile(total_scores_sorted, 97.5)
    stats['95ci_lower'] = lower_bound
    stats['95ci_upper'] = upper_bound
    
    return stats


def calculate_hallmark_statistics(resampling_results: Dict[str, List[float]]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate statistics for each individual hallmark from resampling results.
    """
    hallmark_stats = {}
    
    for key, scores in resampling_results.items():
        if key.startswith("hallmark_"):
            hallmark_name = key.replace("hallmark_", "")
            
            if scores:  # Check if we have data
                hallmark_stats[hallmark_name] = {
                    'mean': statistics.mean(scores),
                    'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0.0,
                    'median': statistics.median(scores),
                    '95ci_lower': np.percentile(scores, 2.5),
                    '95ci_upper': np.percentile(scores, 97.5),
                    'scores': scores  # Keep raw scores for plotting
                }
            else:
                hallmark_stats[hallmark_name] = {
                    'mean': 0.0, 'std_dev': 0.0, 'median': 0.0,
                    '95ci_lower': 0.0, '95ci_upper': 0.0, 'scores': []
                }
    
    return hallmark_stats


def plot_resampling_results(
    disease_name: str,
    resampling_results: Dict[str, List[float]],
    stats: Dict[str, Any],
    save_path: str = None
):
    """
    Create a histogram of resampling results.
    """
    fig = go.Figure()

    # Histogram of resampled total scores
    fig.add_trace(go.Histogram(
        x=resampling_results['total_scores'],
        name='Resampled Scores',
        marker_color='#330C73',
        opacity=0.75
    ))

    # Line for mean resampled score (not original score)
    fig.add_vline(
        x=stats['mean'],
        line_width=3,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Mean Resampled: {stats['mean']:.2f}",
        annotation_position="top right"
    )

    # Lines for 95% CI
    fig.add_vline(x=stats['95ci_lower'], line_width=2, line_dash="dot", line_color="grey")
    fig.add_vline(x=stats['95ci_upper'], line_width=2, line_dash="dot", line_color="grey")

    fig.update_layout(
        title_text=f'Resampling Analysis for {disease_name.title()}',
        xaxis_title_text='Total Hallmark Score',
        yaxis_title_text='Frequency',
        annotations=[
            dict(
                x=0.95, y=0.95, xref='paper', yref='paper',
                text=f"95% CI: [{stats['95ci_lower']:.2f}, {stats['95ci_upper']:.2f}]",
                showarrow=False
            )
        ]
    )
    
    if save_path:
        fig.write_image(save_path, width=800, height=600, scale=2)
        print(f"Saved plot: {save_path}")
    
    return fig


def plot_hallmark_distributions(
    disease_name: str,
    resampling_results: Dict[str, List[float]],
    hallmark_stats: Dict[str, Dict[str, Any]],
    save_path: str = None
):
    """
    Create a subplot showing distribution of each hallmark score across bootstrap iterations.
    """
    # Get hallmark names and sort them for consistent plotting
    hallmark_names = sorted([name for name in hallmark_stats.keys()])
    
    if not hallmark_names:
        print(f"No hallmarks found for {disease_name}")
        return None
    
    # Calculate subplot layout
    n_hallmarks = len(hallmark_names)
    n_cols = 3  # 3 columns
    n_rows = math.ceil(n_hallmarks / n_cols)
    
    # Create subplots
    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=hallmark_names,
        vertical_spacing=0.08,
        horizontal_spacing=0.05
    )
    
    for i, hallmark_name in enumerate(hallmark_names):
        row = (i // n_cols) + 1
        col = (i % n_cols) + 1
        
        # Get resampled scores for this hallmark
        resampled_scores = hallmark_stats[hallmark_name]['scores']
        
        # Get mean resampled score for this hallmark (not original score)
        mean_resampled_score = hallmark_stats[hallmark_name]['mean']
        
        # Add histogram
        fig.add_trace(
            go.Histogram(
                x=resampled_scores,
                name=f'{hallmark_name} Resampled',
                marker_color='lightblue',
                opacity=0.7,
                showlegend=False
            ),
            row=row, col=col
        )
        
        # Add vertical line for mean resampled score
        if resampled_scores:  # Only if we have data
            y_max = max(25, len(resampled_scores) // 10)  # Rough estimate for y-axis height
            fig.add_shape(
                type="line",
                x0=mean_resampled_score, y0=0,
                x1=mean_resampled_score, y1=y_max,
                line=dict(color="red", width=2, dash="dash"),
                row=row, col=col
            )
    
    fig.update_layout(
        title_text=f'Hallmark Score Distributions for {disease_name.title()}',
        height=300 * n_rows,  # Adjust height based on number of rows
        showlegend=False
    )
    
    if save_path:
        fig.write_image(save_path, width=1200, height=300 * n_rows, scale=2)
        print(f"Saved hallmark plot: {save_path}")
    
    return fig


def create_summary_barplot(result_dict: Dict[str, Any], save_path: str = None):
    """
    Create the summary bar plot with error bars (descending order).
    """
    # Extract data for plotting
    keys = list(result_dict.keys())
    means = []
    errors = []

    for key in keys:
        scores = result_dict[key]['resampling']['total_scores']
        means.append(np.mean(scores))
        errors.append(np.std(scores))  # or np.std(scores)/np.sqrt(len(scores)) for standard error

    # Sort by descending mean values
    sorted_data = sorted(zip(keys, means, errors), key=lambda x: x[1], reverse=True)
    sorted_keys, sorted_means, sorted_errors = zip(*sorted_data)

    # Create bar plot with error bars
    fig = go.Figure(data=go.Bar(
        x=sorted_keys,
        y=sorted_means,
        error_y=dict(type='data', array=sorted_errors, visible=True),
        marker_color='steelblue'
    ))

    fig.update_layout(
        title='Results with Error Bars (Descending Order)',
        xaxis_title='',
        yaxis_title='Total Scores',
        showlegend=False,
        xaxis_tickangle=-45,
        height=600,
        margin=dict(b=150)  # More bottom margin for rotated labels
    )

    if save_path:
        fig.write_image(save_path, width=1200, height=600, scale=2)
        print(f"Saved summary plot: {save_path}")

    return fig


# ===== HEATMAP VISUALIZATION FUNCTIONS =====

def calculate_pvalue_for_heatmap(scores, test_value=0):
    """
    One-sided non-parametric test (Wilcoxon signed-rank) 
    Tests if hallmark scores are significantly greater than test_value
    """
    try:
        if len(np.unique(scores)) == 1:
            if scores[0] > test_value:
                return 1e-10
            else:
                return 1.01
        
        if len(scores) < 3:
            return 1.02
        
        differences = scores - test_value
        differences = differences[differences != 0]
        
        if len(differences) == 0:
            return 1.03
        
        statistic, p_val_two_sided = stats.wilcoxon(differences, alternative='two-sided')
        
        if np.median(differences) > 0:
            p_val = p_val_two_sided / 2
        else:
            p_val = 1.0 - (p_val_two_sided / 2)
        
        if np.isnan(p_val):
            return 1.04
            
        return max(p_val, 1e-300)
        
    except Exception as e:
        print(e)
        return 1.05


def create_heatmap_data(results, significance_threshold=0.001):
    """Create data for heatmap visualization"""
    
    # Extract all hallmarks from first disease resampling data
    first_disease = list(results.keys())[0]
    resampling_data = results[first_disease]['resampling']
    
    # Get hallmark names
    hallmark_keys = [key for key in resampling_data.keys() if key.startswith('hallmark_')]
    hallmarks = [key.replace('hallmark_', '') for key in hallmark_keys]
    
    print(f"Processing {len(hallmarks)} hallmarks across {len(results)} diseases for heatmap...")
    
    # Prepare data
    data = []
    disease_total_scores = {}
    
    for disease, disease_data in results.items():
        resampling_data = disease_data['resampling']
        disease_scores = []
        
        for hallmark in hallmarks:
            hallmark_key = f'hallmark_{hallmark}'
            
            if hallmark_key in resampling_data:
                scores = np.array(resampling_data[hallmark_key])
                mean_score = np.mean(scores)
                std_score = np.std(scores, ddof=1)
                
                # Calculate p-value
                p_val = calculate_pvalue_for_heatmap(scores, test_value=0)
                
                data.append({
                    'disease': disease,
                    'hallmark': hallmark,
                    'mean_score': mean_score,
                    'std_score': std_score,
                    'p_value': p_val,
                    'scores': scores
                })
                
                disease_scores.append(mean_score)
        
        disease_total_scores[disease] = np.mean(disease_scores) if disease_scores else 0
    
    df = pd.DataFrame(data)
    
    # Calculate total scores for sorting
    disease_total_scores = {}
    hallmark_total_scores = {}
    
    # Disease totals (mean across all hallmarks)
    for disease in df['disease'].unique():
        disease_scores = df[df['disease'] == disease]['mean_score'].values
        disease_total_scores[disease] = np.mean(disease_scores) if len(disease_scores) > 0 else 0
    
    # Hallmark totals (sum across all diseases)
    for hallmark in df['hallmark'].unique():
        hallmark_scores = df[df['hallmark'] == hallmark]['mean_score'].values
        hallmark_total_scores[hallmark] = np.sum(hallmark_scores) if len(hallmark_scores) > 0 else 0
    
    # Sort diseases by total score (descending)
    sorted_diseases = sorted(disease_total_scores.keys(), 
                           key=lambda x: disease_total_scores[x], 
                           reverse=True)
    
    # Sort hallmarks by total score (descending - highest at top)
    sorted_hallmarks = sorted(hallmark_total_scores.keys(),
                            key=lambda x: hallmark_total_scores[x],
                            reverse=True)
    
    # Handle any remaining NaN p-values
    df['p_value'] = df['p_value'].fillna(1.0)
    
    # FDR correction across all tests
    reject, fdr_corrected = fdrcorrection(df['p_value'], alpha=0.05)
    df['fdr_p_value'] = fdr_corrected
    df['fdr_reject'] = reject
    
    # Determine significance based on FDR
    df['is_significant'] = df['fdr_p_value'] < significance_threshold
    
    print(f"Significant results (FDR < {significance_threshold}): {df['is_significant'].sum()}/{len(df)}")
    
    return df, sorted_diseases, sorted_hallmarks


def create_heatmap_matrix(df, sorted_diseases, sorted_hallmarks):
    """Create matrices for heatmap visualization"""
    
    # Create pivot tables
    score_matrix = df.pivot(index='hallmark', columns='disease', values='mean_score')
    pval_matrix = df.pivot(index='hallmark', columns='disease', values='fdr_p_value')
    sig_matrix = df.pivot(index='hallmark', columns='disease', values='is_significant')
    
    # Reorder according to sorted diseases and hallmarks
    # Reverse hallmarks for display so highest scores appear at top
    score_matrix = score_matrix.reindex(index=sorted_hallmarks[::-1], columns=sorted_diseases)
    pval_matrix = pval_matrix.reindex(index=sorted_hallmarks[::-1], columns=sorted_diseases)
    sig_matrix = sig_matrix.reindex(index=sorted_hallmarks[::-1], columns=sorted_diseases)
    
    # Fill any missing values
    score_matrix = score_matrix.fillna(0)
    pval_matrix = pval_matrix.fillna(1.0)
    sig_matrix = sig_matrix.fillna(False)
    
    return score_matrix, pval_matrix, sig_matrix


def create_heatmap_annotations(score_matrix, sig_matrix, show_values=True):
    """Create text annotations for the heatmap"""
    
    annotations = []
    
    for i, hallmark in enumerate(score_matrix.index):
        for j, disease in enumerate(score_matrix.columns):
            score = score_matrix.iloc[i, j]
            is_sig = sig_matrix.iloc[i, j]
            
            if is_sig:
                if show_values:
                    text = f"{score:.1f}"
                    color = "white" if score > 10 else "black"
                else:
                    text = ""
                    color = "black"
            else:
                text = "NS"
                color = "darkgray"
            
            annotations.append(
                dict(
                    x=j, y=i,
                    text=text,
                    showarrow=False,
                    font=dict(
                        color=color,
                        size=10,
                        family="Arial"
                    )
                )
            )
    
    return annotations


def create_aging_heatmap(df, sorted_diseases, sorted_hallmarks, 
                        title="Aging Hallmarks Enrichment Across Diseases",
                        height=800, width=1200, show_values=True,
                        colorscale='Reds', save_path=None):
    """Create the heatmap visualization"""
    
    # Create matrices
    score_matrix, pval_matrix, sig_matrix = create_heatmap_matrix(df, sorted_diseases, sorted_hallmarks)
    
    # Create annotations
    annotations = create_heatmap_annotations(score_matrix, sig_matrix, show_values)
    
    # Create the heatmap
    fig = go.Figure(data=go.Heatmap(
        z=score_matrix.values,
        x=score_matrix.columns,
        y=score_matrix.index,
        colorscale=colorscale,
        colorbar=dict(
            title="Mean Enrichment Score",
            tickvals=[0, 5, 10, 15, 20],
            ticktext=['0', '5', '10', '15', '≥20']
        ),
        zmin=0,
        zmax=20,
        hoverongaps=False,
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "<b>%{x}</b><br>" +
            "Enrichment Score: %{z:.2f}<br>" +
            "<extra></extra>"
        )
    ))
    
    # Add annotations
    fig.update_layout(annotations=annotations)
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            font=dict(size=16)
        ),
        xaxis=dict(
            title="Disease (ordered by total enrichment)",
            tickangle=45,
            side='bottom'
        ),
        yaxis=dict(
            title="Aging Hallmark (ordered by total enrichment)",
            tickmode='linear'
        ),
        height=height,
        width=width,
        template='plotly_white',
        margin=dict(l=200, r=150, t=100, b=150)
    )
    
    # Add note about NS
    fig.add_annotation(
        text="NS = Not Significant (FDR ≥ 0.001)",
        xref="paper", yref="paper",
        x=1.0, y=1.05,
        xanchor="right", yanchor="bottom",
        showarrow=False,
        font=dict(size=10, color="gray"),
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="gray",
        borderwidth=1
    )
    
    if save_path:
        fig.write_image(save_path, width=width, height=height, scale=2)
        print(f"Saved heatmap: {save_path}")
    
    return fig
