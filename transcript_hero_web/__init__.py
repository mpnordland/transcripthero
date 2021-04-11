import os
from functools import partial
from flask import Flask
from flask_mail import Mail
from flask_sqlalchemy_session import flask_scoped_session
from flask_migrate import Migrate
from transcript_hero.database import Database
from transcript_hero_web.context import TranscriptHeroContext
from transcript_hero_web.security import register as security_register
from transcript_hero_web.payment import setup_payment_processing
from transcript_hero_web.uploads import setup_uploads
from transcript_hero_web.admin import register as admin_register
from transcript_hero_web.errors import register_error_handlers
from transcript_hero_web.blueprints.public import build_blueprint as public
from transcript_hero_web.blueprints.basic import build_blueprint as basic
from transcript_hero_web.blueprints.webhooks import build_blueprint as webhooks

app = Flask(__name__)
app.config.from_object('transcript_hero_web.default_settings')
app.config.from_envvar('TRANSCRIPT_HERO_SETTINGS')

if not app.debug:
    import logging
    from logging.handlers import TimedRotatingFileHandler
    # https://docs.python.org/3.6/library/logging.handlers.html#timedrotatingfilehandler
    file_handler = TimedRotatingFileHandler(os.path.join(
        app.config['LOG_DIR'], 'transcript_hero.log'), 'midnight')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(
        '<%(asctime)s> <%(levelname)s> %(message)s'))
    app.logger.addHandler(file_handler)


Mail(app)
db = Database(app.config["SQLALCHEMY_DATABASE_URI"],
              partial(flask_scoped_session, app=app))
db.create_if_not_exists()
Migrate(app, db)

if app.config['USE_DRAMATIQ']:
    from transcript_hero_job import DramatiqBatchProcessor
    TranscriptHeroContext.BATCH_PROCESSOR_CLASS = DramatiqBatchProcessor

th_context = TranscriptHeroContext(app, db)

setup_payment_processing(app)
security = security_register(th_context)
setup_uploads(app)
admin_register(app, db)
register_error_handlers(app)


app.register_blueprint(public())
app.register_blueprint(basic(th_context), url_prefix='/basic')
app.register_blueprint(webhooks(th_context), url_prefix='/webhooks')
