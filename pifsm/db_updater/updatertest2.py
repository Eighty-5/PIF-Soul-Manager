import csv
import os
import sys
import shutil
import subprocess
import string
from typing import Type

from datetime import datetime
from dotenv import load_dotenv
from pifsm import create_app
from sqlalchemy import or_, event
from itertools import chain
import time
from pifsm.decorators import func_timer
from pifsm.models import *

from database_utils import (
    create_pokedex_html,
    read_pokedex_csv,
    backup_database,
    sanitized_input,
    create_family_instances,
    create_fusion_species,
    create_fusion_stats,
    create_fusion_typing,
    create_fusion,
    convert_pokedex
)


app = create_app()

# Path Variables

# Constants
TMP_NUM = '000'
STATS_LIST = ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']
POKEDEX_ATTR = ['pokedex_number', 'species', 'type_primary', 'type_secondary', 'family_order', 'name_head', 'name_body']
POKEDEX_ATTR_ALL = POKEDEX_ATTR + STATS_LIST + ['family_number']
ALPHABET = string.ascii_lowercase
ALLOWED_SPRITE_CODE_CHAR = set(ALPHABET + string.digits + '.')

# Log File Time
start_time = datetime.now().strftime('%Y-%b-%d_T%H-%M-%S')

# Load ENV variables
load_dotenv()


def main(*args, **kwargs) -> None:

    # backup_database('sqlite')

    with app.app_context():
        if 'pokedex' in sys.argv:
            update_pokedex()
        if 'sprites' in sys.argv:
            update_sprites_test()
        if 'upload_sprites' in sys.argv:
            upload_sprites()
        if 'routes' in sys.argv:
            update_routes_list(routes_html_path=os.getenv('ROUTES_HTML_PATH'))
        print("Update Complete!")




@func_timer
def update_pokedex():
    new_dex = read_pokedex_csv(
        dict_key='species',
        base_pokedex_path=os.getenv('BASE_DEX_CSV_PATH_TEST'), 
        removed_pokedex_path=os.getenv('REMOVED_DEX_CSV_PATH')
    )
    new_dex = convert_pokedex(pokedex=new_dex, session_add=False)
    old_dex = get_pokedex(pokedex_type='base', dict_key='species')

    dex_deletions, dex_changes, dex_additions = compare_pokedexes(old_dex, new_dex)

    # Dont print any changes on initial upload to avoid screen clutter
    print_changes(dex_additions, dex_deletions, dex_changes)

    prompt_continue()

    # Order required: Deletions -> Changes -> Additions
    delete_pokemon_from_db(dex_deletions)
    dex_removals = []
    for number_change in dex_changes['pokedex_number']:
        if 'r' in number_change['new']:
            dex_removals.append(number_change)
    pokemon_to_removed_csv(dex_removals)
    bulk_change_pokemon(dex_changes)
    bulk_add_pokemon(dex_additions)
    prompt_continue()
    db.session.commit()

    create_pokedex_html(pokedex_html_path=os.getenv('POKEDEX_HTML_PATH'))


def print_changes(dex_additions, dex_deletions, changes_dict):
    """Prints any changes that will be made to the existing Pokedex in the DB"""
    print(f"Dex Additions:\n")
    for pokemon_addition in dex_additions:
        print(f"  {pokemon_addition}")
    print(f"Dex Deletions:\n")
    for pokemon_delete in dex_deletions:
        print(f"  {pokemon_delete}")
    for attr, changes in changes_dict.items():
        print(f"{attr}:")
        for change in changes:
            print(f"  {change}")


