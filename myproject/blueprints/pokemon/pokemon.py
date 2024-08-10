from collections import Counter
from ...extensions import db
from flask import Blueprint, request, flash, redirect, url_for
from flask_login import login_required, current_user
from ...models import User, Save, Player, Pokemon, Pokedex, Sprite
from .pokemon_utils import add_pokemon_per_ruleset_group, create_fusion_pokemon, dex_check, evolution_check, get_new_link_id, remove_route_key    
from sqlalchemy import or_, func
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
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    ruleset = current_save.ruleset
    # ADD SERVER SIDE CHECKS HERE

    if ruleset != MANUAL_RULESET:
        try:
            route = request.form['route']
            max_num = 1 if ruleset == 2 else 2
            route_check = db.session.scalar(db.select(func.count("*")).select_from(Pokemon).join(Pokemon.player).where(Player.saves==current_save, Pokemon.route==route))
            if not route_check < max_num * len(current_save.players):
                flash("Maximum Pokemon caught for that route. Please choose another")
                return redirect(url_for('main.view_save'))
        except KeyError:
            flash("No route selected")
            return redirect(url_for('main.view_save'))
    pokemon_to_add_dict = {}
    for key, value in request.form.items():
        if key != 'route' and key != 'csrf_token':
            pokemon_to_add_dict[key] = value
    if ruleset == MANUAL_RULESET:
        added_pokemon_lst = []
        for player_num in pokemon_to_add_dict:
            species = pokemon_to_add_dict[player_num]
            link_id = get_new_link_id(current_save.id)
            add_pokemon_per_ruleset_group(
                'manual', player_num, species, link_id, None, current_save.id)
            added_pokemon_lst.append(species)
        flash(f"{', '.join(added_pokemon_lst)} were added to the save!")
        db.session.commit()
    elif ruleset in AUTO_RULESET:
        link_id = get_new_link_id(current_save.id)
        added_pokemon_lst = []
        for player_num in pokemon_to_add_dict:
            species = pokemon_to_add_dict[player_num]
            add_pokemon_per_ruleset_group(
                'auto', player_num, species, link_id, route, current_save.id)
            added_pokemon_lst.append(species)
        flash(f"{', '.join(added_pokemon_lst)} were added to the save!")
        db.session.commit()
    elif ruleset in [ROUTE_RULESET, SPECIAL_RULESET]:
        added_pokemon_lst = []
        for player_num in pokemon_to_add_dict:
            species = pokemon_to_add_dict[player_num]
            add_pokemon_per_ruleset_group(
                'route', player_num, species, 'temp', route, current_save.id)
            added_pokemon_lst.append(species)
        flash(f"{', '.join(added_pokemon_lst)} were added to the save!")
        db.session.commit()
    else:
        flash("""NOT VIABLE RULESET: PLEASE USE DESIGNATED 
              RULESET OR RECREATE SAVE WITH FULL FREEDOM RULESET""")
    return redirect(url_for('main.view_save'))


@pokemon.route('/add/random', methods=['POST'])
@login_required
def add_random():
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    ruleset = current_save.ruleset
    link_id = get_new_link_id(current_save.id)
    taken_routes = [r.route for r in Pokemon.query.join(Save.players).join(Player.pokemons).filter(Save.id == current_save.id, Player.number == 1)]
    rand_route = random.randrange(1, 100)
    if ruleset == 2:
        while taken_routes.count(rand_route) >= 1:
            rand_route = random.randrange(1, 100)
    else:
        while taken_routes.count(rand_route) >= 2:
            rand_route = random.randrange(1, 100)
    # ADD SERVER SIDE CHECKS HERE
    added_pokemon_lst = []
    for player in current_save.players:
        if ruleset == MANUAL_RULESET:
            link_id, linked, rand_route = get_new_link_id(current_save.id), False, None
        elif ruleset in AUTO_RULESET:
            linked = True
        elif ruleset in [ROUTE_RULESET, SPECIAL_RULESET]:
            link_id, linked = get_new_link_id(current_save.id), False
        rand_pokedex_number = random.randrange
        rand_pokedex_number = random.randrange(1, db.session.scalar(db.select(func.count("*")).select_from(Pokedex).where(Pokedex.head_id==None)))
        print(rand_pokedex_number)
        new_pokemon_info = db.session.scalar(db.select(Pokedex).where(Pokedex.number==rand_pokedex_number))
        new_sprite = db.session.scalar(db.select(Sprite).where(Sprite.pokedex_info==new_pokemon_info, Sprite.variant_let==''))
        pokemon = Pokemon(
            link_id=link_id,
            linked=linked,
            route=rand_route,
            position='box',
            player=player,
            info=new_pokemon_info,
            sprite=new_sprite)
        db.session.add(pokemon)
        added_pokemon_lst.append(rand_pokedex_number)
    added_pokemon_lst = [Pokedex.query.filter(Pokedex.number == i).first().species for i in added_pokemon_lst]
    db.session.commit()
    flash(f"{', '.join(added_pokemon_lst)} were added to the save! ")
    return redirect(url_for('main.view_save'))


