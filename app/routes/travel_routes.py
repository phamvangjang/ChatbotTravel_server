from flask import request
from flask_restx import Namespace, Resource, fields
from ..services.travel_assistant import travel_assistant
from ..services.speech_service import speech_service
from werkzeug.datastructures import FileStorage
import logging

logger = logging.getLogger(__name__)

api = Namespace('travel', description='Travel recommendation operations')

# Request models
location_model = api.model('Location', {
    'latitude': fields.Float(required=True, description='Latitude coordinate'),
    'longitude': fields.Float(required=True, description='Longitude coordinate')
})

travel_query_model = api.model('TravelQuery', {
    'query': fields.String(required=True, description='Natural language travel query'),
    'user_id': fields.String(required=True, description='User identifier'),
    'user_location': fields.Nested(location_model, required=False, description='User\'s current location'),
    'lang': fields.String(required=False, default='vi', description='Response language (default: vi)')
})

# Audio upload parser
audio_parser = api.parser()
audio_parser.add_argument('audio', type=FileStorage, location='files', required=True, help='Audio file (MP3, WAV, M4A)')
audio_parser.add_argument('user_id', type=str, required=True, help='User ID')
audio_parser.add_argument('user_location', type=dict, required=False, help='User location')
audio_parser.add_argument('lang', type=str, required=False, default='vi', help='Response language (vi/en/zh/ko)')

# Response models
activity_model = api.model('Activity', {
    'time': fields.String(description='Activity time'),
    'name': fields.String(description='Activity name'),
    'description': fields.String(description='Activity description'),
    'location': fields.Raw(description='Location information'),
    'estimated_cost': fields.Float(description='Estimated cost')
})

day_model = api.model('Day', {
    'day': fields.Integer(description='Day number'),
    'activities': fields.List(fields.Nested(activity_model), description='Activities for the day')
})

itinerary_model = api.model('Itinerary', {
    'itinerary': fields.List(fields.Nested(day_model), description='Daily activities'),
    'tips': fields.List(fields.String, description='Travel tips'),
    'transportation': fields.String(description='Transportation information'),
    'total_cost': fields.Float(description='Total estimated cost'),
    'map_url': fields.String(description='URL to static map')
})

error_model = api.model('Error', {
    'error': fields.String(description='Error message')
})

@api.route('/ask')
class TravelQuery(Resource):
    @api.expect(travel_query_model)
    @api.doc('ask_travel_question',
             responses={
                 200: 'Success',
                 400: 'Invalid input',
                 500: 'Internal server error'
             })
    def post(self):
        """Process a natural language travel query"""
        try:
            logger.info("Received travel query request")
            data = request.get_json()
            logger.debug(f"Request data: {data}")
            
            # Validate required fields
            if not data:
                logger.error("No data provided in request")
                return {'error': 'No data provided'}, 400
                
            if 'query' not in data:
                logger.error("Missing 'query' field in request")
                return {'error': 'Query is required'}, 400
                
            if 'user_id' not in data:
                logger.error("Missing 'user_id' field in request")
                return {'error': 'User ID is required'}, 400
            
            # Extract parameters
            query = data.get('query')
            user_id = data.get('user_id')
            user_location = data.get('user_location')
            lang = data.get('lang', 'vi')
            
            logger.info(f"Processing query: {query}")
            logger.debug(f"User ID: {user_id}, Language: {lang}")
            if user_location:
                logger.debug(f"User location: {user_location}")
            
            # Check if travel assistant is initialized
            if travel_assistant is None:
                logger.error("Travel assistant not initialized")
                return {'error': 'Service not available'}, 500
            
            # Process query
            result = travel_assistant.process_travel_query(
                query=query,
                user_id=user_id,
                user_location=user_location,
                lang=lang
            )
            
            if 'error' in result:
                logger.error(f"Error processing query: {result['error']}")
                return result, 500
                
            logger.info("Query processed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in travel query endpoint: {str(e)}", exc_info=True)
            return {'error': f'Internal server error: {str(e)}'}, 500

@api.route('/ask/voice')
class VoiceTravelQuery(Resource):
    @api.expect(audio_parser)
    @api.response(200, 'Success', itinerary_model)
    @api.response(400, 'Error', error_model)
    def post(self):
        """Process a voice query and return travel recommendations"""
        args = audio_parser.parse_args()
        audio_file = args['audio']
        
        try:
            # Convert speech to text
            text = speech_service.convert_speech_to_text(audio_file)
            if not text:
                return {'error': 'Failed to convert speech to text'}, 400
                
            # Process the text query
            result = travel_assistant.process_travel_query(
                query=text,
                user_id=args['user_id'],
                user_location=args.get('user_location'),
                lang=args.get('lang', 'vi')
            )
            return result
            
        except Exception as e:
            return {'error': str(e)}, 400 