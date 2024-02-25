from flask import Blueprint, request, flash, redirect, url_for
from flask_login import login_required, current_user
from ...extensions import db
from ...models import Users, Sessions, Players, Pokemon, Pokedex, PokedexBase
# from ...webforms import 
from ...helpers import dex_check, fusion_check, evolution_check

pokemon = Blueprint('pokemon', __name__, template_folder='templates')

# Add Pokemon to Session route
@pokemon.route('/add', methods=['POST'])
@login_required
def add_pokemon():
    # Set variables
    id = current_user.id
    current_session = Sessions.query.get(Users.query.get_or_404(id).current_session)

    # Get new link_id
    last_pokemon = Pokemon.query.join(Players).join(Sessions).filter(Sessions.id==current_session.id).filter(Players.number==1).order_by(Pokemon.link_id.desc()).first()
    if last_pokemon:
        link_id = last_pokemon.link_id + 1
    else:
        link_id = 1

    # Adds new pokemon
    for key, value in request.form.items():
        # Get Pokedex_Id
        pokedex_number = PokedexBase.query.filter_by(species=value).first().number
        # Query Pokedex for pokemon info
        pokemon_to_add = Pokedex.query.filter_by(number=pokedex_number).first()
        # Get Player ID
        player_id = Players.query.join(Sessions).filter(Sessions.id==current_session.id).filter(Players.number==key).first().id
        # Add pokemon to DB
        pokemon = Pokemon(player_id=player_id, pokedex_number=pokemon_to_add.number, sprite=pokemon_to_add.number, link_id=link_id, position='box')
        db.session.add(pokemon)
        db.session.commit()

    # Returns user to 
    return redirect(url_for('main.view_session'))


# Change Variant Route
@pokemon.route('/variant/<player_num>/<link_id>', methods=['POST'])
@login_required
def change_variant(player_num, link_id):
    id = current_user.id
    current_session = Users.query.get_or_404(id).current_session
    variant = request.form.get("variant_select")
    if variant == 'default':
        variant = ''
    variant_to_change = Pokemon.query.join(Players).join(Sessions).filter(Sessions.id==current_session).filter(Players.number==player_num).filter(Pokemon.link_id==link_id).first()
    variant_to_change.sprite = variant_to_change.pokedex_number + variant
    db.session.commit()
    return redirect(url_for('main.view_session'))


# Fuse Pokemon Route
@pokemon.route('/fuse', methods=['POST'])
@login_required
def fuse_pokemon():
    # Set variables
    id = current_user.id
    current_session = Sessions.query.get(Users.query.get_or_404(id).current_session)
    heads = []
    bodys = []
    for key, value in request.form.items():
        if value != None:
            if 'Head' in key:
                heads.append(value)
            elif 'Body' in key:
                bodys.append(value)

    # Check if all 'head' link_ids are the same (as well as the 'body')
    player_count = len(Sessions.query.get(Users.query.get(id).current_session).players)
    if len(heads) != player_count or len(bodys) != player_count:
        flash("Ensure head and body is selected for each player")
        return redirect(url_for('main.view_session'))
    elif not fusion_check(heads, bodys):
        flash("Heads/bodies do not match")
        return redirect(url_for('main.view_session'))

    # Get new link_id
    last_pokemon = Pokemon.query.join(Players).join(Sessions).filter(Sessions.id==current_session.id).filter(Players.number==1).order_by(Pokemon.link_id.desc()).first()
    if last_pokemon:
        link_id = last_pokemon.link_id + 1
    else:
        link_id = 1

    # Fuse Pokemon
    for head, body, player in zip(heads, bodys, Players.query.filter_by(session_id=Sessions.query.get(Users.query.get(id).current_session).id)):
        # Get Head pokemon pokedex id for player
        head_pokemon = Pokemon.query.filter_by(link_id=head, player_id=player.id).first()
        # Get Body pokemon pokedex id for player
        body_pokemon = Pokemon.query.filter_by(link_id=body, player_id=player.id).first()
        # Combine both id's to make fused id
        fused_pokemon_id = f"{head_pokemon.info.number}.{body_pokemon.info.number}"
        # Get pokemon info based on fused id
        fused_pokemon = Pokedex.query.filter_by(number=fused_pokemon_id).first()
        # Add new Pokemon to DB
        pokemon_to_add = Pokemon(player_id=player.id, pokedex_number=fused_pokemon.number, sprite=fused_pokemon.number, link_id=link_id, position='box')
        db.session.add(pokemon_to_add)
        db.session.commit()

        # Delete the base pokemon from DB as they are now fused together
        db.session.delete(head_pokemon)
        db.session.commit()
        db.session.delete(body_pokemon)
        db.session.commit()        

    # Return to current session manager
    return redirect(url_for('main.view_session'))


# Delete a pokemon from session route
@pokemon.route('/delete/<int:link_id>', methods=['POST'])
@login_required
def delete_pokemon(link_id):
    id = current_user.id
    current_session = Users.query.get_or_404(id).current_session
    for player in Sessions.query.get(current_session).players:
        for pokemon_to_delete in Pokemon.query.filter(Pokemon.link_id==link_id, Pokemon.player_id==player.id):
            db.session.delete(pokemon_to_delete)
            db.session.commit()
    # pokemon_to_delete = Pokemon.query.join(Players).join(Sessions).filter(Sessions.id==current_session).filter(Pokemon.link_id==link_id)
    # print(pokemon_to_delete)
    # db.session.delete(pokemon_to_delete)
    # db.session.commit()
    if id == 1:
        return redirect(url_for('admin.pokemon'))
    else:
        return redirect(url_for('main.view_session'))


