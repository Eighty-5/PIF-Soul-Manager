from myproject.models import Pokedex, Pokemon
from myproject.extensions import db
from sqlalchemy import or_

def create_fusion_typing(pokemon_1, pokemon_2):
    # If pokemon is a Normal/Flying primary typing needs to be Flying
    if pokemon_1["type_primary"] == 'Normal' and pokemon_1["type_secondary"] == 'Flying':
        head_type = pokemon_1["type_secondary"]
    else:
        head_type = pokemon_1["type_primary"]
    # As of version 6.0 of Infinite Fusion some pokemon no longer has a dominant typing
    # if pokemon_2['number'] in FUSION_EXCEPTIONS:
    #     body_type = pokemon_2["type_primary"]
    # If body Pokemon only has one type, the secondary typing of the new fused pokemon uses the primary typing of the body Pokemon
    if pokemon_2["type_secondary"] == "":
        body_type = pokemon_2["type_primary"]
    # If the body Pokemon's secondary type is the same as the head Pokemon's primary type, the body Pokemon's primary type is instead used for the fused Pokemon's secondary type
    elif pokemon_2["type_secondary"] == head_type:
        body_type = pokemon_2["type_primary"]
    # If none of the above apply then the fused Pokemon's secondary type is the body Pokemon's secondary type. 
    else:
        body_type = pokemon_2["type_secondary"]
    # If the newly fused Pokemon has two typings that are the same, the secondary typing is removed
    if body_type == head_type:
        body_type = ""

    return head_type, body_type

def create_fusion_name(name_1, name_2):
    if name_1[-1] == name_2[0]:
        species = name_1 + name_2[1:]
    else:
        species = name_1 + name_2
    return species

def create_fusion_stats(pokemon_1, pokemon_2):
    fused_stats = {}
    fused_stats['hp'] = int(2 * pokemon_1['hp']/3 + pokemon_2['hp']/3)
    fused_stats['attack'] = int(2 * pokemon_2['attack']/3 + pokemon_1['attack']/3)
    fused_stats['defense'] = int(2 * pokemon_2['defense']/3 + pokemon_1['defense']/3)
    fused_stats['sp_attack'] = int(2 * pokemon_1['sp_attack']/3 + pokemon_2['sp_attack']/3)
    fused_stats['sp_defense'] = int(2 * pokemon_1['sp_defense']/3 + pokemon_2['sp_defense']/3)
    fused_stats['speed'] = int(2 * pokemon_2['speed']/3 + pokemon_1['speed']/3)
    fused_stats['total'] = int(fused_stats['hp'] + fused_stats['attack'] + fused_stats['defense'] + fused_stats['sp_attack'] + fused_stats['sp_defense'] + fused_stats['speed'])
    return fused_stats

def prep_number(sprite):
    prep_dict = {}
    sprite_split = sprite.split('.')
    if len(sprite_split) == 3:
        return 'TRIPLE'
    elif len(sprite_split) == 1:
        try:
            if sprite_split[0][-1].isalpha():
                if sprite_split[0][-2].isalpha():
                    return 'EXTRA VARIANT'
                prep_dict['base_1'] = sprite_split[0][:-1]
                prep_dict['var'] = sprite_split[0][-1]
            else:
                prep_dict['base_1'] = sprite_split[0]
        except IndexError:
            return 'BLANK'
    elif len(sprite_split) == 2:
        if sprite_split[1][-1].isalpha():
            if sprite_split[1][-2].isalpha():
                return 'EXTRA VARIANT'
            prep_dict['base_1'] = sprite_split[0]
            prep_dict['base_2'] = sprite_split[1][:-1]
            prep_dict['var'] = sprite_split[1][-1]
        else:
            prep_dict['base_1'] = sprite_split[0]
            prep_dict['base_2'] = sprite_split[1]
    else:
        return 'INVALID NUMBER'
    return prep_dict

def create_master_dex(master_pokedex, pokedex):
    for base_id_1, info_1 in pokedex.items():
        master_pokedex[base_id_1] = {}
        master_pokedex[base_id_1]['base'] = {'species': info_1['species'],
                                             'type_primary': info_1['type_primary'],
                                             'type_secondary': None if info_1['type_secondary'] == '' else info_1['type_secondary'],
                                             'family': info_1['family'],
                                             'family_order': info_1['family_order'],
                                             'variants_dict': {'-': 'japeal'},
                                             'hp': info_1['hp'],
                                             'attack': info_1['attack'],
                                             'defense': info_1['defense'],
                                             'sp_attack': info_1['sp_attack'],
                                             'sp_defense': info_1['sp_defense'],
                                             'speed': info_1['speed'],
                                             'total': info_1['total']}
        for base_id_2, info_2 in pokedex.items():
            type_primary, type_secondary = create_fusion_typing(info_1, info_2)
            fused_stats = create_fusion_stats(info_1, info_2)
            master_pokedex[base_id_1][base_id_2] = {}
            master_pokedex[base_id_1][base_id_2] = {'species': create_fusion_name(info_1['name_1'], info_2['name_2']),
                                                    'base_id_1': base_id_1,
                                                    'base_id_2': base_id_2,
                                                    'type_primary': type_primary,
                                                    'type_secondary': None if type_secondary == '' else type_secondary,
                                                    'family': f"{info_1['family']}.{info_2['family']}",
                                                    'family_order': f"{info_1['family_order']}.{info_2['family_order']}",
                                                    'variants_dict': {'-': 'japeal'},
                                                    'hp': fused_stats['hp'],
                                                    'attack': fused_stats['attack'],
                                                    'defense': fused_stats['defense'],
                                                    'sp_attack': fused_stats['sp_attack'],
                                                    'sp_defense': fused_stats['sp_defense'],
                                                    'speed': fused_stats['speed'],
                                                    'total': fused_stats['total']}
                                                    

def change_numbers(dict):
    pokemon_to_change = Pokemon.query.join(Pokedex).filter(or_(Pokedex.base_id_1.in_(dict.keys()), Pokedex.base_id_2.in_(dict.keys())))
    for pokemon in pokemon_to_change:
        split_number = pokemon.pokedex_number.split('.')
        for i, s in enumerate(split_number):
            try:
                split_number[i] = dict[s]
            except KeyError:
                continue
        new_number = '.'.join(split_number)
        pokemon.pokedex_number = new_number
        pokemon.sprite = new_number
    db.session.commit()

def delete_numbers(dict):
    pokemon_to_delete = Pokemon.query.join(Pokedex).filter(or_(Pokedex.base_id_1.in_(dict.keys()), Pokedex.base_id_2.in_(dict.keys())))
    for pokemon in pokemon_to_delete:
        db.session.delete(pokemon)
    db.session.commit()