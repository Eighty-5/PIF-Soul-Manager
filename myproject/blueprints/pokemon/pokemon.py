from collections import Counter
from ...extensions import db
from flask import Blueprint, request, flash, redirect, url_for
from flask_login import login_required, current_user
from ...models import User, Save, Player, Pokemon, Pokedex, Sprite, Route, RouteList, SoulLink
from .pokemon_utils import (
    create_fusion_pokemon, 
    get_new_link_id, get_pokemon, get_current_save, get_new_link_number, 
    pokemon_check, pokemon_verification
)    
from sqlalchemy import or_, func
# from ...utils import get_default_vars

import random

pokemon = Blueprint('pokemon', __name__, template_folder='templates')

MANUAL_RULESET = 1
AUTO_RULESET = [2, 3]
ROUTE_RULESET = 4
SPECIAL_RULESET = 5
ONE_ROUTE_RULESET = [2]
TWO_ROUTE_RULESET = [3, 4, 5]
# Add Pokemon to Save route

@pokemon.route('/add', methods=['POST'])
@login_required
def add_pokemon():

    def add_pokemon_per_ruleset_group(pokemon_to_add={}, linkage=None, route=None):
        added_pokemon_lst = []
        for player_number in pokemon_to_add:
            species = pokemon_to_add[player_number]['species']
            pokedex_info = db.session.scalar(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head_pokemon==None))
            if pokedex_info:
                new_pokemon = Pokemon(
                    position="box",
                    player_info=pokemon_to_add[player_number]['player'],
                    pokedex_info=pokedex_info,
                    soul_linked=linkage,
                    route_caught=route
                )
            else:
                flash(f"{species} does not exist in the current Pokedex")
                return False
            added_pokemon_lst.append(species)
            db.session.add(new_pokemon)
        flash(f"{', '.join(added_pokemon_lst)} were added to the save!")
        db.session.commit()
        return True


    current_save = current_user.current_save()
    pokemon_to_add = {player.player_number:{'player':player,'species':None} for player in current_save.players}
    ruleset = current_save.ruleset

    # Serverside Checks
    if ruleset != MANUAL_RULESET:
        try:
            route_id = request.form['route']
            max_num = 1 if ruleset == 2 else 2
            # UPDATE LATER TO INCLUDE CUSTOM ROUTES FROM USER INPUT
            new_route_info = db.session.get(RouteList, route_id)
            if not new_route_info:
                flash("Please select a route from the dropdown")
                return redirect(url_for('main.view_save'))
            route_check = db.session.scalar(db.select(Route).where(Route.save_info==current_save, Route.route_info==new_route_info))
            if not route_check:
                if ruleset == 2:
                    route = Route(save_info=current_save, route_info=new_route_info, complete=True)
                else:
                    route = Route(save_info=current_save, route_info=new_route_info, complete=False)
            elif route_check.complete == True:
                flash("Maximum Pokemon caught for that route. Please choose another")
                return redirect(url_for('main.view_save'))
            else:
                route = route_check
                route.complete = True

        except KeyError:
            flash("No route selected")
            return redirect(url_for('main.view_save'))
        db.session.add(route)
    
    pokemon_to_add_dict = {}

    for player_number, species in request.form.items():
        if player_number != 'route' and player_number != 'csrf_token':
            pokemon_to_add[int(player_number)]['species'] = species

    if ruleset == MANUAL_RULESET:
        add_pokemon_per_ruleset_group(pokemon_to_add=pokemon_to_add)
    elif ruleset in AUTO_RULESET:
        linkage = current_save.create_soul_link()
        add_pokemon_per_ruleset_group(pokemon_to_add=pokemon_to_add, linkage=linkage, route=route)
    elif ruleset in [ROUTE_RULESET, SPECIAL_RULESET]:
        add_pokemon_per_ruleset_group(pokemon_to_add=pokemon_to_add, route=route)
    else:
        flash("""NOT VIABLE RULESET: PLEASE USE DESIGNATED 
              RULESET OR RECREATE SAVE WITH FULL FREEDOM RULESET""")
    return redirect(url_for('main.view_save'))


