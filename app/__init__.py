from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from .routes.travel_routes import api as travel_ns

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
    
    # Initialize app
    app.config['RESTX_VALIDATE'] = True
    app.config['RESTX_MASK_SWAGGER'] = False
    app.config['ERROR_404_HELP'] = False
    
    # Register API
    api.init_app(app)
    
    return app 