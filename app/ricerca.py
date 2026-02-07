from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import text
from app.error_reporting import limiter
from app.models import get_db_engine

ricerca_bp = Blueprint('ricerca', __name__, url_prefix='/ricerca')


@ricerca_bp.route('/api', methods=['GET'])
@limiter.limit("30 per minute")
def cerca():
    """API endpoint for unified search"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 3:
        return jsonify({'atleti': [], 'societa': []})
    
    engine = get_db_engine()
    
    atleti = []
    societa = []
    
    try:
        with engine.connect() as conn:
            # Search athletes
            terms = query.split()
            
            if len(terms) > 1:
                conditions = []
                params = {}
                
                for i, term in enumerate(terms):
                    param_name = f"term_{i}"
                    conditions.append(f"atleta ILIKE :{param_name}")
                    params[param_name] = f"%{term}%"
                
                where_clause = " AND ".join(conditions)
                
                atleti_sql = text(f"""
                    SELECT DISTINCT atleta, link_atleta, anno
                    FROM atleti 
                    WHERE {where_clause}
                    ORDER BY atleta
                    LIMIT 8
                """)
                
                result = conn.execute(atleti_sql, params)
            else:
                atleti_sql = text("""
                    SELECT DISTINCT atleta, link_atleta, anno
                    FROM atleti 
                    WHERE atleta ILIKE :query
                    ORDER BY atleta
                    LIMIT 8
                """)
                
                result = conn.execute(atleti_sql, {"query": f"%{query}%"})
            
            for row in result:
                if row[1]:
                    identifier = '_'.join(row[1].split('/')[-2:])
                    identifier = identifier[:-3] + '='
                    atleti.append({
                        "name": row[0],
                        "anno": row[2],
                        "link": identifier
                    })
            
            # Search societies
            societa_sql = text("""
                SELECT DISTINCT società, cod_società
                FROM results 
                WHERE (società ILIKE :query OR cod_società ILIKE :query)
                  AND cod_società IS NOT NULL
                ORDER BY società
                LIMIT 8
            """)
            
            result = conn.execute(societa_sql, {"query": f"%{query}%"})
            
            for row in result:
                if row[1]:
                    societa.append({
                        "name": row[0],
                        "codice": row[1]
                    })
        
        return jsonify({'atleti': atleti, 'societa': societa})
        
    except Exception as e:
        print(f"Error in unified search: {e}")
        return jsonify({'atleti': [], 'societa': []})