# FOR TESTING ONLY 
# Optimize if time allots
@pokemon.route('/add/random', methods=['POST'])
@login_required
def add_random():

    def route_per_ruleset(rand_route):
        if ruleset in ONE_ROUTE_RULESET:
            complete = True
        else:
            complete = False
        route = Route(route_info=rand_route, save_info=current_save, complete=complete)

    current_save = current_user.current_save()
    ruleset = current_save.ruleset
    
    if ruleset != MANUAL_RULESET:
        complete_routes = []
        incomplete_routes = []
        if len(current_save.recorded_routes) > 0:
            routes_dict = {route.route_info.name:route for route in current_save.recorded_routes}
            while True:
                rand_route = db.session.scalar(db.select(RouteList).order_by(func.random()).limit(1))
                print(rand_route)
                if rand_route.name in routes_dict:
                    if ruleset in TWO_ROUTE_RULESET and routes_dict[rand_route.name].complete != True:
                        route = routes_dict[rand_route.name]
                        route.complete = True
                        if ruleset in ONE_ROUTE_RULESET:
                            complete = True
                        else:
                            complete = False
                        route = Route(route_info=rand_route, save_info=current_save, complete=complete)
                        break
                    else:
                        pass
                else:
                    if ruleset in ONE_ROUTE_RULESET:
                        complete = True
                    else:
                        complete = False
                    route = Route(route_info=rand_route, save_info=current_save, complete=complete)
                    break
        else:
            rand_route = db.session.scalar(db.select(RouteList).order_by(func.random()).limit(1))
            if ruleset in ONE_ROUTE_RULESET:
                complete = True
            else:
                complete = False
            route = Route(route_info=rand_route, save_info=current_save, complete=complete)
    else:
        route = None

    if ruleset in AUTO_RULESET:
        linkage = current_save.create_soul_link()
    else:
        linkage = None

    added_pokemon_lst = []
    for player in current_save.players:
        rand_pokedex_number = random.randrange(
            1, db.session.scalar(db.select(func.count("*")).select_from(Pokedex).where(Pokedex.head_id==None))
            )
        new_pokemon_info = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==rand_pokedex_number))
        pokemon_to_add = Pokemon(player_info=player, pokedex_info=new_pokemon_info, route_caught=route, soul_linked=linkage, position="box")
        pokemon_to_add.set_default_sprite()
        db.session.add(pokemon_to_add)
        added_pokemon_lst.append(pokemon_to_add.pokedex_info.species)
    db.session.commit()
    flash(f"{', '.join(added_pokemon_lst)} were added to the save! ")
    return redirect(url_for('main.view_save'))


# Change Variant Route
@pokemon.route('/variant/<int:id>', methods=['POST'])
@login_required
def change_variant(id):
    current_save = current_user.current_save()
    variant_id = request.form.get("variant_select")
    if variant_id == 'default':
        variant = ''
    elif variant is None:
        flash("Please select a variant sprite to switch to")
        return redirect(url_for('main.view_save'))
    variant_to_change = db.session.scalar(
        db.select(Pokemon).join(Pokemon.player_info).where(
            Player.number==player_num, Player.save_info==current_save, Pokemon.soul_linked.soul_link_number==link_id
        )
    )
    new_variant = db.session.scalar(
        db.select(Sprite).join(Sprite.info).where(
            Pokedex.number==variant_to_change.info.number, Sprite.variant_let==variant
        )
    )
    if new_variant:
        variant_to_change.sprite = new_variant
        db.session.commit()
    else:
        flash("Please select a valid variant letter")
    return redirect(url_for('main.view_save'))


