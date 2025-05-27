from datetime import datetime
from src.models import Conversation, Message, ItinerarySuggestion, ItineraryActivity
from src.models.base import db

class TravelAssistant:
    def process_message(self, message, conversation_id, mapbox_service, language_detector, openai_service, crawler):
        # Get or create conversation
        if conversation_id:
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                return {'error': 'Conversation not found'}, 404
        else:
            conversation = Conversation(
                started_at=datetime.utcnow(),
                source_language=language_detector.detect_language(message)
            )
            db.session.add(conversation)
            db.session.commit()
        
        # Save user message
        user_message = Message(
            conversation_id=conversation.conversation_id,
            sender='user',
            message_text=message,
            message_type='text'
        )
        db.session.add(user_message)
        
        # Generate response using OpenAI
        response = openai_service.generate_response(message)
        
        # Save bot response
        bot_message = Message(
            conversation_id=conversation.conversation_id,
            sender='bot',
            message_text=response['text'],
            message_type='text'
        )
        db.session.add(bot_message)
        
        # If response includes itinerary, save it
        itinerary = None
        if 'itinerary' in response:
            itinerary_data = response['itinerary']
            if itinerary_data is not None:
                itinerary = ItinerarySuggestion(
                    conversation_id=conversation.conversation_id,
                    destination=itinerary_data['destination'],
                    total_days=itinerary_data['total_days'],
                    estimated_cost=itinerary_data['estimated_cost'],
                    mapbox_link=mapbox_service.generate_map_link(itinerary_data['locations'])
                )
                db.session.add(itinerary)
                db.session.flush()  # Get itinerary_id
                
                # Save activities
                for activity in itinerary_data['activities']:
                    itinerary_activity = ItineraryActivity(
                        itinerary_id=itinerary.itinerary_id,
                        day_number=activity['day'],
                        activity_title=activity['title'],
                        description=activity['description'],
                        location_name=activity['location'],
                        map_url=mapbox_service.generate_map_link(activity['location']),
                        start_time=activity['start_time'],
                        end_time=activity['end_time']
                    )
                    db.session.add(itinerary_activity)
        
        db.session.commit()
        
        return {
            'conversation_id': conversation.conversation_id,
            'message': {
                'id': bot_message.message_id,
                'sender': bot_message.sender,
                'text': bot_message.message_text,
                'type': bot_message.message_type,
                'sent_at': bot_message.sent_at.isoformat()
            },
            'itinerary': {
                'id': itinerary.itinerary_id if itinerary else None,
                'destination': itinerary.destination if itinerary else None,
                'total_days': itinerary.total_days if itinerary else None,
                'estimated_cost': float(itinerary.estimated_cost) if itinerary else None,
                'mapbox_link': itinerary.mapbox_link if itinerary else None,
                'activities': [{
                    'id': act.activity_id,
                    'day': act.day_number,
                    'title': act.activity_title,
                    'description': act.description,
                    'location': act.location_name,
                    'map_url': act.map_url,
                    'start_time': str(act.start_time),
                    'end_time': str(act.end_time)
                } for act in itinerary.activities] if itinerary else []
            }
        } 