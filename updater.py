import csv
import os
import sys
import shutil
import subprocess
from natsort import natsorted
import string

from datetime import datetime
from dotenv import load_dotenv
from myproject import create_app
from myproject.models import *
from myproject.extensions import db
from myproject.utils import func_logger, func_timer
from sqlalchemy import or_, event
from itertools import chain
import time

app = create_app()
PASS_LST = ['450_1']

# Path Variables
BASE_DEX_CSV_PATH = 'pokedex_stuff/pokedexes/if-base-dex.csv'
SPRITES_CREDITS_PATH = 'pokedex_stuff/sprite_credits/Sprite Credits.csv'
ROUTES_LIST_PATH = 'pokedex_stuff/routes.csv'
POKEDEX_HTML_PATH = 'myproject/blueprints/main/templates/pokemon_list.html'

REMOVED_DEX_CSV_PATH = 'pokedex_stuff/pokedexes/removed-dex.csv'
POKEDEX_UPDATES_PATH = 'pokedex_stuff/logs/pokedex_updates/'
ARTISTS_UPDATES_PATH = 'pokedex_stuff/logs/artists_updates/'
SPRITES_UPDATES_PATH = 'pokedex_stuff/logs/sprites_updates/'

# Constants
TMP_NUM = '000'
STATS_LIST = ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']
POKEDEX_ATTR = ['pokedex_number', 'species', 'type_primary', 'type_secondary', 'family_order', 'name_1', 'name_2']
FAMILY_ATTR = ['family_number']
ALPHABET = string.ascii_lowercase
ALLOWED_SPRITE_CODE_CHAR = set(ALPHABET + string.digits + '.')

# Log File Time
start_time = datetime.now().strftime('%Y-%b-%d_T%H-%M-%S')

# Family Dictionary Global Variable
family_dict = {}

# Load ENV variables
load_dotenv()

def main(*args, **kwargs) -> None:

    backup_database('sqlite')

    with app.app_context():
        initial_upload = False
        if 'pokedex' in sys.argv:
            initial_upload = update_pokedex(initial_upload)
        if 'sprites' in sys.argv:
            update_sprites_test(initial_upload)
        if 'upload_sprites' in sys.argv:
            upload_sprites()
        if 'routes' in sys.argv:
            update_routes_list()


