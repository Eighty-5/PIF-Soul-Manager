import csv
import os
import sys
import shutil
import subprocess
from string import ascii_lowercase as alphabet

from datetime import datetime
from dotenv import load_dotenv
from myproject import create_app
from myproject.models import Pokedex, PokedexFamily, PokedexStats, Sprite, Artist, RouteList
from myproject.extensions import db
from myproject.utils import func_logger, func_timer
from sqlalchemy import create_engine, text, insert, or_
from itertools import chain
import time

app = create_app()
PASS_LST = ['450_1']

# Path Variables
BASE_DEX_CSV_PATH = 'pokedex_stuff/pokedexes/if-base-dex-new.csv'
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

# Family Dictionary Global Variable
family_dict = {}

# Load ENV variables
load_dotenv()

def main(*args, **kwargs) -> None:
    with app.app_context():
        initial_upload = False
        if 'pokedex' in sys.argv:
            initial_upload = update_pokedex_test(initial_upload)
        if 'sprites' in sys.argv:
            update_sprites(initial_upload)
        if 'upload_sprites' in sys.argv:
            upload_sprites()
        if 'routes' in sys.argv:
            update_routes_list()


@func_timer
def update_pokedex_test(initial_upload):

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
                family_object = PokedexFamily(
                    family_number=row['family']
                )
                family_dict[row['family']] = family_object
            else:
                family_object = family_dict[row['family']]
            dex_object = Pokedex(
                pokedex_number=pokedex_number, species=species, type_primary=row['type_primary'], type_secondary=row['type_secondary'], 
                family=row['family'], family_order=row['family_order'], 
                name_1=row['name_1'], name_2=row['name_2'], stats=stats_object, evolution_family=family_object)
            new_dex[species] = dex_object

    old_dex = get_db_pokedex(pokedex_type='base', dict_key='species')
    old_dex_nums = {pokemon.pokedex_number:species for species, pokemon in old_dex.items()}
    changes_dict = {attr:[] for attr in POKEDEX_ATTR}
    changes_dict['family_number'] = []
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
            if new_dex_object.family != old_dex_object.evolution_family.family_number:
                changes_dict['family_number'].append(
                    create_update_dict(
                        old_dex[species].evolution_family.family_number, 
                        new_dex_object.family, old_dex_object
                    )
                )       
        elif new_dex_object.pokedex_number in old_dex_nums:
            old_dex_object = old_dex[old_dex_nums[new_dex_object.pokedex_number]]
            prompt = (f"Should No. {new_dex_object.pokedex_number} {old_dex_object.species} be updated to {species}?  ")
            answers = ('y', 'n')
            answer_1 = sanitised_input(prompt, type_=str.lower, range_=answers)
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
                if new_dex_object.family != old_dex_object.evolution_family.family_number:
                    changes_dict['family_number'].append(
                        create_update_dict(
                            old_dex_object.evolution_family.family_number,
                            new_dex_object.family, old_dex_object
                        )
                    )
            else:
                prompt = (f"Is No. {new_dex_object.pokedex_number} {species} a new pokedex addition?  ")
                answers = ('y', 'n')
                answer_2 = sanitised_input(prompt, type_=str.lower, range_=answers)
                if answer_2 == 'y':
                    dex_additions.append(new_dex_object)
        else:
            dex_additions.append(new_dex_object)

    dex_deletions = []
    for species, old_dex_object in old_dex.items():
        if not species in new_dex and 'r' not in old_dex_object.pokedex_number and not species in changes_dict['species']:
            prompt = (f"Should No. {old_dex_object.pokedex_number} {species} be added to removed dex?  ")
            answers = ('y', 'n')
            answer_1 = sanitised_input(prompt, type_=str.lower, range_=answers)
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

    # BACKUP DATABASE
    start_time = datetime.now().strftime('%Y-%b-%d_T%H-%M-%S')
    db_backup_filename = start_time + '_pifsm.db'
    # MySQL
    # subprocess.run(f"mysqldump -u root -p pif_game_manager > {os.getenv('DB_BACKUP_PATH')}{db_backup_filename}", shell=True)
    # SQLite
    src = "instance/pifsm.db"
    dst = f"db_backups/{db_backup_filename}"
    shutil.copyfile(src, dst)
    # subprocess.run(f"cp instance/pifsm.db db_backups/{start_time}pifsm.db")



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
                f"{pokemon.name_1},{pokemon.name_2},{pokemon.family},{pokemon.family_order},"
                f"{pokemon.stats.hp},{pokemon.stats.attack},{pokemon.stats.defense},"
                f"{pokemon.stats.sp_attack},{pokemon.stats.sp_defense},{pokemon.stats.speed}\n"
            )     

    for attr, changes in changes_dict.items():
        if attr == 'family_number':
            for change in changes:
                pokemon_to_update, new_value = change['obj'], change['new']
                setattr(pokemon_to_update.evolution_family, attr, new_value)
                # for fusion in pokemon_to_update.head_fusions + pokemon_to_update.body_fusions:
                    
        else:
            for change in changes:
                pokemon_to_update, new_value = change['obj'], change['new']
                setattr(pokemon_to_update, attr, new_value)
                if attr == 'pokedex_number':
                    fusions = pokemon_to_update.fusions_head + pokemon_to_update.fusions_body
                    for fusion in fusions:
                        create_fusion_pokedex_number(fusion.head_pokemon, fusion.body_pokemon, fusion)
    
    pokemon_to_add = []
    for pokemon_1 in dex_additions:
        db.session.add(pokemon_1)
        create_fusion(pokemon_1, pokemon_1)
        for pokemon_2 in dex_additions:
            if pokemon_1 != pokemon_2:
                create_fusion(pokemon_1, pokemon_2)
        for pokemon_2 in old_dex.values():
            create_fusion(pokemon_1, pokemon_2)
            create_fusion(pokemon_2, pokemon_1)

    


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