# Fuse Pokemon Route
# Clean up later
@pokemon.route('/fuse', methods=['POST'])
@login_required
def fuse_pokemon():
    current_save = current_user.current_save()
    ruleset = current_save.ruleset
    head_ids, body_ids = [], []
    
    for key, value in request.form.items():
        if value is not None and not key == 'csrf_token':
            if 'Head' in key:
                head_ids.append(value)
            elif 'Body' in key:
                body_ids.append(value)
            else:
                flash("Error")
                return redirect(url_for('main.view_save'))

    player_count = current_save.player_count()
    if len(head_ids) != player_count or len(body_ids) != player_count:
        flash("Ensure head and body is selected for each player")
        return redirect(url_for('main.view_save'))
    elif any(count > player_count for count in Counter(head_ids + body_ids).values()):
        flash("Fusion Failed: A Pokemon was used multiple times in one fusion")
        return redirect(url_for('main.view_save'))
    
    # Checks that all link numbers are legit
    head_pokemons, body_pokemons = [], []
    for head_id in head_ids:
        head_pokemon = pokemon_verification(head_id, current_save)
        if not head_pokemon:
            flash("Error: One or more provided pokemon do not match records")
            return redirect(url_for('main.view_save')) 
        elif head_pokemon.pokedex_info.head_pokemon:
            flash("Error: One or more provided pokemon are already fused")
            return redirect(url_for('main.view_save'))
        else:
            head_pokemons.append(head_pokemon)
    for body_id in body_ids:
        body_pokemon = pokemon_verification(body_id, current_save)
        if not body_pokemon:
            flash("Error: One or more provided pokemon do not match records")
            return redirect(url_for('main.view_save'))
        elif body_pokemon.pokedex_info.body_pokemon:
            flash("Error: One or more provided pokemon are already fused")
            return redirect(url_for('main.view_save'))
        else:
            body_pokemons.append(body_pokemon)

    linkage = SoulLink(save_info=current_save, soul_link_number=get_new_link_number(current_save))
    
    if ruleset in AUTO_RULESET:
        link_1, link_2 = False, False
        for head_pokemon, body_pokemon in zip(head_pokemons, body_pokemons):
            if not link_1 or not link_2:
                link_1, link_2 = head_pokemon.soul_linked, body_pokemon.soul_linked
            if head_pokemon.soul_linked in [link_1, link_2] and body_pokemon.soul_linked in [link_1, link_2]:
                create_fusion_pokemon(linkage, head_pokemon, body_pokemon, current_save)
            else:
                flash(f"Error: Ruleset {current_save.ruleset} requires all pokemon between each player to be linked to one another")
                return redirect(url_for('main.view_save'))
        db.session.delete(link_1)
        db.session.delete(link_2)
        db.session.commit()
        flash(f"Fusion Completed Successfully!")
    elif ruleset == ROUTE_RULESET:
        for head_pokemon, body_pokemon in zip(head_pokemons, body_pokemons):
            if head_pokemon.__eq__(body_pokemon, 'route_id'):
                create_fusion_pokemon(linkage, head_pokemon, body_pokemon, current_save)
            else:
                flash(f"Error: Ruleset {current_save.ruleset} requires {head_pokemon.pokedex_info.species} and {body_pokemon.pokedex_info.species} to be of the same route")
                return redirect(url_for('main.view_save'))
        db.session.commit()
        flash(f"Fusion Completed Successfully!")
    elif ruleset == SPECIAL_RULESET:
        route_1, route_2 = False, False
        for head_pokemon, body_pokemon in zip(head_pokemons, body_pokemons):
            if not route_1 or not route_2:
                route_1, route_2 = head_pokemon.route_caught, body_pokemon.route_caught
            if head_pokemon.route_caught in [route_1, route_2] and body_pokemon.route_caught in [route_1, route_2]:
                create_fusion_pokemon(linkage, head_pokemon, body_pokemon, current_save)
            else:
                flash(f"Error: Ruleset {current_save.ruleset} requires route combo of both head and body pokemon for each player to be of the same route")
                return redirect(url_for('main.view_save'))
        db.session.commit()
        flash(f"Fusion Completed Successfully!")
    elif ruleset == MANUAL_RULESET:
        for head_pokemon, body_pokemon in zip(head_pokemons, body_pokemons):
            create_fusion_pokemon(linkage, head_pokemon, body_pokemon, current_save)
        db.session.commit()
        flash(f"Fusion Completed Successfully!")
    else:
        flash("Ruleset does not exist")
    return redirect(url_for('main.view_save'))


# Delete a pokemon from save route
@pokemon.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_pokemon(id):
    current_save = current_user.current_save()
    pokemon_to_delete = pokemon_verification(id, current_save)
    if not pokemon_to_delete:
        flash(f"ERROR: Deletion Failed - Please select a valid pokemon")
    if pokemon_to_delete.soul_linked:
        flash(f"{', '.join([pokemon.pokedex_info.species for pokemon in pokemon_to_delete.soul_linked.linked_pokemon])} deleted from save")
        # for pokemon in pokemon_to_delete.soul_linked.linked_pokemon:
        #     db.session.delete(pokemon)
        db.session.delete(pokemon_to_delete.soul_linked)
    else:
        db.session.delete(pokemon_to_delete)
        flash(f"{pokemon_to_delete.pokedex_info.species} deleted from save")
    db.session.commit()
    return redirect(url_for('main.view_save'))
    

