from flask import Blueprint
from .views import register


def build_blueprint():
    public = Blueprint("public", __name__)
    register(public)
    return public
