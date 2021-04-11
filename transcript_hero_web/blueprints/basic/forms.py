import re
from flask import flash
from flask_wtf import FlaskForm
from wtforms import (StringField, IntegerField, RadioField,
                     FormField, FieldList, SubmitField,
                     SelectField)
from wtforms.compat import text_type
from wtforms.widgets import TextArea
from wtforms.validators import Optional, InputRequired, Email, NumberRange, ValidationError
from wtforms_components.widgets import EmailInput
from sqlalchemy import Boolean
from wtforms_alchemy import (model_form_factory, ModelForm,
                             ModelFormField, QuerySelectField, ClassMap)

from flask_wtf.file import FileField
from transcript_hero.business.grading import GradingService
from transcript_hero.database.models import (
    Transcript, Year, Course, GradeIncrement, GradingScale, CourseType,
    TranscriptSettings, Address)

from transcript_hero_web.address import get_country_choices, get_state_choices
from transcript_hero_web.uploads import get_stream_size


class TranscriptSearchForm(FlaskForm):
    name = StringField("Name:", validators=[Optional()])
    year_start = IntegerField("Years:", validators=[Optional()], render_kw={
                              "placeholder": "YYYY",
                              "aria-label": "Start year"})
    year_end = IntegerField("to", validators=[Optional()], render_kw={
                            "placeholder": "YYYY", "aria-label": "End year"})


class AccountSettingsForm(FlaskForm):
    name = StringField("Name", validators=[InputRequired()])
    email = StringField("Email", validators=[InputRequired(), Email()])
    basic_interface = RadioField(
        "Basic Interface", choices=[("on", "On"), ("off", "Off")],
        description="Lower system requirements, better for older devices. "
        "Does not support auto-save.", validators=[Optional()])
    save = SubmitField("Save")


class DeleteAccountForm(FlaskForm):
    delete = SubmitField("Yes, Delete my account",
                         description="This will irretrievably delete all of"
                         " your data, do you want to continue?")


class DeleteGradingScaleForm(FlaskForm):
    delete = SubmitField("Yes, Delete this grading scale",
                         description="This will irretrievably delete this"
                         " grading scale and any transcripts that use it will"
                         " reset to the default grading scale."
                         " Do you want to continue?")


class DeleteTranscriptForm(FlaskForm):
    delete = SubmitField("Yes, Delete this Transcript",
                         description="This will irretrievably delete this"
                         " transcript. "
                         " Do you want to continue?")


class CancelSubscriptionForm(FlaskForm):
    cancel = SubmitField("Yes, cancel my subscription",
                         description="You will continue to have access"
                         " to the service until the end of your current"
                         " billing period."
                         " Do you want to continue?")


BaseModelFlaskForm = model_form_factory(FlaskForm)


class ModelFlaskForm(BaseModelFlaskForm):

    @classmethod
    def set_session(cls, db_session):
        cls.db_session = db_session

    @classmethod
    def get_session(cls):
        return cls.db_session


class USAddressForm(ModelForm):

    class Meta:
        model = Address
        only = [
            'address1',
            'address2',
            'city',
            'postalcode',
        ]

    stateprov = SelectField(
        "State", choices=get_state_choices(), validators=[InputRequired()])


class InternationalAddressForm(ModelForm):
    class Meta:
        model = Address
        only = [
            'international_address'
        ]
        field_args = {
            'international_address': {'widget': TextArea()}
        }


class TranscriptStudentForm(ModelFlaskForm):
    title = "Student"

    class Meta:
        model = Transcript
        only = [
            'student_name',
            'student_birthday',
            'student_graduation_date',
            'student_parents'
        ]
    student_country = SelectField(
        'Country', default="United States", choices=get_country_choices())


class TranscriptStudentUSForm(TranscriptStudentForm):
    student_address = FormField(USAddressForm)


class TranscriptStudentIntlForm(TranscriptStudentForm):
    student_address = FormField(InternationalAddressForm)