@func_timer
def update_pokedex(initial_upload):
    # Checks for Duplicates
    new_dex, new_dex_stats, new_dex_nums, new_familys = {}, {}, {}, {}
    master_logger_arr = []
    dupes = []
    with (open(BASE_DEX_CSV_PATH, newline='') as dexfile, open(REMOVED_DEX_CSV_PATH, newline='') as rdexfile):
        dex = chain(csv.DictReader(rdexfile), csv.DictReader(dexfile))
        for row in dex:
            pokedex_number, species = row['number'], row['species']
            if species in new_dex:
                dupes.append(({'pokedex_number':pokedex_number, 'species':species}, 
                              {'pokedex_number':new_dex[species].pokedex_number,'species':species}))
            if pokedex_number in new_dex_nums:
                dupes.append(({'pokedex_number':pokedex_number, 'species':species}, 
                              {'pokedex_number':pokedex_number,'species':new_dex_nums[pokedex_number]}))
            stats_obj = PokedexStats(
                hp=int(row['hp']), attack=int(row['attack']), defense=int(row['defense']), 
                sp_attack=int(row['sp_attack']), sp_defense=int(row['sp_defense']), speed=int(row['speed']))
            if not row['family'] in new_familys:
                family_obj = PokedexFamily(
                    family_number=row['family']
                )
            else:
                family_obj = new_familys[row['family']]
            dex_obj = Pokedex(
                pokedex_number=pokedex_number, species=species, type_primary=row['type_primary'], type_secondary=row['type_secondary'], 
                family=row['family'], family_order=row['family_order'], 
                name_1=row['name_1'], name_2=row['name_2'], stats=stats_obj, evolution_family=family_obj)
            new_familys[row['family']] = family_obj
            new_dex[species] = dex_obj
            new_dex_nums[pokedex_number] = species
    if dupes:
        print(f"DUPLICATES FOUND:\n{dupes}")
        exit()

    old_dex = get_db_pokedex(pokedex_type='base', dict_key='species')
    old_dex_nums = {pokemon.pokedex_number:species for species, pokemon in old_dex.items()}
    dex_removals = []
    species_updates = []
    pokedex_number_updates = []
    dex_additions = []
    pokedex_numbers_and_species_updates = []
    dex_deletions = []
    
    # Only manual part of the program. When a name from the previous pokedex is not detected in the new pokedex, 
    # admin needs to determine whether this is simply a name being updated to a correct name, or if the pokemon should actually be deleted/removed
    # from the pokedex

    # CHECKS FOR ANY CHANGES IN pokedex_number OR SPECIES BETWEEN OLD AND NEW POKEDEXES
    if not old_dex:
        initial_upload = True
        print("Initial Pokedex Upload")
    for old_species, old_dex_entry in old_dex.copy().items():
        try:
            if not old_dex[old_species].__eq__(new_dex[old_species], 'pokedex_number'):
                pokedex_number_updates.append(
                    create_update_dict(old_dex_entry.pokedex_number, new_dex[old_species].pokedex_number, old_dex_entry))
        except KeyError:
            if not 'r' in old_dex_entry.pokedex_number: 
                try:
                    replacement_species = new_dex_nums[old_dex_entry.pokedex_number]
                    prompt = (f"Should [{old_dex[old_species].pokedex_number} - {old_species.upper()}] be removed or pokedex_number "
                              f"and/or species updated to [{old_dex_entry.pokedex_number} - {replacement_species.upper()}]? \n"   
                              f"    [R (removed) / U (species update) / C (pokedex_number and species update)] ")
                    answers = ('r', 'u', 'c')
                except KeyError:
                    prompt = (f"Should [{old_dex[old_species].pokedex_number} - {old_species.upper()}] be removed or " 
                              f"pokedex_number and species updated? \n"        
                              f"    [R (removed) / C (pokedex_number and species update)] ")
                    answers = ('r', 'c')
                answer_1 = sanitised_input(prompt, type_=str.lower, range_=answers)
                if answer_1 == "u" and not (any(replacement_species == _dict['obj'].species for _dict in pokedex_number_updates)):
                    species_updates.append(
                        create_update_dict(old_dex_entry.species, replacement_species, old_dex_entry))
                elif answer_1 == "r":
                    dex_removals.append(
                        create_update_dict(old_dex_entry.pokedex_number, old_dex_entry.pokedex_number + 'r', old_dex_entry))
                else:
                    prompt_2 = (f"Please specify which pokedex pokedex_number + species combo that "
                                f"[{old_dex_entry.pokedex_number} - {old_species.upper()}] should be updated to: ")
                    answer_2 = sanitised_input(prompt_2, int, range_=old_dex_nums)
                    pokedex_numbers_and_species_updates.append(
                        create_update_dict(
                            {'pokedex_number':old_dex_entry.pokedex_number,'species':old_species},
                            {'pokedex_number':answer_2,'species':old_dex_nums[answer_2]},
                            old_dex_entry))
            else:
                dex_deletions.append(create_update_dict('', '', old_dex_entry))
        
    if not initial_upload:
        print(f"SPECIES UPDATES:\n{species_updates}")
        print(f"NUMBER UPDATES:\n{pokedex_number_updates}")
        print(f"NUMBER AND SPECIES UPDATES:\n{pokedex_numbers_and_species_updates}")
        print(f"DEX REMOVALS:\n{dex_removals}")
        print(f"DEX DELETIONS:\n{dex_deletions}")

    prompt_continue()

    # BACKUP DATABASE
    # db_backup_filename = 'pifsm_db_' + start_time + '.sql'
    # subprocess.run(f"mysqldump -u root -p pif_game_manager > {os.getenv('DB_BACKUP_PATH')}{db_backup_filename}", shell=True)
    
    for pokemon in dex_deletions:
        del old_dex[pokemon['obj'].species]
        db.session.delete(pokemon['obj'])

    with open(REMOVED_DEX_CSV_PATH, 'a') as removeddex:
        for pokemon_to_remove in dex_removals:
            pokemon = pokemon_to_remove['obj']
            update_pokedex_number_in_db(pokemon_to_remove['new'], pokemon)
            removeddex.write(f"{pokemon.pokedex_number},{pokemon.species},{pokemon.type_primary},{pokemon.type_secondary},"
                             f"{pokemon.name_1},{pokemon.name_2},{pokemon.family},{pokemon.family_order},"
                             f"{pokemon.stats.hp},{pokemon.stats.attack},{pokemon.stats.defense},"
                             f"{pokemon.stats.sp_attack},{pokemon.stats.sp_defense},{pokemon.stats.speed}\n")                    
            
    for pokemon in species_updates:
        old_dex[pokemon['new']] = pokemon['obj']
        del old_dex[pokemon['old']]
        pokemon['obj'].species = pokemon['new']
    
    pokedex_number_change_all(pokedex_number_updates)

    # UPDATE HERE
    for update_dict in pokedex_numbers_and_species_updates:
        pokemon = update_dict['obj']
        update_pokedex_number_in_db(update_dict['new']['pokedex_number'], pokemon)
        pokemon.species = update_dict['new']['species']
        old_dex[pokemon['old']['species']] = pokemon

    # update_existing_t0 = time.perf_counter()
    family_orders_to_update, stats_to_update, typing_to_update, naming_schema_to_update = [], [], [], []
    for old_species in old_dex:
        try:
            new_entry, old_entry = new_dex[old_species], old_dex[old_species]
        except KeyError:
            continue
        if not new_entry.__eq__(old_entry, 'family_order'):
            print(f"{old_entry}\n{new_entry}")
            family_orders_to_update.append(create_update_dict(old_entry.family_order, new_entry.family_order, old_entry))
        for stat in STATS_LIST:
            if not new_entry.stats.__eq__(old_entry.stats, stat):
                stats_to_update.append(create_update_dict(old_entry.stats, new_entry.stats, old_entry))
                break
        if not new_entry.__eq__(old_entry, 'type_primary', 'type_secondary'):
            typing_to_update.append(
                create_update_dict(
                    {'type_primary':old_entry.type_primary, 'type_secondary':old_entry.type_secondary},
                    {'type_primary':new_entry.type_primary, 'type_secondary':new_entry.type_secondary},
                    old_entry))
        if not new_entry.__eq__(old_entry, 'name_1', 'name_2'):
            naming_schema_to_update.append(
                create_update_dict(
                    {'name_1':old_entry.name_1, 'name_2':old_entry.name_2},
                    {'name_1':new_entry.name_1, 'name_2':new_entry.name_2},
                    old_entry))
    print("\nPOKEDEX BASE ENTRIES THAT REQUIRE INFO UPDATES:")
    for update, _dict in {'Stats':stats_to_update, 'Typing':typing_to_update, 
                          'Family Order': family_orders_to_update, 
                          'Naming Schema': naming_schema_to_update}.items():
        print(f"{update}")
        for pokemon in _dict:
            print(pokemon)

    prompt_continue()

    update_stats(stats_to_update)
    update_typing(typing_to_update)
    update_family_order(family_orders_to_update)
    update_naming(naming_schema_to_update)
    # update_existing_t1 = time.perf_counter()
    
    # additions_checks_t0 = time.perf_counter()
    for new_species, pokemon in new_dex.items():
        if not new_species in old_dex:
            dex_additions.append(create_update_dict('', '', pokemon))
    if dex_additions:
        print(f"NEW POKEMON FOUND:")
        for pokemon in dex_additions:
            print(pokemon['obj'])
        print("")
    else:
        print("No new pokemon found\n")

    prompt_continue()

    # Create evolutions table
    pokedex_familys = db.session.scalars(db.select(PokedexFamily).where(~PokedexFamily.family_number.contains('.')))
    pokedex_familys = {entry.family_number:entry for entry in pokedex_familys}
    new_fusion_familys = {}
    for family_number_1 in new_familys:
        for family_number_2 in new_familys:
            new_fusion_familys[f"{family_number_1}.{family_number_2}"] = PokedexFamily(
                family_number=f"{family_number_1}.{family_number_2}"
            )
        for family_number_2 in pokedex_familys:
            new_fusion_familys[f"{family_number_1}.{family_number_2}"] = PokedexFamily(
                family_number=f"{family_number_1}.{family_number_2}"
            )
    for family_number_1 in pokedex_familys:
        for family_number_2 in new_familys:
            new_fusion_familys[f"{family_number_1}.{family_number_2}"] = PokedexFamily(
                family_number=f"{family_number_1}.{family_number_2}"
            )
    for family in new_fusion_familys:
        print(family, end=', ')
            
    pokemon_to_add = []
    for pokemon in dex_additions:
        pokemon_1 = pokemon['obj']
        create_fusion(pokemon_1, pokemon_1, new_fusion_familys)
        for pokemon in dex_additions:
            pokemon_2 = pokemon['obj']
            if pokemon_1 != pokemon_2:
                create_fusion(pokemon_1, pokemon_2, new_fusion_familys)
        for pokemon_2 in old_dex.values():
            create_fusion(pokemon_1, pokemon_2, new_fusion_familys)
            create_fusion(pokemon_2, pokemon_1, new_fusion_familys)
        pokemon_to_add.append(pokemon_1)
    db.session.add_all(pokemon_to_add)
    db.session.commit()

    for pokemon in dex_additions:
        old_dex[pokemon['obj'].species] = pokemon

    working_pokedex = old_dex
    
    pokedex_lst_path = os.getenv('POKEDEX_HTML_PATH')
    with open(pokedex_lst_path, 'w') as pokedex_list:
        pokedex_list.write('<datalist id="pokedex">\n')
        for entry in working_pokedex:
            pokedex_list.write(f'    <option value="{entry}"></option>\n')
        pokedex_list.write("</datalist>")
    
    # logging_t0 = time.perf_counter()
    # # if not initial_upload:
    # #     with open(f"{POKEDEX_UPDATES_PATH}{start_time}_pokedex-updates.txt", 'w') as pokedex_updates_log:
    # #         master_logger_dict = {"POKEDEX ADDED":dex_additions, "POKEMON MOVED TO REMOVED DEX": dex_removals,
    # #                               "POKEMON DELETED":dex_deletions, "POKEDEX NUMBER UPDATED":pokedex_number_updates,
    # #                               "POKEDEX SPECIES UPDATED":species_updates,
    # #                               "POKEDEX NUMBER AND SPECIES UPDATED":pokedex_numbers_and_species_updates,
    # #                               "POKEDEX TYPE UPDATES":typing_to_update,
    # #                               "POKEDEX FAMILY ORDER UPDATES":family_orders_to_update,
    # #                               "POKEDEX NAMING SCHEMA UPDATES":naming_schema_to_update,
    # #                               "POKEDEX STATS UPDATES":stats_to_update}
    # #         for title, log in master_logger_dict.items():
    # #             pokedex_updates_log.write(f"{title}:\n")
    # #             write_into_logs(log, pokedex_updates_log)
    # logging_t1 = time.perf_counter()
    # pokedex_full_t1 = time.perf_counter()

    # print("RUN TIMES:")
    # print(f"Update Existing: {update_existing_t1 - update_existing_t0}")
    # print(f"Additions Check: {additions_checks_t1 - additions_checks_t0}")
    # print(f"Additions Add: {additions_add_t1 - additions_add_t0}")
    # print(f"Additions Commit: {additions_commit_t1 - additions_commit_t0}")
    # print(f"Logging: {logging_t1 - logging_t0}")
    # print(f"Pokedex Func Full: {pokedex_full_t1 - pokedex_full_t0}")

    return initial_upload


