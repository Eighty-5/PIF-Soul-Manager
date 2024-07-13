from collections import Counter
from ...extensions import db
from flask import Blueprint, request, flash, redirect, url_for
from flask_login import login_required, current_user
from ...models import User, Save, Player, Pokemon, Pokedex
from .pokemon_utils import add_pokemon_per_ruleset_group, create_fusion_pokemon, dex_check, evolution_check, get_new_link_id, remove_route_key    
from sqlalchemy import or_
from ...utils import get_default_vars

import random

pokemon = Blueprint('pokemon', __name__, template_folder='templates')

MANUAL_RULESET = 1
AUTO_RULESET = [2, 3]
ROUTE_RULESET = 4
SPECIAL_RULESET = 5
# Add Pokemon to Save route


@pokemon.route('/add', methods=['POST'])
@login_required
def add_pokemon():
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    # ADD SERVER SIDE CHECKS HERE

    if ruleset != MANUAL_RULESET:
        try:
            route = request.form['route']
            max_num = 1 if ruleset == 2 else 2
            if not Pokemon.query.join(Save.players).join(Player.pokemon).filter(
                    Save.id == current_session_id).filter(Pokemon.route == route).count() < max_num * len(current_session.players):
                flash("Maximum Pokemon caught for that route. Please choose another")
                return redirect(url_for('main.view_session'))
        except KeyError:
            flash("No route selected")
            return redirect(url_for('main.view_session'))
    pokemon_to_add_dict = {}
    for key, value in request.form.items():
        if key != 'route' and key != 'csrf_token':
            pokemon_to_add_dict[key] = value
    if ruleset == MANUAL_RULESET:
        added_pokemon_lst = []
        for player_num in pokemon_to_add_dict:
            species = pokemon_to_add_dict[player_num]
            link_id = get_new_link_id(current_session.id)
            add_pokemon_per_ruleset_group(
                'manual', player_num, species, link_id, None, current_session_id)
            added_pokemon_lst.append(species)
        flash(f"{', '.join(added_pokemon_lst)} were added to the session!")
        db.session.commit()
    elif ruleset in AUTO_RULESET:
        link_id = get_new_link_id(current_session.id)
        added_pokemon_lst = []
        for player_num in pokemon_to_add_dict:
            species = pokemon_to_add_dict[player_num]
            add_pokemon_per_ruleset_group(
                'auto', player_num, species, link_id, route, current_session_id)
            added_pokemon_lst.append(species)
        flash(f"{', '.join(added_pokemon_lst)} were added to the session!")
        db.session.commit()
    elif ruleset in [ROUTE_RULESET, SPECIAL_RULESET]:
        added_pokemon_lst = []
        for player_num in pokemon_to_add_dict:
            species = pokemon_to_add_dict[player_num]
            add_pokemon_per_ruleset_group(
                'route', player_num, species, 'temp', route, current_session_id)
            added_pokemon_lst.append(species)
        flash(f"{', '.join(added_pokemon_lst)} were added to the session!")
        db.session.commit()
    else:
        flash("""NOT VIABLE RULESET: PLEASE USE DESIGNATED 
              RULESET OR RECREATE SESSION WITH FULL FREEDOM RULESET""")
    return redirect(url_for('main.view_session'))


@pokemon.route('/add/random', methods=['POST'])
@login_required
def add_random():
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    link_id = get_new_link_id(current_session.id)
    taken_routes = [r.route for r in Pokemon.query.join(Save.players).join(Player.pokemon).filter(Save.id == current_session_id, Player.number == 1)]
    rand_route = random.randrange(1, 100)
    if ruleset == 2:
        while taken_routes.count(rand_route) >= 1:
            rand_route = random.randrange(1, 100)
    else:
        while taken_routes.count(rand_route) >= 2:
            rand_route = random.randrange(1, 100)
    # ADD SERVER SIDE CHECKS HERE
    added_pokemon_lst = []
    for player in current_session.players:
        if ruleset == MANUAL_RULESET:
            link_id, linked, rand_route = get_new_link_id(current_session_id), False, None
        elif ruleset in AUTO_RULESET:
            linked = True
        elif ruleset in [ROUTE_RULESET, SPECIAL_RULESET]:
            link_id, linked = get_new_link_id(current_session_id), False
        rand_pokedex_number = random.randrange(1, Pokedex.query.filter(Pokedex.base_id_1==None).count())
        print(rand_pokedex_number)

        pokemon = Pokemon(
            player_id=player.id,
            pokedex_number=rand_pokedex_number,
            sprite=rand_pokedex_number,
            link_id=link_id,
            linked=linked,
            route=rand_route,
            position='box')
        db.session.add(pokemon)
        added_pokemon_lst.append(rand_pokedex_number)
    added_pokemon_lst = [Pokedex.query.filter(Pokedex.number == i).first().species for i in added_pokemon_lst]
    db.session.commit()
    flash(f"{', '.join(added_pokemon_lst)} were added to the session! ")
    return redirect(url_for('main.view_session'))


