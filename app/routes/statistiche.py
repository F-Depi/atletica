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
            'immagine': genera_plot_categorie()
        },
        'record_evoluzione': {
            'titolo': 'Evoluzione dei record nazionali',
            'descrizione': 'Andamento dei record nazionali nelle discipline principali',
            'immagine': genera_plot_record()
        }
    }
    
    return render_template('statistiche/index.html', stats=stats)

def genera_plot_distribuzione():
    """Genera un grafico di distribuzione delle prestazioni"""
    # Esempio di grafico - in produzione dovresti usare dati reali dal DB
    fig, ax = plt.subplots(figsize=(10, 6))
    
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

def genera_plot_categorie():
    """Genera un grafico a barre con il numero di atleti per categoria"""
    # Esempio di grafico - in produzione dovresti usare dati reali dal DB
    fig, ax = plt.subplots(figsize=(10, 6))
    
    categories = ['U14', 'U16', 'U18', 'U20', 'U23', 'SEN', 'ASS']
    num_athletes = [2500, 3200, 2800, 1900, 1200, 900, 2000]
    
    bars = ax.bar(categories, num_athletes, color='#e74c3c')
    
    # Aggiungi i valori sopra le barre
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 50,
                f'{int(height)}', ha='center', va='bottom')
    
    ax.set_title('Numero di atleti attivi per categoria (2024)', fontsize=14)
    ax.set_xlabel('Categoria', fontsize=12)
    ax.set_ylabel('Numero di atleti', fontsize=12)
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    # Salva l'immagine in memoria
    img = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img, format='png', dpi=100)
    img.seek(0)
    plt.close(fig)  # Importante: chiudi esplicitamente la figura
    
    # Converte l'immagine in base64 per l'inclusione nel HTML
    encoded = base64.b64encode(img.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{encoded}"

def genera_plot_record():
    """Genera un grafico dell'evoluzione dei record nazionali"""
    # Esempio di grafico - in produzione dovresti usare dati reali dal DB
    fig, ax = plt.subplots(figsize=(10, 6))
    
    years = [2005, 2008, 2012, 2016, 2020, 2024]
    records_100m = [10.01, 9.99, 9.97, 9.95, 9.93, 9.89]
    records_200m = [20.2, 20.12, 20.08, 20.05, 20.02, 19.98]
    records_400m = [45.69, 45.52, 45.41, 45.33, 45.20, 45.12]
    
    ax.plot(years, records_100m, marker='o', linestyle='-', label='100m', color='#3498db')
    ax.plot(years, records_200m, marker='s', linestyle='-', label='200m', color='#e74c3c')
    ax.plot(years, records_400m, marker='^', linestyle='-', label='400m', color='#2ecc71')
    
    ax.set_title('Evoluzione dei record nazionali (velocità)', fontsize=14)
    ax.set_xlabel('Anno', fontsize=12)
    ax.set_ylabel('Tempo (secondi)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend()
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
