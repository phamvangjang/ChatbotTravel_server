import os
import requests
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class MapboxService:
    def __init__(self):
        logger.info("Initializing Mapbox service...")
        self.access_token = os.getenv('MAPBOX_ACCESS_TOKEN')
        if not self.access_token:
            logger.error("MAPBOX_ACCESS_TOKEN environment variable is not set")
            raise ValueError("MAPBOX_ACCESS_TOKEN environment variable is not set")
            
        self.base_url = "https://api.mapbox.com"
        logger.info("Mapbox service initialized successfully")
        
    def search_places(self, query: str) -> Optional[Tuple[float, float]]:
        """Search for places using Mapbox Geocoding API"""
        try:
            logger.info(f"Searching for place: {query}")
            print(f"Searching for place: {query}")

            # Thêm từ khóa "Ho Chi Minh City" để tăng độ chính xác
            _query = f"{query}, Ho Chi Minh City"
            
            # Construct URL
            url = f"{self.base_url}/geocoding/v5/mapbox.places/{_query}.json"
            params = {
                'access_token': self.access_token,
                'country': 'vn',
                'types': 'poi,place,address',
                'limit': 1,
                'language': 'vi',
                'proximity': '106.660172,10.762622'  # Center of HCMC
            }
            
            # Send request
            logger.debug(f"Sending request to: {url}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            logger.debug(f"Received response: {data}")
            
            if not data['features']:
                logger.warning(f"No results found for: {query}")
                return None
                
            # Extract coordinates (longitude, latitude)
            coordinates = data['features'][0]['center']
            logger.info(f"Found coordinates: {coordinates}")
            
            # Return as tuple (latitude, longitude)
            return (coordinates[1], coordinates[0])
            
        except Exception as e:
            logger.error(f"Error searching places: {str(e)}", exc_info=True)
            return None

    def generate_map_link(self, locations: List[Dict]) -> str:
        """Generate a map link for the given locations"""
        try:
            logger.info("Generating map link...")
            
            # Base URL for Mapbox Static Images API
            base_url = "https://api.mapbox.com/styles/v1/mapbox/streets-v11/static"
            
            # Add markers to the URL
            marker_strings = []
            for location in locations:
                # Search for location coordinates
                coords = self.search_places(location)
                if coords:
                    marker_strings.append(f"pin-s+ff0000({coords[1]},{coords[0]})")
            
            if not marker_strings:
                logger.warning("No valid coordinates found for locations")
                return ""
            
            # Construct the final URL
            markers_str = ",".join(marker_strings)
            url = f"{base_url}/{markers_str}/106.660172,10.762622,13/600x400?access_token={self.access_token}"
            
            logger.info("Map link generated successfully")
            return url
            
        except Exception as e:
            logger.error(f"Error generating map link: {str(e)}")
            return ""

# Initialize Mapbox service
try:
    logger.info("Creating Mapbox service instance...")
    mapbox_service = MapboxService()
    logger.info("Mapbox service instance created successfully")
except Exception as e:
    logger.error(f"Failed to initialize Mapbox service: {str(e)}", exc_info=True)
    mapbox_service = None 