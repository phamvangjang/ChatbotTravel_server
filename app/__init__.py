from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from .routes.travel_routes import api as travel_ns
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
mail = Mail()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Configure API
    api = Api(
        title='Travel Assistant API',
        version='1.0',
        description='A travel recommendation system for Vietnamese destinations',
        doc='/docs'
    )
    
    # Add namespaces
    api.add_namespace(travel_ns, path='/api/travel')
    from app.auth.routes import auth_ns
    api.add_namespace(auth_ns, path='/api/auth')
    
    # Initialize app
    app.config['RESTX_VALIDATE'] = True
    app.config['RESTX_MASK_SWAGGER'] = False
    app.config['ERROR_404_HELP'] = False
    
    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Email configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Register API
    api.init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app 