"""Flask application for the QEC decoder visualization."""

from flask import Flask

app = Flask(
    __name__,
    static_folder="../static",
    static_url_path="/static",
)

from server.routes import register_routes  # noqa: E402
register_routes(app)
