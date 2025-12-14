#!/usr/bin/env python3
"""
Config Backup - Switch Configuration Backup System
Backup Huawei switch configurations via SSH/Telnet with diff visualization.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS

# Support both module and standalone execution
try:
    from .routes import bp as routes_bp
    from . import database
except ImportError:
    from routes import bp as routes_bp
    import database


def create_app():
    """Create and configure Flask application"""

    # Get app directory
    app_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(app_dir, 'templates'),
        static_folder=os.path.join(app_dir, 'static'),
    )

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'config-backup-secret-key')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

    # Enable CORS
    CORS(app, origins=["*"])

    # Setup logging
    setup_logging(app, app_dir)

    # Initialize database
    database.init_db()

    # Ensure backups directory exists
    backups_dir = os.path.join(app_dir, 'backups')
    os.makedirs(backups_dir, exist_ok=True)

    # Register blueprint
    app.register_blueprint(routes_bp)

    app.logger.info("Config Backup application initialized")

    return app


def setup_logging(app, app_dir):
    """Setup logging with rotating file handler"""

    # Create logs directory
    logs_dir = os.path.join(app_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # File handler
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'config_backup.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    ))
    file_handler.setLevel(logging.INFO)

    # Apply to app and root logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    # Also configure root logger for module loggers
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        handlers=[file_handler]
    )


# Create app instance
app = create_app()


if __name__ == '__main__':
    # Run development server
    app.run(
        host='0.0.0.0',
        port=5003,
        debug=True
    )
