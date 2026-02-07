from flask import Blueprint, render_template, request, jsonify, abort, redirect, url_for
from sqlalchemy import text
import pandas as pd
from datetime import datetime
from app.error_reporting import limiter
from app.models import get_db_engine
from app.utils import format_time
from app.app import DISCIPLINES

# Create blueprint for società
societa_bp = Blueprint('societa', __name__, url_prefix='/societa')


def get_discipline_order(conn):
    """
    Recupera l'ordine delle discipline dalla tabella discipline.
    Ritorna un dizionario {nome_disciplina: ordine}
    """
    order_sql = text("""
        SELECT disciplina, COALESCE(ordine, 999) as ordine
        FROM discipline
        ORDER BY ordine, disciplina
    """)
    result = conn.execute(order_sql)
    
    return {row[0]: row[1] for row in result}


def sort_disciplines_dict(results_dict, discipline_order):
    """
    Ordina un dizionario di discipline secondo l'ordine dal database.
    
    Args:
        results_dict: Dizionario con discipline come chiavi
        discipline_order: Dizionario {disciplina: ordine}
    
    Returns:
        Dizionario ordinato
    """
    sorted_keys = sorted(
        results_dict.keys(),
        key=lambda x: (discipline_order.get(x, 999), x)
    )
    return {k: results_dict[k] for k in sorted_keys}


@societa_bp.route('/', methods=['GET'])
def index():
    """Redirect to home"""
    return redirect(url_for('index'))


