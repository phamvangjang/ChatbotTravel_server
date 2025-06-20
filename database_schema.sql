-- ScapeData Database Schema
-- Tạo database và các bảng cho dự án ScapeData

-- Tạo database
CREATE DATABASE IF NOT EXISTS scapedata 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE scapedata;

-- 1. Bảng Users
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    language_preference VARCHAR(10) DEFAULT 'vi',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE,
    
    INDEX idx_users_email (email),
    INDEX idx_users_created_at (created_at),
    
    CONSTRAINT chk_email_format CHECK (email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$')
);

-- 2. Bảng OTP
CREATE TABLE OTP (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL,
    otp_code VARCHAR(6) NOT NULL,
    purpose VARCHAR(20) NOT NULL, -- 'register' or 'reset_password'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    
    INDEX idx_otp_email (email),
    INDEX idx_otp_expires_at (expires_at)
);

-- 3. Bảng Conversations
CREATE TABLE Conversations (
    conversation_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME NULL,
    source_language VARCHAR(10) NOT NULL,
    title VARCHAR(100) NULL,
    
    INDEX idx_conversations_user_id (user_id),
    INDEX idx_conversations_started_at (started_at),
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- 4. Bảng Messages
CREATE TABLE Messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT,
    sender ENUM('user', 'bot') NOT NULL,
    message_text TEXT NOT NULL,
    translated_text TEXT NULL,
    message_type ENUM('text', 'voice') DEFAULT 'text',
    voice_url TEXT NULL,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_messages_conversation_id (conversation_id),
    INDEX idx_messages_sent_at (sent_at),
    INDEX idx_messages_sender (sender),
    
    FOREIGN KEY (conversation_id) REFERENCES Conversations(conversation_id) ON DELETE CASCADE
);

-- 5. Bảng Attractions
CREATE TABLE Attractions (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(500) NOT NULL,
    description TEXT NULL,
    image_url VARCHAR(500) NULL,
    rating FLOAT DEFAULT 0.0,
    latitude FLOAT NULL,
    longitude FLOAT NULL,
    category VARCHAR(100) NULL,
    tags JSON NULL,
    price FLOAT NULL,
    opening_hours VARCHAR(200) NULL,
    phone_number VARCHAR(20) NULL,
    website VARCHAR(500) NULL,
    aliases JSON NULL,
    
    INDEX idx_attractions_category (category),
    INDEX idx_attractions_rating (rating),
    INDEX idx_attractions_location (latitude, longitude),
    
    CONSTRAINT chk_rating_range CHECK (rating >= 0 AND rating <= 5)
);

-- 6. Bảng ItineraryItems
CREATE TABLE ItineraryItems (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    attraction_id VARCHAR(50) NOT NULL,
    visit_time DATETIME NOT NULL,
    estimated_duration INT NULL, -- Duration in minutes
    notes TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_itinerary_items_user_id (user_id),
    INDEX idx_itinerary_items_attraction_id (attraction_id),
    INDEX idx_itinerary_items_visit_time (visit_time),
    INDEX idx_itinerary_items_user_visit_time (user_id, visit_time),
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (attraction_id) REFERENCES Attractions(id) ON DELETE CASCADE,
    CONSTRAINT chk_duration_positive CHECK (estimated_duration > 0)
);

-- Tạo các views hữu ích

-- View: User Conversation Summary
CREATE VIEW UserConversationSummary AS
SELECT 
    u.user_id,
    u.full_name,
    u.email,
    COUNT(c.conversation_id) as total_conversations,
    COUNT(m.message_id) as total_messages,
    MAX(c.started_at) as last_conversation_date
FROM Users u
LEFT JOIN Conversations c ON u.user_id = c.user_id
LEFT JOIN Messages m ON c.conversation_id = m.conversation_id
GROUP BY u.user_id, u.full_name, u.email;