@func_logger
def delete_from_pokedex(pokedex_object):
    db.session.delete(pokedex_object)

@func_logger
def add_to_pokedex(pokedex_object):
    pass


@func_timer
def update_sprites_test(initial_upload):
    artist_query = db.session.scalars(db.select(Artist))
    artists = {artist.name: artist for artist in artist_query}
    
    artists_to_add = []
    if not 'japeal' in artists:
        artists_to_add.append(Artist(name='japeal'))
    with open(SPRITES_CREDITS_PATH, newline='', errors='ignore') as sprites_file:
        sprite_reader = csv.DictReader(sprites_file)
        for row in sprite_reader:
            artist_name = row['artist']
            if not artist_name in artists:
                artist = Artist(name=artist_name)
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

    with open(SPRITES_CREDITS_PATH, newline='', errors='ignore') as sprites_file:
        sprite_reader = csv.DictReader(sprites_file)
        for sprite in sprite_reader:
            sprite_code = sprite['sprite']
            artist = sprite['artist']
            sprite_group, pokedex_number, variant = sanitized_sprite_code(sprite_code)
            if sprite_group != None:
                pass
                





def update_sprites(initial_upload):
    # sprites_full_t0 = time.perf_counter()
    print("Adding Sprites and their Artists. . .\n")
    # artist_additions_t0 = time.perf_counter()
    artist_query = db.session.scalars(db.select(Artist))
    # artist_query = db.session.execute(db.select(Artist)).scalars()
    artists = {artist.name: artist for artist in artist_query}
    artists_to_add = []
    if not 'japeal' in artists:
        artists_to_add.append(Artist(name='japeal'))
    with open(SPRITES_CREDITS_PATH, newline='', errors='ignore') as sprites_file:
        sprite_reader = csv.DictReader(sprites_file)
        for row in sprite_reader:
            artist_name = row['artist']
            if not artist_name in artists:
                artist = Artist(name=artist_name)
                artists[artist_name] = artist
                artists_to_add.append(artist)
        db.session.add_all(artists_to_add)
    print("New Artists Added")
    # artist_additions_t1 = time.perf_counter()

    # get_lists_t0 = time.perf_counter()
    pokedex_full = get_db_pokedex('full', 'pokedex_number')
    pokedex_full_pokedex_numbers = {pokedex_number:'' for pokedex_number in pokedex_full}
    sprites_full = db.session.scalars(db.select(Sprite))
    sprites_dict = {sprite.sprite_code(): sprite for sprite in sprites_full}
    sprites_to_delete = sprites_dict.copy()
    sprites_to_add = []
    artist_changes = []
    new_sprites_dict = {}
    # get_lists_t1 = time.perf_counter()

    with open(SPRITES_CREDITS_PATH, newline='', errors='ignore') as sprites_file:
        sprite_reader = csv.DictReader(sprites_file)
        dna_dict = {'TRIPLE': [], 'INVALID NUMBER': [], 'INVALID VARIANT': [], 'DUPLICATE': []}
        dupe_check_dict = {}
        # sprite_credits_reader_t0 = time.perf_counter()
        for sprite in sprite_reader:
            sprite_code = sprite['sprite']
            if sprite_code in dupe_check_dict:
                dna_dict['DUPLICATE'].append(sprite)
                continue
            else:
                dupe_check_dict[sprite_code] = ''
            try:
                if sprites_dict[sprite_code].artists.name != sprite['artist']:
                    artist_changes.append(create_update_dict(sprites_dict[sprite_code].artists, 
                                                                artists[sprite['artist']], 
                                                                sprites_dict[sprite_code]))
                    # artist_changes[sprite_code] = {'id':sprites_dict[sprite_code].id, 'before':sprites_dict[sprite_code], 'after':artists[sprite['artist']]}
                    del sprites_to_delete[sprite_code]
                else:
                    del sprites_to_delete[sprite_code]   
            except KeyError:
                prepped_sprite = prep_pokedex_number(sprite_code)
                if prepped_sprite == 'TRIPLE' or prepped_sprite == 'INVALID NUMBER' or prepped_sprite == 'INVALID VARIANT':
                    dna_dict[prepped_sprite].append(sprite)
                    continue
                elif not prepped_sprite['pokedex_number'] in pokedex_full_pokedex_numbers:
                    dna_dict['INVALID NUMBER'].append(sprite)
                    continue
                else:
                    sprite_to_add = Sprite(variant_let=prepped_sprite['variant'], info=pokedex_full[prepped_sprite['pokedex_number']], 
                                            artists=artists[sprite['artist']])
                    sprites_to_add.append(sprite_to_add)
        # sprite_credits_reader_t1 = time.perf_counter()

        # update_artists_t0 = time.perf_counter()
        for updater_dict in artist_changes:
            updater_dict['obj'].artists = updater_dict['new']
        # update_artists_t1 = time.perf_counter()

        # delete_sprites_t0 = time.perf_counter()
        japeal = db.session.scalar(db.select(Artist).where(Artist.name=='japeal'))
        for sprite_code, sprite in sprites_to_delete.copy().items():
            if sprite.artists == japeal and sprite.info.pokedex_number in pokedex_full:
                del sprites_to_delete[sprite_code]
        for sprite_code, sprite in sprites_to_delete.items():
            db.session.delete(sprite)
        # delete_sprites_t1 = time.perf_counter()
        
        # sprites_additions_t0 = time.perf_counter()
        db.session.add_all(sprites_to_add)
        # sprites_additions_t1 = time.perf_counter()
    
    # autogen_sprites_t0 = time.perf_counter()
    japeal = db.session.scalar(db.select(Artist).where(Artist.name=='japeal'))
    pokedex_needs_sprites = db.session.execute(db.select(Pokedex).where(Pokedex.sprites==None)).scalars()
    japeal_sprites_to_add = []
    for entry in pokedex_needs_sprites:
        basic_sprite = Sprite(variant_let='', artists=japeal, info=entry)
        japeal_sprites_to_add.append(basic_sprite)
    db.session.add_all(japeal_sprites_to_add)
    autogen_sprites_t1 = time.perf_counter()

    # commits_t0 = time.perf_counter()
    db.session.commit()
    # commits_t1 = time.perf_counter()
    
    print("Logging Sprites")
    # if initial_upload == False:
    #     with open(f"{SPRITES_UPDATES_PATH}{start_time}_sprites-updates.txt", 'w') as sprites_updates_log:
    #         sprites_updates_log.write(f"SPRITES UPDATES - {start_time}\n\n")
    #         if len(sprites_to_add) > 0:
    #             sprites_updates_log.write(f"SPRITES ADDED:\n")
    #             for sprite in sprites_to_add:
    #                 sprites_updates_log.write(f"{sprite}\n")
    #         if len(sprites_to_delete) > 0:
    #             sprites_updates_log.write(f"SPRITES DELETED:\n")
    #             for sprite in sprites_to_delete:
    #                 sprites_updates_log.write(f"{sprite}\n")
    #         if len(dna_dict) > 0:
    #             sprites_updates_log.write(f"SPRITES NOT ADDED (DNA):\n")
    #             for reason, sprites in dna_dict.items():
    #                 sprites_updates_log.write(f"{reason}:\n")
    #                 for sprite in sprites:
    #                     sprites_updates_log.write(f"{sprite}\n")
            
    #     with open(f"{ARTISTS_UPDATES_PATH}{start_time}_artists-updates.txt", 'w') as artist_updates_log:
    #         artist_updates_log.write(f"ARTISTS UPDATES - {start_time}\n\n")
    #         if len(artists_to_add) > 0:
    #             artist_updates_log.write(f"ARTISTS ADDED:\n")
    #             for artist in artists_to_add:
    #                 artist_updates_log.write(f"{artist}\n")
    #         if len(artist_changes) > 0:
    #             artist_updates_log.write(f"ARTISTS CHANGES:\n")
    #             for artist_switch in artist_changes:
    #                 artist_updates_log.write(f"{artist_switch['obj']}: {artist_switch['old']} -> {artist_switch['new']}\n")

    # sprites_full_t1 = time.perf_counter()

    # print("RUN TIMES:")
    # print(f"Artist Additions: {artist_additions_t1 - artist_additions_t0}")
    # print(f"Get Lists: {get_lists_t1 - get_lists_t0}")
    # print(f"Sprite Credits Reader: {sprite_credits_reader_t1 - sprite_credits_reader_t0}")
    # print(f"Update Artists: {update_artists_t1 - update_artists_t0}")
    # print(f"Delete Sprites: {delete_sprites_t1 - delete_sprites_t0}")
    # print(f"Sprite Additions: {sprites_additions_t1 - sprites_additions_t0}")
    # print(f"Autogen Sprites: {autogen_sprites_t1 - autogen_sprites_t0}")
    # print(f"Final Commit: {commits_t1 - commits_t0}")
    # print(f"Sprites Func Full: {sprites_full_t1 - sprites_full_t0}")


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
    # db.session.execute(db.delete(RouteList))
    routes_html_path = os.getenv('ROUTES_HTML_PATH')
    new_routes_lst = []
    old_routes_lst = {route.name:'' for route in db.session.scalars(db.select(RouteList))}
    # with open(ROUTES_LIST_PATH, newline='', errors='ignore') as routes_file, open(routes_html_path, 'w') as routes_html:
    #     reader = csv.DictReader(routes_file)
    #     for row in reader:
    #         route_name = row['route']
    #         if route_name not in old_routes_lst:
    #             new_routes_lst.append({'name':route_name})
            
    # if len(new_routes_lst) > 0:
    #     db.session.execute(insert(RouteList), new_routes_lst)
    #     db.session.commit()

    with open(ROUTES_LIST_PATH, newline='', errors='ignore') as routes_file:
        reader = csv.DictReader(routes_file)
        for row in reader:
            route_name = row['route']
            if route_name not in old_routes_lst:
                db.session.add(
                    RouteList(name=route_name)
                )
    db.session.commit()
    new_routes_lst = db.session.scalars(db.select(RouteList).order_by(RouteList.name))
    with open(routes_html_path, 'w') as routes_html:
        for route in new_routes_lst:
            routes_html.write(f'<option value="{route.id}">{route.name}</option>\n')


