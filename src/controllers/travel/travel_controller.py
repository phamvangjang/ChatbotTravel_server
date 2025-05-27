from flask_restx import Resource, Namespace, fields, reqparse
from src.services.travel.travel_assistant import TravelAssistant
from src.services.ai.mapbox_service import MapboxService
from src.services.ai.language_detector import LanguageDetector
from src.services.ai.openai_service import OpenAIService
from src.services.external.vnexpress_crawler import VnExpressCrawler
from src.services.ai.speech_service import SpeechService
from src.models import Conversation, Message, ItinerarySuggestion, ItineraryActivity
from src.models.base import db
from datetime import datetime

# Create namespace
api = Namespace('travel', description='Travel recommendation operations')

# Define models for Swagger documentation
message_model = api.model('Message', {
    'message_id': fields.Integer(description='Message ID'),
    'conversation_id': fields.Integer(description='Conversation ID'),
    'sender': fields.String(description='Message sender (user/bot)'),
    'message_text': fields.String(description='Message text'),
    'translated_text': fields.String(description='Translated text'),
    'message_type': fields.String(description='Message type (text/voice)'),
    'voice_url': fields.String(description='Voice message URL'),
    'sent_at': fields.DateTime(description='Message sent time')
})

itinerary_activity_model = api.model('ItineraryActivity', {
    'activity_id': fields.Integer(description='Activity ID'),
    'itinerary_id': fields.Integer(description='Itinerary ID'),
    'day_number': fields.Integer(description='Day number'),
    'activity_title': fields.String(description='Activity title'),
    'description': fields.String(description='Activity description'),
    'location_name': fields.String(description='Location name'),
    'map_url': fields.String(description='Map URL'),
    'start_time': fields.String(description='Start time'),
    'end_time': fields.String(description='End time')
})

itinerary_model = api.model('ItinerarySuggestion', {
    'itinerary_id': fields.Integer(description='Itinerary ID'),
    'conversation_id': fields.Integer(description='Conversation ID'),
    'destination': fields.String(description='Destination'),
    'total_days': fields.Integer(description='Total days'),
    'estimated_cost': fields.Float(description='Estimated cost'),
    'mapbox_link': fields.String(description='Mapbox link'),
    'created_at': fields.DateTime(description='Created time'),
    'activities': fields.List(fields.Nested(itinerary_activity_model))
})

chat_request_model = api.model('ChatRequest', {
    'message': fields.String(required=True, description='User message'),
    'conversation_id': fields.Integer(description='Existing conversation ID')
})

chat_response_model = api.model('ChatResponse', {
    'conversation_id': fields.Integer(description='Conversation ID'),
    'message': fields.Nested(message_model),
    'itinerary': fields.Nested(itinerary_model)
})

error_model = api.model('Error', {
    'error': fields.String(description='Error message')
})

# Create request parser for voice query
audio_parser = reqparse.RequestParser()
audio_parser.add_argument('audio', type=reqparse.FileStorage, location='files', required=True, help='Audio file')
audio_parser.add_argument('user_id', type=int, required=True, help='User ID')
audio_parser.add_argument('user_location', type=str, help='User location')
audio_parser.add_argument('lang', type=str, default='vi', help='Language code')

@api.route('/chat')
class Chat(Resource):
    @api.expect(chat_request_model)
    @api.response(200, 'Success', chat_response_model)
    def post(self):
        data = api.payload
        message = data.get('message')
        conversation_id = data.get('conversation_id')
        
        # Initialize services
        travel_assistant = TravelAssistant()
        mapbox_service = MapboxService()
        language_detector = LanguageDetector()
        openai_service = OpenAIService()
        crawler = VnExpressCrawler()
        
        # Process message and generate response
        response = travel_assistant.process_message(
            message=message,
            conversation_id=conversation_id,
            mapbox_service=mapbox_service,
            language_detector=language_detector,
            openai_service=openai_service,
            crawler=crawler
        )
        
        return response

@api.route('/ask/voice')
class VoiceTravelQuery(Resource):
    @api.expect(audio_parser)
    @api.response(200, 'Success', chat_response_model)
    @api.response(400, 'Error', error_model)
    def post(self):
        """Process a voice query and return travel recommendations"""
        args = audio_parser.parse_args()
        audio_file = args['audio']
        
        try:
            # Initialize services
            speech_service = SpeechService()
            travel_assistant = TravelAssistant()
            mapbox_service = MapboxService()
            language_detector = LanguageDetector()
            openai_service = OpenAIService()
            crawler = VnExpressCrawler()
            
            # Convert speech to text
            text = speech_service.convert_speech_to_text(audio_file)
            if not text:
                return {'error': 'Failed to convert speech to text'}, 400
            
            # Process the text query
            response = travel_assistant.process_message(
                message=text,
                conversation_id=None,  # Create new conversation for voice query
                mapbox_service=mapbox_service,
                language_detector=language_detector,
                openai_service=openai_service,
                crawler=crawler
            )
            
            return response
            
        except Exception as e:
            return {'error': str(e)}, 400

@api.route('/conversations/<int:conversation_id>')
class ConversationHistory(Resource):
    @api.response(200, 'Success')
    def get(self, conversation_id):
        conversation = Conversation.query.get_or_404(conversation_id)
        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.sent_at).all()
        itineraries = ItinerarySuggestion.query.filter_by(conversation_id=conversation_id).all()
        
        return {
            'conversation': {
                'id': conversation.conversation_id,
                'started_at': conversation.started_at,
                'ended_at': conversation.ended_at,
                'source_language': conversation.source_language
            },
            'messages': [{
                'id': msg.message_id,
                'sender': msg.sender,
                'text': msg.message_text,
                'translated_text': msg.translated_text,
                'type': msg.message_type,
                'voice_url': msg.voice_url,
                'sent_at': msg.sent_at
            } for msg in messages],
            'itineraries': [{
                'id': itin.itinerary_id,
                'destination': itin.destination,
                'total_days': itin.total_days,
                'estimated_cost': float(itin.estimated_cost),
                'mapbox_link': itin.mapbox_link,
                'activities': [{
                    'id': act.activity_id,
                    'day': act.day_number,
                    'title': act.activity_title,
                    'description': act.description,
                    'location': act.location_name,
                    'map_url': act.map_url,
                    'start_time': str(act.start_time),
                    'end_time': str(act.end_time)
                } for act in itin.activities]
            } for itin in itineraries]
        } 