from transcript_hero.database.models import (
    User, Transcript, SubscriptionType, SubscriptionStanding)


class LimitService:
    """
    LimitService is designed to be used from other business layer
    classes. Therefore, it should not call other business layer classes
    or modify models.
    """
    # TODO: for now we have just the one limit,
    # but we will probably need more.
    max_transcripts = 10
    max_courses_per_year = 17

    @classmethod
    def reached_transcript_limit(cls, user: User):
        result = True

        if (user.subscription and not
            (user.subscription.standing == SubscriptionStanding.DROPPED or
             user.subscription.standing == SubscriptionStanding.PENDING)):

            one = user.subscription.type == SubscriptionType.ONE_STUDENT
            many = user.subscription.type == SubscriptionType.MANY_STUDENT
            unlimited = user.subscription.type == SubscriptionType.UNLIMITED

            if one and len(user.transcripts) < 1:
                result = False
            elif many and len(user.transcripts) < cls.max_transcripts:
                result = False
            elif unlimited:
                result = False

        return result

    @classmethod
    def reached_course_limit(cls, transcript: Transcript):
        for year in transcript.years:
            if len(year.courses) > cls.max_courses_per_year:
                return True
        return False
