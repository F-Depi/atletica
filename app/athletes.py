from flask import Blueprint, render_template, request, jsonify, abort
from sqlalchemy import text
import pandas as pd
from app.error_reporting import limiter
from app.models import get_db_engine
from app.utils import format_time
from app.app import DISCIPLINES
import re
from datetime import datetime

# Create blueprint for athletes
athletes_bp = Blueprint('athletes', __name__, url_prefix='/athlete')

@athletes_bp.route('/', methods=['GET'])
def index():
    """Render the athlete search page"""
    return render_template('athlete/search.html')

@athletes_bp.route('/search', methods=['GET'])
@limiter.limit("30 per minute")
def search_athletes():
    """API endpoint for searching athletes"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify([])
    
    engine = get_db_engine()
    
    try:
        # Use ILIKE for case-insensitive matching
        sql = text("""
            SELECT DISTINCT atleta, link_atleta 
            FROM atleti 
            WHERE atleta ILIKE :query
            ORDER BY atleta
            LIMIT 10
        """)
        
        # Add wildcards to search for partial matches
        search_query = f"%{query}%"
        
        with engine.connect() as conn:
            result = conn.execute(sql, {"query": search_query})
            athletes = []
            
            for row in result:
                # Extract name + unique code from link_atleta
                identifier = '_'.join(row[1].split('/')[-2:])
                athletes.append({"name": row[0], "link": identifier})
            
        return jsonify(athletes)
    
    except Exception as e:
        print(f"Error searching athletes: {e}")
        return jsonify([])

@athletes_bp.route('/<path:athlete_path>', methods=['GET'])
def athlete_profile(athlete_path):
    """Display athlete profile and performances
    
    athlete_path is expected to be in the format "NAME/ID"
    but the actual link_atleta in the database might be a full URL
    """
    engine = get_db_engine()
    
    # Search for the athlete with the given path fragment in their link_atleta
    athlete_sql = text("""
        SELECT atleta, link_atleta
        FROM atleti 
        WHERE link_atleta LIKE :path_fragment
        LIMIT 1
    """)
    
    # Add wildcards to search for the path in the full URL
    path_fragment = f"%{athlete_path}%"
    
    with engine.connect() as conn:
        # Get athlete name and full link
        athlete_result = conn.execute(athlete_sql, {"path_fragment": path_fragment})
        athlete_data = athlete_result.fetchone()
        
        if not athlete_data:
            abort(404)
            
        athlete_name = athlete_data[0]
        full_link_atleta = athlete_data[1]
        
        # Try to get additional athlete info (birthdate, current club, category)
        athlete_info_sql = text("""
            SELECT 
                anno, categoria, società, link_società
            FROM results
            WHERE link_atleta = :link_atleta
            ORDER BY data DESC
            LIMIT 1
        """)
        
        athlete_info_result = conn.execute(athlete_info_sql, {"link_atleta": full_link_atleta})
        athlete_info = athlete_info_result.fetchone()
        
        athlete_additional_data = None
        if athlete_info:
            athlete_additional_data = {
                "anno_nascita": athlete_info[0],
                "categoria": athlete_info[1],
                "societa": athlete_info[2],
                "link_societa": athlete_info[3]
            }
        
        # Get all results for the athlete using the full link_atleta
        results_sql = text("""
            SELECT 
                prestazione, vento, tempo, cronometraggio, 
                anno, categoria, società, posizione, 
                luogo, data, disciplina, ambiente
            FROM results
            WHERE link_atleta = :link_atleta
            ORDER BY data DESC, disciplina ASC
        """)
        
        # Get athlete results
        results = conn.execute(results_sql, {"link_atleta": full_link_atleta})
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(results, columns=[
            'prestazione', 'vento', 'tempo', 'cronometraggio',
            'anno', 'categoria', 'società', 'posizione',
            'luogo', 'data', 'disciplina', 'ambiente'
        ])
        
        # Format data for display
        if not df.empty:
            # Format time/performance values
            df['prestazione_display'] = df.apply(
                lambda row: format_time(row['prestazione'], DISCIPLINES[row['disciplina']], row['cronometraggio']),
                axis=1
            )
            
            # Group results by discipline for display
            disciplines = {}
            for discipline in df['disciplina'].unique():
                discipline_df = df[df['disciplina'] == discipline].copy()

                if discipline_df.empty:
                    continue
                
                # Sort the results appropriately
                if DISCIPLINES[discipline]['classifica'] == 'tempo':
                    # For running events, sort from fastest to slowest
                    discipline_df = discipline_df.sort_values('prestazione', ascending=True).reset_index(drop=True)
                else:
                    # For field events, sort from best to worst
                    discipline_df = discipline_df.sort_values('prestazione', ascending=False).reset_index(drop=True)
                
                # Get best result for this discipline (considering wind)
                best_result = None
                # Check if this is a wind-affected discipline
                is_wind_affected = True
                if DISCIPLINES[discipline]['vento'] == 'no':
                    is_wind_affected = False
                
                best_result = []
                if is_wind_affected:
                    best_result = discipline_df[(discipline_df['vento'].astype(float) <= 2) | (discipline_df['ambiente'] == 'I')].iloc[0].to_dict()

                else:
                    best_result = discipline_df.iloc[0].to_dict()
            
                # Convert to list of dictionaries for the template
                disciplines[discipline] = {
                    'results': discipline_df.to_dict('records'),
                    'best': best_result
                }
            
            # Get recent results (last 10 performances)
            recent_results = df.sort_values('data', ascending=False).head(10).to_dict('records')
        else:
            disciplines = {}
            recent_results = []
            
    return render_template(
        'athlete/profile.html',
        athlete_name=athlete_name,
        athlete_data=athlete_additional_data,
        athlete_link=athlete_path,  # Use the original path for linking
        disciplines=disciplines,
        recent_results=recent_results
    )
