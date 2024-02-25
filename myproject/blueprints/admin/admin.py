from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required

from ...extensions import db
from ...models import Users, Sessions, Players, Pokemon, Pokedex
from ...webforms import LoginForm, RegisterForm, AdminAddPokedexForm, SearchNumberForm, SearchSpeciesForm

import csv

admin = Blueprint('admin', __name__, template_folder='templates')

# Index
@admin.route('/')
def index():
    return "Admin Page"

# Admin Test Pages
# Admin route for showing all sessions in DB
@admin.route('/sessions', methods=['GET', 'POST'])
def admin_sessions():
    sessions = Sessions.query.order_by(Sessions.id)
    return render_template('admin_sessions.html', sessions=sessions)

# Admin Delete Session
@admin.route('/sessions/delete/<int:session_id>', methods=['GET', 'POST'])
def admin_delete_session(session_id):
    session_to_delete = Sessions.query.get(session_id)
    try:
        db.session.delete(session_to_delete)
        db.session.commit()
    except:
        flash("Could Not Delete this session")
    return redirect(url_for('admin.admin_sessions'))


# Admin route for showing all users in DB
@admin.route('/users', methods=['GET', 'POST'])
def admin_users():
    users = Users.query.order_by(Users.id)
    return render_template('admin_users.html', users=users)


# Admin route for showing all players in DB
@admin.route('/players', methods=['GET', 'POST'])
def admin_players():
    players = Players.query.order_by(Players.id)
    return render_template('admin_players.html', players=players)


# Admin route for showing all pokemon in DB
@admin.route('/pokemon', methods=['GET', 'POST'])
def admin_pokemon():
    pokemon = Pokemon.query.order_by(Pokemon.id)
    return render_template('admin_pokemon.html', pokemon=pokemon)


# Admin route for deleting pokemon and any pokemon linked to said pokemon
@admin.route('/pokemon/delete/<int:mon_id>', methods=['POST'])
@login_required
def admin_delete_pokemon(mon_id):
    link_id = Pokemon.query.get_or_404(mon_id).link_id
    session_num = Pokemon.query.get_or_404(mon_id).player.session.id
    for player in Players.query.filter_by(session_id=session_num):
        pokemon_to_delete = Pokemon.query.filter_by(link_id=link_id, player_id=player.id).first()
        try:
            db.session.delete(pokemon_to_delete)
            db.session.commit()
            print("Problem deleting pokemon")
        except:
            print("Pokemon for this player does not exist")
    return redirect('/admin/pokemon')


# Admin route for showing the pokedex in DB
@admin.route('/pokedex', methods=['GET', 'POST'])
def admin_pokedex():
    numberform = SearchNumberForm()
    speciesform = SearchSpeciesForm()
    if speciesform.validate_on_submit():
        search_results = Pokedex.query.filter_by(species=speciesform.species.data)
        speciesform.species.data = ''
        return render_template('admin_pokedex.html', speciesform=speciesform, numberform=numberform, search_results=search_results)
    if numberform.validate_on_submit():
        search_results = Pokedex.query.filter_by(number=numberform.number.data)
        numberform.number.data = ''
        return render_template('admin_pokedex.html', speciesform=speciesform, numberform=numberform, search_results=search_results)
    return render_template('admin_pokedex.html', speciesform=speciesform, numberform=numberform)
