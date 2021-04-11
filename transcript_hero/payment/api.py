from datetime import datetime, date
import stripe
from transcript_hero.database.models import (
    Transaction, PayApi, User, SubscriptionType)


class PaymentInformation:
    def __init__(self, kind, number, expires):
        self.kind = kind
        self.number = number
        self.expires = expires

    @property
    def expired(self):
        return date.today() > self.expires


class PaymentApi:
    def __init__(self):
        self.payment_error_message = \
            "There was an error processing"\
            " your payment information, please try again"

    def setup(self):
        raise NotImplementedError

    def validate_token(self, token):
        raise NotImplementedError

    def parse_event(self, event):
        raise NotImplementedError

    def process_event(self, event):
        raise NotImplementedError

    def get_payment_methods(self, user: User):
        raise NotImplementedError

    def create_subscription(self, user: User, token=None):
        raise NotImplementedError

    def cancel_subscription(self, external_sub_id):
        raise NotImplementedError

    def update_payment_information(self, user, token):
        raise NotImplementedError

    def get_plan_info(self):
        raise NotImplementedError

    def get_guide_sections(self):
        """ If implemented, these sections will be placed under the Account
        section of the user guide
        return a dict of "Section Name": "Section content"
        """
        return None

    def get_subscription_help(self):
        return None

    def can_cancel(self):
        return False

    def get_payment_update_label(self):
        return None


class StripeApi(PaymentApi):
    def __init__(self, api_key, webhook_secret):
        super().__init__()
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.product_id = "prod_transcripthero"
        self.plan_id = 'transcript-hero-subscriber'
        self.plan_amount = 16.00
        self.token_name = 'stripeToken'

    def setup(self):
        """
        Sets up product and plan in stripe for use in creating subscriptions
        """
        product_name = "Transcript Hero"
        try:
            stripe.Product.retrieve(
                self.product_id, api_key=self.api_key)
        except stripe.error.InvalidRequestError:
            stripe.Product.create(
                id=self.product_id,
                name=product_name,
                type="service",
                api_key=self.api_key
            )
        plan_nickname = 'Subscriber'
        try:
            stripe.Plan.retrieve(
                self.plan_id,
                api_key=self.api_key)
        except stripe.error.InvalidRequestError:
            stripe.Plan.create(
                id=self.plan_id,
                currency='usd',
                interval='year',
                product=self.product_id,
                nickname=plan_nickname,
                amount=self._convert_dollars_to_cents(self.plan_amount),
                api_key=self.api_key
            )

    def _convert_cents_to_dollars(self, cents):
        return cents / 100

    def _convert_dollars_to_cents(self, dollars):
        return int(dollars * 100)

    def parse_event(self, event, signature):
        try:
            event = stripe.Webhook.construct_event(
                event, signature, self.webhook_secret,
                api_key=self.api_key
            )
            return event
        except (ValueError, stripe.error.SignatureVerificationError):
            return None

    def process_event(self, event):
        invoice = stripe.Invoice.construct_from(
            event.data.object, self.api_key)
        ext_sub = stripe.Subscription.retrieve(invoice.subscription,
                                               api_key=self.api_key)
        transaction = self.make_transaction(invoice)
        return (invoice.subscription, transaction,
                datetime.utcfromtimestamp(ext_sub.current_period_end))

    def make_transaction(self, invoice):
        # TODO: only create one transaction
        # in case this gets called twice
        # with the same invoice
        transaction = Transaction()
        transaction.external_id = invoice.id
        transaction.pay_api = PayApi.STRIPE
        transaction.amount = self._convert_cents_to_dollars(
            invoice.amount_paid)
        transaction.date = datetime.utcfromtimestamp(invoice.date)
        return transaction

    def validate_token(self, token):
        try:
            stripe.Token.retrieve(token, api_key=self.api_key)
            return True
        except stripe.error.StripeError:
            return False

    def create_subscription(self, user: User, token=None):
        """
        Creates and returns a subscription for the given user
        """

        customers = self.get_customers(user.email)

        if customers.data:
            customer = customers.data[0]
            if token:
                self.add_new_payment_information(customer, token)

        elif self.validate_token(token):
            customer = stripe.Customer.create(
                source=token,
                email=user.email,
                api_key=self.api_key
            )
        else:
            msg = "{} has no customer in stripe and no token was passed"
            raise ValueError(msg.format(user))

        try:
            ext_sub = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {
                        "plan": self.plan_id,
                    },
                ],
                api_key=self.api_key
            )
            return ext_sub.id, SubscriptionType.ONE_STUDENT, None, None
        except stripe.error.StripeError as e:
            msg = "Creating the subscription for {} failed: {}"
            raise ValueError(msg.format(user, e.user_message))

    def get_customers(self, email):
        customers = stripe.Customer.list(
            email=email, api_key=self.api_key)
        return customers

    def _convert_source_to_paymentinfo(self, source):
        return PaymentInformation(source.brand, source.last4,
                                  date(source.exp_year, source.exp_month, 1))

    def get_payment_methods(self, user: User):
        customers = self.get_customers(user.email)
        payment_methods = []
        if customers.data:
            customer = customers.data[0]
            payment_methods = map(
                self._convert_source_to_paymentinfo, customer.sources.data)
        return payment_methods

    def cancel_subscription(self, external_sub_id):
        sub = stripe.Subscription.retrieve(
            external_sub_id, api_key=self.api_key)
        sub.delete()
        return None

    def add_new_payment_information(self, customer, token):
        card = customer.sources.create(source=token)
        customer.default_source = card.id
        customer.save()
        return card

    def update_payment_information(self, user, token):
        customers = self.get_customers(user.email)
        if customers.data:
            customer = customers.data[0]
            try:
                old_card = customer.default_source
                card = self.add_new_payment_information(customer, token)
                sub = stripe.Subscription.retrieve(
                    user.subscription.external_id,
                    api_key=self.api_key)
                sub.default_source = card.id
                sub.save()
                customer.sources.retrieve(old_card).delete()
            except stripe.error.CardError:
                pass
        return None, None, None

    def get_plan_info(self):
        return """<h3>$16 / year</h3>
                    <ul>
                        <li>5 transcripts</li>
                        <li>Printable PDFs</li>
                        <li>Accessible anywhere</li>
                    </ul>"""

    def can_cancel(self):
        return True