-- View: Attraction Statistics
CREATE VIEW AttractionStatistics AS
SELECT 
    a.id,
    a.name,
    a.category,
    a.rating,
    COUNT(ii.id) as times_included_in_itinerary,
    AVG(ii.estimated_duration) as avg_visit_duration
FROM Attractions a
LEFT JOIN ItineraryItems ii ON a.id = ii.attraction_id
GROUP BY a.id, a.name, a.category, a.rating;

-- View: Popular Attractions
CREATE VIEW PopularAttractions AS
SELECT 
    a.id,
    a.name,
    a.category,
    a.rating,
    COUNT(ii.id) as inclusion_count
FROM Attractions a
LEFT JOIN ItineraryItems ii ON a.id = ii.attraction_id
GROUP BY a.id, a.name, a.category, a.rating
ORDER BY inclusion_count DESC, a.rating DESC;

-- View: User Itinerary Summary
CREATE VIEW UserItinerarySummary AS
SELECT 
    u.user_id,
    u.full_name,
    u.email,
    COUNT(ii.id) as total_itinerary_items,
    COUNT(DISTINCT a.id) as unique_attractions_visited,
    AVG(ii.estimated_duration) as avg_visit_duration,
    MAX(ii.visit_time) as last_visit_date
FROM Users u
LEFT JOIN ItineraryItems ii ON u.user_id = ii.user_id
LEFT JOIN Attractions a ON ii.attraction_id = a.id
GROUP BY u.user_id, u.full_name, u.email;

-- Insert sample data cho testing

-- Sample Users
INSERT INTO Users (full_name, email, password_hash, language_preference, is_verified) VALUES
('Nguyễn Văn A', 'nguyenvana@example.com', '$2b$12$hashedpassword1', 'vi', TRUE),
('Trần Thị B', 'tranthib@example.com', '$2b$12$hashedpassword2', 'en', TRUE),
('Lê Văn C', 'levanc@example.com', '$2b$12$hashedpassword3', 'vi', FALSE);

-- Sample Attractions
INSERT INTO Attractions (id, name, address, description, rating, latitude, longitude, category, tags, price) VALUES
('attr_001', 'Chùa Một Cột', 'Đội Cấn, Ba Đình, Hà Nội', 'Ngôi chùa có kiến trúc độc đáo hình hoa sen', 4.5, 21.0354, 105.8344, 'Di tích lịch sử', '["chùa", "kiến trúc", "lịch sử"]', 0),
('attr_002', 'Phở Gà', '123 Nguyễn Huệ, Quận 1, TP.HCM', 'Nhà hàng phở gà nổi tiếng', 4.2, 10.7769, 106.7009, 'Nhà hàng', '["phở", "ẩm thực", "việt nam"]', 50000),
('attr_003', 'Bảo tàng Dân tộc học', 'Nguyễn Văn Huyên, Cầu Giấy, Hà Nội', 'Bảo tàng về văn hóa các dân tộc Việt Nam', 4.7, 21.0387, 105.7994, 'Bảo tàng', '["văn hóa", "dân tộc", "giáo dục"]', 40000);

-- Sample Conversations
INSERT INTO Conversations (user_id, source_language, title) VALUES
(1, 'vi', 'Tư vấn du lịch Hà Nội'),
(2, 'en', 'Travel advice for Ho Chi Minh City'),
(1, 'vi', 'Đặt lịch trình 3 ngày');

-- Sample Messages
INSERT INTO Messages (conversation_id, sender, message_text, translated_text) VALUES
(1, 'user', 'Tôi muốn đi du lịch Hà Nội 3 ngày', 'I want to travel to Hanoi for 3 days'),
(1, 'bot', 'Tôi sẽ giúp bạn lập lịch trình du lịch Hà Nội 3 ngày', 'I will help you plan a 3-day Hanoi itinerary'),
(2, 'user', 'What are the best attractions in Ho Chi Minh City?', 'Đâu là những điểm du lịch tốt nhất ở TP.HCM?'),
(2, 'bot', 'Here are the top attractions in Ho Chi Minh City', 'Đây là những điểm du lịch hàng đầu ở TP.HCM');

