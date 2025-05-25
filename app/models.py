from app import db
from datetime import datetime

class Users(db.Model):
    __tablename__ = 'Users'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(255))
    language_preference = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    
    conversations = db.relationship('Conversations', backref='user', lazy=True)

class OTP(db.Model):
    __tablename__ = 'OTP'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100))
    otp_code = db.Column(db.String(6))
    purpose = db.Column(db.String(20))  # 'register' or 'reset_password'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    is_used = db.Column(db.Boolean, default=False)

class Conversations(db.Model):
    __tablename__ = 'Conversations'
    
    conversation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    source_language = db.Column(db.String(10))
    
    messages = db.relationship('Messages', backref='conversation', lazy=True)
    itinerary_suggestions = db.relationship('ItinerarySuggestions', backref='conversation', lazy=True)

class Messages(db.Model):
    __tablename__ = 'Messages'
    
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('Conversations.conversation_id'))
    sender = db.Column(db.Enum('user', 'bot'))
    message_text = db.Column(db.Text)
    translated_text = db.Column(db.Text)
    message_type = db.Column(db.Enum('text', 'voice'))
    voice_url = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

class ItinerarySuggestions(db.Model):
    __tablename__ = 'ItinerarySuggestions'
    
    itinerary_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('Conversations.conversation_id'))
    destination = db.Column(db.String(100))
    total_days = db.Column(db.Integer)
    estimated_cost = db.Column(db.Numeric(10, 2))
    mapbox_link = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    activities = db.relationship('ItineraryActivities', backref='itinerary', lazy=True)

class ItineraryActivities(db.Model):
    __tablename__ = 'ItineraryActivities'
    
    activity_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    itinerary_id = db.Column(db.Integer, db.ForeignKey('ItinerarySuggestions.itinerary_id'))
    day_number = db.Column(db.Integer)
    activity_title = db.Column(db.String(255))
    description = db.Column(db.Text)
    location_name = db.Column(db.String(255))
    map_url = db.Column(db.Text)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time) 