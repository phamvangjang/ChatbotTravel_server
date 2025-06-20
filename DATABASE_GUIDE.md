# Hướng dẫn sử dụng Database - ScapeData Project

## 🚀 Quick Start

### 1. Cài đặt MySQL
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server

# Windows
# Tải MySQL Installer từ https://dev.mysql.com/downloads/installer/
```

### 2. Tạo Database
```bash
# Đăng nhập MySQL
mysql -u root -p

# Chạy script tạo database
source database_schema.sql
```

### 3. Cấu hình Environment
Tạo file `.env` trong thư mục gốc:
```env
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/scapedata
```

## 📊 Cấu trúc Database

### Core Tables (6 bảng chính)
- **Users**: Quản lý người dùng
- **OTP**: Xác thực email
- **Conversations**: Cuộc hội thoại
- **Messages**: Tin nhắn
- **Attractions**: Điểm du lịch
- **ItineraryItems**: Mục lịch trình (liên kết với User)

## 🔍 Queries thường dùng

### 1. Lấy thông tin user và cuộc hội thoại
```sql
SELECT 
    u.full_name,
    u.email,
    c.title,
    c.started_at,
    COUNT(m.message_id) as message_count
FROM Users u
JOIN Conversations c ON u.user_id = c.user_id
LEFT JOIN Messages m ON c.conversation_id = m.conversation_id
WHERE u.user_id = ?
GROUP BY u.full_name, u.email, c.title, c.started_at
ORDER BY c.started_at DESC;
```

### 2. Lấy lịch trình của user
```sql
CALL GetUserItinerary(1);
```

### 3. Tìm kiếm điểm du lịch
```sql
CALL SearchAttractions('chùa');
```

### 4. Lấy điểm du lịch theo danh mục
```sql
CALL GetAttractionsByCategory('Di tích lịch sử');
```

### 5. Thống kê lịch trình của user
```sql
SELECT 
    u.full_name,
    COUNT(ii.id) as total_items,
    COUNT(DISTINCT ii.attraction_id) as unique_attractions,
    AVG(ii.estimated_duration) as avg_duration
FROM Users u
LEFT JOIN ItineraryItems ii ON u.user_id = ii.user_id
WHERE u.user_id = ?
GROUP BY u.user_id, u.full_name;
```

### 6. Thống kê điểm du lịch phổ biến
```sql
SELECT * FROM PopularAttractions LIMIT 10;
```

### 7. Lấy lịch trình theo thời gian
```sql
SELECT 
    ii.visit_time,
    a.name as attraction_name,
    a.address,
    ii.estimated_duration,
    ii.notes
FROM ItineraryItems ii
JOIN Attractions a ON ii.attraction_id = a.id
WHERE ii.user_id = ? 
AND ii.visit_time BETWEEN ? AND ?
ORDER BY ii.visit_time;
```

## 🛠️ API Endpoints tương ứng

### Users
```python
# GET /api/users/{user_id}
# POST /api/users/register
# POST /api/users/login
# PUT /api/users/{user_id}
```

### Conversations
```python
# GET /api/conversations?user_id={user_id}
# POST /api/conversations
# GET /api/conversations/{conversation_id}
# PUT /api/conversations/{conversation_id}
```

### Messages
```python
# GET /api/conversations/{conversation_id}/messages
# POST /api/conversations/{conversation_id}/messages
# PUT /api/messages/{message_id}
```

### Attractions
```python
# GET /api/attractions
# GET /api/attractions/{attraction_id}
# GET /api/attractions/search?q={query}
# GET /api/attractions/category/{category}
```

### ItineraryItems
```python
# GET /api/users/{user_id}/itinerary-items
# POST /api/users/{user_id}/itinerary-items
# PUT /api/itinerary-items/{item_id}
# DELETE /api/itinerary-items/{item_id}
# GET /api/itinerary-items?user_id={user_id}&date={date}
```

## 🔧 Database Operations

### Backup Database
```bash
# Full backup
mysqldump -u root -p scapedata > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup specific tables
mysqldump -u root -p scapedata Users Conversations Messages Attractions ItineraryItems > core_tables_backup.sql
```

### Restore Database
```bash
mysql -u root -p scapedata < backup_file.sql
```

### Monitor Performance
```sql
-- Xem slow queries
SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'long_query_time';

-- Xem index usage
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    CARDINALITY
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'scapedata'
ORDER BY TABLE_NAME, INDEX_NAME;
```

### Optimize Tables
```sql
-- Analyze table statistics
ANALYZE TABLE Users, Conversations, Messages, Attractions, ItineraryItems;

