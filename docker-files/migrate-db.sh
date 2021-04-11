#!/bin/sh
# attempts to migrate to a new format of the database
source venv/bin/activate
export FLASK_APP=transcript_hero_web
flask db init
flask db migrate
flask db upgrade
rm -r migrations