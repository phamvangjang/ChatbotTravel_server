from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from flask_mail import Mail
from src.models.base import db
from src.config.config import Config

mail = Mail()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Configure API
    api = Api(
        title='Travel Assistant API',
        version='1.0',
        description='A travel recommendation system for Vietnamese destinations',
        doc='/docs'
    )
    
    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    
    # Register API
    api.init_app(app)
    
    # Add namespaces
    from src.controllers.auth_controller import auth_ns
    from src.controllers.chatting_controller import chatting_ns
    from src.controllers.nlp_controller import nlp_ns
    
    api.add_namespace(auth_ns, path='/api/auth')
    api.add_namespace(chatting_ns, path='/api/chatting')
    api.add_namespace(nlp_ns, path='/api/nlp')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app 