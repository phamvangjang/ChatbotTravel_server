import os
import requests
from typing import List, Dict, Tuple, Optional
import logging
from urllib.parse import quote

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
        
    def get_directions(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        waypoints: List[Tuple[float, float]] = None
    ) -> Dict:
        """Get directions between points"""
        try:
            logger.info("Getting directions...")
            logger.debug(f"Start: {start}, End: {end}, Waypoints: {waypoints}")
            
            coordinates = f"{start[1]},{start[0]}"  # lon,lat format
            
            if waypoints:
                for point in waypoints:
                    coordinates += f";{point[1]},{point[0]}"
                    
            coordinates += f";{end[1]},{end[0]}"
            
            url = f"{self.base_url}/directions/v5/mapbox/driving/{coordinates}"
            params = {
                'access_token': self.access_token,
                'geometries': 'geojson',
                'steps': 'true',
                'language': 'vi'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info("Directions retrieved successfully")
            return data
            
        except Exception as e:
            logger.error(f"Error getting directions: {str(e)}", exc_info=True)
            return {}
        
    def get_static_map(
        self,
        center: Tuple[float, float],
        markers: List[Dict],
        width: int = 600,
        height: int = 400,
        zoom: int = 13
    ) -> str:
        """Generate static map URL with markers"""
        try:
            logger.info("Generating static map URL...")
            logger.debug(f"Center: {center}, Markers: {markers}")
            
            # Construct URL
            url = f"{self.base_url}/styles/v1/mapbox/streets-v11/static"
            
            # Add markers
            marker_str = ""
            for marker in markers:
                marker_str += f"pin-s+{marker['color']}({marker['longitude']},{marker['latitude']}),"
            marker_str = marker_str.rstrip(',')
            
            # Add center and zoom
            url += f"/{marker_str}/{center[1]},{center[0]},{zoom}"
            
            # Add size
            url += f"/{width}x{height}"
            
            # Add access token
            url += f"?access_token={self.access_token}"
            
            logger.info("Static map URL generated successfully")
            return url
            
        except Exception as e:
            logger.error(f"Error generating static map: {str(e)}", exc_info=True)
            return ""
        
    def search_places(self, location):
        """Search for a place using Mapbox Geocoding API"""
        try:
            # Clean and format the location string
            location = location.strip()
            if not location:
                return None
                
            # Encode the location for URL
            encoded_location = quote(location)
            
            # Make request to Mapbox Geocoding API
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded_location}.json"
            params = {
                'access_token': self.access_token,
                'country': 'vn',  # Limit to Vietnam
                'types': 'place,address,poi',  # Limit to places, addresses and points of interest
                'limit': 1  # Get only the best match
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data['features']:
                # Return coordinates [latitude, longitude]
                return data['features'][0]['center']
            return None
            
        except Exception as e:
            logger.error(f"Error searching for place: {str(e)}")
            return None
        
    def optimize_route(
        self,
        points: List[Tuple[float, float]],
        start_point: Tuple[float, float] = None
    ) -> List[int]:
        """Optimize route between multiple points"""
        try:
            logger.info("Optimizing route...")
            logger.debug(f"Points: {points}, Start point: {start_point}")
            
            if not points:
                logger.warning("No points provided for route optimization")
                return []
                
            if start_point:
                points.insert(0, start_point)
                
            coordinates = ";".join([f"{point[1]},{point[0]}" for point in points])
            
            url = f"{self.base_url}/optimized-trips/v1/mapbox/driving/{coordinates}"
            params = {
                'access_token': self.access_token,
                'roundtrip': 'false',
                'source': 'first',
                'destination': 'last'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info("Route optimized successfully")
            return data.get('waypoints', [])
            
        except Exception as e:
            logger.error(f"Error optimizing route: {str(e)}", exc_info=True)
            return []

    def get_static_map_url(self, center: List[float], markers: List[Dict]) -> str:
        """Generate a static map URL with markers"""
        try:
            logger.info("Generating static map URL...")
            
            # Base URL for Mapbox Static Images API
            base_url = "https://api.mapbox.com/styles/v1/mapbox/streets-v11/static"
            
            # Add markers to the URL
            marker_strings = []
            for marker in markers:
                coords = marker['coordinates']
                marker_strings.append(f"pin-s+ff0000({coords[0]},{coords[1]})")
            
            # Construct the final URL
            markers_str = ",".join(marker_strings)
            url = f"{base_url}/{markers_str}/{center[0]},{center[1]},13/600x400?access_token={self.access_token}"
            
            logger.info("Static map URL generated successfully")
            return url
            
        except Exception as e:
            logger.error(f"Error generating static map URL: {str(e)}")
            return ""

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