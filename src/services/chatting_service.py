from datetime import datetime
from src.models.conversation import Conversation
from src.models.message import Message
from src.services.ai.openai_service import OpenAIService
from src import db
from datetime import datetime, timezone

def create_conversation(user_id: int, source_language: str = 'en', started_at: datetime = None):
    """
    Create a new conversation for a user
    
    Args:
        user_id (int): ID of the user
        source_language (str): Source language for the conversation
        started_at (datetime): Start time of the conversation
        
    Returns:
        tuple: (success: bool, result: dict or str)
    """
    try:
        if started_at is None:
            started_at = datetime.utcnow()
            
        new_conversation = Conversation(
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
            "ended_at": new_conversation.ended_at.isoformat() if new_conversation.ended_at else None
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
            "ended_at": conv.ended_at.isoformat() if conv.ended_at else None
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
            "content": msg.message_text,
            "role": msg.sender,
            "created_at": msg.sent_at.isoformat() if msg.sent_at else None
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
        db.session.commit()
        db.session.refresh(new_message)
        
        # If message is from user, get AI response
        if sender == "user":
            try:
                # Initialize OpenAI service
                openai_service = OpenAIService()
                
                # Get AI response
                ai_response = openai_service.generate_response(message_text)
                
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
            "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None
        }
    except Exception as e:
        db.session.rollback()
        return False, str(e) 