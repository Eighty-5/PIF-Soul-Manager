from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from ...extensions import db
from ...models import User, Save, Player, Pokemon, Pokedex
from ...webforms import LoginForm, RegisterForm, AdminAddPokedexForm, SearchNumberForm, SearchSpeciesForm

import csv

admin = Blueprint('admin', __name__, template_folder='templates')

# Index
@admin.route('/')
def index():
    return "Admin Page"

# Admin Test Pages
# Admin route for showing all saves in DB
@admin.route('/saves', methods=['GET', 'POST'])
def admin_saves():
    saves = db.session.scalars(db.select(Save))
    return render_template('admin_saves.html', saves=saves)

# Admin Delete Save
@admin.route('/saves/delete/<int:save_id>', methods=['GET', 'POST'])
def admin_delete_save(save_id):
    save_to_delete = db.session.scalar(db.select(Save).where(Save.id==save_id))
    if save_to_delete:
        db.session.delete(save_to_delete)
        db.session.commit()
    return redirect(url_for('admin.admin_saves'))


# Admin route for showing all users in DB
@admin.route('/users', methods=['GET', 'POST'])
def admin_users():
    users = db.session.scalars(db.select(User).order_by(User.id))
    return render_template('admin_users.html', users=users)


# Admin route for showing all players in DB
@admin.route('/players', methods=['GET', 'POST'])
def admin_players():
    players = db.session.scalars(db.select(Player).order_by(Player.id))
    return render_template('admin_players.html', players=players)


# Admin route for showing all pokemon in DB
@admin.route('/pokemon', methods=['GET', 'POST'])
def admin_pokemon():
    pokemons = db.session.scalars(db.select(Pokemon).order_by(Pokemon.id))
    return render_template('admin_pokemon.html', pokemons=pokemons)


# Admin route for deleting pokemon and any pokemon linked to said pokemon
@admin.route('/pokemon/delete/<int:pokemon_id>', methods=['POST'])
@login_required
def admin_delete_pokemon(mon_id):
    selection = db.session.scalar(db.select(Pokemon).where(Pokemon.id==mon_id))
    link_id = selection.link_id
    selection_save = selection.player.saves
    pokemon_to_delete = db.session.scalars(db.select(Pokemon).join(Pokemon.player).where(Pokemon.link_id==link_id, Player.saves==selection_save))
    db.session.delete(pokemon_to_delete)
    db.session.commit()
    return redirect('/admin/pokemon')


# Admin route for showing the pokedex in DB
@admin.route('/pokedex', methods=['GET', 'POST'])
def admin_pokedex():
    numberform = SearchNumberForm()
    speciesform = SearchSpeciesForm()
    if speciesform.validate_on_submit():
        search_results = db.session.scalars(db.select(Pokedex).where(Pokedex.species==speciesform.species.data))
        speciesform.species.data = ''
        return render_template('admin_pokedex.html', speciesform=speciesform, numberform=numberform, search_results=search_results)
    if numberform.validate_on_submit():
        search_results = db.session.scalars(db.select(Pokedex).where(Pokedex.number==numberform.number.data))
        print(search_results)
        numberform.number.data = ''
        return render_template('admin_pokedex.html', speciesform=speciesform, numberform=numberform, search_results=search_results)
    return render_template('admin_pokedex.html', speciesform=speciesform, numberform=numberform)

