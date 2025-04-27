from flask import Flask, render_template, request, jsonify
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import create_engine, text
import json
import os
import logging
from datetime import datetime
import pandas as pd
from config import DB_CONFIG, SECRET_KEY
from flask import Flask, render_template, request, jsonify, redirect, url_for



app = Flask(__name__)

# Create SQLAlchemy engine
def get_db_engine():
    return create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}")

# Load disciplines data
with open('data/dizionario_gare.json') as f:
    DISCIPLINES = json.load(f)
with open('data/discipline_standard.json') as f:
    DISCIPLINE_STANDARD = json.load(f)
with open('data/regioni_province.json') as f:
    REGIONI_PROVINCE = json.load(f)


"""Questa è la parte per la gestione delle segnalazioni"""
# Configurazione del logging
app.config['SECRET_KEY'] = SECRET_KEY

# Inizializza CSRF protection
csrf = CSRFProtect(app)

# Restituisce l'IP con cui arriva la richiesta a nginx
def get_real_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr

# Inizializza rate limiter (usando la memoria invece di Redis)
# Questo è un limiter GLOBALE
limiter = Limiter(
    get_real_ip,
    app=app,
    #default_limits=["100 per day", "30 per hour"],
    storage_uri="memory://"
)

# Custom error handler specifically for rate limiting
@app.errorhandler(429)
def ratelimit_handler(e):
    # Determine which endpoint triggered the rate limit
    if request.path == '/api/segnala-errore':
        message = 'Limite di utilizzo superato: massimo 10 segnalazioni al minuto.'
    else:
        # Generic message for other rate-limited endpoints
        message = 'Troppe richieste. Riprova più tardi.'
    
    return jsonify({
        'success': False,
        'error': message,
    }), 429

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='segnalazioni.log'
)
logger = logging.getLogger('segnalazioni')

# Directory per salvare le segnalazioni
SEGNALAZIONI_DIR = 'segnalazioni'
os.makedirs(SEGNALAZIONI_DIR, exist_ok=True)

# Rotta per la pagina principale con il token CSRF incorporato
#@app.route('/')
#def index():
#    return render_template('index.html')

# API per ottenere il token CSRF
@app.route('/get-csrf-token', methods=['GET'])
def get_csrf_token():
    token = generate_csrf()
    return jsonify({'csrf_token': token})

