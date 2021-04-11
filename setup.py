from setuptools import setup, find_packages

setup(
    name='transcript_hero',
    version='3.0',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'transcript_hero_scheduler = transcript_hero_job.scheduler:main'
        ]

    },
    install_requires=[
        'werkzeug==0.16.0',
        'flask',
        'pymysql',
        'flask-sqlalchemy-session',
        'Flask-Migrate',
        'authlib',
        'flask-login',
        'flask-principal',
        'Flask-WTF',
        'flask-security',
        'bcrypt',
        'WTForms-alchemy',
        'xhtml2pdf',
        'flask-admin',
        'stripe',
        'dramatiq[rabbitmq]',
        'APScheduler',
        'python-dotenv',
        'flask-uploads',
        'zeep',
        'pycountry',
        'sqlalchemy-citext'
    ],
    extras_require={
        'dev': [
            'autopep8',
            'pycodestyle<2.4.0,>=2.0.0',
            'flake8',
            'rope',
            'dramatiq[watch]',
            'coverage'
        ],
        'postgre': [
            'psycopg2-binary'
        ]
    }
)
