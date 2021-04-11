from typing import List, Optional, Iterable, Union
from decimal import Decimal
from sqlalchemy.orm import Query
from transcript_hero.database.models import (
    GradingScale, GradeIncrement, User, Transcript, CourseType, Course)


class TranscriptGrader:
    def __init__(self, grading_scale: GradingScale =None,
                 ap_grading_scale: GradingScale = None,
                 unweighted=False):

        self.half_credit_increments = {
            'A+': 2.15,
            'A': 2.0,
            'A-': 1.85,
            'B+': 1.65,
            'B': 1.5,
            'B-': 1.35,
            'C+': 1.15,
            'C': 1.0,
            'C-': 0.85,
            'D+': 0.65,
            'D': 0.5,
            'D-': 0.35,
            'F': 0.0,
        }

        self.increments = {
            'A+': 4.3,
            'A': 4.0,
            'A-': 3.7,
            'B+': 3.3,
            'B': 3.0,
            'B-': 2.7,
            'C+': 2.3,
            'C': 2.0,
            'C-': 1.7,
            'D+': 1.3,
            'D': 1.0,
            'D-': 0.7,
            'F': 0.0,
        }

        self.honors_increments = {
            'A+': 4.5,
            'A': 4.5,
            'A-': 4.2,
            'B+': 3.8,
            'B': 3.5,
            'B-': 3.2,
            'C+': 2.8,
            'C': 2.5,
            'C-': 2.2,
            'D+': 1.8,
            'D': 1.0,
            'D-': 0.7,
            'F': 0.0,
        }

        self.ap_increments = {
            'A+': 5.0,
            'A': 5.0,
            'A-': 4.7,
            'B+': 4.3,
            'B': 4.0,
            'B-': 3.7,
            'C+': 3.3,
            'C': 3.0,
            'C-': 2.7,
            'D+': 2.3,
            'D': 2.0,
            'D-': 1.7,
            'F': 0.0,
        }

        self.unfinished_grades = GradingService.get_unfinished_grades()
        self.ignored_grades = GradingService.get_ignored_grades()
        self.ap_ignored_grades = GradingService.get_ignored_grades()
        self.unweighted = unweighted
        self.failed_grades = ["F"]

        # build increments
        # We do case insensitive matching to avoid
        # case errors in grade or grade increment data.
        if grading_scale:
            self.increments = {}
            self.ignored_grades = self.unfinished_grades
            for increment in grading_scale.increments:
                self.increments[increment.name.upper()] = increment.point_value


        if ap_grading_scale:
            self.ap_increments = {}
            self.ap_ignored_grades = self.unfinished_grades
            for increment in ap_grading_scale.increments:
                self.ap_increments[increment.name.upper()] = increment.point_value

    def calculate_gpa(self,
                      grades: Iterable[Union[int, float, Decimal]], credits):

        try:
            gpa = sum(grades)/credits
        except ZeroDivisionError:
            gpa = Decimal()
        return gpa

    def total_credits(self, credits: Iterable[Union[int, float, Decimal]]):
        return sum(credits)

    def letter_grade_to_numeric(self, course: Course 
                                ) -> Union[int, float, Decimal]:
        num_grade = 0
        # Avoid case errors and whitespace in grade data
        grade = course.grade.upper().strip()
        try:
            if not self.unweighted and course.type == CourseType.AP:
                num_grade = self.ap_increments[grade]

            elif not self.unweighted and course.type == CourseType.Honors:
                num_grade = self.honors_increments[grade]

            else:
                num_grade = self.increments[grade]

        except KeyError:
            pass

        return Decimal(num_grade) * Decimal(course.credits)

    def grade_transcript(self, transcript: Transcript):
        return self.grade_year(transcript.years[-1], True)

    def filter_unfinished_courses(self, course):
        grade = course.grade.strip() if course.grade else ''
        unfinished = grade.upper() in self.unfinished_grades
        return grade and not unfinished

    def filter_ignored_courses(self, course):
        grade = course.grade.strip() if course.grade else ''
        ignored_list = self.ap_ignored_grades if course.type == CourseType.AP else self.ignored_grades
        ignored = grade.upper() in ignored_list 
        return grade and not ignored

    def filter_unearned_courses(self, course):
        grade = course.grade.strip() if course.grade else ''
        unfinished = grade.upper() in self.unfinished_grades
        failed = grade.upper() in self.failed_grades
        return grade and not (failed or unfinished)

    def grade_year(self, year, cumulative=False):
        grades = []
        credits = 0

        if cumulative:
            transcript = year.transcript
            for past_year in transcript.years:

                grades.extend(map(self.grade_course, filter(
                    self.filter_ignored_courses, past_year.courses)))
                credits += self.year_gpa_credits(past_year)

                if past_year.id == year.id:
                    break
        else:
            grades = list(map(self.grade_course, filter(
                self.filter_ignored_courses, year.courses)))
            credits = self.year_gpa_credits(year)

        return self.calculate_gpa(grades, credits)

    def grade_course(self, course):
        return self.letter_grade_to_numeric(course)

    def transcript_credits(self, transcript):
        credits = [self.year_earned_credits(year) for year in transcript.years]
        return self.total_credits(credits)

    def year_gpa_credits(self, year):
        """
        GPAs need to include credits for failed courses and (for the default scales)
        not include credits for courses with a pass (P/PASS) grade.
        """
        credits = [course.credits if course.credits is not None else Decimal()
                   for course in filter(self.filter_ignored_courses, year.courses)]
        return self.total_credits(credits)

    def year_earned_credits(self, year):
        """
        Earned credits include credits for all courses with a passing
        (anything not failing, P/PASS grades included) grade.
        """
        credits = [course.credits if course.credits is not None else Decimal()
                   for course in filter(self.filter_unearned_courses, year.courses)]
        return self.total_credits(credits)



