from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # Configuration de la base de données
   # 👉 charge toute la config depuis Config
    app.config.from_object(Config)
    # Initialisation des extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Enregistrement des blueprints
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app