# Change Variant Route
@pokemon.route('/variant/<player_num>/<link_id>', methods=['POST'])
@login_required
def change_variant(player_num, link_id):
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    ruleset = current_save.ruleset
    variant = request.form.get("variant_select")
    if variant == 'default':
        variant = ''
    elif variant is None:
        flash("Please select a variant sprite to switch to")
        return redirect(url_for('main.view_save'))
    variant_to_change = db.session.scalar(db.select(Pokemon).join(Pokemon.player).where(Player.number==player_num, Player.saves==current_save, Pokemon.link_id==link_id))
    new_variant = db.session.scalar(db.select(Sprite).join(Sprite.pokedex_info).where(Pokedex.number==variant_to_change.info.number, Sprite.variant_let==variant))
    if new_variant:
        variant_to_change.sprite = new_variant
        db.session.commit()
    else:
        flash("Please select a valid variant letter")
    return redirect(url_for('main.view_save'))


# Fuse Pokemon Route
@pokemon.route('/fuse', methods=['POST'])
@login_required
def fuse_pokemon():
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    ruleset = current_save.ruleset
    head_link_ids, body_link_ids = [], []
    
    for key, value in request.form.items():
        if value is not None and not key == 'csrf_token':
            if 'Head' in key:
                head_link_ids.append(value)
            elif 'Body' in key:
                body_link_ids.append(value)
            else:
                flash("Error")
                return redirect(url_for('main.view_save'))

    player_count = len(current_save.players)
    if len(head_link_ids) != player_count or len(body_link_ids) != player_count:
        flash("Ensure head and body is selected for each player")
        return redirect(url_for('main.view_save'))
    elif any(count > player_count for count in Counter(head_link_ids + body_link_ids).values()):
        flash("Fusion Failed: A Pokemon was used multiple times in one fusion")
        return redirect(url_for('main.view_save'))
    
    new_link_id = get_new_link_id(current_save.id)
    if ruleset == ROUTE_RULESET:
        head_routes = [r.route for r in db.session.scalars(db.select(Pokemon).join(Pokemon.player).where(Player.saves==current_save, Pokemon.link_id.in_(head_link_ids)))]
        body_routes = [r.route for r in db.session.scalars(db.select(Pokemon).join(Pokemon.player).where(Player.saves==current_save, Pokemon.link_id.in_(body_link_ids)))]
        if all(i == head_routes[0] for i in head_routes) and all(
                i == head_routes[0] for i in body_routes):
            create_fusion_pokemon(new_link_id, head_link_ids, body_link_ids, current_save)
        else:
            flash("not valid fusions")
    elif ruleset == SPECIAL_RULESET:
        players_routes = []
        players_routes.append(sorted([r.route for r in db.session.scalars(db.select(Pokemon)
                                                                          .join(Pokemon.player)
                                                                          .where(Player.saves==current_save, Pokemon.link_id.in_(head_link_ids + body_link_ids)))]))
        if all(i == players_routes[0] for i in players_routes):
            create_fusion_pokemon(new_link_id, head_link_ids, body_link_ids, current_save)
        else:
            flash("not valid fusions")
    elif ruleset in AUTO_RULESET:
        players_link_ids = []
        for head, body in zip(head_link_ids, body_link_ids):
            players_link_ids.append(sorted([head, body]))
        if all(i == players_link_ids[0] for i in players_link_ids):
            create_fusion_pokemon(new_link_id, head_link_ids, body_link_ids, current_save)
        else:
            flash("not valid fusions")
    elif ruleset == MANUAL_RULESET:
        create_fusion_pokemon(new_link_id, head_link_ids, body_link_ids, current_save)
    else:
        flash("Ruleset does not exist")
    return redirect(url_for('main.view_save'))


