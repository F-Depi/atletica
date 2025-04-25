from flask import Blueprint

# Create blueprints
main_bp = Blueprint('main', __name__)
rankings_bp = Blueprint('rankings', __name__, url_prefix='/rankings')
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import routes to register them with blueprints
from app.routes.main import *
from app.routes.rankings import *
from app.routes.api import *
