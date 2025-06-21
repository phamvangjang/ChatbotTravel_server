# Tích hợp Travel Chatbot vào Chatting Service

## Tổng quan

Đã tích hợp thành công travel chatbot service vào chatting service để trả lời câu hỏi du lịch từ người dùng dựa trên dataset địa điểm du lịch Hồ Chí Minh, thay vì phụ thuộc hoàn toàn vào OpenAI API.

## Tính năng mới

### 1. Nhận diện câu hỏi du lịch
- Hàm `is_travel_related_question()` kiểm tra xem câu hỏi có liên quan đến du lịch không
- Hỗ trợ đa ngôn ngữ: Tiếng Việt, Tiếng Anh, Tiếng Trung, Tiếng Nhật, Tiếng Hàn
- Sử dụng từ khóa và pattern matching để nhận diện

### 2. Xử lý câu hỏi du lịch
- Hàm `process_travel_question()` xử lý toàn bộ pipeline:
  - Nhận biết ngôn ngữ
  - Trích xuất thực thể và ý định
  - Tìm kiếm kết hợp với bộ lọc
  - Tạo câu trả lời tự nhiên

### 3. Tích hợp vào Chatting Service
- Cập nhật hàm `save_message_update()` để sử dụng travel chatbot
- Fallback về OpenAI API nếu không phải câu hỏi du lịch hoặc có lỗi
- Trả về thêm `travel_data` trong response

## Cách sử dụng

### API Endpoint
```
POST /api/chatting/messages/update
```

### Request Body
```json
{
    "conversation_id": 123,
    "sender": "user",
    "message_text": "Nhà hàng ngon ở quận 1",
    "message_type": "text"
}
```

### Response
```json
{
    "status": "success",
    "message": "Message saved successfully",
    "data": {
        "user_message": {
            "message_id": 456,
            "conversation_id": 123,
            "sender": "user",
            "message_text": "Nhà hàng ngon ở quận 1",
            "message_type": "text",
            "sent_at": "2024-01-01T12:00:00Z"
        },
        "bot_message": {
            "message_id": 457,
            "conversation_id": 123,
            "sender": "bot",
            "message_text": "Dựa trên tìm kiếm của bạn, tôi tìm thấy những nhà hàng ngon ở quận 1...",
            "message_type": "text",
            "sent_at": "2024-01-01T12:00:01Z"
        },
        "travel_data": {
            "success": true,
            "language": "vietnamese",
            "language_name": "Tiếng Việt",
            "search_results": [
                {
                    "id": "1",
                    "ten_dia_diem": "Nhà hàng ABC",
                    "mo_ta": "Nhà hàng nổi tiếng với món phở",
                    "loai_dia_diem": "Nhà hàng",
                    "khu_vuc": "Quận 1",
                    "similarity": 0.85,
                    "language": "vietnamese"
                }
            ],
            "suggested_activities": ["Ăn phở", "Thăm quan"],
            "follow_up_questions": ["Bạn có muốn biết thêm về giá cả không?"],
            "extracted_features": {
                "loai_dia_diem": "nhà hàng",
                "khu_vuc": "quận 1"
            }
        }
    }
}
```

## Từ khóa nhận diện du lịch

### Tiếng Việt
- Địa điểm: địa điểm, địa danh, nơi, chỗ, khu vực, quận, huyện
- Hoạt động: du lịch, thăm quan, khám phá, đi chơi, nghỉ dưỡng, ăn uống
- Loại địa điểm: nhà hàng, khách sạn, cafe, quán ăn, chợ, trung tâm thương mại
- Từ khóa tìm kiếm: ở đâu, đi đâu, tìm, kiếm

### Tiếng Anh
- Places: place, location, area, district, ward, attraction, destination
- Activities: travel, visit, explore, tour, vacation, restaurant, food
- Types: restaurant, hotel, cafe, market, mall, shopping center
- Keywords: where, find, search

### Tiếng Trung
- 景点, 地方, 区域, 地区 (địa điểm, địa phương, khu vực)
- 旅游, 参观, 探索, 游玩, 度假, 餐厅, 美食 (du lịch, thăm quan, khám phá, chơi, nghỉ, nhà hàng, ẩm thực)

### Tiếng Nhật
- 場所, エリア, 地域 (địa điểm, khu vực, vùng)
- 旅行, 観光, 探索, 遊び, 休暇, レストラン, 料理 (du lịch, thăm quan, khám phá, chơi, nghỉ, nhà hàng, ẩm thực)

### Tiếng Hàn
- 지역, 장소 (khu vực, địa điểm)
- 여행, 관광, 탐험, 놀기, 휴가, 레스토랑, 음식 (du lịch, thăm quan, khám phá, chơi, nghỉ, nhà hàng, ẩm thực)

## Kiểm tra và Test

Chạy file test để kiểm tra tích hợp:

```bash
python test_travel_integration.py
```

## Lưu ý

1. **Fallback mechanism**: Nếu không phải câu hỏi du lịch hoặc có lỗi, hệ thống sẽ tự động chuyển sang OpenAI API
2. **Performance**: Travel chatbot nhanh hơn OpenAI API vì sử dụng dataset local
3. **Accuracy**: Kết quả dựa trên dataset địa điểm Hồ Chí Minh, đảm bảo thông tin chính xác và cập nhật
4. **Multilingual**: Hỗ trợ đa ngôn ngữ với nhận biết ngôn ngữ tự động

## Cấu trúc file đã cập nhật

- `src/services/chatting_service.py`: Thêm các hàm mới và cập nhật logic xử lý
- `src/controllers/chatting_controller.py`: Cập nhật response model để hỗ trợ travel_data
- `test_travel_integration.py`: File test để kiểm tra chức năng
- `TRAVEL_CHATBOT_INTEGRATION.md`: Tài liệu hướng dẫn này 