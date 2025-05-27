from datetime import datetime
from src.models.base import db

class Conversation(db.Model):
    __tablename__ = 'Conversations'
    
    conversation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    source_language = db.Column(db.String(10))
    
    messages = db.relationship('Message', backref='conversation', lazy=True)
    itinerary_suggestions = db.relationship('ItinerarySuggestion', backref='conversation', lazy=True) 