@func_timer
def update_pokedex(initial_upload):

    new_dex, new_dex_stats, new_dex_nums, new_familys = {}, {}, {}, {}
    dupes = []
    with (open(BASE_DEX_CSV_PATH, newline='') as dexfile, open(REMOVED_DEX_CSV_PATH, newline='') as rdexfile):
        both_dexes = chain(csv.DictReader(rdexfile), csv.DictReader(dexfile))
        for row in both_dexes:
            pokedex_number, species = row['number'], row['species']
            if species in new_dex:
                dupes.append(({'pokedex_number':pokedex_number, 'species':species}, 
                              {'pokedex_number':new_dex[species].pokedex_number,'species':species}))
            if pokedex_number in new_dex_nums:
                dupes.append(({'pokedex_number':pokedex_number, 'species':species}, 
                              {'pokedex_number':pokedex_number,'species':new_dex_nums[pokedex_number]}))
            stats_object = PokedexStats(
                hp=int(row['hp']), attack=int(row['attack']), defense=int(row['defense']), 
                sp_attack=int(row['sp_attack']), sp_defense=int(row['sp_defense']), speed=int(row['speed']))
            if not row['family'] in family_dict:
                family_object = Family(
                    family_number=row['family']
                )
                family_dict[row['family']] = family_object
            else:
                family_object = family_dict[row['family']]
            dex_object = Pokedex(
                pokedex_number=pokedex_number, species=species, type_primary=row['type_primary'], type_secondary=row['type_secondary'], 
                family=family_object, family_order=row['family_order'], 
                name_1=row['name_1'], name_2=row['name_2'], stats=stats_object)
            new_dex[species] = dex_object

    old_dex = get_db_pokedex(pokedex_type='base', dict_key='species')
    old_dex_nums = {pokemon.pokedex_number:species for species, pokemon in old_dex.items()}
    changes_dict = {attr:[] for attr in POKEDEX_ATTR}
    changes_dict['family_number'] = []
    changes_dict['stats'] = []
    dex_additions = []

    if not old_dex:
        initial_upload = True
        print("Initial Pokedex Upload")
    for species, new_dex_object in new_dex.items():
        if species in old_dex:
            old_dex_object = old_dex[species]
            for attr in POKEDEX_ATTR:
                returner = new_dex_object.__eq__(old_dex_object, attr)
                if returner == False:
                    changes_dict[attr].append(
                        create_update_dict(
                            old_dex[species].__dict__.get(attr, float('NaN')), 
                            new_dex_object.__dict__.get(attr, float('NaN')), old_dex_object
                        )
                    )
            if not all(new_dex_object.stats.__eq__(old_dex_object.stats, stat) for stat in STATS_LIST):
                changes_dict['stats'].append(
                    create_update_dict(
                        old_dex_object.stats, new_dex_object.stats, old_dex_object 
                    )
                )
            if not new_dex_object.family.__eq__(old_dex_object.family, 'family_number'):
                changes_dict['family_number'].append(
                    create_update_dict(
                        old_dex[species].family.family_number, 
                        new_dex_object.family.family_number, old_dex_object
                    )
                )       
        elif new_dex_object.pokedex_number in old_dex_nums:
            old_dex_object = old_dex[old_dex_nums[new_dex_object.pokedex_number]]
            prompt = (f"Should No. {new_dex_object.pokedex_number} {old_dex_object.species} be updated to {species}?  ")
            answers = ('y', 'n')
            answer_1 = sanitized_input(prompt, type_=str.lower, range_=answers)
            if answer_1 == 'y':
                for attr in POKEDEX_ATTR:
                    returner = new_dex_object.__eq__(old_dex_object, attr)
                    if returner == False:
                        changes_dict[attr].append(
                            create_update_dict(
                                old_dex_object.__dict__.get(attr, float('NaN')),
                                new_dex_object.__dict__.get(attr, float('NaN')), old_dex_object
                            )
                        )
                if not all(new_dex_object.stats.__eq__(old_dex_object.stats, stat) for stat in STATS_LIST):
                    changes_dict['stats'].append(
                        create_update_dict(
                            old_dex_object.stats, new_dex_object.stats, old_dex_object 
                        )
                    )
                if not new_dex_object.family.__eq__(old_dex_object.family, 'family_number'):
                    changes_dict['family_number'].append(
                        create_update_dict(
                            old_dex_object.family.family_number,
                            new_dex_object.family.family_number, old_dex_object
                        )
                    )
            else:
                prompt = (f"Is No. {new_dex_object.pokedex_number} {species} a new pokedex addition?  ")
                answers = ('y', 'n')
                answer_2 = sanitized_input(prompt, type_=str.lower, range_=answers)
                if answer_2 == 'y':
                    dex_additions.append(new_dex_object)
        else:
            dex_additions.append(new_dex_object)

    dex_deletions = []
    for species, old_dex_object in old_dex.items():
        if not species in new_dex and 'r' not in old_dex_object.pokedex_number and not species in [species_change['old'] for species_change in changes_dict['species']]:
            prompt = (f"Should No. {old_dex_object.pokedex_number} {species} be added to removed dex?  ")
            answers = ('y', 'n')
            answer_1 = sanitized_input(prompt, type_=str.lower, range_=answers)
            if answer_1 == 'y':
                changes_dict['pokedex_number'].append(
                    create_update_dict(
                        old_dex_object.pokedex_number,
                        old_dex_object.pokedex_number + 'r',
                        old_dex_object
                    )
                )
            else:
                dex_deletions.append(old_dex_object)

    if not initial_upload:
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

    prompt_continue()

    # Order required: Deletions -> Changes -> Additions
    for pokemon in dex_deletions:
        delete_from_pokedex(pokedex_object=pokemon)

    dex_removals = []
    for number_change in changes_dict['pokedex_number']:
        if 'r' in number_change['new']:
            dex_removals.append(number_change)
    print("Dex Removals")
    print(dex_removals)

    with open(REMOVED_DEX_CSV_PATH, 'a') as removeddex:
        for pokemon_to_remove in dex_removals:
            pokemon = pokemon_to_remove['obj']
            update_pokedex_number_in_db(pokemon_to_remove['new'], pokemon)
            removeddex.write(
                f"{pokemon.pokedex_number},{pokemon.species},{pokemon.type_primary},{pokemon.type_secondary},"
                f"{pokemon.name_1},{pokemon.name_2},{pokemon.family.family_number},{pokemon.family_order},"
                f"{pokemon.stats.hp},{pokemon.stats.attack},{pokemon.stats.defense},"
                f"{pokemon.stats.sp_attack},{pokemon.stats.sp_defense},{pokemon.stats.speed}\n"
            )     

    for attr, changes in changes_dict.items():
        if attr == 'family_number':
            for change in changes:
                pokemon_to_update, new_value = change['obj'], change['new']
                setattr(pokemon_to_update.family, attr, new_value)
                # for fusion in pokemon_to_update.head_fusions + pokemon_to_update.body_fusions:
        elif attr == 'stats':
            for change in changes:
                pokemon_to_update = change['obj']
                new_stats = change['new']
                for stat in STATS_LIST:
                    setattr(pokemon_to_update.stats, stat, getattr(new_stats, stat))
                fusions = pokemon_to_update.fusions_head + pokemon_to_update.fusions_body
                for fusion in fusions:
                    create_fusion_stats(fusion.head_pokemon, fusion.body_pokemon, fusion)
        else:
            for change in changes:
                pokemon_to_update, new_value = change['obj'], change['new']
                setattr(pokemon_to_update, attr, new_value)
                fusions = pokemon_to_update.fusions_head + pokemon_to_update.fusions_body
                for fusion in fusions:
                    if attr == 'pokedex_number':
                        create_fusion_pokedex_number(fusion.head_pokemon, fusion.body_pokemon, fusion)
                    elif attr in ['species', 'name_1', 'name_2']:
                        create_fusion_species(fusion.head_pokemon, fusion.body_pokemon, fusion)
                    elif attr in ['type_primary', 'type_secondary']:
                        create_fusion_typing(fusion.head_pokemon, fusion.body_pokemon, fusion)
                    elif attr == 'family_order':
                        create_fusion_family_order(fusion.head_pokemon, fusion.body_pokemon, fusion)
    
    japeal = db.session.scalar(db.select(Artist).where(Artist.artist_name=='japeal'))
    if not japeal:
        japeal = Artist(
            artist_name='japeal'
        )
        db.session.add(japeal)
    for pokemon_1 in dex_additions:
        default_sprite = Sprite(
            variant='',
            artist_info=japeal,
            pokedex_info=pokemon_1
        )
        db.session.add(default_sprite)
        pokemon_1.artist_info = japeal
        new_fusion = create_fusion(pokemon_1, pokemon_1, japeal)
        for pokemon_2 in dex_additions:
            if pokemon_1 != pokemon_2:
                create_fusion(pokemon_1, pokemon_2, japeal)
        for pokemon_2 in old_dex.values():
            create_fusion(pokemon_1, pokemon_2, japeal)
            create_fusion(pokemon_2, pokemon_1, japeal)


    db.session.commit()


    # Create pokedex list for adding pokemon
    base_pokedex = db.session.scalars(db.select(Pokedex).where(Pokedex.head_pokemon==None))
    
    # Quick and Dirty sort change later
    base_pokedex = {int(pokemon.pokedex_number):pokemon.species for pokemon in base_pokedex}
    count = 1
    pokedex_lst = []
    while count <= len(base_pokedex):
        pokedex_lst.append(base_pokedex[count])
        count += 1

    with open(POKEDEX_HTML_PATH, 'w') as pokedex_html_file:
        pokedex_html_file.write('<datalist id="pokedex">\n')
        for pokemon in pokedex_lst:
            pokedex_html_file.write(f'  <option value="{pokemon}"></option>\n')
        pokedex_html_file.write('</datalist>')


