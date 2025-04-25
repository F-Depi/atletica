from flask import Blueprint

# Create blueprints
main_bp = Blueprint('main', __name__)
rankings_bp = Blueprint('rankings', __name__, url_prefix='/rankings')
api_bp = Blueprint('api', __name__, url_prefix='/api')
statistics_bp = Blueprint('statistics', __name__, url_prefix='/statistics')

# Import routes to register them with blueprints
from app.routes.statistics import *
from app.routes.main import *
from app.routes.rankings import *
from app.routes.api import *
