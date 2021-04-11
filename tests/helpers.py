import os
import unittest
from datetime import datetime, timedelta
from sqlalchemy.orm import scoped_session
from flask_security.utils import hash_password
from transcript_hero import parse_config
from transcript_hero.database import Database
from transcript_hero.database.models import Role, User
from transcript_hero.business.users import UserService
from transcript_hero.business.transcripts import TranscriptService
from transcript_hero.business.subscriptions import SubscriptionService

from transcript_hero_web import app


class TranscriptHeroTestCase(unittest.TestCase):

    def setUp(self):
        self.config = parse_config(os.environ["TRANSCRIPT_HERO_SETTINGS"])
        self.db = Database("sqlite://",
                           scoped_session=scoped_session)

        self.db.metadata.create_all(self.db.engine)
        self.db.save(Role(name="subscriber"))
        self.db.save(Role(name="superuser"))

        self.user_service = UserService(self.db, self.config)
        self.transcript_service = TranscriptService(self.db)
        self.subscription_service = SubscriptionService(self.db, self.config)
        self.setUpExtra()

    def setUpExtra(self):
        raise NotImplemented()

    def make_test_user(self, name, email, password):
        user = User()
        user.email = email
        user.name = name
        user.active = True
        user.confirmed_at = datetime.now()
        with app.app_context():
            user.password = hash_password(password)
        self.user_service.save(user)
        return user

    def make_test_subscription(self, user, standing, sub_type):
        # Make a subscription without a pay method
        # should be enough for most cases
        sub = self.subscription_service.create(user)
        sub.standing = standing
        sub.type = sub_type
        # one year expiration should be enough afaik, there's no code that
        # checks it except the scheduled task that drops people
        sub.expiration = datetime.now() + timedelta(days=365)

        return sub

    def make_test_transcript(self, user, student_name):
        transcript = self.transcript_service.new(user)
        transcript.student_name = student_name
        self.transcript_service.save(transcript)
        return transcript