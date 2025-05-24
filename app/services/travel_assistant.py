from typing import Dict, Optional, List
from .openai_service import openai_service
from .mapbox_service import mapbox_service
from .scraper import scraper
from .vnexpress_crawler import VnExpressCrawler
from .language_detector import LanguageDetector
import json
import os
import logging

logger = logging.getLogger(__name__)

class TravelAssistant:
    def __init__(self):
        logger.info("Initializing TravelAssistant...")
        
        # Check required environment variables
        if not os.getenv('OPENAI_API_KEY'):
            logger.error("OPENAI_API_KEY environment variable is not set")
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        if not os.getenv('MAPBOX_ACCESS_TOKEN'):
            logger.error("MAPBOX_ACCESS_TOKEN environment variable is not set")
            raise ValueError("MAPBOX_ACCESS_TOKEN environment variable is not set")
            
        self.openai = openai_service
        self.mapbox = mapbox_service
        self.vnexpress_crawler = VnExpressCrawler()
        self.language_detector = LanguageDetector()
        
        logger.info("Loading travel data...")
        self.travel_data = scraper.load_from_json()
        
        # If no data exists, scrape and save it
        if not self.travel_data:
            logger.info("No existing travel data found. Scraping new data...")
            self.travel_data = scraper.get_travel_guide()
            scraper.save_to_json(self.travel_data)
            logger.info("Travel data saved successfully")
        
    def process_travel_query(
        self,
        query: str,
        user_id: str,
        user_location: Dict[str, float],
        lang: Optional[str] = None
    ) -> Dict:
        """Process travel query and return recommendations"""
        try:
            logger.info(f"Processing travel query: {query}")
            
            # Detect language if not specified
            if not lang:
                lang = self.language_detector.detect_language(query)
                logger.info(f"Detected language: {self.language_detector.get_language_name(lang)}")
                print(f"Detected language: {self.language_detector.get_language_name(lang)}")
            
            # Validate language
            if not self.language_detector.is_supported_language(lang):
                logger.warning(f"Unsupported language: {lang}, defaulting to Vietnamese")
                lang = 'vi'
            
            # Get data from VnExpress
            vnexpress_data = self.vnexpress_crawler.get_travel_guide()
            attractions = self.vnexpress_crawler.get_attractions()
            food_recommendations = self.vnexpress_crawler.get_food_recommendations()
            
            # Prepare context with VnExpress data
            context = self._prepare_context(vnexpress_data, attractions, food_recommendations)
            
            # Get recommendations from OpenAI
            recommendations = self.openai.analyze_travel_query(query, context)
            
            # Định nghĩa center và markers trước
            center = [106.660172, 10.762622]  # Tọa độ mặc định của HCMC
            markers = []
            
            # Add location coordinates và tạo markers
            for day in recommendations['itinerary']:
                for activity in day['activities']:
                    if 'location' in activity:
                        coords = self.mapbox.search_places(activity['location']['address'])
                        if coords:
                            activity['location']['coordinates'] = {
                                'latitude': coords[0],
                                'longitude': coords[1]
                            }
                            # Thêm vào markers
                            markers.append({
                                'name': activity['location']['name'],
                                'coordinates': [coords[1], coords[0]]  # [longitude, latitude]
                            })
            
            # Tạo dữ liệu cho bản đồ
            map_data = {
                'center': center,
                'markers': []
            }
            
            # Thêm markers vào map_data
            for marker in markers:
                map_data['markers'].append({
                    'name': marker['name'],
                    'coordinates': {
                        'latitude': marker['coordinates'][1],
                        'longitude': marker['coordinates'][0]
                    }
                })
            
            # Cập nhật center nếu có markers
            if markers:
                center = markers[0]['coordinates']
                map_data['center'] = center
            
            # Tạo URL bản đồ tĩnh
            recommendations['map_url'] = self.mapbox.get_static_map_url(center, markers)
            
            # Add VnExpress tips and transportation info
            if 'tips' in vnexpress_data:
                recommendations['tips'].extend(vnexpress_data['tips'])
            if 'transportation' in vnexpress_data:
                recommendations['transportation'] = vnexpress_data['transportation']
            
            # Translate if needed
            if lang != 'vi':
                recommendations = self._translate_response(recommendations, lang)
            
            # Add detected language info
            recommendations['detected_language'] = {
                'code': lang,
                'name': self.language_detector.get_language_name(lang)
            }
            
            # Thêm map_data vào recommendations
            recommendations['map_data'] = map_data
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error processing travel query: {str(e)}")
            raise
        
    def _prepare_context(self, vnexpress_data: Dict, attractions: List[Dict], food_recommendations: List[Dict]) -> str:
        """Prepare context string from VnExpress data"""
        context_parts = []
        
        # Add weather info
        if 'weather' in vnexpress_data:
            context_parts.append(f"Weather: {vnexpress_data['weather']}")
            
        # Add attractions
        if attractions:
            context_parts.append("Attractions:")
            for attraction in attractions:
                context_parts.append(f"- {attraction['name']}: {attraction['description']}")
                
        # Add food recommendations
        if food_recommendations:
            context_parts.append("Food Recommendations:")
            for food in food_recommendations:
                context_parts.append(f"- {food['name']}: {food['description']}")
                
        # Add accommodation info
        if 'accommodation' in vnexpress_data:
            context_parts.append(f"Accommodation: {vnexpress_data['accommodation']}")
            
        return "\n".join(context_parts)
        
    def _translate_response(self, response: Dict, target_lang: str) -> Dict:
        """Translate response to target language"""
        try:
            logger.info(f"Translating response to {target_lang}...")
            translated = {}
            
            for key, value in response.items():
                if key == 'itinerary':
                    translated[key] = []
                    for day in value:
                        translated_day = {
                            'day': day['day'],
                            'activities': []
                        }
                        for activity in day['activities']:
                            logger.debug(f"Translating activity: {activity['name']}")
                            translated_activity = {
                                'time': activity['time'],
                                'name': self.openai.translate_text(activity['name'], target_lang),
                                'description': self.openai.translate_text(activity['description'], target_lang),
                                'location': {
                                    'name': self.openai.translate_text(activity['location']['name'], target_lang),
                                    'address': self.openai.translate_text(activity['location']['address'], target_lang),
                                    'coordinates': activity['location'].get('coordinates')
                                },
                                'estimated_cost': activity['estimated_cost']
                            }
                            translated_day['activities'].append(translated_activity)
                        translated[key].append(translated_day)
                elif key == 'tips':
                    translated[key] = [
                        self.openai.translate_text(tip, target_lang)
                        for tip in value
                    ]
                elif key == 'transportation':
                    translated[key] = self.openai.translate_text(value, target_lang)
                elif key == 'total_cost':
                    translated[key] = value
                elif key == 'map_url':
                    translated[key] = value
                    
            logger.info("Translation completed successfully")
            return translated
            
        except Exception as e:
            logger.error(f"Error translating response: {str(e)}", exc_info=True)
            return response

# Initialize travel assistant
try:
    logger.info("Creating travel assistant instance...")
    travel_assistant = TravelAssistant()
    logger.info("Travel assistant instance created successfully")
except Exception as e:
    logger.error(f"Failed to initialize travel assistant: {str(e)}", exc_info=True)
    travel_assistant = None 