def prompt_continue():
    continue_ans = ''
    while not continue_ans in ["y", "n"]:
        continue_ans = input("Continue with the above changes [Y / N]? ").lower()
    print("")
    if continue_ans == "n":
        print("UPDATER CANCELED\n")
        exit()
    

def sanitize_sprite_code(sprite_code):
    split_sprite_code = sprite_code.split('.')
    
    # Check for Triple+ fusions
    if len(split_sprite_code) >= 3:
        return None, 'TRIPLE+ FUSION', None
    
    # Check for fusion or not
    sprite_group = split_sprite_code[0]
    if len(split_sprite_code) >= 2:
        return 'FUSION'
        # Check if variants are anywhere except at the end of the string
        for pokedex_number in split_sprite_code[:-1]:
            stripped_pokedex_number = pokedex_number.rstrip(alphabet)
            if len(stripped_pokedex_number) < len(pokedex_number):
                return None, 'ERROR: EXTRA VARIANT(S)', None
        # Remove and store variant letter from last number
        last_number = split_sprite_code[-1]
        stripped_last_number = last_number.rstrip(alphabet)
        variant = last_number[len(stripped_last_number):]
        split_sprite_code[-1] = stripped_last_number
        recombined_number = '.'.join(split_sprite_code)
        return sprite_group, recombined_number, variant
        
    else:
        return 'BASE'
        stripped_sprite_group = sprite_group.rstrip(alphabet)
        variant = sprite_group[len(stripped_sprite_group)]
        recombined_number = '.'.join(split_sprite_code)
        return stripped_sprite_group, stripped_sprite_group, variant



