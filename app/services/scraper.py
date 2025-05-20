import requests
from bs4 import BeautifulSoup
import json
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class VnExpressScraper:
    def __init__(self):
        logger.info("Initializing VnExpress scraper...")
        self.base_url = "https://vnexpress.net"
        self.travel_guide_url = "https://vnexpress.net/du-lich/ho-chi-minh"
        logger.info("VnExpress scraper initialized successfully")
        
    def get_travel_guide(self) -> Dict:
        """Scrape travel guide information from VnExpress"""
        try:
            logger.info(f"Scraping travel guide from: {self.travel_guide_url}")
            
            # Send request
            response = requests.get(self.travel_guide_url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.debug("HTML content parsed successfully")
            
            # Initialize travel data structure
            travel_data = {
                'attractions': [],
                'cuisine': [],
                'transportation': '',
                'accommodation': [],
                'weather': '',
                'tips': []
            }
            
            # Extract attractions
            logger.info("Extracting attractions...")
            attraction_sections = soup.find_all('div', class_='item-news')
            for section in attraction_sections:
                try:
                    title = section.find('h2', class_='title-news')
                    desc = section.find('p', class_='description')
                    if title and desc:
                        travel_data['attractions'].append({
                            'name': title.text.strip(),
                            'description': desc.text.strip()
                        })
                except Exception as e:
                    logger.warning(f"Error extracting attraction: {str(e)}")
                    
            logger.info(f"Found {len(travel_data['attractions'])} attractions")
            
            # Extract cuisine
            logger.info("Extracting cuisine information...")
            cuisine_sections = soup.find_all('div', class_='item-news')
            for section in cuisine_sections:
                try:
                    title = section.find('h2', class_='title-news')
                    desc = section.find('p', class_='description')
                    if title and desc and any(keyword in title.text.lower() for keyword in ['món', 'ăn', 'nhà hàng']):
                        travel_data['cuisine'].append({
                            'name': title.text.strip(),
                            'description': desc.text.strip()
                        })
                except Exception as e:
                    logger.warning(f"Error extracting cuisine: {str(e)}")
                    
            logger.info(f"Found {len(travel_data['cuisine'])} cuisine items")
            
            # Extract transportation
            logger.info("Extracting transportation information...")
            transport_sections = soup.find_all('div', class_='item-news')
            for section in transport_sections:
                try:
                    title = section.find('h2', class_='title-news')
                    desc = section.find('p', class_='description')
                    if title and desc and any(keyword in title.text.lower() for keyword in ['di chuyển', 'phương tiện', 'taxi']):
                        travel_data['transportation'] = desc.text.strip()
                        break
                except Exception as e:
                    logger.warning(f"Error extracting transportation: {str(e)}")
                    
            # Extract accommodation
            logger.info("Extracting accommodation information...")
            accom_sections = soup.find_all('div', class_='item-news')
            for section in accom_sections:
                try:
                    title = section.find('h2', class_='title-news')
                    desc = section.find('p', class_='description')
                    if title and desc and any(keyword in title.text.lower() for keyword in ['khách sạn', 'nhà nghỉ', 'homestay']):
                        travel_data['accommodation'].append({
                            'type': title.text.strip(),
                            'description': desc.text.strip()
                        })
                except Exception as e:
                    logger.warning(f"Error extracting accommodation: {str(e)}")
                    
            logger.info(f"Found {len(travel_data['accommodation'])} accommodation options")
            
            # Extract weather
            logger.info("Extracting weather information...")
            weather_sections = soup.find_all('div', class_='item-news')
            for section in weather_sections:
                try:
                    title = section.find('h2', class_='title-news')
                    desc = section.find('p', class_='description')
                    if title and desc and any(keyword in title.text.lower() for keyword in ['thời tiết', 'khí hậu']):
                        travel_data['weather'] = desc.text.strip()
                        break
                except Exception as e:
                    logger.warning(f"Error extracting weather: {str(e)}")
                    
            # Extract tips
            logger.info("Extracting travel tips...")
            tip_sections = soup.find_all('div', class_='item-news')
            for section in tip_sections:
                try:
                    title = section.find('h2', class_='title-news')
                    desc = section.find('p', class_='description')
                    if title and desc and any(keyword in title.text.lower() for keyword in ['kinh nghiệm', 'lưu ý', 'tip']):
                        travel_data['tips'].append(desc.text.strip())
                except Exception as e:
                    logger.warning(f"Error extracting tip: {str(e)}")
                    
            logger.info(f"Found {len(travel_data['tips'])} travel tips")
            
            # Add default data if sections are empty
            if not travel_data['attractions']:
                logger.warning("No attractions found, adding default data")
                travel_data['attractions'] = [
                    {
                        'name': 'Bến Thành Market',
                        'description': 'Famous central market in District 1'
                    },
                    {
                        'name': 'Notre Dame Cathedral',
                        'description': 'Historic French colonial cathedral'
                    }
                ]
                
            if not travel_data['cuisine']:
                logger.warning("No cuisine found, adding default data")
                travel_data['cuisine'] = [
                    {
                        'name': 'Phở',
                        'description': 'Traditional Vietnamese noodle soup'
                    },
                    {
                        'name': 'Bánh mì',
                        'description': 'Vietnamese baguette sandwich'
                    }
                ]
                
            if not travel_data['transportation']:
                logger.warning("No transportation found, adding default data")
                travel_data['transportation'] = "Taxis and Grab are widely available. Public buses and motorbike taxis are also common."
                
            if not travel_data['accommodation']:
                logger.warning("No accommodation found, adding default data")
                travel_data['accommodation'] = [
                    {
                        'type': 'Hotels',
                        'description': 'Wide range of hotels from budget to luxury in District 1'
                    },
                    {
                        'type': 'Hostels',
                        'description': 'Budget-friendly options in Pham Ngu Lao area'
                    }
                ]
                
            if not travel_data['weather']:
                logger.warning("No weather found, adding default data")
                travel_data['weather'] = "Tropical climate with two seasons: dry (December to April) and rainy (May to November)"
                
            if not travel_data['tips']:
                logger.warning("No tips found, adding default data")
                travel_data['tips'] = [
                    "Carry an umbrella during rainy season",
                    "Bargain when shopping at markets",
                    "Be careful with street food hygiene"
                ]
                
            logger.info("Travel guide data scraped successfully")
            return travel_data
            
        except Exception as e:
            logger.error(f"Error scraping travel guide: {str(e)}", exc_info=True)
            return {}
            
    def save_to_json(self, data: Dict) -> bool:
        """Save scraped data to JSON file"""
        try:
            logger.info("Saving travel data to JSON file...")
            
            # Create data directory if it doesn't exist
            os.makedirs('data', exist_ok=True)
            
            # Save to file
            with open('data/travel_guide.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info("Travel data saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving travel data: {str(e)}", exc_info=True)
            return False
            
    def load_from_json(self) -> Optional[Dict]:
        """Load travel data from JSON file"""
        try:
            logger.info("Loading travel data from JSON file...")
            
            file_path = 'data/travel_guide.json'
            if not os.path.exists(file_path):
                logger.warning("Travel data file not found")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            logger.info("Travel data loaded successfully")
            return data
            
        except Exception as e:
            logger.error(f"Error loading travel data: {str(e)}", exc_info=True)
            return None

# Initialize scraper
try:
    logger.info("Creating VnExpress scraper instance...")
    scraper = VnExpressScraper()
    logger.info("VnExpress scraper instance created successfully")
except Exception as e:
    logger.error(f"Failed to initialize VnExpress scraper: {str(e)}", exc_info=True)
    scraper = None 