@func_timer
def update_sprites_test(initial_upload):
    artist_query = db.session.scalars(db.select(Artist))
    artists = {artist.artist_name: artist for artist in artist_query}
    
    artists_to_add = []
    if not 'japeal' in artists:
        artists_to_add.append(Artist(name='japeal'))
    sprite_credits_path = os.getenv('SPRITES_CREDITS_PATH')
    with open(sprite_credits_path, newline='', errors='ignore') as sprites_file:
        sprite_reader = csv.DictReader(sprites_file)
        for row in sprite_reader:
            artist_name = row['artist']
            if not artist_name in artists:
                artist = Artist(artist_name=artist_name)
                artists[artist_name] = artist
                artists_to_add.append(artist)
        db.session.add_all(artists_to_add)
    print("New Artists Added")

    pokedex_full = get_pokedex('full', 'pokedex_number')
    sprites_full = db.session.scalars(db.select(Sprite))
    sprites_dict = {sprite.sprite_code(): sprite for sprite in sprites_full}
    sprites_to_add = []
    artist_changes = []
    new_sprites_dict = {}
    dna_sprites = []

    with open(spirte_credits_path, newline='', errors='ignore') as sprites_file:
        sprite_reader = csv.DictReader(sprites_file)
        for sprite in sprite_reader:
            sprite_code = sprite['sprite']
            artist = sprite['artist']
            sprite_group, pokedex_number, variant, error = sanitized_sprite_code(sprite_code)
            if error:
                dna_sprites.append(
                    {
                        "ERROR": error,
                        "sprite": sprite_code,
                        "artist": artist
                    }
                )
            elif not pokedex_number in pokedex_full:
                dna_sprites.append(
                    {
                        "ERROR": "NUMBER NOT IN POKEDEX",
                        "sprite": sprite_code,
                        "artist": artist
                    }
                )
            else:
                try:
                    if not sprites_dict[sprite_code].artist_info.artist_name == artist:
                        sprites_dict[sprite_code].artist_info = artists[artist]
                except KeyError:
                    pokedex_info = pokedex_full[pokedex_number]
                    new_sprite = Sprite(
                        variant=variant,
                        artist_info=artists[artist],
                        pokedex_info=pokedex_info
                    )
                    db.session.add(new_sprite)
        
    db.session.commit()

    with open(f"{sprite_credits_path}{start_time}_error_logs.txt", 'w') as error_log:
        for err in dna_sprites:
            for key, value in err.items():
                error_log.write(f"{key}:{value}, ")
            error_log.write("\n")
                

@func_timer
def upload_sprites() -> None:
    # Move sprites to sprites directory
    confirm_sprite_additions = input("ADD NEW SPRITES [y/n]? ")
    if confirm_sprite_additions == 'y':
        # new_sprites_path = input("ENTER PATH OF NEW SPRITES: ")
        new_sprites_path = "D:/Projects/PIF-Game-Manager/pifsm/views/main/static/images/sprites"
        
        if not os.path.exists(os.path.dirname(new_sprites_path)):
            print(f"ERROR: Please provide a valid path")
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            sys.exit()
        else:
            sprite_dir_path = os.getenv('SPRITE_DIRECTORY_PATH')
            not_moved = []
            for filename in os.listdir(new_sprites_path):
                try:
                    if filename.endswith(".png"):
                        # Split each filename to determine correct directory
                        split_filename = filename.split(".")
                        if split_filename[0].isdigit() or split_filename[0] in PASS_LST:
                            destination = sprite_dir_path + "/" + split_filename[0]
                            shutil.move(os.path.join(new_sprites_path, filename), os.path.join(destination, filename))
                        elif split_filename[0][-1].isalpha() and (split_filename[0][:-1].isdigit() or split_filename[0][:-1] in PASS_LST):
                            destination = sprite_dir_path + "/" + split_filename[0][:-1]
                            shutil.move(os.path.join(new_sprites_path, filename), os.path.join(destination, filename))
                        else:
                            not_moved.append(filename)
                    else:
                        not_moved.append(filename)
                except FileNotFoundError:
                    not_moved.append(filename)

        print("SPRITE LIBRARY UPDATED")
        print(f"Files not moved: {not_moved}")


@func_timer
def update_routes_list(routes_html_path: str) -> None:
    from natsort import natsorted
    new_routes_lst = []
    old_routes_lst = {route.route_name:'' for route in db.session.scalars(db.select(RouteList))}
    routes_list_path = os.getenv('ROUTES_LIST_PATH')
    with open(routes_list_path, newline='', errors='ignore') as routes_file:
        reader = csv.DictReader(routes_file)
        for row in reader:
            route_name = row['route']
            if route_name not in old_routes_lst:
                db.session.add(
                    RouteList(route_name=route_name)
                )
    db.session.commit()
    new_routes_dict = {route.route_name:route.id for route in db.session.scalars(db.select(RouteList).order_by(RouteList.route_name))}
    sorted_route_names = natsorted(new_routes_dict.keys())
    with open(routes_html_path, 'w') as routes_html:
        for route in sorted_route_names:
            routes_html.write(f'<option value="{new_routes_dict[route]}">{route}</option>\n')


