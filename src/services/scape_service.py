import pandas as pd
import uuid
from src.models.attraction import Attraction
from src.models.base import db
import json
import re
import os
import math

def extract_price_from_string(price_string):
    """
    Trích xuất giá vé từ chuỗi phức tạp hỗ trợ 5 thứ tiếng
    
    Args:
        price_string (str): Chuỗi chứa thông tin giá vé
        
    Returns:
        float: Giá vé trung bình hoặc None nếu không thể trích xuất
    """
    if not price_string or pd.isna(price_string):
        return None
    
    price_string = str(price_string).strip()
    
    # Từ khóa miễn phí cho 5 thứ tiếng
    free_keywords = {
        'vi': ['miễn phí', 'free', 'gratis', '0'],
        'en': ['free', 'no charge', 'gratis', '0'],
        'zh': ['免费', '免費', '免票', '0'],
        'ja': ['入場無料', '無料', 'フリー', '0'],
        'ko': ['무료', '무료 입장', '공짜', '0']
    }
    
    # Kiểm tra từ khóa miễn phí
    price_lower = price_string.lower()
    for lang_keywords in free_keywords.values():
        for keyword in lang_keywords:
            if keyword in price_lower:
                return 0.0
    
    # Patterns để tìm số trong các định dạng khác nhau
    # Hỗ trợ: 65.000, 65,000, 65000, 65,000.00
    price_patterns = [
        r'(\d{1,3}(?:[.,]\d{3})*(?:\.\d+)?)',  # 65.000, 65,000, 1,500, 30.5
        r'(\d+(?:\.\d+)?)',  # 65000, 15000.5
    ]
    
    prices = []
    for pattern in price_patterns:
        matches = re.findall(pattern, price_string)
        for match in matches:
            # Loại bỏ dấu phẩy và dấu chấm phân cách hàng nghìn
            clean_price = match.replace(',', '').replace('.', '')
            try:
                price = float(clean_price)
                # Chỉ lấy giá hợp lý (từ 0 đến 10 triệu VNĐ)
                if 0 <= price <= 10000000:
                    prices.append(price)
            except ValueError:
                continue
    
    if not prices:
        return None
    
    # Trả về giá trung bình nếu có nhiều giá
    return sum(prices) / len(prices)

def clean_value(value):
    """
    Làm sạch giá trị để tránh lỗi NaN trong MySQL
    
    Args:
        value: Giá trị cần làm sạch
        
    Returns:
        Giá trị đã được làm sạch
    """
    if pd.isna(value) or value is None:
        return None
    
    # Nếu là số và là NaN
    if isinstance(value, (int, float)) and math.isnan(value):
        return None
    
    # Nếu là string và rỗng
    if isinstance(value, str) and value.strip() == '':
        return None
    
    return value

