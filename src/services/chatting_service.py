from datetime import datetime
import re
from src.models.conversation import Conversation
from src.models.message import Message
from src.services.ai.openai_service import OpenAIService
from src.services.travel_chatbot_service import (
    detect_language,
    get_language_info,
    extract_user_intent_and_features,
    combined_search_with_filters,
    create_chatbot_response
)
from src import db
from datetime import datetime, timezone

def is_travel_related_question(question: str) -> bool:
    """
    Kiểm tra xem câu hỏi có liên quan đến du lịch hay không
    
    Args:
        question (str): Câu hỏi của người dùng
        
    Returns:
        bool: True nếu câu hỏi liên quan đến du lịch
    """
    # Chuyển về chữ thường để dễ so sánh
    question_lower = question.lower()
    
    # Từ khóa liên quan đến du lịch
    travel_keywords = [
        # Địa điểm du lịch
        'địa điểm', 'địa danh', 'nơi', 'chỗ', 'khu vực', 'quận', 'huyện', 'phường',
        'place', 'location', 'area', 'district', 'ward', 'attraction', 'destination',
        '景点', '地方', '区域', '地区', '場所', 'エリア', '지역', '장소',
        
        # Hoạt động du lịch
        'du lịch', 'thăm quan', 'khám phá', 'đi chơi', 'nghỉ dưỡng', 'ăn uống',
        'travel', 'visit', 'explore', 'tour', 'vacation', 'restaurant', 'food',
        '旅游', '参观', '探索', '游玩', '度假', '餐厅', '美食',
        '旅行', '観光', '探索', '遊び', '休暇', 'レストラン', '料理',
        '여행', '관광', '탐험', '놀기', '휴가', '레스토랑', '음식',
        
        # Loại địa điểm
        'nhà hàng', 'khách sạn', 'cafe', 'quán ăn', 'chợ', 'trung tâm thương mại',
        'restaurant', 'hotel', 'cafe', 'market', 'mall', 'shopping center',
        '餐厅', '酒店', '咖啡', '市场', '购物中心',
        'レストラン', 'ホテル', 'カフェ', '市場', 'ショッピングセンター',
        '레스토랑', '호텔', '카페', '시장', '쇼핑센터',
        
        # Địa danh cụ thể ở HCM
        'bến thành', 'landmark', 'bùi viện', 'nguyễn huệ', 'đồng khởi',
        'ben thanh', 'landmark 81', 'bui vien', 'nguyen hue', 'dong khoi',
        
        # Từ khóa tìm kiếm
        'ở đâu', 'đi đâu', 'tìm', 'kiếm', 'where', 'find', 'search',
        '哪里', '找', '搜索', 'どこ', '探す', '검색', '찾다'
    ]
    
    # Kiểm tra xem có từ khóa du lịch nào trong câu hỏi không
    for keyword in travel_keywords:
        if keyword in question_lower:
            return True
    
    # Kiểm tra các pattern đặc biệt
    travel_patterns = [
        r'\b(địa điểm|nơi|chỗ)\s+(nào|đẹp|ngon|vui|thú vị)',
        r'\b(restaurant|hotel|cafe|market|mall)\b',
        r'\b(đi|đến|thăm|khám phá)\s+',
        r'\b(where|visit|travel|tour)\b',
        r'\b(餐厅|酒店|咖啡|市场|购物)\b',
        r'\b(レストラン|ホテル|カフェ|市場|ショッピング)\b',
        r'\b(레스토랑|호텔|카페|시장|쇼핑)\b'
    ]
    
    for pattern in travel_patterns:
        if re.search(pattern, question_lower):
            return True
    
    return False

