import os
import json
import hashlib
import re
import collections
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, List, Union, Generator, Tuple
import requests

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
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl

    def _iter_cache_data(self) -> Generator[Tuple[Path, dict], None, None]:
        """Generator that yields cache file paths and their loaded JSON data."""
        for file_path in self.cache_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                yield file_path, data
            except (json.JSONDecodeError, OSError):
                # In case of corrupted file, remove it and continue
                try:
                    file_path.unlink()
                except OSError:
                    pass
                continue

    def _get_cache_path(self, key: str) -> Path:
        """Get path for cache file"""
        # Create hash of key for filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            # Corrupted file, treat as a cache miss and delete it
            try:
                cache_path.unlink()
            except OSError:
                pass # Ignore if deletion fails
            return None

        # Check if cache is expired
        if self.ttl != self.INFINITE_TTL:
            timestamp = data.get("timestamp")
            if not timestamp:
                # No timestamp, treat as expired
                cache_path.unlink()
                return None
            
            try:
                if datetime.now() - datetime.fromisoformat(timestamp) >= timedelta(seconds=self.ttl):
                    self.delete(key) # Use self.delete to handle file removal
                    return None
            except ValueError:
                # Invalid timestamp format
                cache_path.unlink()
                return None

        return data.get("value")

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

    def delete(self, key: str):
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()

    def clear(self):
        for item in self.cache_dir.iterdir():
            if item.is_file():
                item.unlink()

    def analyze_cache(self) -> dict:
        api_types = collections.defaultdict(list)
        cached_diseases = set()
        timestamps = []
        total_size_bytes = 0
        total_files = 0

        for file_path, data in self._iter_cache_data():
            total_files += 1
            total_size_bytes += file_path.stat().st_size
            if data.get("timestamp"):
                timestamps.append(data["timestamp"])

            file_type = self._get_cache_type_from_data(file_path, data)
            api_types[file_type].append(file_path)

            if file_type == 'ols':
                value = data.get("value", {})
                if isinstance(value, dict) and "response" in value:
                    docs = value.get("response", {}).get("docs", [])
                    for doc in docs:
                        if "label" in doc and doc.get("ontology_name") == "efo":
                            cached_diseases.add(doc.get("label"))
                            break
        
        timestamp_range = {}
        if timestamps:
            timestamps.sort()
            timestamp_range = {"oldest": timestamps[0], "newest": timestamps[-1]}

        return {
            "cache_dir": str(self.cache_dir),
            "total_items": total_files,
            "size_mb": total_size_bytes / (1024 * 1024),
            "api_breakdown": {key: len(value) for key, value in api_types.items()},
            "cached_diseases": list(cached_diseases),
            "timestamp_range": timestamp_range
        }

    def get_key_prefixes(self, top_n: int = 30) -> dict:
        prefixes = collections.Counter()
        files_with_keys = 0
        total_files = 0

        for file_path, data in self._iter_cache_data():
            total_files += 1
            if 'original_key' in data:
                files_with_keys += 1
                key = data['original_key']
                match = re.match(r'^([a-zA-Z:_\\-]+)', key)
                if match:
                    prefix = match.group(1).rstrip('_-:')
                    prefixes[prefix] += 1

        return {
            "total_files_scanned": total_files,
            "files_with_original_key": files_with_keys,
            "top_prefixes": dict(prefixes.most_common(top_n))
        }

    def _is_disease_cached(self, disease_name: str) -> bool:
        for _, data in self._iter_cache_data():
            value = data.get("value", {})
            if isinstance(value, dict) and "response" in value:
                docs = value.get("response", {}).get("docs", [])
                for doc in docs:
                    if doc.get("label", "").lower() == disease_name.lower():
                        return True
        return False

    def clear_disease_cache(self, disease_name: str) -> int:
        cleared_count = 0
        for file_path, data in self._iter_cache_data():
            value = data.get("value", {})
            if isinstance(value, dict) and "response" in value:
                docs = value.get("response", {}).get("docs", [])
                for doc in docs:
                    if doc.get("label", "").lower() == disease_name.lower():
                        file_path.unlink()
                        cleared_count += 1
                        break
        return cleared_count

    def _get_cache_type_from_data(self, file_path: Path, data: dict) -> str:
        if 'original_key' in data:
            key = data['original_key'].lower()
            if key.startswith('ot_disease_targets_'): return 'opentargets'
            if key.startswith('gpt4_') or key.startswith('pathway_analysis_'): return 'gpt4'
            if key.startswith('enrichr_'): return 'enrichr'
            if key.startswith('go_pathway_') or 'geneontology.org' in key: return 'go'
            if key.startswith('quickgo_') or 'ebi.ac.uk/quickgo' in key: return 'go'
            if key.startswith('ols_api_') or 'ebi.ac.uk/ols' in key: return 'ols'
            if 'platform.opentargets.org' in key or 'opentargets' in key: return 'opentargets'

        value = data.get('value', {})
        value_str = str(value).lower()
        
        if isinstance(value, dict):
            if 'go:' in value_str or 'gene_ontology' in value_str or 'geneontology' in value_str: return 'go'
            if 'ontology' in value_str or 'efo' in value_str: return 'ols'
            if 'go_biological_process' in value_str or 'kegg' in value_str or 'enrichr' in value_str: return 'enrichr'
            if ('target' in value_str or 'disease' in value_str) and 'opentargets' in value_str: return 'opentargets'

        if isinstance(value, list) and value:
            if any('hallmark' in str(item).lower() for item in value): return 'gpt4'
            if all(isinstance(item, str) for item in value) and any('_' in item for item in value): return 'gpt4'

        if file_path.stem.lower().startswith('pathway_analysis_'): return 'gpt4'

        return 'other'

    def list_cache_by_type(self, cache_type: str = None) -> list[dict]:
        results = []
        for file_path, data in self._iter_cache_data():
            file_type = self._get_cache_type_from_data(file_path, data)
            if cache_type is not None and file_type != cache_type:
                continue

            is_expired = False
            timestamp = data.get('timestamp', 'unknown')
            if self.ttl != self.INFINITE_TTL and timestamp != 'unknown':
                cache_time = datetime.fromisoformat(timestamp)
                if datetime.now() - cache_time >= timedelta(seconds=self.ttl):
                    is_expired = True
            
            results.append({
                'path': file_path,
                'type': file_type,
                'size': file_path.stat().st_size,
                'timestamp': timestamp,
                'is_expired': is_expired,
                'original_key': data.get('original_key', 'unknown')
            })
        return results

    def clear_cache_by_type(self, cache_type: str) -> int:
        cleared = 0
        for file_path, data in self._iter_cache_data():
            if self._get_cache_type_from_data(file_path, data) == cache_type:
                try:
                    file_path.unlink()
                    cleared += 1
                except OSError:
                    continue
        return cleared

    def clear_expired(self) -> int:
        if self.ttl == self.INFINITE_TTL:
            return 0
        cleared = 0
        for file_path, data in self._iter_cache_data():
            timestamp = data.get('timestamp')
            if timestamp:
                try:
                    cache_time = datetime.fromisoformat(timestamp)
                    if datetime.now() - cache_time >= timedelta(seconds=self.ttl):
                        file_path.unlink()
                        cleared += 1
                except (ValueError, OSError):
                    continue
        return cleared


    
    def _is_related_to_disease(self, data: dict, disease_name: str) -> bool:
        """Check if a cache entry is related to a specific disease."""
        disease_name_lower = disease_name.lower()
        
        # Check original_key
        original_key = data.get('original_key', '').lower()
        if disease_name_lower in original_key:
            return True
            
        # Check for OLS EFO responses, where the disease name might be in the value
        value = data.get('value', {})
        if isinstance(value, dict):
            response = value.get('response', {})
            if isinstance(response, dict):
                docs = response.get('docs', [])
                for doc in docs:
                    if disease_name_lower in doc.get('label', '').lower():
                        return True
        
        return False

    def list_cache_by_type(self, cache_type: str = None) -> list[dict]:
        """List all cache items of a specific type."""
        results = []
        for file_path, data in self._iter_cache_data():
            file_type = self._get_cache_type_from_data(file_path, data)
            if cache_type is not None and file_type != cache_type:
                continue

            is_expired = False
            timestamp = data.get('timestamp', 'unknown')
            if self.ttl != self.INFINITE_TTL and timestamp != 'unknown':
                try:
                    cache_time = datetime.fromisoformat(timestamp)
                    if datetime.now() - cache_time >= timedelta(seconds=self.ttl):
                        is_expired = True
                except ValueError:
                    is_expired = True # Treat invalid timestamps as expired
            
            results.append({
                'path': file_path,
                'type': file_type,
                'size': file_path.stat().st_size,
                'timestamp': timestamp,
                'is_expired': is_expired,
                'original_key': data.get('original_key', 'unknown')
            })
        return results

    def list_disease_cache(self, disease_name: str) -> list[dict]:
        """List all cache items related to a specific disease."""
        results = []
        for file_path, data in self._iter_cache_data():
            if self._is_related_to_disease(data, disease_name):
                is_expired = False
                timestamp = data.get('timestamp', 'unknown')
                if self.ttl != self.INFINITE_TTL and timestamp != 'unknown':
                    try:
                        cache_time = datetime.fromisoformat(timestamp)
                        if datetime.now() - cache_time >= timedelta(seconds=self.ttl):
                            is_expired = True
                    except ValueError:
                        is_expired = True
                
                results.append({
                    'path': file_path,
                    'type': self._get_cache_type_from_data(file_path, data),
                    'size': file_path.stat().st_size,
                    'timestamp': timestamp,
                    'is_expired': is_expired,
                    'original_key': data.get('original_key', 'unknown')
                })
        return results

    def clear_disease_cache(self, disease_name: str) -> int:
        """Clear all cache items related to a specific disease."""
        cleared = 0
        for file_path, data in self._iter_cache_data():
            if self._is_related_to_disease(data, disease_name):
                try:
                    file_path.unlink()
                    cleared += 1
                except OSError:
                    continue
        return cleared