def prep_pokedex_number(sprite):
    prepped_pokedex_number_dict = {}
    try:
        pokedex_number, variant = split_sprite_code(sprite)
    except ValueError:
        return 'INVALID VARIANT'
    split_pokedex_number = pokedex_number.split('.')
    if '' in split_pokedex_number or len(split_pokedex_number) > 3:
        return 'INVALID NUMBER'
    elif len(split_pokedex_number) == 3:
        return 'TRIPLE'
    else:
        prepped_pokedex_number_dict['pokedex_number'] = pokedex_number
    prepped_pokedex_number_dict['variant'] = variant
    return prepped_pokedex_number_dict


def split_sprite_code(s):
    pokedex_number = s.rstrip('abcdefghijklmnopqrstuvwxyz')
    variant = s[len(pokedex_number):]
    if len(variant) > 2:
        raise ValueError("Variant letter length greater than 2")
    return pokedex_number, variant        



def update_family_order(family_orders_to_update):
    for pokemon in family_orders_to_update:
        pokemon['obj'].family_order = pokemon['new']
    for pokemon in family_orders_to_update:
        head_fusions_to_update = pokemon['obj'].fusions_head
        body_fusions_to_update = pokemon['obj'].fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            fusion.family_order = f"{fusion.head_pokemon.family_order}.{fusion.body_pokemon.family_order}"


