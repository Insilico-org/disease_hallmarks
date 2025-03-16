import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Any, Union
import requests
from datetime import datetime, timedelta

class Cache:
    """Simple file-based cache for API responses"""
    
    # Special value for infinite TTL (never expire)
    INFINITE_TTL = -1
    
    def __init__(self, cache_dir: str, ttl: int = 86400):
        """
        Initialize cache
        
        Args:
            cache_dir: Directory to store cache files
            ttl: Time to live in seconds (default 24 hours), use INFINITE_TTL for no expiration
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get path for cache file"""
        # Create hash of key for filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and is not expired"""
        # Create hash of key for lookup
        key_hash = hashlib.md5(key.encode()).hexdigest()
        
        # Check in-memory cache first if available
        if hasattr(self, '_memory_cache') and key_hash in self._memory_cache:
            return self._memory_cache[key_hash]
        
        # Otherwise check file cache
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
            
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                
            # Check if TTL is set to infinite
            if self.ttl == Cache.INFINITE_TTL:
                return data.get('value')
                
            # Check if cache is expired
            timestamp = data.get('timestamp')
            if timestamp:
                cache_time = datetime.fromisoformat(timestamp)
                if datetime.now() - cache_time < timedelta(seconds=self.ttl):
                    return data.get('value')
            
            return None
        except Exception as e:
            print(f"Error reading cache: {e}")
            return None
    
    def set(self, key: str, value: Any):
        """Save value to cache"""
        cache_path = self._get_cache_path(key)
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "value": value,
            "original_key": key  # Store the original key for debugging
        }
        
        with open(cache_path, "w") as f:
            json.dump(data, f)
    
    def get_or_fetch(
        self, 
        url: str, 
        method: str = "GET",
        **kwargs
    ) -> requests.Response:
        """Get response from cache or make new request"""
        # Create cache key from URL and request params
        cache_key = f"{method}:{url}"
        if "json" in kwargs:
            cache_key += f":{json.dumps(kwargs['json'], sort_keys=True)}"
        
        # Try to get from cache
        cached = self.get(cache_key)
        if cached:
            # Create mock response
            response = requests.Response()
            response._content = json.dumps(cached).encode()
            response.status_code = 200
            return response
        
        # Make actual request
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        
        # Cache the response data
        self.set(cache_key, response.json())
        
        return response
        
    def analyze_cache(self) -> dict:
        """
        Analyze the cache contents and return a dictionary with detailed information
        
        Returns:
            Dictionary with cache analysis information
        """
        cache_path = self.cache_dir
        if not cache_path.exists():
            return {"error": f"Cache directory {cache_path} does not exist"}
            
        # Get all JSON files in cache directory
        cache_files = list(cache_path.glob("*.json"))
        if not cache_files:
            return {"error": f"No cache files found in {cache_path}"}
            
        # Categorize cache files by API type
        api_types = {
            "ols_search": [],  # EBI Ontology Lookup Service
            "opentargets": [],  # Open Targets API
            "enrichr": [],     # Enrichr API
            "pathway_analysis": [],  # GPT-4 pathway analysis
            "other": []        # Other APIs
        }
        
        # Track diseases that have been cached
        cached_diseases = set()
        
        # Analyze each cache file
        for cache_file in cache_files:
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    
                # Extract the original URL or key from the data if possible
                value = data.get("value", {})
                key = data.get("key", "")
                
                # Categorize based on content patterns and key patterns
                if "pathway_analysis_" in cache_file.stem:
                    # This is a GPT-4 pathway analysis call
                    api_types["pathway_analysis"].append(cache_file)
                elif isinstance(value, dict):
                    if "response" in value and "docs" in value.get("response", {}):
                        # This is an OLS API response
                        api_types["ols_search"].append(cache_file)
                        
                        # Try to extract disease name
                        docs = value.get("response", {}).get("docs", [])
                        if docs:
                            for doc in docs:
                                if "label" in doc and doc.get("ontology_name") == "efo":
                                    cached_diseases.add(doc.get("label"))
                                    break
                    
                    elif "data" in value and "disease" in value.get("data", {}):
                        # This is an Open Targets API response
                        api_types["opentargets"].append(cache_file)
                        
                    elif any(key.startswith("KEGG_") or key.startswith("GO_") for key in value.keys()):
                        # This is likely an Enrichr API response
                        api_types["enrichr"].append(cache_file)
                    
                    else:
                        # Other API
                        api_types["other"].append(cache_file)
                elif "enrichr_" in cache_file.stem:
                    # This is an Enrichr API response based on the key
                    api_types["enrichr"].append(cache_file)
                else:
                    api_types["other"].append(cache_file)
                    
            except (json.JSONDecodeError, KeyError, ValueError):
                api_types["other"].append(cache_file)
        
        # Calculate total cache size
        cache_size_mb = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)
        
        # Get timestamp range
        timestamps = []
        for cache_file in cache_files:
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    if "timestamp" in data:
                        timestamps.append(data["timestamp"])
            except:
                pass
                
        timestamp_range = {}
        if timestamps:
            timestamps.sort()
            timestamp_range = {
                "oldest": timestamps[0],
                "newest": timestamps[-1]
            }
            
        # Return analysis results
        return {
            "cache_dir": str(cache_path),
            "total_items": len(cache_files),
            "size_mb": cache_size_mb,
            "api_breakdown": {
                "ols_search": len(api_types["ols_search"]),
                "opentargets": len(api_types["opentargets"]),
                "enrichr": len(api_types["enrichr"]),
                "pathway_analysis": len(api_types["pathway_analysis"]),
                "other": len(api_types["other"])
            },
            "cached_diseases": list(cached_diseases),
            "timestamp_range": timestamp_range
        }
        
    def print_analysis(self):
        """Print a detailed analysis of the cache contents"""
        analysis = self.analyze_cache()
        
        if "error" in analysis:
            print(f"\n===== Cache Analysis =====")
            print(f"Error: {analysis['error']}")
            print("===========================\n")
            return
            
        print(f"\n===== Cache Analysis =====")
        print(f"Cache directory: {analysis['cache_dir']}")
        print(f"Total cached items: {analysis['total_items']} ({analysis['size_mb']:.2f} MB)")
        
        print(f"\nAPI breakdown:")
        print(f"- EBI Ontology Lookup Service: {analysis['api_breakdown']['ols_search']} items")
        print(f"- Open Targets API: {analysis['api_breakdown']['opentargets']} items")
        print(f"- Enrichr API: {analysis['api_breakdown']['enrichr']} items")
        print(f"- GPT-4 Pathway Analysis: {analysis['api_breakdown']['pathway_analysis']} items")
        print(f"- Other/Unknown: {analysis['api_breakdown']['other']} items")
        
        if analysis['cached_diseases']:
            print(f"\nCached disease queries (up to 5):")
            for disease in analysis['cached_diseases'][:5]:
                print(f"- {disease}")
            
            if len(analysis['cached_diseases']) > 5:
                print(f"- ...and {len(analysis['cached_diseases']) - 5} more")
        
        if analysis['timestamp_range']:
            print(f"\nCache timestamp range:")
            print(f"- Oldest: {analysis['timestamp_range']['oldest']}")
            print(f"- Newest: {analysis['timestamp_range']['newest']}")
        
        # Show GPT-4 pathway analysis details if any exist
        if analysis['api_breakdown']['pathway_analysis'] > 0:
            print(f"\nGPT-4 Pathway Analysis:")
            print(f"- {analysis['api_breakdown']['pathway_analysis']} cached pathway analyses")
            print(f"- These are expensive API calls that have been cached for reuse")
            print(f"- Each cached pathway analysis saves approximately $0.01-$0.03 in API costs")
            estimated_savings = analysis['api_breakdown']['pathway_analysis'] * 0.02  # Average cost per call
            print(f"- Estimated cost savings: ${estimated_savings:.2f}")
            
        print("===========================\n")
        
    def preload_cache(self) -> int:
        """
        Preload all cache files into memory for faster access
        
        This method scans all cache files and loads them into an in-memory dictionary
        for faster access. This is useful when you know you'll be accessing many
        cached items and want to avoid disk I/O.
        
        Returns:
            int: Number of cache items loaded
        """
        cache_path = self.cache_dir
        if not cache_path.exists():
            return 0
            
        # Get all JSON files in cache directory
        cache_files = list(cache_path.glob("*.json"))
        if not cache_files:
            return 0
            
        # In-memory cache dictionary
        self._memory_cache = {}
        loaded_count = 0
        
        # Load each cache file
        for cache_file in cache_files:
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                
                # Extract key from filename
                key_hash = cache_file.stem
                
                # Check if expired
                if "timestamp" in data:
                    if self.ttl == Cache.INFINITE_TTL:
                        self._memory_cache[key_hash] = data["value"]
                        loaded_count += 1
                    else:
                        cached_time = datetime.fromisoformat(data["timestamp"])
                        if datetime.now() - cached_time < timedelta(seconds=self.ttl):
                            self._memory_cache[key_hash] = data["value"]
                            loaded_count += 1
                    
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
                
        return loaded_count

    def list_cache_items(self, pattern: str = None) -> list[dict]:
        """
        List all cache items, optionally filtered by a pattern in the original key.
        
        Args:
            pattern: Optional string pattern to filter keys
            
        Returns:
            List of dicts with key, hash, timestamp, and is_expired information
        """
        results = []
        
        # Iterate through all files in the cache directory
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                # Extract original key if available
                original_key = data.get('original_key', 'unknown')
                
                # Skip if pattern is provided and doesn't match
                if pattern and pattern not in original_key:
                    continue
                    
                # Check if cache is expired
                is_expired = False
                if self.ttl != Cache.INFINITE_TTL:
                    timestamp = data.get('timestamp')
                    if timestamp:
                        cache_time = datetime.fromisoformat(timestamp)
                        if datetime.now() - cache_time >= timedelta(seconds=self.ttl):
                            is_expired = True
                
                results.append({
                    'key': original_key,
                    'hash': cache_file.stem,
                    'timestamp': data.get('timestamp', 'unknown'),
                    'is_expired': is_expired
                })
                
            except Exception as e:
                # Skip files that can't be read
                continue
                
        return results
    
    def clear_expired(self) -> int:
        """
        Clear all expired cache items
        
        Returns:
            Number of items cleared
        """
        cleared = 0
        
        # Skip if TTL is infinite
        if self.ttl == Cache.INFINITE_TTL:
            return 0
            
        # Iterate through all files in the cache directory
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                # Check if cache is expired
                timestamp = data.get('timestamp')
                if timestamp:
                    cache_time = datetime.fromisoformat(timestamp)
                    if datetime.now() - cache_time >= timedelta(seconds=self.ttl):
                        # Remove expired file
                        cache_file.unlink()
                        cleared += 1
                        
            except Exception as e:
                # Skip files that can't be read
                continue
                
        return cleared

    def get_cache_type(self, file_path: Path) -> str:
        """
        Determine the type of API a cache file is associated with.
        
        Args:
            file_path: Path to the cache file
            
        Returns:
            String indicating the API type: 'enrichr', 'ols', 'opentargets', 
            'gpt4', 'go', 'quickgo', 'disease', or 'other'
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Check if we have the original key
            if 'original_key' in data:
                key = data['original_key'].lower()
                if 'enrichr' in key:
                    return 'enrichr'
                elif 'ols_api' in key or 'ebi.ac.uk/ols' in key:
                    return 'ols'
                elif 'opentargets' in key or 'platform.opentargets.org' in key:
                    return 'opentargets'
                elif 'pathway_analysis' in key or 'gpt-4' in key or 'gpt4' in key:
                    return 'gpt4'
                elif 'go_pathway' in key or 'geneontology.org' in key:
                    return 'go'
                elif 'quickgo' in key or 'ebi.ac.uk/quickgo' in key:
                    return 'go'
                
            # If no original key or no match, try to infer from the value
            value = data.get('value', {})
            value_str = str(value).lower()
            
            # Check if it's an Enrichr response
            if isinstance(value, dict) and ('go_biological_process' in value_str or 
                                           'kegg' in value_str or 
                                           'enrichr' in value_str):
                return 'enrichr'
                
            # Check if it's an OpenTargets response
            if isinstance(value, dict) and ('target' in value_str or 'disease' in value_str) and 'opentargets' in value_str:
                return 'opentargets'
                
            # Check if it's an OLS response
            if isinstance(value, dict) and ('ontology' in value_str or 'efo' in value_str):
                return 'ols'
                
            # Check if it's a Gene Ontology or QuickGO response
            if isinstance(value, dict) and ('go:' in value_str.lower() or 'gene_ontology' in value_str.lower() or 
                                           'quickgo' in value_str.lower() or 'geneontology' in value_str.lower()):
                return 'go'
                
            # Check if it's a GPT-4 response for pathway analysis
            if isinstance(value, list) and any('hallmark' in str(item).lower() for item in value):
                return 'gpt4'
            
            # Additional check for GPT-4 pathway analysis
            if file_path.stem.lower().startswith('pathway_analysis_'):
                return 'gpt4'
            
            return 'other'
            
        except Exception as e:
            return 'error'
    
    def is_related_to_disease(self, file_path: Path, disease_name: str) -> bool:
        """
        Determine if a cache file is related to a specific disease.
        
        Args:
            file_path: Path to the cache file
            disease_name: Name of the disease to check for
            
        Returns:
            True if the cache file is related to the disease, False otherwise
        """
        disease_lower = disease_name.lower()
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Check if we have the original key
            if 'original_key' in data and disease_lower in data['original_key'].lower():
                return True
                    
            # If no original key, try to infer from the value
            value = data.get('value', {})
            value_str = str(value).lower()
            
            # Check if the disease name appears in the value
            if disease_lower in value_str:
                return True
                
            return False
            
        except Exception as e:
            return False
    
    def list_cache_by_type(self, cache_type: str = None) -> list[dict]:
        """
        List all cache items of a specific type.
        
        Args:
            cache_type: Type of cache to list ('enrichr', 'ols', 'opentargets', 'gpt4', 'go', 'quickgo', 'other')
                        If None, list all cache items
            
        Returns:
            List of dicts with path, type, size, timestamp, and is_expired information
        """
        results = []
        
        # Iterate through all files in the cache directory
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                # If a specific type is requested, check if this file matches
                if cache_type is not None:
                    file_type = self.get_cache_type(cache_file)
                    if file_type != cache_type:
                        continue
                
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                # Check if cache is expired
                is_expired = False
                timestamp = data.get('timestamp', 'unknown')
                
                if self.ttl != Cache.INFINITE_TTL and timestamp != 'unknown':
                    cache_time = datetime.fromisoformat(timestamp)
                    if datetime.now() - cache_time >= timedelta(seconds=self.ttl):
                        is_expired = True
                
                # Get file size
                size_bytes = cache_file.stat().st_size
                
                results.append({
                    'path': cache_file,
                    'type': self.get_cache_type(cache_file),
                    'size': size_bytes,
                    'timestamp': timestamp,
                    'is_expired': is_expired,
                    'original_key': data.get('original_key', 'unknown')
                })
                
            except Exception as e:
                # Skip files that can't be read
                continue
                
        return results
    
    def list_disease_cache(self, disease_name: str) -> list[dict]:
        """
        List all cache items related to a specific disease.
        
        Args:
            disease_name: Name of the disease to find cache entries for
            
        Returns:
            List of dicts with path, type, size, timestamp, and is_expired information
        """
        results = []
        
        # Iterate through all files in the cache directory
        for cache_file in self.cache_dir.glob("*.json"):
            if self.is_related_to_disease(cache_file, disease_name):
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                    
                    # Check if cache is expired
                    is_expired = False
                    timestamp = data.get('timestamp', 'unknown')
                    
                    if self.ttl != Cache.INFINITE_TTL and timestamp != 'unknown':
                        cache_time = datetime.fromisoformat(timestamp)
                        if datetime.now() - cache_time >= timedelta(seconds=self.ttl):
                            is_expired = True
                    
                    # Get file size
                    size_bytes = cache_file.stat().st_size
                    
                    results.append({
                        'path': cache_file,
                        'type': self.get_cache_type(cache_file),
                        'size': size_bytes,
                        'timestamp': timestamp,
                        'is_expired': is_expired,
                        'original_key': data.get('original_key', 'unknown')
                    })
                    
                except Exception as e:
                    # Skip files that can't be read
                    continue
                    
        return results
    
    def clear_cache_by_type(self, cache_type: str) -> int:
        """
        Clear all cache items of a specific type.
        
        Args:
            cache_type: Type of cache to clear ('enrichr', 'ols', 'opentargets', 'gpt4', 'go', 'quickgo', 'other')
            
        Returns:
            Number of items cleared
        """
        cleared = 0
        
        # Get all cache files of the specified type
        cache_items = self.list_cache_by_type(cache_type)
        
        # Delete each file
        for item in cache_items:
            try:
                item['path'].unlink()
                cleared += 1
            except Exception as e:
                # Skip files that can't be deleted
                continue
                
        return cleared
    
    def clear_disease_cache(self, disease_name: str) -> int:
        """
        Clear all cache items related to a specific disease.
        
        Args:
            disease_name: Name of the disease to clear cache for
            
        Returns:
            Number of items cleared
        """
        cleared = 0
        
        # Get all cache files related to the disease
        cache_items = self.list_disease_cache(disease_name)
        
        # Delete each file
        for item in cache_items:
            try:
                item['path'].unlink()
                cleared += 1
            except Exception as e:
                # Skip files that can't be deleted
                continue
                
        return cleared
