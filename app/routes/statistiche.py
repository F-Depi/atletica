from flask import render_template, Blueprint
import matplotlib
matplotlib.use('Agg')  # Imposta il backend non interattivo PRIMA di importare pyplot
import matplotlib.pyplot as plt
import io
import base64
import os
import pandas as pd
from app.services.database import get_db_engine
from sqlalchemy import text

statistiche_bp = Blueprint('statistiche', __name__, url_prefix='/statistiche')

@statistiche_bp.route('/')
def index():
    # Generiamo le statistiche al momento della richiesta
    stats = {
        'distribuzione_prestazioni': {
            'titolo': 'Distribuzione delle prestazioni nel tempo',
            'descrizione': 'Evoluzione delle prestazioni nelle principali discipline dal 2005 ad oggi',
            'immagine': genera_plot_distribuzione()
        },
        'atleti_per_categoria': {
            'titolo': 'Numero di atleti per categoria',
            'descrizione': 'Confronto tra il numero di atleti attivi nelle diverse categorie',
            'immagine': '/static/images/normal/test.png',  # Normal size
            'immagine_small': '/static/images/small/test.png',  # Small size
            'immagine_really_small': '/static/images/really_small/test.png'  # Really small size
        }
    }
    
    return render_template('statistiche/index.html', stats=stats)

def genera_plot_distribuzione():
    """Genera un grafico di distribuzione delle prestazioni"""
    # Esempio di grafico - in produzione dovresti usare dati reali dal DB
    fig, ax = plt.subplots(figsize=(5, 3))
    
    years = range(2005, 2026)
    performances_100m = [10.2, 10.15, 10.17, 10.12, 10.08, 10.05, 10.04, 10.02, 10.01, 10.0, 
                       9.99, 9.98, 9.97, 9.96, 9.95, 9.94, 9.93, 9.92, 9.91, 9.9, 9.89]
    
    ax.plot(years, performances_100m, marker='o', linestyle='-', color='#3498db')
    ax.set_title('Evoluzione prestazioni 100m (1° classificato)', fontsize=14)
    ax.set_xlabel('Anno', fontsize=12)
    ax.set_ylabel('Tempo (secondi)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.invert_yaxis()  # Inverti l'asse Y in modo che i tempi migliori siano più in alto
    
    # Salva l'immagine in memoria
    img = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img, format='png', dpi=100)
    img.seek(0)
    plt.close(fig)  # Importante: chiudi esplicitamente la figura
    
    # Converte l'immagine in base64 per l'inclusione nel HTML
    encoded = base64.b64encode(img.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{encoded}"

import matplotlib.pyplot as plt
from PIL import Image
import os

# Generate and save the chart at different sizes
def generate_chart(data, title, save_path):
    # Your existing chart generation code
    fig, ax = plt.subplots(figsize=(12, 8))
    years = range(2005, 2026)
    performances_100m = [10.2, 10.15, 10.17, 10.12, 10.08, 10.05, 10.04, 10.02, 10.01, 10.0, 
                       9.99, 9.98, 9.97, 9.96, 9.95, 9.94, 9.93, 9.92, 9.91, 9.9, 9.89]
    
    ax.plot(years, performances_100m, marker='o', linestyle='-', color='#3498db')
    ax.set_title('Evoluzione prestazioni 100m (1° classificato)', fontsize=14)
    ax.set_xlabel('Anno', fontsize=12)
    ax.set_ylabel('Tempo (secondi)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.invert_yaxis()  # Inverti l'asse Y in modo che i tempi migliori siano più in alto
    plt.title(title)
    
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(save_path + '/normal/'), exist_ok=True)
    os.makedirs(os.path.dirname(save_path + '/small/'), exist_ok=True)
    os.makedirs(os.path.dirname(save_path + '/really_small/'), exist_ok=True)
    
    # Save the normal size image
    normal_path = save_path + '/normal/' + title.replace(' ', '_') + '.png'
    plt.savefig(normal_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    # Create smaller versions with PIL
    img = Image.open(normal_path)
    
    # Small version (768px width)
    small_width = 768
    ratio = small_width / img.width
    small_height = int(img.height * ratio)
    small_img = img.resize((small_width, small_height), Image.LANCZOS)
    small_img.save(save_path + '/small/' + title.replace(' ', '_') + '.png')
    
    # Really small version (320px width)
    really_small_width = 320
    ratio = really_small_width / img.width
    really_small_height = int(img.height * ratio)
    really_small_img = img.resize((really_small_width, really_small_height), Image.LANCZOS)
    really_small_img.save(save_path + '/really_small/' + title.replace(' ', '_') + '.png')

generate_chart(None, "test", "app/static/images")
