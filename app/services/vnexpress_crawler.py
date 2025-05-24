import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class VnExpressCrawler:
    def __init__(self):
        self.base_url = "https://vnexpress.net"
        self.travel_guide_url = "https://vnexpress.net/cam-nang-du-lich-tp-hcm-4608205.html"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.data_dir = "data"
        self.ensure_data_directory()
        
    def ensure_data_directory(self):
        """Tạo thư mục data nếu chưa tồn tại"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Created data directory: {self.data_dir}")
            
    def save_to_json(self, data: Dict, filename: str):
        """Lưu dữ liệu vào file JSON"""
        try:
            filepath = os.path.join(self.data_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved data to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {str(e)}")
            return False
            
    def load_from_json(self, filename: str) -> Optional[Dict]:
        """Đọc dữ liệu từ file JSON"""
        try:
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                logger.warning(f"File not found: {filepath}")
                return None
                
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded data from {filepath}")
            return data
        except Exception as e:
            logger.error(f"Error loading data from {filename}: {str(e)}")
            return None
            
    def update_travel_data(self):
        """Cập nhật dữ liệu du lịch và lưu vào file"""
        try:
            # Lấy dữ liệu mới
            guide_data = self.get_travel_guide()
            attractions = self.get_attractions()
            food_recommendations = self.get_food_recommendations()
            
            # Tạo cấu trúc dữ liệu
            travel_data = {
                "last_updated": datetime.now().isoformat(),
                "guide": guide_data,
                "attractions": attractions,
                "food_recommendations": food_recommendations
            }
            
            # Lưu vào file
            if self.save_to_json(travel_data, "travel_data.json"):
                logger.info("Successfully updated travel data")
                return travel_data
            return None
            
        except Exception as e:
            logger.error(f"Error updating travel data: {str(e)}")
            return None
            
    def get_travel_data(self, force_update: bool = False) -> Optional[Dict]:
        """Lấy dữ liệu du lịch, cập nhật nếu cần"""
        # Nếu không yêu cầu cập nhật, thử đọc từ file
        if not force_update:
            data = self.load_from_json("travel_data.json")
            if data:
                return data
                
        # Nếu không có file hoặc yêu cầu cập nhật, cào dữ liệu mới
        return self.update_travel_data()

    def get_travel_guide(self) -> Dict:
        """Crawl travel guide data from VnExpress"""
        try:
            logger.info("Fetching travel guide from VnExpress...")
            response = requests.get(self.travel_guide_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different content selectors
            content = None
            selectors = [
                'article.fck_detail',
                'div.width_common',
                'div.sidebar_1',
                'div.content_detail'
            ]
            
            for selector in selectors:
                content = soup.select_one(selector)
                if content:
                    logger.info(f"Found content using selector: {selector}")
                    break
                    
            if not content:
                logger.warning("Could not find main content with any selector")
                return {}
                
            # Extract sections
            sections = {}
            
            # Extract weather info
            weather_section = content.find(['h2', 'h3'], string=lambda x: x and 'Mùa đẹp' in x)
            if weather_section:
                weather_text = weather_section.find_next('p')
                if weather_text:
                    sections['weather'] = weather_text.text.strip()
                
            # Extract transportation info
            transport_section = content.find(['h2', 'h3'], string=lambda x: x and 'Di chuyển trong TP HCM' in x)
            if transport_section:
                transport_text = transport_section.find_next('p')
                if transport_text:
                    sections['transportation'] = transport_text.text.strip()
                
            # Extract accommodation info
            accom_section = content.find(['h2', 'h3'], string=lambda x: x and 'Lưu trú' in x)
            if accom_section:
                accom_text = accom_section.find_next('p')
                if accom_text:
                    sections['accommodation'] = accom_text.text.strip()
                
            # Extract food info
            food_section = content.find(['h2', 'h3'], string=lambda x: x and 'Ẩm thực' in x)
            if food_section:
                food_text = food_section.find_next('p')
                if food_text:
                    sections['food'] = food_text.text.strip()
                    
                # Extract food streets
                food_streets = []
                current_street = None
                
                for element in food_section.find_next_siblings():
                    if element.name == 'h3' or element.name == 'h2':
                        break
                    if element.name == 'p':
                        text = element.text.strip()
                        if text.startswith('**'):
                            if current_street:
                                food_streets.append(current_street)
                            current_street = {
                                'name': text.strip('*'),
                                'description': '',
                                'dishes': []
                            }
                        elif current_street:
                            current_street['description'] += text + '\n'
                            
                if current_street:
                    food_streets.append(current_street)
                    
                sections['food_streets'] = food_streets
                
            # Extract tips
            tips_section = content.find(['h2', 'h3'], string=lambda x: x and 'Lưu ý' in x)
            if tips_section:
                tips = []
                tips_list = tips_section.find_next('ul')
                if tips_list:
                    for tip in tips_list.find_all('li'):
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
            # Lấy dữ liệu từ trang web
            response = requests.get(self.travel_guide_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different content selectors
            content = None
            selectors = [
                'article.fck_detail',
                'div.width_common',
                'div.sidebar_1',
                'div.content_detail'
            ]
            
            for selector in selectors:
                content = soup.select_one(selector)
                if content:
                    logger.info(f"Found content using selector: {selector}")
                    break
                    
            if not content:
                logger.warning("Could not find main content with any selector")
                return []
                
            attractions = []
            
            # Extract historical sites
            hist_section = content.find(['h2', 'h3'], string=lambda x: x and 'Di tích lịch sử' in x)
            if hist_section:
                hist_text = hist_section.find_next('p')
                if hist_text:
                    attractions.append({
                        'name': 'Di tích lịch sử',
                        'description': hist_text.text.strip(),
                        'type': 'historical'
                    })
                
            # Extract architecture
            arch_section = content.find(['h2', 'h3'], string=lambda x: x and 'Kiến trúc cổ' in x)
            if arch_section:
                arch_text = arch_section.find_next('p')
                if arch_text:
                    attractions.append({
                        'name': 'Kiến trúc cổ',
                        'description': arch_text.text.strip(),
                        'type': 'architecture'
                    })
                
            # Extract markets
            market_section = content.find(['h2', 'h3'], string=lambda x: x and 'Chợ' in x)
            if market_section:
                market_text = market_section.find_next('p')
                if market_text:
                    attractions.append({
                        'name': 'Chợ',
                        'description': market_text.text.strip(),
                        'type': 'market'
                    })
                
            logger.info(f"Successfully extracted {len(attractions)} attractions")
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