def prompt_continue():
    """Asks user if they want to continue with program"""
    continue_ans = ''
    while not continue_ans in ["y", "n"]:
        continue_ans = input("Continue with the above changes [Y / N]? ").lower()
    print("")
    if continue_ans == "n":
        print("UPDATER CANCELED\n")
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        exit()
    

def sanitized_sprite_code(sprite_code):
    """Filters our invalid sprite codes and returns values needed for app"""
    split_sprite_code = sprite_code.split('.')
    if not str_check(sprite_code, ALLOWED_SPRITE_CODE_CHAR):
        return None, None, None, 'SPECIAL CHARACTERS'
    if len(split_sprite_code) >= 3:
        return None, None, None, 'TRIPLE+ FUSION'
    sprite_group = split_sprite_code[0]
    if len(split_sprite_code) >= 2: # Setup for triple fusions later if desired
        last_number = split_sprite_code[-1]
        stripped_last_number = last_number.rstrip(ALPHABET)
        for pokedex_number in split_sprite_code[:-1] + [stripped_last_number]:
            if not pokedex_number.isdigit():
                return None, None, None, 'EXTRA LETTERS'
        variant = last_number[len(stripped_last_number):]
        split_sprite_code[-1] = stripped_last_number
        recombined_number = sprite_code[:len(sprite_code)-len(variant)]
    else:
        sprite_group = sprite_group.rstrip(ALPHABET)
        variant = sprite_code[len(sprite_group):]
        recombined_number = sprite_group
    return sprite_group, recombined_number, variant, None


def str_check(s, substr):
    """Returns True if all characters in string 's' are of substring 'substr'"""
    return set(s) <= substr


def get_pokedex(pokedex_type='base', dict_key='species'):
    """Returns a dictionary of either the full pokedex or just the base pokedex"""
    """and keys are either each pokemons species or number"""
    if pokedex_type == 'base':
        pokedex_query = db.session.scalars(db.select(Pokedex).where(Pokedex.head_pokemon==None))
    elif pokedex_type == 'full':
        pokedex_query = db.session.scalars(db.select(Pokedex))
    else:
        raise ValueError("get_pokedex() pokedex_type parameter must be 'base' or 'full'")
    
    if dict_key == 'species':
        pokedex = {entry.species: entry for entry in pokedex_query}
    elif dict_key == 'pokedex_number':
        pokedex = {entry.pokedex_number: entry for entry in pokedex_query}
    else:
        raise ValueError("get_pokedex() dict_type parameter must be 'species' or 'pokedex_number'") 
    
    return pokedex


def compare_pokedex_entries(entry_old, entry_new):
    """Compares two pokedex entries and returns any changes"""
    changes = {}
    for attr in POKEDEX_ATTR_ALL:
        if attr == 'family_number' and not entry_old.family.family_number==entry_new.family_number:
            changes[attr] = create_update_dict(
                entry_old.family.family_number, entry_new.family_number, entry_old
            )
        elif attr in STATS_LIST and not entry_old.stats.__eq__(entry_new.stats, attr):
            changes[attr] = create_update_dict(getattr(entry_old.stats, attr), getattr(entry_new.stats, attr), entry_old)
        elif attr in POKEDEX_ATTR and not entry_old.__eq__(entry_new, attr):
            changes[attr] = create_update_dict(getattr(entry_old, attr), getattr(entry_new, attr), entry_old)
    return changes  