def update_stats(stats_to_update):
    for pokemon in stats_to_update:
        new_stats = pokemon['new']
        old_stats = pokemon['obj'].stats
        old_stats.hp, old_stats.attack, old_stats.defense, \
        old_stats.sp_attack, old_stats.sp_defense, old_stats.speed = \
        new_stats.hp, new_stats.attack, new_stats.defense, \
        new_stats.sp_attack, new_stats.sp_defense, new_stats.speed
    for pokemon in stats_to_update:
        head_fusions_to_update = pokemon['obj'].fusions_head
        body_fusions_to_update = pokemon['obj'].fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            fusion.stats.hp = int(2 * fusion.head_pokemon.stats.hp/3 + fusion.body_pokemon.stats.hp/3)
            fusion.stats.attack = int(2 * fusion.body_pokemon.stats.attack/3 + fusion.head_pokemon.stats.attack/3)
            fusion.stats.defense = int(2 * fusion.body_pokemon.stats.defense/3 + fusion.head_pokemon.stats.defense/3)
            fusion.stats.sp_attack = int(2 * fusion.head_pokemon.stats.sp_attack/3 + fusion.body_pokemon.stats.sp_attack/3)
            fusion.stats.sp_defense = int(2 * fusion.head_pokemon.stats.sp_defense/3 + fusion.body_pokemon.stats.sp_defense/3)
            fusion.stats.speed = int(2 * fusion.body_pokemon.stats.speed/3 + fusion.head_pokemon.stats.speed/3)


