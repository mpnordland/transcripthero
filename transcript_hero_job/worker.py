import os
import time
import functools
from datetime import datetime
from sqlalchemy.orm import scoped_session
import dramatiq
from dramatiq.middleware import (
    AgeLimit, TimeLimit, ShutdownNotifications, Callbacks, Pipelines, Retries)
from transcript_hero import parse_config
from transcript_hero.database import Database
from transcript_hero.database.models import PayApi
from transcript_hero.business.subscriptions import SubscriptionService, SubscriptionManager
from transcript_hero.business.users import UserService
from transcript_hero_job.tasks import expire_subscriptions, renew_subscription
config = parse_config(os.environ["TRANSCRIPT_HERO_SETTINGS"])
db = Database(config["SQLALCHEMY_DATABASE_URI"], scoped_session=scoped_session)

subscription_service = SubscriptionService(db, config)
user_service = UserService(db, config)
sub_manager = SubscriptionManager(user_service, subscription_service)

rabbitmq_host = config.get("RABBITMQ_HOST", None)
if rabbitmq_host is not None:
    middleware = [
        AgeLimit(), TimeLimit(), ShutdownNotifications(),
        Callbacks(), Pipelines(), Retries()
    ]
    broker = dramatiq.brokers.rabbitmq.RabbitmqBroker(
        host=rabbitmq_host, middleware=middleware)
    dramatiq.set_broker(broker)
    tries = 1
    while True:
        try:
            # throws an exception if we are not connected
            # to RabbitMQ
            broker.connection
            break  # if we reach here we are connected and should stop waiting
        except Exception as ce:
            seconds = tries * 2
            print("Connection to Rabbitmq failed. Sleeping for",
                  seconds, "seconds.")
            time.sleep(seconds)

        tries += 1


@functools.wraps(dramatiq.actor)
def actor(fn=None, **kwargs):

    def decorator(fn):

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            db._session.remove()
            return result

        return dramatiq.actor(wrapper)

    if fn is None:
        return decorator
    return decorator(fn)


actor(functools.partial(expire_subscriptions, sub_manager))

# max_age = 5 minutes is how long signatures are valid
actor(functools.partial(renew_subscription, sub_manager), max_age=300000)
