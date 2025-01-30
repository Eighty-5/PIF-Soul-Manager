from ...extensions import db
from flask import flash, request, redirect, url_for
from ...models import Player, Pokedex, Pokemon, Save, SoulLink


def flash_success_switch(pokemon_switched):
    if not pokemon_switched:
        return False
    if pokemon_switched.soul_linked:
        flash(
            f"{', '.join([pokemon.pokedex_info.species for pokemon in pokemon_switched.soul_linked.linked_pokemon])}"
            f" switched position to {pokemon_switched.position.title()}"
        )
    else:
        flash(f"{pokemon_switched.pokedex_info.species} switched position to {pokemon_switched.position.title()}")


def pokemon_verification(pokemon_id, save_file):
    pokemon_to_check = db.session.get(Pokemon, pokemon_id)
    if not pokemon_to_check or pokemon_to_check.player_info.save_info != save_file:
        return False
    else:
        return pokemon_to_check

# def pokemon_verification(pokemon_ids_to_verify, save_file):
#     for pokemon in pokemon_ids_to_verify:
#         pokemon_to_verify = db.session.get(Pokemon, pokemon)
#         if not pokemon_to_verify or pokemon_to_verify.player_info.save_info != save_file:
#             return False
#         else:
#             pokemon = pokemon_to_verify
#     return pokemon_ids_to_verify


def pokemon_check(pokemon_to_check, save_file):
    if not pokemon_to_check.player_info.save_info == save_file:
        flash("Not a valid pokemon")
        return False


def add_pokemon_per_ruleset_group(ruleset_group, player_num, species, linkage, route, current_save):

    if ruleset == 2:
        linkage = SoulLink(soul_link_number=get_new_link_number(current_save))
    print(current_save)
    player = db.session.scalar(db.select(Player).where(Player.save_info==current_save, Player.player_number==player_num))
    print(player)
    if ruleset_group == 'manual':
        linked = False
    elif ruleset_group == 'auto':
        linked = True
    elif ruleset_group == 'route':
        linked, link_id = False, get_new_link_id(current_save.id)
    else:
        return 'ERROR'
    pokedex_entry = db.session.scalar(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head_pokemon==None))
    print(pokedex_entry)
    pokemon_to_add = Pokemon(player_info=player,
                             pokedex_info=pokedex_entry,
                             route_caught=route,
                             soul_linked=linkage,
                             position='box')
    pokemon_to_add.set_default_sprite()
    db.session.add(pokemon_to_add)


def create_fusion_pokemon(linkage, head_pokemon, body_pokemon, current_save):
    fused_pokedex_info = db.session.scalar(db.select(Pokedex).where(Pokedex.head_pokemon==head_pokemon.pokedex_info, Pokedex.body_pokemon==body_pokemon.pokedex_info))
    pokemon_to_add = Pokemon(
        position = "box",
        player_info = head_pokemon.player_info,
        pokedex_info = fused_pokedex_info,
        soul_linked = linkage
    )
    pokemon_to_add.set_default_sprite()
    db.session.add(pokemon_to_add)
    db.session.delete(head_pokemon)
    db.session.delete(body_pokemon)


def dex_check(dex_num):
    return db.session.scalar(db.select(Pokedex).where(Pokedex.number==dex_num))


def evolution_check(evolution_number, pokemon_to_evolve):
    if db.session.scalar(db.select(Pokedex).where(Pokedex.number==evolution_number)) in pokemon_to_evolve.evolutions():
        return True
    else:
        return False


def fusion_check(heads, bodys):
    check = [heads[0], bodys[0]]
    for head, body in zip(heads, bodys):
        if not head in check or not body in check:
            return False
    return True


def get_new_link_number(current_save):
    last_soul_link = db.session.scalar(
        db.select(SoulLink).where(SoulLink.save_info==current_save).order_by(SoulLink.soul_link_number.desc())
        )
    if last_soul_link:
        return last_soul_link.soul_link_number
    else:
        return 1
    # last_pokemon = db.session.scalar(
    #     db.select(Pokemon).join(Pokemon.player_info).join(Pokemon.soul_linked).where(
    #         Player.save_info==current_save
    #         )
    #     )
    # if last_pokemon:
    #     return last_pokemon.soul_linked.soul_link_number

def get_new_link_id(current_save):
    last_pokemon = db.session.scalar(db.select(Pokemon).join(Pokemon.player_info).join(Pokemon.soul_linked).where(Player.save_info==current_save).order_by(SoulLink.soul_link_number.desc()))
    if last_pokemon:
        return last_pokemon.soul_linked.soul_link_number + 1
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
    

def get_pokemon(current_save, player_num, link_id):
    return db.session.scalar(db.select(Pokemon).join(Pokemon.player).where(Player.number==player_num, Player.saves==current_save, Pokemon.link_id==link_id))

def get_current_save(current_user):
    return db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))    



    



    

    