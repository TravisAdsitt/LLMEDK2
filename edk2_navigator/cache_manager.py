"""
Cache Manager - Handles caching of parsed DSC data and dependency graphs
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class CacheManager:
    """Manages caching of parsed DSC data"""
    
    def __init__(self, cache_dir: str = "~/.edk2_navigator/cache"):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache configuration
        self.cache_ttl = timedelta(hours=24)  # 24 hour TTL
        self.max_cache_size = 1024 * 1024 * 1024  # 1GB max cache size
    
    def _get_cache_key(self, dsc_path: str, build_flags: Dict[str, str]) -> str:
        """Generate cache key for DSC file and build flags"""
        # Create hash from DSC path and build flags
        content = f"{dsc_path}:{json.dumps(build_flags, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for cache key"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file contents for change detection"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def is_cache_valid(self, dsc_path: str, build_flags: Dict[str, str]) -> bool:
        """Check if cached data is still valid"""
        cache_key = self._get_cache_key(dsc_path, build_flags)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return False
        
        try:
            # Load cache metadata
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            # Check TTL
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_time > self.cache_ttl:
                return False
            
            # Check file hash for changes
            current_hash = self._get_file_hash(dsc_path)
            if current_hash != cache_data['file_hash']:
                return False
            
            return True
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return False
    
    def store_parsed_data(self, dsc_path: str, build_flags: Dict[str, str], data: Any):
        """Store parsed DSC data in cache"""
        cache_key = self._get_cache_key(dsc_path, build_flags)
        cache_path = self._get_cache_path(cache_key)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'dsc_path': dsc_path,
            'build_flags': build_flags,
            'file_hash': self._get_file_hash(dsc_path),
            'data': data
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def load_cached_data(self, dsc_path: str, build_flags: Dict[str, str]) -> Optional[Any]:
        """Load cached DSC data"""
        if not self.is_cache_valid(dsc_path, build_flags):
            return None
        
        cache_key = self._get_cache_key(dsc_path, build_flags)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            return cache_data['data']
        except (json.JSONDecodeError, KeyError):
            return None
    
    def clear_cache(self):
        """Clear all cached data"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'cache_dir': str(self.cache_dir),
            'file_count': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'max_size_mb': self.max_cache_size / (1024 * 1024)
        }