@func_logger
def delete_from_pokedex(pokedex_object):
    db.session.delete(pokedex_object)

@func_logger
def add_to_pokedex(pokedex_object):
    pass


@func_timer
def update_sprites_test(initial_upload):
    artist_query = db.session.scalars(db.select(Artist))
    artists = {artist.artist_name: artist for artist in artist_query}
    
    artists_to_add = []
    if not 'japeal' in artists:
        artists_to_add.append(Artist(name='japeal'))
    with open(SPRITES_CREDITS_PATH, newline='', errors='ignore') as sprites_file:
        sprite_reader = csv.DictReader(sprites_file)
        for row in sprite_reader:
            artist_name = row['artist']
            if not artist_name in artists:
                artist = Artist(artist_name=artist_name)
                artists[artist_name] = artist
                artists_to_add.append(artist)
        db.session.add_all(artists_to_add)
    print("New Artists Added")

    pokedex_full = get_db_pokedex('full', 'pokedex_number')
    sprites_full = db.session.scalars(db.select(Sprite))
    sprites_dict = {sprite.sprite_code(): sprite for sprite in sprites_full}
    sprites_to_add = []
    artist_changes = []
    new_sprites_dict = {}
    dna_sprites = []

    with open(SPRITES_CREDITS_PATH, newline='', errors='ignore') as sprites_file:
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

    with open(f"{SPRITES_UPDATES_PATH}{start_time}_error_logs.txt", 'w') as error_log:
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
        new_sprites_path = "D:/Projects/PIF-Game-Manager/myproject/blueprints/main/static/images/sprites"
        
        if not os.path.exists(os.path.dirname(new_sprites_path)):
            print(f"ERROR: Please provide a valid path")
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
def update_routes_list():
    routes_html_path = os.getenv('ROUTES_HTML_PATH')
    new_routes_lst = []
    old_routes_lst = {route.route_name:'' for route in db.session.scalars(db.select(RouteList))}

    with open(ROUTES_LIST_PATH, newline='', errors='ignore') as routes_file:
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
    continue_ans = ''
    while not continue_ans in ["y", "n"]:
        continue_ans = input("Continue with the above changes [Y / N]? ").lower()
    print("")
    if continue_ans == "n":
        print("UPDATER CANCELED\n")
        exit()
    

