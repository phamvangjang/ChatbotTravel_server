from flask import Blueprint, request, jsonify
from app.services.question_handler import QuestionHandler

question_bp = Blueprint('questions', __name__)
question_handler = QuestionHandler()

@question_bp.route('/ask', methods=['POST'])
def ask_question():
    """Handle travel-related questions"""
    data = request.get_json()
    
    if not data or 'question' not in data:
        return jsonify({
            'error': 'Missing question in request'
        }), 400
        
    question = data['question']
    answer = question_handler.answer_question(question)
    
    return jsonify({
        'question': question,
        'answer': answer
    })

@question_bp.route('/locations', methods=['GET'])
def get_locations():
    """Get list of available locations"""
    from app.models.sample_data import SAMPLE_LOCATIONS
    
    locations = []
    for name, data in SAMPLE_LOCATIONS.items():
        locations.append({
            'name': name,
            'region': data['region'],
            'categories': data['categories'],
            'description': data['description']
        })
        
    return jsonify({
        'locations': locations
    }) 