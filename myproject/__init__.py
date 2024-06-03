from flask import Flask
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from .extensions import db
from .models import Users
from dotenv import load_dotenv
from flask_migrate import Migrate

import os
import jinja2

from .blueprints.main.main import main
from .blueprints.admin.admin import admin
from .blueprints.manage_users.manage_users import manage_users
from .blueprints.pokemon.pokemon import pokemon

# Load env variables
load_dotenv()

# CSRF Protections
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)

    # Config MySQL
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')

    # Secret Key
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

    # Add zip to jinja
    app.jinja_env.globals.update(zip=zip)

    # Flask Login Stuff
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'manage_users.login'

    @login_manager.user_loader
    def load_user(user_id):
        return Users.query.get(user_id)
    
    csrf.init_app(app)
    
    db.init_app(app)
    migrate = Migrate(app, db)

    app.register_blueprint(main)
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(manage_users)
    app.register_blueprint(pokemon, url_prefix='/pokemon')

    return app