# Delete pokemon and open route
@pokemon.route('/delete/open_route/<int:id>', methods=['POST'])
@login_required
def delete_pokemon_open(id):
    current_save = current_user.current_save()
    pokemon_to_delete = pokemon_verification(id, current_save)
    pokemon_to_delete.route_caught.complete = False
    if not pokemon_to_delete:
        flash(f"ERROR: Deletion Failed - Please select a valid pokemon")
    if pokemon_to_delete.soul_linked:
        flash(f"{', '.join([pokemon.pokedex_info.species for pokemon in pokemon_to_delete.soul_linked.linked_pokemon])} deleted from save")
        # for pokemon in pokemon_to_delete.soul_linked.linked_pokemon:
        #     db.session.delete(pokemon)
        db.session.delete(pokemon_to_delete.soul_linked)
    else:
        db.session.delete(pokemon_to_delete)
        flash(f"{pokemon_to_delete.pokedex_info.species} deleted from save")
    db.session.commit()
    return redirect(url_for('main.view_save'))

# Delete pokemon and keep route closed


@pokemon.route('/evolve/<int:id>', methods=['POST'])
@login_required
def evolve_pokemon(id):
    current_save = current_user.current_save()
    evolution_number = request.form["evolve"]
    pokemon_to_evolve = pokemon_verification(id, current_save)
    if not pokemon_to_evolve:
        flash("Error: Please select a valid Pokemon")
        return redirect(url_for('main.view_save')) 
    prevolution = pokemon_to_evolve.pokedex_info
    evolution = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==evolution_number))
    if prevolution and evolution in pokemon_to_evolve.pokedex_info.evolutions():
        pokemon_to_evolve.pokedex_info = evolution
        pokemon_to_evolve.set_default_sprite()
        db.session.commit()
        flash(f"{prevolution.species} evolved into {evolution.species}")
    else:
        flash("Not a valid evolution")
    return redirect(url_for('main.view_save'))


@pokemon.route('/switch/party/<int:id>', methods=['POST'])
@login_required
def switch_party(id):
    current_save = current_user.current_save()
    pokemon_to_party = pokemon_verification(id, current_save)
    if not pokemon_to_party:
        flash(f"ERROR: Add to Party Failed - Please select a valid pokemon")
        return redirect(url_for('main.view_save'))
    value = request.form['switch_with']
    if value != "addparty":
        pokemon_to_box = pokemon_verification(int(value), current_save)
        if pokemon_to_box:
            pokemon_to_box.switch_position(position="box")
        else:
            flash(f"ERROR: Add to Party Failed - Please select a valid pokemon")
    pokemon_to_party.switch_position(position="party")
    

    return redirect(url_for('main.view_save'))


@pokemon.route('/switch/box/<int:id>', methods=['POST'])
@login_required
def switch_box(id):
    current_save = current_user.current_save()
    pokemon_to_box = pokemon_verification(id, current_save)
    if not pokemon_to_box:
        flash(f"ERROR: Send to Box Failed - Please select a valid pokemon")
        return redirect(url_for('main.view_save'))
    pokemon_to_box.switch_position(position="box")
    value = request.form['switch_with']
    if value != "sendbox":
        pokemon_to_party = pokemon_verification(int(value), current_save)
        if not pokemon_to_party:
            flash(f"ERROR: Send to Box Failed - Please select a valid pokemon")
            return redirect(url_for('main.view_save'))
        pokemon_to_party.switch_position(position="party")
    return redirect(url_for('main.view_save'))


@pokemon.route('/switch/dead/<int:id>', methods=['POST'])
@login_required
def switch_dead(id):
    current_save = current_user.current_save()
    pokemon_to_graveyard = pokemon_verification(id, current_save)
    if not pokemon_to_graveyard:
        flash(f"ERROR: Fainting Failed - Please select a valid pokemon")
    pokemon_to_graveyard.switch_position(position="dead")
    return redirect(url_for('main.view_save'))


@pokemon.route('/switch/revive/<int:id>', methods=['POST'])
@login_required
def switch_revive(id):
    current_save = current_user.current_save()
    pokemon_to_box = pokemon_verification(id, current_save)
    if not pokemon_to_box:
        flash(f"ERROR: Revive Failed - Please select a valid pokemon")
    pokemon_to_box.switch_position(position="box")
    return redirect(url_for('main.view_save'))