def update_typing(typing_to_update):
    for pokemon in typing_to_update:
        pokemon['obj'].type_primary = pokemon['new']['type_primary']
        pokemon['obj'].type_secondary = pokemon['new']['type_secondary']
    for pokemon in typing_to_update:
        head_fusions_to_update = pokemon['obj'].fusions_head
        body_fusions_to_update = pokemon['obj'].fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            type_primary, type_secondary = create_fusion_typing(fusion.head_pokemon, fusion.body_pokemon)
            fusion.type_primary = type_primary
            fusion.type_secondary = type_secondary


def update_naming(naming_schema_to_update):
    for pokemon in naming_schema_to_update:
        pokemon['obj'].name_1 = pokemon['new']['name_1']
        pokemon['obj'].name_2 = pokemon['new']['name_2']
    for pokemon in naming_schema_to_update:
        head_fusions_to_update = pokemon['obj'].fusions_head
        body_fusions_to_update = pokemon['obj'].fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            fusion.species = create_fusion_species(fusion.head_pokemon.name_1, fusion.body_pokemon.name_2)


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


def create_update_dict(old, new, obj):
    return {'old':old, 'new':new, 'obj':obj}


def write_into_logs(updater_arr, file):
    for pokemon in updater_arr:
        file.write(f"{pokemon['obj']}\n{pokemon['old']} -> {pokemon['new']}\n")

    
