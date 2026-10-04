from datetime import date
from urllib.parse import quote

import pandas as pd
from flask import Blueprint, abort, make_response, render_template, request
from sqlalchemy import text

from app.app import DISCIPLINES, REGIONI_PROVINCE
from app.cache import cache
from app.error_reporting import limiter
from app.models import get_db_engine
from app.utils import format_time

societa_bp = Blueprint("societa", __name__, url_prefix="/societa")

TTL = 3600  # secondi di validità della cache (si svuota comunque a ogni import)
TOP_PER_DISCIPLINA = 10  # quanti atleti mostrare nel dettaglio di ogni record sociale
N_ULTIMI_RISULTATI = 300  # quanti risultati mostrare in "Ultimi risultati"
N_MAX_PERIODO = 5000  # tetto risultati quando è attivo un filtro temporale

# Ordine "naturale" delle discipline = ordine in dizionario_gare.json
DISC_ORDER = {d: i for i, d in enumerate(DISCIPLINES)}
DISC_TEMPO = {d for d, i in DISCIPLINES.items() if i["classifica"] == "tempo"}
DISC_VENTO = {d for d, i in DISCIPLINES.items() if i.get("vento") == "sì"}

# Ordine categorie: giovanili → assoluti → master
ORDINE_CAT = {c: i for i, c in enumerate("ERCAJPS")}

GRUPPO = ["disciplina", "ambiente", "sesso"]

# Condizioni comuni a tutte le query: società, discipline note, data e prestazione presenti
WHERE_BASE = """
    cod_società = :cod
    AND disciplina NOT LIKE '%sconosciuto%'
    AND disciplina = ANY(CAST(:discipline AS text[]))
    AND data IS NOT NULL
    AND prestazione IS NOT NULL
"""

COLONNE_RISULTATO = """prestazione, vento, cronometraggio, atleta, link_atleta,
    anno, categoria, posizione, luogo, data, disciplina, ambiente, sesso"""


# --- helper di presentazione ---


def atleta_url(link_atleta):
    """Stesso identificatore usato dalla ricerca atleti (vedi atleti.trova_atleti)"""
    if not link_atleta:
        return None
    identifier = "_".join(link_atleta.split("/")[-2:])
    return "/atleta/" + quote(identifier[:-3] + "=", safe="")


def regione_da_codice(cod_societa):
    provincia = cod_societa[:2]
    for regione, province in REGIONI_PROVINCE.items():
        if provincia in province:
            return regione
    return None


def vento_display(r):
    if r["ambiente"] != "P" or r["disciplina"] not in DISC_VENTO:
        return None
    v = r["vento"]
    return None if pd.isna(v) or v == "" else v


def to_row(r):
    """Da riga del DataFrame a dizionario pronto per il template"""
    return {
        "disciplina": r["disciplina"],
        "ambiente": r["ambiente"],
        "sesso": r["sesso"],
        "prestazione_display": format_time(
            r["prestazione"], DISCIPLINES[r["disciplina"]], r["cronometraggio"]
        ),
        "vento": vento_display(r),
        "atleta": r["atleta"],
        "url_atleta": atleta_url(r["link_atleta"]),
        "anno": r["anno"],
        "categoria": r["categoria"],
        "posizione": r["posizione"],
        "luogo": r["luogo"],
        "data": r["data"],
    }


def chiave_ordine(x):
    return (x["sesso"] != "M", DISC_ORDER.get(x["disciplina"], 999), x["ambiente"])


def chiave_categoria(c):
    num = "".join(ch for ch in c if ch.isdigit())
    return (ORDINE_CAT.get(c[:1], 99), int(num) if num else 0, c[1:2] != "M", c)


def raggruppa_record(df):
    """Da un DataFrame già limitato ai top (e ordinato per posizione) a una lista di
    record, uno per disciplina/ambiente/sesso"""
    record = []
    for (disc, amb, sesso), g in df.groupby(GRUPPO, sort=False):
        righe = [to_row(r) for r in g.to_dict("records")]
        record.append(
            {
                "disciplina": disc,
                "ambiente": amb,
                "sesso": sesso,
                "best": righe[0],
                "top": righe,
            }
        )
    record.sort(key=chiave_ordine)
    return record