@func_timer
def compare_pokedexes(old_dex, new_dex):
    """Compares both pokedexes for any deletions, changes or additions and returns them as lists"""
    dex_deletions = []
    dex_changes = {attr:[] for attr in POKEDEX_ATTR_ALL}
    dex_additions = []
    old_dex_nums = {pokemon.pokedex_number:species for species, pokemon in old_dex.items()}
    for species, new_dex_object in new_dex.items():
        changes = {}
        if species in old_dex:
            old_dex_object = old_dex[species]
            changes = compare_pokedex_entries(old_dex_object, new_dex_object)
        elif new_dex_object.pokedex_number in old_dex_nums:
            old_dex_object = old_dex[old_dex_nums[new_dex_object.pokedex_number]]
            prompt = (
                f"Should No. {new_dex_object.pokedex_number} {old_dex_object.species}"
                f" be updated to {species}?  "
            )
            answers = ('y', 'n')
            answer = sanitized_input(prompt, type_=str.lower, range_=answers)
            if answer == 'y':
                changes = compare_pokedex_entries(old_dex_object, new_dex_object)
            else:
                prompt = (
                    f"Is No. {new_dex_object.pokedex_number} {species} a new pokedex addition?  "
                )
                answers = ('y', 'n')
                answer = sanitized_input(prompt, type_=str.lower, range_=answers)
                if answer == 'y':
                    dex_additions.append(new_dex_object)
        else:
            dex_additions.append(new_dex_object)
        for attr, change in changes.items():
            dex_changes[attr].append(change)
    
    for species, old_dex_object in old_dex.items():
        if (not species in new_dex and 'r' not in old_dex_object.pokedex_number 
                and not species in [change['old'] for change in dex_changes['species']]):
            prompt = (
                f"Should No. {old_dex_object.pokedex_number} {species} be added to removed dex?  "
            )
            answers = ('y', 'n')
            answer = sanitized_input(prompt, type_=str.lower, range_=answers)
            if answer == 'y':
                dex_changes['pokedex_number'].append(
                    create_update_dict(
                        old_dex_object.pokedex_number, 
                        old_dex_object.pokedex_number + 'r', old_dex_object
                    )
                )
            else:
                dex_deletions.append(old_dex_object)
    return dex_deletions, dex_changes, dex_additions


@func_timer
def bulk_add_pokemon(dex_additions: list, commit=False):
    """Adds all new pokemon to the pokedex, including any fusions that would be created from the new pokemon""" 
    # family_dict = {family.family_number:family for family in db.session.scalars(db.select(Family))}
    # old_dex = get_pokedex('base', 'species')
    # japeal = db.session.scalar(db.select(Artist).where(Artist.artist_name=='japeal'))
    # bulk_additions = []
    # for pokemon_1 in dex_additions:
    #     default_sprite = Sprite(
    #         variant='',
    #         artist_info=japeal,
    #         pokedex_info=pokemon_1
    #     )
    #     new_fusion, family_dict = create_fusion(pokemon_1, pokemon_1, japeal, family_dict) 
    #     bulk_additions.append(new_fusion)
    #     for pokemon_2 in old_dex.values():
    #         new_fusion, family_dict = create_fusion(pokemon_1, pokemon_2, japeal, family_dict)
    #         bulk_additions.append(new_fusion)
    #         new_fusion, family_dict = create_fusion(pokemon_2, pokemon_1, japeal, family_dict)
    #         bulk_additions.append(new_fusion)
    #     for pokemon_2 in dex_additions:
    #         if pokemon_1 != pokemon_2:
    #             new_fusion, family_dict = create_fusion(pokemon_1, pokemon_2, japeal, family_dict)
    #             bulk_additions.append(new_fusion)
    # db.session.add_all(bulk_additions)
    # if commit:
    #     db.session.commit()

    """Adds all new pokemon to the pokedex, including any fusions that would be created from the new pokemon""" 
    family_dict = {family.family_number:family for family in db.session.scalars(db.select(Family))}
    old_dex = get_pokedex('base', 'species')
    japeal = db.session.scalar(db.select(Artist).where(Artist.artist_name=='japeal'))
    bulk_additions = {}
    for pokemon_1 in dex_additions:
        for pokemon_2 in old_dex.values():
            pokemon_2.family_number = pokemon_2.family.family_number
            new_fusion = create_fusion(pokemon_1, pokemon_2, japeal)
            bulk_additions[new_fusion.pokedex_number] = new_fusion
            # db.session.add(new_fusion)
            new_fusion = create_fusion(pokemon_2, pokemon_1, japeal)
            bulk_additions[new_fusion.pokedex_number] = new_fusion
            # db.session.add(new_fusion)
        for pokemon_2 in dex_additions:
            new_fusion = create_fusion(pokemon_1, pokemon_2, japeal)
            bulk_additions[new_fusion.pokedex_number] = new_fusion
            # db.session.add(new_fusion)
    
    family_dict = create_family_instances(bulk_additions, family_dict=family_dict)
    
    db.session.add_all(bulk_additions.values())
    if commit:
        db.session.commit()


