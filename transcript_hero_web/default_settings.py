DEBUG = False  # make sure DEBUG is off unless enabled explicitly otherwise
LOG_DIR = '.'  # create log files in current working directory
SECURITY_MSG_FORGOT_PASSWORD = ('Forgot your password?', 'info')
SECURITY_MSG_USER_DOES_NOT_EXIST = (
    'An account could not be found for this email', 'error')
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_POST_LOGIN_VIEW = 'basic.index'
SECURITY_EMAIL_SENDER = 'no-reply@localhost'
MAIL_DEFAULT_SENDER = 'no-reply@localhost'
SECURITY_REGISTERABLE = True
SECURITY_RECOVERABLE = True
SECURITY_CHANGEABLE = True
SECURITY_CONFIRMABLE = True
MAIL_SUPPRESS_SEND = False
TRANSCRIPT_HERO_DEFAULT_PAY_API = 'STRIPE'
STRIPE_MAX_REQUEST_SIZE = 5000
NO_DEFAULT_CSS = False
CUSTOM_CSS = ''
SITE_NAME = 'Transcript Hero'
GOOGLE_FONTS = 'Almendra:wght@400;700&family=Open+Sans'
USE_DRAMATIQ = False

# This is a stop gap against massive uploads.
# Most reasonable photos will be way under this.
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
