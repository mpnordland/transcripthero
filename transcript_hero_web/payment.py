from flask import request, flash, get_flashed_messages
from flask_security import current_user
from wtforms.fields import HiddenField
from wtforms.validators import InputRequired, ValidationError
from transcript_hero.database.models import PayApi
from transcript_hero.business.subscriptions import SubscriptionService
from transcript_hero.payment import get_payment_api


def load_payment_api(config):
    pay_api = PayApi[config["TRANSCRIPT_HERO_DEFAULT_PAY_API"]]
    return pay_api, get_payment_api(pay_api, config)


def handle_payment(th_context, user):
    pay_api = PayApi[config["TRANSCRIPT_HERO_DEFAULT_PAY_API"]]
    th_context.sub_manager.subscribe(
        user,
        pay_api,
        request.form["payment_token"]
    )


def warn_subscription_absent(func):
    def warning_wrapper(*args, **kwargs):
        message = "Your subscription has ended"
        flashed = message in map(lambda m: m[1], get_flashed_messages())
        if not flashed and not SubscriptionService.validate(current_user.subscription):
            flash(message, 'warning')
        return func(*args, **kwargs)
    return warning_wrapper


def contribute_payment_form(form_class, config):
    _, payment_api = load_payment_api(config)
    setattr(form_class, 'payment_token',
            HiddenField(validators=[InputRequired()]))

    def validate_payment_token(self, field):
        if not payment_api.validate_token(field.data):
            raise ValidationError(payment_api.payment_error_message)

    setattr(form_class, "validate_payment_token", validate_payment_token)
    return form_class


def setup_payment_processing(app):
    pay_api, payment_api = load_payment_api(app.config)
    payment_api.setup()

    @app.context_processor
    def payment_context_processor():
        payment_context = {
            'pay_include': "payment/{}.html".format(pay_api.name),
            'pay_plans': payment_api.get_plan_info(),
            'help_sections': payment_api.get_guide_sections(),
            'subscription_help': payment_api.get_subscription_help(),
            'payment_context': 'create',
        }

        if pay_api == PayApi.STRIPE:
            payment_context['stripe_key'] = app.config["STRIPE_API_PUB_KEY"],

        return payment_context
