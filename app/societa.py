from urllib.parse import quote

import numpy as np
import pandas as pd
from flask import Blueprint, render_template, abort
from sqlalchemy import text

from app.app import DISCIPLINES, REGIONI_PROVINCE
from app.models import get_db_engine
from app.utils import format_time
from app.error_reporting import limiter

societa_bp = Blueprint('societa', __name__, url_prefix='/societa')

TOP_PER_DISCIPLINA = 10     # quanti atleti mostrare nel dettaglio di ogni record sociale
N_ULTIMI_RISULTATI = 300    # quanti risultati mostrare in "Ultimi risultati"

# Ordine "naturale" delle discipline = ordine in dizionario_gare.json
DISC_ORDER = {d: i for i, d in enumerate(DISCIPLINES)}
DISC_TEMPO = {d for d, i in DISCIPLINES.items() if i['classifica'] == 'tempo'}
DISC_VENTO = {d for d, i in DISCIPLINES.items() if i.get('vento') == 'sì'}


# ---------------------------------------------------------------- helper ---

def atleta_url(link_atleta):
    """Stesso identificatore usato dalla ricerca atleti (vedi atleti.trova_atleti)"""
    if not link_atleta:
        return None
    identifier = '_'.join(link_atleta.split('/')[-2:])
    return '/atleta/' + quote(identifier[:-3] + '=', safe='')


def regione_da_codice(cod_societa):
    provincia = cod_societa[:2]
    for regione, province in REGIONI_PROVINCE.items():
        if provincia in province:
            return regione
    return None


def vento_display(r):
    if r['ambiente'] != 'P' or r['disciplina'] not in DISC_VENTO:
        return None
    v = r['vento']
    return None if pd.isna(v) or v == '' else v


def to_row(r):
    """Da riga del DataFrame a dizionario pronto per il template"""
    return {
        'disciplina': r['disciplina'],
        'ambiente': r['ambiente'],
        'sesso': r['sesso'],
        'prestazione_display': format_time(r['prestazione'], DISCIPLINES[r['disciplina']], r['cronometraggio']),
        'vento': vento_display(r),
        'atleta': r['atleta'],
        'url_atleta': atleta_url(r['link_atleta']),
        'anno': r['anno'],
        'categoria': r['categoria'],
        'posizione': r['posizione'],
        'luogo': r['luogo'],
        'data': r['data'],
    }


def chiave_ordine(x):
    return (x['sesso'] != 'M', DISC_ORDER.get(x['disciplina'], 999), x['ambiente'])


def solo_validi(df):
    """Per record e primati escludiamo i risultati ventosi (stessa regola delle rankings)"""
    vento = pd.to_numeric(df['vento'], errors='coerce')
    ventoso = (df['ambiente'] == 'P') & df['disciplina'].isin(DISC_VENTO)
    return df[~ventoso | (vento.round(1) <= 2.0)]


# ----------------------------------------------------------------- route ---

