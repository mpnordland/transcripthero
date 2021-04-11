from flask import Blueprint
from .views import BasicViews


def build_blueprint(th_context):
    basic = Blueprint("basic", __name__, template_folder="templates")
    BasicViews(th_context).register(basic)
    return basic