def process_travel_question(question: str) -> dict:
    """
    Xử lý câu hỏi du lịch sử dụng travel chatbot service
    
    Args:
        question (str): Câu hỏi của người dùng
        
    Returns:
        dict: Kết quả xử lý với response và metadata
    """
    try:
        # Bước 1: Nhận biết ngôn ngữ
        language_result = detect_language(question)
        
        # Kiểm tra ngôn ngữ có được hỗ trợ không
        if not language_result.get('is_supported', False):
            lang_info = get_language_info('unknown')
            return {
                'success': False,
                'response': lang_info['unsupported_message'],
                'error': 'Unsupported language'
            }
        
        detected_language = language_result.get('language', 'vietnamese')
        lang_info = get_language_info(detected_language)
        
        # Bước 2: Trích xuất thực thể và ý định
        extraction_result = extract_user_intent_and_features(question)
        
        # Bước 3: Thực hiện tìm kiếm kết hợp với bộ lọc
        search_result = combined_search_with_filters(
            question=question,
            extracted_features=extraction_result.get('extracted_features', {}),
            n_results=8
        )
        
        # Kiểm tra kết quả tìm kiếm
        if search_result.get('status') == 'error' or search_result.get('success') == False:
            return {
                'success': False,
                'response': f"Xin lỗi, {search_result.get('message', 'Không tìm thấy thông tin phù hợp')}",
                'error': search_result.get('message', 'Search failed')
            }
        
        # Format kết quả tìm kiếm
        formatted_results = []
        for result in search_result['results']:
            metadata = result.get('metadata', {})
            distance = result.get('distance', 0)
            
            # Tính similarity score từ distance
            similarity = 1 / (1 + distance) if distance > 0 else 0
            
            # Xác định ngôn ngữ của kết quả
            result_language = 'unknown'
            if metadata.get('mo_ta'):
                mo_ta = metadata.get('mo_ta', '')
                # Kiểm tra ngôn ngữ dựa trên ký tự
                if any(char in mo_ta for char in ['は', 'が', 'を', 'に', 'へ', 'で', 'から', 'まで', 'の', 'と', 'や', 'も']):
                    result_language = 'japanese'
                elif any(char in mo_ta for char in ['은', '는', '이', '가', '을', '를', '의', '에', '에서', '로', '으로', '와', '과']):
                    result_language = 'korean'
                elif any(char in mo_ta for char in ['的', '是', '在', '有', '和', '与', '或', '但', '因为', '所以', '如果', '虽然']):
                    result_language = 'chinese'
                elif any(char in mo_ta for char in ['à', 'á', 'ạ', 'ả', 'ã', 'â', 'ầ', 'ấ', 'ậ', 'ẩ', 'ẫ', 'ă', 'ằ', 'ắ', 'ặ', 'ẳ', 'ẵ', 'è', 'é', 'ẹ', 'ẻ', 'ẽ', 'ê', 'ề', 'ế', 'ệ', 'ể', 'ễ', 'ì', 'í', 'ị', 'ỉ', 'ĩ', 'ò', 'ó', 'ọ', 'ỏ', 'õ', 'ô', 'ồ', 'ố', 'ộ', 'ổ', 'ỗ', 'ơ', 'ờ', 'ớ', 'ợ', 'ở', 'ỡ', 'ù', 'ú', 'ụ', 'ủ', 'ũ', 'ư', 'ừ', 'ứ', 'ự', 'ử', 'ữ', 'ỳ', 'ý', 'ỵ', 'ỷ', 'ỹ', 'đ']):
                    result_language = 'vietnamese'
                else:
                    result_language = 'english'
            
            # Ưu tiên kết quả cùng ngôn ngữ với câu hỏi
            language_boost = 0.3 if result_language == detected_language else 0.0
            adjusted_similarity = min(similarity + language_boost, 1.0)
            
            formatted_result = {
                'id': result.get('id', ''),
                'ten_dia_diem': metadata.get('ten_dia_diem', ''),
                'mo_ta': metadata.get('mo_ta', ''),
                'loai_dia_diem': metadata.get('loai_dia_diem', ''),
                'khu_vuc': metadata.get('khu_vuc', ''),
                'dia_chi': metadata.get('dia_chi', ''),
                'similarity': round(adjusted_similarity, 3),
                'language': result_language
            }
            formatted_results.append(formatted_result)
        
        # Sắp xếp kết quả theo similarity và ưu tiên ngôn ngữ
        formatted_results.sort(key=lambda x: (x['similarity'], x['language'] == detected_language), reverse=True)
        
        # Chỉ giữ lại kết quả có similarity > 0.1
        formatted_results = [r for r in formatted_results if r['similarity'] > 0.1]
        
        # Ưu tiên kết quả cùng ngôn ngữ với câu hỏi
        same_language_results = [r for r in formatted_results if r['language'] == detected_language]
        other_language_results = [r for r in formatted_results if r['language'] != detected_language]
        
        if len(same_language_results) >= 3:
            formatted_results = same_language_results[:8]
        else:
            formatted_results = same_language_results + other_language_results[:8-len(same_language_results)]
        
        # Bước 4: Tạo câu trả lời tự nhiên cho chatbot
        chatbot_response = create_chatbot_response(
            question=question,
            search_results=formatted_results,
            extracted_features=extraction_result.get('extracted_features', {}),
            language=detected_language
        )
        
        return {
            'success': True,
            'response': chatbot_response.get('response', ''),
            'language': detected_language,
            'language_name': lang_info['name'],
            'search_results': formatted_results,
            'suggested_activities': chatbot_response.get('suggested_activities', []),
            'follow_up_questions': chatbot_response.get('follow_up_questions', []),
            'extracted_features': extraction_result.get('extracted_features', {}),
            'search_method': search_result.get('search_method', 'unknown')
        }
        
    except Exception as e:
        return {
            'success': False,
            'response': f'Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi du lịch: {str(e)}',
            'error': str(e)
        }

