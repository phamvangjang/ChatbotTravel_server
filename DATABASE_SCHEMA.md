# Mô hình hóa dữ liệu - ScapeData Project

## Tổng quan hệ thống
Dự án ScapeData là một ứng dụng du lịch thông minh với các tính năng:
- Quản lý người dùng và xác thực
- Chatbot đa ngôn ngữ
- Gợi ý lịch trình du lịch
- Quản lý điểm du lịch (attractions)
- Xử lý tin nhắn và cuộc hội thoại

## Sơ đồ ERD (Entity Relationship Diagram)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│    Users    │────▶│Conversations │────▶│  Messages   │
└─────────────┘     └──────────────┘     └─────────────┘
       │                     │                     │
       │                     │                     │
       ▼                     │                     │
┌─────────────┐              │                     │
│     OTP     │              │                     │
└─────────────┘              │                     │
                             │                     │
┌─────────────┐     ┌──────────────┐               │
│ Attractions │◀────│ItineraryItems│◀──────────────┘
└─────────────┘     └──────────────┘
                             ▲
                             │
                             │
                    ┌─────────────┐
                    │    Users    │
                    └─────────────┘
```

## Chi tiết các bảng dữ liệu

### 1. Bảng Users
**Mô tả**: Lưu trữ thông tin người dùng hệ thống

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|-----|-------------|-----------|-------|
| user_id | INT | PRIMARY KEY, AUTO_INCREMENT | ID duy nhất của người dùng |
| full_name | VARCHAR(100) | NOT NULL | Họ tên đầy đủ |
| email | VARCHAR(100) | UNIQUE, NOT NULL | Email đăng nhập |
| password_hash | VARCHAR(255) | NOT NULL | Mật khẩu đã mã hóa |
| language_preference | VARCHAR(10) | DEFAULT 'vi' | Ngôn ngữ ưa thích |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | Thời gian tạo tài khoản |
| is_verified | BOOLEAN | DEFAULT FALSE | Trạng thái xác thực email |

**Mối quan hệ**:
- 1:N với Conversations
- 1:N với OTP
- 1:N với ItineraryItems

### 2. Bảng OTP
**Mô tả**: Lưu trữ mã OTP cho xác thực email

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|-----|-------------|-----------|-------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | ID duy nhất |
| email | VARCHAR(100) | NOT NULL | Email nhận OTP |
| otp_code | VARCHAR(6) | NOT NULL | Mã OTP 6 số |
| purpose | VARCHAR(20) | NOT NULL | Mục đích: 'register' hoặc 'reset_password' |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | Thời gian tạo |
| expires_at | DATETIME | NOT NULL | Thời gian hết hạn |
| is_used | BOOLEAN | DEFAULT FALSE | Đã sử dụng chưa |

### 3. Bảng Conversations
**Mô tả**: Lưu trữ các cuộc hội thoại giữa user và bot

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|-----|-------------|-----------|-------|
| conversation_id | INT | PRIMARY KEY, AUTO_INCREMENT | ID duy nhất cuộc hội thoại |
| user_id | INT | FOREIGN KEY | Tham chiếu đến Users |
| started_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | Thời gian bắt đầu |
| ended_at | DATETIME | NULL | Thời gian kết thúc |
| source_language | VARCHAR(10) | NOT NULL | Ngôn ngữ gốc |
| title | VARCHAR(100) | NULL | Tiêu đề cuộc hội thoại |

**Mối quan hệ**:
- N:1 với Users
- 1:N với Messages

### 4. Bảng Messages
**Mô tả**: Lưu trữ các tin nhắn trong cuộc hội thoại

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|-----|-------------|-----------|-------|
| message_id | INT | PRIMARY KEY, AUTO_INCREMENT | ID duy nhất tin nhắn |
| conversation_id | INT | FOREIGN KEY | Tham chiếu đến Conversations |
| sender | ENUM('user', 'bot') | NOT NULL | Người gửi |
| message_text | TEXT | NOT NULL | Nội dung tin nhắn gốc |
| translated_text | TEXT | NULL | Nội dung đã dịch |
| message_type | ENUM('text', 'voice') | DEFAULT 'text' | Loại tin nhắn |
| voice_url | TEXT | NULL | URL file âm thanh |
| sent_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | Thời gian gửi |

**Mối quan hệ**:
- N:1 với Conversations

### 5. Bảng Attractions
**Mô tả**: Lưu trữ thông tin các điểm du lịch

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|-----|-------------|-----------|-------|
| id | VARCHAR(50) | PRIMARY KEY | ID duy nhất điểm du lịch |
| name | VARCHAR(255) | NOT NULL | Tên điểm du lịch |
| address | VARCHAR(500) | NOT NULL | Địa chỉ |
| description | TEXT | NULL | Mô tả chi tiết |
| image_url | VARCHAR(500) | NULL | URL hình ảnh |
| rating | FLOAT | DEFAULT 0.0 | Đánh giá (0-5) |
| latitude | FLOAT | NULL | Vĩ độ |
| longitude | FLOAT | NULL | Kinh độ |
| category | VARCHAR(100) | NULL | Danh mục (nhà hàng, khách sạn, v.v.) |
| tags | JSON | NULL | Mảng các tag |
| price | FLOAT | NULL | Giá ước tính |
| opening_hours | VARCHAR(200) | NULL | Giờ mở cửa |
| phone_number | VARCHAR(20) | NULL | Số điện thoại |
| website | VARCHAR(500) | NULL | Website chính thức |
| aliases | JSON | NULL | Mảng tên gọi khác |

**Mối quan hệ**:
- 1:N với ItineraryItems

### 6. Bảng ItineraryItems
**Mô tả**: Lưu trữ các mục trong lịch trình du lịch

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|-----|-------------|-----------|-------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | ID duy nhất |
| user_id | INT | FOREIGN KEY | Tham chiếu đến Users |
| attraction_id | VARCHAR(50) | FOREIGN KEY | Tham chiếu đến Attractions |
| visit_time | DATETIME | NOT NULL | Thời gian thăm quan |
| estimated_duration | INT | NULL | Thời gian ước tính (phút) |
| notes | TEXT | NULL | Ghi chú |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | Thời gian tạo |

**Mối quan hệ**:
- N:1 với Users
- N:1 với Attractions

## Indexes đề xuất

### Performance Indexes
```sql
-- Users table
CREATE INDEX idx_users_email ON Users(email);
CREATE INDEX idx_users_created_at ON Users(created_at);

