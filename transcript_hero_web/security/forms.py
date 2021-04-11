from flask import flash, url_for
from wtforms.fields import StringField
from wtforms.validators import Required
from flask_security import ConfirmRegisterForm, LoginForm
from flask_security.utils import get_message


class TranscriptHeroRegisterForm(ConfirmRegisterForm):
    name = StringField('Name', [Required()])


class TranscriptHeroLoginForm(LoginForm):
    def validate(self, extra_validators=None):
        result = super().validate()
        confirm_message = get_message('CONFIRMATION_REQUIRED')[0]
        msg = "Can't find the confirmation email? <a href=\"{}\">Resend it</a>"
        if confirm_message in self.email.errors:
            flash(msg.format(url_for('security.send_confirmation')))
        return result
