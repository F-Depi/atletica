from flask import Blueprint, render_template

statistiche_bp = Blueprint('statistiche', __name__)

@statistiche_bp.route('/statistiche')
def index():
    return render_template('statistiche/index.html')

import matplotlib.pyplot as plt
import os

def genera_plot_statistiche():
    # Crea un semplice grafico di esempio
    x = [1, 2, 3, 4]
    y = [10, 20, 25, 30]

    plt.figure()
    plt.plot(x, y)
    plt.title('Statistiche di esempio')

    # Percorso completo verso la cartella static
    static_path = os.path.join('app', 'static', 'images')
    os.makedirs(static_path, exist_ok=True)

    # Salva l'immagine
    plt.savefig(os.path.join(static_path, 'statistiche_plot.png'))
    plt.close()