@func_timer
def bulk_change_pokemon(dex_changes, commit=False) -> None:
    """Makes changes to DB Pokedex based on 'dex_changes' dictionary"""
    if dex_changes['family_number']:
        family_dict = {family.family_number:family for family in db.session.scalars(db.select(Family))}
    function_dispatcher = {
        'pokedex_number': update_fusion_pokedex_number,
        'species': update_fusion_species,
        'type_primary': update_fusion_typing,
        'type_secondary': update_fusion_typing,
        'family': update_fusion_family,
        'family_order': update_fusion_family_order,
        'stats': update_fusion_stats,
        'name_head': update_fusion_species,
        'name_body': update_fusion_species
    }
    for attr, changes in dex_changes.items():
        for change in changes:
            pokemon_to_update, new_value = change['obj'], change['new']
            if attr == 'family_number':
                if not new_value in family_dict:
                    new_family = Family(
                        family_number=new_value
                    )
                    family_dict[new_value] = new_family
                pokemon_to_update.family = family_dict[new_value]
                family_dict = update_fusion_family(base_pokemon=pokemon_to_update, family_dict=family_dict)
            elif attr in STATS_LIST:
                stat = attr
                pokemon_to_update.stats.update(commit=False, **{stat:new_value})
                function_dispatcher['stats'](pokemon_to_update)
            elif attr in POKEDEX_ATTR:
                pokemon_to_update.update(commit=False, **{attr:new_value})
                function_dispatcher[attr](pokemon_to_update)
    db.session.execute(db.delete(Family).where(Family.evolutions==None))
    if commit:
        db.session.commit()


@func_timer
def pokemon_to_removed_csv(dex_removals: list, commit: bool = False):
    """Adds all pokemon in dex_removals list to the 'removed_dex.csv' file"""
    removed_dex_path = os.getenv('REMOVED_DEX_CSV_PATH')
    with open(removed_dex_path, 'a') as removeddex:
        for pokemon_to_remove in dex_removals:
            pokemon = pokemon_to_remove['obj']
            removeddex.write(
                f"{pokemon.pokedex_number},{pokemon.species},{pokemon.type_primary},{pokemon.type_secondary},"
                f"{pokemon.name_head},{pokemon.name_body},{pokemon.family.family_number},{pokemon.family_order},"
                f"{pokemon.stats.hp},{pokemon.stats.attack},{pokemon.stats.defense},"
                f"{pokemon.stats.sp_attack},{pokemon.stats.sp_defense},{pokemon.stats.speed}\n"
            )     
    if commit:
        db.session.commit()


@func_timer
def delete_pokemon_from_db(dex_deletions: list, commit: bool = False):
    """Marks pokedex entries for deletion"""
    for pokemon in dex_deletions:
        db.session.delete(pokemon)
    if commit:
        db.session.commit()


def write_into_logs(updater_arr, file):
    for pokemon in updater_arr:
        file.write(f"{pokemon['obj']}\n{pokemon['old']} -> {pokemon['new']}\n")


def create_update_dict(old, new, obj):
    return {'old':old, 'new':new, 'obj':obj}


def update_fusion_pokedex_number(base_pokemon: Type[Pokedex], commit: bool = False):
    """Updates pokedex_number for every fusion that contains base_pokemon."""
    for fusion in base_pokemon.fusions_head + base_pokemon.fusions_body:
        new_pokedex_number = f"{fusion.head_pokemon.pokedex_number}.{fusion.body_pokemon.pokedex_number}"
        fusion.pokedex_number = new_pokedex_number
    if commit:
        db.session.commit()

def update_fusion_species(base_pokemon: Type[Pokedex], commit: bool = False):
    """Updates species for every fusion that contains base_pokemon."""
    for fusion in base_pokemon.fusions_head + base_pokemon.fusions_body:
        new_species = create_fusion_species(fusion.head_pokemon, fusion.body_pokemon)
        fusion.species = new_species
    if commit:
        db.session.commit()

def update_fusion_typing(base_pokemon: Type[Pokedex], commit: bool = False):
    """Updates type_primary and type_secondary for every fusion that contains base_pokemon."""
    for fusion in base_pokemon.fusions_head + base_pokemon.fusions_body:
        (new_type_primary, new_type_secondary) = create_fusion_typing(
            fusion.head_pokemon, fusion.body_pokemon
        )
        fusion.type_primary = new_type_primary
        fusion.type_secondary = new_type_secondary
    if commit:
        db.session.commit()