@pokemon.route('/link/<int:id>', methods=['POST'])
@login_required
def link_pokemon(id):
    current_save = current_user.current_save()
    if current_save.ruleset != MANUAL_RULESET:
        flash("Cannot perform manual link for current ruleset!")
        return redirect(url_for('main.view_save'))

    pokemon_1 = pokemon_verification(id, current_save)
    link_to_id = request.form['link_with']
    pokemon_2 = pokemon_verification(link_to_id, current_save)
    
    if not pokemon_1 or not pokemon_2:
        flash("Selected Pokemon does not exist for this save")
    elif pokemon_1.soul_linked:
        flash("This pokemon is already linked with another, please delink this pokemon first if you wish to link to another")
    elif pokemon_2.soul_linked:
        if pokemon_1.player_info in pokemon_2.soul_linked.linked_players():
            flash(f"Other pokemon is already linked to another one of {pokemon_1.player_info.player_name}'s pokemon")
            return redirect(url_for('main.view_save'))
        pre_link_lst = [pokemon.pokedex_info.species for pokemon in pokemon_2.soul_linked.linked_pokemon] 
        pokemon_1.soul_linked = pokemon_2.soul_linked
        db.session.commit()
        flash(f"Manual Link Successful - {pokemon_1.pokedex_info.species} successfully linked to {', '.join([species for species in pre_link_lst])}!")
    else:
        new_soul_link = current_save.create_soul_link()
        pokemon_1.soul_linked = new_soul_link
        pokemon_2.soul_linked = new_soul_link
        db.session.commit()
        flash(f"Manual Link Successful - {pokemon_1.pokedex_info.species} successfully linked to {pokemon_2.pokedex_info.species}")
    return redirect(url_for('main.view_save'))


# Clean up if statements later
@pokemon.route('/unlink/<int:id>', methods=['GET', 'POST'])
@login_required
def unlink_pokemon(id):
    current_save = current_user.current_save()
    pokemon_to_unlink = pokemon_verification(id, current_save)
    if not pokemon_to_unlink:
        flash(f"ERROR: Unlink Failed - Please select a valid pokemon")
    elif not pokemon_to_unlink.soul_linked:
        flash(f"Error: {pokemon_to_unlink.pokedex_info.species} is not currently soul linked to another pokemon")
    else:
        soul_link = pokemon_to_unlink.soul_linked

        print("1", soul_link.linked_pokemon)
        if len(soul_link.linked_pokemon) <= 2:
            while len(soul_link.linked_pokemon) > 0:
                soul_link.linked_pokemon[0].soul_linked = None
            db.session.delete(soul_link)
        else:
            pokemon_to_unlink.soul_linked = None
        flash(f"Manual Link Successful - {pokemon_to_unlink.pokedex_info.species} successfully unlinked!")
        db.session.commit()
    return redirect(url_for('main.view_save'))


@pokemon.route('/swapfusion/<int:id>', methods=['GET', 'POST'])
@login_required
def swap_fusion(id):
    current_save = current_user.current_save()
    fusion_to_swap = pokemon_verification(id, current_save)
    if not fusion_to_swap:
        flash(f"ERROR: Fusion Swap Failed - Please select a valid pokemon")
    elif not fusion_to_swap.pokedex_info.head_pokemon:
        flash(f"ERROR: Pokemon is not a fused pokemon and therefore cannot swap fusions")
    else:
        pre_swap_name = fusion_to_swap.pokedex_info.species
        swapped_fusion_info = db.session.scalar(
            db.select(Pokedex).where(
                Pokedex.head_pokemon==fusion_to_swap.pokedex_info.body_pokemon, 
                Pokedex.body_pokemon==fusion_to_swap.pokedex_info.head_pokemon
                )
            )
        fusion_to_swap.pokedex_info = swapped_fusion_info
        fusion_to_swap.set_default_sprite()
        db.session.commit()
        flash(f"{pre_swap_name} fusion successfully swapped to {fusion_to_swap.pokedex_info.species}")
    return redirect(url_for('main.view_save'))


    # current_save = db.session.scalar(db.select(Save).where(Save.user_info==current_user, Save.current_status==True))
    # fusion_to_swap = db.session.scalar(db.select(Pokemon).join(Pokemon.player_info).where(Player.number==player_num, Player.save_info==current_save, Pokemon.soul_linked.soul_link_number==link_id))
    # if not fusion_to_swap.info.head is None:
    #     swapped_fusion = db.session.scalar(db.select(Pokedex).where(Pokedex.head==fusion_to_swap.info.body, Pokedex.body==fusion_to_swap.info.head))
    #     fusion_to_swap.info = swapped_fusion
    #     fusion_to_swap.set_default_sprite()
    #     db.session.commit()
    # else:
    #     flash(f"ERROR: Pokemon is not a fused pokemon  and cannot swap")

    # return redirect(url_for('main.view_save'))


@pokemon.route('/update_nickname/<int:id>', methods=['POST'])
@login_required
def update_nickname(id):
    print(request.form.get("change_nickname"))
    return redirect(url_for('main.view_save')) 