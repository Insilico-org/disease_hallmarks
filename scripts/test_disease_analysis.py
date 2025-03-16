#!/usr/bin/env python
"""
Script to test disease analysis with the updated OpenTargets API integration
"""
import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import from the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from disease_hallmarks.analysis import DiseaseAnalyzer

def main():
    """Test disease analysis with verbose output"""
    parser = argparse.ArgumentParser(description='Test disease analysis with the updated OpenTargets API integration')
    parser.add_argument('--cache-dir', type=str, default=os.getenv('CACHE_DIR', '.cache'),
                        help='Cache directory path (default: CACHE_DIR env var or .cache)')
    parser.add_argument('--disease', type=str, default="idiopathic pulmonary fibrosis",
                        help='Disease name to analyze')
    parser.add_argument('--score-threshold', type=float, default=0.0,
                        help='Minimum association score threshold (0.0-1.0)')
    args = parser.parse_args()
    
    # Initialize analyzer with specified cache directory
    analyzer = DiseaseAnalyzer(cache_dir=args.cache_dir)
    
    # Test with the specified disease
    disease_name = args.disease
    score_threshold = args.score_threshold
    
    print(f"\nAnalyzing disease: {disease_name}")
    print(f"Using score threshold: {score_threshold}")
    
    # First analyze with no threshold
    print("\n=== Analysis with no score threshold ===")
    result_no_threshold = analyzer.analyze_disease(disease_name, verbose=True)
    
    if result_no_threshold:
        print(f"\nResults for {disease_name} (no threshold):")
        print(f"EFO ID: {result_no_threshold.efo_id}")
        print(f"Number of target genes: {len(result_no_threshold.target_genes)}")
        print(f"Number of longevity genes: {len(result_no_threshold.longevity_genes)}")
        print(f"\nTotal aging score: {result_no_threshold.total_score:.3f}")
        
        # Print top hallmarks
        print("\nTop hallmarks:")
        for i, (hallmark, score) in enumerate(sorted(result_no_threshold.hallmark_scores.items(), 
                                                   key=lambda x: x[1].score, 
                                                   reverse=True)[:5]):
            print(f"{i+1}. {hallmark}: {score.score:.3f}")
    else:
        print(f"Failed to analyze {disease_name}")
    
    # Now analyze with threshold
    if score_threshold > 0:
        print(f"\n=== Analysis with score threshold {score_threshold} ===")
        result_with_threshold = analyzer.analyze_disease(disease_name, verbose=True, score_threshold=score_threshold)
        
        if result_with_threshold:
            print(f"\nResults for {disease_name} (threshold {score_threshold}):")
            print(f"EFO ID: {result_with_threshold.efo_id}")
            print(f"Number of target genes: {len(result_with_threshold.target_genes)}")
            print(f"Number of longevity genes: {len(result_with_threshold.longevity_genes)}")
            print(f"\nTotal aging score: {result_with_threshold.total_score:.3f}")
            
            # Print top hallmarks
            print("\nTop hallmarks:")
            for i, (hallmark, score) in enumerate(sorted(result_with_threshold.hallmark_scores.items(), 
                                                       key=lambda x: x[1].score, 
                                                       reverse=True)[:5]):
                print(f"{i+1}. {hallmark}: {score.score:.3f}")
        else:
            print(f"Failed to analyze {disease_name}")

if __name__ == "__main__":
    main()
