from datetime import datetime, timedelta, date
import zeep
from transcript_hero.database.models import (
    Transaction, PayApi, User, SubscriptionType)
from .api import PaymentApi, PaymentInformation


class HsldaApi(PaymentApi):
    def __init__(self, config):
        super().__init__()
        self.payment_error_message = \
            "The code could not be validated. Please double check"\
            " that you have entered it correctly"
        wsdl = config["HSLDA_COUPON_ENDPOINT"]
        self.client = zeep.Client(wsdl=wsdl)
        self.system_code = config["HSLDA_COUPON_SYSTEM_CODE"]
        self.thirty_day_single = config["HSLDA_COUPON_30_SINGLE"]
        self.one_year_single = config['HSLDA_COUPON_1Y_SINGLE']
        self.one_year_multiple = config['HSLDA_COUPON_1Y_MANY']
        self.lifetime_multiple = config['HSLDA_COUPON_LIFE_MANY']
        self.private_school = config['HSLDA_COUPON_PS_MANY']
        self.account_url = config['HSLDA_COUPON_ACCOUNT_URL']

    def calculate_expiration_date(self, coupon):
        offset = timedelta(days=30)
        if (coupon.startswith(self.one_year_single)
                or coupon.startswith(self.one_year_multiple)
                or coupon.startswith(self.private_school)):
            offset = timedelta(days=365)
        elif coupon.startswith(self.lifetime_multiple):
            # 200 years. Should be good enough. I hope.
            offset = timedelta(days=73000)
        return datetime.now() + offset

    def setup(self):
        pass

    def parse_event(self, event, signature):
        return event

    def process_event(self, event):
        self.client.service.RedeemCoupon(self.system_code, event, {})
        expiration = self.calculate_expiration_date(event)
        return event, self.make_transaction(event), expiration

    def make_transaction(self, coupon_code):
        transaction = Transaction()
        transaction.external_id = coupon_code
        transaction.pay_api = PayApi.HSLDA
        transaction.amount = 0
        transaction.date = datetime.now()
        return transaction

    def get_payment_methods(self, user: User):
        payment_methods = []
        if user.subscription:
            payment_methods.append(
                PaymentInformation(None, user.subscription.external_id,
                                   user.subscription.expiration or date.today()
                                   )
            )
        return payment_methods

    def cancel_subscription(self, external_sub_id):
        return self.account_url

    def create_subscription(self, user, token):
        if not self.validate_token(token):
            raise ValueError(
                "Activation code is not valid or already redeemed")

        sub_type = SubscriptionType.ONE_STUDENT
        if (token.startswith(self.one_year_multiple) or
                token.startswith(self.lifetime_multiple)):
            sub_type = SubscriptionType.MANY_STUDENT
        elif token.startswith(self.private_school):
            sub_type = SubscriptionType.UNLIMITED

        _, transaction, exp_date = self.process_event(token)
        return token, sub_type, transaction, exp_date

    def validate_token(self, token):
        coupon = self.client.service.RetrieveCouponByCouponCode(
            self.system_code, token)
        return coupon and not coupon.Redeemed

    def update_payment_information(self, user, token):
        if self.validate_token(token):
            expiration = self.calculate_expiration_date(token)
            _, sub_type = self.create_subscription(user, token)
            return token, sub_type, expiration
        return None, None, None

    def get_plan_info(self):
        return """<p>If you haven't yet purchased a subscription, please
        visit the <a href="https://store.hslda.org/">HSLDA Store</a>. If you
        purchased a subscription but haven't received your code yet, please
        contact us at <a
        href="mailto:transcripts@hslda.org">transcripts@hslda.org</a>.</p>"""

    def get_guide_sections(self):
        return {
            "Renew Subscription": """<p>To renew your subscription, first 
            <a href="https://store.hslda.org/high-school-transcript-service-p262.aspx">
            visit the HSLDA Store</a>. Then click the link in the email you receive.</p>"""
        }

    def get_subscription_help(self):
        return "If you have questions about your subscription, please send us an email at <a href=\"mailto:transcripts@hslda.org\">transcripts@hslda.org</a>"

    def get_payment_update_label(self):
        return "Update Activation Code"