@societa_bp.route('/<cod_societa>', methods=['GET'])
def societa_profilo(cod_societa):
    """Display società profile and performances"""
    
    engine = get_db_engine()
    current_year = datetime.now().year
    selected_year = request.args.get('year', current_year, type=int)
    
    with engine.connect() as conn:
        # Recupera l'ordine delle discipline dalla tabella discipline
        discipline_order = get_discipline_order(conn)
        
        # Get società info using cod_società
        societa_sql = text("""
            SELECT DISTINCT società, link_società, cod_società
            FROM results 
            WHERE cod_società = :cod_societa
            LIMIT 1
        """)
        
        societa_result = conn.execute(societa_sql, {"cod_societa": cod_societa})
        societa_data = societa_result.fetchone()
        
        if not societa_data:
            abort(404)
            
        societa_name = societa_data[0]
        link_societa_fidal = societa_data[1]
        
        # Get società statistics
        stats_sql = text("""
            SELECT 
                COUNT(*) as num_risultati,
                COUNT(DISTINCT link_atleta) as num_atleti,
                COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM data) = :current_year) as num_risultati_stagione
            FROM results
            WHERE cod_società = :cod_societa
        """)
        
        stats_result = conn.execute(stats_sql, {
            "cod_societa": cod_societa,
            "current_year": current_year
        })
        stats = stats_result.fetchone()
        
        societa_additional_data = {
            "codice": cod_societa,
            "num_risultati": stats[0] if stats else 0,
            "num_atleti": stats[1] if stats else 0,
            "num_risultati_stagione": stats[2] if stats else 0
        }
        
        # Get available years for filter
        years_sql = text("""
            SELECT DISTINCT EXTRACT(YEAR FROM data)::integer as anno
            FROM results
            WHERE cod_società = :cod_societa
              AND data IS NOT NULL
            ORDER BY anno DESC
        """)
        
        years_result = conn.execute(years_sql, {"cod_societa": cod_societa})
        available_years = [row[0] for row in years_result]
        
        # Get seasonal results (selected year)
        seasonal_sql = text("""
            SELECT 
                prestazione, vento, tempo, cronometraggio,
                atleta, link_atleta, anno, categoria,
                posizione, luogo, data, disciplina, ambiente
            FROM results
            WHERE cod_società = :cod_societa
              AND EXTRACT(YEAR FROM data) = :selected_year
              AND disciplina NOT LIKE '%sconosciuto%'
            ORDER BY disciplina, prestazione
        """)
        
        seasonal_result = conn.execute(seasonal_sql, {
            "cod_societa": cod_societa,
            "selected_year": selected_year
        })
        
        seasonal_df = pd.DataFrame(seasonal_result, columns=[
            'prestazione', 'vento', 'tempo', 'cronometraggio',
            'atleta', 'link_atleta', 'anno', 'categoria',
            'posizione', 'luogo', 'data', 'disciplina', 'ambiente'
        ])
        
        # Process seasonal results
        seasonal_results = {}
        if not seasonal_df.empty:
            seasonal_df['prestazione_display'] = seasonal_df.apply(
                lambda row: format_time(row['prestazione'], DISCIPLINES.get(row['disciplina'], {}), row['cronometraggio']),
                axis=1
            )
            seasonal_df['atleta_link'] = seasonal_df['link_atleta'].apply(
                lambda x: '_'.join(x.split('/')[-2:])[:-3] + '=' if x else ''
            )
            
            for discipline in seasonal_df['disciplina'].unique():
                if discipline not in DISCIPLINES:
                    continue
                    
                discipline_df = seasonal_df[seasonal_df['disciplina'] == discipline].copy()
                
                if discipline_df.empty:
                    continue
                
                if DISCIPLINES[discipline]['classifica'] == 'tempo':
                    discipline_df = discipline_df.sort_values('prestazione', ascending=True).reset_index(drop=True)
                else:
                    discipline_df = discipline_df.sort_values('prestazione', ascending=False).reset_index(drop=True)
                
                # Get best result (considering wind for affected disciplines)
                is_wind_affected = DISCIPLINES[discipline].get('vento', 'no') != 'no'
                if is_wind_affected:
                    valid_results = discipline_df[
                        (discipline_df['vento'].astype(float) <= 2) | 
                        (discipline_df['ambiente'] == 'I')
                    ]
                    best_idx = 0 if valid_results.empty else valid_results.index[0]
                else:
                    best_idx = 0
                
                seasonal_results[discipline] = {
                    'results': discipline_df.to_dict('records'),
                    'best': discipline_df.iloc[best_idx].to_dict()
                }
        
        # Ordina i risultati stagionali
        seasonal_results = sort_disciplines_dict(seasonal_results, discipline_order)
        
        # Get recent results (last 100)
        recent_sql = text("""
            SELECT 
                prestazione, vento, tempo, cronometraggio,
                atleta, link_atleta, anno, categoria,
                posizione, luogo, data, disciplina, ambiente
            FROM results
            WHERE cod_società = :cod_societa
              AND disciplina NOT LIKE '%sconosciuto%'
            ORDER BY data DESC, luogo
            LIMIT 100
        """)
        
        recent_result = conn.execute(recent_sql, {"cod_societa": cod_societa})
        
        recent_df = pd.DataFrame(recent_result, columns=[
            'prestazione', 'vento', 'tempo', 'cronometraggio',
            'atleta', 'link_atleta', 'anno', 'categoria',
            'posizione', 'luogo', 'data', 'disciplina', 'ambiente'
        ])
        
        recent_results = []
        if not recent_df.empty:
            recent_df['prestazione_display'] = recent_df.apply(
                lambda row: format_time(row['prestazione'], DISCIPLINES.get(row['disciplina'], {}), row['cronometraggio']),
                axis=1
            )
            recent_df['atleta_link'] = recent_df['link_atleta'].apply(
                lambda x: '_'.join(x.split('/')[-2:])[:-3] + '=' if x else ''
            )
            recent_results = recent_df.to_dict('records')
        
        # Get athletes list
        athletes_sql = text("""
            SELECT 
                atleta,
                link_atleta,
                MAX(anno) as anno,
                MAX(categoria) as categoria,
                COUNT(*) as num_risultati,
                COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM data) = :current_year) as risultati_stagione
            FROM results
            WHERE cod_società = :cod_societa
            GROUP BY atleta, link_atleta
            ORDER BY atleta
        """)

        athletes_result = conn.execute(athletes_sql, {
            "cod_societa": cod_societa,
            "current_year": current_year
        })

        athletes = []
        athlete_categories = set()
        for row in athletes_result:
            link = '_'.join(row[1].split('/')[-2:])[:-3] + '=' if row[1] else ''
            categoria = row[3] or ''
            
            # Determina il genere dalla categoria (M=maschile, F=femminile)
            # Le categorie italiane tipicamente contengono M o F (es: SM35, SF40, JM, JF)
            genere = ''
            if categoria:
                cat_upper = categoria.upper()
                # Cerca F o M nella categoria
                if 'F' in cat_upper:
                    genere = 'F'
                elif 'M' in cat_upper:
                    genere = 'M'
            
            is_active = row[5] > 0  # Ha risultati nell'anno corrente
            
            athletes.append({
                'nome': row[0],
                'link': link,
                'anno': row[2],
                'categoria': categoria,
                'num_risultati': row[4],
                'genere': genere,
                'is_active': is_active,
                'risultati_stagione': row[5]
            })
            if categoria:
                athlete_categories.add(categoria)

        athlete_categories = sorted(list(athlete_categories))
        
        # Get society records (all-time bests per discipline)
        records_sql = text("""
            SELECT 
                prestazione, vento, tempo, cronometraggio,
                atleta, link_atleta, anno, categoria,
                posizione, luogo, data, disciplina, ambiente
            FROM results
            WHERE cod_società = :cod_societa
              AND disciplina NOT LIKE '%sconosciuto%'
            ORDER BY disciplina, prestazione
        """)
        
        records_result = conn.execute(records_sql, {"cod_societa": cod_societa})
        
        records_df = pd.DataFrame(records_result, columns=[
            'prestazione', 'vento', 'tempo', 'cronometraggio',
            'atleta', 'link_atleta', 'anno', 'categoria',
            'posizione', 'luogo', 'data', 'disciplina', 'ambiente'
        ])
        
        records = {}
        if not records_df.empty:
            records_df['prestazione_display'] = records_df.apply(
                lambda row: format_time(row['prestazione'], DISCIPLINES.get(row['disciplina'], {}), row['cronometraggio']),
                axis=1
            )
            records_df['atleta_link'] = records_df['link_atleta'].apply(
                lambda x: '_'.join(x.split('/')[-2:])[:-3] + '=' if x else ''
            )
            
            for discipline in records_df['disciplina'].unique():
                if discipline not in DISCIPLINES:
                    continue
                    
                discipline_df = records_df[records_df['disciplina'] == discipline].copy()
                
                if discipline_df.empty:
                    continue
                
                if DISCIPLINES[discipline]['classifica'] == 'tempo':
                    discipline_df = discipline_df.sort_values('prestazione', ascending=True).reset_index(drop=True)
                else:
                    discipline_df = discipline_df.sort_values('prestazione', ascending=False).reset_index(drop=True)
                
                # Get best result (considering wind)
                is_wind_affected = DISCIPLINES[discipline].get('vento', 'no') != 'no'
                if is_wind_affected:
                    valid_results = discipline_df[
                        (discipline_df['vento'].astype(float) <= 2) | 
                        (discipline_df['ambiente'] == 'I')
                    ]
                    best_idx = 0 if valid_results.empty else valid_results.index[0]
                else:
                    best_idx = 0
                
                # Get top 10 for this discipline
                top_10 = discipline_df.head(10).to_dict('records')
                
                # Get discipline type for filtering
                discipline_type = DISCIPLINES[discipline].get('tipo', 'Altro')
                
                records[discipline] = {
                    'best': discipline_df.iloc[best_idx].to_dict(),
                    'top_10': top_10,
                    'tipo': discipline_type
                }
        
        # Ordina i record
        records = sort_disciplines_dict(records, discipline_order)
    
    return render_template(
        'societa/profilo.html',
        societa_name=societa_name,
        societa_data=societa_additional_data,
        cod_societa=cod_societa,
        link_societa_fidal=link_societa_fidal,
        seasonal_results=seasonal_results,
        recent_results=recent_results,
        athletes=athletes,
        athlete_categories=athlete_categories,
        records=records,
        current_year=current_year,
        selected_year=selected_year,
        available_years=available_years,
        enumerate=enumerate
    )