# --- helper SQL ---


def _params(cod, **extra):
    return {"cod": cod, "discipline": list(DISC_ORDER), **extra}


def _filtri(categoria="", da=None, a=None):
    """Clausole opzionali (categoria, intervallo di date [da, a)) con i relativi parametri.
    Usiamo intervalli su `data` e non EXTRACT(), così l'indice resta utilizzabile."""
    sql, params = "", {}
    if categoria:
        sql += " AND categoria = :categoria"
        params["categoria"] = categoria
    if da:
        sql += " AND data >= :da"
        params["da"] = da
    if a:
        sql += " AND data < :a"
        params["a"] = a
    return sql, params


def intervallo_periodo(periodo, oggi):
    """Da '3m' / '6m' / 'ytd' / '2023' a (da, a); `a` è esclusivo, None = aperto"""
    if periodo == "3m":
        return (oggi - pd.DateOffset(months=3)).date(), None
    if periodo == "6m":
        return (oggi - pd.DateOffset(months=6)).date(), None
    anno = oggi.year if periodo == "ytd" else int(periodo)
    return date(anno, 1, 1), date(anno + 1, 1, 1)


def leggi(sql, params):
    """Esegue la query e restituisce un DataFrame con date vere e None al posto dei NaN"""
    with get_db_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"])
    return df.astype(object).where(df.notna(), None)


# --- accesso ai dati (tutto in cache) ---


@cache.memoize(TTL)
def info_societa(cod):
    with get_db_engine().connect() as conn:
        row = conn.execute(
            text("""
            SELECT società, link_società
            FROM results
            WHERE cod_società = :cod
            ORDER BY data DESC NULLS LAST
            LIMIT 1
        """),
            {"cod": cod},
        ).fetchone()
    return tuple(row) if row else None


@cache.memoize(TTL)
def statistiche(cod):
    """Statistiche di intestazione e valori dei filtri: una sola query aggregata"""
    sql = f"""
        WITH base AS (
            SELECT link_atleta, categoria, sesso,
                   CAST(EXTRACT(year FROM data) AS int) AS stagione
            FROM results
            WHERE {WHERE_BASE}
        )
        SELECT COUNT(*)                    AS n_risultati,
               COUNT(DISTINCT link_atleta) AS n_atleti,
               MIN(stagione)               AS prima,
               MAX(stagione)               AS ultima,
               array_agg(DISTINCT stagione) AS stagioni,
               array_agg(DISTINCT categoria)
                   FILTER (WHERE categoria IS NOT NULL AND categoria <> '') AS categorie,
               COUNT(*) FILTER (WHERE sesso = 'M') AS n_m,
               COUNT(*) FILTER (WHERE sesso = 'F') AS n_f
        FROM base
    """
    with get_db_engine().connect() as conn:
        r = conn.execute(text(sql), _params(cod)).mappings().one()
    if not r["n_risultati"]:
        return None
    return {
        "n_risultati": r["n_risultati"],
        "n_atleti": r["n_atleti"],
        "prima": r["prima"],
        "ultima": r["ultima"],
        "anni": sorted(r["stagioni"], reverse=True),
        "categorie": sorted(r["categorie"] or [], key=chiave_categoria),
        # Sesso predefinito nei filtri: quello con più risultati
        "sesso_default": "F" if r["n_f"] > r["n_m"] else "M",
    }


