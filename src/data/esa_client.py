"""
ESA DISCOS API client for fetching additional space debris data.
Documentation: https://discosweb.esoc.esa.int/api
"""

import os
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)

class ESAClient:
    """Client for interacting with ESA's DISCOS API."""
    
    BASE_URL = "https://discosweb.esoc.esa.int"
    
    def __init__(self, cache_dir: str = ".cache"):
        """Initialize the ESA DISCOS client."""
        load_dotenv()
        self.api_key = "ImVlN2Y4Zjc4LTA4ZjgtNDkwOS04ZDgzLTMxMjgwNGYxZmJjZCI.aCucAmHbDmu6yvmJQWrvxzqrZ0g".strip()
        self.session = None
        self.cache_manager = CacheManager(os.path.join(cache_dir, "esa"))
        
        if not self.api_key:
            logger.warning("ESA API key not found in .env file. ESA data will not be available.")
            self.enabled = False
        else:
            self.enabled = True
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self):
        """Initialize HTTP session."""
        if self.session:
            return
            
        self.session = aiohttp.ClientSession(headers={
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/vnd.api+json',
            'DiscosWeb-Api-Version': '2'
        })
        logger.info("ESA DISCOS session initialized")
    
    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("ESA DISCOS session closed")
    
    async def fetch_debris_data(self, days_ago: int = 7, use_cache: bool = False) -> List[Dict]:
        if not self.enabled:
            logger.info("ESA client is disabled due to missing API key")
            return []
        """
        Fetch recent space debris data from ESA DISCOS.
        
        Args:
            days_ago: Number of days in the past to fetch data for
            use_cache: Whether to use cached data if available
            
        Returns:
            List of debris objects with their parameters
        """
        if use_cache:
            cached_data = await self.cache_manager.get_cached_data()
            if cached_data:
                logger.info(f"Using cached ESA data with {len(cached_data)} objects")
                return cached_data
        
        if not self.session:
            await self.connect()
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_ago)
        
        try:
            # Query parameters for debris objects
            # Calculate date range for the filter
            end_date_str = end_date.strftime('%Y-%m-%d')
            start_date_str = start_date.strftime('%Y-%m-%d')
            
            params = {
                'page[size]': '100',
                'page[number]': '1',
                'filter': 'objectClass:"Debris"',  # Filter for debris objects
                'fields[object]': 'cosparId,name,type',  # Basic fields
                'include': 'orbits',  # Include orbital data
                'fields[orbits]': 'epoch,semiMajorAxis,eccentricity,inclination'  # Orbital parameters
            }
            
            logger.info(f"Making request to {self.BASE_URL}/api/objects with params: {params}")
            # Try the catalog endpoint
            async with self.session.get(f'{self.BASE_URL}/api/catalog', params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"ESA API error: {response.status}, {error_text}")
                    raise Exception(f"Failed to fetch data: {response.status}, {error_text}")
                
                response_data = await response.json()
                if not response.ok:
                    logger.error(f"ESA API error response: {response_data.get('errors', [])}")
                    raise Exception(f"Failed to fetch data: {response.status}, {response_data.get('errors', [])}")
                
                # Get main data and included relationships
                debris_data = response_data.get('data', [])
                included = {item['type'] + '_' + item['id']: item 
                           for item in response_data.get('included', [])}
                
                logger.info(f"Successfully fetched {len(debris_data)} ESA debris objects")
                logger.info(f"Found {len(included)} included relationships")
                
                processed_data = self._process_debris_data(debris_data, included)
                
                if use_cache:
                    await self.cache_manager.update_cache(processed_data)
                
                return processed_data
                
        except Exception as e:
            logger.error(f"Error fetching ESA debris data: {str(e)}")
            raise
    
    def _process_debris_data(self, raw_data: List[Dict], included: Dict[str, Dict]) -> List[Dict]:
        """
        Process raw ESA debris data into visualization format.
        
        Args:
            raw_data: Raw data from ESA DISCOS API
            included: Dictionary of included relationships
            
        Returns:
            Processed data in visualization-friendly format
        """
        processed_data = []
        
        for item in raw_data:
            try:
                attributes = item.get('attributes', {})
                relationships = item.get('relationships', {})
                
                # Get related data
                elements_rel = relationships.get('elements', {}).get('data', {})
                elements_key = f"elements_{elements_rel.get('id', '')}" if elements_rel else None
                elements = included.get(elements_key, {}).get('attributes', {}) if elements_key else {}
                
                launch_rel = relationships.get('launch', {}).get('data', {})
                launch_key = f"launch_{launch_rel.get('id', '')}" if launch_rel else None
                launch = included.get(launch_key, {}).get('attributes', {}) if launch_key else {}
                
                decay_rel = relationships.get('decay', {}).get('data', {})
                decay_key = f"decay_{decay_rel.get('id', '')}" if decay_rel else None
                decay = included.get(decay_key, {}).get('attributes', {}) if decay_key else {}
                
                # Extract orbital parameters
                semi_major_axis = float(elements.get('semiMajorAxis', 0))
                eccentricity = float(elements.get('eccentricity', 0))
                inclination = float(elements.get('inclination', 0))
                
                # Basic position calculation (placeholder)
                position = {
                    'x': semi_major_axis * (1 - eccentricity) * 0.02,  # Scale for visualization
                    'y': semi_major_axis * inclination / 90 * 0.02,
                    'z': semi_major_axis * eccentricity * 0.02
                }
                
                # Calculate risk level based on various factors
                mass = float(attributes.get('mass', 0))
                perigee = float(elements.get('perigeeAltitude', 0))
                velocity = float(elements.get('velocity', 0))
                
                risk_factors = [
                    (mass / 1000) * 30,  # Heavier objects are riskier
                    (1 - perigee / 1000) * 40,  # Lower orbit = higher risk
                    (velocity / 10) * 30  # Higher velocity = higher risk
                ]
                risk_level = min(100, sum(risk_factors) / len(risk_factors))
                
                processed_item = {
                    'id': f"esa_{item.get('id', '')}",  # Prefix to avoid conflicts
                    'type': 'debris',
                    'source': 'esa',  # Mark the data source
                    'position': position,
                    'size': float(attributes.get('crossSection', 1.0)),  # Cross-sectional area
                    'risk_level': risk_level,
                    'metadata': {
                        'name': attributes.get('name'),
                        'launch_date': launch.get('epoch'),
                        'decay_date': decay.get('epoch'),
                        'mass': mass,
                        'perigee': perigee,
                        'apogee': elements.get('apogeeAltitude'),
                        'semi_major_axis': semi_major_axis,
                        'eccentricity': eccentricity,
                        'inclination': inclination,
                        'source': 'ESA DISCOS'
                    }
                }
                processed_data.append(processed_item)
                
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing ESA debris item: {str(e)}")
                continue
        
        return processed_data
