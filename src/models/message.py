from datetime import datetime
from src.models.base import db

class Message(db.Model):
    __tablename__ = 'Messages'
    
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('Conversations.conversation_id'))
    sender = db.Column(db.Enum('user', 'bot'))
    message_text = db.Column(db.Text)
    translated_text = db.Column(db.Text)
    message_type = db.Column(db.Enum('text', 'voice'))
    voice_url = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow) 