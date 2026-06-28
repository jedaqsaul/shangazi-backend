"""
App Factory
-----------
Creates and configures the Flask application.
Using the factory pattern allows:
  - Multiple app instances (testing, development, production)
  - Clean extension initialization
  - Avoidance of circular imports

Usage:
    from app import create_app
    app = create_app()  # uses FLASK_ENV from environment
"""

import os
from flask import Flask
from dotenv import load_dotenv

from app.extensions import db, jwt, migrate, cors, limiter
from app.utils.error_handlers import register_error_handlers
from app.utils.logger import get_logger
from app.config import config_map

load_dotenv()

logger = get_logger(__name__)


def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory function.
    config_name: 'development' | 'production' (defaults to FLASK_ENV env var)
    """
    app = Flask(__name__)

    # ── Load Configuration ────────────────────────────────────────────────
    env = config_name or os.environ.get("FLASK_ENV", "development")
    config_class = config_map.get(env, config_map["development"])
    app.config.from_object(config_class)

    # NOTE: from_object() only pulls attributes off config_class — it does not
    # know which "env" string was used to select that class. Several places
    # (e.g. the Daraja callback IP whitelist) need to read the resolved
    # environment name from app.config, so we store it explicitly here.
    app.config["FLASK_ENV"] = env

    logger.info(f"Starting Shangazi Foundation backend in [{env}] mode")

    # ── Initialize Extensions ─────────────────────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    cors.init_app(app, resources={
        r"/api/*": {
            "origins": [app.config["FRONTEND_URL"]],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
        }
    })

    # ── Register Blueprints ───────────────────────────────────────────────
    from app.routes.auth_routes import auth_bp
    from app.routes.donation_routes import donation_bp
    from app.routes.daraja_routes import daraja_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.gallery_routes import gallery_bp, admin_gallery_bp
    from app.routes.impact_story_routes import impact_story_bp, admin_impact_story_bp
    from app.routes.program_routes import program_bp, admin_program_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(donation_bp)
    app.register_blueprint(daraja_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(admin_gallery_bp)
    app.register_blueprint(impact_story_bp)
    app.register_blueprint(admin_impact_story_bp)
    app.register_blueprint(program_bp)
    app.register_blueprint(admin_program_bp)

    # ── Register Error Handlers ───────────────────────────────────────────
    register_error_handlers(app)

    # ── Health Check Endpoint ─────────────────────────────────────────────
    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "Shangazi Foundation API"}, 200

    # ── Register CLI Commands ─────────────────────────────────────────────
    _register_cli_commands(app)

    # ── Import models so Flask-Migrate detects them ───────────────────────
    with app.app_context():
        from app.models import User, Donation, AuditLog, GalleryImage, ImpactStory, Program  # noqa: F401

    return app


def _register_cli_commands(app: Flask) -> None:
    """Register Flask CLI management commands."""

    @app.cli.command("seed-admin")
    def seed_admin():
        """Create the initial super admin user from environment variables."""
        from app.services.auth_service import AuthService

        username = os.environ.get("INITIAL_ADMIN_USERNAME", "superadmin")
        email = os.environ.get("INITIAL_ADMIN_EMAIL")
        password = os.environ.get("INITIAL_ADMIN_PASSWORD")

        if not email or not password:
            print("ERROR: Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD in .env")
            return

        user = AuthService.seed_super_admin(username, email, password)
        if user:
            print(f"Super admin created: {email}")
        else:
            print("Super admin already exists. No action taken.")

    @app.cli.command("create-tables")
    def create_tables():
        """Create all database tables (development only)."""
        db.create_all()
        print("Database tables created.")
