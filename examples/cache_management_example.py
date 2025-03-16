#!/usr/bin/env python3
"""
Example script demonstrating how to use the cache management functionality.

This script shows how to:
1. Check the cache status
2. List cache items by type
3. Clear specific types of cache
4. Clear disease-specific cache
"""

import os
import sys
from pathlib import Path

# Add parent directory to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import dotenv for loading environment variables
from dotenv import load_dotenv

# Load environment variables from .env files
load_dotenv()

from disease_hallmarks.cache import Cache

def main():
    """Demonstrate cache management functionality"""
    # Get cache directory from environment or use default
    cache_dir = os.getenv('CACHE_DIR', '.cache')
    print(f"Using cache directory: {cache_dir}")
    
    # Initialize cache with TTL from environment or default (24 hours)
    cache_ttl = int(os.getenv('CACHE_TTL', '86400'))
    cache = Cache(cache_dir, ttl=cache_ttl)
    
    # Print cache analysis
    print("\n=== Cache Analysis ===")
    cache.print_analysis()
    
    # Example 1: List all cache items
    print("\n=== Example 1: List all cache items ===")
    all_items = cache.list_cache_items()
    print(f"Found {len(all_items)} cache items")
    
    # Example 2: List cache items by type
    print("\n=== Example 2: List cache items by type ===")
    for cache_type in ['enrichr', 'ols', 'opentargets', 'go', 'gpt4', 'other']:
        items = cache.list_cache_by_type(cache_type)
        print(f"Found {len(items)} cache items of type '{cache_type}'")
        
        # Print details of the first 3 items
        for i, item in enumerate(items[:3]):
            print(f"  Item {i+1}:")
            print(f"    Path: {item['path'].name}")
            print(f"    Size: {item['size']} bytes")
            print(f"    Timestamp: {item['timestamp']}")
            print(f"    Expired: {'Yes' if item['is_expired'] else 'No'}")
            print()
    
    # Example 3: Check for disease-specific cache
    print("\n=== Example 3: Check for disease-specific cache ===")
    disease_name = "Alzheimer's disease"
    disease_items = cache.list_disease_cache(disease_name)
    print(f"Found {len(disease_items)} cache items related to '{disease_name}'")
    
    # Example 4: Clear expired cache (demonstration only, commented out)
    print("\n=== Example 4: Clear expired cache ===")
    print("This would clear expired cache items:")
    print("  cache.clear_expired()")
    # Uncomment to actually clear expired cache:
    # cleared = cache.clear_expired()
    # print(f"Cleared {cleared} expired cache items")
    
    # Example 5: Clear cache by type (demonstration only, commented out)
    print("\n=== Example 5: Clear cache by type ===")
    print("This would clear all Enrichr cache items:")
    print("  cache.clear_cache_by_type('enrichr')")
    # Uncomment to actually clear Enrichr cache:
    # cleared = cache.clear_cache_by_type('enrichr')
    # print(f"Cleared {cleared} Enrichr cache items")
    
    # Example 6: Clear disease-specific cache (demonstration only, commented out)
    print("\n=== Example 6: Clear disease-specific cache ===")
    print(f"This would clear all cache items related to '{disease_name}':")
    print(f"  cache.clear_disease_cache('{disease_name}')")
    # Uncomment to actually clear disease-specific cache:
    # cleared = cache.clear_disease_cache(disease_name)
    # print(f"Cleared {cleared} cache items related to '{disease_name}'")

if __name__ == "__main__":
    main()
