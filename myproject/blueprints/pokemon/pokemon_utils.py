from ...extensions import db
from flask import flash, request
from ...models import Player, Pokedex, Pokemon, Save

def add_pokemon_per_ruleset_group(ruleset_group, player, species, link_id, route, current_save):
    if ruleset_group == 'manual':
        linked = False
    elif ruleset_group == 'auto':
        linked = True
    elif ruleset_group == 'route':
        linked, link_id = False, get_new_link_id(current_save.id)
    else:
        return 'ERROR'
    # pokedex_number = PokedexBase.query.filter(PokedexBase.species==species).first().number
    pokedex_entry = db.session.scalar(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None))
    pokemon_to_add = Pokemon(link_id=link_id,
                             linked=linked,
                             route=route,
                             position='box',
                             player=player,
                             info=pokedex_entry)
    db.session.add(pokemon_to_add)


def create_fusion_pokemon(new_link_id, head_link_ids, body_link_ids, current_save):
    for head_link_id, body_link_id, player in zip(head_link_ids, body_link_ids, current_save.players):
        if current_save.ruleset == 1:
            new_link_id == get_new_link_id(current_save.id)
        head_pokemon = db.session.scalar(db.select(Pokemon).where(Pokemon.player==player, Pokemon.link_id==head_link_id))
        body_pokemon = db.session.scalar(db.select(Pokemon).where(Pokemon.player==player, Pokemon.link_id==body_link_id))
        fused_pokemon = db.session.scalar(db.select(Pokedex).where(Pokedex.head==head_pokemon.info, Pokedex.body==body_pokemon.info))
        pokemon_to_add = Pokemon(
            link_id = new_link_id,
            linked=True,
            position='box',
            player=player,
            info=fused_pokemon,
            sprite=fused_pokemon.sprites[0])
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


def get_new_link_id(current_save_id):
    last_pokemon = Pokemon.query.join(Save.players).join(Player.pokemons).filter(Save.id==current_save_id).order_by(Pokemon.link_id.desc()).first()
    if last_pokemon:
        return last_pokemon.link_id + 1
    else:
        return 1


def remove_route_key(dict):
    return {k: dict[k] for k in dict if k != 'route'}

def route_validation(num_of_encounters, current_save):
    try:
        route = request.form['route']
        if not Pokemon.query.join(Save.players).join(Player.pokemon).filter(
                Save.id == current_save.id).filter(Pokemon.route == route).count() < num_of_encounters * len(current_save.players):
            flash("Maximum Pokemon caught for that route. Please choose another")
            return False
    except KeyError:
        flash("No route selected")
        return False
    



    



    

    