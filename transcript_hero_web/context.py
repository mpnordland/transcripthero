from transcript_hero.business.subscriptions import SubscriptionService, SubscriptionManager
from transcript_hero.business.users import UserService
from transcript_hero.business.transcripts import TranscriptService
from transcript_hero.business.grading import GradingService
from transcript_hero_job import InProcessBatchProcessor


class TranscriptHeroContext():

    SUBSCRIPTION_SERVICE_CLASS = SubscriptionService
    USER_SERVICE_CLASS = UserService
    TRANSCRIPT_SERVICE_CLASS = TranscriptService
    GRADING_SERVICE_CLASS = GradingService
    BATCH_PROCESSOR_CLASS = InProcessBatchProcessor

    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.subscription_service = self.SUBSCRIPTION_SERVICE_CLASS(
            self.db, self.app.config)
        self.user_service = self.USER_SERVICE_CLASS(self.db, self.app.config)
        self.sub_manager = SubscriptionManager(
            self.user_service, self.subscription_service)
        self.transcript_service = self.TRANSCRIPT_SERVICE_CLASS(self.db)

        self.grading_service = self.GRADING_SERVICE_CLASS(self.db)
        self.batch_processor = self.BATCH_PROCESSOR_CLASS(
            self.sub_manager, self.app.config)
