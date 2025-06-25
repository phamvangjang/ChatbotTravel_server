from flask import request
from flask_restx import Namespace, Resource, fields
from src.services.Itinerary_service import create_itinerary_with_items, get_user_itineraries, get_itinerary_by_id, delete_itinerary, update_itinerary_item

# Create namespace for itinerary API
itinerary_ns = Namespace('itinerary', description='Itinerary management operations')

# Define attraction model for nested response
attraction_model = itinerary_ns.model('Attraction', {
    'id': fields.String(description='Attraction ID'),
    'name': fields.String(description='Attraction name'),
    'address': fields.String(description='Attraction address'),
    'description': fields.String(description='Attraction description'),
    'latitude': fields.Float(description='Latitude coordinate'),
    'longitude': fields.Float(description='Longitude coordinate'),
    'category': fields.String(description='Attraction category'),
    'rating': fields.Float(description='Attraction rating'),
    'image_url': fields.String(description='Attraction image URL'),
    'language': fields.String(description='Language of the attraction'),
    'phone': fields.String(description='Attraction phone number'),
    'opening_hours': fields.String(description='Opening hours'),
    'price': fields.Float(description='Price range'),
    'tags': fields.List(fields.String, description='Attraction tags')
})

# Define itinerary item model
itinerary_item_model = itinerary_ns.model('ItineraryItem', {
    'id': fields.Integer(description='Itinerary item ID'),
    'itinerary_id': fields.Integer(description='Itinerary ID'),
    'attraction': fields.Nested(attraction_model, description='Attraction details'),
    'attraction_id': fields.String(description='Attraction ID'),
    'visit_time': fields.String(description='Visit time in ISO format'),
    'estimated_duration': fields.Integer(description='Estimated duration in minutes'),
    'notes': fields.String(description='Additional notes'),
    'order_index': fields.Integer(description='Order index in itinerary'),
    'created_at': fields.String(description='Creation time in ISO format')
})

# Define itinerary model
itinerary_model = itinerary_ns.model('Itinerary', {
    'id': fields.Integer(description='Itinerary ID'),
    'user_id': fields.Integer(description='User ID'),
    'selected_date': fields.String(description='Selected date in ISO format'),
    'title': fields.String(description='Itinerary title'),
    'notes': fields.String(description='General notes for itinerary'),
    'created_at': fields.String(description='Creation time in ISO format'),
    'updated_at': fields.String(description='Last update time in ISO format'),
    'items': fields.List(fields.Nested(itinerary_item_model), description='List of itinerary items')
})

# Define request model for creating itinerary
create_itinerary_request_model = itinerary_ns.model('CreateItineraryRequest', {
    'user_id': fields.Integer(required=True, description='User ID'),
    'selected_date': fields.String(required=True, description='Selected date in ISO format (YYYY-MM-DD)'),
    'itinerary_items': fields.List(fields.Raw, required=True, description='List of itinerary items'),
    'title': fields.String(description='Optional title for the itinerary'),
    'notes': fields.String(description='General notes for the itinerary')
})

# Define request model for updating itinerary item
update_itinerary_request_model = itinerary_ns.model('UpdateItineraryRequest', {
    'visit_time': fields.String(description='New visit time in ISO format'),
    'estimated_duration': fields.Integer(description='New estimated duration in minutes'),
    'notes': fields.String(description='New notes')
})

# Define response models
itinerary_response_model = itinerary_ns.model('ItineraryResponse', {
    'status': fields.String(description='Status of the response'),
    'message': fields.String(description='Response message'),
    'data': fields.Nested(itinerary_model, description='Itinerary data')
})

itinerary_list_response_model = itinerary_ns.model('ItineraryListResponse', {
    'status': fields.String(description='Status of the response'),
    'message': fields.String(description='Response message'),
    'data': fields.List(fields.Nested(itinerary_model), description='List of itineraries')
})

@itinerary_ns.route('/create')
class CreateItineraryResource(Resource):
    @itinerary_ns.expect(create_itinerary_request_model)
    @itinerary_ns.response(201, 'Successfully created itinerary', itinerary_response_model)
    @itinerary_ns.response(400, 'Invalid request data')
    @itinerary_ns.response(404, 'User or attraction not found')
    @itinerary_ns.response(500, 'Internal server error')
    def post(self):
        """Create a new itinerary with multiple items"""
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['user_id', 'selected_date', 'itinerary_items']
        for field in required_fields:
            if field not in data:
                return {'message': f'Missing required field: {field}'}, 400
        
        # Validate itinerary_items is a list and not empty
        if not isinstance(data['itinerary_items'], list) or len(data['itinerary_items']) == 0:
            return {'message': 'itinerary_items must be a non-empty list'}, 400
        
        # Validate each itinerary item
        for index, item in enumerate(data['itinerary_items']):
            if not isinstance(item, dict):
                return {'message': f'itinerary_items[{index}] must be an object'}, 400
            
            item_required_fields = ['attraction_id', 'visit_time']
            for field in item_required_fields:
                if field not in item:
                    return {'message': f'Missing required field: {field} in itinerary_items[{index}]'}, 400
        
        try:
            success, result = create_itinerary_with_items(
                user_id=data['user_id'],
                selected_date=data['selected_date'],
                itinerary_items=data['itinerary_items'],
                title=data.get('title'),
                notes=data.get('notes')
            )
            
            if not success:
                if "not found" in str(result):
                    return {'message': str(result)}, 404
                return {'message': str(result)}, 400
                
            return {
                'status': 'success',
                'message': 'Successfully created itinerary',
                'data': result
            }, 201
            
        except Exception as e:
            return {'message': f'Error processing request: {str(e)}'}, 500

