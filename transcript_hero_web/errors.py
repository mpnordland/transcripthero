from flask import render_template


def register_error_handlers(app):
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(404)
    def not_found(e=None):
        return render_template("errors/404.html"), 404

    app.add_url_rule("/not-found", 'not_found', not_found)
