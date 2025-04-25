from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os
from config import SECRET_KEY

def create_app():
    app = Flask(__name__)
    
    # Configure the app
    app.config['SECRET_KEY'] = SECRET_KEY
    
    # Initialize extensions
    csrf = CSRFProtect(app)
    
    # Initialize rate limiter
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["100 per day", "30 per hour"],
        storage_uri="memory://"
    )

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='segnalazioni.log'
    )
    
    # Create directory for reports
    SEGNALAZIONI_DIR = 'segnalazioni'
    os.makedirs(SEGNALAZIONI_DIR, exist_ok=True)
    
    # Load blueprints
    from app.routes import main_bp, rankings_bp, api_bp, statistics_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(rankings_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(statistics_bp)
    
    return app