-- Sample ItineraryItems
INSERT INTO ItineraryItems (user_id, attraction_id, visit_time, estimated_duration, notes) VALUES
(1, 'attr_001', '2024-01-15 09:00:00', 60, 'Thăm chùa vào buổi sáng'),
(1, 'attr_003', '2024-01-15 14:00:00', 120, 'Tham quan bảo tàng vào buổi chiều'),
(1, 'attr_002', '2024-01-15 12:00:00', 45, 'Ăn trưa tại nhà hàng phở'),
(2, 'attr_002', '2024-01-16 18:00:00', 60, 'Ăn tối tại nhà hàng phở');

-- Tạo stored procedures hữu ích

DELIMITER //

-- Procedure: Get User Conversations
CREATE PROCEDURE GetUserConversations(IN user_id_param INT)
BEGIN
    SELECT 
        c.conversation_id,
        c.title,
        c.started_at,
        c.ended_at,
        c.source_language,
        COUNT(m.message_id) as message_count
    FROM Conversations c
    LEFT JOIN Messages m ON c.conversation_id = m.conversation_id
    WHERE c.user_id = user_id_param
    GROUP BY c.conversation_id, c.title, c.started_at, c.ended_at, c.source_language
    ORDER BY c.started_at DESC;
END //

-- Procedure: Get User Itinerary
CREATE PROCEDURE GetUserItinerary(IN user_id_param INT)
BEGIN
    SELECT 
        ii.id,
        ii.visit_time,
        ii.estimated_duration,
        ii.notes,
        a.id as attraction_id,
        a.name as attraction_name,
        a.address,
        a.description,
        a.rating,
        a.category,
        a.price
    FROM ItineraryItems ii
    JOIN Attractions a ON ii.attraction_id = a.id
    WHERE ii.user_id = user_id_param
    ORDER BY ii.visit_time ASC;
END //

-- Procedure: Get Attractions by Category
CREATE PROCEDURE GetAttractionsByCategory(IN category_param VARCHAR(100))
BEGIN
    SELECT 
        id,
        name,
        address,
        description,
        rating,
        latitude,
        longitude,
        price,
        tags
    FROM Attractions
    WHERE category = category_param
    ORDER BY rating DESC, name ASC;
END //

-- Procedure: Search Attractions
CREATE PROCEDURE SearchAttractions(IN search_term VARCHAR(255))
BEGIN
    SELECT 
        id,
        name,
        address,
        description,
        rating,
        category,
        price,
        tags
    FROM Attractions
    WHERE 
        name LIKE CONCAT('%', search_term, '%') OR
        description LIKE CONCAT('%', search_term, '%') OR
        JSON_SEARCH(tags, 'one', search_term) IS NOT NULL OR
        JSON_SEARCH(aliases, 'one', search_term) IS NOT NULL
    ORDER BY rating DESC, name ASC;
END //

DELIMITER ;

-- Tạo triggers

-- Trigger: Update conversation ended_at when last message is sent
DELIMITER //
CREATE TRIGGER UpdateConversationEndTime
AFTER INSERT ON Messages
FOR EACH ROW
BEGIN
    UPDATE Conversations 
    SET ended_at = NEW.sent_at 
    WHERE conversation_id = NEW.conversation_id;
END //
DELIMITER ;

-- Trigger: Clean up expired OTP records
DELIMITER //
CREATE EVENT CleanupExpiredOTP
ON SCHEDULE EVERY 1 HOUR
DO
BEGIN
    DELETE FROM OTP WHERE expires_at < NOW();
END //
DELIMITER ;

-- Tạo user và phân quyền (cho production)
-- CREATE USER 'scapedata_user'@'localhost' IDENTIFIED BY 'strong_password_here';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON scapedata.* TO 'scapedata_user'@'localhost';
-- FLUSH PRIVILEGES;

-- Hiển thị thông tin database
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'scapedata'
ORDER BY TABLE_NAME; 