from flask import Blueprint, request, jsonify
from flask_wtf.csrf import generate_csrf
from flask_limiter import Limiter
import json
import os
from datetime import datetime
import logging

from app.app import app


# Create blueprint
error_reporting_bp = Blueprint('error_reporting', __name__)

# Configure error reporting logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='segnalazioni.log'
)
logger = logging.getLogger('segnalazioni')


# Restituisce l'IP con cui arriva la richiesta a nginx
def get_real_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr


# Inizializza rate limiter, questo è un limiter GLOBALE, salva i dati in memoria
limiter = Limiter(
    get_real_ip,
    app=app,
    #default_limits=["100 per day", "30 per hour"],
    storage_uri="memory://"
)


# Directory to save error reports
SEGNALAZIONI_DIR = 'segnalazioni'
os.makedirs(SEGNALAZIONI_DIR, exist_ok=True)


@error_reporting_bp.route('/get-csrf-token', methods=['GET'])
def get_csrf_token():
    token = generate_csrf()
    return jsonify({'csrf_token': token})


@error_reporting_bp.route('/api/segnala-errore', methods=['POST'])
@limiter.limit("5/minute")  # Limit to 5 requests per minute
def segnala_errore():
    try:
        # Get data from request
        dati = request.get_json()
        
        # Verify required fields are present
        required_fields = ['descrizione', 'atleta', 'prestazione']
        for field in required_fields:
            if field not in dati:
                return jsonify({'success': False, 'error': f'Campo mancante: {field}'}), 400
        
        # Add timestamp and client info
        timestamp = datetime.now().isoformat()
        dati['timestamp'] = timestamp
        
        # Get real IP from forward header
        if request.headers.get('X-Forwarded-For'):
            dati['ip_client'] = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            dati['ip_client'] = request.headers.get('X-Real-IP')
        else:
            dati['ip_client'] = request.remote_addr
            
        # Add relevant headers for debugging
        dati['headers'] = {
            'X-Forwarded-For': request.headers.get('X-Forwarded-For', ''),
            'X-Real-IP': request.headers.get('X-Real-IP', ''),
            'User-Agent': request.headers.get('User-Agent', '')
        }
        
        # Create filename for error report
        filename = f"{timestamp.replace(':', '-').replace('.', '-')}.json"
        filepath = os.path.join(SEGNALAZIONI_DIR, filename)
        
        # Save data to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)
        
        # Log operation
        logger.info(f"Nuova segnalazione ricevuta: {dati['atleta']} - {dati['prestazione']}")
        
        return jsonify({'success': True, 'message': 'Segnalazione ricevuta correttamente'}), 200
    
    except Exception as e:
        logger.error(f"Errore durante la gestione della segnalazione: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

