"""
Cache manager for space debris data.
Implements local caching with periodic updates to reduce API calls.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages caching of space debris data."""
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.debris_cache_file = self.cache_dir / "debris_data.json"
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.cache_lock = asyncio.Lock()
        self.update_interval = timedelta(minutes=30)  # Update every 30 minutes
    
    async def get_cached_data(self) -> Optional[List[Dict]]:
        """
        Get cached debris data if it exists and is not expired.
        
        Returns:
            Cached debris data or None if cache is invalid
        """
        async with self.cache_lock:
            if not self._is_cache_valid():
                return None
            
            try:
                with open(self.debris_cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Error reading cache: {str(e)}")
                return None
    
    async def update_cache(self, data: List[Dict]):
        """
        Update the cache with new data.
        
        Args:
            data: New debris data to cache
        """
        async with self.cache_lock:
            try:
                # Save debris data
                with open(self.debris_cache_file, 'w') as f:
                    json.dump(data, f)
                
                # Update metadata
                metadata = {
                    'last_update': datetime.utcnow().isoformat(),
                    'num_objects': len(data)
                }
                with open(self.metadata_file, 'w') as f:
                    json.dump(metadata, f)
                
                logger.info(f"Cache updated with {len(data)} objects")
            except Exception as e:
                logger.error(f"Error updating cache: {str(e)}")
    
    def _is_cache_valid(self) -> bool:
        """
        Check if the cache is valid and not expired.
        
        Returns:
            True if cache is valid, False otherwise
        """
        try:
            if not (self.debris_cache_file.exists() and self.metadata_file.exists()):
                return False
            
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            
            last_update = datetime.fromisoformat(metadata['last_update'])
            return datetime.utcnow() - last_update < self.update_interval
            
        except Exception as e:
            logger.warning(f"Error checking cache validity: {str(e)}")
            return False
    
    async def clear_cache(self):
        """Clear all cached data."""
        async with self.cache_lock:
            try:
                if self.debris_cache_file.exists():
                    self.debris_cache_file.unlink()
                if self.metadata_file.exists():
                    self.metadata_file.unlink()
                logger.info("Cache cleared")
            except Exception as e:
                logger.error(f"Error clearing cache: {str(e)}")
    
    def get_cache_info(self) -> Dict:
        """
        Get information about the current cache state.
        
        Returns:
            Dictionary with cache information
        """
        try:
            if not self.metadata_file.exists():
                return {
                    'status': 'no_cache',
                    'last_update': None,
                    'num_objects': 0
                }
            
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            
            last_update = datetime.fromisoformat(metadata['last_update'])
            is_valid = datetime.utcnow() - last_update < self.update_interval
            
            return {
                'status': 'valid' if is_valid else 'expired',
                'last_update': metadata['last_update'],
                'num_objects': metadata['num_objects']
            }
        except Exception as e:
            logger.error(f"Error getting cache info: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
