import os
from functools import lru_cache
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import math
from dotenv import load_dotenv
from pathlib import Path
import json
import logging
from typing import Optional

from .models import DiseaseAnnotation, HallmarkScore, DiseaseDB
from .cache import Cache
from .pathway_agent import PathwayAnalysisAgent
from .api_callers import EnrichrAnalysis, OpenTargetsAPI
from .hallmark_genes import *
from .pathway_normalizer import PathwayNormalizer

class DiseaseAnalyzer:
    """Main class for disease analysis through aging hallmarks"""
    
    def __init__(self, cache_dir: str | None = None):
        # Load environment variables
        load_dotenv()
        
        # Use environment variables or defaults
        self.cache_dir = cache_dir or os.getenv('CACHE_DIR', '.cache')
        
        # Get cache TTL from environment (default to 24 hours, -1 for infinite)
        cache_ttl = os.getenv('CACHE_TTL')
        if cache_ttl is not None:
            try:
                cache_ttl = int(cache_ttl)
            except ValueError:
                print(f"Warning: Invalid CACHE_TTL value '{cache_ttl}', using default")
                cache_ttl = 86400  # 24 hours
        else:
            cache_ttl = 86400  # 24 hours
            
        # Initialize cache with TTL
        self.cache = Cache(self.cache_dir, ttl=cache_ttl)
        
        self._load_reference_data()
        self.db = DiseaseDB()
        
        # Check cache and load cached data if available
        self._check_and_load_cache()
        
        # Initialize pathway agent with model from env
        model = os.getenv('PATHWAY_AGENT_MODEL', 'gpt-4')
        self.pathway_agent = PathwayAnalysisAgent(model=model, cache=self.cache)
        
        # Initialize pathway normalizer
        self.pathway_normalizer = PathwayNormalizer(cache_dir=self.cache_dir, pathway_agent=self.pathway_agent)
        
    def _check_and_load_cache(self):
        """Check if cache directory has content and load it"""
        # Analyze cache contents
        self.cache.print_analysis()
        
        # Preload cache into memory for faster access
        loaded_items = self.cache.preload_cache()
        if loaded_items > 0:
            print(f"Preloaded {loaded_items} cache items into memory for faster access")
        
    def _load_reference_data(self):
        """Load hallmark genes and longevity data from modules and files"""
        # Load hallmark genes from the hallmark_genes.py module
        self.hallmark_genes: dict[str, set[str]] = {
            "Genomic instability": set(genomic_instability_genes),
            "Telomere attrition": set(telomere_attrition_genes),
            "Epigenetic alterations": set(epigenetic_alterations_genes),
            "Loss of proteostasis": set(loss_of_proteostasis_genes),
            "Disabled macroautophagy": set(disabled_macroautophagy_genes),
            "Deregulated nutrient sensing": set(deregulated_nutrient_sensing_genes),
            "Mitochondrial dysfunction": set(mitochondrial_dysfunction_genes),
            "Cellular senescence": set(cellular_senescence_genes),
            "Stem cell exhaustion": set(stem_cell_exhaustion_genes),
            "Altered intercellular communication": set(altered_intercellular_communication_genes),
            "Chronic inflammation": set(chronic_inflammation_genes)
        }
            
        # Load longevity genes
        df = pd.read_csv("longevity.csv")
        self.longevity_genes = set(df[df["Association"] == "significant"]["Gene(s)"].unique())
    
    @lru_cache(maxsize=1000)
    def _get_efo_id(self, disease_name: str) -> str | None:
        """Get EFO ID for disease name using OLS API"""
        url = f"https://www.ebi.ac.uk/ols/api/search?q={disease_name}&ontology=efo"
        response = self.cache.get_or_fetch(url)
        data = response.json()
        
        if not data["response"]["docs"]:
            return None
            
        # Get best matching EFO ID
        for doc in data["response"]["docs"]:
            if doc["ontology_name"] == "efo":
                return doc["short_form"]
        return None
    
    @lru_cache(maxsize=1000)
    def _get_disease_targets(self, efo_id: str, score_threshold: float = 0.2) -> list[str]:
        """
        Get target genes for disease from OpenTargets
        
        Args:
            efo_id: EFO ID of the disease
            score_threshold: Minimum association score to include a target (0.0-1.0)
            
        Returns:
            List of gene symbols associated with the disease
        """
        # Create OpenTargetsAPI instance if not already created
        if not hasattr(self, 'ot_api'):
            from disease_hallmarks.api_callers import OpenTargetsAPI
            self.ot_api = OpenTargetsAPI(cache=self.cache)
            
        # Use the API to get disease targets
        # Note: The max_targets parameter is applied after retrieving from cache
        return self.ot_api.get_disease_targets(efo_id, max_targets=25, score_threshold=score_threshold)
    
    def _calculate_hallmark_scores(
        self, 
        disease_genes: list[str],
        enriched_pathways: dict[str, float],
        verbose: bool = False
    ) -> dict[str, HallmarkScore]:
        """Calculate scores for each hallmark based on gene overlaps and pathways"""
        # Create a hashable key for caching
        cache_key = (
            tuple(sorted(disease_genes)),
            tuple(sorted((k, v) for k, v in enriched_pathways.items()))
        )
        
        # Check if we have a cached result
        if hasattr(self, '_hallmark_score_cache'):
            if cache_key in self._hallmark_score_cache:
                return self._hallmark_score_cache[cache_key]
        else:
            # Initialize cache if it doesn't exist
            self._hallmark_score_cache = {}
            
        scores = {}
        
        # Convert to sets for faster operations
        disease_genes_set = set(disease_genes)
        
        if verbose:
            print(f"\n=== Hallmark Scoring Analysis ===")
            print(f"Analyzing {len(disease_genes)} disease genes against {len(self.hallmark_genes)} hallmarks")
            print(f"Found {len(enriched_pathways)} enriched pathways")
        
        # Get pathway-hallmark relationships from AI agent
        pathway_hallmark_scores = self.pathway_agent.analyze_pathways(enriched_pathways)
        
        # Create a mapping between the hallmark names used in the pathway agent and the hallmark names used here
        # The pathway agent uses underscores instead of spaces
        hallmark_name_mapping = {
            "Genomic_instability": "Genomic instability",
            "Telomere_attrition": "Telomere attrition",
            "Epigenetic_alterations": "Epigenetic alterations",
            "Loss_of_proteostasis": "Loss of proteostasis",
            "Disabled_macroautophagy": "Disabled macroautophagy",
            "Deregulated_nutrient_sensing": "Deregulated nutrient sensing",
            "Mitochondrial_dysfunction": "Mitochondrial dysfunction",
            "Cellular_senescence": "Cellular senescence",
            "Stem_cell_exhaustion": "Stem cell exhaustion",
            "Altered_intercellular_communication": "Altered intercellular communication",
            "Chronic_inflammation": "Chronic inflammation"
        }
        
        if verbose:
            # Count pathways per hallmark
            hallmark_pathway_counts = {}
            for hallmark in self.hallmark_genes.keys():
                hallmark_pathway_counts[hallmark] = 0
                
            # Convert hallmark names from pathway agent format to analysis format
            for pathway, hallmarks in pathway_hallmark_scores.items():
                for hallmark in hallmarks:
                    if hallmark in hallmark_name_mapping:
                        mapped_hallmark = hallmark_name_mapping[hallmark]
                        if mapped_hallmark in hallmark_pathway_counts:
                            hallmark_pathway_counts[mapped_hallmark] += 1
            
            print(f"\nHallmark pathway counts:")
            for hallmark, count in sorted(hallmark_pathway_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {hallmark}: {count} enriched pathways")
        
        # First pass to calculate raw scores
        raw_scores = {}
        for hallmark, genes in self.hallmark_genes.items():
            if verbose:
                print(f"Analyzing {hallmark}...", end=" ")
            
            # Calculate direct gene overlap score
            overlapping = disease_genes_set & genes
            gene_score = len(overlapping) / len(genes) if genes else 0
            
            # Convert hallmark name to pathway agent format for comparison
            agent_hallmark_name = None
            for agent_name, analysis_name in hallmark_name_mapping.items():
                if analysis_name == hallmark:
                    agent_hallmark_name = agent_name
                    break
            
            # Calculate pathway score
            pathway_score = 0.0
            pathway_count = 0
            relevant_pathways = []
            
            for pathway, hallmark_list in pathway_hallmark_scores.items():
                if agent_hallmark_name and agent_hallmark_name in hallmark_list:
                    # Weight pathway contribution by -log(p-value)
                    p_value = enriched_pathways[pathway]
                    weight = -math.log10(p_value) if p_value > 0 else 0
                    pathway_score += weight
                    pathway_count += 1
                    relevant_pathways.append(pathway)
            
            if pathway_count > 0:
                # Calculate average pathway score
                avg_pathway_score = pathway_score / pathway_count
                
                # Apply a more balanced normalization based on total pathways for this hallmark
                # Use a logarithmic scale to prevent over-penalizing common hallmarks
                normalization_factor = self.pathway_normalizer.get_normalization_factor(hallmark)
                
                # Apply normalization with a minimum value to prevent zeroing out important hallmarks
                pathway_score = avg_pathway_score * max(normalization_factor, 0.5)
                
                # Apply a bonus for having multiple pathways (diminishing returns)
                pathway_bonus = min(math.log2(pathway_count + 1) / 4, 1.0)  # Caps at 1.0 for 15+ pathways
                pathway_score = pathway_score * (1 + pathway_bonus)
                
                if verbose:
                    print(f"score: {pathway_score:.4f} ({pathway_count} pathways, {len(overlapping)} genes)")
            else:
                if verbose:
                    print(f"score: {pathway_score:.4f} (no pathways, {len(overlapping)} genes)")
            
            # Calculate combined raw score with adjusted weights (30% gene overlap, 70% pathway)
            # This gives more weight to pathway evidence which is often more specific
            raw_total_score = (gene_score * 0.3) + (pathway_score * 0.7)
            
            # Store raw scores and metadata for second pass
            raw_scores[hallmark] = {
                "gene_score": gene_score,
                "pathway_score": pathway_score, 
                "raw_total": raw_total_score,
                "overlapping_genes": list(overlapping),
                "relevant_pathways": relevant_pathways,
                "pathway_count": pathway_count
            }
        
        # Calculate diversity metrics
        non_zero_hallmarks = sum(1 for s in raw_scores.values() if s["raw_total"] > 0)
        total_hallmarks = len(raw_scores)
        
        # Calculate the entropy of the distribution to measure diversity
        # Higher entropy means more evenly distributed hallmarks
        total_raw_score = sum(s["raw_total"] for s in raw_scores.values())
        entropy = 0
        
        if total_raw_score > 0:
            for s in raw_scores.values():
                if s["raw_total"] > 0:
                    p = s["raw_total"] / total_raw_score
                    entropy -= p * math.log(p)
        
        # Normalize entropy by maximum possible entropy
        max_entropy = math.log(non_zero_hallmarks) if non_zero_hallmarks > 0 else 0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        # Calculate standard deviation of scores to measure imbalance
        mean_score = total_raw_score / total_hallmarks if total_hallmarks > 0 else 0
        variance = sum((s["raw_total"] - mean_score) ** 2 for s in raw_scores.values()) / total_hallmarks if total_hallmarks > 0 else 0
        std_dev = math.sqrt(variance)
        
        # Calculate coefficient of variation to measure relative dispersion
        cv = std_dev / mean_score if mean_score > 0 else 0
        
        # Calculate diversity factor (higher for more diverse hallmark profiles)
        # This rewards diseases with multiple hallmarks rather than a single dominant one
        diversity_factor = (non_zero_hallmarks / total_hallmarks) * (1 + normalized_entropy)
        
        if verbose:
            print(f"\n=== Diversity Analysis ===")
            print(f"Non-zero hallmarks: {non_zero_hallmarks}/{total_hallmarks}")
            print(f"Normalized entropy: {normalized_entropy:.4f}")
            print(f"Coefficient of variation: {cv:.4f}")
            print(f"Diversity factor: {diversity_factor:.4f}")
        
        # Second pass to create final scores with diversity adjustment
        for hallmark, raw_data in raw_scores.items():
            # Initialize score object
            score = HallmarkScore(
                name=hallmark,
                gene_overlap_score=raw_data["gene_score"],
                pathway_score=raw_data["pathway_score"],
                overlapping_genes=raw_data["overlapping_genes"],
                relevant_pathways=raw_data["relevant_pathways"]
            )
            
            # Adjust score based on pathway diversity
            # If this hallmark has many pathways, it gets a slight boost
            pathway_diversity = math.sqrt(raw_data["pathway_count"] + 1) / math.sqrt(10)  # Normalize to ~1.0 for 9 pathways
            pathway_diversity = min(pathway_diversity, 1.5)  # Cap the boost
            
            # Calculate final score with diversity adjustment
            score.total_score = raw_data["raw_total"] * pathway_diversity
            
            if verbose:
                print(f"\nFinal {hallmark} score: {score.total_score:.4f} (raw: {raw_data['raw_total']:.4f}, pathway diversity: {pathway_diversity:.2f})")
            
            scores[hallmark] = score
                
        # Store result in cache
        self._hallmark_score_cache[cache_key] = scores
        
        return scores
    
    def _analyze_pathways(self, genes: list[str], pval: float = 0.001, debug: bool = False) -> dict[str, float]:
        """Analyze pathway enrichment using Enrichr"""
        analysis = EnrichrAnalysis(genes, cache=self.cache, debug=debug, description="Disease analysis")
        analysis.analyze()
        
        # Get significant terms
        terms = analysis.get_significant_terms(p_value_threshold=pval, min_overlap=3)

        # Convert to dictionary of pathway -> p-value
        return {term['term']: float(term['p_value']) for term in terms}
    
    def analyze_disease(
        self, 
        disease_name: str, 
        verbose: bool = False,
        score_threshold: float = 0.0
    ) -> Optional[DiseaseAnnotation]:
        """
        Analyze a disease and calculate its aging hallmark scores
        
        Args:
            disease_name: Name of the disease to analyze
            verbose: Whether to print verbose output
            score_threshold: Minimum association score to include a target (0.0-1.0)
            
        Returns:
            DiseaseAnnotation object with results, or None if disease not found
        """
        # First, get the EFO ID for the disease
        efo_id = self._get_efo_id(disease_name)
        
        if not efo_id:
            if verbose:
                print(f"Disease '{disease_name}' not found in EFO ontology")
            return None
            
        if verbose:
            print(f"Found disease: {disease_name} (EFO ID: {efo_id})")
            
        # Get target genes for the disease
        target_genes = self._get_disease_targets(efo_id, score_threshold=score_threshold)
        
        if not target_genes:
            if verbose:
                print(f"No target genes found for disease: {disease_name} (EFO ID: {efo_id})")
            return None
            
        if verbose:
            print(f"Found {len(target_genes)} target genes for {disease_name} (EFO ID: {efo_id})")
            
            # Get total available targets from OpenTargets API
            if hasattr(self, 'ot_api'):
                # Make a minimal query to get just the count
                query = """
                query diseaseAssociationsCount($efoId: String!) {
                  disease(efoId: $efoId) {
                    associatedTargets {
                      count
                    }
                  }
                }
                """
                url = "https://api.platform.opentargets.org/api/v4/graphql"
                try:
                    response = self.cache.get_or_fetch(
                        url, 
                        method="POST",
                        json={"query": query, "variables": {"efoId": efo_id}}
                    )
                    data = response.json()
                    total_count = data["data"]["disease"]["associatedTargets"]["count"]
                    print(f"Total available targets in OpenTargets: {total_count}")
                except Exception:
                    pass
        
        # Get pathway enrichment
        enriched_pathways = self._analyze_pathways(target_genes, debug=verbose)
        
        if not enriched_pathways:
            if verbose:
                print(f"No enriched pathways found for disease: {disease_name}")
                
        # Find overlapping longevity genes
        longevity_overlap = list(set(target_genes) & self.longevity_genes)
        
        if verbose:
            print(f"Number of longevity genes: {len(longevity_overlap)}")
        
        # Calculate hallmark scores
        hallmark_scores = self._calculate_hallmark_scores(target_genes, enriched_pathways, verbose=verbose)
        
        if verbose and longevity_overlap:
            print(f"\nFound {len(longevity_overlap)} overlapping longevity genes:")
            print(f"  {', '.join(longevity_overlap[:10])}{' ...' if len(longevity_overlap) > 10 else ''}")
        
        # Calculate total aging score using a principled approach
        
        # 1. Get scores and count non-zero hallmarks
        hallmark_values = [s.total_score for s in hallmark_scores.values()]
        non_zero_hallmarks = sum(1 for s in hallmark_values if s > 0)
        total_hallmarks = len(hallmark_values)
        
        # 2. Calculate basic statistics
        total_score_sum = sum(hallmark_values)
        mean_score = total_score_sum / total_hallmarks if total_hallmarks > 0 else 0
        
        # 3. Calculate the entropy of the distribution (measure of evenness)
        entropy = 0
        if total_score_sum > 0:
            for score in hallmark_values:
                if score > 0:
                    p = score / total_score_sum
                    entropy -= p * math.log(p)
        
        # Normalize entropy by maximum possible entropy
        max_entropy = math.log(non_zero_hallmarks) if non_zero_hallmarks > 0 else 0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        # 4. Calculate standard deviation to measure spread
        variance = sum((s - mean_score) ** 2 for s in hallmark_values) / total_hallmarks if total_hallmarks > 0 else 0
        std_dev = math.sqrt(variance)
        
        # 5. Calculate coefficient of variation (relative standard deviation)
        cv = std_dev / mean_score if mean_score > 0 else 0
        
        # 6. Calculate representativeness score
        # This rewards diseases with:
        # - Higher average hallmark scores
        # - More non-zero hallmarks (breadth of aging mechanisms)
        # - More even distribution across hallmarks (not dominated by a single hallmark)
        
        # Calculate breadth factor (reward having more non-zero hallmarks)
        # Use a progressive scale that rewards having more non-zero hallmarks
        breadth_factor = (non_zero_hallmarks / total_hallmarks) * (1 + math.log2(non_zero_hallmarks + 1) / 4)
        
        # Calculate evenness factor (reward more even distribution)
        evenness_factor = normalized_entropy
        
        # Calculate strength factor (reward higher average scores)
        strength_factor = mean_score
        
        # Combine factors into representativeness score
        # This formula balances breadth, evenness, and strength
        representativeness = strength_factor * (1 + breadth_factor) * (1 + evenness_factor)
        
        # Calculate final aging score
        # Base on average score but boost by representativeness
        total_score = mean_score * (1 + representativeness)
        
        # Add a small bonus for longevity gene overlap
        longevity_factor = len(longevity_overlap) / 20  # Normalize to ~0.5 for 10 genes
        longevity_factor = min(longevity_factor, 1.0)  # Cap at 1.0
        
        # Apply longevity bonus
        total_score *= (1 + (longevity_factor * 0.2))  # Max 20% boost for longevity genes
        
        if verbose:
            print(f"\n=== Total Aging Score Analysis ===")
            print(f"Non-zero hallmarks: {non_zero_hallmarks}/{total_hallmarks}")
            print(f"Mean hallmark score: {mean_score:.4f}")
            print(f"Normalized entropy: {normalized_entropy:.4f}")
            print(f"Breadth factor: {breadth_factor:.4f}")
            print(f"Evenness factor: {evenness_factor:.4f}")
            print(f"Strength factor: {strength_factor:.4f}")
            print(f"Representativeness: {representativeness:.4f}")
            print(f"Longevity gene bonus: {longevity_factor * 0.2:.4f}")
            print(f"Total aging score: {total_score:.4f}")
        
        # Create annotation with additional metrics
        annotation = DiseaseAnnotation(
            name=disease_name,
            efo_id=efo_id,
            target_genes=target_genes,
            hallmark_scores=hallmark_scores,
            longevity_genes=longevity_overlap,
            enriched_pathways=enriched_pathways,
            total_aging_score=total_score
        )
        
        # Add to database
        self.db.add_disease(annotation)
        
        return annotation
    
    def compare_diseases(
        self, 
        disease1_name: str, 
        disease2_name: str,
        verbose: bool = False
    ) -> tuple[DiseaseAnnotation | None, DiseaseAnnotation | None]:
        """Analyze and compare two diseases"""
        if verbose:
            print(f"Comparing diseases: {disease1_name} vs {disease2_name}")
            
        d1 = self.analyze_disease(disease1_name, verbose=verbose)
        d2 = self.analyze_disease(disease2_name, verbose=verbose)
        
        if verbose and d1 and d2:
            print("\n=== Disease Comparison Summary ===")
            print(f"{disease1_name} total score: {d1.total_aging_score:.4f}")
            print(f"{disease2_name} total score: {d2.total_aging_score:.4f}")
            
            # Compare top hallmarks
            print("\nTop hallmarks comparison:")
            d1_top = dict(d1.get_top_hallmarks(5))
            d2_top = dict(d2.get_top_hallmarks(5))
            
            all_top = set(d1_top.keys()) | set(d2_top.keys())
            for hallmark in all_top:
                score1 = d1_top.get(hallmark, 0)
                score2 = d2_top.get(hallmark, 0)
                diff = abs(score1 - score2)
                print(f"  {hallmark}: {score1:.4f} vs {score2:.4f} (diff: {diff:.4f})")
        
        return d1, d2
    
    def plot_hallmark_comparison(
        self,
        disease1: DiseaseAnnotation,
        disease2: DiseaseAnnotation
    ) -> go.Figure:
        """Create comparison plot of hallmark scores"""
        hallmarks = list(self.hallmark_genes.keys())
        
        # Create shorter labels for the y-axis
        def shorten_hallmark_name(name):
            # If the name contains "GO:" extract just that part
            if "GO:" in name:
                return name.split("GO:")[1].split()[0]
            # Otherwise take the first few words or characters
            words = name.split()
            if len(words) > 3:
                return " ".join(words[:3]) + "..."
            return name
        
        # Create mapping of full names to short names
        short_hallmarks = [shorten_hallmark_name(h) for h in hallmarks]
        
        # Create subplots
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(disease1.name, disease2.name)
        )
        
        # Add bars for each disease
        for i, disease in enumerate([disease1, disease2], 1):
            scores = [disease.hallmark_scores[h].total_score for h in hallmarks]
            fig.add_trace(
                go.Bar(
                    x=scores,
                    y=short_hallmarks,  # Use shortened names
                    orientation='h',
                    name=disease.name,
                    hovertext=hallmarks  # Show full name on hover
                ),
                row=1, col=i
            )
        
        # Update layout
        fig.update_layout(
            title="Hallmark Score Comparison",
            showlegend=False,
            height=600,
            margin=dict(l=150)  # Add more margin on the left for the labels
        )
        
        return fig

    def visualize_score_components(self, disease_annotation: DiseaseAnnotation) -> go.Figure:
        """Create a visualization showing the components of each hallmark score"""
        # Get all hallmarks and sort by total score
        hallmarks = sorted(
            disease_annotation.hallmark_scores.keys(),
            key=lambda h: disease_annotation.hallmark_scores[h].total_score,
            reverse=True
        )
        
        # Extract score components
        gene_scores = [disease_annotation.hallmark_scores[h].gene_overlap_score for h in hallmarks]
        pathway_scores = [disease_annotation.hallmark_scores[h].pathway_score for h in hallmarks]
        total_scores = [disease_annotation.hallmark_scores[h].total_score for h in hallmarks]
        
        # Create figure
        fig = go.Figure()
        
        # Add bars for each score component
        fig.add_trace(go.Bar(
            y=hallmarks,
            x=gene_scores,
            name='Gene Overlap Score',
            orientation='h',
            marker=dict(color='rgba(58, 71, 180, 0.6)')
        ))
        
        fig.add_trace(go.Bar(
            y=hallmarks,
            x=pathway_scores,
            name='Pathway Score',
            orientation='h',
            marker=dict(color='rgba(246, 78, 139, 0.6)')
        ))
        
        fig.add_trace(go.Scatter(
            y=hallmarks,
            x=total_scores,
            name='Total Score',
            mode='markers',
            marker=dict(color='black', size=10)
        ))
        
        # Update layout
        fig.update_layout(
            title=f"Score Components for {disease_annotation.name}",
            xaxis_title="Score",
            barmode='group',
            height=600,
            margin=dict(l=150),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig

    def visualize_disease_comparison(
        self,
        disease1: DiseaseAnnotation,
        disease2: DiseaseAnnotation
    ) -> dict[str, go.Figure]:
        """Create a comprehensive visualization comparing two diseases
        
        Returns:
            Dictionary with multiple figures for different aspects of comparison
        """
        figures = {}
        
        # 1. Standard hallmark comparison (existing method)
        figures['hallmark_comparison'] = self.plot_hallmark_comparison(disease1, disease2)
        
        # 2. Score components for each disease
        figures['disease1_components'] = self.visualize_score_components(disease1)
        figures['disease2_components'] = self.visualize_score_components(disease2)
        
        # 3. Score difference visualization
        diff_data = []
        for hallmark in self.hallmark_genes.keys():
            score1 = disease1.hallmark_scores.get(hallmark, HallmarkScore(hallmark)).total_score
            score2 = disease2.hallmark_scores.get(hallmark, HallmarkScore(hallmark)).total_score
            diff = score2 - score1  # Positive means disease2 has higher score
            diff_data.append((hallmark, diff))
        
        # Sort by absolute difference
        diff_data.sort(key=lambda x: abs(x[1]), reverse=True)
        
        # Create difference figure
        diff_fig = go.Figure()
        
        # Add bars for differences
        hallmarks = [d[0] for d in diff_data]
        diffs = [d[1] for d in diff_data]
        colors = ['rgba(246, 78, 139, 0.8)' if d > 0 else 'rgba(58, 71, 180, 0.8)' for d in diffs]
        
        diff_fig.add_trace(go.Bar(
            y=hallmarks,
            x=diffs,
            orientation='h',
            marker_color=colors,
            text=[f"{abs(d):.4f}" for d in diffs],
            textposition='auto'
        ))
        
        # Add reference line at zero
        diff_fig.add_shape(
            type="line",
            x0=0, y0=-0.5,
            x1=0, y1=len(hallmarks)-0.5,
            line=dict(color="black", width=1, dash="dash")
        )
        
        # Update layout
        diff_fig.update_layout(
            title=f"Hallmark Score Differences: {disease2.name} - {disease1.name}",
            xaxis_title="Score Difference",
            height=600,
            margin=dict(l=150),
            xaxis=dict(
                zeroline=True,
                zerolinecolor='black',
                zerolinewidth=1
            )
        )
        
        figures['score_differences'] = diff_fig
        
        return figures

    def export_score_breakdown(self, disease_annotation: DiseaseAnnotation, file_path: str) -> None:
        """Export the detailed score breakdown for a disease to a CSV file
        
        Args:
            disease_annotation: The disease annotation to export
            file_path: Path to save the CSV file
        """
        # Create data for each hallmark
        data = []
        for hallmark, score in disease_annotation.hallmark_scores.items():
            row = {
                'Hallmark': hallmark,
                'Gene Overlap Score': score.gene_overlap_score,
                'Pathway Score': score.pathway_score,
                'Total Score': score.total_score,
                'Overlapping Gene Count': len(score.overlapping_genes),
                'Relevant Pathway Count': len(score.relevant_pathways),
                'Overlapping Genes': ','.join(score.overlapping_genes[:10]) + ('...' if len(score.overlapping_genes) > 10 else ''),
                'Relevant Pathways': ','.join(score.relevant_pathways[:5]) + ('...' if len(score.relevant_pathways) > 5 else '')
            }
            data.append(row)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(data)
        df.sort_values('Total Score', ascending=False, inplace=True)
        df.to_csv(file_path, index=False)
        
        logging.info(f"Score breakdown exported to {file_path}")