class GradingService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def get_unfinished_grades():
        return ["IP", "SPR"]

    @staticmethod
    def get_ignored_grades():
        return ["IP", "SPR", "Pass", "P", "PASS", "pass"]

    @staticmethod
    def get_transcript_grader(
            grading_scale: GradingScale = None,
            ap_grading_scale: GradingScale = None,
            unweighted=False
    ) -> TranscriptGrader:
        return TranscriptGrader(grading_scale, ap_grading_scale, unweighted)

    def get_grading_scales(self, user_id: int) -> List[GradingScale]:
        with self.db.session() as session:
            return session.query(GradingScale).filter_by(user_id=user_id).all()

    def get_grading_scales_query(self, user_id: int) -> Query:
        """
        This  will only work if a scoped_session
        was set when Database was created. So only call it if you know
        it's been setup.
        """
        with self.db.session() as session:
            return session.query(GradingScale).filter_by(user_id=user_id)

    def get_user_grading_scale(self, grading_scale_id: int,
                               user_id: int) -> Optional[GradingScale]:
        with self.db.session() as session:
            grading_scale = session.query(GradingScale).get(grading_scale_id)
            if grading_scale and grading_scale.user_id == user_id:
                return grading_scale
            return None

    @staticmethod
    def new_grading_scale(user: User) -> GradingScale:
        grading_scale = GradingScale()

        if user:
            grading_scale.user = user

        return grading_scale

    def add_grade_increment(self, grading_scale: GradingScale) -> None:
        grade_increment = GradeIncrement()
        if grading_scale.id < 0:
            self.save_grading_scale(grading_scale)
        grade_increment.grading_scale = grading_scale
        grade_increment.grading_scale_id = grading_scale.id
        grading_scale.increments.append(grade_increment)
        self.save_grading_scale(grading_scale)

    def save_grading_scale(self, grading_scale: GradingScale) -> None:
        self.db.save(grading_scale)

    def delete_grade_increment(self, grade_increment: GradeIncrement) -> None:
        self.db.delete(grade_increment)

    def delete_grading_scale(self, grading_scale: GradingScale) -> None:
        self.db.delete(grading_scale)
