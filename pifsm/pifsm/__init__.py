from flask import Flask
from flask_login import LoginManager
from .extensions import (
    csrf_protect,
    db,
    login_manager,
    migrate
)
from .models import User
from dotenv import load_dotenv
from flask_migrate import Migrate

from sqlalchemy.orm import sessionmaker, Session

import os
import logging

# Load env variables
load_dotenv()

def create_app(config_object="pifsm.settings"):
    
    app = Flask(__name__)
    app.config.from_object(config_object)
    # Configure Logging
    # logging.basicConfig()
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


    # Flask Login Stuff
    register_blueprints(app)
    register_extensions(app) 

    return app


def register_extensions(app):
    db.init_app(app)
    csrf_protect.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    migrate = Migrate(app, db)



def register_blueprints(app):
    from pifsm import (main, admin, auth, pokemon)
    app.register_blueprint(main.views.main)
    app.register_blueprint(admin.views.admin, url_prefix='/admin')
    app.register_blueprint(auth.views.auth)
    app.register_blueprint(pokemon.views.pokemon, url_prefix='/pokemon')