# Change Variant Route
@pokemon.route('/variant/<player_num>/<link_id>', methods=['POST'])
@login_required
def change_variant(player_num, link_id):
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    variant = request.form.get("variant_select")
    if variant == 'default':
        variant = ''
    elif variant is None:
        flash("Please select a variant sprite to switch to")
        return redirect(url_for('main.view_session')) 
    variant_to_change = Pokemon.query.join(Player).join(Save).filter(
        Save.id == current_session_id).filter(
        Player.number == player_num).filter(
            Pokemon.link_id == link_id).first()
    print(variant_to_change.pokedex_number, variant)
    variant_to_change.sprite = variant_to_change.pokedex_number + variant
    db.session.commit()
    return redirect(url_for('main.view_session'))


# Fuse Pokemon Route
@pokemon.route('/fuse', methods=['POST'])
@login_required
def fuse_pokemon():
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    head_link_ids, body_link_ids = [], []
    
    for key, value in request.form.items():
        if value is not None and not key == 'csrf_token':
            if 'Head' in key:
                head_link_ids.append(value)
            elif 'Body' in key:
                body_link_ids.append(value)
            else:
                flash("Error")
                return redirect(url_for('main.view_session'))

    player_count = len(current_session.players)
    if len(head_link_ids) != player_count or len(body_link_ids) != player_count:
        flash("Ensure head and body is selected for each player")
        return redirect(url_for('main.view_session'))
    elif any(count > player_count for count in Counter(head_link_ids + body_link_ids).values()):
        flash("Fusion Failed: A Pokemon was used multiple times in one fusion")
        return redirect(url_for('main.view_session'))
    
    new_link_id = get_new_link_id(current_session_id)
    if ruleset == ROUTE_RULESET:
        head_routes = [r.route for r in Pokemon.query.join(Save.players).join(Player.pokemon).filter(Save.id == current_session.id, Pokemon.link_id.in_(head_link_ids))]
        body_routes = [r.route for r in Pokemon.query.join(Save.players).join(Player.pokemon).filter(Save.id == current_session.id, Pokemon.link_id.in_(body_link_ids))]
        if all(i == head_routes[0] for i in head_routes) and all(
                i == head_routes[0] for i in body_routes):
            create_fusion_pokemon(new_link_id, head_link_ids, body_link_ids, ruleset, current_session_id)
        else:
            flash("not valid fusions")
    elif ruleset == SPECIAL_RULESET:
        players_routes = []
        for head, body in zip(head_link_ids, body_link_ids):
            players_routes.append(sorted([r.route for r in Pokemon.query.join(Save.players).join(Player.pokemon).filter(Save.id == current_session_id, or_(Pokemon.link_id == head, Pokemon.link_id == body))]))
        if all(i == players_routes[0] for i in players_routes):
            create_fusion_pokemon(new_link_id, head_link_ids, body_link_ids, ruleset, current_session_id)
        else:
            flash("not valid fusions")
    elif ruleset in AUTO_RULESET:
        players_link_ids = []
        for head, body in zip(head_link_ids, body_link_ids):
            players_link_ids.append(sorted([head, body]))
        if all(i == players_link_ids[0] for i in players_link_ids):
            create_fusion_pokemon(new_link_id, head_link_ids, body_link_ids, ruleset, current_session_id)
        else:
            flash("not valid fusions")
    elif ruleset == MANUAL_RULESET:
        create_fusion_pokemon(new_link_id, head_link_ids, body_link_ids, ruleset, current_session_id)
    else:
        flash("Ruleset does not exist")
    return redirect(url_for('main.view_session'))


# Delete a pokemon from session route
@pokemon.route('/delete/<int:link_id>', methods=['POST'])
@login_required
def delete_pokemon(link_id):
    id = current_user.id
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    pokemon_to_delete = Pokemon.query.join(Save.players).join(Player.pokemon).filter(Save.id==current_session_id).filter(Pokemon.link_id==link_id)
    deleted_pokemon = []
    for pokemon in pokemon_to_delete:
        deleted_pokemon.append(pokemon.info.species)
        db.session.delete(pokemon)
    db.session.commit()
    flash(f"{', '.join(deleted_pokemon)} deleted from session")
    if id == 1:
        return redirect(url_for('admin.admin_pokemon'))
    else:
        return redirect(url_for('main.view_session'))


