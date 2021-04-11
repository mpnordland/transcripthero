from flask import request, abort
from transcript_hero.database.models import PayApi
from transcript_hero.payment.hslda import HsldaApi
from transcript_hero_job import InProcessBatchProcessor


class WebhookViews():
    def __init__(self, th_context):
        self.app = th_context.app
        self.batch_processor = th_context.batch_processor

    def stripe(self):
        # Prevent overwhelming server with too large requests
        # Set the max request size to something reasonable.
        # See default_settings.py for default value.
        if request.content_length < self.app.config["STRIPE_MAX_REQUEST_SIZE"]:
            signature = request.headers.get("Stripe-Signature")
            self.batch_processor.renew_subscription(
                PayApi.STRIPE, request.get_data(as_text=True), signature)
        return ""

    def hslda(self):
        coupon = request.args.get("coupon")
        hslda = HsldaApi(self.app.config)
        if not hslda.validate_token(coupon):
            abort(400)
        return ""

    def register(self, webhooks):
        webhooks.add_url_rule('/stripe', 'stripe',
                              self.stripe, methods=["POST"])
        webhooks.add_url_rule('/hslda', 'hslda', self.hslda, methods=["GET"])
