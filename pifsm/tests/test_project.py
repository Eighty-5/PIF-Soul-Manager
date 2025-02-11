from pifsm.models import User, Save
from pifsm.extensions import db

def test_home(client):
    response = client.get("/")
    assert b"<title>IFSM: About</title>" in response.data


def test_registration(client, app):
    response = client.post("/register", data={'username': 'Tester 1', 'password': 'password', 'password_confirm': 'password'})

    with app.app_context():
        assert len(db.session.scalars(db.select(User)).all()) == 1
        assert db.session.scalar(db.select(User).where(User.username=='Tester 1'))

def test_login(client, app):
    client.post("/login", data={'username': 'Tester 1', 'password': 'password'})


def test_create_save(client, app):
    client.post("/login", data={'username': 'Tester 1', 'password': 'password'})

    response = client.post("/save/create", data={
        'save_name':'New Save',
        'player_num': 2,
        'ruleset': 3,
        'player_names': [{'player_name': 'Red'}, {'player_name': 'Blue'}]
    })
    
    with app.app_context():
        assert db.session.scalar(db.select(Save).where(Save.user_info.has(User.username=="Tester 1")))
