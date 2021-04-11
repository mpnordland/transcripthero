all: run

clean:
	rm -rf venv && rm -rf *.egg-info && rm -rf dist && rm -rf *.log* && rm -rf transcript_hero.db && rm -rf migrations

venv:
	virtualenv --python=python3 venv && venv/bin/pip install -e .[dev,postgre]

migrations: venv
	venv/bin/flask db init

dbUpgrade: migrations
	venv/bin/flask db upgrade

dbMigrate: 
	venv/bin/flask db migrate

dbCreate: migrations dbUpgrade

run: venv 
	FLASK_ENV=development venv/bin/flask run

test: venv
	TRANSCRIPT_HERO_SETTINGS=../settings.cfg venv/bin/coverage run --source=transcript_hero,transcript_hero_web,transcript_hero_job -m unittest discover -s tests

sdist: venv test
	venv/bin/python setup.py sdist
