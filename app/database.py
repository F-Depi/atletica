import pandas as pd
from sqlalchemy import text
from config import DISCIPLINES, CATEGORY_MAPPING, REGIONI_PROVINCE, get_db_engine

def format_time(seconds, discipline_info, cronometraggio=None):
    """Il tuo format_time esistente"""
    if seconds is None:
        return '-'
    
    if discipline_info.get('classifica') == 'tempo':
        seconds = float(seconds)
        if seconds >= 60:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}:{secs:05.2f}"
        return f"{seconds:.2f}"
    else:
        return f"{float(seconds):.2f}"


def should_show_wind(disciplina, ambiente):
    """Il tuo should_show_wind esistente"""
    if ambiente == 'I':
        return False
    return DISCIPLINES[disciplina]['vento']


def get_rankings(
    discipline: str,
    ambiente: str = None,  # Può essere 'I', 'P', 'IP' o None
    gender: str = None,
    category: str = None,
    year: int = None,
    regione: str = None,
    provincia_societa: str = None,
    limit: int = 50,
    page: int = 1,
    show_all: bool = False,
    legal_wind_only: bool = True,
) -> tuple[list[dict], int, int]:
    """
    Ritorna (risultati, total_count, total_pages)
    """
    conditions = ["disciplina = :discipline"]
    params = {'discipline': discipline}
    
    # Gestione ambiente (I, P, IP, o None)
    if ambiente:
        if ambiente in ['I', 'P']:
            conditions.append("ambiente = :ambiente")
            params['ambiente'] = ambiente
        elif ambiente == 'IP':
            conditions.append("ambiente IN ('I', 'P')")
        # Se ambiente è altro valore, non filtrare
    
    if gender:
        conditions.append("sesso = :gender")
        params['gender'] = gender
    
    if category:
        italian_categories = CATEGORY_MAPPING.get(category, [])
        if italian_categories:
            categories_list = "', '".join(italian_categories)
            conditions.append(f"categoria IN ('{categories_list}')")
    
    if year:
        conditions.append("EXTRACT(YEAR FROM data) = :year")
        params['year'] = int(year)
    
    if regione:
        province = REGIONI_PROVINCE.get(regione, [])
        if province:
            province_list = "', '".join(province)
            conditions.append(f"LEFT(cod_società, 2) IN ('{province_list}')")
    
    if provincia_societa:
        if len(provincia_societa) == 2:
            if provincia_societa == "RM":
                conditions.append("(LEFT(cod_società, 2) = 'RM' OR LEFT(cod_società, 2) = 'RS')")
            else:
                conditions.append("LEFT(cod_società, 2) = :provincia_societa")
                params['provincia_societa'] = provincia_societa
        elif len(provincia_societa) == 5:
            conditions.append("cod_società = :provincia_societa")
            params['provincia_societa'] = provincia_societa
    
    # Filtro vento - usa should_show_wind con ambiente corretto
    if legal_wind_only and should_show_wind(discipline, ambiente if ambiente and ambiente != 'IP' else 'P'):
        conditions.append("(ambiente = 'I' OR (vento IS NOT NULL AND ROUND(vento, 1) <= 2.0))")
    
    where_clause = " AND ".join(conditions)
    
    # Count query
    engine = get_db_engine()
    count_col = "COUNT(*)" if show_all else "COUNT(DISTINCT atleta)"
    count_query = f"SELECT {count_col} FROM results WHERE {where_clause}"
    
    with engine.connect() as conn:
        total_count = pd.read_sql(text(count_query), conn, params=params).iloc[0, 0]
    
    total_pages = max(1, (total_count + limit - 1) // limit)
    offset = (page - 1) * limit
    params['limit'] = limit
    params['offset'] = offset
    
    # Main query
    sort_direction = 'ASC' if DISCIPLINES[discipline]['classifica'] == 'tempo' else 'DESC'
    
    if show_all:
        main_query = f"""
            WITH base_results AS (
                SELECT prestazione, cronometraggio, atleta, anno, categoria,
                       società, luogo, data, vento, ambiente, link_atleta, cod_società
                FROM results WHERE {where_clause}
            )
            SELECT *, RANK() OVER (ORDER BY prestazione {sort_direction}) as position
            FROM base_results
            ORDER BY prestazione {sort_direction}, atleta ASC, data DESC
            LIMIT :limit OFFSET :offset
        """
    else:
        main_query = f"""
            WITH ranked_athletes AS (
                SELECT DISTINCT ON (atleta)
                    prestazione, cronometraggio, atleta, anno, categoria,
                    società, luogo, data, vento, ambiente, link_atleta, cod_società
                FROM results WHERE {where_clause}
                ORDER BY atleta, prestazione {sort_direction}, data DESC
            )
            SELECT *, RANK() OVER (ORDER BY prestazione {sort_direction}) as position
            FROM ranked_athletes
            ORDER BY prestazione {sort_direction}, atleta ASC
            LIMIT :limit OFFSET :offset
        """
    
    with engine.connect() as conn:
        result = pd.read_sql(text(main_query), conn, params=params)
    
    return result.to_dict('records'), int(total_count), int(total_pages)


def search_athletes(query: str, limit: int = 10) -> list[dict]:
    """Cerca atleti per nome"""
    if len(query) < 3:
        return []
    
    engine = get_db_engine()
    sql = """
        SELECT DISTINCT atleta as name, anno, link_atleta as link
        FROM results
        WHERE atleta ILIKE :query
        ORDER BY atleta
        LIMIT :limit
    """
    
    with engine.connect() as conn:
        result = pd.read_sql(text(sql), conn, params={'query': f'%{query}%', 'limit': limit})
    
    return result.to_dict('records')


def search_societies(query: str, limit: int = 10) -> list[dict]:
    """Cerca società per nome o codice"""
    if len(query) < 2:
        return []
    
    engine = get_db_engine()
    sql = """
        SELECT DISTINCT società as name, cod_società as codice
        FROM results
        WHERE società ILIKE :query OR cod_società ILIKE :query
        ORDER BY società
        LIMIT :limit
    """
    
    with engine.connect() as conn:
        result = pd.read_sql(text(sql), conn, params={'query': f'%{query}%', 'limit': limit})
    
    return result.to_dict('records')
