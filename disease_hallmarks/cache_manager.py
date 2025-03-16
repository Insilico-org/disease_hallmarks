#!/usr/bin/env python3
"""
Cache Manager - Utility for managing the disease_hallmarks cache

This module provides a command-line interface for inspecting, analyzing,
and clearing the cache used by the disease_hallmarks package.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Import dotenv for loading environment variables
from dotenv import load_dotenv

# Load environment variables from .env files
load_dotenv()

from disease_hallmarks.cache import Cache

def format_size(size_bytes: int) -> str:
    """Format size in human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def print_cache_item(item: dict, verbose: bool = False):
    """Print information about a cache item"""
    print(f"  - {item['path'].name}")
    print(f"    Type: {item['type']}")
    print(f"    Size: {format_size(item['size'])}")
    print(f"    Timestamp: {item['timestamp']}")
    print(f"    Expired: {'Yes' if item['is_expired'] else 'No'}")
    
    if verbose and item['original_key'] != 'unknown':
        print(f"    Key: {item['original_key']}")
    
    print()

def analyze_command(args):
    """Analyze the cache contents"""
    cache = Cache(args.cache_dir, ttl=args.ttl)
    
    # Get all cache items
    all_items = cache.list_cache_by_type()
    
    if not all_items:
        print(f"No cache items found in {args.cache_dir}")
        return
    
    # Group by type
    items_by_type = {
        'enrichr': [],
        'ols': [],
        'opentargets': [],
        'gpt4': [],
        'go': [],
        'other': [],
        'error': []
    }
    
    total_size = 0
    for item in all_items:
        item_type = item['type']
        items_by_type[item_type].append(item)
        total_size += item['size']
    
    # Print analysis
    print(f"\n===== Cache Analysis =====")
    print(f"Cache directory: {args.cache_dir}")
    print(f"Total cached items: {len(all_items)} ({format_size(total_size)})")
    
    print("\nAPI breakdown:")
    print(f"- EBI Ontology Lookup Service: {len(items_by_type['ols'])} items")
    print(f"- Open Targets API: {len(items_by_type['opentargets'])} items")
    print(f"- Enrichr API: {len(items_by_type['enrichr'])} items")
    print(f"- Gene Ontology/QuickGO API: {len(items_by_type['go'])} items")
    print(f"- GPT-4 Pathway Analysis: {len(items_by_type['gpt4'])} items")
    print(f"- Other/Unknown: {len(items_by_type['other']) + len(items_by_type['error'])} items")
    
    # Show GPT-4 pathway analysis details if any exist
    if len(items_by_type['gpt4']) > 0:
        print(f"\nGPT-4 Pathway Analysis:")
        print(f"- {len(items_by_type['gpt4'])} cached pathway analyses")
        print(f"- These are expensive API calls that have been cached for reuse")
        print(f"- Each cached pathway analysis saves approximately $0.01-$0.03 in API costs")
        estimated_savings = len(items_by_type['gpt4']) * 0.02  # Average cost per call
        print(f"- Estimated cost savings: ${estimated_savings:.2f}")
    
    print("===========================\n")

def list_command(args):
    """List cache items"""
    cache = Cache(args.cache_dir, ttl=args.ttl)
    
    if args.disease:
        # List disease-specific cache
        items = cache.list_disease_cache(args.disease)
        if not items:
            print(f"No cache items found for disease: {args.disease}")
            return
        
        print(f"Found {len(items)} cache items for disease '{args.disease}':")
        
    elif args.type:
        # List cache by type
        items = cache.list_cache_by_type(args.type)
        if not items:
            print(f"No cache items found of type: {args.type}")
            return
        
        print(f"Found {len(items)} cache items of type '{args.type}':")
        
    else:
        # List all cache
        items = cache.list_cache_by_type()
        if not items:
            print(f"No cache items found in {args.cache_dir}")
            return
        
        print(f"Found {len(items)} cache items:")
    
    # Print items
    for item in items:
        print_cache_item(item, args.verbose)

def clear_command(args):
    """Clear cache items"""
    cache = Cache(args.cache_dir, ttl=args.ttl)
    
    if args.expired:
        # Clear expired cache
        cleared = cache.clear_expired()
        print(f"Cleared {cleared} expired cache items")
        
    elif args.disease:
        # Clear disease-specific cache
        cleared = cache.clear_disease_cache(args.disease)
        print(f"Cleared {cleared} cache items for disease '{args.disease}'")
        
    elif args.type:
        # Clear cache by type
        cleared = cache.clear_cache_by_type(args.type)
        print(f"Cleared {cleared} cache items of type '{args.type}'")
        
    elif args.all:
        # Clear all cache
        all_items = cache.list_cache_by_type()
        cleared = 0
        
        for item in all_items:
            try:
                item['path'].unlink()
                cleared += 1
            except Exception:
                pass
                
        print(f"Cleared {cleared} cache items")
        
    else:
        print("No clear option specified. Use --expired, --disease, --type, or --all")

def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()
    
    # Get default cache directory from environment
    default_cache_dir = os.getenv('CACHE_DIR', '.cache')
    
    parser = argparse.ArgumentParser(
        description='Disease Hallmarks Cache Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze cache contents
  python -m disease_hallmarks.cache_manager analyze
  
  # List all cache items
  python -m disease_hallmarks.cache_manager list
  
  # List cache items for a specific disease
  python -m disease_hallmarks.cache_manager list --disease "Alzheimer's disease"
  
  # List cache items of a specific type
  python -m disease_hallmarks.cache_manager list --type enrichr
  
  # Clear expired cache items
  python -m disease_hallmarks.cache_manager clear --expired
  
  # Clear cache items for a specific disease
  python -m disease_hallmarks.cache_manager clear --disease "Alzheimer's disease"
  
  # Clear cache items of a specific type
  python -m disease_hallmarks.cache_manager clear --type opentargets
  
  # Clear all cache items
  python -m disease_hallmarks.cache_manager clear --all
"""
    )
    
    # Global arguments
    parser.add_argument('--cache-dir', type=str, default=default_cache_dir,
                        help=f'Cache directory path (default: CACHE_DIR env var or .cache)')
    parser.add_argument('--ttl', type=int, default=int(os.getenv('CACHE_TTL', '86400')),
                        help='Cache TTL in seconds for expiration check (default: CACHE_TTL env var or 24 hours)')
    
    # Subparsers
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze cache contents')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List cache items')
    list_parser.add_argument('--disease', type=str, help='List cache items for a specific disease')
    list_parser.add_argument('--type', type=str, choices=['enrichr', 'ols', 'opentargets', 'gpt4', 'go', 'other'],
                            help='List cache items of a specific type')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='Show more details for each item')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear cache items')
    clear_parser.add_argument('--expired', action='store_true', help='Clear expired cache items')
    clear_parser.add_argument('--disease', type=str, help='Clear cache items for a specific disease')
    clear_parser.add_argument('--type', type=str, choices=['enrichr', 'ols', 'opentargets', 'gpt4', 'go', 'other'],
                             help='Clear cache items of a specific type')
    clear_parser.add_argument('--all', action='store_true', help='Clear all cache items')
    
    args = parser.parse_args()
    
    # Print the cache directory being used
    print(f"Using cache directory: {args.cache_dir}")
    
    # Run the appropriate command
    if args.command == 'analyze':
        analyze_command(args)
    elif args.command == 'list':
        list_command(args)
    elif args.command == 'clear':
        clear_command(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
