from decimal import Decimal
import enum
from datetime import date
from sqlalchemy import (Column, Integer, String, Date,
                        Numeric, ForeignKey, Boolean, DateTime, Enum)
from sqlalchemy.orm import relationship, backref
# Look, the thing works with the model classes ordered the way they are.
# Be a pal and don't change it unless you absolutely must.
from .datatypes import CaseInsensitiveString
from . import Model


class Role(Model):
    """Define the Role data-model"""

    __tablename__ = 'role'
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(225))

    def __str__(self):
        return self.name


# Define the UserRoles association table
class UserRole(Model):
    __tablename__ = 'user_role'
    id = Column(Integer(), primary_key=True)

    user_id = Column(Integer(), ForeignKey(
        'user.id', ondelete='CASCADE'))

    role_id = Column(Integer(), ForeignKey(
        'role.id', ondelete='CASCADE'))


class Transcript(Model):
    """
    An academic transcript. Users may have more than one of these.
    This model stores mostly student and school information. Links
    to years/courses which hold the actual academic information
    """

    __tablename__ = 'transcript'
    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)

    student_name = Column(String(255), nullable=False,
                          info={'label': 'Name'})

    student_address_id = Column(Integer, ForeignKey('address.id'))

    student_address = relationship(
        'Address', foreign_keys=[student_address_id])

    student_birthday = Column(Date(), info={'label': 'Birthday'})

    student_graduation_date = Column(Date(),
                                     info={'label': 'Graduation Date'})

    # May need to hold 2 full names, so double the rest
    student_parents = Column(
        String(510), info={'label': 'Parent/Guardian(s)'})

    school_name = Column(String(255),
                         info={'label': 'Name'})

    school_address_id = Column(Integer, ForeignKey('address.id'))

    school_address = relationship(
        'Address', foreign_keys=[school_address_id])

    school_email = Column(String(255),
                          info={'label': 'Email'})

    school_phone = Column(String(255),
                          info={'label': 'Phone'})

    signature_title = Column(String(255), info={'label': 'Title'})

    signature_date = Column(Date(), info={'label': 'Signature Date'})

    signature_image = Column(
        String(255),
        info={
            'label': 'Signature <small>(Leave blank to physically sign)</small>'
        }
    )

    notes = Column(String(400), info={'label': 'Notes'}, default="")

    years = relationship('Year', cascade="all,delete", order_by="asc(Year.id)",
                         backref='transcript', lazy=False)
    settings = relationship('TranscriptSettings', cascade="all,delete",
                            backref='transcript', lazy=False, uselist=False)
    grading_scale_id = Column(
        Integer, ForeignKey("grading_scale.id"), nullable=True)

    grading_scale = relationship(
        'GradingScale', foreign_keys=[grading_scale_id])

    ap_grading_scale_id = Column(
        Integer, ForeignKey("grading_scale.id"), nullable=True)

    ap_grading_scale = relationship(
        'GradingScale', foreign_keys=[ap_grading_scale_id])

    @property
    def first_year(self):
        year = ''
        if len(self.years) > 0:
            year = self.years[0].begin.year
        return year

    @property
    def last_year(self):
        year = ''
        if len(self.years) > 0:
            year = self.years[-1].end.year
        return year

    def validate(self):
        pass

    def __str__(self):
        return self.student_name


class TranscriptSettings(Model):
    __tablename__ = 'transcript_settings'
    id = Column(Integer, primary_key=True)
    transcript_id = Column(Integer,
                           ForeignKey(Transcript.id),
                           nullable=False)
    courses_by_subject = Column(
        Boolean(), info={'label': 'List Courses by Subject'})
    cumulative_gpa = Column(Boolean(), info={'label': 'Cumulative GPA'})
    unweighted_gpa = Column(Boolean(), info={'label': 'Unweighted GPA'})
    hide_unfinished_courses = Column(
        Boolean(), info={'label': 'Hide Unfinished Courses'})

    def __str__(self):
        return "Settings for transcript {}".format(self.transcript_id)

    def __repr__(self):
        return "<TranscriptSettings {}>".format(self.id)


class Year(Model):
    """
    Holds a collection of courses. Used to associate courses with
    a particular time frame and a transcript.
    """

    __tablename__ = 'year'
    id = Column(Integer, primary_key=True)
    class_name = Column(String(20), nullable=False,
                        info={'label': 'Class'})
    begin = Column(Date(),
                   info={'label': 'Begin'})
    end = Column(Date(),
                 info={'label': 'End'})
    transcript_id = Column(Integer,
                           ForeignKey(Transcript.id),
                           nullable=False)
    courses = relationship('Course', cascade="all,delete",
                           order_by="asc(Course.id)", backref="year")

    def __str__(self):
        return self.class_name

    def __repr__(self):
        return "<Year {}>".format(self.id)

    @property
    def begin_year(self):
        return self.begin.year

    @begin_year.setter
    def begin_year(self, year):
        if year is not None:
            self.begin = date(year, 1, 1)
        else:
            self.begin = None

    @property
    def end_year(self):
        return self.end.year

    @end_year.setter
    def end_year(self, year):
        if year is not None:
            self.end = date(year, 1, 1)
        else:
            self.end = None

    def clear_empty_courses(self):
        self.courses = [
            course for course in self.courses if not course.empty()]

    def validate(self):
        pass


