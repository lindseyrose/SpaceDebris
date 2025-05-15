"""
Space-Track.org API client for fetching space debris data.
Documentation: https://www.space-track.org/documentation
"""

import os
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from .cache_manager import CacheManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpaceTrackClient:
    """Client for interacting with Space-Track.org API."""
    
    BASE_URL = "https://www.space-track.org"
    LOGIN_URL = f"{BASE_URL}/ajaxauth/login"
    
    def __init__(self, cache_dir: str = ".cache"):
        """Initialize the Space-Track client."""
        load_dotenv()
        self.email = 'lindseyroseweisman@gmail.com'
        self.password = 'JSNH9.f22_m*UZ3'
        self.session = None
        self.cache_manager = CacheManager(cache_dir)
        
        if not self.email or not self.password:
            raise ValueError("Space-Track credentials not found in .env file")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.logout()
    
    async def login(self):
        """Login to Space-Track.org."""
        if self.session:
            return
            
        self.session = aiohttp.ClientSession()
        credentials = {
            'identity': self.email,
            'password': self.password
        }
        
        try:
            async with self.session.post(self.LOGIN_URL, data=credentials) as response:
                if response.status != 200:
                    raise Exception(f"Login failed with status {response.status}")
                logger.info("Successfully logged in to Space-Track.org")
        except Exception as e:
            logger.error(f"Failed to login to Space-Track.org: {str(e)}")
            raise
    
    async def logout(self):
        """Logout from Space-Track.org."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Logged out from Space-Track.org")
    
    async def fetch_space_objects(self, object_type: str = None, days_ago: int = 7, use_cache: bool = True) -> List[Dict]:
        """
        Fetch recent space objects data (debris or satellites).
        
        Args:
            object_type: Type of objects to fetch ('DEBRIS' or 'PAYLOAD' or None for both)
            days_ago: Number of days in the past to fetch data for
            use_cache: Whether to use cached data
            
        Returns:
            List of space objects with their parameters
        """
        if not self.session:
            await self.login()
        
        # Try to get data from cache first
        cache_key = f"{object_type or 'all'}_{days_ago}"
        if use_cache:
            cached_data = await self.cache_manager.get_cached_data(cache_key)
            if cached_data:
                logger.info(f"Using cached data with {len(cached_data)} objects")
                return cached_data
        
        # Build query URL
        endpoint = f"{self.BASE_URL}/basicspacedata/query/class/gp"
        
        if object_type:
            endpoint += f"/object_type/{object_type}"
            
        endpoint += f"/decay_date/null-val/orderby/norad_cat_id" \
                   f"/metadata/false" \
                   f"/predicates/NORAD_CAT_ID,OBJECT_NAME,OBJECT_TYPE,CLASSIFICATION_TYPE," \
                   f"LAUNCH_DATE,INCLINATION,MEAN_MOTION,ECCENTRICITY,RCS_SIZE,TLE_LINE1,TLE_LINE2" \
                   f"/format/json"
        
        try:
            async with self.session.get(endpoint) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch data: {response.status}")
                
                data = await response.json()
                logger.info(f"Successfully fetched {len(data)} debris objects")
                processed_data = self._process_debris_data(data)
                
                # Update cache with new data
                if use_cache:
                    await self.cache_manager.update_cache(processed_data)
                
                return processed_data
        except Exception as e:
            logger.error(f"Error fetching debris data: {str(e)}")
            raise
    
    def _process_space_objects(self, raw_data: List[Dict], object_type: str = None) -> List[Dict]:
        """
        Process raw space objects data into the format needed for visualization.
        
        Args:
            raw_data: Raw data from Space-Track API
            object_type: Type of objects being processed ('DEBRIS' or 'PAYLOAD' or None)
            
        Returns:
            Processed data in visualization-friendly format
        """
        from sgp4.earth_gravity import wgs84
        from sgp4.io import twoline2rv
        from datetime import datetime, timezone
        import numpy as np
        
        processed_data = []
        current_time = datetime.now(timezone.utc)
        
        for item in raw_data:
            try:
                # Extract TLE data
                norad_id = item.get('NORAD_CAT_ID')
                tle_line1 = item.get('TLE_LINE1')
                tle_line2 = item.get('TLE_LINE2')
                item_type = item.get('OBJECT_TYPE', object_type or 'UNKNOWN')
                
                if not all([norad_id, tle_line1, tle_line2]):
                    continue
                
                # Create satellite object from TLE
                satellite = twoline2rv(tle_line1, tle_line2, wgs84)
                
                # Calculate trajectory points (24 points over one orbit)
                trajectory_points = []
                period_minutes = 1440 / float(item.get('MEAN_MOTION', 1))
                time_step = period_minutes * 60 / 24  # seconds between points
                
                for i in range(24):
                    future_time = current_time + timedelta(seconds=i * time_step)
                    pos, vel = satellite.propagate(
                        future_time.year,
                        future_time.month,
                        future_time.day,
                        future_time.hour,
                        future_time.minute,
                        future_time.second
                    )
                    # Scale position
                    scale = 10/6371
                    trajectory_points.append({
                        'x': float(pos[0] * scale),
                        'y': float(pos[1] * scale),
                        'z': float(pos[2] * scale)
                    })
                
                # Get current position
                position, velocity = satellite.propagate(
                    current_time.year,
                    current_time.month,
                    current_time.day,
                    current_time.hour,
                    current_time.minute,
                    current_time.second
                )
                
                # Scale position for visualization
                scale = 10/6371
                position = [p * scale for p in position]
                
                # Calculate risk level
                inclination = float(item.get('INCLINATION', 0))
                mean_motion = float(item.get('MEAN_MOTION', 0))
                eccentricity = float(item.get('ECCENTRICITY', 0))
                
                risk_factors = [
                    inclination / 90,
                    mean_motion / 20,
                    eccentricity * 100
                ]
                risk_level = min(100, np.mean(risk_factors) * 100)
                
                processed_item = {
                    'id': norad_id,
                    'type': 'satellite' if item_type == 'PAYLOAD' else 'debris',
                    'position': {
                        'x': float(position[0]),
                        'y': float(position[1]),
                        'z': float(position[2])
                    },
                    'trajectory': trajectory_points,
                    'size': self._get_size_from_rcs(item.get('RCS_SIZE', 'SMALL')),
                    'risk_level': risk_level,
                    'metadata': {
                        'name': item.get('OBJECT_NAME'),
                        'launch_date': item.get('LAUNCH_DATE'),
                        'inclination': inclination,
                        'eccentricity': eccentricity,
                        'mean_motion': mean_motion,
                        'period_minutes': period_minutes
                    }
                }
                processed_data.append(processed_item)
            except Exception as e:
                logger.warning(f"Error processing space object {item.get('NORAD_CAT_ID')}: {str(e)}")
                continue
        
        return processed_data

    def _get_size_from_rcs(self, rcs_value: str) -> float:
        """Convert RCS text value to numeric size."""
        rcs_sizes = {
            'SMALL': 0.5,    # < 0.1 square meters
            'MEDIUM': 1.0,   # 0.1-1 square meters
            'LARGE': 2.0,    # > 1 square meter
        }
        return rcs_sizes.get(str(rcs_value).upper(), 0.5)

async def main():
    """Test the SpaceTrackClient."""
    async with SpaceTrackClient() as client:
        data = await client.fetch_debris_data(days_ago=1)
        print(f"Fetched {len(data)} debris objects")
        if data:
            print("Sample object:", data[0])

if __name__ == "__main__":
    asyncio.run(main())
