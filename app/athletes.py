from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import text
import pandas as pd

from app.error_reporting import limiter
from app.models import get_db_engine
from app.utils import format_time

# Create blueprint for athletes
athletes_bp = Blueprint('athletes', __name__)

@athletes_bp.route('/athlete/<link_atleta>')
def athlete_profile(link_atleta):
    """Display athlete profile with all their performances"""
    engine = get_db_engine()
    
    # Query to get athlete basic info
    info_query = """
    SELECT DISTINCT
        atleta, 
        anno, 
        sesso,
        link_atleta
    FROM results
    WHERE link_atleta = :link_atleta
    LIMIT 1
    """
    
    # Query to get all athlete performances
    performances_query = """
    SELECT 
        prestazione,
        cronometraggio,
        disciplina,
        categoria,
        società,
        luogo,
        data,
        vento,
        ambiente
    FROM results
    WHERE link_atleta = :link_atleta
    ORDER BY data DESC, disciplina ASC
    """
    
    # Query to get athlete's personal bests by discipline
    personal_bests_query = """
    WITH ranked_performances AS (
        SELECT 
            disciplina,
            prestazione,
            cronometraggio,
            data,
            luogo,
            vento,
            ambiente,
            RANK() OVER (
                PARTITION BY disciplina, ambiente
                ORDER BY 
                    CASE WHEN (
                        SELECT classifica 
                        FROM disciplines 
                        WHERE codice = disciplina
                    ) = 'tempo' THEN prestazione END ASC,
                    CASE WHEN (
                        SELECT classifica 
                        FROM disciplines 
                        WHERE codice = disciplina
                    ) != 'tempo' THEN prestazione END DESC
            ) as rank
        FROM results
        WHERE link_atleta = :link_atleta
    )
    SELECT 
        disciplina,
        prestazione,
        cronometraggio,
        data,
        luogo,
        vento,
        ambiente
    FROM ranked_performances
    WHERE rank = 1
    ORDER BY disciplina, ambiente
    """
    
    params = {'link_atleta': link_atleta}
    
    with engine.connect() as conn:
        # Get athlete info
        athlete_info = pd.read_sql(text(info_query), conn, params=params)
        if athlete_info.empty:
            return render_template('404.html'), 404
        
        # Get all performances
        performances = pd.read_sql(text(performances_query), conn, params=params)
        
        # Get personal bests
        personal_bests = pd.read_sql(text(personal_bests_query), conn, params=params)
    
    # Convert to dictionary for template
    athlete_data = athlete_info.iloc[0].to_dict()
    
    return render_template(
        'athlete_profile.html',
        athlete=athlete_data,
        performances=performances.to_dict('records'),
        personal_bests=personal_bests.to_dict('records'),
        format_time=format_time
    )

@athletes_bp.route('/api/search/athletes')
@limiter.limit("20/minute")
def search_athletes():
    """API endpoint to search athletes by name"""
    search_term = request.args.get('q', '')
    if len(search_term) < 3:
        return jsonify({'results': []})
    
    engine = get_db_engine()
    
    # Search query
    search_query = """
    SELECT DISTINCT
        atleta,
        anno,
        sesso,
        link_atleta
    FROM results
    WHERE 
        atleta ILIKE :search_term
    ORDER BY atleta
    LIMIT 50
    """
    
    with engine.connect() as conn:
        results = pd.read_sql(
            text(search_query), 
            conn, 
            params={'search_term': f'%{search_term}%'}
        )
    
    return jsonify({'results': results.to_dict('records')})

@athletes_bp.route('/search-athletes')
def search_athletes_page():
    """Page for searching athletes"""
    return render_template('search_athletes.html')