class TranscriptSchoolForm(ModelFlaskForm):
    title = "School"

    class Meta:
        model = Transcript
        only = [
            'school_name',
            'school_email',
            'school_phone',
        ]

        validators = {
            'school_name': [InputRequired()],
            'school_email': [Email()],
        }

        field_args = {
            'school_email': {'widget': EmailInput()}
        }
    school_country = SelectField(
        'Country', default="United States", choices=get_country_choices())


class TranscriptSchoolUSForm(TranscriptSchoolForm):
    school_address = FormField(USAddressForm)


class TranscriptSchoolIntlForm(TranscriptSchoolForm):
    school_address = FormField(InternationalAddressForm)


def get_course_delete_indexes(button):
    button_regex = r'delete-years-(?P<year>\d+)-courses-(?P<course>\d+)'
    return re.match(button_regex, button)


class CourseForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formdata = kwargs.get("formdata", None)

    def validate(self):
        delete_course_match = get_course_delete_indexes(
            self.formdata["button"] if self.formdata and self.formdata.get("button", False) else "")
        if delete_course_match:
            year_index = int(delete_course_match.group("year"))
            course_index = int(delete_course_match.group("course"))
            transcript = self._obj.year.transcript
            if transcript.years[year_index].courses[course_index] == self._obj:
                return True

        return super().validate()

    class Meta:
        model = Course
        field_args = {
            'title': {
                'label': "Course Name",
                'render_kw': {
                    'placeholder': 'Ex., Algebra',
                },
            },
            'category': {
                'label': "Subject (optional)",
                'render_kw': {
                    'placeholder': 'English'
                },
            },
            'grade': {
                'render_kw': {
                    'placeholder': 'B'
                },
            },
            'credits': {
                'render_kw': {
                    'placeholder': '1.0',
                    'step': '0.25',
                    'min': '0',
                },
            },
        }
        validators = {
            'credits': [InputRequired()],
        }

    type = SelectField("Type", validators=[InputRequired()],
                       coerce=CourseType.coerce, choices=CourseType.choices())

    def validate_credits(self, field):
        course = self._obj
        if course is not None and course.year is not None:
            transcript = course.year.transcript
            address = transcript.school_address
        else:
            address = None

        exceptions = [
            "Indiana",
            "Idaho",
            "New Jersey",
            "California"
        ]

        grade = self.grade.data.strip()
        if grade and grade not in GradingService.get_ignored_grades():
            if field.data <= 0:
                raise ValidationError(
                    "A course with a grade must have more than zero credits")

            if (address and address.country == "United States" and
                    address.stateprov not in exceptions and
                    field.data not in (0.25, 0.5, 0.75, 1)):
                raise ValidationError(
                    "A course may be worth 0.25, 0.5, 0.75, or 1 credit")


class YearForm(ModelForm):
    class Meta:
        model = Year
        exclude = ["class_name", "begin", "end"]
    id = IntegerField(validators=[Optional()])
    begin_year = IntegerField("Begin",
                              render_kw={
                                  "placeholder": "YYYY",
                                  "pattern": "\d{4}",
                                  "minlength": 4,
                                  "maxlength": 4,
                                  "title": "4 digit year"
                              },
                              validators=[
                                  Optional(),
                                  NumberRange(min=1000, max=9999,
                                              message="Should be a 4 digit number")
                              ]
                              )

    end_year = IntegerField("End",
                            render_kw={
                                "placeholder": "YYYY",
                                "pattern": "\d{4}",
                                "minlength": 4,
                                "maxlength": 4,
                                "title": "4 digit year"
                            },
                            validators=[
                                Optional(),
                                NumberRange(min=1000, max=9999,
                                            message="Should be a 4 digit number")
                            ]
                            )

    courses = FieldList(FormField(CourseForm))


