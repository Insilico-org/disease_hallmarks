import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

def plot_all_disease_scores(disease_dict):
    """
    Create a bar chart comparing total aging scores for all diseases.
    
    Args:
        disease_dict: Dictionary mapping disease names to DiseaseAnnotation objects
        
    Returns:
        Plotly figure object
    """
    # Extract disease names and scores
    diseases = list(disease_dict.keys())
    scores = [disease_dict[d].total_aging_score for d in diseases]
    
    # Sort by score in descending order
    sorted_indices = np.argsort(scores)[::-1]
    sorted_diseases = [diseases[i] for i in sorted_indices]
    sorted_scores = [scores[i] for i in sorted_indices]
    
    # Create bar chart
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=sorted_diseases,
            y=sorted_scores,
            marker_color='darkblue',
            text=[f"{score:.3f}" for score in sorted_scores],
            textposition='auto'
        )
    )
    
    # Update layout
    fig.update_layout(
        title="Total Aging Score by Disease",
        xaxis_title="Disease",
        yaxis_title="Total Aging Score",
        xaxis_tickangle=-45,
        height=600,
        margin=dict(b=150)  # Add bottom margin for rotated labels
    )
    
    return fig

def plot_hallmark_heatmap(disease_dict):
    """
    Create a heatmap showing hallmark scores across all diseases.
    
    Args:
        disease_dict: Dictionary mapping disease names to DiseaseAnnotation objects
        
    Returns:
        Plotly figure object
    """
    # Get list of all hallmarks from the first disease (assuming all have the same hallmarks)
    first_disease = next(iter(disease_dict.values()))
    hallmarks = list(first_disease.hallmark_scores.keys())
    
    # Create a DataFrame with hallmark scores for each disease
    data = []
    for disease_name, disease in disease_dict.items():
        row = {'Disease': disease_name}
        for hallmark in hallmarks:
            row[hallmark] = disease.hallmark_scores[hallmark].total_score
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Sort diseases by total aging score
    df['Total Score'] = df[hallmarks].sum(axis=1)
    df = df.sort_values('Total Score', ascending=False)
    
    # Melt the DataFrame for heatmap
    df_melted = pd.melt(
        df, 
        id_vars=['Disease', 'Total Score'],
        value_vars=hallmarks,
        var_name='Hallmark',
        value_name='Score'
    )
    
    # Create heatmap
    fig = px.density_heatmap(
        df_melted,
        x='Hallmark',
        y='Disease',
        z='Score',
        color_continuous_scale='Viridis',
        title='Hallmark Scores Across Diseases'
    )
    
    # Update layout
    fig.update_layout(
        xaxis_tickangle=-45,
        height=800,
        margin=dict(l=150, b=150)
    )
    
    return fig

def identify_representative_diseases(disease_dict):
    """
    Identify which diseases are most representative of aging based on:
    1. Total aging score
    2. Number of hallmarks with non-zero scores
    3. Distribution of scores across hallmarks
    
    Args:
        disease_dict: Dictionary mapping disease names to DiseaseAnnotation objects
        
    Returns:
        DataFrame with ranking metrics
    """
    # Get list of all hallmarks from the first disease
    first_disease = next(iter(disease_dict.values()))
    hallmarks = list(first_disease.hallmark_scores.keys())
    
    # Create data for analysis
    data = []
    for disease_name, disease in disease_dict.items():
        # Get hallmark scores
        scores = [disease.hallmark_scores[h].total_score for h in hallmarks]
        
        # Calculate metrics
        total_score = disease.total_aging_score
        non_zero_hallmarks = sum(1 for s in scores if s > 0)
        score_std = np.std(scores)  # Standard deviation of scores
        max_score = max(scores)
        
        # Calculate a "representativeness score" 
        # Higher is better: combines total score, number of hallmarks, and evenness
        representativeness = total_score * (non_zero_hallmarks / len(hallmarks)) * (1 / (1 + score_std))
        
        data.append({
            'Disease': disease_name,
            'Total Aging Score': total_score,
            'Non-zero Hallmarks': non_zero_hallmarks,
            'Score Std Dev': score_std,
            'Max Hallmark Score': max_score,
            'Representativeness': representativeness
        })
    
    # Create DataFrame and sort by representativeness
    df = pd.DataFrame(data)
    df = df.sort_values('Representativeness', ascending=False)
    
    return df

def plot_multi_disease_radar(disease_dict, disease_names=None):
    """
    Create a radar chart comparing multiple diseases across all hallmarks.
    
    Args:
        disease_dict: Dictionary mapping disease names to DiseaseAnnotation objects
        disease_names: List of disease names to include (if None, include all)
        
    Returns:
        Plotly figure object
    """
    # Get list of all hallmarks from the first disease
    first_disease = next(iter(disease_dict.values()))
    hallmarks = list(first_disease.hallmark_scores.keys())
    
    # If no specific diseases provided, use all
    if disease_names is None:
        disease_names = list(disease_dict.keys())
    
    # Create radar chart
    fig = go.Figure()
    
    # Add a trace for each disease
    for disease_name in disease_names:
        if disease_name not in disease_dict:
            continue
            
        disease = disease_dict[disease_name]
        scores = [disease.hallmark_scores[h].total_score for h in hallmarks]
        
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=hallmarks,
            fill='toself',
            name=disease_name
        ))
    
    # Update layout
    fig.update_layout(
        title="Multi-Disease Hallmark Comparison",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max([disease_dict[d].hallmark_scores[h].total_score 
                              for d in disease_names 
                              for h in hallmarks]) * 1.1]
            )
        ),
        showlegend=True,
        height=700,
        width=800
    )
    
    return fig