@pokemon.route('/evolve/<int:player_num>/<int:link_id>', methods=['POST'])
@login_required
def evolve_pokemon(player_num, link_id):
    id = current_user.id
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    # Check if evolution is a valid evolution
    evolution = request.form.get(f"evolve_{str(player_num)}_{str(link_id)}")
    pokemon_to_evolve = Pokemon.query.join(Player).join(Save).filter(
        Save.id == current_session_id).filter(
        Player.number == player_num).filter(
            Pokemon.link_id == link_id).first()
    base_id = pokemon_to_evolve.pokedex_number
    prevolution = pokemon_to_evolve.info.species
    if dex_check(evolution) and evolution_check(evolution, base_id):
        pokemon_to_evolve.pokedex_number = evolution
        pokemon_to_evolve.sprite = evolution
        db.session.commit()
        newvolution = pokemon_to_evolve.info.species
        flash(f"{prevolution} evolved into {newvolution}")
    else:
        flash("Not a valid evolution")
    return redirect(url_for('main.view_session'))


@pokemon.route('/switch/party/<link_id>', methods=['POST'])
@login_required
def switch_party(link_id):
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_session'))
    id = current_user.id
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    for key, value in request.form.items():
        if value.isdigit():
            pokemon_to_box = Pokemon.query.join(Save.players).join(Player.pokemon).filter(Save.id == current_session_id, Pokemon.link_id == value)
            for pokemon in pokemon_to_box:
                pokemon.position = 'box'
    pokemon_to_party = Pokemon.query.join(Save.players).join(Player.pokemon).filter(Save.id == current_session_id, Pokemon.link_id == link_id)
    for pokemon in pokemon_to_party:

        if Pokemon.query.filter(Pokemon.player_id == pokemon.player_id, Pokemon.position == "party").count() >= 6:
            flash("Party is full or pokemon is soul-linked to another pokemon whose Player party is full")
            return redirect(url_for('main.view_session'))
        else:
            pokemon.position = 'party'
    db.session.commit()
    return redirect(url_for('main.view_session'))


@pokemon.route('/switch/box/<link_id>', methods=['POST'])
@login_required
def switch_box(link_id):
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_session'))
    id = current_user.id
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    pokemon_to_box = Pokemon.query.join(Player).join(Save).join(User).filter(
        User.id == id).filter(
        Save.id == current_session_id).filter(
            Pokemon.link_id == link_id)
    for pokemon in pokemon_to_box:
        pokemon.position = 'box'
    for key, value in request.form.items():
        if value.isdigit():
            pokemon_to_party = Pokemon.query.join(Player).join(Save).join(User).filter(
                User.id == id).filter(
                Save.id == current_session_id).filter(
                Pokemon.link_id == value)
            for pokemon in pokemon_to_party:
                if Pokemon.query.filter(Pokemon.player_id == pokemon.player_id, Pokemon.position == "party").count() >= 6:
                    flash("Pokemon in box is linked with another pokemon whose Player party is full")
                    return redirect(url_for('main.view_session'))
                else:
                    pokemon.position = 'party'
    db.session.commit()
    return redirect(url_for('main.view_session'))


@pokemon.route('/switch/dead/<link_id>', methods=['POST'])
@login_required
def switch_dead(link_id):
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_session'))
    id = current_user.id
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    pokemon_to_dead = Pokemon.query.join(Player).join(Save).join(User).filter(
        User.id == id).filter(
        Save.id == current_session_id).filter(
            Pokemon.link_id == link_id)
    for pokemon in pokemon_to_dead:
        pokemon.position = 'dead'
        db.session.commit()
    return redirect(url_for('main.view_session'))


@pokemon.route('/switch/revive/<link_id>', methods=['POST'])
@login_required
def switch_revive(link_id):
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_session'))
    id = current_user.id
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    pokemon_to_box = Pokemon.query.join(Player).join(Save).join(User).filter(
        User.id == id).filter(
        Save.id == current_session_id).filter(
            Pokemon.link_id == link_id)
    for pokemon in pokemon_to_box:
        pokemon.position = 'box'
        db.session.commit()

    return redirect(url_for('main.view_session'))


