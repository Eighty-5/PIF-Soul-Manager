from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import login_user, LoginManager, login_required, logout_user, current_user

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)