#!/usr/bin/env python3
"""
Wrapper script for the disease_hallmarks.cache_manager module.
This script allows for easy management of the cache from the command line.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and run the main function from cache_manager
from disease_hallmarks.cache_manager import main

if __name__ == "__main__":
    main()
