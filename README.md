# Vietnam Travel Assistant API

Hệ thống API hỗ trợ du lịch Việt Nam, cung cấp thông tin chi tiết về các địa điểm du lịch và trả lời câu hỏi của người dùng.

## Tính năng

- Thông tin chi tiết về các địa điểm du lịch
- Trả lời câu hỏi về:
  - Thời điểm tốt nhất để đi
  - Thời tiết
  - Phương tiện di chuyển
  - Ẩm thực địa phương
  - Chỗ ở
  - Địa điểm tham quan
  - Mua sắm
  - Hoạt động về đêm

## Cài đặt

1. Clone repository:
```bash
git clone <repository-url>
cd vietnam-travel-assistant
```

2. Tạo môi trường ảo:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

## Chạy ứng dụng

1. Chạy Flask server:
```bash
python run.py
```

Server sẽ chạy tại `http://localhost:5000`

## API Endpoints

### 1. Hỏi đáp về du lịch

```http
POST /api/questions/ask
Content-Type: application/json

{
    "question": "Khi nào nên đi du lịch Hạ Long?"
}
```

Ví dụ câu hỏi:
- "Khi nào nên đi du lịch Hạ Long?"
- "Thời tiết ở TP.HCM như thế nào?"
- "Có những món ăn gì ngon ở Hạ Long?"
- "Phương tiện di chuyển ở TP.HCM?"

### 2. Lấy danh sách địa điểm

```http
GET /api/questions/locations
```

## Cấu trúc dữ liệu

### Location
```python
{
    "name": str,
    "region": VietnamRegion,
    "categories": List[LocationCategory],
    "description": str,
    "weather": {
        "spring": str,
        "summer": str,
        "autumn": str,
        "winter": str,
        "monthly_details": Dict
    },
    "transportation": {
        "to_destination": List[Dict],
        "local": List[str]
    },
    "cuisine": {
        "specialties": List[Dict],
        "restaurants": List[Dict],
        "areas": List[str]
    },
    "accommodation": {
        "luxury": List[Dict],
        "mid_range": List[Dict],
        "budget": List[Dict]
    },
    "attractions": List[Dict],
    "shopping": {
        "modern": List[str],
        "traditional": List[str]
    },
    "nightlife": {
        "areas": List[str],
        "activities": List[str]
    },
    "suburban_tourism": List[Dict],
    "best_months": List[str],
    "peak_season": {
        "domestic": List[str],
        "international": List[str]
    }
}
```

## Contributing

Vui lòng đọc [CONTRIBUTING.md](CONTRIBUTING.md) để biết thêm chi tiết về quy trình đóng góp.

## License

MIT License - xem [LICENSE.md](LICENSE.md) để biết thêm chi tiết. 