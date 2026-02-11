from flask import Flask
import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    # Get the absolute path to the project root
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    app = Flask(__name__,
                template_folder=os.path.join(basedir, 'templates'),
                static_folder=os.path.join(basedir, 'static'))
    
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-in-production")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    # Setup logging
    logs_dir = os.path.join(basedir, "logs")
    if not os.path.exists(logs_dir):
        os.mkdir(logs_dir)

    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, "switch_migration.log"),
        maxBytes=10240000,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("Huawei Switch Migration startup")

    # Register routes
    from app import routes
    app.register_blueprint(routes.bp)

    return app