-- Conversations table
CREATE INDEX idx_conversations_user_id ON Conversations(user_id);
CREATE INDEX idx_conversations_started_at ON Conversations(started_at);

-- Messages table
CREATE INDEX idx_messages_conversation_id ON Messages(conversation_id);
CREATE INDEX idx_messages_sent_at ON Messages(sent_at);
CREATE INDEX idx_messages_sender ON Messages(sender);

-- Attractions table
CREATE INDEX idx_attractions_category ON Attractions(category);
CREATE INDEX idx_attractions_rating ON Attractions(rating);
CREATE INDEX idx_attractions_location ON Attractions(latitude, longitude);

-- ItineraryItems table
CREATE INDEX idx_itinerary_items_user_id ON ItineraryItems(user_id);
CREATE INDEX idx_itinerary_items_attraction_id ON ItineraryItems(attraction_id);
CREATE INDEX idx_itinerary_items_visit_time ON ItineraryItems(visit_time);
CREATE INDEX idx_itinerary_items_user_visit_time ON ItineraryItems(user_id, visit_time);

-- OTP table
CREATE INDEX idx_otp_email ON OTP(email);
CREATE INDEX idx_otp_expires_at ON OTP(expires_at);
```

## Constraints và Validation

### Foreign Key Constraints
```sql
ALTER TABLE Conversations ADD CONSTRAINT fk_conversations_user 
FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;

ALTER TABLE Messages ADD CONSTRAINT fk_messages_conversation 
FOREIGN KEY (conversation_id) REFERENCES Conversations(conversation_id) ON DELETE CASCADE;

ALTER TABLE ItineraryItems ADD CONSTRAINT fk_itinerary_items_user 
FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;

ALTER TABLE ItineraryItems ADD CONSTRAINT fk_itinerary_items_attraction 
FOREIGN KEY (attraction_id) REFERENCES Attractions(id) ON DELETE CASCADE;
```

### Check Constraints
```sql
-- Rating validation
ALTER TABLE Attractions ADD CONSTRAINT chk_rating_range 
CHECK (rating >= 0 AND rating <= 5);

-- Duration validation
ALTER TABLE ItineraryItems ADD CONSTRAINT chk_duration_positive 
CHECK (estimated_duration > 0);

-- Email format validation
ALTER TABLE Users ADD CONSTRAINT chk_email_format 
CHECK (email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
```

## Quy trình Migration

### Bước 1: Tạo database
```sql
CREATE DATABASE scapedata CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE scapedata;
```

### Bước 2: Tạo bảng theo thứ tự
1. Users
2. OTP
3. Conversations
4. Messages
5. Attractions
6. ItineraryItems

### Bước 3: Tạo indexes và constraints
Áp dụng các indexes và constraints đã đề xuất ở trên.

## Backup và Recovery Strategy

### Backup Strategy
- **Full Backup**: Hàng ngày vào 2:00 AM
- **Incremental Backup**: Mỗi 6 giờ
- **Transaction Log Backup**: Mỗi 15 phút

### Recovery Strategy
- **Point-in-time Recovery**: Có thể khôi phục đến bất kỳ thời điểm nào
- **Disaster Recovery**: RTO < 4 giờ, RPO < 15 phút

## Monitoring và Maintenance

### Performance Monitoring
- Query execution time
- Index usage statistics
- Table size growth
- Connection pool utilization

### Maintenance Tasks
- **Weekly**: Analyze table statistics
- **Monthly**: Rebuild fragmented indexes
- **Quarterly**: Archive old data (messages > 1 year) 