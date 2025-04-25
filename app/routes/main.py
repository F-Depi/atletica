import json
from flask import render_template
from app.routes import main_bp

# Load disciplines data
with open('data/dizionario_gare.json') as f:
    DISCIPLINES = json.load(f)

@main_bp.route('/')
def index():
    """Main page route"""
    return render_template('index.html', disciplines=DISCIPLINES)
