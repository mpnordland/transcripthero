from transcript_hero.database.models import PayApi
from .api import StripeApi, PaymentApi
from .hslda import HsldaApi


def get_payment_api(pay_api: PayApi, config) -> PaymentApi:
    payment_api = None
    if pay_api == PayApi.STRIPE:
        payment_api = StripeApi(config["STRIPE_API_SECRET_KEY"],
                                config["STRIPE_WEBHOOK_SECRET"])
    elif pay_api == PayApi.HSLDA:
        payment_api = HsldaApi(config)

    elif pay_api == PayApi.BRAINTREE:
        pass
    elif pay_api == PayApi.AUTHORIZENET:
        pass

    return payment_api