-- Optimize tables
OPTIMIZE TABLE Users, Conversations, Messages, Attractions, ItineraryItems;
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Connection Error
```python
# Error: Can't connect to MySQL server
# Solution: Kiểm tra MySQL service
sudo systemctl status mysql
sudo systemctl start mysql
```

#### 2. Character Encoding Issues
```sql
-- Kiểm tra character set
SHOW VARIABLES LIKE 'character_set%';
SHOW VARIABLES LIKE 'collation%';

-- Set proper encoding
SET NAMES utf8mb4;
```

#### 3. Foreign Key Constraint Errors
```sql
-- Kiểm tra foreign key constraints
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'scapedata' 
AND REFERENCED_TABLE_NAME IS NOT NULL;
```

#### 4. Performance Issues
```sql
-- Kiểm tra slow queries
SELECT 
    query,
    exec_count,
    avg_timer_wait/1000000000 as avg_time_sec
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME = 'scapedata'
ORDER BY avg_timer_wait DESC
LIMIT 10;
```

## 📈 Monitoring Queries

### User Activity
```sql
-- Users active in last 7 days
SELECT 
    COUNT(DISTINCT u.user_id) as active_users
FROM Users u
JOIN Conversations c ON u.user_id = c.user_id
WHERE c.started_at >= DATE_SUB(NOW(), INTERVAL 7 DAY);
```

### User Itinerary Activity
```sql
-- Users with itinerary items in last 30 days
SELECT 
    COUNT(DISTINCT u.user_id) as users_with_itinerary
FROM Users u
JOIN ItineraryItems ii ON u.user_id = ii.user_id
WHERE ii.visit_time >= DATE_SUB(NOW(), INTERVAL 30 DAY);
```

### Popular Attractions
```sql
-- Top 10 most included attractions
SELECT 
    a.name,
    a.category,
    COUNT(ii.id) as inclusion_count,
    AVG(ii.estimated_duration) as avg_duration
FROM Attractions a
LEFT JOIN ItineraryItems ii ON a.id = ii.attraction_id
GROUP BY a.id, a.name, a.category
ORDER BY inclusion_count DESC
LIMIT 10;
```

### Conversation Statistics
```sql
-- Average messages per conversation
SELECT 
    AVG(message_count) as avg_messages_per_conversation,
    MAX(message_count) as max_messages,
    MIN(message_count) as min_messages
FROM (
    SELECT 
        conversation_id,
        COUNT(*) as message_count
    FROM Messages
    GROUP BY conversation_id
) as msg_counts;
```

## 🔐 Security Best Practices

### 1. User Permissions
```sql
-- Tạo user với quyền hạn chế
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON scapedata.* TO 'app_user'@'localhost';
REVOKE DROP, CREATE, ALTER ON scapedata.* FROM 'app_user'@'localhost';
```

### 2. Password Policy
```sql
-- Set password validation
SET GLOBAL validate_password.policy=MEDIUM;
SET GLOBAL validate_password.length=8;
```

### 3. SSL Connection
```sql
-- Require SSL for connections
ALTER USER 'app_user'@'localhost' REQUIRE SSL;
```

## 📝 Migration Scripts

### Adding New Columns
```sql
-- Example: Add new column to Users table
ALTER TABLE Users 
ADD COLUMN phone_number VARCHAR(20) NULL AFTER email,
ADD COLUMN avatar_url VARCHAR(500) NULL AFTER phone_number;
```

### Updating Data Types
```sql
-- Example: Change column type
ALTER TABLE Attractions 
MODIFY COLUMN price DECIMAL(10,2) NULL;
```

### Creating New Indexes
```sql
-- Example: Add composite index
CREATE INDEX idx_messages_conversation_sender 
ON Messages(conversation_id, sender, sent_at);
```

## 🎯 Performance Tips

1. **Use Indexes**: Đảm bảo có index cho các cột thường query
2. **Limit Results**: Luôn sử dụng LIMIT cho queries lớn
3. **Use Prepared Statements**: Tránh SQL injection và tăng performance
4. **Monitor Query Performance**: Sử dụng EXPLAIN để analyze queries
5. **Regular Maintenance**: Backup và optimize tables định kỳ

## 📚 Additional Resources

- [MySQL Documentation](https://dev.mysql.com/doc/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Database Design Best Practices](https://www.mysql.com/why-mysql/white-papers/) 