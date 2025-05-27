from datetime import datetime
from src.models.base import db

class ItinerarySuggestion(db.Model):
    __tablename__ = 'ItinerarySuggestions'
    
    itinerary_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('Conversations.conversation_id'))
    destination = db.Column(db.String(100))
    total_days = db.Column(db.Integer)
    estimated_cost = db.Column(db.Numeric(10, 2))
    mapbox_link = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    activities = db.relationship('ItineraryActivity', backref='itinerary', lazy=True)

class ItineraryActivity(db.Model):
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