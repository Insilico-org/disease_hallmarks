"""
Module for normalizing pathway scores based on hallmark annotations.
This module provides functionality to precompute hallmark annotations for pathways
and normalize scores based on the total number of pathways per hallmark.
"""

import os
import json
from pathlib import Path
import logging
from typing import Dict, List, Set, Optional
from collections import Counter, defaultdict
import hashlib
import math

from .pathway_agent import PathwayAnalysisAgent
from .cache import Cache

class PathwayNormalizer:
    """
    Class for normalizing pathway scores based on hallmark annotations.
    Precomputes hallmark annotations for pathways and provides normalization factors.
    """
    
    def __init__(self, cache_dir: str = None, pathway_agent: Optional[PathwayAnalysisAgent] = None):
        """
        Initialize the PathwayNormalizer.
        
        Args:
            cache_dir: Directory to store cache files
            pathway_agent: Optional PathwayAnalysisAgent instance to use for annotations
        """
        self.cache_dir = cache_dir or os.getenv('CACHE_DIR', '.cache')
        
        # Get cache TTL from environment (default to 24 hours, -1 for infinite)
        cache_ttl = os.getenv('CACHE_TTL')
        if cache_ttl is not None:
            try:
                cache_ttl = int(cache_ttl)
            except ValueError:
                logging.warning(f"Invalid CACHE_TTL value '{cache_ttl}', using default")
                cache_ttl = 86400  # 24 hours
        else:
            cache_ttl = 86400  # 24 hours
            
        # Initialize cache with TTL
        self.cache = Cache(self.cache_dir, ttl=cache_ttl)
        
        self.pathway_agent = pathway_agent
        
        # Dictionary to store hallmark counts
        self.hallmark_pathway_counts: Dict[str, int] = {}
        
        # Dictionary to store pathway to hallmark mappings
        self.pathway_hallmarks: Dict[str, List[str]] = {}
        
        # Path to save/load precomputed annotations
        self.annotations_file = Path(self.cache_dir) / "hallmark_pathway_annotations.json"
        
        # Load precomputed annotations if available
        self._load_annotations()
    
    def _load_annotations(self) -> None:
        """Load precomputed hallmark annotations if available."""
        if self.annotations_file.exists():
            try:
                with open(self.annotations_file, 'r') as f:
                    data = json.load(f)
                    self.pathway_hallmarks = data.get('pathway_hallmarks', {})
                    self.hallmark_pathway_counts = data.get('hallmark_counts', {})
                logging.info(f"Loaded hallmark annotations for {len(self.pathway_hallmarks)} pathways")
                logging.info(f"Hallmark counts: {self.hallmark_pathway_counts}")
            except Exception as e:
                logging.error(f"Error loading hallmark annotations: {e}")
    
    def _save_annotations(self) -> None:
        """Save precomputed hallmark annotations to file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.annotations_file), exist_ok=True)
            
            with open(self.annotations_file, 'w') as f:
                json.dump({
                    'pathway_hallmarks': self.pathway_hallmarks,
                    'hallmark_counts': self.hallmark_pathway_counts
                }, f, indent=2)
            logging.info(f"Saved hallmark annotations to {self.annotations_file}")
        except Exception as e:
            logging.error(f"Error saving hallmark annotations: {e}")
    
    def precompute_annotations(self, go_file_path: str, pathway_agent: Optional[PathwayAnalysisAgent] = None) -> Dict[str, int]:
        """
        Precompute hallmark annotations for all pathways in the GO file.
        
        Args:
            go_file_path: Path to the GO file containing pathway definitions
            pathway_agent: Optional PathwayAnalysisAgent to use for annotations
        
        Returns:
            Dictionary mapping hallmarks to their pathway counts
        """
        if pathway_agent:
            self.pathway_agent = pathway_agent
        
        if not self.pathway_agent:
            raise ValueError("PathwayAgent is required for precomputing annotations")
        
        # Read GO file
        try:
            with open(go_file_path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            logging.error(f"Error reading GO file {go_file_path}: {e}")
            return self.hallmark_pathway_counts
        
        # Process each pathway
        pathways = {}
        for line in lines:
            if not line.strip():
                continue
                
            parts = line.strip().split('\t\t')
            if len(parts) >= 2:
                pathway_name = parts[0].strip()
                # Use a dummy p-value for analysis
                pathways[pathway_name] = 0.001
        
        logging.info(f"Analyzing {len(pathways)} pathways from {go_file_path}")
        
        # Analyze pathways in batches to avoid memory issues
        batch_size = 100
        pathway_list = list(pathways.keys())
        
        for i in range(0, len(pathway_list), batch_size):
            batch = {k: pathways[k] for k in pathway_list[i:i+batch_size]}
            logging.info(f"Processing batch {i//batch_size + 1}/{(len(pathway_list) + batch_size - 1)//batch_size}")
            
            # Analyze pathways
            batch_results = self.pathway_agent.analyze_pathways(batch)
            
            # Update pathway hallmarks dictionary
            self.pathway_hallmarks.update(batch_results)
        
        # Count hallmarks
        hallmark_counter = Counter()
        for pathway, hallmarks in self.pathway_hallmarks.items():
            for hallmark in hallmarks:
                # Skip if hallmark is not a string (e.g., if it's a dictionary)
                if not isinstance(hallmark, str):
                    logging.warning(f"Skipping non-string hallmark for pathway '{pathway}': {hallmark}")
                    continue
                hallmark_counter[hallmark] += 1
        
        # Update hallmark counts
        self.hallmark_pathway_counts = dict(hallmark_counter)
        
        # Save annotations
        self._save_annotations()
        
        return self.hallmark_pathway_counts
    
    def get_normalization_factor(self, hallmark: str) -> float:
        """
        Get normalization factor for a hallmark based on pathway counts.
        
        Args:
            hallmark: Name of the hallmark
            
        Returns:
            Normalization factor (1.0 if no data available)
        """
        if not self.hallmark_pathway_counts or hallmark not in self.hallmark_pathway_counts:
            return 1.0
        
        count = self.hallmark_pathway_counts.get(hallmark, 0)
        if count == 0:
            return 1.0
        
        # Calculate normalization factor using a logarithmic scale
        # This provides a more balanced approach that doesn't penalize
        # hallmarks with many pathways too severely
        # For example:
        # - 1 pathway: 1.0
        # - 4 pathways: ~0.71
        # - 16 pathways: ~0.5
        # - 100 pathways: ~0.32
        return 1.0 / math.sqrt(math.log2(count + 1) + 1)
    
    def normalize_pathway_score(self, hallmark: str, pathway_score: float) -> float:
        """
        Normalize a pathway score based on the hallmark's pathway count.
        
        Args:
            hallmark: Name of the hallmark
            pathway_score: Original pathway score
            
        Returns:
            Normalized pathway score
        """
        normalization_factor = self.get_normalization_factor(hallmark)
        return pathway_score * normalization_factor
