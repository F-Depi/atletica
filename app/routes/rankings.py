import json
import pandas as pd
from sqlalchemy import text
from flask import render_template, request, redirect, url_for
from app.routes import rankings_bp
from app.services.database import get_db_engine
from app.services.formatting import format_time, should_show_wind


# Load disciplines data
with open('data/dizionario_gare.json') as f:
    DISCIPLINES = json.load(f)
with open('data/category_mapping.json') as f:
    CATEGORY_MAPPING = json.load(f)


@rankings_bp.route('/')
def rankings():
    """Main rankings route that dispatches to appropriate handler"""
    tab = request.args.get('tab', 'men')

    # If no parameters or missing discipline, redirect to default configuration
    if not request.args or not request.args.get('discipline'):
        return redirect(url_for('rankings.rankings', tab=tab, discipline='110Hs_h106-9.14', ambiente='P', category='ASS'))

    if tab in ['men', 'women']:
        return handle_standard_rankings(tab)
    else:
        return handle_advanced_rankings()


def handle_standard_rankings(tab):
    """Handle standard rankings (men/women tabs)"""
    # Get parameters
    category = request.args.get('category', 'ASS')
    discipline = request.args.get('discipline', '100m')
    year = request.args.get('year', None)
    limit = request.args.get('limit', 50, type=int)
    show_all = request.args.get('allResults', '').lower() == 'true'
    legal_wind_only = request.args.get('legal_wind', 'true').lower() == 'true'
    page = request.args.get('page', 1, type=int)
    
    # Determine gender from tab
    gender = 'M' if tab == 'men' else 'F'
    
    # Get corresponding Italian categories
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

    # Handle environment
    ambiente = request.args.get('ambiente')
    if ambiente:
        if ambiente in ['I', 'P']:
            conditions.append("ambiente = :ambiente")
            params['ambiente'] = ambiente
        elif ambiente == 'IP':
            conditions.append("ambiente IN ('I', 'P')")

    # Add category filter
    if italian_categories:
        categories_list = "', '".join(italian_categories)
        conditions.append(f"categoria IN ('{categories_list}')")

    # Add year filter
    if year:
        conditions.append("EXTRACT(YEAR FROM data) = :year")
        params['year'] = int(year) #pyright: ignore

    # Add wind filter if necessary
    if legal_wind_only and should_show_wind(discipline, 'P', DISCIPLINES):
        conditions.append("""(
            ambiente = 'I' OR
            CAST(NULLIF(REPLACE(vento, ',', '.'), '') AS FLOAT) <= 2.0
        )""")

    # Build query
    where_clause = " AND ".join(conditions)

    # Execute query for count
    engine = get_db_engine()
    if show_all:
        count_query = f"SELECT COUNT(*) FROM results WHERE {where_clause}"
    else:
        count_query = f"SELECT COUNT(DISTINCT atleta) FROM results WHERE {where_clause}"

    with engine.connect() as conn:
        total_count = pd.read_sql(text(count_query), conn, params=params).iloc[0, 0]

    # Calculate pagination
    total_pages = (total_count + limit - 1) // limit
    offset = (page - 1) * limit
    params['limit'] = limit #pyright: ignore
    params['offset'] = offset #pyright: ignore

    # Build main query
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

    # Execute main query
    with engine.connect() as conn:
        result = pd.read_sql(text(main_query), conn, params=params)

    return render_template(
        'rankings.html',
        results=result.to_dict('records'),
        discipline=discipline,
        discipline_info=DISCIPLINES[discipline],
        show_wind=should_show_wind(discipline, 'P', DISCIPLINES),
        current_page=page,
        total_pages=total_pages,
        limit=limit,
        total_count=total_count,
        format_time=format_time,
        show_all=show_all,
        legal_wind_only=legal_wind_only
    )


def handle_advanced_rankings():
    """Handle advanced rankings (all filters tab)"""
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
    show_wind = should_show_wind(discipline, ambiente, DISCIPLINES)

    # Base conditions for both queries
    conditions = ["disciplina = :discipline"]
    params = {'discipline': discipline}

    if ambiente != 'ALL':
        conditions.append("ambiente = :ambiente")
        params['ambiente'] = ambiente

    if year:
        conditions.append("EXTRACT(YEAR FROM data) = :year")
        params['year'] = int(year) #pyright: ignore

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