@societa_bp.route('/<cod_societa>', methods=['GET'])
@limiter.limit("30/minute")
def societa_profilo(cod_societa):
    cod_societa = cod_societa.upper()
    engine = get_db_engine()

    with engine.connect() as conn:
        info = conn.execute(text("""
            SELECT società, link_società
            FROM results
            WHERE cod_società = :cod
            ORDER BY data DESC
            LIMIT 1
        """), {'cod': cod_societa}).fetchone()

        if not info:
            abort(404)

        df = pd.read_sql(text("""
            SELECT prestazione, vento, cronometraggio, atleta, link_atleta,
                   anno, categoria, posizione, luogo, data,
                   disciplina, ambiente, sesso
            FROM results
            WHERE cod_società = :cod
                  AND disciplina NOT LIKE '%sconosciuto%'
        """), conn, params={'cod': cod_societa})

    nome_societa, link_fidal = info[0], info[1]

    # Pulizia: servono data e prestazione, e solo discipline note
    df['data'] = pd.to_datetime(df['data'])
    df = df.dropna(subset=['data', 'prestazione'])
    df = df[df['disciplina'].isin(list(DISC_ORDER))]
    if df.empty:
        abort(404)

    df['stagione'] = df['data'].dt.year
    # Ordinando per "sort_key" crescente il migliore è sempre il primo
    df['sort_key'] = np.where(df['disciplina'].isin(DISC_TEMPO), df['prestazione'], -df['prestazione'])
    df = df.sort_values('data').reset_index(drop=True)

    valid = solo_validi(df)
    valid_sorted = valid.sort_values(['sort_key', 'data'])

    # ---------------------------------------------------- Record sociali ---
    # Miglior risultato di ogni atleta per (disciplina, ambiente, sesso), poi top N
    migliori = valid_sorted.drop_duplicates(['disciplina', 'ambiente', 'sesso', 'link_atleta'])
    gruppo = ['disciplina', 'ambiente', 'sesso']
    migliori = migliori[migliori.groupby(gruppo).cumcount() < TOP_PER_DISCIPLINA]

    record_sociali = []
    for (disc, amb, sesso), g in migliori.groupby(gruppo, sort=False):
        righe = [to_row(r) for r in g.to_dict('records')]
        record_sociali.append({
            'disciplina': disc, 'ambiente': amb, 'sesso': sesso,
            'best': righe[0], 'top': righe,
        })
    record_sociali.sort(key=chiave_ordine)

    # -------------------------------------------------- Primati stagionali ---
    # Miglior risultato della società per stagione e (disciplina, ambiente, sesso)
    stagionali_df = valid_sorted.drop_duplicates(['stagione'] + gruppo)
    primati_stagionali = {}
    for stagione, g in stagionali_df.groupby('stagione'):
        righe = [to_row(r) for r in g.to_dict('records')]
        primati_stagionali[int(stagione)] = sorted(righe, key=chiave_ordine)
    anni = sorted(primati_stagionali, reverse=True)

    # ------------------------------------------------- Ultimi risultati ---
    # Ordino anche per luogo così i gruppi "data - luogo" restano contigui
    recenti_df = (df.sort_values(['data', 'luogo', 'disciplina'], ascending=[False, True, True])
                    .head(N_ULTIMI_RISULTATI))
    ultimi_risultati = [to_row(r) for r in recenti_df.to_dict('records')]

    # ------------------------------------------------------ Lista atleti ---
    # df è già ordinato per data, quindi 'last' = valore più recente
    ultima_stagione_societa = int(df['stagione'].max())
    atleti_df = (df.groupby('link_atleta')
                   .agg(atleta=('atleta', 'last'),
                        anno=('anno', 'last'),
                        sesso=('sesso', 'last'),
                        categoria=('categoria', 'last'),
                        prima=('stagione', 'min'),
                        ultima=('stagione', 'max'),
                        n_risultati=('prestazione', 'size'))
                   .reset_index()
                   .sort_values(['ultima', 'atleta'], ascending=[False, True]))
    lista_atleti = []
    for a in atleti_df.to_dict('records'):
        a['url_atleta'] = atleta_url(a['link_atleta'])
        a['attivo'] = a['ultima'] >= ultima_stagione_societa
        lista_atleti.append(a)

    return render_template(
        'societa/profilo.html',
        cod_societa=cod_societa,
        nome_societa=nome_societa,
        link_fidal=link_fidal,
        provincia=cod_societa[:2],
        regione=regione_da_codice(cod_societa),
        n_atleti=len(lista_atleti),
        n_risultati=len(df),
        prima_stagione=int(df['stagione'].min()),
        ultima_stagione=ultima_stagione_societa,
        record_sociali=record_sociali,
        primati_stagionali=primati_stagionali,
        anni=anni,
        ultimi_risultati=ultimi_risultati,
        lista_atleti=lista_atleti,
    )