def sanitized_sprite_code(sprite_code):
    def str_check(s, substr):
        return set(s) <= substr

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


def get_db_pokedex(pokedex_type='base', dict_key='species'):
    if pokedex_type == 'base':
        db_pokedex_query = db.session.scalars(db.select(Pokedex).where(Pokedex.head_pokemon==None))
    elif pokedex_type == 'full':
        db_pokedex_query = db.session.scalars(db.select(Pokedex))
    else:
        raise ValueError("get_db_pokedex() pokedex_type parameter must be 'base' or 'full'")
    
    if dict_key == 'species':
        db_pokedex = {entry.species: entry for entry in db_pokedex_query}
    elif dict_key == 'pokedex_number':
        db_pokedex = {entry.pokedex_number: entry for entry in db_pokedex_query}
    else:
        raise ValueError("get_db_pokedex() dict_type parameter must be 'species' or 'pokedex_number'") 
    
    return db_pokedex


def write_into_logs(updater_arr, file):
    for pokemon in updater_arr:
        file.write(f"{pokemon['obj']}\n{pokemon['old']} -> {pokemon['new']}\n")


def create_update_dict(old, new, obj):
    return {'old':old, 'new':new, 'obj':obj}


def sanitized_input(prompt, type_=None, min_=None, max_=None, range_=None):
    # https://stackoverflow.com/a/23294659
    if min_ is not None and max_ is not None and max_ < min_:
        raise ValueError("min_ must be less than or equal to max_.")
    while True:
        ui = input(prompt)
        if type_ is not None:
            try:
                ui = type_(ui)
            except ValueError:
                print("Input type must be {0}.".format(type_.__name__))
                continue
        if max_ is not None and ui > max_:
            print("Input must be less than or equal to {0}.".format(max_))
        elif min_ is not None and ui < min_:
            print("Input must be greater than or equal to {0}.".format(min_))
        elif range_ is not None and ui not in range_:
            if isinstance(range_, range):
                template = "Input must be between {0.start} and {0.stop}."
                print(template.format(range_))
            else:
                template = "Input must be {0}."
                if len(range_) == 1:
                    print(template.format(*range_))
                else:
                    expected = " or ".join((
                        ", ".join(str(x) for x in range_[:-1]),
                        str(range_[-1])
                    ))
                    print(template.format(expected))
        else:
            return ui