def create_conversation(user_id: int, source_language: str = 'en', started_at: datetime = None, title: str = None):
    """
    Create a new conversation for a user
    
    Args:
        user_id (int): ID of the user
        source_language (str): Source language for the conversation
        started_at (datetime): Start time of the conversation
        title (str): Title of the conversation
    Returns:
        tuple: (success: bool, result: dict or str)
    """
    try:
        if started_at is None:
            started_at = datetime.utcnow()
            
        new_conversation = Conversation(
            title=title,
            user_id=user_id,
            source_language=source_language,
            started_at=started_at,
            ended_at=None
        )
        
        db.session.add(new_conversation)
        db.session.commit()
        db.session.refresh(new_conversation)
        
        return True, {
            "conversation_id": new_conversation.conversation_id,
            "user_id": new_conversation.user_id,
            "source_language": new_conversation.source_language,
            "started_at": new_conversation.started_at.isoformat() if new_conversation.started_at else None,
            "ended_at": new_conversation.ended_at.isoformat() if new_conversation.ended_at else None,
            "title": new_conversation.title
        }
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def get_user_conversations(user_id: int):
    """
    Get all conversations for a specific user
    
    Args:
        user_id (int): ID of the user
        
    Returns:
        tuple: (success: bool, result: list or str)
    """
    try:
        conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.started_at.desc()).all()
        
        return True, [{
            "conversation_id": conv.conversation_id,
            "user_id": conv.user_id,
            "source_language": conv.source_language,
            "started_at": conv.started_at.isoformat() if conv.started_at else None,
            "ended_at": conv.ended_at.isoformat() if conv.ended_at else None,
            "title": conv.title
        } for conv in conversations]
    except Exception as e:
        return False, str(e)

def get_conversation_messages(conversation_id: int):
    """
    Get all messages for a specific conversation
    
    Args:
        conversation_id (int): ID of the conversation
        
    Returns:
        tuple: (success: bool, result: list or str)
    """
    try:
        # Check if conversation exists
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return False, "Conversation not found"
            
        # Get messages ordered by created_at
        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.sent_at.asc()).all()
        
        return True, [{
            "message_id": msg.message_id,
            "conversation_id": msg.conversation_id,
            "message_text": msg.message_text,
            "sender": msg.sender,
            "sent_at": msg.sent_at.isoformat() if msg.sent_at else None
        } for msg in messages]
    except Exception as e:
        return False, str(e)