@cache.memoize(TTL)
def record_sociali(cod, categoria="", anno=None):
    """Top N atleti per disciplina/ambiente/sesso, calcolati interamente dal database.
    Con `anno` sono i primati di quella stagione, altrimenti i record assoluti.
    Si escludono i risultati ventosi (> +2.0 m/s o vento mancante)."""
    da, a = (date(anno, 1, 1), date(anno + 1, 1, 1)) if anno else (None, None)
    filtri, fparams = _filtri(categoria, da, a)
    sql = f"""
        WITH base AS (
            SELECT {COLONNE_RISULTATO},
                   CASE WHEN disciplina = ANY(CAST(:tempo AS text[]))
                        THEN prestazione ELSE -prestazione END AS sort_key,
                   CASE WHEN CAST(vento AS text) ~ '^[+-]?[0-9]+([.][0-9]+)?$'
                        THEN CAST(CAST(vento AS text) AS numeric) END AS vento_num
            FROM results
            WHERE {WHERE_BASE} {filtri}
        ),
        validi AS (
            SELECT * FROM base
            WHERE NOT (ambiente = 'P' AND disciplina = ANY(CAST(:vento_disc AS text[])))
                  OR round(vento_num, 1) <= 2.0
        ),
        migliori AS (  -- la migliore prestazione di ogni atleta per gruppo
            SELECT DISTINCT ON (disciplina, ambiente, sesso, link_atleta) *
            FROM validi
            ORDER BY disciplina, ambiente, sesso, link_atleta, sort_key, data
        ),
        classifica AS (
            SELECT *, ROW_NUMBER() OVER (
                       PARTITION BY disciplina, ambiente, sesso
                       ORDER BY sort_key, data, link_atleta) AS rn
            FROM migliori
        )
        SELECT {COLONNE_RISULTATO}
        FROM classifica
        WHERE rn <= :top
        ORDER BY disciplina, ambiente, sesso, rn
    """
    params = _params(
        cod,
        tempo=sorted(DISC_TEMPO),
        vento_disc=sorted(DISC_VENTO),
        top=TOP_PER_DISCIPLINA,
        **fparams,
    )
    df = leggi(sql, params)
    return raggruppa_record(df) if not df.empty else []


@cache.memoize(TTL)
def ultimi_risultati(cod, categoria="", periodo=""):
    """(righe, totale) dei risultati più recenti. Limite e totale calcolati dal DB."""
    da, a = intervallo_periodo(periodo, pd.Timestamp.today().normalize()) if periodo else (None, None)
    filtri, fparams = _filtri(categoria, da, a)
    sql = f"""
        SELECT {COLONNE_RISULTATO}, COUNT(*) OVER () AS n_tot
        FROM results
        WHERE {WHERE_BASE} {filtri}
        ORDER BY data DESC, luogo ASC, disciplina ASC
        LIMIT :limite
    """
    limite = N_MAX_PERIODO if periodo else N_ULTIMI_RISULTATI
    df = leggi(sql, _params(cod, limite=limite, **fparams))
    if df.empty:
        return [], 0
    return [to_row(r) for r in df.to_dict("records")], int(df["n_tot"].iloc[0])


@cache.memoize(TTL)
def lista_atleti(cod, categoria=""):
    """Un record per atleta. 'Attivo' = ha gareggiato nell'ultima stagione della società,
    a prescindere dalla categoria filtrata."""
    cat_sql = " AND categoria = :categoria" if categoria else ""
    fparams = {"categoria": categoria} if categoria else {}
    sql = f"""
        WITH base AS (
            SELECT link_atleta, atleta, anno, sesso, categoria, data,
                   CAST(EXTRACT(year FROM data) AS int) AS stagione
            FROM results
            WHERE {WHERE_BASE} AND link_atleta IS NOT NULL
        ),
        attivi AS (
            SELECT DISTINCT link_atleta FROM base
            WHERE stagione = (SELECT MAX(stagione) FROM base)
        )
        SELECT link_atleta,
               (array_agg(atleta    ORDER BY data DESC))[1] AS atleta,
               (array_agg(anno      ORDER BY data DESC))[1] AS anno,
               (array_agg(sesso     ORDER BY data DESC))[1] AS sesso,
               (array_agg(categoria ORDER BY data DESC))[1] AS categoria,
               MIN(stagione) AS prima,
               MAX(stagione) AS ultima,
               COUNT(*)      AS n_risultati,
               link_atleta IN (SELECT link_atleta FROM attivi) AS attivo
        FROM base
        WHERE TRUE {cat_sql}
        GROUP BY link_atleta
        ORDER BY ultima DESC, atleta
    """
    df = leggi(sql, _params(cod, **fparams))
    righe = df.to_dict("records")
    for a in righe:
        a["url_atleta"] = atleta_url(a["link_atleta"])
    return righe


