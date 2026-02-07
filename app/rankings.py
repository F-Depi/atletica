from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from sqlalchemy import text
import pandas as pd

from app.app import DISCIPLINES, DISCIPLINE_STANDARD, REGIONI_PROVINCE, CATEGORY_MAPPING
from app.models import get_db_engine
from app.utils import should_show_wind, format_time
from app.error_reporting import limiter

# Create blueprint
rankings_bp = Blueprint('rankings', __name__)


## Invia tutte le discipline alla tab con tutti i filtri
## Per la tab "Tutti i filtri e le gare"
@rankings_bp.route('/api/disciplines/all')
def get_all_disciplines():
    return jsonify(list(DISCIPLINES.keys()))


## Carichiamo le discipline in funzione della categoria
## Per le tab "Uomni" e "Donne"
@rankings_bp.route('/api/disciplines/<category>/<gender>')
def get_disciplines(category, gender):
    disciplines = [
        d for d in DISCIPLINE_STANDARD[category] 
        if gender in d['sesso']
    ]
    return jsonify(disciplines)


## Permette a rankings.js di sapere se una disciplina ha il vento e 
## visualizzare il checkbox di conseguenza
@rankings_bp.route('/api/discipline_info/<discipline>')
def get_wind_info(discipline):
    if discipline in DISCIPLINES:
        return jsonify({
            'vento': DISCIPLINES[discipline].get('vento', 'no')
        })
    return jsonify({'error': 'Disciplina non trovata'}), 404


## Questa è quella che gestisce le query quando si preme invio
@rankings_bp.route('/rankings')
@limiter.limit("50/minute")
def rankings():
    tab = request.args.get('tab', 'men')

    # Se non ci sono parametri o manca la disciplina, reindirizza alla configurazione di default
    if not request.args or not request.args.get('discipline'):
        return redirect(url_for('rankings.rankings', tab=tab, discipline='110Hs_h106-9.14', ambiente='P', category='ASS', year='2025'))

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
    regione = request.args.get('regione', None)
    provincia_societa = request.args.get('provincia_societa', None)
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

    # Aggiungi filtro vento se necessario
    if legal_wind_only and should_show_wind(discipline, 'P'):
        conditions.append("""(ambiente = 'I' OR
                         (vento IS NOT NULL AND ROUND(vento, 1) <= 2.0))""")


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
                    cod_società
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
                    cod_società
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
        conditions.append("""(ambiente = 'I' OR
                         (vento IS NOT NULL AND ROUND(vento, 1) <= 2.0))""")

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
                    cod_società
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
                    cod_società
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