class TranscriptAcademicsForm(FlaskForm):
    title = "Academics"

    grading_scale = QuerySelectField("Normal:", allow_blank=True,
                                     blank_text="Default 4.0")
    ap_grading_scale = QuerySelectField("AP:", allow_blank=True,
                                        blank_text="Default 5.0")
    years = FieldList(FormField(YearForm))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        transcript = kwargs.get('obj', None)
        user = kwargs.get('user', None)
        db = kwargs.get('db', None)
        user_id = None

        if transcript and transcript.user_id:
            user_id = transcript.user_id
        elif user:
            user_id = user.id

        if user_id and db:
            query = GradingService(db).get_grading_scales_query(user_id)
            self.grading_scale.query = query
            self.ap_grading_scale.query = query


class TranscriptSignatureForm(ModelFlaskForm):
    title = "Signature"

    class Meta:
        model = Transcript
        optional_validator = None
        only = [
            'signature_title',
            'signature_date',
            'notes',
        ]
        field_args = {
            'notes': {'widget': TextArea()}
        }

    signature_image_file = FileField("Signature Image")

    def validate_signature_image_file(self, field):
        max_image_size = 3 * 1024 * 1024  # 3 MB
        image_data = field.data
        if (image_data and image_data.stream
                and get_stream_size(image_data.stream) > max_image_size):
            raise ValidationError("File size must be less than 3 MB")


class TranscriptWizard:
    def __init__(self, db, transcript, user):
        ModelFlaskForm.set_session(db._session)

        student_form_class = TranscriptStudentForm
        if transcript.student_address:
            transcript.student_country = transcript.student_address.country
            if transcript.student_address.country == 'United States':
                student_form_class = TranscriptStudentUSForm
            else:
                student_form_class = TranscriptStudentIntlForm

        school_form_class = TranscriptSchoolForm
        if transcript.school_address:
            transcript.school_country = transcript.school_address.country

            if transcript.school_address.country == 'United States':
                school_form_class = TranscriptSchoolUSForm
            else:
                school_form_class = TranscriptSchoolIntlForm

        student_form = student_form_class(obj=transcript)
        school_form = school_form_class(obj=transcript)
        self.transcript = transcript
        self.transcript_forms = [
            student_form,
            school_form,
            TranscriptAcademicsForm(db=db, obj=transcript, user=user),
            TranscriptSignatureForm(obj=transcript),
        ]

    def get_form(self, page):
        page = min(max(page, 1), len(self.transcript_forms))
        if self.transcript.id is None and page > 1:
            flash("You must fill out the first page to continue")
            page = 1
        return self.transcript_forms[page-1], page


class ToggleButtonsField(RadioField):
    def __init__(self, label=None, validators=None, **kwargs):
        super().__init__(label, validators, coerce=self._str_to_bool, **kwargs)

        self.choices = [(True, "On"), (False, "Off")]

    def _str_to_bool(self, val):
        if type(val) == str:
            return val == "True"
        return val

    def process_data(self, value):
        self.data = self.coerce(value)

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = self.coerce(valuelist[0])
        else:
            self.data = False

    def _value(self):
        if self.raw_data:
            return text_type(self.raw_data[0])
        else:
            return False


class TranscriptSettingsForm(ModelFlaskForm):
    class Meta:
        type_map = ClassMap({Boolean: ToggleButtonsField})
        model = TranscriptSettings


class GradeIncrementForm(ModelForm):
    class Meta:
        model = GradeIncrement
        optional_validator = None
        validators = {
            'name': [InputRequired()],
            'point_value': [InputRequired()],
        }
        field_args = {
            'name': {
                'label': 'Grade Letter',
                'render_kw': {
                    'placeholder': 'Ex., A+, A, A-'
                }
            },
            'point_value': {
                'label': 'GPA Points',
                'render_kw': {
                    'placeholder': '4.0'
                }
            }
        }


class GradingScaleForm(ModelFlaskForm):
    class Meta:
        model = GradingScale
        field_args = {
            'name': {
                'label': 'Name of Custom Scale',
            }
        }

    increments = FieldList(ModelFormField(GradeIncrementForm))


class PaymentInformationForm(FlaskForm):
    pass