# API per segnalare errori
@app.route('/api/segnala-errore', methods=['POST'])
@limiter.limit("10/minute")  # Limite di 10 richieste al minuto
def segnala_errore():
    try:
        # Ottieni i dati dalla richiesta
        dati = request.get_json()
        
        # Verifica che i dati necessari siano presenti
        required_fields = ['descrizione', 'atleta', 'prestazione']
        for field in required_fields:
            if field not in dati:
                return jsonify({'success': False, 'error': f'Campo mancante: {field}'}), 400
        
        # Aggiungi timestamp e info client
        timestamp = datetime.now().isoformat()
        dati['timestamp'] = timestamp
        
        # Ottieni l'IP reale dal forward header
        if request.headers.get('X-Forwarded-For'):
            dati['ip_client'] = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            dati['ip_client'] = request.headers.get('X-Real-IP')
        else:
            dati['ip_client'] = request.remote_addr
            
        # Aggiungi anche gli header pertinenti per debug
        dati['headers'] = {
            'X-Forwarded-For': request.headers.get('X-Forwarded-For', ''),
            'X-Real-IP': request.headers.get('X-Real-IP', ''),
            'User-Agent': request.headers.get('User-Agent', '')
        }
        
        # Crea un nome file per la segnalazione
        filename = f"{timestamp.replace(':', '-').replace('.', '-')}.json"
        filepath = os.path.join(SEGNALAZIONI_DIR, filename)
        
        # Salva i dati in un file JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)
        
        # Log dell'operazione
        logger.info(f"Nuova segnalazione ricevuta: {dati['atleta']} - {dati['prestazione']}")
        
        return jsonify({'success': True, 'message': 'Segnalazione ricevuta correttamente'}), 200
    
    except Exception as e:
        logger.error(f"Errore durante la gestione della segnalazione: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/')
def index():
    return render_template('index.html', disciplines=DISCIPLINES)


"""Da qui comincia la gestione della pagina dei rankings"""

## Invia tutte le discipline alla tab con tutti i filtri
## Per la tab "Tutti i filtri e le gare"
@app.route('/api/disciplines/all')
def get_all_disciplines():
    return jsonify(DISCIPLINES)


## Carichiamo le discipline in funzione della categoria
## Per le tab "Uomni" e "Donne"
@app.route('/api/disciplines/<category>/<gender>')
def get_disciplines(category, gender):
    disciplines = [
        d for d in DISCIPLINE_STANDARD[category] 
        if gender in d['sesso']
    ]
    return jsonify(disciplines)


## Permette a rankings.js di sapere se una disciplina ha il vento e 
## visualizzare il checkbox di conseguenza
@app.route('/api/discipline_info/<discipline>')
def get_discipline_info(discipline):
    if discipline in DISCIPLINES:
        return jsonify({
            'vento': DISCIPLINES[discipline].get('vento', 'no')
        })
    return jsonify({'error': 'Disciplina non trovata'}), 404


## Questa è quella che gestisce le query quando si preme invio
@app.route('/rankings')
@limiter.limit("50/minute")  # Limite di 50 richieste al minuto
def rankings():
    tab = request.args.get('tab', 'men')

    # Se non ci sono parametri, reindirizza alla configurazione di default
    # Se non ci sono parametri o manca la disciplina, reindirizza alla configurazione di default

    if not request.args or not request.args.get('discipline'):
        return redirect(url_for('rankings', tab=tab, discipline='110Hs_h106-9.14', ambiente='P', category='ASS'))

    if tab in ['men', 'women']:
        return handle_standard_rankings(tab)
    else:
        return handle_advanced_rankings()


## Tab "Uomini" e "Donne". Sesso è già determinato, si sceglie subito una categoria
## e le discipline possibili sono caricate a partire da DISCIPLINE_STANDARD
def handle_standard_rankings(tab):
    # Ottieni i parametri
    category = request.args.get('category', 'ASS')
    discipline = request.args.get('discipline', '100m')
    year = request.args.get('year', None)
    limit = request.args.get('limit', 50, type=int)
    show_all = request.args.get('allResults', '').lower() == 'true'
    legal_wind_only = request.args.get('legal_wind', 'true').lower() == 'true'
    page = request.args.get('page', 1, type=int)
    
    # Determina il genere da tab
    gender = 'M' if tab == 'men' else 'F'
    
    # Ottieni le categorie italiane corrispondenti
    italian_categories = CATEGORY_MAPPING[category]
    
    # Base conditions
    conditions = [
        "disciplina = :discipline",
        "sesso = :gender"
    ]
    params = {
        'discipline': discipline,
        'gender': gender
    }

    # Gestione ambiente
    ambiente = request.args.get('ambiente')
    if ambiente:
        if ambiente in ['I', 'P']:
            conditions.append("ambiente = :ambiente")
            params['ambiente'] = ambiente
        elif ambiente == 'IP':
            conditions.append("ambiente IN ('I', 'P')")

    # Aggiungi filtro categoria
    if italian_categories:
        categories_list = "', '".join(italian_categories)
        conditions.append(f"categoria IN ('{categories_list}')")

    # Aggiungi filtro anno
    if year:
        conditions.append("EXTRACT(YEAR FROM data) = :year")
        params['year'] = int(year) #pyright: ignore

    # Aggiungi filtro vento se necessario
    if legal_wind_only and should_show_wind(discipline, 'P'):
        conditions.append("""(
            ambiente = 'I' OR
            CAST(NULLIF(REPLACE(vento, ',', '.'), '') AS FLOAT) <= 2.0
        )""")

    # Costruisci la query
    where_clause = " AND ".join(conditions)

    # Esegui query per il conteggio
    engine = get_db_engine()
    if show_all:
        count_query = f"SELECT COUNT(*) FROM results WHERE {where_clause}"
    else:
        count_query = f"SELECT COUNT(DISTINCT atleta) FROM results WHERE {where_clause}"

    with engine.connect() as conn:
        total_count = pd.read_sql(text(count_query), conn, params=params).iloc[0, 0]

    # Calcola paginazione
    total_pages = (total_count + limit - 1) // limit
    offset = (page - 1) * limit
    params['limit'] = limit #pyright: ignore
    params['offset'] = offset #pyright: ignore

    # Costruisci la query principale
    sort_direction = 'ASC' if DISCIPLINES[discipline]['classifica'] == 'tempo' else 'DESC'
    
    if show_all:
        main_query = f"""
            WITH base_results AS (
                SELECT 
                    prestazione, 
                    cronometraggio,
                    atleta, 
                    anno, 
                    categoria, 
                    società, 
                    luogo, 
                    data, 
                    vento,
                    ambiente,
                    link_atleta,
                    link_società
                FROM results 
                WHERE {where_clause}
            )
            SELECT *,
                RANK() OVER (ORDER BY prestazione {sort_direction}) as position
            FROM base_results
            ORDER BY prestazione {sort_direction}, atleta ASC, data DESC
            LIMIT :limit OFFSET :offset
        """
    else:
        main_query = f"""
            WITH ranked_athletes AS (
                SELECT DISTINCT ON (atleta)
                    prestazione, 
                    cronometraggio,
                    atleta, 
                    anno, 
                    categoria, 
                    società, 
                    luogo, 
                    data, 
                    vento,
                    ambiente,
                    link_atleta,
                    link_società
                FROM results 
                WHERE {where_clause}
                ORDER BY atleta, prestazione {sort_direction}, data DESC
            )
            SELECT *,
                RANK() OVER (ORDER BY prestazione {sort_direction}) as position
            FROM ranked_athletes
            ORDER BY prestazione {sort_direction}, atleta ASC
            LIMIT :limit OFFSET :offset
        """

    # Esegui query principale
    with engine.connect() as conn:
        result = pd.read_sql(text(main_query), conn, params=params)

    return render_template(
        'rankings.html',
        results=result.to_dict('records'),
        discipline=discipline,
        discipline_info=DISCIPLINES[discipline],
        show_wind=should_show_wind(discipline, 'P'),
        current_page=page,
        total_pages=total_pages,
        limit=limit,
        total_count=total_count,
        format_time=format_time,
        show_all=show_all,
        legal_wind_only=legal_wind_only
    )


## "Tutti i filtri e le gare" tab
def handle_advanced_rankings():
    # Get all query parameters with defaults
    discipline = request.args.get('discipline', '100m')
    ambiente = request.args.get('ambiente', None)
    year = request.args.get('year', None)
    gender = request.args.get('gender', None)
    category = request.args.get('category')
    regione = request.args.get('regione', None)
    provincia_societa = request.args.get('provincia_societa', None)
    limit = request.args.get('limit', 50, type=int)
    show_all = request.args.get('allResults', '').lower() == 'true'
    legal_wind_only = request.args.get('legal_wind', 'true').lower() == 'true'  # Default to true
    page = request.args.get('page', 1, type=int)
    
    # Get properties of the discipline
    classification_type = DISCIPLINES[discipline]['classifica']
    sort_direction = 'ASC' if classification_type == 'tempo' else 'DESC'
    show_wind = should_show_wind(discipline, ambiente)

    # Base conditions for both queries, params contains the parameters for the SQL query
    conditions = ["disciplina = :discipline"]
    params = {'discipline': discipline}

    if ambiente:
        conditions.append("ambiente = :ambiente")
        params['ambiente'] = ambiente

    if year:
        conditions.append("EXTRACT(YEAR FROM data) = :year")
        params['year'] = int(year) #pyright: ignore

    if regione:
        province = REGIONI_PROVINCE[regione]
        province_list = "', '".join(province)
        conditions.append(f"LEFT(cod_società, 2) IN ('{province_list}')")
    
    if provincia_societa:

        # Provincia
        if len(provincia_societa) == 2:
            # Caso speciale Roma, provincia divisa in RM e RS
            if provincia_societa == "RM":
                conditions.append("(LEFT(cod_società, 2) = 'RM' OR LEFT(cod_società, 2) = 'RS')")
            else:
                conditions.append("LEFT(cod_società, 2) = :provincia_societa")
            params['provincia_societa'] = provincia_societa

        # Società
        elif len(provincia_societa) == 5:
            conditions.append("cod_società = :provincia_societa")
            params['provincia_societa'] = provincia_societa

    if legal_wind_only and show_wind:
        conditions.append("""(
            ambiente = 'I' OR
            CAST(NULLIF(REPLACE(vento, ',', '.'), '') AS FLOAT) <= 2.0
        )""")

    if gender:
        conditions.append("sesso = :gender")
        params['gender'] = gender

    if category:
        italian_categories = CATEGORY_MAPPING[category]
        categories_list = "', '".join(italian_categories)
        conditions.append(f"categoria IN ('{categories_list}')")

    # Join conditions
    where_clause = " AND ".join(conditions)

    # Execute count query
    engine = get_db_engine()
    if show_all:
        count_query = f"""
            SELECT COUNT(*)
            FROM results 
            WHERE {where_clause}
        """
    else:
        count_query = f"""
            SELECT COUNT(DISTINCT atleta)
            FROM results 
            WHERE {where_clause}
        """

    with engine.connect() as conn:
        total_count = pd.read_sql(text(count_query), conn, params=params).iloc[0, 0]

    # Calculate pagination
    total_pages = (total_count + limit - 1) // limit
    offset = (page - 1) * limit
    params['limit'] = limit #pyright: ignore
    params['offset'] = offset #pyright: ignore

    # Main query
    if show_all:
        main_query = f"""
            WITH base_results AS (
                SELECT 
                    prestazione, 
                    cronometraggio,
                    atleta, 
                    anno, 
                    categoria, 
                    società, 
                    luogo, 
                    data, 
                    vento,
                    ambiente,
                    link_atleta,
                    link_società
                FROM results 
                WHERE {where_clause}
            )
            SELECT *,
                RANK() OVER (ORDER BY prestazione {sort_direction}) as position
            FROM base_results
            ORDER BY prestazione {sort_direction}, atleta ASC, data DESC
            LIMIT :limit OFFSET :offset
        """
    else:
        main_query = f"""
            WITH ranked_athletes AS (
                SELECT DISTINCT ON (atleta)
                    prestazione, 
                    cronometraggio,
                    atleta, 
                    anno, 
                    categoria, 
                    società, 
                    luogo, 
                    data, 
                    vento,
                    ambiente,
                    link_atleta,
                    link_società
                FROM results 
                WHERE {where_clause}
                ORDER BY atleta, prestazione {sort_direction}, data DESC
            )
            SELECT *,
                RANK() OVER (ORDER BY prestazione {sort_direction}) as position
            FROM ranked_athletes
            ORDER BY prestazione {sort_direction}, atleta ASC
            LIMIT :limit OFFSET :offset
        """

    # Execute main query
    with engine.connect() as conn:
        result = pd.read_sql(text(main_query), conn, params=params)

    return render_template(
        'rankings.html',
        disciplines=DISCIPLINES,
        discipline=discipline,
        discipline_info=DISCIPLINES[discipline],
        results=result.to_dict('records'),
        ambiente=ambiente,
        year=year,
        regione=regione,
        provincia_societa=provincia_societa,
        sort_direction=sort_direction.lower(),
        current_page=page,
        total_pages=total_pages,
        limit=limit,
        total_count=total_count,
        min=min,
        max=max,
        show_wind=show_wind,
        legal_wind_only=legal_wind_only,
        gender=gender,
        category=category,
        format_time=format_time,
        show_all=show_all
)


#@app.route('/api/stats/<discipline>')
#def discipline_stats(discipline):
#    engine = get_db_engine()
#    ambiente = request.args.get('ambiente', 'I').split('?')[0]
#    gender = request.args.get('gender')
#    category = request.args.get('category')
#    year = request.args.get('year')
#    legal_wind_only = request.args.get('legal_wind', 'true').lower() == 'true'
#
#    classification_type = DISCIPLINES[discipline]['classifica']
#    best_function = 'MIN' if classification_type == 'tempo' else 'MAX'
#    show_wind = should_show_wind(discipline, 'P')  # Always check for outdoor wind
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


def should_show_wind(discipline, ambiente):
    # Don't show wind for indoor events
    if ambiente == 'I':
        return False
    
    # Get discipline info
    discipline_info = DISCIPLINES[discipline]
    
    # Don't show wind if discipline doesn't use it
    if discipline_info.get('vento') != 'sì':
        return False
    
    return True


def format_time(seconds, discipline_info, cronometraggio):
    """Format time based on discipline type, duration and cronometraggio"""
    tot_digits = 5
    decimal_digits = 2

    ## Prove multiple sono un punteggio
    if discipline_info['tipo'] == 'Prove Multiple':
        return f"{seconds:.0f}"

    ## To manual timings 0.24s is added in prestazione for the rankings, but we
    ## now want to display the original time with 1 decimal digit
    if cronometraggio == 'm':
        seconds -= 0.24
        decimal_digits = 1
        tot_digits = 4

    ## Anche i salti e i lanci non vogliono avere lo 0 se sono < 10
    if seconds < 10:
            return f"{seconds:0{tot_digits - 1}.{decimal_digits}f}"

    ## I tempi li mettiamo in formato MM:SS.sss altrimenti gliuis si lamenta
    if discipline_info['classifica'] == 'tempo' and seconds >= 60:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:0{tot_digits}.{decimal_digits}f}"
    return f"{seconds:0{tot_digits}.{decimal_digits}f}"


# Category mapping dictionary
CATEGORY_MAPPING = {
    'U12': ['EM', 'EF'],
    'U14': ['RM', 'RF'],
    'U16': ['CM', 'CF'],
    'U18': ['AM', 'AF'],
    'U20': ['JM', 'JF'],
    'U23': ['PM', 'PF'],
    'SEN': ['SM', 'SF'],
    'ASS': ['AM', 'AF', 'JM', 'JF', 'PM', 'PF', 'SM', 'SF']
    + [f'SM{age}' for age in range(35, 100, 5)]
    + [f'SF{age}' for age in range(35, 100, 5)]
}
# Add Masters categories (from M35 to M95)
for age in range(35, 100, 5):
    CATEGORY_MAPPING[f'M{age}'] = [f'SM{age}', f'SF{age}']




if __name__ == '__main__':
    app.run(debug=False)
