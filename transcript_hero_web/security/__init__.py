from flask_security import (Security, UserMixin, RoleMixin)
from flask_security.datastore import UserDatastore
from transcript_hero.business.users import UserService
from transcript_hero.database.models import User, Role
from transcript_hero_web.payment import handle_payment, contribute_payment_form
from .forms import TranscriptHeroRegisterForm, TranscriptHeroLoginForm


class _SecUser(User, UserMixin):
    """
    Compatibility class used to decouple the data
    layer from the presentation layer
    """


class _SecRole(Role, RoleMixin):
    """
    Compatibility class used to decouple the data
    layer from the presentation layer
    """


class MyUserDatastore(UserDatastore):

    def __init__(self, th_context):
        super().__init__(User, Role)
        self.th_context = th_context

    def convert_to_real(self, model):
        if isinstance(model, _SecUser):
            model.__class__ = User
        elif isinstance(model, _SecRole):
            model.__class__ = Role
        return model

    def convert_to_facade(self, model):
        if isinstance(model, User):
            model.__class__ = _SecUser
        elif isinstance(model, Role):
            model.__class__ = _SecRole
        return model

    def create_user(self, **kwargs):
        user = self.user_model(**kwargs)
        user = self.put(user)
        handle_payment(self.th_context, user)
        return user

    def commit(self):
        # Commits are handled in the database's session context manager
        # no op for compatibility
        pass

    def put(self, model):
        model = self.convert_to_real(model)
        if isinstance(model, User):
            self.th_context.user_service.save(model)
        else:
            self.th_context.db.save(model)
        return self.convert_to_facade(model)

    def delete(self, model):
        self.th_context.db.delete(self.convert_to_real(model))

    def get_user(self, identifier):

        rv = None
        if self._is_numeric(identifier):
            rv = self.th_context.user_service.get(identifier)
        else:
            rv = self.th_context.user_service.get_by_email(identifier)

        return self.convert_to_facade(rv)

    # Taken from Flask-Security
    def _is_numeric(self, value):
        try:
            int(value)
        except (TypeError, ValueError):
            return False
        return True
    # End Taken from Flask-Security

    def find_user(self, **kwargs):
        user = self.th_context.user_service.find(**kwargs)
        return self.convert_to_facade(user)

    def find_role(self, role):
        return self.convert_to_facade(
            self.th_context.user_service.find_role(role))


def register(th_context):
    user_datastore = MyUserDatastore(th_context)
    register_form_class = contribute_payment_form(
        TranscriptHeroRegisterForm, th_context.app.config)
    security = Security(th_context.app, datastore=user_datastore,
                        confirm_register_form=register_form_class,
                        login_form=TranscriptHeroLoginForm)

    @th_context.app.before_first_request
    def security_init():
        user_datastore.find_or_create_role("superuser")
        user_datastore.find_or_create_role("subscriber")
    return security
