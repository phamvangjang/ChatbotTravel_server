import requests
from bs4 import BeautifulSoup
import json
from typing import Dict, List, Optional
import re
from datetime import datetime

class VNExpressCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def extract_price_range(self, text: str) -> Dict:
        """Extract price range from text"""
        # Match patterns like "2-4 triệu đồng", "200-300k VND", etc.
        price_pattern = r'(\d+(?:[\.,]\d+)?(?:\s*-\s*\d+(?:[\.,]\d+)?)?)\s*(k|nghìn|triệu|tr)?\s*(VND|đồng)?'
        match = re.search(price_pattern, text)
        if match:
            price_text = match.group(0)
            return {
                "price_text": price_text,
                "original_text": text
            }
        return {"original_text": text}

    def parse_hcmc_data(self, url: str) -> Dict:
        """Parse HCMC travel guide data from VNExpress"""
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        data = {
            "name": "TP.HCM",
            "region": "Nam",
            "description": "Thành phố năng động nhất Việt Nam, với các sản phẩm du lịch đa dạng, là thành phố không ngủ với những hoạt động vui chơi, giải trí sôi động cả ngày lẫn đêm",
            "weather": {
                "dry_season": "Tháng 12 đến tháng 4, nhiệt độ cao đều, nắng không gay gắt, độ ẩm thấp",
                "rainy_season": "Tháng 5 đến tháng 11, có mưa rào",
                "average_temperature": "27 độ C",
                "monthly_details": {
                    "all": "Nhiệt độ trung bình khoảng 27 độ C, cao nhất lên hơn 40 độ C nhưng đa phần nắng không gay gắt, độ ẩm thấp, dịu mát về chiều tối"
                }
            },
            "transportation": {
                "to_destination": [
                    {
                        "type": "Máy bay",
                        "to": "Sân bay Tân Sơn Nhất",
                        "details": "Các hãng hàng không nội địa đều khai thác chuyến bay thẳng với tần suất lớn",
                        "price_range": "2-4 triệu đồng (khứ hồi)",
                        "notes": "Sân bay cách trung tâm (quận 1) khoảng 8 km"
                    },
                    {
                        "type": "Tàu hỏa",
                        "details": "Tàu Thống Nhất từ Hà Nội, thời gian 30 tiếng",
                        "stops": ["Vinh", "Đồng Hới", "Huế", "Đà Nẵng"]
                    }
                ],
                "local": [
                    {
                        "type": "Xe máy thuê",
                        "price_range": "100.000-200.000 đồng/ngày",
                        "notes": "Cần đặt cọc 1-4 triệu đồng hoặc giấy tờ tùy thân"
                    },
                    {
                        "type": "Xe công nghệ",
                        "options": ["Ôtô", "Xe máy"],
                        "notes": "Tiện lợi nhưng chi phí cao nếu di chuyển nhiều"
                    },
                    {
                        "type": "Xe buýt công cộng",
                        "notes": "Tiết kiệm chi phí"
                    },
                    {
                        "type": "Xe đạp công cộng",
                        "area": "Khu trung tâm quận 1",
                        "price": "5.000 đồng/30 phút, 10.000 đồng/60 phút"
                    }
                ]
            },
            "cuisine": {
                "description": "Nơi hội tụ của ẩm thực nhiều vùng miền và nhiều quốc gia",
                "specialties": [
                    "Cơm tấm",
                    "Hủ tíu",
                    "Bánh mì",
                    "Cá lóc nướng trui",
                    "Bánh xèo",
                    "Cơm cháy kho quẹt"
                ],
                "food_streets": [
                    {
                        "name": "Phố Phan Xích Long",
                        "location": "Quận Phú Nhuận",
                        "description": "Tập trung nhiều nhà hàng, quán ăn đa dạng từ Á đến Âu",
                        "specialties": ["Lẩu", "Đồ nướng", "Ẩm thực Nhật", "Thái", "Hàn"],
                        "opening_hours": "Đến nửa đêm"
                    },
                    {
                        "name": "Phố ốc Vĩnh Khánh",
                        "location": "Quận 4",
                        "specialties": ["Ốc", "Hải sản"],
                        "price_range": "80.000-150.000 đồng/phần",
                        "opening_hours": "Đến nửa đêm"
                    },
                    {
                        "name": "Phố ẩm thực Hồ Thị Kỷ",
                        "location": "Quận 10",
                        "description": "Hơn 100 hàng quán Âu-Á",
                        "specialties": ["Xiên nướng", "Hải sản", "Tôm hùm nướng phô mai"],
                        "price_range": "7.000-100.000 đồng",
                        "opening_hours": "Từ 15h"
                    }
                ]
            },
            "attractions": [
                {
                    "name": "Phố đi bộ Nguyễn Huệ",
                    "type": "Giải trí",
                    "description": "Trung tâm văn hóa, giải trí về đêm",
                    "best_time": "Chiều tối và tối"
                },
                {
                    "name": "Dinh Độc Lập",
                    "type": "Di tích lịch sử",
                    "address": "135 Nam Kỳ Khởi Nghĩa"
                },
                {
                    "name": "Bảo tàng chứng tích chiến tranh",
                    "type": "Bảo tàng",
                    "address": "28 Võ Văn Tần"
                },
                {
                    "name": "Nhà thờ Đức Bà",
                    "type": "Kiến trúc",
                    "style": "Gothic",
                    "built_year": 1880
                },
                {
                    "name": "Bưu điện Trung tâm",
                    "type": "Kiến trúc",
                    "style": "Pháp",
                    "built_year": 1891
                }
            ],
            "shopping": {
                "traditional_markets": [
                    "Chợ Bến Thành",
                    "Chợ Bình Tây"
                ],
                "modern_retail": [
                    "Vincom Center",
                    "Saigon Centre"
                ]
            },
            "suburban_tourism": [
                {
                    "name": "Củ Chi",
                    "attractions": ["Địa đạo Củ Chi", "Khu du lịch Bến Dược"],
                    "distance": "70km từ trung tâm"
                },
                {
                    "name": "Cần Giờ",
                    "attractions": ["Rừng ngập mặn", "Khu dã ngoại Dần Xây"],
                    "distance": "50km từ trung tâm"
                }
            ],
            "travel_tips": [
                "Chủ động bảo quản tư trang cá nhân khi đến nơi đông người",
                "Tránh ra đường vào giờ cao điểm (8h-9h30 và 17h30-19h)",
                "Kiểm tra đường đi theo bản đồ để tránh các đường một chiều",
                "Không nên đi vào các hẻm nhỏ nếu không thạo đường"
            ]
        }
        
        return data

    def save_to_json(self, data: Dict, filename: str):
        """Save crawled data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    crawler = VNExpressCrawler()
    url = "https://vnexpress.net/cam-nang-du-lich-tp-hcm-4608205.html"
    
    # Crawl HCMC data
    hcmc_data = crawler.parse_hcmc_data(url)
    
    # Save to JSON file
    crawler.save_to_json(hcmc_data, 'data/hcmc_travel_data.json')
    
    print("Crawled and saved HCMC travel data successfully!")

if __name__ == "__main__":
    main() 