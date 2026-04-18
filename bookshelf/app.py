"""Factory da aplicação Flask."""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from .config import get_config
from .models import db


def create_app(config_object: object | None = None) -> Flask:
    """Cria e configura a aplicação principal."""

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(get_config())

    if config_object is not None:
        if isinstance(config_object, dict):
            app.config.update(config_object)
        else:
            app.config.from_object(config_object)

    db.init_app(app)
    CORS(app)

    from .api.books import books_bp
    from .api.connections import connections_bp
    from .api.genres import genres_bp
    from .api.graph import graph_bp
    from .api.stats import stats_bp
    from .api.tags import tags_bp
    from .views import register_views

    app.register_blueprint(books_bp, url_prefix="/api")
    app.register_blueprint(genres_bp, url_prefix="/api")
    app.register_blueprint(tags_bp, url_prefix="/api")
    app.register_blueprint(connections_bp, url_prefix="/api")
    app.register_blueprint(graph_bp, url_prefix="/api")
    app.register_blueprint(stats_bp, url_prefix="/api")
    register_views(app)

    with app.app_context():
        db.create_all()

    return app
