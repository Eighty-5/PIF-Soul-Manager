from ...extensions import db
from flask import flash, request
from ...models import Players, PokedexBase, Pokedex, Pokemon, Sessions

def add_pokemon_per_ruleset_group(ruleset_group, player_number, species, link_id, route, current_session_id):
    if ruleset_group == 'manual':
        linked = False
    elif ruleset_group == 'auto':
        linked = True
    elif ruleset_group == 'route':
        linked, link_id = False, get_new_link_id(current_session_id)
    else:
        return 'ERROR'
    pokedex_number = PokedexBase.query.filter(PokedexBase.species==species).first().number
    player_id = Players.query.join(Sessions).filter(Sessions.id==current_session_id, Players.number==player_number).first().id
    pokemon = Pokemon(player_id=player_id, pokedex_number=pokedex_number, sprite=pokedex_number, link_id=link_id, linked=linked, route=route, position='box')
    db.session.add(pokemon)


def create_fusion_pokemon(new_link_id, head_link_ids, body_link_ids, ruleset, current_session_id):
    for head, body, player in zip(head_link_ids, body_link_ids, Players.query.filter(
            Players.session_id==current_session_id)):
        if ruleset == 1:
            new_link_id == get_new_link_id(current_session_id)
        head_pokemon, body_pokemon = Pokemon.query.filter_by(
            link_id=head, player_id=player.id).first(), Pokemon.query.filter_by(
            link_id=body, player_id=player.id).first()
        fused_pokemon_id = f"{ 
            head_pokemon.info.number}.{
            body_pokemon.info.number}"
        fused_pokemon = Pokedex.query.filter_by(
            number=fused_pokemon_id).first()
        pokemon_to_add = Pokemon(
            player_id=player.id,
            pokedex_number=fused_pokemon.number,
            sprite=fused_pokemon.number,
            link_id=new_link_id,
            linked=True,
            route=None,
            position='box')
        db.session.add(pokemon_to_add)
        db.session.delete(head_pokemon)
        db.session.delete(body_pokemon)
    flash("Pokemon fused successfully")
    db.session.commit()


def dex_check(dex_num):
    if not Pokedex.query.filter(Pokedex.number==dex_num).first():
        return False
    return True


def evolution_check(evolution_id, base_id):
    if Pokedex.query.filter(Pokedex.number==evolution_id).first().family == Pokedex.query.filter(Pokedex.number==base_id).first().family:
        return True
    else:
        return False


def fusion_check(heads, bodys):
    check = [heads[0], bodys[0]]
    for head, body in zip(heads, bodys):
        if not head in check or not body in check:
            return False
    return True


def get_new_link_id(current_session_id):
    last_pokemon = Pokemon.query.join(Sessions.players).join(Players.pokemon).filter(Sessions.id==current_session_id).order_by(Pokemon.link_id.desc()).first()
    if last_pokemon:
        return last_pokemon.link_id + 1
    else:
        return 1


def remove_route_key(dict):
    return {k: dict[k] for k in dict if k != 'route'}

def route_validation(num_of_encounters, current_session):
    try:
        route = request.form['route']
        if not Pokemon.query.join(Sessions.players).join(Players.pokemon).filter(
                Sessions.id == current_session.id).filter(Pokemon.route == route).count() < num_of_encounters * len(current_session.players):
            flash("Maximum Pokemon caught for that route. Please choose another")
            return False
    except KeyError:
        flash("No route selected")
        return False
    



    



    

    