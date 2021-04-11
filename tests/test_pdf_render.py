from transcript_hero.database.models import (
    SubscriptionStanding, SubscriptionType, CourseType)
from transcript_hero.business.transcripts import TranscriptService
from transcript_hero.business.grading import GradingService
import transcript_hero_web
from transcript_hero_web.pdf import render_pdf
from helpers import TranscriptHeroTestCase

class PDFRenderTestCase(TranscriptHeroTestCase):

    def setUpExtra(self):
        name = "Chuck Tester"
        email = "test@rehack.me"
        password = "password"
        self.user = self.make_test_user(name, email, password)
        self.user.subscription = self.make_test_subscription(
            self.user, SubscriptionStanding.ACTIVE,
            SubscriptionType.ONE_STUDENT)


    def test_pdf_render(self):
        transcript = self.make_test_transcript(self.user, "Test Student")
        transcript_grader = GradingService.get_transcript_grader(
            transcript.grading_scale, transcript.ap_grading_scale)
        year = transcript.years[0]
        TranscriptService.add_course(year)
        course = year.courses[0]
        course.title = "Test Course"
        course.grade = 'A'
        course.credits = 1
        course.type = CourseType.Normal

        self.transcript_service.save(transcript)

        # if this throws an exception that's a fail
        with transcript_hero_web.app.app_context():
            render_pdf(transcript, transcript_grader)

        TranscriptService.add_course(year)
        transcript.settings.courses_by_subject = True
        self.transcript_service.save(transcript)

        with transcript_hero_web.app.app_context():
            render_pdf(transcript, transcript_grader)
