from flask import Flask, render_template
from flask_restx import Api
from flask_cors import CORS
from .routes.travel_routes import api as travel_ns
import os
from dotenv import load_dotenv
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5500", "http://127.0.0.1:5500"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Accept"]
        }
    })
    
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
    
    # Add error handlers
    @app.errorhandler(Exception)
    def handle_error(error):
        logger.error(f"Unhandled error: {str(error)}", exc_info=True)
        return {'error': str(error)}, 500
    
    # Add route for HTML interface
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app

if __name__ == '__main__':
    # Check required environment variables
    required_vars = ['OPENAI_API_KEY', 'MAPBOX_ACCESS_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error("Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"- {var}")
        logger.error("\nPlease set these variables in your .env file")
        exit(1)
        
    app = create_app()
    logger.info("Starting Travel Assistant API...")
    app.run(debug=True, host='0.0.0.0', port=5000) 