from factory import Sequence
from factory.alchemy import SQLAlchemyModelFactory

from .database import db
from .models import User

class BaseFactory(SQLAlchemyModelFactory):
    class Meta:

        abstract = True
        sqlalchemy_session = db.session


class UserFactory(BaseFactory):

    username = Sequence(lambda n: f"user{n}")
    password = Sequence(lambda n: "password")
    active = True

    class Meta:
        model = User