def import_csv_to_attractions(csv_file_path):
    """
    Import dữ liệu từ file CSV vào bảng Attractions
    
    Args:
        csv_file_path (str): Đường dẫn đến file CSV
        
    Returns:
        dict: Kết quả import với số lượng records đã import và thông báo lỗi nếu có
    """
    try:
        # Đọc file CSV
        df = pd.read_csv(csv_file_path)
        
        # Kiểm tra các cột bắt buộc
        required_columns = ['ten_dia_diem', 'dia_chi']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'success': False,
                'error': f'❌ Thiếu các cột bắt buộc: {", ".join(missing_columns)}',
                'details': {
                    'missing_columns': missing_columns,
                    'available_columns': list(df.columns),
                    'total_columns': len(df.columns),
                    'suggestion': f'Hãy đảm bảo file CSV có các cột: {", ".join(required_columns)}'
                }
            }
        
        # Mapping các cột từ CSV sang model
        column_mapping = {
            'ten_dia_diem': 'name',
            'mo_ta': 'description', 
            'loai_dia_diem': 'category',
            'khu_vuc': 'address',  # Giả sử khu_vuc map với address
            'dia_chi': 'address',
            'tu_khoa': 'tags',
            'thoi_gian_hoat_dong': 'opening_hours',
            'gia_ve': 'price',
            'danh_gia': 'rating',
            'hinh_anh': 'image_url',
            'Latitude': 'latitude',
            'Longitude': 'longitude'
        }
        
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Tạo ID duy nhất cho attraction
                attraction_id = str(uuid.uuid4())
                
                # Xử lý tags - chuyển từ string sang list nếu cần
                tags = clean_value(row.get('tu_khoa', ''))
                if isinstance(tags, str) and tags:
                    # Giả sử tags được phân tách bằng dấu phẩy
                    tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                else:
                    tags_list = []
                
                # Xử lý giá vé từ chuỗi phức tạp (hỗ trợ đa ngôn ngữ)
                gia_ve_raw = clean_value(row.get('gia_ve', ''))
                processed_price = extract_price_from_string(gia_ve_raw) if gia_ve_raw else None
                
                # Kiểm tra dữ liệu bắt buộc
                ten_dia_diem = clean_value(row.get('ten_dia_diem', ''))
                dia_chi = clean_value(row.get('dia_chi', ''))
                
                if not ten_dia_diem:
                    raise ValueError("Tên địa điểm không được để trống")
                
                if not dia_chi:
                    raise ValueError("Địa chỉ không được để trống")
                
                # Xử lý các trường không có trong CSV với giá trị mặc định
                # phone_number, website, aliases không có trong CSV nên set null
                phone_number = None
                website = None
                aliases = []  # JSON array rỗng
                
                # Xử lý các giá trị số để tránh NaN
                rating_value = clean_value(row.get('danh_gia', 0))
                if rating_value is not None:
                    try:
                        rating_float = float(rating_value)
                        rating_final = rating_float if not math.isnan(rating_float) else 0.0
                    except (ValueError, TypeError):
                        rating_final = 0.0
                else:
                    rating_final = 0.0
                
                # Xử lý latitude và longitude
                lat_value = clean_value(row.get('Latitude'))
                if lat_value is not None:
                    try:
                        lat_float = float(lat_value)
                        latitude_final = lat_float if not math.isnan(lat_float) else None
                    except (ValueError, TypeError):
                        latitude_final = None
                else:
                    latitude_final = None
                
                lng_value = clean_value(row.get('Longitude'))
                if lng_value is not None:
                    try:
                        lng_float = float(lng_value)
                        longitude_final = lng_float if not math.isnan(lng_float) else None
                    except (ValueError, TypeError):
                        longitude_final = None
                else:
                    longitude_final = None
                
                # Tạo attraction object với tất cả các trường đã được làm sạch
                attraction = Attraction(
                    id=attraction_id,
                    name=ten_dia_diem,
                    description=clean_value(row.get('mo_ta', '')),
                    category=clean_value(row.get('loai_dia_diem', '')),
                    address=dia_chi,
                    tags=tags_list,
                    opening_hours=clean_value(row.get('thoi_gian_hoat_dong', '')),
                    price=processed_price,
                    rating=rating_final,
                    image_url=clean_value(row.get('hinh_anh', '')),
                    latitude=latitude_final,
                    longitude=longitude_final,
                    # Các trường không có trong CSV - set giá trị mặc định
                    phone_number=phone_number,
                    website=website,
                    aliases=aliases
                )
                
                # Thêm vào database
                db.session.add(attraction)
                imported_count += 1
                
            except Exception as e:
                error_msg = f"❌ Dòng {index + 1}: {str(e)}"
                if ten_dia_diem:
                    error_msg += f" (Tên: {ten_dia_diem})"
                errors.append(error_msg)
                continue
        
        # Commit tất cả thay đổi
        db.session.commit()
        
        return {
            'success': True,
            'imported_count': imported_count,
            'total_rows': len(df),
            'errors': errors
        }
        
    except pd.errors.EmptyDataError:
        return {
            'success': False,
            'error': '❌ File CSV trống hoặc không có dữ liệu',
            'details': {
                'file_path': csv_file_path,
                'file_size': os.path.getsize(csv_file_path) if os.path.exists(csv_file_path) else 0,
                'suggestion': 'Kiểm tra file CSV có chứa dữ liệu không'
            }
        }
    except pd.errors.ParserError as e:
        return {
            'success': False,
            'error': f'❌ Lỗi parse CSV: {str(e)}',
            'details': {
                'file_path': csv_file_path,
                'suggestion': 'Kiểm tra định dạng CSV và delimiter. Đảm bảo file được lưu với định dạng CSV chuẩn.',
                'common_issues': [
                    'Dấu phẩy trong dữ liệu không được escape',
                    'Delimiter không đúng (nên dùng dấu phẩy)',
                    'File có encoding không đúng'
                ]
            }
        }
    except Exception as e:
        # Rollback nếu có lỗi
        db.session.rollback()
        return {
            'success': False,
            'error': f'❌ Lỗi không mong muốn: {str(e)}',
            'details': {
                'file_path': csv_file_path,
                'suggestion': 'Kiểm tra lại file CSV và thử lại. Nếu lỗi vẫn tiếp tục, hãy liên hệ admin.',
                'error_type': type(e).__name__
            },
            'imported_count': 0,
            'total_rows': 0,
            'errors': []
        }