@cache.memoize(TTL)
def contesto_profilo(cod, categoria):
    """Tutto ciò che serve alla pagina principale (intestazione + record sociali).
    Mettiamo in cache i dati e non l'HTML, così base.html può restare per-utente."""
    nome, link_fidal = info_societa(cod)
    stats = statistiche(cod)
    return {
        "cod_societa": cod,
        "nome_societa": nome,
        "link_fidal": link_fidal,
        "provincia": cod[:2],
        "regione": regione_da_codice(cod),
        "n_atleti": stats["n_atleti"],
        "n_risultati": stats["n_risultati"],
        "prima_stagione": stats["prima"],
        "ultima_stagione": stats["ultima"],
        "sesso_default": stats["sesso_default"],
        "categorie": stats["categorie"],
        "anni": stats["anni"],
        "record_sociali": record_sociali(cod, categoria),
    }


# --- frammenti HTML (in cache già renderizzati: sono partial senza dati per-utente) ---


@cache.memoize(TTL)
def html_stagionali(cod, anno, categoria):
    return render_template(
        "societa/_stagionali.html", record=record_sociali(cod, categoria, anno)
    )


@cache.memoize(TTL)
def html_recenti(cod, categoria, periodo):
    righe, totale = ultimi_risultati(cod, categoria, periodo)
    return render_template(
        "societa/_recenti.html", ultimi_risultati=righe, n_recenti_totali=totale
    )


@cache.memoize(TTL)
def html_atleti(cod, categoria):
    return render_template("societa/_atleti.html", lista_atleti=lista_atleti(cod, categoria))


# --- route ---


def _carica(cod_societa):
    cod = cod_societa.upper()
    stats = statistiche(cod)
    if not stats:
        abort(404)
    return cod, stats


def _filtri_validi(stats):
    """Categoria e periodo dalla query string, normalizzati (valori sconosciuti → vuoto).
    Così le chiavi di cache restano un insieme finito."""
    categoria = request.args.get("categoria", "")
    if categoria not in stats["categorie"]:
        categoria = ""
    periodo = request.args.get("periodo", "")
    if periodo not in {"3m", "6m", "ytd"} | {str(a) for a in stats["anni"]}:
        periodo = ""
    return categoria, periodo


def frammento(html):
    resp = make_response(html)
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@societa_bp.route("/<cod_societa>", methods=["GET"])
@limiter.limit("30/minute")
def societa_profilo(cod_societa):
    cod, stats = _carica(cod_societa)
    categoria, periodo = _filtri_validi(stats)
    oggi = pd.Timestamp.today().normalize()

    return render_template(
        "societa/profilo.html",
        **contesto_profilo(cod, categoria),
        # filtri
        categoria=categoria,
        periodo=periodo,
        anno_corrente=oggi.year,
        anni_periodo=[a for a in stats["anni"] if a != oggi.year],
        n_ultimi=N_ULTIMI_RISULTATI,
    )


@societa_bp.route("/<cod_societa>/stagionali/<int:anno>", methods=["GET"])
@limiter.limit("120/minute")
def societa_stagionali(cod_societa, anno):
    cod, stats = _carica(cod_societa)
    if anno not in stats["anni"]:
        abort(404)
    categoria, _ = _filtri_validi(stats)
    return frammento(html_stagionali(cod, anno, categoria))


@societa_bp.route("/<cod_societa>/recenti", methods=["GET"])
@limiter.limit("120/minute")
def societa_recenti(cod_societa):
    cod, stats = _carica(cod_societa)
    categoria, periodo = _filtri_validi(stats)
    return frammento(html_recenti(cod, categoria, periodo))


@societa_bp.route("/<cod_societa>/atleti", methods=["GET"])
@limiter.limit("120/minute")
def societa_atleti(cod_societa):
    cod, stats = _carica(cod_societa)
    categoria, _ = _filtri_validi(stats)
    return frammento(html_atleti(cod, categoria))
