from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
import logging
import json
import os

from config import SECRET_KEY


# Initialize Flask app
app = Flask(__name__)


"""Questa è la parte per la gestione delle segnalazioni"""
app.config['SECRET_KEY'] = SECRET_KEY

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger('athletics')



# Custom error handler specifically for rate limiting
@app.errorhandler(429)
def ratelimit_handler(e):
    # Determine which endpoint triggered the rate limit
    if request.path == '/api/segnala-errore':
        message = 'Limite di utilizzo superato: massimo 5 segnalazioni al minuto.'
    else:
        # Generic message for other rate-limited endpoints
        message = 'Troppe richieste. Riprova più tardi.'
    
    return jsonify({
        'success': False,
        'error': message,
    }), 429


""" Load disciplines data """
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(f'{BASE_DIR}/data/dizionario_gare.json') as f:
    DISCIPLINES = json.load(f)
with open(f'{BASE_DIR}/data/discipline_standard.json') as f:
    DISCIPLINE_STANDARD = json.load(f)
with open(f'{BASE_DIR}/data/regioni_province.json') as f:
    REGIONI_PROVINCE = json.load(f)
with open(f'{BASE_DIR}/data/category_mapping.json') as f:
    CATEGORY_MAPPING = json.load(f)


# Main route
@app.route('/')
def index():
    return render_template('index.html', disciplines=DISCIPLINES)


""" Register blueprints """
from app.rankings import rankings_bp
from app.error_reporting import error_reporting_bp
from app.atleti import atleti_bp
app.register_blueprint(rankings_bp)
app.register_blueprint(error_reporting_bp)
app.register_blueprint(atleti_bp)


if __name__ == '__main__':
    app.run(debug=False)