# Delete a pokemon from save route
@pokemon.route('/delete/<int:link_id>', methods=['POST'])
@login_required
def delete_pokemon(link_id):
    id = current_user.id
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    ruleset = current_save.ruleset
    current_save_id = current_save.id
    pokemon_to_delete = Pokemon.query.join(Save.players).join(Player.pokemon).filter(Save.id==current_save_id).filter(Pokemon.link_id==link_id)
    deleted_pokemon = []
    for pokemon in pokemon_to_delete:
        deleted_pokemon.append(pokemon.info.species)
        db.session.delete(pokemon)
    db.session.commit()
    flash(f"{', '.join(deleted_pokemon)} deleted from save")
    if id == 1:
        return redirect(url_for('admin.admin_pokemon'))
    else:
        return redirect(url_for('main.view_save'))


@pokemon.route('/evolve/<int:player_num>/<int:link_id>', methods=['POST'])
@login_required
def evolve_pokemon(player_num, link_id):
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    ruleset = current_save.ruleset
    current_save_id = current_save.id
    # Check if evolution is a valid evolution
    evolution = request.form.get(f"evolve_{str(player_num)}_{str(link_id)}")
    pokemon_to_evolve = Pokemon.query.join(Player).join(Save).filter(
        Save.id == current_save_id).filter(
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
    return redirect(url_for('main.view_save'))


@pokemon.route('/switch/party/<link_id>', methods=['POST'])
@login_required
def switch_party(link_id):
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_save'))
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    ruleset = current_save.ruleset
    current_save_id = current_save.id
    for key, value in request.form.items():
        if value.isdigit():
            pokemon_to_box = db.session.scalars(db.select(Pokemon).join(Pokemon.player).where(Pokemon.link_id==value, Player.saves==current_save))
            for pokemon in pokemon_to_box:
                pokemon.position = 'box'
    pokemon_to_party = db.session.scalars(db.select(Pokemon).join(Pokemon.player).where(Pokemon.link_id==link_id, Player.saves==current_save))
    for pokemon in pokemon_to_party:

        if pokemon.player.party_length() >= 6:
            flash("Party is full or pokemon is soul-linked to another pokemon whose Player party is full")
            return redirect(url_for('main.view_save'))
        else:
            pokemon.position = 'party'
    db.session.commit()
    return redirect(url_for('main.view_save'))


@pokemon.route('/switch/box/<link_id>', methods=['POST'])
@login_required
def switch_box(link_id):
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_save'))
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    ruleset = current_save.ruleset
    current_save_id = current_save.id
    pokemon_to_box = db.session.scalars(db.select(Pokemon).join(Pokemon.player).where(Player.saves==current_save, Pokemon.link_id==link_id))
    for pokemon in pokemon_to_box:
        pokemon.position = 'box'
    for key, value in request.form.items():
        if value.isdigit():
            pokemon_to_party = Pokemon.query.join(Player).join(Save).join(User).filter(
                User.id == id).filter(
                Save.id == current_save_id).filter(
                Pokemon.link_id == value)
            for pokemon in pokemon_to_party:
                if Pokemon.query.filter(Pokemon.player_id == pokemon.player_id, Pokemon.position == "party").count() >= 6:
                    flash("Pokemon in box is linked with another pokemon whose Player party is full")
                    return redirect(url_for('main.view_save'))
                else:
                    pokemon.position = 'party'
    db.session.commit()
    return redirect(url_for('main.view_save'))


@pokemon.route('/switch/dead/<link_id>', methods=['POST'])
@login_required
def switch_dead(link_id):
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_save'))
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    ruleset = current_save.ruleset
    current_save_id = current_save.id
    pokemon_to_grave = db.session.scalars(db.select(Pokemon).join(Pokemon.player).where(Pokemon.link_id==link_id, Player.saves==current_save))
    for pokemon in pokemon_to_grave:
        pokemon.position = 'dead'
    db.session.commit()
    return redirect(url_for('main.view_save'))


@pokemon.route('/switch/revive/<link_id>', methods=['POST'])
@login_required
def switch_revive(link_id):
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_save'))
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    pokemon_to_box = db.session.scalars(db.select(Pokemon).join(Pokemon.player).where(Pokemon.link_id==link_id, Player.saves==current_save))
    for pokemon in pokemon_to_box:
        pokemon.position = 'box'
    db.session.commit()
    return redirect(url_for('main.view_save'))


# BUG TESTING REQUIRED
@pokemon.route('/link/<link_id_1>', methods=['POST'])
@login_required
def link_pokemon(link_id_1):
    current_save, current_save_id, ruleset = get_default_vars(current_user.id)
    if ruleset != MANUAL_RULESET:
        flash("Cannot perform manual link for current ruleset!")
        return redirect(url_for('main.view_save'))
    for key, value in request.form.items():
        if key != 'csrf_token':
            print(key, value)
            link_id_2 = int(value)
    pokemon_1 = Pokemon.query.join(
        Save.players).join(
        Player.pokemon).filter(
            Pokemon.link_id == int(link_id_1),
        Save.id == current_save_id)
    pokemon_2 = Pokemon.query.join(
        Save.players).join(
        Player.pokemon).filter(
            Pokemon.link_id == link_id_2,
        Save.id == current_save_id)
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
        return redirect(url_for('main.view_save'))


@pokemon.route('/unlink/<player_num>/<link_id>', methods=['GET', 'POST'])
@login_required
def unlink_pokemon(player_num, link_id):
    current_save, current_save_id, ruleset = get_default_vars(current_user.id)
    # pokemon_to_unlink = Pokemon.query.join(Save.players).join(Player.pokemon).filter(Pokemon.link_id==link_id, Save.id==current_save_id, Player.number==player_num)
    pokemon_linked = Pokemon.query.join(
        Save.players).join(
        Player.pokemon).filter(
            Pokemon.link_id == link_id,
        Save.id == current_save_id)
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
        pokemon_to_unlink.link_id = get_new_link_id(current_save_id)
        pokemon_to_unlink.linked = False
        db.session.commit()
        extra_unlink = Pokemon.query.join(Save.players).join(Player.pokemon).filter(Pokemon.link_id == link_id, Save.id == current_save_id)
        if len(extra_unlink.all()) == 1:
            extra_unlink.first().linked = False
            db.session.commit()
    if current_user.id == 1:
        return redirect(url_for('admin.admin_pokemon'))
    else:
        return redirect(url_for('main.view_save'))


@pokemon.route('/swapfusion/<player_num>/<link_id>', methods=['GET', 'POST'])
@login_required
def swap_fusion(player_num, link_id):
    current_save, current_save_id, ruleset = get_default_vars(current_user.id)
    fusion_to_swap = Pokemon.query.join(Save.players).join(Player.pokemon).filter(Pokemon.link_id == link_id, Save.id == current_save_id, Player.number == player_num).first()
    if fusion_to_swap.info.base_id_2 is not None:
        fusion_to_swap.pokedex_number = fusion_to_swap.info.base_id_2 + '.' + fusion_to_swap.info.base_id_1
        fusion_to_swap.sprite = fusion_to_swap.pokedex_number
        print(fusion_to_swap.pokedex_number)
        db.session.commit()
    else:
        flash(f"ERROR: Pokemon is not a fused pokemon and cannot swap")

    return redirect(url_for('main.view_save'))

    