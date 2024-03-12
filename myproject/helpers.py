from .extensions import db
from .models import Players, Pokedex, Pokemon

def fusion_check(heads, bodys):
    check = [heads[0], bodys[0]]
    for head, body in zip(heads, bodys):
        if not head in check or not body in check:
            return False
    return True

# def delete_player(player_id):
#     player_to_delete = Players.query.get_or_404(player_id)
#     delete_all_pokemon_by_player(player_to_delete.id)
#     # delete_all_pokemon_by_player(player_to_delete.id)
#     db.session.delete(player_to_delete)
#     db.session.commit()

def dex_check(dex_num):
    if not Pokedex.query.filter(Pokedex.number==dex_num).first():
        return False
    return True

def evolution_check(evolution_id, base_id):
    # Check if entered pokemon is part of same family
    if Pokedex.query.filter(Pokedex.number==evolution_id).first().family == Pokedex.query.filter(Pokedex.number==base_id).first().family:
        return True
    else:
        return False
    
# def delete_all_pokemon_by_player(player_id):
#     pokemon_to_delete = Pokemon.query.filter_by(player_id=player_id)
#     db.session.delete(pokemon_to_delete)
#     db.session.commit()

# Find first missing session number
# https://www.geeksforgeeks.org/python-find-missing-numbers-in-a-sorted-list-range/
def find_first_missing(lst):
    try:
        return sorted(set(range(1, 4)) - set(lst))[0]
    except IndexError:
        return False