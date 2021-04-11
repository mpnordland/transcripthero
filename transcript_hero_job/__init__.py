from dramatiq import Message
from dramatiq.broker import get_broker
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.middleware import (
    AgeLimit, TimeLimit, ShutdownNotifications, Callbacks, Pipelines, Retries)

from transcript_hero_job.tasks import renew_subscription


class DramatiqBatchProcessor():
    def __init__(self, sub_manager, config):
        rabbitmq_host = config.get("RABBITMQ_HOST", None)
        if rabbitmq_host is not None:
            middleware = [
                AgeLimit(), TimeLimit(), ShutdownNotifications(),
                Callbacks(), Pipelines(), Retries()
            ]
            self.broker = RabbitmqBroker(
                host=rabbitmq_host, middleware=middleware)
        else:
            self.broker = get_broker()

    def _call_actor(self, actor_name, *args, **kwargs):
        return self.broker.enqueue(Message(
            queue_name="default",
            actor_name=actor_name,
            args=args, kwargs=kwargs,
            options={},
        ))

    def renew_subscription(self, pay_api, event, signature):

        # pay_api is an instance of the PayApi enum
        # we need to send its value because enums are not
        # JSON serializable.
        return self._call_actor("renew_subscription", pay_api.value, event, signature)

    def expire_subscriptions(self):
        return self._call_actor("expire_subscriptions")


class InProcessBatchProcessor():
    def __init__(self, sub_manager, config):
        self.sub_manager = sub_manager

    def renew_subscription(self, pay_api, event, signature):
        renew_subscription(self.sub_manager, pay_api, event, signature)

    def expire_subscriptions(self):
        self.sub_manager.expire_all()
