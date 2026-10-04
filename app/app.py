from flask import Flask, render_template, request, jsonify  # vedi nota sotto
from flask_compress import Compress
from flask_wtf.csrf import CSRFProtect
import logging, json, os

from config import SECRET_KEY
from app.cache import cache

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

csrf = CSRFProtect(app)

# --- Cache e compressione ---
cache.init_app(
    app,
    config={
        "CACHE_TYPE": "FileSystemCache",  # parti da qui, senza installare Redis
        "CACHE_DIR": "/tmp/fidal_cache",  # o una cartella tua
        "CACHE_DEFAULT_TIMEOUT": 3600,
        "CACHE_THRESHOLD": 2000,  # numero massimo di voci
    },
)
Compress(app)


# Comando per svuotare la cache: flask --app app.app:app clear-cache
@app.cli.command("clear-cache")
def clear_cache_cmd():
    cache.clear()
    print("Cache svuotata")


"""Questa è la parte per la gestione delle segnalazioni"""
app.config["SECRET_KEY"] = SECRET_KEY

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="app.log",
)
logger = logging.getLogger("athletics")


# Custom error handler specifically for rate limiting
@app.errorhandler(429)
def ratelimit_handler(e):
    # Determine which endpoint triggered the rate limit
    if request.path == "/api/segnala-errore":
        message = "Limite di utilizzo superato: massimo 5 segnalazioni al minuto."
    else:
        # Generic message for other rate-limited endpoints
        message = "Troppe richieste. Riprova più tardi."

    return jsonify(
        {
            "success": False,
            "error": message,
        }
    ), 429


""" Load disciplines data """
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(f"{BASE_DIR}/data/dizionario_gare.json") as f:
    DISCIPLINES = json.load(f)
with open(f"{BASE_DIR}/data/discipline_standard.json") as f:
    DISCIPLINE_STANDARD = json.load(f)
with open(f"{BASE_DIR}/data/regioni_province.json") as f:
    REGIONI_PROVINCE = json.load(f)
with open(f"{BASE_DIR}/data/category_mapping.json") as f:
    CATEGORY_MAPPING = json.load(f)


# Main route
@app.route("/")
def index():
    return render_template("index.html", disciplines=DISCIPLINES)


""" Register blueprints """
from app.rankings import rankings_bp
from app.error_reporting import error_reporting_bp
from app.atleti import atleti_bp
from app.societa import societa_bp

app.register_blueprint(rankings_bp)
app.register_blueprint(error_reporting_bp)
app.register_blueprint(atleti_bp)
app.register_blueprint(societa_bp)


if __name__ == "__main__":
    app.run(debug=False)
