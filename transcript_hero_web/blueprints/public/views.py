import os
from flask import render_template, redirect, url_for, send_file, current_app, abort
from flask_security import current_user


def index():
    if current_user.is_active and current_user.is_authenticated:
        return redirect(url_for('basic.index'))

    return render_template('index.html')


def user_help():
    return render_template('help/index.html')


def custom_css():
    custom_css = os.path.abspath(current_app.config['CUSTOM_CSS'])
    if os.path.isfile(custom_css) and custom_css.endswith(".css"):
        return send_file(custom_css)
    return abort(404)


def register(public):
    public.add_url_rule('/', 'index', index)
    public.add_url_rule('/help', 'help', user_help)
    public.add_url_rule('/custom_css', 'custom_css', custom_css)