def save_message(conversation_id: int, sender: str, message_text: str, translated_text: str = None, 
                message_type: str = 'text', voice_url: str = None):
    """
    Save a new message to the database and get AI response if message is from user
    
    Args:
        conversation_id (int): ID of the conversation
        sender (str): Sender of the message (bot or user)
        message_text (str): Content of the message
        translated_text (str, optional): Translated text of the message
        message_type (str, optional): Type of the message (default: text)
        voice_url (str, optional): URL of the voice message if any
        
    Returns:
        tuple: (success: bool, result: dict or str)
    """
    try:
        # Check if conversation exists
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return False, "Conversation not found"
            
        # print(f"Current conversation title: {conversation.title}")
            
        # Create new message
        new_message = Message(
            conversation_id=conversation_id,
            sender=sender,
            message_text=message_text,
            translated_text=translated_text,
            message_type=message_type,
            voice_url=voice_url,
            sent_at=datetime.now(timezone.utc)
        )
        
        db.session.add(new_message)
        
        # If message is from user, get AI response
        if sender == "user":
            try:
                # Initialize OpenAI service
                openai_service = OpenAIService()
                
                # Get AI response
                ai_response = openai_service.generate_response(message_text)
                # print(f"AI generated title: {ai_response['title']}")
                
                # Check if conversation needs a title
                if conversation.title is None or conversation.title.strip() == "":
                    conversation.title = ai_response['title']
                    # print(f"Setting new conversation title: {conversation.title}")
                    # Commit title update separately
                    db.session.commit()
                    db.session.refresh(conversation)
                # else:
                #     # print(f"Conversation already has title: {conversation.title}")
                
                # Save AI response as a new message
                bot_message = Message(
                    conversation_id=conversation_id,
                    sender="bot",
                    message_text=ai_response['text'],
                    message_type='text',
                    sent_at=datetime.now(timezone.utc)
                )
                
                db.session.add(bot_message)
                db.session.commit()
                db.session.refresh(new_message)
                db.session.refresh(bot_message)
                
                # Return both messages
                return True, {
                    "user_message": {
                        "message_id": new_message.message_id,
                        "conversation_id": new_message.conversation_id,
                        "sender": new_message.sender,
                        "message_text": new_message.message_text,
                        "translated_text": new_message.translated_text,
                        "message_type": new_message.message_type,
                        "voice_url": new_message.voice_url,
                        "sent_at": new_message.sent_at.isoformat() if new_message.sent_at else None
                    },
                    "bot_message": {
                        "message_id": bot_message.message_id,
                        "conversation_id": bot_message.conversation_id,
                        "sender": bot_message.sender,
                        "message_text": bot_message.message_text,
                        "message_type": bot_message.message_type,
                        "sent_at": bot_message.sent_at.isoformat() if bot_message.sent_at else None
                    },
                }
            except Exception as e:
                # If AI response fails, still return the user message
                db.session.commit()
                db.session.refresh(new_message)
                return True, {
                    "user_message": {
                        "message_id": new_message.message_id,
                        "conversation_id": new_message.conversation_id,
                        "sender": new_message.sender,
                        "message_text": new_message.message_text,
                        "translated_text": new_message.translated_text,
                        "message_type": new_message.message_type,
                        "voice_url": new_message.voice_url,
                        "sent_at": new_message.sent_at.isoformat() if new_message.sent_at else None
                    },
                    "error": f"Failed to get AI response: {str(e)}"
                }
        
        # If message is from bot, just return the message
        db.session.commit()
        db.session.refresh(new_message)
        return True, {
            "message_id": new_message.message_id,
            "conversation_id": new_message.conversation_id,
            "sender": new_message.sender,
            "message_text": new_message.message_text,
            "translated_text": new_message.translated_text,
            "message_type": new_message.message_type,
            "voice_url": new_message.voice_url,
            "sent_at": new_message.sent_at.isoformat() if new_message.sent_at else None
        }
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def save_message_update(conversation_id: int, sender: str, message_text: str, translated_text: str = None, 
                message_type: str = 'text', voice_url: str = None):
    """
    Save a new message update to the database and get AI response if message is from user
    
    Args:
        conversation_id (int): ID of the conversation
        sender (str): Sender of the message (bot or user)
        message_text (str): Content of the message
        translated_text (str, optional): Translated text of the message
        message_type (str, optional): Type of the message (default: text)
        voice_url (str, optional): URL of the voice message if any
        
    Returns:
        tuple: (success: bool, result: dict or str)
    """
    try:
        # Check if conversation exists
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return False, "Conversation not found"
            
        # print(f"Current conversation title: {conversation.title}")
            
        # Create new message
        new_message = Message(
            conversation_id=conversation_id,
            sender=sender,
            message_text=message_text,
            translated_text=translated_text,
            message_type=message_type,
            voice_url=voice_url,
            sent_at=datetime.now(timezone.utc)
        )
        
        db.session.add(new_message)
        
        # If message is from user, get AI response
        if sender == "user":
            try:
                # Kiểm tra xem câu hỏi có liên quan đến du lịch không
                if is_travel_related_question(message_text):
                    print("✅ Câu hỏi liên quan đến du lịch")
                    # Thử xử lý câu hỏi du lịch
                    travel_result = process_travel_question(message_text)
                    
                    if travel_result['success']:
                        # Nếu xử lý du lịch thành công, sử dụng kết quả đó
                        print(f"✅ xử lý du lịch thành công")
                        ai_response_text = travel_result['response']
                        
                        # Tạo title từ kết quả du lịch nếu có
                        if travel_result.get('search_results'):
                            first_result = travel_result['search_results'][0]
                            ai_response_title = f"Tư vấn du lịch: {first_result.get('ten_dia_diem', 'Địa điểm')}"
                        else:
                            ai_response_title = "Tư vấn du lịch"
                    else:
                        # Nếu xử lý du lịch thất bại, fallback về OpenAI
                        print("❌ xử lý du lịch thất bại")
                        openai_service = OpenAIService()
                        ai_response = openai_service.generate_response(message_text)
                        ai_response_text = ai_response['text']
                        ai_response_title = ai_response['title']
                        travel_result = {'success': False}
                else:
                    print("✅ Câu hỏi không liên quan đến du lịch")
                    # Nếu không phải câu hỏi du lịch, sử dụng OpenAI service
                    openai_service = OpenAIService()
                    ai_response = openai_service.generate_response(message_text)
                    ai_response_text = ai_response['text']
                    ai_response_title = ai_response['title']
                    travel_result = {'success': False}
                
                # Check if conversation needs a title
                if conversation.title is None or conversation.title.strip() == "":
                    conversation.title = ai_response_title if 'ai_response_title' in locals() else "Cuộc trò chuyện mới"
                    # Commit title update separately
                    db.session.commit()
                    db.session.refresh(conversation)
                
                # Save AI response as a new message
                bot_message = Message(
                    conversation_id=conversation_id,
                    sender="bot",
                    message_text=ai_response_text,
                    message_type='text',
                    sent_at=datetime.now(timezone.utc)
                )
                
                db.session.add(bot_message)
                db.session.commit()
                db.session.refresh(new_message)
                db.session.refresh(bot_message)
                
                # Return both messages
                return True, {
                    "user_message": {
                        "message_id": new_message.message_id,
                        "conversation_id": new_message.conversation_id,
                        "sender": new_message.sender,
                        "message_text": new_message.message_text,
                        "translated_text": new_message.translated_text,
                        "message_type": new_message.message_type,
                        "voice_url": new_message.voice_url,
                        "sent_at": new_message.sent_at.isoformat() if new_message.sent_at else None
                    },
                    "bot_message": {
                        "message_id": bot_message.message_id,
                        "conversation_id": bot_message.conversation_id,
                        "sender": bot_message.sender,
                        "message_text": bot_message.message_text,
                        "message_type": bot_message.message_type,
                        "sent_at": bot_message.sent_at.isoformat() if bot_message.sent_at else None
                    },
                    "travel_data": travel_result if travel_result.get('success') else None
                }
            except Exception as e:
                # If AI response fails, still return the user message
                db.session.commit()
                db.session.refresh(new_message)
                return True, {
                    "user_message": {
                        "message_id": new_message.message_id,
                        "conversation_id": new_message.conversation_id,
                        "sender": new_message.sender,
                        "message_text": new_message.message_text,
                        "translated_text": new_message.translated_text,
                        "message_type": new_message.message_type,
                        "voice_url": new_message.voice_url,
                        "sent_at": new_message.sent_at.isoformat() if new_message.sent_at else None
                    },
                    "error": f"Failed to get AI response: {str(e)}"
                }
        
        # If message is from bot, just return the message
        db.session.commit()
        db.session.refresh(new_message)
        return True, {
            "message_id": new_message.message_id,
            "conversation_id": new_message.conversation_id,
            "sender": new_message.sender,
            "message_text": new_message.message_text,
            "translated_text": new_message.translated_text,
            "message_type": new_message.message_type,
            "voice_url": new_message.voice_url,
            "sent_at": new_message.sent_at.isoformat() if new_message.sent_at else None
        }
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def end_conversation(conversation_id: int):
    """
    End a conversation by setting its ended_at timestamp
    
    Args:
        conversation_id (int): ID of the conversation to end
        
    Returns:
        tuple: (success: bool, result: dict or str)
    """
    try:
        # Check if conversation exists
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return False, "Conversation not found"
            
        # Check if conversation is already ended
        if conversation.ended_at is not None:
            return False, "Conversation is already ended"
            
        # Set ended_at to current time
        conversation.ended_at = datetime.utcnow()
        db.session.commit()
        
        return True, {
            "conversation_id": conversation.conversation_id,
            "user_id": conversation.user_id,
            "source_language": conversation.source_language,
            "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
            "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
            "title": conversation.title
        }
    except Exception as e:
        db.session.rollback()
        return False, str(e) 