def update_fusion_family(base_pokemon: Type[Pokedex], family_dict: dict, commit: bool = False) -> dict:
    for fusion in base_pokemon.fusions_head + base_pokemon.fusions_body:
        fusion_family_number = f"{fusion.head_pokemon.family.family_number}.{fusion.body_pokemon.family.family_number}"
        if not fusion_family_number in family_dict:
            fusion_family = Family(
                family_number=fusion_family_number
            )
            family_dict[fusion_family_number] = fusion_family
        fusion.family = family_dict[fusion_family_number]
    if commit:
        db.session.commit()
    return family_dict


def update_fusion_family_order(base_pokemon: Type[Pokedex], commit: bool = False):
    """Updates family_order for every fusion that contains base_pokemon."""
    for fusion in base_pokemon.fusions_head + base_pokemon.fusions_body:
        new_family_order = f"{fusion.head_pokemon.family_order}.{fusion.body_pokemon.family_order}"
        fusion.family_order = new_family_order
    if commit:
        db.session.commit()

def update_fusion_stats(base_pokemon: Type[Pokedex], commit: bool = False):
    """Updates stats for every fusion that contains base_pokemon."""
    for fusion in base_pokemon.fusions_head + base_pokemon.fusions_body:
        new_stats = create_fusion_stats(fusion.head_pokemon, fusion.body_pokemon)
        fusion.stats.hp = new_stats.hp
        fusion.stats.attack = new_stats.attack
        fusion.stats.defense = new_stats.defense
        fusion.stats.sp_attack = new_stats.sp_attack
        fusion.stats.sp_defense = new_stats.sp_defense
        fusion.stats.speed = new_stats.speed
    if commit:
        db.session.commit()

# def create_fusion(head_pokemon: Type[Pokedex], body_pokemon: Type[Pokedex], japeal:Type[Artist], family_dict: dict) -> (Type[Pokedex], dict):
#     pokedex_number = create_fusion_pokedex_number(head_pokemon, body_pokemon)
#     species = create_fusion_species(head_pokemon, body_pokemon)
#     type_primary, type_secondary = create_fusion_typing(head_pokemon, body_pokemon)
#     (family, family_dict) = create_fusion_family(head_pokemon, body_pokemon, family_dict)
#     family_order = create_fusion_family_order(head_pokemon, body_pokemon)
#     stats = create_fusion_stats(head_pokemon, body_pokemon)
#     fusion = Pokedex(
#         pokedex_number=pokedex_number,
#         species=species,
#         type_primary=type_primary,
#         type_secondary=type_secondary,
#         family_order=family_order,
#         family=family,
#         head_pokemon=head_pokemon,
#         body_pokemon=body_pokemon,
#         stats=stats
#     )
#     default_sprite = Sprite(
#         variant='',
#         artist_info=japeal,
#         pokedex_info=fusion
#     )
#     return (fusion, family_dict)


# @func_timer
# def convert_pokedex(pokedex: dict, session_add: bool = True) -> dict:
#     """Converts the pokedex dictionaries into class instances for DB insertion."""
#     pokedex_copy = pokedex.copy()
#     for key, pokemon in pokedex_copy.items():
#         stats = PokedexStats(
#             hp=pokemon['hp'],
#             attack=pokemon['attack'],
#             defense=pokemon['defense'],
#             sp_attack=pokemon['sp_attack'],
#             sp_defense=pokemon['sp_defense'],
#             speed=pokemon['speed']
#         )
#         pokedex_instance = Pokedex(
#             pokedex_number=pokemon['pokedex_number'],
#             species=pokemon['species'],
#             type_primary=pokemon['type_primary'],
#             type_secondary=pokemon['type_secondary'],
#             family_order=pokemon['family_order'],
#             name_head=pokemon['name_head'],
#             name_body=pokemon['name_body'],
#             stats=stats
#         )
#         pokedex_instance.family_number = pokemon['family_number']
#         pokedex[key] = pokedex_instance
#     return pokedex


def session_check(session_type: str ="all"):
    """Prints any items in a session to console"""
    print("\nSESSION CHECK")
    if session_type == "all":
        for item in db.session:
            print(item)
    elif session_type == "modified":
        for item in db.session:
            if db.session.is_modified(item):
                print(item)
    else:
        raise ValueError("Incorrect Session Type")


if __name__ == "__main__":
    main()