# BUG TESTING REQUIRED
@pokemon.route('/link/<link_id_1>', methods=['POST'])
@login_required
def link_pokemon(link_id_1):
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    if ruleset != MANUAL_RULESET:
        flash("Cannot perform manual link for current ruleset!")
        return redirect(url_for('main.view_session'))
    for key, value in request.form.items():
        if key != 'csrf_token':
            print(key, value)
            link_id_2 = int(value)
    pokemon_1 = Pokemon.query.join(
        Save.players).join(
        Player.pokemon).filter(
            Pokemon.link_id == int(link_id_1),
        Save.id == current_session_id)
    pokemon_2 = Pokemon.query.join(
        Save.players).join(
        Player.pokemon).filter(
            Pokemon.link_id == link_id_2,
        Save.id == current_session_id)
    print(pokemon_2.first().position)
    if pokemon_1.count() == 0 or pokemon_2.count() == 0:
        flash(f"ERROR: Manual Link Failed - One or Two pokemon missing")
    elif pokemon_1.count() > 1:
        pokemon_names = [pokemon.info.species for pokemon in pokemon_1]
        flash(f"ERROR: Manual Link Failed - {', '.join(pokemon_names)
                                             } are already linked together, please unlink one first.")
    elif pokemon_2.filter(Pokemon.player_id == pokemon_1.first().player_id).first():
        if pokemon_2.count() == 1:
            flash(
                f"ERROR: Manual Link Failed - {
                    pokemon_1.first().info.species} and {
                    pokemon_2.first().info.species} belong to the same player")
        else:
            for pokemon in pokemon_2:
                pokemon_names = [pokemon.info.species for pokemon in pokemon_2]
            flash(
                f"ERROR: Manual Link Failed - Player already has a pokemon linked to {
                    ', '.join(pokemon_names)}. Please unlink {
                    pokemon_2.filter(
                        Pokemon.player_id == pokemon_1.first().player_id).first().info.species} first")
    else:
        pokemon_1 = pokemon_1.first()
        flash(f"Manual Link Successful - {pokemon_1.info.species} successfully linked to {
              ', '.join([pokemon.info.species for pokemon in pokemon_2])}!")
        if pokemon_2.first().position == 'box' and pokemon_1.position == 'party': 
            pokemon_1.position = 'box'
        pokemon_1.link_id, pokemon_1.linked, pokemon_1.position = link_id_2, True, 'box'
        for pokemon in pokemon_2: 
            pokemon.linked, pokemon.position = True, 'box'
        db.session.commit()
    if current_user.id == 1:
        return redirect(url_for('admin.admin_pokemon'))
    else:
        return redirect(url_for('main.view_session'))


@pokemon.route('/unlink/<player_num>/<link_id>', methods=['GET', 'POST'])
@login_required
def unlink_pokemon(player_num, link_id):
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    # pokemon_to_unlink = Pokemon.query.join(Save.players).join(Player.pokemon).filter(Pokemon.link_id==link_id, Save.id==current_session_id, Player.number==player_num)
    pokemon_linked = Pokemon.query.join(
        Save.players).join(
        Player.pokemon).filter(
            Pokemon.link_id == link_id,
        Save.id == current_session_id)
    if pokemon_linked.count() == 0:
        flash(f"ERROR: Unlink Failed - Please select a valid pokemon")
    elif pokemon_linked.count() == 1:
        flash(f"ERROR: Unlink Failed - {
            pokemon_to_unlink.info.species} is not currently linked to another pokemon")
    else:
        pokemon_to_unlink = pokemon_linked.filter(
            Player.number == player_num).first()
        flash(
            f"Manual Link Successful - {pokemon_to_unlink.info.species} successfully unlinked!")
        pokemon_to_unlink.link_id = get_new_link_id(current_session_id)
        pokemon_to_unlink.linked = False
        db.session.commit()
        extra_unlink = Pokemon.query.join(Save.players).join(Player.pokemon).filter(Pokemon.link_id == link_id, Save.id == current_session_id)
        if len(extra_unlink.all()) == 1:
            extra_unlink.first().linked = False
            db.session.commit()
    if current_user.id == 1:
        return redirect(url_for('admin.admin_pokemon'))
    else:
        return redirect(url_for('main.view_session'))


@pokemon.route('/swapfusion/<player_num>/<link_id>', methods=['GET', 'POST'])
@login_required
def swap_fusion(player_num, link_id):
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    fusion_to_swap = Pokemon.query.join(Save.players).join(Player.pokemon).filter(Pokemon.link_id == link_id, Save.id == current_session_id, Player.number == player_num).first()
    if fusion_to_swap.info.base_id_2 is not None:
        fusion_to_swap.pokedex_number = fusion_to_swap.info.base_id_2 + '.' + fusion_to_swap.info.base_id_1
        fusion_to_swap.sprite = fusion_to_swap.pokedex_number
        print(fusion_to_swap.pokedex_number)
        db.session.commit()
    else:
        flash(f"ERROR: Pokemon is not a fused pokemon and cannot swap")

    return redirect(url_for('main.view_session'))

    