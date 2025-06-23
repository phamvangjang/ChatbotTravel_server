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


## Contributing

Vui lòng đọc [CONTRIBUTING.md](CONTRIBUTING.md) để biết thêm chi tiết về quy trình đóng góp.

## License

MIT License - xem [LICENSE.md](LICENSE.md) để biết thêm chi tiết. 