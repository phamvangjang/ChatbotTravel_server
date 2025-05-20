import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import db
from app.models.models import User, Location, VietnamRegion, LocationCategory
from app import create_app
from app.utils.auth_utils import create_user

def init_db():
    app = create_app()
    with app.app_context():
        # Xóa và tạo lại tất cả bảng
        db.drop_all()
        db.create_all()
        
        # Tạo tài khoản admin mẫu
        admin = create_user(
            email='admin@example.com',
            password='admin123',
            full_name='Admin User'
        )
        
        # Tạo dữ liệu địa điểm mẫu
        locations = [
            # Miền Bắc
            Location(
                name='Hạ Long Bay',
                region=VietnamRegion.NORTH,
                province='Quảng Ninh',
                latitude=20.9100,
                longitude=107.1839,
                description='Di sản thiên nhiên thế giới với hàng nghìn hòn đảo đá vôi',
                categories=[LocationCategory.NATURE.value, LocationCategory.BEACH.value],
                ratings=4.8,
                best_time_to_visit={
                    'months': ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
                    'description': 'Mùa khô từ tháng 10 đến tháng 3, thời tiết mát mẻ và ít mưa'
                },
                weather_info={
                    'dry_season': 'Tháng 10 - Tháng 3',
                    'rainy_season': 'Tháng 4 - Tháng 9',
                    'average_temperature': '20-25°C'
                },
                activities={
                    'water_activities': ['boat_tour', 'kayaking', 'swimming'],
                    'land_activities': ['hiking', 'cave_exploration', 'photography']
                },
                attractions=[
                    {
                        'name': 'Hang Sửng Sốt',
                        'description': 'Hang động lớn nhất vịnh Hạ Long',
                        'best_time': 'Sáng sớm để tránh đông người'
                    },
                    {
                        'name': 'Đảo Ti Tốp',
                        'description': 'Bãi tắm đẹp và điểm ngắm cảnh toàn vịnh',
                        'best_time': 'Chiều tối để ngắm hoàng hôn'
                    }
                ],
                how_to_get_there={
                    'by_air': ['Sân bay Vân Đồn'],
                    'by_bus': ['Bến xe Mỹ Đình - Hà Nội'],
                    'by_car': ['Cao tốc Hà Nội - Hải Phòng - Hạ Long']
                },
                local_transportation={
                    'taxi': 'Taxi Mai Linh, Taxi Hạ Long',
                    'boat': 'Du thuyền tham quan vịnh',
                    'bus': 'Xe bus công cộng trong thành phố'
                },
                cuisine={
                    'local_specialties': [
                        'Chả mực Hạ Long',
                        'Sá sùng',
                        'Hàu nướng'
                    ],
                    'famous_restaurants': [
                        {
                            'name': 'Nhà hàng Cua Biển',
                            'address': '169 Lê Thánh Tông'
                        }
                    ],
                    'street_food_areas': [
                        'Chợ đêm Hạ Long',
                        'Phố ẩm thực Giếng Đồn'
                    ]
                },
                accommodation={
                    'luxury': ['Vinpearl Resort', 'Paradise Cruise'],
                    'mid_range': ['Mường Thanh Hotel', 'Royal Hotel'],
                    'budget': ['Backpacker Hostels', 'Homestay Hạ Long']
                },
                shopping={
                    'traditional_markets': ['Chợ Hạ Long 1', 'Chợ Hòn Gai'],
                    'modern_retail': ['Vincom Plaza', 'Marine Plaza'],
                    'souvenirs': ['Chợ đêm', 'Làng nghề truyền thống']
                }
            ),
            
            # Thành phố Hồ Chí Minh
            Location(
                name='Thành phố Hồ Chí Minh',
                region=VietnamRegion.SOUTH,
                province='TP.HCM',
                latitude=10.8231,
                longitude=106.6297,
                description='Thành phố năng động nhất Việt Nam với sự pha trộn độc đáo giữa hiện đại và truyền thống, là nơi hội tụ nhiều nền văn hóa với các sản phẩm du lịch đa dạng, là "thành phố không ngủ" với những hoạt động vui chơi, giải trí sôi động cả ngày lẫn đêm.',
                categories=[LocationCategory.URBAN.value, LocationCategory.CULTURAL.value],
                ratings=4.7,
                best_time_to_visit={
                    'months': ['Dec', 'Jan', 'Feb', 'Mar', 'Apr'],
                    'description': 'Mùa khô từ tháng 12 đến tháng 4, thời tiết mát mẻ và ít mưa'
                },
                weather_info={
                    'dry_season': 'Tháng 12 - Tháng 4',
                    'rainy_season': 'Tháng 5 - Tháng 11',
                    'average_temperature': '27°C'
                },
                activities={
                    'cultural': ['city_tour', 'museum_visit', 'market_exploration'],
                    'entertainment': ['rooftop_bars', 'shopping', 'food_tour']
                },
                attractions=[
                    {
                        'name': 'Phố đi bộ Nguyễn Huệ',
                        'description': 'Trung tâm văn hóa, giải trí về đêm',
                        'best_time': 'Chiều tối và tối'
                    },
                    {
                        'name': 'Chợ Bến Thành',
                        'description': 'Khu chợ truyền thống nổi tiếng nhất Sài Gòn',
                        'best_time': 'Sáng sớm hoặc chiều tối'
                    },
                    {
                        'name': 'Chợ Bình Tây',
                        'description': 'Trung tâm thương mại sầm uất của người Hoa',
                        'best_time': 'Buổi sáng'
                    }
                ],
                cuisine={
                    'local_specialties': [
                        'Cơm tấm',
                        'Hủ tiếu',
                        'Bánh mì Sài Gòn',
                        'Cá lóc nướng trui',
                        'Bánh xèo',
                        'Cơm cháy kho quẹt'
                    ],
                    'famous_restaurants': [
                        {
                            'name': 'Phố ốc Vĩnh Khánh',
                            'description': 'Thiên đường ốc và hải sản',
                            'address': 'Đường Vĩnh Khánh, Quận 4'
                        },
                        {
                            'name': 'Phố ẩm thực Hồ Thị Kỷ',
                            'description': 'Trên 100 quán ăn đa dạng',
                            'address': 'Đường Hồ Thị Kỷ, Quận 10'
                        }
                    ],
                    'street_food_areas': [
                        'Phố ẩm thực Phan Xích Long - Phú Nhuận',
                        'Phố ốc Vĩnh Khánh - Quận 4',
                        'Phố ẩm thực Hồ Thị Kỷ - Quận 10',
                        'Phố ẩm thực Nguyễn Thượng Hiền - Quận 3',
                        'Phố sủi cảo Hà Tôn Quyền - Quận 11'
                    ]
                },
                how_to_get_there={
                    'by_air': ['Sân bay Tân Sơn Nhất (cách trung tâm 8km)'],
                    'by_bus': ['Bến xe Miền Đông', 'Bến xe Miền Tây'],
                    'by_train': ['Ga Sài Gòn']
                },
                local_transportation={
                    'bus': 'Hệ thống xe buýt công cộng',
                    'bike': 'Xe đạp công cộng (5.000đ/30 phút)',
                    'grab': 'Dịch vụ gọi xe công nghệ',
                    'taxi': 'Taxi truyền thống'
                },
                shopping={
                    'traditional_markets': ['Chợ Bến Thành', 'Chợ Bình Tây'],
                    'modern_retail': ['Vincom Center', 'Saigon Centre'],
                    'souvenirs': ['Chợ Bến Thành', 'Đường Lê Lợi']
                },
                nightlife={
                    'areas': ['Phố Tây Bùi Viện', 'Phố Nhật Lê Thánh Tôn'],
                    'activities': ['Bar hopping', 'Rooftop bars', 'Live music']
                }
            )
        ]
        
        db.session.add_all(locations)
        db.session.commit()
        
        print("Database initialized successfully!")
        print("Admin account created:")
        print("Email: admin@example.com")
        print("Password: admin123")

if __name__ == '__main__':
    init_db() 