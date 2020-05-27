from flask import Blueprint

bp = Blueprint('collaboration', __name__, template_folder='templates')

from . import routes, models