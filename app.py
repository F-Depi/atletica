from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, text
import json
import pandas as pd
from config import DB_CONFIG
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

@app.route('/')
def index():
    return render_template('index.html', disciplines=DISCIPLINES)


## Invia tutte le discipline alla tab con tutti i filtri
## Per la tab "Tutti i filtri e le gare"
@app.route('/api/disciplines/all')
def get_all_disciplines():
    return jsonify(DISCIPLINES)


## Carichiamo le discipline in funzione della categoria
## Per le tab "Uomni" e "Donne"
@app.route('/api/disciplines/<category>/<gender>')
def get_disciplines(category, gender):
    try:
        disciplines = [
            d for d in DISCIPLINE_STANDARD[category] 
            if gender in d['sesso']
        ]
        return jsonify(disciplines)

    except Exception as e:
        app.logger.error(f"Error loading disciplines: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


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
def rankings():
    tab = request.args.get('tab', 'men')
    
    if tab in ['men', 'women']:
        # Gestione modalità standard
        return handle_standard_rankings(tab)
    else:
        # Gestione modalità avanzata
        return handle_advanced_rankings()


## Tab "Uomini" e "Donne". Sesso è già determinato, si sceglie subito una categoria
## e le discipline possibili sono caricate a partire da DISCIPLINE_STANDARD
def handle_standard_rankings(tab):
    # Ottieni i parametri
    category = request.args.get('category', 'Assoluti')
    discipline = request.args.get('discipline', '100m')
    year = request.args.get('year', None)
    limit = request.args.get('limit', 50, type=int)
    show_all = request.args.get('allResults', '').lower() == 'true'
    legal_wind_only = request.args.get('legal_wind', 'true').lower() == 'true'
    page = request.args.get('page', 1, type=int)
    
    # Determina il genere da tab
    gender = 'M' if tab == 'men' else 'F'
    
    # Ottieni le categorie italiane corrispondenti
    italian_categories = [k for k, v in CATEGORY_MAPPING.items() if v == category]
    print(f"italian_categories: {italian_categories}")
    
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
        params['year'] = int(year)

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
    params['limit'] = limit
    params['offset'] = offset

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
    ambiente = request.args.get('ambiente', 'P')
    year = request.args.get('year', None)
    gender = request.args.get('gender', None)
    category = request.args.get('category')
    limit = request.args.get('limit', 50, type=int)
    show_all = request.args.get('allResults', '').lower() == 'true'
    legal_wind_only = request.args.get('legal_wind', 'true').lower() == 'true'
    page = request.args.get('page', 1, type=int)
    
    # Get properties of the discipline
    classification_type = DISCIPLINES[discipline]['classifica']
    sort_direction = 'ASC' if classification_type == 'tempo' else 'DESC'
    show_wind = should_show_wind(discipline, ambiente)

    # Base conditions for both queries
    conditions = ["disciplina = :discipline"]
    params = {
        'discipline': discipline
    }

    if ambiente != 'ALL':
        conditions.append("ambiente = :ambiente")
        params['ambiente'] = ambiente

    if year:
        conditions.append("EXTRACT(YEAR FROM data) = :year")
        params['year'] = int(year)

    if legal_wind_only and show_wind:
        conditions.append("""(
            ambiente = 'I' OR
            CAST(NULLIF(REPLACE(vento, ',', '.'), '') AS FLOAT) <= 2.0
        )""")
        params['legal_wind'] = legal_wind_only

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
    params['limit'] = limit
    params['offset'] = offset

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


@app.route('/api/stats/<discipline>')
def discipline_stats(discipline):
    engine = get_db_engine()
    ambiente = request.args.get('ambiente', 'I').split('?')[0]
    gender = request.args.get('gender')
    category = request.args.get('category')
    year = request.args.get('year')
    legal_wind_only = request.args.get('legal_wind', 'true').lower() == 'true'

    classification_type = DISCIPLINES[discipline]['classifica']
    best_function = 'MIN' if classification_type == 'tempo' else 'MAX'
    show_wind = should_show_wind(discipline, 'P')  # Always check for outdoor wind
    
    query = f"""
        SELECT 
            {best_function}(prestazione) as best,
            AVG(prestazione) as average,
            COUNT(DISTINCT atleta) as athletes,
            COUNT(*) as performances
        FROM results 
        WHERE disciplina = :discipline
    """

    params = {
        'discipline': discipline
    }

    # Only add ambiente condition if not 'ALL'
    if ambiente != 'ALL':
        query += " AND ambiente = :ambiente"
        params['ambiente'] = ambiente

    if year:
        query += " AND EXTRACT(YEAR FROM data) = :year"
        params['year'] = int(year)

    if gender:
        query += """ 
        AND sesso = :gender
        """
        params['gender'] = gender

    if category:
        italian_categories = [k for k, v in CATEGORY_MAPPING.items() if v == category]
        if italian_categories:
            categories_list = "', '".join(italian_categories)
            query += f" AND categoria IN ('{categories_list}')"

    if legal_wind_only and show_wind:
        query += """ 
        AND (
            ambiente = 'I' OR
            CAST(NULLIF(REPLACE(vento, ',', '.'), '') AS FLOAT) <= 2.0
        )
        """

    with engine.connect() as conn:
        result = pd.read_sql(
            text(query), 
            conn,
            params=params
        )
    
    return jsonify(result.to_dict('records')[0])


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

    ## To manual timings 0.24s is added in prestazione for the rankings, but we
    ## now want to display the original time with 1 decimal digit
    if cronometraggio == 'm':
        seconds -= 0.24
        decimal_digits = 1
        tot_digits = 4
    if discipline_info['classifica'] == 'tempo' and seconds < 10:
            return f"{seconds:0{tot_digits - 1}.{decimal_digits}f}"
    if discipline_info['classifica'] == 'tempo' and seconds >= 60:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:0{tot_digits}.{decimal_digits}f}"
    return f"{seconds:0{tot_digits}.{decimal_digits}f}"


# Category mapping dictionary
CATEGORY_MAPPING = {
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
    app.run(debug=True)



#ORDERED_CATEGORIES = [
#    # Youth categories
#    'U14', 'U16', 'U18', 'U20',
#    # Under 23
#    'U23',
#    # Senior
#    'SEN',
#    # Masters (from M35 to M95)
#] + [f'M{age}' for age in range(35, 100, 5)]



#def get_categories(discipline, ambiente):
#    engine = get_db_engine()
#    
#    # Modify query based on ambiente
#    if ambiente == 'ALL':
#        query = """
#            SELECT DISTINCT categoria 
#            FROM results 
#            WHERE disciplina = :discipline 
#            ORDER BY categoria
#        """
#        params = {'discipline': discipline}
#    else:
#        query = """
#            SELECT DISTINCT categoria 
#            FROM results 
#            WHERE disciplina = :discipline 
#            AND ambiente = :ambiente 
#            ORDER BY categoria
#        """
#        params = {'discipline': discipline, 'ambiente': ambiente}
#    
#    with engine.connect() as conn:
#        result = pd.read_sql(
#            text(query), 
#            conn,
#            params=params
#        )
#    
#    # Convert Italian categories to standardized ones
#    standardized_categories = set()
#    for cat in result['categoria']:
#        if cat in CATEGORY_MAPPING:
#            standardized_categories.add(CATEGORY_MAPPING[cat])
#    
#    # Return only categories that exist in the database, maintaining our preferred order
#    return [cat for cat in ORDERED_CATEGORIES if cat in standardized_categories]
