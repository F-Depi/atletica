import json
import os
from datetime import datetime
from flask import jsonify, request
from flask_wtf.csrf import generate_csrf
from app.routes import api_bp


# Load disciplines data
with open('data/dizionario_gare.json') as f:
    DISCIPLINES = json.load(f)
with open('data/discipline_standard.json') as f:
    DISCIPLINE_STANDARD = json.load(f)
with open('data/category_mapping.json') as f:
    CATEGORY_MAPPING = json.load(f)


# Directory for saving reports
SEGNALAZIONI_DIR = 'segnalazioni'


@api_bp.route('/disciplines/all')
def get_all_disciplines():
    """API endpoint to send all disciplines for the 'all filters' tab"""
    return jsonify(DISCIPLINES)


@api_bp.route('/disciplines/<category>/<gender>')
def get_disciplines(category, gender):
    """API endpoint to load disciplines based on category, for 'Men' and 'Women' tabs"""
    disciplines = [
        d for d in DISCIPLINE_STANDARD[category] 
        if gender in d['sesso']
    ]
    return jsonify(disciplines)


@api_bp.route('/discipline_info/<discipline>')
def get_discipline_info(discipline):
    """API endpoint to allow rankings.js to know if a discipline has wind"""
    if discipline in DISCIPLINES:
        return jsonify({
            'vento': DISCIPLINES[discipline].get('vento', 'no')
        })
    return jsonify({'error': 'Disciplina non trovata'}), 404


#@api_bp.route('/stats/<discipline>')
#def discipline_stats(discipline):
#    """API endpoint for discipline statistics"""
#    engine = get_db_engine()
#    ambiente = request.args.get('ambiente', 'I').split('?')[0]
#    gender = request.args.get('gender')
#    category = request.args.get('category')
#    year = request.args.get('year')
#    legal_wind_only = request.args.get('legal_wind', 'true').lower() == 'true'
#
#    classification_type = DISCIPLINES[discipline]['classifica']
#    best_function = 'MIN' if classification_type == 'tempo' else 'MAX'
#    show_wind = should_show_wind(discipline, 'P', DISCIPLINES)  # Always check for outdoor wind
#    
#    query = f"""
#        SELECT 
#            {best_function}(prestazione) as best,
#            AVG(prestazione) as average,
#            COUNT(DISTINCT atleta) as athletes,
#            COUNT(*) as performances
#        FROM results 
#        WHERE disciplina = :discipline
#    """
#
#    params = {
#        'discipline': discipline
#    }
#
#    # Only add ambiente condition if not 'ALL'
#    if ambiente != 'ALL':
#        query += " AND ambiente = :ambiente"
#        params['ambiente'] = ambiente
#
#    if year:
#        query += " AND EXTRACT(YEAR FROM data) = :year"
#        params['year'] = int(year)
#
#    if gender:
#        query += """ 
#        AND sesso = :gender
#        """
#        params['gender'] = gender
#
#    if category:
#        italian_categories = [k for k, v in CATEGORY_MAPPING.items() if v == category]
#        if italian_categories:
#            categories_list = "', '".join(italian_categories)
#            query += f" AND categoria IN ('{categories_list}')"
#
#    if legal_wind_only and show_wind:
#        query += """ 
#        AND (
#            ambiente = 'I' OR
#            CAST(NULLIF(REPLACE(vento, ',', '.'), '') AS FLOAT) <= 2.0
#        )
#        """
#
#    with engine.connect() as conn:
#        result = pd.read_sql(
#            text(query), 
#            conn,
#            params=params
#        )
#    
#    return jsonify(result.to_dict('records')[0])


@api_bp.route('/get-csrf-token', methods=['GET'])
def get_csrf_token():
    """API to get CSRF token"""
    token = generate_csrf()
    return jsonify({'csrf_token': token})


@api_bp.route('/segnala-errore', methods=['POST'])
def segnala_errore():
    """API to report errors"""
    try:
        # Get data from request
        dati = request.get_json()
        
        # Verify required fields are present
        required_fields = ['descrizione', 'atleta', 'prestazione']
        for field in required_fields:
            if field not in dati:
                return jsonify({'success': False,
                                'error': f'Campo mancante: {field}'}), 400
        
        # Add timestamp and client info
        timestamp = datetime.now().isoformat()
        dati['timestamp'] = timestamp
        dati['ip_client'] = request.remote_addr
        
        # Create filename for the report
        filename = f"{timestamp.replace(':', '-').replace('.', '-')}.json"
        filepath = os.path.join(SEGNALAZIONI_DIR, filename)
        
        # Save data to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message':
                        'Segnalazione ricevuta correttamente'}), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
