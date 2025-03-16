#!/usr/bin/env python
"""
Script to precompute hallmark annotations for all pathways in the GO file.
This allows for faster analysis and proper normalization of pathway scores.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from disease_hallmarks.pathway_agent import PathwayAnalysisAgent
from disease_hallmarks.pathway_normalizer import PathwayNormalizer
from disease_hallmarks.cache import Cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main function to precompute hallmark annotations."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Precompute hallmark annotations for pathways')
    parser.add_argument('--go-file', type=str, default='materials/GO_Molecular_Function_2023',
                        help='Path to GO file containing pathway definitions')
    parser.add_argument('--cache-dir', type=str, default=None,
                        help='Directory to store cache files (default: use environment variable or .cache)')
    parser.add_argument('--model', type=str, default=None,
                        help='Model to use for pathway analysis (default: use environment variable or gpt-4)')
    parser.add_argument('--ttl', type=int, default=None,
                        help='Cache TTL in seconds, use -1 for infinite (default: use environment variable or 24 hours)')
    parser.add_argument('--use-quick-go', action='store_true', default=True,
                        help='Use QuickGO API instead of Gene Ontology API (default: True)')
    parser.add_argument('--use-gene-ontology', action='store_false', dest='use_quick_go',
                        help='Use Gene Ontology API instead of QuickGO API')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Use environment variables or defaults
    cache_dir = args.cache_dir or os.getenv('CACHE_DIR', '.cache')
    model = args.model or os.getenv('PATHWAY_AGENT_MODEL', 'gpt-4')
    
    # Get cache TTL from arguments, environment, or default
    if args.ttl is not None:
        cache_ttl = args.ttl
    else:
        cache_ttl_env = os.getenv('CACHE_TTL')
        if cache_ttl_env is not None:
            try:
                cache_ttl = int(cache_ttl_env)
            except ValueError:
                logging.warning(f"Invalid CACHE_TTL value '{cache_ttl_env}', using default")
                cache_ttl = 86400  # 24 hours
        else:
            cache_ttl = 86400  # 24 hours
    
    # Initialize cache
    logging.info(f"Initializing Cache with directory: {cache_dir}, TTL: {cache_ttl}")
    cache = Cache(cache_dir, ttl=cache_ttl)
    
    # Initialize pathway agent
    logging.info(f"Initializing PathwayAnalysisAgent with model: {model}")
    logging.info(f"Using {'QuickGO API' if args.use_quick_go else 'Gene Ontology API'}")
    pathway_agent = PathwayAnalysisAgent(model=model, cache=cache, max_tokens=7500, use_quick_go=args.use_quick_go)
    
    # Initialize pathway normalizer
    logging.info(f"Initializing PathwayNormalizer with cache directory: {cache_dir}")
    normalizer = PathwayNormalizer(cache_dir=cache_dir, pathway_agent=pathway_agent)
    
    # Precompute annotations
    go_file_path = args.go_file
    logging.info(f"Precomputing hallmark annotations for pathways in {go_file_path}")
    
    # Check if file exists
    if not Path(go_file_path).exists():
        logging.error(f"GO file not found: {go_file_path}")
        sys.exit(1)
    
    # Precompute annotations
    hallmark_counts = normalizer.precompute_annotations(go_file_path, pathway_agent)
    
    # Print results
    logging.info("Precomputation complete!")
    logging.info(f"Analyzed {len(normalizer.pathway_hallmarks)} pathways")
    logging.info("Hallmark counts:")
    for hallmark, count in sorted(hallmark_counts.items(), key=lambda x: x[1], reverse=True):
        logging.info(f"  - {hallmark}: {count} pathways")
    
    logging.info(f"Annotations saved to {normalizer.annotations_file}")

if __name__ == "__main__":
    main()
