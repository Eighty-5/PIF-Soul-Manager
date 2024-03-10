from myproject.models import Pokedex, Pokemon
from myproject.extensions import db
from sqlalchemy import or_

def create_fusion_typing(pokemon_1, pokemon_2):
    # If pokemon is a Normal/Flying primary typing needs to be Flying
    if pokemon_1["type_1"] == 'Normal' and pokemon_1["type_2"] == 'Flying':
        head_type = pokemon_1["type_2"]
    else:
        head_type = pokemon_1["type_1"]
    # Pokemon in below list always use their primary typing even if they are to be used as the body Pokemon (where they would normally use their secondary typing)
    # Note: will need to update list manually as game is patched
    if pokemon_2['number'] in [1, 2, 3, 6, 74, 75, 76, 92, 93, 94, 95, 123, 130, 144, 145, 146, 149, 208]:
        body_type = pokemon_2["type_1"]
    # If body Pokemon only has one type, the secondary typing of the new fused pokemon uses the primary typing of the body Pokemon
    elif pokemon_2["type_2"] == "":
        body_type = pokemon_2["type_1"]
    # If the body Pokemon's secondary type is the same as the head Pokemon's primary type, the body Pokemon's primary type is instead used for the fused Pokemon's secondary type
    elif pokemon_2["type_2"] == head_type:
        body_type = pokemon_2["type_1"]
    # If none of the above apply then the fused Pokemon's secondary type is the body Pokemon's secondary type. 
    else:
        body_type = pokemon_2["type_2"]
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
    
def confirmation(str, lst, print_triple, print_extra_variants):
    if str.count('.') > 1:
        if print_triple == 'y':
            print(f"TRIPLE FUSION (did not add): {str}")
        return False
    elif str[-2].isalpha():
        if print_extra_variants == 'y':
            print(f"EXTRA VARIANT (did not add): {str}")
        return False
    for item in lst:
        if item in str:
            return True
    confirm = input(f"{str} is not standard format would you like to add anyway [y/n]? ")
    if confirm == 'y':
        return True
    return False
        
def prep_number(sprite):
    prep_dict = {}
    sprite_split = sprite.split('.')
    if len(sprite_split) == 3:
        return 'TRIPLE'
    elif len(sprite_split) == 1:
        try:
            if sprite_split[0][-1].isalpha():
                prep_dict['base_1'] = sprite_split[0][:-1]
                prep_dict['var'] = sprite_split[0][-1]
            else:
                prep_dict['base_1'] = sprite_split[0]
        except IndexError:
            return 'BLANK'
    elif len(sprite_split) == 2:
        if sprite_split[1][-1].isalpha():
            prep_dict['base_1'] = sprite_split[0]
            prep_dict['base_2'] = sprite_split[1][:-1]
            prep_dict['var'] = sprite_split[1][-1]
        else:
            prep_dict['base_1'] = sprite_split[0]
            prep_dict['base_2'] = sprite_split[1]
    else:
        return 'INVALID NUMBER'

    return prep_dict

def extra_var_check(str):
    if str[-1].isalpha():
        print(f"EXTRA VARIANT (d.n.a): {str}")
    else:
        print(f"NOT VALID NUMBER (d.n.a): {str}")    

def create_master_dex(master_pokedex, dex_1, dex_2):
    for base_id_1, info_1 in dex_1.items():
        master_pokedex[base_id_1] = {}
        master_pokedex[base_id_1]['base'] = {}
        master_pokedex[base_id_1]['base']['species'] = info_1['species']
        master_pokedex[base_id_1]['base']['type_primary'] = info_1['type_1']
        if info_1['type_2'] == '':
            master_pokedex[base_id_1]['base']['type_secondary'] = None
        else:
            master_pokedex[base_id_1]['base']['type_secondary'] = info_1['type_2']
        master_pokedex[base_id_1]['base']['family'] = info_1['family']
        master_pokedex[base_id_1]['base']['family_order'] = info_1['family_order']
        master_pokedex[base_id_1]['base']['variants'] = '-'
        master_pokedex[base_id_1]['base']['variants_dict'] = {}
        master_pokedex[base_id_1]['base']['variants_dict'][''] = 'japeal'
        for base_id_2, info_2 in dex_1.items():
            master_pokedex[base_id_1][base_id_2] = {}
            master_pokedex[base_id_1][base_id_2]['species'] = create_fusion_name(info_1['name_1'], info_2['name_2'])
            master_pokedex[base_id_1][base_id_2]['base_id_1'] = base_id_1
            master_pokedex[base_id_1][base_id_2]['base_id_2'] = base_id_2
            type_primary, type_secondary = create_fusion_typing(info_1, info_2) 
            master_pokedex[base_id_1][base_id_2]['type_primary'] = type_primary
            if type_secondary == '':
                master_pokedex[base_id_1][base_id_2]['type_secondary'] = None
            else:
                master_pokedex[base_id_1][base_id_2]['type_secondary'] = type_secondary
            master_pokedex[base_id_1][base_id_2]['family'] = f"{info_1['family']}.{info_2['family']}"
            master_pokedex[base_id_1][base_id_2]['family_order'] = f"{info_1['family_order']}.{info_2['family_order']}"
            master_pokedex[base_id_1][base_id_2]['variants'] = '-'
            master_pokedex[base_id_1][base_id_2]['variants_dict'] = {}
            master_pokedex[base_id_1][base_id_2]['variants_dict'][''] = 'japeal'
        for base_id_2, info_2 in dex_2.items():
            master_pokedex[base_id_1][base_id_2] = {}
            master_pokedex[base_id_1][base_id_2]['species'] = create_fusion_name(info_1['name_1'], info_2['name_2'])
            master_pokedex[base_id_1][base_id_2]['base_id_1'] = base_id_1
            master_pokedex[base_id_1][base_id_2]['base_id_2'] = base_id_2
            type_primary, type_secondary = create_fusion_typing(info_1, info_2) 
            master_pokedex[base_id_1][base_id_2]['type_primary'] = type_primary
            if type_secondary == '':
                master_pokedex[base_id_1][base_id_2]['type_secondary'] = None
            else:
                master_pokedex[base_id_1][base_id_2]['type_secondary'] = type_secondary
            master_pokedex[base_id_1][base_id_2]['family'] = f"{info_1['family']}.{info_2['family']}"
            master_pokedex[base_id_1][base_id_2]['family_order'] = f"{info_1['family_order']}.{info_2['family_order']}"
            master_pokedex[base_id_1][base_id_2]['variants'] = '-'
            master_pokedex[base_id_1][base_id_2]['variants_dict'] = {}
            master_pokedex[base_id_1][base_id_2]['variants_dict'][''] = 'japeal'

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
        print(pokemon.id, pokemon.pokedex_number, pokemon.sprite)
    db.session.commit()

def delete_numbers(dict):
    pokemon_to_delete = Pokemon.query.join(Pokedex).filter(or_(Pokedex.base_id_1.in_(dict.keys()), Pokedex.base_id_2.in_(dict.keys())))
    for pokemon in pokemon_to_delete:
        db.session.delete(pokemon)
    db.session.commit()