@societa_bp.route('/<cod_societa>/seasonal', methods=['GET'])
def get_seasonal_results(cod_societa):
    """API endpoint to get seasonal results for a specific year"""
    year = request.args.get('year', datetime.now().year, type=int)
    
    engine = get_db_engine()
    
    with engine.connect() as conn:
        # Recupera l'ordine delle discipline
        discipline_order = get_discipline_order(conn)
        
        # Verify società exists
        check_sql = text("""
            SELECT 1 FROM results 
            WHERE cod_società = :cod_societa
            LIMIT 1
        """)
        check_result = conn.execute(check_sql, {"cod_societa": cod_societa})
        
        if not check_result.fetchone():
            return jsonify({'error': 'Società non trovata'}), 404
        
        # Get seasonal results
        seasonal_sql = text("""
            SELECT 
                prestazione, vento, tempo, cronometraggio,
                atleta, link_atleta, anno, categoria,
                posizione, luogo, data, disciplina, ambiente
            FROM results
            WHERE cod_società = :cod_societa
              AND EXTRACT(YEAR FROM data) = :year
              AND disciplina NOT LIKE '%sconosciuto%'
            ORDER BY disciplina, prestazione
        """)
        
        result = conn.execute(seasonal_sql, {
            "cod_societa": cod_societa,
            "year": year
        })
        
        df = pd.DataFrame(result, columns=[
            'prestazione', 'vento', 'tempo', 'cronometraggio',
            'atleta', 'link_atleta', 'anno', 'categoria',
            'posizione', 'luogo', 'data', 'disciplina', 'ambiente'
        ])
        
        if df.empty:
            return jsonify({'results': {}, 'discipline_order': []})
        
        df['prestazione_display'] = df.apply(
            lambda row: format_time(row['prestazione'], DISCIPLINES.get(row['disciplina'], {}), row['cronometraggio']),
            axis=1
        )
        df['atleta_link'] = df['link_atleta'].apply(
            lambda x: '_'.join(x.split('/')[-2:])[:-3] + '=' if x else ''
        )
        df['data'] = df['data'].apply(lambda x: x.strftime('%d/%m/%Y') if x else '-')
        
        seasonal_results = {}
        for discipline in df['disciplina'].unique():
            if discipline not in DISCIPLINES:
                continue
                
            discipline_df = df[df['disciplina'] == discipline].copy()
            
            if discipline_df.empty:
                continue
            
            if DISCIPLINES[discipline]['classifica'] == 'tempo':
                discipline_df = discipline_df.sort_values('prestazione', ascending=True).reset_index(drop=True)
            else:
                discipline_df = discipline_df.sort_values('prestazione', ascending=False).reset_index(drop=True)
            
            seasonal_results[discipline] = {
                'results': discipline_df.to_dict('records'),
                'best': discipline_df.iloc[0].to_dict() if not discipline_df.empty else None
            }
        
        # Ordina i risultati stagionali
        seasonal_results = sort_disciplines_dict(seasonal_results, discipline_order)
        
        # Restituisci anche l'ordine delle discipline presenti
        ordered_disciplines = list(seasonal_results.keys())
        
        return jsonify({
            'results': seasonal_results,
            'discipline_order': ordered_disciplines
        })
