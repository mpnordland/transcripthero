from datetime import date
from collections import defaultdict
from itertools import chain
from typing import List, Optional
from sqlalchemy import or_, and_
from transcript_hero.database.models import (
    Transcript, Year, Course, User, TranscriptSettings, Address)
from transcript_hero.business.limits import LimitService
from transcript_hero.errors import LimitError


class TranscriptService:
    """
    This class provides access to and implements rules surrounding
    Transcripts. Sections of the presentation layer wishing to work with
    Transcripts must retrieve and persist them through this class.
    """

    def __init__(self, db):
        self.db = db

    def get(self, transcript_id: int) -> Transcript:
        with self.db.session() as session:
            return session.query(Transcript).get(transcript_id)

    def get_user_transcript(self, transcript_id: int,
                            user_id: int) -> Optional[Transcript]:
        transcript = self.get(transcript_id)
        if transcript and transcript.user_id == user_id:
            return transcript
        return None

    def search_transcripts(self, user_id: int, name: str,
                           begin: int, end: int) -> List[Transcript]:
        """
        Returns a list of transcripts filtered by user id,
        the name on the transcript, and the date range provided.
        """

        with self.db.session() as session:
            query = session.query(Transcript).filter_by(user_id=user_id)
            # filter transcripts
            if name:
                query = query.filter(
                    Transcript.student_name.like("%"+name+"%"))

            if begin and end:
                begin_date = date(int(begin), 1, 1)
                end_date = date(int(end), 1, 1)
                query = query.join(Transcript.years).filter(
                    or_(
                        and_(Year.begin != None, Year.begin <=
                             end_date, Year.begin >= begin_date),
                        and_(Year.end != None, Year.end >=
                             begin_date, Year.end <= end_date)
                    )
                )
            elif begin:
                begin_date = date(int(begin), 1, 1)
                query = query.join(Transcript.years).filter(
                    or_(Year.begin >= begin_date, Year.end >= begin_date))

            elif end:
                end_date = date(int(end), 1, 1)
                query = query.join(Transcript.years).filter(
                    or_(Year.end <= end_date, Year.begin <= end_date))

            return query.all()

    def save(self, transcript: Transcript):
        self.db.save(transcript)

    def new(self, user: User) -> Transcript:
        if LimitService.reached_transcript_limit(user):
            raise LimitError(
                "User limit reached. No more transcripts can be created.")
        transcript = Transcript()
        transcript.user_id = user.id
        transcript.settings = self.new_settings(transcript)
        class_names = [
            "Freshman",
            "Sophmore",
            "Junior",
            "Senior",
        ]

        for class_name in class_names:
            year = Year()
            year.class_name = class_name
            transcript.years.append(year)

        return transcript

    def new_settings(self, transcript: Transcript):
        settings = TranscriptSettings()
        settings.courses_by_subject = False
        settings.cumulative_gpa = True
        settings.unweighted_gpa = False
        settings.hide_unfinished_courses = False
        return settings

    @staticmethod
    def add_course(year: Year):
        course = Course()
        course.title = ''
        course.grade = ''
        course.credits = 0
        year.courses.append(course)

    def delete_course(self, course: Course):
        self.db.delete(course)

    def delete_transcript(self, transcript: Transcript):
        self.db.delete(transcript)

    @staticmethod
    def get_course_categories(transcript: Transcript):

        def extract_courses(year):
            return year.courses

        categories = defaultdict(list)
        courses = chain.from_iterable(map(extract_courses, transcript.years))

        for course in courses:
            if course.category:
                # Avoid casing errors in category data
                categories[course.category.title().strip()].append(course)
            else:
                categories['Other'].append(course)
        # Keep Other always last, depends on Python > 3.6
        # or CPython >= 3.6
        if 'Other' in categories:
            other = categories['Other']
            del categories['Other']
            categories['Other'] = other

        return categories

    def add_address(self, transcript, field_name, country):
        address = Address()
        address.country = country
        setattr(transcript, field_name, address)