@pokemon.route('/evolve/<int:player_num>/<int:link_id>', methods=['GET', 'POST'])
@login_required
def evolve_pokemon(player_num, link_id):
    id = current_user.id
    current_session = Users.query.get_or_404(id).current_session
    # Check if evolution is a valid evolution
    evolution = request.form.get(f"evolve_{str(player_num)}_{str(link_id)}")
    pokemon_to_evolve = Pokemon.query.join(Players).join(Sessions).filter(Sessions.id==current_session).filter(Players.number==player_num).filter(Pokemon.link_id==link_id).first()
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
    # Serverside check ensuring link_id is a digit
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_session'))
    id = current_user.id
    current_session = Users.query.get_or_404(id).current_session
    # Send requested pokemon souls to box
    for key, value in request.form.items():
        # Serverside check that targeted party pokemon link_id was not changed to a non digit
        # Changed to a digit that is not a valid link_id is okay as query will come up none anyway
        if value.isdigit():
            # If serverside check is true, query db for pokemon and add to box
            pokemon_to_box = Pokemon.query.join(Players).join(Sessions).join(Users).filter(Users.id==id).filter(Sessions.id==current_session).filter(Pokemon.link_id==value)
            for pokemon in pokemon_to_box:
                pokemon.position = 'box'
                db.session.commit()
    # Serverside check if party is not full 
    if Pokemon.query.join(Players).join(Sessions).filter(Sessions.user_id==id).filter(Sessions.id==current_session).filter(Players.number==1).filter(Pokemon.position=='party').count() < 6:
        pokemon_to_party = Pokemon.query.join(Players).join(Sessions).join(Users).filter(Users.id==id).filter(Sessions.id==current_session).filter(Pokemon.link_id==link_id)
        # Add pokemon to box
        for pokemon in pokemon_to_party:
            pokemon.position = 'party'
            db.session.commit()
    else:
        flash("Party is Full")
    
    return redirect(url_for('main.view_session'))


@pokemon.route('/switch/box/<link_id>', methods=['POST'])
@login_required
def switch_box(link_id):
    # Serverside check ensuring link_id is a digit
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_session'))
    id = current_user.id
    current_session = Users.query.get_or_404(id).current_session
    # Send requested pokemon souls to box
    pokemon_to_box = Pokemon.query.join(Players).join(Sessions).join(Users).filter(Users.id==id).filter(Sessions.id==current_session).filter(Pokemon.link_id==link_id)
    for pokemon in pokemon_to_box:
        pokemon.position = 'box'
        db.session.commit()
    # Serverside check if party is not full 
    if Pokemon.query.join(Players).join(Sessions).filter(Sessions.user_id==id).filter(Sessions.id==current_session).filter(Players.number==1).filter(Pokemon.position=='party').count() < 6:
        for key, value in request.form.items():
            # Serverside check that targeted party pokemon link_id was not changed to a non digit
            # Changed to a digit that is not a valid link_id is okay as query will come up none anyway
            if value.isdigit():
                # If serverside check is true, query db for pokemon and add to box
                pokemon_to_party = Pokemon.query.join(Players).join(Sessions).join(Users).filter(Users.id==id).filter(Sessions.id==current_session).filter(Pokemon.link_id==value)
                for pokemon in pokemon_to_party:
                    pokemon.position = 'party'
                    db.session.commit()
    else:
        flash("Party is Full")
    
    return redirect(url_for('main.view_session'))


@pokemon.route('/switch/dead/<link_id>', methods=['POST'])
@login_required
def switch_dead(link_id):
    # Serverside check ensuring link_id is a digit
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_session'))
    id = current_user.id
    current_session = Users.query.get_or_404(id).current_session
    # Send requested pokemon souls to box
    pokemon_to_dead = Pokemon.query.join(Players).join(Sessions).join(Users).filter(Users.id==id).filter(Sessions.id==current_session).filter(Pokemon.link_id==link_id)
    for pokemon in pokemon_to_dead:
        pokemon.position = 'dead'
        db.session.commit()
    
    return redirect(url_for('main.view_session'))


@pokemon.route('/switch/revive/<link_id>', methods=['POST'])
@login_required
def switch_revive(link_id):
    # Serverside check ensuring link_id is a digit
    if not link_id.isdigit():
        flash("Not a valid Pokemon")
        return redirect(url_for('main.view_session'))
    id = current_user.id
    current_session = Users.query.get_or_404(id).current_session
    # Send requested pokemon souls to box
    pokemon_to_box = Pokemon.query.join(Players).join(Sessions).join(Users).filter(Users.id==id).filter(Sessions.id==current_session).filter(Pokemon.link_id==link_id)
    for pokemon in pokemon_to_box:
        pokemon.position = 'box'
        db.session.commit()

    return redirect(url_for('main.view_session'))