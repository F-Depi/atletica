from flask import Blueprint, render_template, request, jsonify, abort
from sqlalchemy import text
import pandas as pd
from app.error_reporting import limiter
from app.models import get_db_engine
from app.utils import format_time
from app.app import DISCIPLINES
import re

# Create blueprint for atletes
atleti_bp = Blueprint('atleti', __name__, url_prefix='/atleta')

#@atleti_bp.route('/', methods=['GET'])
#def index():
#    """Render the atleta ricerca page"""
#    return render_template('atleta/ricerca.html')

@atleti_bp.route('/ricerca', methods=['GET'])
@limiter.limit("30 per minute")
def trova_atleti():
    """API endpoint for searching atleti and società"""
    query = request.args.get('q', '').strip()

    if not query or len(query) < 3:
        return jsonify([])

    engine = get_db_engine()

    try:
        terms = query.split()

        # --- Atleti: ogni termine deve comparire nel nome, in qualsiasi ordine ---
        atleti_params = {}
        atleti_conditions = []
        for i, term in enumerate(terms):
            atleti_conditions.append(f"atleta ILIKE :term_{i}")
            atleti_params[f"term_{i}"] = f"%{term}%"

        atleti_sql = text(f"""
            SELECT DISTINCT atleta, link_atleta, anno
            FROM atleti
            WHERE {" AND ".join(atleti_conditions)}
            ORDER BY atleta
            LIMIT 10
        """)

        # --- Società: ogni termine nel nome, oppure il codice società ---
        soc_params = {"full_query": f"%{query}%", "exact": query}
        soc_conditions = []
        for i, term in enumerate(terms):
            soc_conditions.append(f"nome ILIKE :term_{i}")
            soc_params[f"term_{i}"] = f"%{term}%"

        societa_sql = text(f"""
            SELECT cod_società, nome
            FROM societa
            WHERE ({" AND ".join(soc_conditions)})
               OR cod_società ILIKE :full_query
            ORDER BY (cod_società ILIKE :exact) DESC, nome
            LIMIT 5
        """)

        risultati = []

        with engine.connect() as conn:
            # Società per prime (sono meno numerose), poi atleti
            for cod, nome in conn.execute(societa_sql, soc_params):
                risultati.append({
                    "type": "societa",
                    "name": f"{nome} ({cod})",
                    "link": cod,
                    "url": f"/societa/{cod}"
                })

            for row in conn.execute(atleti_sql, atleti_params):
                identifier = '_'.join(row[1].split('/')[-2:])
                identifier = identifier[:-3] + '='
                risultati.append({
                    "type": "atleta",
                    "name": f"{row[0]} ({row[2]})",
                    "link": identifier,
                    "url": f"/atleta/{identifier}"
                })

        return jsonify(risultati)

    except Exception as e:
        print(f"Error searching atleti/società: {e}")
        return jsonify([])


@atleti_bp.route('/<path:atleta_path>', methods=['GET'])
def atleta_profilo(atleta_path):
    atleta_path = atleta_path[:-1] + "%3D"
    """ Display atleta profilo and performances """

    engine = get_db_engine()
    
    # Search for the atleta with the given path fragment in their link_atleta
    atleta_sql = text("""
        SELECT atleta, link_atleta
        FROM atleti 
        WHERE link_atleta LIKE :path_fragment
        LIMIT 1
    """)
    
    # Add wildcards to ricerca for the path in the full URL
    path_fragment = f"%{atleta_path}%"
    
    with engine.connect() as conn:
        # Get atleta name and full link
        atleta_result = conn.execute(atleta_sql, {"path_fragment": path_fragment})
        atleta_data = atleta_result.fetchone()
        
        if not atleta_data:
            abort(404)
            
        atleta_name = atleta_data[0]
        link_atleta_fidal = atleta_data[1]
        
        # Try to get additional atleta info (birthdate, current club, category)
        atleta_info_sql = text("""
            SELECT 
                anno, categoria, società, cod_società, link_società
            FROM results
            WHERE link_atleta = :link_atleta
            ORDER BY data DESC
            LIMIT 1
        """)
        
        atleta_info_result = conn.execute(atleta_info_sql, {"link_atleta": link_atleta_fidal})
        atleta_info = atleta_info_result.fetchone()
        
        atleta_additional_data = None
        if atleta_info:
            atleta_additional_data = {
                "anno_nascita": atleta_info[0],
                "categoria": atleta_info[1],
                "societa": atleta_info[2],
                "cod_societa": atleta_info[3],
                "nome_societa": f"{atleta_info[4].split('/')[-2].replace('-',' ')} ({atleta_info[3]})"
            }
        
        # Get all results for the atleta using the full link_atleta_fidal
        results_sql = text("""
            SELECT 
                prestazione, vento, tempo, cronometraggio, 
                anno, categoria, società, posizione, 
                luogo, data, disciplina, ambiente
            FROM results
            WHERE link_atleta = :link_atleta
                  AND disciplina NOT LIKE '%sconosciuto%'
            ORDER BY data DESC, disciplina ASC
        """)
        
        # Get atleta results
        results = conn.execute(results_sql, {"link_atleta": link_atleta_fidal})
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(results, columns=[
            'prestazione', 'vento', 'tempo', 'cronometraggio',
            'anno', 'categoria', 'società', 'posizione',
            'luogo', 'data', 'disciplina', 'ambiente'
        ])
        
        # Format data for display
        if df.empty:
            abort(404)

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
            
            # Check if this is a wind-affected discipline
            is_wind_affected = True
            if DISCIPLINES[discipline]['vento'] == 'no':
                is_wind_affected = False

            if is_wind_affected:
                valid_results = discipline_df[(discipline_df['vento'].astype(float) <= 2) | (discipline_df['ambiente'] == 'I')]
                idx = 0 if valid_results.empty else valid_results.index[0]
            else:
                idx = 0

            best_result = discipline_df.loc[idx].to_dict()

            # Convert to list of dictionaries for the template
            disciplines[discipline] = {
                'results': discipline_df.to_dict('records'),
                'best': best_result
            }
        
        # Get recent results (ALL of them)
        recent_results = df.sort_values('data', ascending=False).to_dict('records')
            
    return render_template(
        'atleta/profilo.html',
        atleta_name=atleta_name,
        atleta_data=atleta_additional_data,
        atleta_link=atleta_path,
        disciplines=disciplines,
        recent_results=recent_results,
        link_atleta_fidal=link_atleta_fidal
    )
