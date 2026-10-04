"""Istanza condivisa di Flask-Caching.

Va inizializzata nella factory dell'app, vedi note in fondo alla risposta:
    from app.cache import cache
    cache.init_app(app, config={...})
"""

from flask_caching import Cache

cache = Cache()
