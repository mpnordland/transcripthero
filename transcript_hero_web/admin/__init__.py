from flask import abort, redirect, url_for, request
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.model.template import EndpointLinkRowAction
from flask_admin.form import SecureForm
from flask_admin.contrib import sqla
from flask_admin.contrib.sqla.form import InlineModelConverter
from flask_security import current_user
from flask_security.utils import encrypt_password
from wtforms.fields import PasswordField, StringField
from transcript_hero.database.models import (
    User, Role, Subscription, Year, Course,
    Transaction, Transcript, GradingScale,
    GradeIncrement, TranscriptSettings)
from transcript_hero.business.transcripts import TranscriptService
from transcript_hero.business.grading import GradingService
from transcript_hero_web.pdf import render_pdf


class SecureAdminViewMixin():
    form_base_class = SecureForm

    def is_accessible(self):
        return current_user.is_active and current_user.is_authenticated \
            and current_user.has_role('superuser')

    def inaccessible_callback(self, name, **kwargs):
        """
        redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class SecureAdminIndexView(SecureAdminViewMixin, AdminIndexView):
    pass


class AdminModelView(SecureAdminViewMixin, sqla.ModelView):
    pass


class TranscriptInlineModelConverter(InlineModelConverter):
    def contribute(self, model, form_class, inline_model):
        # have the converter build the year form
        form_class = super().contribute(model, form_class, inline_model)

        # Allow us to have other inline models
        if inline_model != Year:
            return form_class

        # find where it was stored
        year_info = self.get_info(inline_model)
        year_forward_prop_key, _ = self._calculate_mapping_key_pair(
            model, year_info)

        # pull the inline year form field back out
        year_inline_form_field = getattr(form_class, year_forward_prop_key)

        # Due to meta classes and stuff this isn't a InlineModelFormField,
        # It's an instance of UnboundField. That's ok, cause we can still
        # get and update the year form class inside
        year_inline_form_args = year_inline_form_field.args

        # Add an inline form field for courses
        year_form_class_with_course = super().contribute(
            inline_model, year_inline_form_args[0], Course)

        # Stuff the year form back where it came from
        year_inline_form_field.args = (
            year_form_class_with_course, *year_inline_form_args[1:])

        return form_class


class TranscriptAdminModelView(AdminModelView):
    column_searchable_list = ['id', 'student_name', 'user_id', 'user.email']
    inline_models = [Year]
    inline_model_form_converter = TranscriptInlineModelConverter
    column_extra_row_actions = [
        EndpointLinkRowAction("glyphicon icon-print", 'transcript.print'),
        EndpointLinkRowAction("glyphicon icon-cog",
                              'transcriptsettings.edit_view')
    ]

    def __init__(self, db, *args, **kwargs):
        super().__init__(Transcript, db._session, *args, **kwargs)
        self.transcript_service = TranscriptService(db)

    @expose('/print/<int:id>')
    def print(self, id):
        transcript = self.transcript_service.get(id)
        if transcript is None:
            return abort(404)
        transcript_grader = GradingService.get_transcript_grader(
            transcript.grading_scale, transcript.ap_grading_scale)

        return render_pdf(transcript, transcript_grader)


class TranscriptSettingsAdminModelView(AdminModelView):
    can_create = False
    can_delete = False

    def __init__(self, db, *args, **kwargs):
        super().__init__(TranscriptSettings, db._session, *args, **kwargs)
        self.transcript_service = TranscriptService(db)

    def is_visible(self):
        return False

    def get_one(self, id):
        transcript = self.transcript_service.get(id)
        settings = None

        if transcript:
            settings = transcript.settings

        return settings

    def get_save_return_url(self, model, is_created=False):
        return self.get_url("transcript.index_view")


class GradingScaleAdminModelView(AdminModelView):
    inline_models = [GradeIncrement]


class SubscriptionAdminModelView(AdminModelView):
    column_searchable_list = ['id', 'user.email']
    inline_models = [Transaction]


class UserAdminModelView(AdminModelView):
    column_searchable_list = ['id', 'name', 'email']
    # Don't display the password on the list of Users
    column_exclude_list = ('password',)

    # Don't include the standard password field when creating or editing a User
    # (but see below)
    form_excluded_columns = ('password',)

    # On the form for creating or editing a User, don't display a field
    # corresponding to the model's password field. There are two reasons for
    # this. First, we want to encrypt the password before storing in the
    # database. Second, we want to use a password field (with the input masked)
    # rather than a regular text field.
    def scaffold_form(self):

        # Start with the standard form as provided by Flask-Admin. We've
        # already told Flask-Admin to exclude the password field from this
        # form.
        form_class = super().scaffold_form()

        # Add a password field, naming it "password2" and labeling it "New
        # Password".
        form_class.password2 = PasswordField('New Password')

        # The email column uses a shapeshifting column type based on the
        # database we're talking to. We need it because Postgres use CITEXT for
        # case insensitive columns and everything else uses a collation.
        form_class.email = StringField("Email")

        return form_class

    # This callback executes when the user saves changes to a newly-created or
    # edited User -- before the changes are committed to the database.
    def on_model_change(self, form, model, is_created):

        # If the password field isn't blank...
        if len(model.password2):

            # ... then encrypt the new password prior to storing it in the
            # database. If the password field is blank,
            # the existing password in the database will be retained.
            model.password = encrypt_password(model.password2)


def register(app, db):
    admin = Admin(name="Transcript Hero Admin",
                  index_view=SecureAdminIndexView())
    admin.add_view(AdminModelView(Role, db._session))
    admin.add_view(UserAdminModelView(User, db._session))
    admin.add_view(SubscriptionAdminModelView(Subscription, db._session))
    admin.add_view(TranscriptAdminModelView(db))
    admin.add_view(TranscriptSettingsAdminModelView(db))
    admin.add_view(GradingScaleAdminModelView(GradingScale, db._session))
    admin.init_app(app)
