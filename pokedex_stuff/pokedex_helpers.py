import csv

def create_fusion_typing(pokemon_1, pokemon_2):
    # If pokemon is a Normal/Flying primary typing needs to be Flying
    if pokemon_1["type_1"] == 'Normal' and pokemon_1["type_2"] == 'Flying':
        head_type = pokemon_1["type_2"]
    else:
        head_type = pokemon_1["type_1"]
    # Pokemon in below list always use their primary typing even if they are to be used as the body Pokemon (where they would normally use their secondary typing)
    # Note: will need to update list manually as game is patched
    if pokemon_2["id"] in [1, 2, 3, 6, 74, 75, 76, 92, 93, 94, 95, 123, 130, 144, 145, 146, 149, 208]:
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
    exceptions_lst = ['450_1']
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