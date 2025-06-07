import openai
import os
import logging
from typing import Optional, Dict

# Initialize logger
logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        logger.info("OpenAI service initialized")
    
    def generate_title(self, message: str) -> str:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are a helpful assistant that creates concise, descriptive titles for travel-related conversations.
                    Create a short title (maximum 100 characters) that captures the main topic of the user's travel query.
                    The title should be in Vietnamese and focus on the key aspects of their travel request.
                    Examples:
                    - "Tư vấn du lịch Đà Nẵng 3 ngày 2 đêm"
                    - "Địa điểm vui chơi phù hợp gia đình tại Hà Nội"
                    - "Lịch trình khám phá Sài Gòn cuối tuần"
                    Return only the title text, no additional explanation."""},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            title = response.choices[0].message.content.strip()
            logger.info(f"Generated title: {title}")
            return title
            
        except Exception as e:
            logger.error(f"Error generating title: {str(e)}")
            return "Tư vấn du lịch"
    
    def generate_response(self, message):
        try:
            # Generate title for the conversation
            title = self.generate_title(message)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are a friendly and helpful Vietnamese travel assistant. Your role is to:
                    1. Maintain conversation context and remember information provided by users
                    2. Provide specific, actionable travel recommendations based on the information you have
                    3. Only ask for missing critical information that is absolutely necessary for making recommendations
                    4. When you have enough information, provide a detailed itinerary including:
                       - Day-by-day schedule
                       - Specific attractions and activities
                       - Estimated costs
                       - Transportation options
                       - Recommended accommodations
                       - Local tips and insights
                    5. If you need more information, ask only ONE specific question at a time
                    6. Always acknowledge the information the user has already provided
                    7. Keep responses focused and practical
                    
                    Example of good response:
                    "Dựa trên thông tin bạn đã cung cấp (3 người, ngân sách 10 triệu, thích di tích lịch sử), tôi đề xuất lịch trình 3 ngày tại TP.HCM như sau:
                    
                    Ngày 1: Khu vực trung tâm
                    - Sáng: Tham quan Dinh Độc Lập
                    - Trưa: Ăn trưa tại nhà hàng địa phương
                    - Chiều: Bảo tàng Chứng tích Chiến tranh
                    - Tối: Khám phá ẩm thực đường phố Bùi Viện
                    
                    [Tiếp tục với ngày 2 và 3...]"
                    
                    Maintain a conversational but efficient tone, focusing on providing value rather than asking unnecessary questions."""},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            logger.info("Received response from OpenAI")
            
            return {
                'text': response_text,
                'title': title
            }
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                'text': f"Xin lỗi, tôi đã gặp lỗi: {str(e)}",
                'title': "Tư vấn du lịch"
            } 