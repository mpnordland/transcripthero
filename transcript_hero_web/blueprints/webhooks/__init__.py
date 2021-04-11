from flask import Blueprint
from .views import WebhookViews


def build_blueprint(th_context):
    webhooks = Blueprint("webhooks", __name__)
    webhook_views = WebhookViews(th_context)
    webhook_views.register(webhooks)
    return webhooks