@itinerary_ns.route('/list')
class UserItinerariesResource(Resource):
    @itinerary_ns.doc(params={
        'user_id': 'User ID (required)'
    })
    @itinerary_ns.response(200, 'Successfully retrieved itineraries', itinerary_list_response_model)
    @itinerary_ns.response(404, 'User not found')
    @itinerary_ns.response(500, 'Internal server error')
    def get(self):
        """Get all itineraries for a user"""
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return {'message': 'user_id parameter is required'}, 400
        try:
            success, result = get_user_itineraries(user_id)
            
            if not success:
                if "not found" in str(result):
                    return {'message': str(result)}, 404
                return {'message': str(result)}, 500
                
            return {
                'status': 'success',
                'message': f'Successfully retrieved itineraries for user {user_id}',
                'data': result
            }
            
        except Exception as e:
            return {'message': f'Error processing request: {str(e)}'}, 500

@itinerary_ns.route('/detail')
class ItineraryDetailResource(Resource):
    @itinerary_ns.doc(params={
        'itinerary_id': 'Itinerary ID (required)',
        'user_id': 'User ID (required for authorization)'
    })
    @itinerary_ns.response(200, 'Successfully retrieved itinerary', itinerary_response_model)
    @itinerary_ns.response(404, 'Itinerary not found')
    @itinerary_ns.response(403, 'Not authorized to view this itinerary')
    @itinerary_ns.response(500, 'Internal server error')
    def get(self):
        """Get a specific itinerary by ID"""
        itinerary_id = request.args.get('itinerary_id', type=int)
        user_id = request.args.get('user_id', type=int)
        if not itinerary_id:
            return {'message': 'itinerary_id parameter is required'}, 400
        if not user_id:
            return {'message': 'user_id parameter is required'}, 400
        try:
            success, result = get_itinerary_by_id(itinerary_id, user_id)
            if not success:
                if "not found" in str(result):
                    return {'message': str(result)}, 404
                if "not authorized" in str(result):
                    return {'message': str(result)}, 403
                return {'message': str(result)}, 500
            return {
                'status': 'success',
                'message': f'Successfully retrieved itinerary {itinerary_id}',
                'data': result
            }
        except Exception as e:
            return {'message': f'Error processing request: {str(e)}'}, 500

@itinerary_ns.route('/delete')
class ItineraryDeleteResource(Resource):
    @itinerary_ns.doc(params={
        'itinerary_id': 'Itinerary ID (required)',
        'user_id': 'User ID (required for authorization)'
    })
    @itinerary_ns.response(200, 'Successfully deleted itinerary')
    @itinerary_ns.response(404, 'Itinerary not found')
    @itinerary_ns.response(403, 'Not authorized to delete this itinerary')
    @itinerary_ns.response(500, 'Internal server error')
    def delete(self):
        """Delete an entire itinerary"""
        itinerary_id = request.args.get('itinerary_id', type=int)
        user_id = request.args.get('user_id', type=int)
        if not itinerary_id:
            return {'message': 'itinerary_id parameter is required'}, 400
        if not user_id:
            return {'message': 'user_id parameter is required'}, 400
        try:
            success, result = delete_itinerary(itinerary_id, user_id)
            if not success:
                if "not found" in str(result):
                    return {'message': str(result)}, 404
                if "not authorized" in str(result):
                    return {'message': str(result)}, 403
                return {'message': str(result)}, 500
            return {
                'status': 'success',
                'message': result
            }
        except Exception as e:
            return {'message': f'Error processing request: {str(e)}'}, 500

@itinerary_ns.route('/item/<int:item_id>/update')
class UpdateItineraryItemResource(Resource):
    @itinerary_ns.expect(update_itinerary_request_model)
    @itinerary_ns.response(200, 'Successfully updated itinerary item', itinerary_response_model)
    @itinerary_ns.response(400, 'Invalid request data')
    @itinerary_ns.response(404, 'Itinerary item not found')
    @itinerary_ns.response(403, 'Not authorized to update this item')
    @itinerary_ns.response(500, 'Internal server error')
    def put(self, item_id):
        """Update a specific itinerary item"""
        data = request.get_json()
        user_id = request.args.get('user_id', type=int)
        
        if not user_id:
            return {'message': 'user_id parameter is required'}, 400
        
        try:
            success, result = update_itinerary_item(
                item_id=item_id,
                user_id=user_id,
                visit_time=data.get('visit_time'),
                estimated_duration=data.get('estimated_duration'),
                notes=data.get('notes')
            )
            
            if not success:
                if "not found" in str(result):
                    return {'message': str(result)}, 404
                if "not authorized" in str(result):
                    return {'message': str(result)}, 403
                return {'message': str(result)}, 400
                
            return {
                'status': 'success',
                'message': 'Successfully updated itinerary item',
                'data': result
            }
            
        except Exception as e:
            return {'message': f'Error processing request: {str(e)}'}, 500
