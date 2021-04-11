from transcript_hero.payment import get_payment_api
from transcript_hero.business.subscriptions import SubscriptionManager


def expire_subscriptions(sub_manager: SubscriptionManager):
    sub_manager.expire_all()


def renew_subscription(sub_manager, pay_api: int, event, signature):
    """
    This task gets started from webhooks for each pay method
    and then this constructs the appropriate PaymentApi
    and gets the updated subscription and new transaction
    and renews the subscription
    """
    # Enums are not JSON serializable. Ints are.
    # The calling code will convert to int, now
    # convert it back here.
    pay_api = PayApi(pay_api)

    pay_api = get_payment_api(pay_api, config)
    event = pay_api.parse_event(event, signature)
    external_sub_id, transaction, exp_date = pay_api.process_event(event)
    subscription = sub_manager.subscription_service.get_by_external_id(
        external_sub_id)
    sub_manager.renew(subscription, transaction, exp_date)


# def renew_subscriptions():
#     sub_service = SubscriptionService(db)
#     expiring = sub_service.expiring(datetime.now()+timedelta(days=5))
#     for subscription in expiring:
#         pass