def update_pokedex_number(pokemon, new):
    pokemon.pokedex_number = new
    fusions = pokemon.fusions_head + pokemon.fusions_body
    for fusion_to_update in fusions:
        create_fusion_pokedex_number(
            head_pokemon=fusion_to_update.head_pokemon, 
            body_pokemonp=fusion_to_update.body_pokemon,
            fusion_to_update=fusion_to_update
        )
    if pokemon.family_order == '1':
        pokemon.family.family_number = new
        first_fusions = db.session.scalars(db.session.select(Pokedex).where(
            or_(Pokedex.head_pokemon==pokemon, Pokedex.body_pokemon==pokemon), 
            Pokedex.family_order=='1.1'
        ))
        for fusion in first_fusions:
            new_fusion_family_number = f"{fusion.head_pokemon.family.family_number}.{fusion.body_pokemon.family.family_number}"
            fusion.family.family_number = new_fusion_family_number


def create_fusion_pokedex_number(head_pokemon, body_pokemon, fusion_to_update=None):
    pokedex_number_1 = head_pokemon.pokedex_number
    pokedex_number_2 = body_pokemon.pokedex_number
    fusion_pokedex_number = f"{pokedex_number_1}.{pokedex_number_2}"
    if fusion_to_update:
        fusion_to_update.pokedex_number = fusion_pokedex_number
        if fusion_to_update.family_order == '1.1':
            fusion_to_update.family.family_number = fusion_to_update.pokedex_number
        return fusion_to_update
    return fusion_pokedex_number


def create_fusion_species(head_pokemon, body_pokemon, fusion_to_update=None):
    name_1 = head_pokemon.name_1
    name_2 = body_pokemon.name_2
    if name_1[-1] == name_2[0]:
        fusion_species = name_1 + name_2[1:]
    else:
        fusion_species = name_1 + name_2
    if fusion_to_update:
        fusion_to_update.species = fusion_species
        return fusion_to_update
    return fusion_species


def create_fusion_typing(head_pokemon, body_pokemon, fusion_to_update=None):
    # See pokedex_stuff/fusion_rules for specification on how fusions are performed
    if head_pokemon.type_primary == 'Normal' and head_pokemon.type_secondary == 'Flying':
        fusion_type_primary = head_pokemon.type_secondary
    else:
        fusion_type_primary = head_pokemon.type_primary
    if body_pokemon.type_secondary == "" or body_pokemon.type_secondary == fusion_type_primary:
        fusion_type_secondary = body_pokemon.type_primary
    else:
        fusion_type_secondary = body_pokemon.type_secondary
    if fusion_type_secondary == fusion_type_primary:
        fusion_type_secondary = ""

    if fusion_to_update:
        fusion_to_update.type_primary = fusion_type_primary
        fusion_to_update.type_secondary = fusion_type_secondary
        return fusion_to_update
    return fusion_type_primary, fusion_type_secondary


