from collections import defaultdict
from datetime import datetime
from transcript_hero.errors import LimitError
from transcript_hero.database.models import (
    SubscriptionStanding, SubscriptionType)
from transcript_hero.business.transcripts import TranscriptService
from helpers import TranscriptHeroTestCase


class TranscriptServiceTestCase(TranscriptHeroTestCase):

    def setUpExtra(self):
        name = "Chuck Tester"
        email = "test@rehack.me"
        email2 = "test2@rehack.me"
        email3 = "test3@rehack.me"
        password = "password"
        self.user = self.make_test_user(name, email, password)
        self.user.subscription = self.make_test_subscription(
            self.user, SubscriptionStanding.ACTIVE,
            SubscriptionType.ONE_STUDENT)
        self.no_sub_user = self.make_test_user(name, email2, password)
        self.many_user = self.make_test_user(name, email3, password)
        self.many_user.subscription = self.make_test_subscription(
            self.many_user, SubscriptionStanding.ACTIVE,
            SubscriptionType.MANY_STUDENT)

    def test_create_transcript(self):
        # User doesn't have a subscription, creation must fail
        with self.assertRaises(LimitError):
            self.transcript_service.new(self.no_sub_user)

        transcript = self.make_test_transcript(self.user, "Test Student")
        self.assertEqual(self.user.id, transcript.user_id)
        self.assertEqual(len(transcript.years), 4)

        self.assertIsNotNone(transcript.settings)

        # We've added a transcript already and this user
        # only has a single student subscription
        with self.assertRaises(LimitError):
            self.transcript_service.new(self.user)

        self.transcript_service.delete_transcript(transcript)

        # should work now, since we deleted the old one
        self.transcript_service.new(self.user)

    def test_get_transcript(self):
        transcript = self.make_test_transcript(self.user, "Test Student")

        # TranscriptService.get_user_transcript calls TranscriptService.get
        # under the hood, so this is testing that as well
        no_sub_transcript = self.transcript_service.get_user_transcript(
            transcript.id, self.no_sub_user.id)
        self.assertIsNone(no_sub_transcript)

        user_transcript = self.transcript_service.get_user_transcript(
            transcript.id, self.user.id)
        self.assertEqual(transcript, user_transcript)

    def test_courses(self):
        transcript = self.make_test_transcript(self.user, "Student Test")

        year = transcript.years[0]
        self.assertEqual(len(year.courses), 0)

        TranscriptService.add_course(transcript.years[0])
        self.transcript_service.save(transcript)
        self.assertEqual(len(year.courses), 1)

        course = year.courses[0]

        course.title = "Test Course"
        course.grade = "C"
        course.category = "Testing"

        categories = self.transcript_service.get_course_categories(transcript)

        self.assertEqual(categories, defaultdict(list, {
            "Testing": [course]
        }))

        year2 = transcript.years[1]

        TranscriptService.add_course(year2)

        course2 = year2.courses[0]

        course2.title = "Test Course2"
        course.grade = "B"
        categories = self.transcript_service.get_course_categories(transcript)
        self.assertEqual(categories, defaultdict(list, {
            "Testing": [course],
            "Other": [course2]
        }))

        self.transcript_service.delete_course(course)
        self.assertEqual(len(year.courses), 0)

    def setup_transcript_search(self):
        student_name1 = "test student1"
        transcript1 = self.make_test_transcript(self.many_user, student_name1)
        transcript1.years[0].begin = datetime(2013, 1, 1)
        transcript1.years[0].end = datetime(2014, 1, 1)
        self.transcript_service.save(transcript1)
        student_name2 = "test student2"
        transcript2 = self.make_test_transcript(self.many_user, student_name2)
        transcript2.years[0].begin = datetime(2010, 1, 1)
        transcript2.years[0].end = datetime(2011, 1, 1)
        transcript2.years[1].begin = datetime(2017, 1, 1)
        transcript2.years[1].end = datetime(2018, 1, 1)
        self.transcript_service.save(transcript2)

    def test_search_by_begin(self):
        self.setup_transcript_search()

        results = self.transcript_service.search_transcripts(
            self.many_user.id, '', 2009, None)
        self.assertEqual(len(results), 2)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, '', 2013, None)
        self.assertEqual(len(results), 2)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, '', 2018, None)
        self.assertEqual(len(results), 1)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, '', 2019, None)
        self.assertEqual(len(results), 0)

    def test_search_by_end(self):
        self.setup_transcript_search()
        results = self.transcript_service.search_transcripts(
            self.many_user.id, None, None, 2009)
        self.assertEqual(len(results), 0)
        results = self.transcript_service.search_transcripts(
            self.many_user.id, None, None, 2011)
        self.assertEqual(len(results), 1)
        results = self.transcript_service.search_transcripts(
            self.many_user.id, None, None, 2013)
        self.assertEqual(len(results), 2)
        results = self.transcript_service.search_transcripts(
            self.many_user.id, None, None, 2019)
        self.assertEqual(len(results), 2)

    def test_search_by_begin_end(self):
        student_name1 = "test student1"
        transcript1 = self.make_test_transcript(self.many_user, student_name1)

        transcript1.years[0].begin = datetime(2013, 1, 1)
        transcript1.years[0].end = datetime(2014, 1, 1)
        self.transcript_service.save(transcript1)
        results = self.transcript_service.search_transcripts(
            self.many_user.id, '', 2010, 2012)

        self.assertEqual(len(results), 0)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, '', 2012, 2013)

        self.assertEqual(len(results), 1)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, '', 2014, 2016)

        self.assertEqual(len(results), 1)

        student_name2 = "test student2"
        transcript2 = self.make_test_transcript(self.many_user, student_name2)
        transcript2.years[0].begin = datetime(2010, 1, 1)
        transcript2.years[0].end = datetime(2011, 1, 1)
        transcript2.years[1].begin = datetime(2017, 1, 1)
        transcript2.years[1].end = datetime(2018, 1, 1)
        self.transcript_service.save(transcript2)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, '', 2014, 2016)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].student_name, student_name1)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, '', 2009, 2010)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].student_name, student_name2)

    def test_search_by_name(self):
        student_name1 = "test student1"
        self.make_test_transcript(self.many_user, student_name1)
        student_name2 = "test student2"
        self.make_test_transcript(self.many_user, student_name2)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, '', None, None)
        self.assertEqual(len(results), 2)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, 'blah', None, None)
        self.assertEqual(len(results), 0)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, 'test', None, None)
        self.assertEqual(len(results), 2)

        results = self.transcript_service.search_transcripts(
            self.many_user.id, student_name1, None, None)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].student_name, student_name1)
