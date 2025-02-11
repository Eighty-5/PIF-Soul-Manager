import pytest
import logging

from pifsm import create_app, db as db
from .factories import UserFactory

@pytest.fixture()
def app():
    app = create_app(config_object="tests.settings")

    with app.app_context():
        db.create_all()

    yield app

@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture
def user(db):
    user = UserFactory(password="password")
    db.session.commit()
    return user