from .extensions import db
from flask_login import UserMixin
from datetime import datetime

# Models
# Create Users model
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    hash = db.Column(db.String(128))
    sessions = db.relationship('Sessions', cascade='all, delete', backref='user')
    current_session = db.Column(db.Integer)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

# Create Sessions Model
class Sessions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    number = db.Column(db.Integer)
    ruleset = db.Column(db.Integer)
    route_tracking = db.Column(db.Boolean, default=False, nullable=False)
    players = db.relationship('Players', cascade='all, delete', backref='session')

# Create Players model
class Players(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), index=True)
    number = db.Column(db.Integer)
    name = db.Column(db.String(20))
    pokemon = db.relationship('Pokemon', cascade='all, delete', backref='player')

# Create Pokemon Model
class Pokemon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), index=True, nullable=False)
    pokedex_number = db.Column(db.String(17), db.ForeignKey('pokedex.number'), index=True, nullable=False)
    sprite = db.Column(db.String(20), db.ForeignKey('artists.sprite'), index=True, nullable=False)
    nickname = db.Column(db.String(30))
    link_id = db.Column(db.Integer)
    linked = db.Column(db.Boolean, default=None, nullable=True)
    route = db.Column(db.Integer, nullable=True)
    position = db.Column(db.String(5), nullable=False)

# Create Base Pokedex Model
class PokedexBase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(5), unique=True, nullable=False)
    species = db.Column(db.String(30), nullable=False)
    pokedex_base_1 = db.relationship('Pokedex', foreign_keys="Pokedex.base_id_1", cascade='save-update', backref='base_1')
    pokedex_base_2 = db.relationship('Pokedex', foreign_keys="Pokedex.base_id_2", cascade='save-update', backref='base_2')
    hp = db.Column(db.Integer)
    attack = db.Column(db.Integer)
    defense = db.Column(db.Integer)
    sp_attack = db.Column(db.Integer)
    sp_defense = db.Column(db.Integer)
    speed = db.Column(db.Integer)
    total = db.Column(db.Integer)

# Create Pokedex Model
class Pokedex(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(17), unique=True, index=True, nullable=False)
    species = db.Column(db.String(30), nullable=False)
    base_id_1 = db.Column(db.String(5), db.ForeignKey('pokedex_base.number'), nullable=False)
    base_id_2 = db.Column(db.String(5), db.ForeignKey('pokedex_base.number'), nullable=True)
    type_primary = db.Column(db.String(10), nullable=False)
    type_secondary = db.Column(db.String(10), nullable=True)
    family = db.Column(db.String(17), index=True, nullable=False)
    family_order = db.Column(db.String(10), nullable=False)
    hp = db.Column(db.Integer)
    attack = db.Column(db.Integer)
    defense = db.Column(db.Integer)
    sp_attack = db.Column(db.Integer)
    sp_defense = db.Column(db.Integer)
    speed = db.Column(db.Integer)
    total = db.Column(db.Integer)
    pokemon = db.relationship('Pokemon', cascade='save-update', backref='info')
    artists = db.relationship('Artists', cascade='save-update', backref='pokedex_info')

# Sprite/Artist Model
class Artists(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pokedex_number = db.Column(db.String(17), db.ForeignKey('pokedex.number'), index=True, nullable=False)
    sprite = db.Column(db.String(20), unique=True, index=True)
    variant_let = db.Column(db.String(2))
    artist = db.Column(db.String(100))
    pokemon = db.relationship('Pokemon', cascade='save-update', backref='artist')