class User(Model):
    __tablename__ = 'user'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_row_format': "DYNAMIC"}

    id = Column(Integer, primary_key=True)

    name = Column(String(254), nullable=False)

    active = Column('is_active', Boolean(),
                    nullable=False, server_default='1')

    email = Column(CaseInsensitiveString(255),
                   nullable=False, unique=True)

    confirmed_at = Column(DateTime())

    password = Column('password', String(
        255), nullable=False, server_default='')

    roles = relationship('Role', secondary='user_role',
                         backref=backref('users', lazy='dynamic'))

    transcripts = relationship(
        'Transcript', cascade="all,delete", backref='user', lazy=True)

    grading_scales = relationship(
        'GradingScale', cascade="all,delete", backref='user', lazy=True)

    subscription = relationship('Subscription', uselist=False,
                                cascade="all,delete", backref='user',
                                lazy=True)
    transactions = relationship(
        'Transaction', cascade="all,delete", backref='user', lazy=True)

    def get_user_id(self):
        return self.id

    def validate(self):
        pass

    def __str__(self):
        return self.email


class CourseType(enum.Enum):
    Normal = 0
    Honors = 1
    AP = 2

    def __str__(self):
        return self.name

    @classmethod
    def choices(cls):
        return [(choice, choice) for choice in cls]

    @classmethod
    def coerce(cls, item):
        if isinstance(item, cls):
            return item

        try:
            return CourseType[item]
        except KeyError:
            raise ValueError(item)


def coerce_course_type(value):
    if value:
        return CourseType[value]
    return CourseType.Normal


class Course(Model):
    """
    Courses are attached to years and hold the bulk of academic
    information in the transcript
    """

    __tablename__ = 'course'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), info={
                   "label": "Title"}, nullable=False)
    grade = Column(String(20), info={"label": "Grade"})
    credits = Column(Numeric(precision=10, scale=2), info={
                     "label": "Credits"}, default=Decimal())
    year_id = Column(Integer, ForeignKey(Year.id), nullable=False)

    type = Column(Enum(CourseType, create_constraint=False, native_enum=False), info={
                  "label": "Type", 'coerce': coerce_course_type})
    category = Column(String(255), info={"label": "Category"})

    def empty(self):
        return not self.id and not self.title

    def validate(self):
        pass

    def __str__(self):
        return self.title

    def __repr__(self):
        return "<Course {}>".format(self.id)


class Address(Model):
    __tablename__ = 'address'
    id = Column(Integer, primary_key=True)

    international_address = Column(String(255), info={
        'label': 'Address'})

    address1 = Column(String(255), info={
        'label': 'Address 1'})

    address2 = Column(String(255), info={'label': 'Address 2'})

    city = Column(String(255),
                  info={'label': 'City'})

    stateprov = Column(
        String(255), info={'label': 'State/Province'})

    postalcode = Column(
        String(255), info={'label': 'Postal Code'})

    country = Column(
        String(255), info={'label': 'Country'})

    def __str__(self):
        if self.country == 'United States':
            return self.address1 or repr(self)
        else:
            return self.international_address or repr(self)

    def __repr__(self):
        return "<Address {}>".format(self.id)


class GradingScale(Model):
    """
    Grading scales link letter grades to numeric grades.
    A container for grade increments.
    """

    __tablename__ = 'grading_scale'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), info={'label': "Name"}, nullable=False)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)

    increments = relationship('GradeIncrement', cascade="all,delete",
                              backref='grading_scale', lazy=True)

    def __str__(self):
        return self.name

    def validate(self):
        pass


class GradeIncrement(Model):
    """
    A grade increment links a letter grade to a point value
    """

    __tablename__ = 'grade_increment'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), info={"label": "Name"})
    point_value = Column(Numeric(precision=10, scale=2),
                         info={"label": "Points"})
    grading_scale_id = Column(
        Integer, ForeignKey(GradingScale.id), nullable=False)

    def validate(self):
        pass

    def __str__(self):
        return "{}: {}".format(self.name, self.point_value)


class PayApi(enum.Enum):
    STRIPE = 0
    BRAINTREE = 1
    AUTHORIZENET = 2
    HSLDA = 3


class SubscriptionStanding(enum.Enum):
    DROPPED = 0
    ACTIVE = 1
    PENDING = 2
    CANCELED = 3


class SubscriptionType(enum.Enum):
    ONE_STUDENT = 1
    MANY_STUDENT = 2
    UNLIMITED = 3


class Subscription(Model):
    """
    Tracks subscription information for users
    """
    __tablename__ = 'subscription'
    id = Column(Integer, primary_key=True)
    standing = Column(
        Enum(SubscriptionStanding, create_constraint=False, native_enum=False))
    type = Column(
        Enum(SubscriptionType, create_constraint=False, native_enum=False))
    expiration = Column(Date)
    user_id = Column(Integer, ForeignKey(User.id))
    transactions = relationship('Transaction',
                                cascade="all,delete", backref='subscription',
                                lazy=True)
    pay_api = Column('pay_method',
                     Enum(PayApi, create_constraint=False, native_enum=False))
    external_id = Column(String(255))

    def __str__(self):
        return "{}: {}".format(self.__class__.__name__, self.id)


class Transaction(Model):
    """
    records when a transaction happened and its amount
    """
    __tablename__ = "transaction"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id))
    date = Column(Date)
    amount = Column(Numeric(2))
    external_id = Column(String(255))
    subscription_id = Column(Integer, ForeignKey(Subscription.id))
    pay_api = Column('pay_method',
                     Enum(PayApi, create_constraint=False, native_enum=False))

    def __str__(self):
        return "{}: {}".format(self.__class__.__name__, self.id)
