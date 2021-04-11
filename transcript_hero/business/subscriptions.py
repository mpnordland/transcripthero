from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from transcript_hero.database.models import (
    Subscription, SubscriptionStanding, Transaction, PayApi)
from transcript_hero.payment import get_payment_api


class SubscriptionManager:
    def __init__(self, user_service, subscription_service):
        self.user_service = user_service
        self.subscription_service = subscription_service
        self.grace_period = timedelta(days=5)

    def add_grace_period(self, exp_date):
        return exp_date + self.grace_period

    def subscribe(self, user, pay_api=None, token=None):
        subscription = self.subscription_service.create(user)

        if pay_api is not None and token is not None:
            payment_api = get_payment_api(
                pay_api, self.subscription_service.config)
            external_id, sub_type, transaction, exp_date = payment_api.create_subscription(
                user, token
            )
            subscription.external_id = external_id
            subscription.type = sub_type

            if transaction:
                self.renew(subscription, transaction, exp_date)
            else:
                subscription.pay_api = pay_api
                self.subscription_service.save(subscription)

    def expire(self, subscription: Subscription):
        subscription.standing = SubscriptionStanding.DROPPED
        self.subscription_service.save(subscription)
        self.user_service.stop_benefits(subscription.user)

    def expire_all(self):
        """
        End all subscriptions which have expired.
        """
        expiring = self.subscription_service.get_expiring(datetime.now())
        for subscription in expiring:
            self.expire(subscription)

    def renew(self, subscription: Subscription,
              transaction: Transaction, exp_date: datetime):
        subscription.standing = SubscriptionStanding.ACTIVE
        subscription.pay_api = transaction.pay_api
        subscription.expiration = self.add_grace_period(exp_date)
        # this saves the subscription too
        self.subscription_service.add_transaction(subscription, transaction)

    def cancel(self, subscription: Subscription):
        """
        This method cancels the subscription with the payment processor
        and marks the subscription as canceled. It does not immediatly
        remove benefits. Instead, that will be handled when the
        subscription expires.
        """
        payment_api = get_payment_api(
            subscription.pay_api, self.subscription_service.config)
        destination = payment_api.cancel_subscription(subscription.external_id)
        subscription.standing = SubscriptionStanding.CANCELED
        self.subscription_service.save(subscription)
        return destination

    def get_payment_methods(self, subscription: Subscription):
        if subscription and subscription.pay_api:
            payment_api = get_payment_api(
                subscription.pay_api, self.subscription_service.config)
            return payment_api.get_payment_methods(subscription.user)
        return []

    def update_payment_method(self, subscription: Subscription, token):
        default_pay_api = self.subscription_service.config['TRANSCRIPT_HERO_DEFAULT_PAY_API']
        payment_api = get_payment_api(
            subscription.pay_api or PayApi[default_pay_api], self.subscription_service.config)

        try:
            updates = payment_api.update_payment_information(
                subscription.user, token)
            new_ext_id, new_sub_type, new_exp_date = updates
            if new_ext_id or new_sub_type or new_exp_date:
                if new_sub_type is not None:
                    subscription.type = new_sub_type

                if new_ext_id is not None:
                    subscription.external_id = new_ext_id

                if new_exp_date is not None:
                    new_exp_date = self.add_grace_period(new_exp_date)
                    subscription.expiration = new_exp_date
                self.subscription_service.save(subscription)

        except Exception as e:
            print(e)
            return False

        return True


class SubscriptionService:

    def __init__(self, db, config):
        self.db = db
        self.config = config

    def create(self, user):
        subscription = Subscription()

        subscription.user_id = user.id
        subscription.standing = SubscriptionStanding.PENDING

        return subscription

    def get_by_external_id(self, external_id) -> Subscription:
        with self.db.session() as session:
            return session.query(Subscription).filter(
                Subscription.external_id == external_id).first()

    def get_expiring(self, datetime: datetime):
        with self.db.session() as session:
            expiring = session.query(Subscription).filter(
                and_(Subscription.expiration <= datetime,
                     or_(Subscription.standing == SubscriptionStanding.ACTIVE,
                         Subscription.standing == SubscriptionStanding.CANCELED)
                     )).all()
            return expiring

    def add_transaction(self, subscription, transaction):
        transaction.subscription_id = subscription.id
        transaction.user_id = subscription.user_id
        with self.db.session() as session:
            session.add(subscription)
            session.add(transaction)
        self.save(subscription)

    def save(self, subscription: Subscription):
        self.db.save(subscription)

    @staticmethod
    def validate(subscription: Subscription) -> bool:
        if (subscription is not None and
                subscription.standing == SubscriptionStanding.DROPPED):
            return False
        return True