def pokedex_number_change_all(pokedex_number_updates) -> None:
    updater_dict = {_dict['new']:_dict['obj'] for _dict in pokedex_number_updates}
    while len(updater_dict) > 0:
        new = list(updater_dict)[0]
        updater_dict = recursive_pokedex_number_change(starter_pokedex_number=new, 
                                        check_pokedex_number=new,
                                        updater_dict=updater_dict)


def recursive_pokedex_number_change(starter_pokedex_number, check_pokedex_number, updater_dict):
    try:
        next_check = next(key for key, value in updater_dict.items() if value.pokedex_number == check_pokedex_number)
        if next_check == starter_pokedex_number:
            update_pokedex_number_in_db(TMP_NUM, updater_dict[starter_pokedex_number])
            updater_dict[starter_pokedex_number].pokedex_number = TMP_NUM
        else:
            updater_dict = recursive_pokedex_number_change(starter_pokedex_number, next_check, updater_dict)
    except StopIteration:
        pass

    update_pokedex_number_in_db(check_pokedex_number, updater_dict[check_pokedex_number])
    updater_dict.pop(check_pokedex_number)

    return updater_dict

    
def update_pokedex_number_in_db(new, obj) -> None:
    pokemon = obj
    pokemon.pokedex_number = new
    if pokemon.family_order == '1':
        evolutions = pokemon.evolutions()
        for evo in evolutions:
            evo.family = new
            fusions = evo.fusions_head + evo.fusions_body
            for fusion in fusions:
                fusion.pokedex_number = f"{fusion.head_pokemon.pokedex_number}.{fusion.body_pokemon.pokedex_number}"
                fusion.family = f"{fusion.head_pokemon.family}.{fusion.body_pokemon.family}"
    else:
        fusions = pokemon.fusions_head + pokemon.fusions_body
        for fusion in fusions:
            fusion.pokedex_number = f"{fusion.head_pokemon.pokedex_number}.{fusion.body_pokemon.pokedex_number}"


def sanitised_input(prompt, type_=None, min_=None, max_=None, range_=None):
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
        pokemon.evolution_family.family_number = new
        first_fusions = db.session.scalars(db.session.select(Pokedex).where(
            or_(Pokedex.head_pokemon==pokemon, Pokedex.body_pokemon==pokemon), 
            Pokedex.family_order=='1.1'
        ))
        for fusion in first_fusions:
            new_fusion_family_number = f"{fusion.head_pokemon.evolution_family.family_number}.{fusion.body_pokemon.evolution_family.family_number}"
            fusion.evolution_family.family_number = new_fusion_family_number


def create_fusion_pokedex_number(head_pokemon, body_pokemon, fusion_to_update=None):
    pokedex_number_1 = head_pokemon.pokedex_number
    pokedex_number_2 = body_pokemon.pokedex_number
    fusion_pokedex_number = f"{pokedex_number_1}.{pokedex_number_2}"
    if fusion_to_update:
        fusion_to_update.pokedex_number = fusion_pokedex_number
        if fusion_to_update.family_order == '1.1':
            fusion_to_update.evolution_family.family_number = fusion_to_update.pokedex_number
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
    family_1 = head_pokemon.evolution_family.family_number
    family_2 = body_pokemon.evolution_family.family_number
    fusion_family_number = f"{family_1}.{family_2}"
    if fusion_to_update:
        fusion_to_update.evolution_family.family_number = fusion_family_number
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
        fusion.stats.hp = hp
        fusion.stats.attack = attack
        fusion.stats.defense = defense
        fusion.stats.sp_attack = sp_attack
        fusion.stats.sp_defense = sp_defense
        fusion.stats.speed = speed
        return fusion
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


def create_fusion(head_pokemon, body_pokemon):
    pokedex_number = create_fusion_pokedex_number(head_pokemon, body_pokemon)
    type_primary, type_secondary = create_fusion_typing(head_pokemon, body_pokemon)
    stats = create_fusion_stats(head_pokemon, body_pokemon)
    species = create_fusion_species(head_pokemon, body_pokemon)
    family_number = create_fusion_family_number(head_pokemon, body_pokemon)
    family_order = create_fusion_family_order(head_pokemon, body_pokemon)
    try:
        evolution_family = family_dict[family_number]
    except KeyError:
        evolution_family = PokedexFamily(
            family_number = family_number
        )
        family_dict[family_number] = evolution_family
    fusion = Pokedex(
        pokedex_number=pokedex_number,
        species=species,
        type_primary=type_primary,
        type_secondary=type_secondary,
        family=family_number,
        family_order=family_order,
        evolution_family=evolution_family,
        head_pokemon=head_pokemon,
        body_pokemon=body_pokemon,
        stats=stats
    )
    db.session.add(fusion)
    return fusion



if __name__ == "__main__":
    main()