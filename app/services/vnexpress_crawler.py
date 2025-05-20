import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class VnExpressCrawler:
    def __init__(self):
        self.base_url = "https://vnexpress.net"
        self.travel_guide_url = "https://vnexpress.net/cam-nang-du-lich-tp-hcm-4608205.html"
        
    def get_travel_guide(self) -> Dict:
        """Crawl travel guide data from VnExpress"""
        try:
            logger.info("Fetching travel guide from VnExpress...")
            response = requests.get(self.travel_guide_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract main content
            content = soup.find('div', class_='sidebar_1')
            if not content:
                logger.warning("Could not find main content")
                return {}
                
            # Extract sections
            sections = {}
            
            # Extract weather info
            weather_section = content.find('h3', string='Mùa đẹp')
            if weather_section:
                weather_text = weather_section.find_next('p').text
                sections['weather'] = weather_text
                
            # Extract transportation info
            transport_section = content.find('h3', string='Di chuyển trong TP HCM')
            if transport_section:
                transport_text = transport_section.find_next('p').text
                sections['transportation'] = transport_text
                
            # Extract accommodation info
            accom_section = content.find('h3', string='Lưu trú')
            if accom_section:
                accom_text = accom_section.find_next('p').text
                sections['accommodation'] = accom_text
                
            # Extract food info
            food_section = content.find('h3', string='Ẩm thực')
            if food_section:
                food_text = food_section.find_next('p').text
                sections['food'] = food_text
                
            # Extract tips
            tips_section = content.find('h3', string='Lưu ý')
            if tips_section:
                tips = []
                for tip in tips_section.find_next('ul').find_all('li'):
                    tips.append(tip.text.strip())
                sections['tips'] = tips
                
            logger.info("Successfully extracted travel guide data")
            return sections
            
        except Exception as e:
            logger.error(f"Error crawling VnExpress: {str(e)}")
            return {}
            
    def get_attractions(self) -> List[Dict]:
        """Extract attractions from the travel guide"""
        try:
            guide_data = self.get_travel_guide()
            attractions = []
            
            # Extract historical sites
            hist_section = guide_data.get('historical_sites', '')
            if hist_section:
                attractions.append({
                    'name': 'Di tích lịch sử',
                    'description': hist_section,
                    'type': 'historical'
                })
                
            # Extract architecture
            arch_section = guide_data.get('architecture', '')
            if arch_section:
                attractions.append({
                    'name': 'Kiến trúc cổ',
                    'description': arch_section,
                    'type': 'architecture'
                })
                
            # Extract markets
            market_section = guide_data.get('markets', '')
            if market_section:
                attractions.append({
                    'name': 'Chợ',
                    'description': market_section,
                    'type': 'market'
                })
                
            return attractions
            
        except Exception as e:
            logger.error(f"Error extracting attractions: {str(e)}")
            return []
            
    def get_food_recommendations(self) -> List[Dict]:
        """Extract food recommendations from the travel guide"""
        try:
            guide_data = self.get_travel_guide()
            food_data = guide_data.get('food', '')
            
            if not food_data:
                return []
                
            # Extract food streets
            food_streets = []
            current_street = None
            
            for line in food_data.split('\n'):
                if line.startswith('**'):
                    if current_street:
                        food_streets.append(current_street)
                    current_street = {
                        'name': line.strip('*'),
                        'description': '',
                        'dishes': []
                    }
                elif current_street:
                    if line.strip():
                        current_street['description'] += line + '\n'
                        
            if current_street:
                food_streets.append(current_street)
                
            return food_streets
            
        except Exception as e:
            logger.error(f"Error extracting food recommendations: {str(e)}")
            return [] 