def create_fusion_family_number(head_pokemon, body_pokemon, fusion_to_update=None):
    family_1 = head_pokemon.family.family_number
    family_2 = body_pokemon.family.family_number
    fusion_family_number = f"{family_1}.{family_2}"
    if fusion_to_update:
        fusion_to_update.family.family_number = fusion_family_number
    return fusion_family_number


def create_fusion_family_order(head_pokemon, body_pokemon, fusion_to_update=None):
    family_order_1 = head_pokemon.family_order
    family_order_2 = body_pokemon.family_order
    fusion_family_order = f"{family_order_1}.{family_order_2}"
    if fusion_to_update:
        fusion_to_update.family_order = fusion_family_order
        return fusion_to_update
    return fusion_family_order


def create_fusion_stats(head_pokemon, body_pokemon, fusion_to_update=None):
    hp=int(2 * (head_pokemon.stats.hp)/3 + (body_pokemon.stats.hp)/3)
    attack=int(2 * (body_pokemon.stats.attack)/3 + (head_pokemon.stats.attack)/3)
    defense=int(2 * (body_pokemon.stats.defense)/3 + (head_pokemon.stats.defense)/3)
    sp_attack=int(2 * head_pokemon.stats.sp_attack/3 + body_pokemon.stats.sp_attack/3)
    sp_defense=int(2 * head_pokemon.stats.sp_defense/3 + body_pokemon.stats.sp_defense/3)
    speed=int(2 * body_pokemon.stats.speed/3 + head_pokemon.stats.speed/3)

    if fusion_to_update:
        fusion_to_update.stats.hp = hp
        fusion_to_update.stats.attack = attack
        fusion_to_update.stats.defense = defense
        fusion_to_update.stats.sp_attack = sp_attack
        fusion_to_update.stats.sp_defense = sp_defense
        fusion_to_update.stats.speed = speed
        return fusion_to_update
    else:
        fused_stats = PokedexStats(
            hp=hp,
            attack=attack,
            defense=defense,
            sp_attack=sp_attack,
            sp_defense=sp_defense,
            speed=speed
        )
        return fused_stats


def create_fusion(head_pokemon, body_pokemon, japeal):
    pokedex_number = create_fusion_pokedex_number(head_pokemon, body_pokemon)
    type_primary, type_secondary = create_fusion_typing(head_pokemon, body_pokemon)
    stats = create_fusion_stats(head_pokemon, body_pokemon)
    species = create_fusion_species(head_pokemon, body_pokemon)
    family_number = create_fusion_family_number(head_pokemon, body_pokemon)
    family_order = create_fusion_family_order(head_pokemon, body_pokemon)
    try:
        family = family_dict[family_number]
    except KeyError:
        family = Family(
            family_number = family_number
        )
        family_dict[family_number] = family
    fusion = Pokedex(
        pokedex_number=pokedex_number,
        species=species,
        type_primary=type_primary,
        type_secondary=type_secondary,
        family_order=family_order,
        family=family,
        head_pokemon=head_pokemon,
        body_pokemon=body_pokemon,
        stats=stats
    )
    default_sprite = Sprite(
        variant='',
        artist_info=japeal,
        pokedex_info=fusion
    )
    db.session.add(default_sprite)
    return fusion, default_sprite


def backup_database(db_type):
    db_backup_filename = start_time + '_pifsm.db'
    db_backup_path = f"{os.getenv('DB_BACKUP_PATH')}{db_backup_filename}"

    if db_type == 'sqlite':
        src = "D:/Projects/PIF-Game-Manager/instance/pifsm.db"
        dst = db_backup_path
        shutil.copyfile(src, dst)
    elif db_type == 'mysql':
        subprocess.run(f"mysqldump -u root -p {os.getenv('DB_NAME')} > {db_backup_path}", shell=True)


if __name__ == "__main__":
    main()