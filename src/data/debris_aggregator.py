"""
Aggregates space debris data from multiple sources.
"""

import logging
from typing import List, Dict
from .space_track_client import SpaceTrackClient
from .esa_client import ESAClient

logger = logging.getLogger(__name__)

class DebrisAggregator:
    """Aggregates and merges space debris data from multiple sources."""
    
    def __init__(self, cache_dir: str = ".cache"):
        """Initialize data sources."""
        self.space_track = SpaceTrackClient(cache_dir)
        self.esa = ESAClient(cache_dir)
    
    async def get_aggregated_data(self, days_ago: int = 7, use_cache: bool = True) -> List[Dict]:
        """
        Fetch and aggregate debris data from all sources.
        
        Args:
            days_ago: Number of days in the past to fetch data for
            use_cache: Whether to use cached data if available
            
        Returns:
            Combined list of debris objects
        """
        try:
            # Fetch data from Space-Track
            all_data = await self.space_track.fetch_debris_data(days_ago, use_cache)
        
            logger.info(f"Using Space-Track data with {len(all_data)} objects")
            return all_data
            
        except Exception as e:
            logger.error(f"Error aggregating debris data: {str(e)}")
            # If one source fails, return data from the other source
            if space_track_data:
                return space_track_data
            if esa_data:
                return esa_data
            raise
    
    def _merge_debris_data(self, space_track_data: List[Dict], esa_data: List[Dict]) -> List[Dict]:
        """
        Merge debris data from different sources, avoiding duplicates.
        
        Args:
            space_track_data: Data from Space-Track.org
            esa_data: Data from ESA DISCOS
            
        Returns:
            Merged list of debris objects
        """
        # Use a dictionary to track objects by their NORAD ID
        merged_dict = {}
        
        # Process Space-Track data first (considered primary source)
        for item in space_track_data:
            norad_id = item.get('id')
            if norad_id:
                merged_dict[norad_id] = item
        
        # Add ESA data, updating existing entries with additional information
        for item in esa_data:
            norad_id = item.get('id').replace('esa_', '')  # Remove ESA prefix
            
            if norad_id in merged_dict:
                # Update existing entry with additional ESA data
                existing = merged_dict[norad_id]
                existing['metadata'].update({
                    'esa_' + k: v 
                    for k, v in item['metadata'].items() 
                    if k not in existing['metadata']
                })
                
                # Update risk level if ESA's is higher
                if item['risk_level'] > existing['risk_level']:
                    existing['risk_level'] = item['risk_level']
                    existing['metadata']['risk_source'] = 'ESA'
            else:
                # Add new ESA entry
                merged_dict[norad_id] = item
        
        return list(merged_dict.values())
