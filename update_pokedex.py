import csv
import os
import sys
import shutil
import subprocess

from datetime import datetime
from dotenv import load_dotenv
from myproject import create_app
from myproject.models import Pokedex, PokedexStats, Sprite, Artist
from myproject.extensions import db
from sqlalchemy import create_engine, text
import time

app = create_app()
PASS_LST = ['450_1']

# Path Variables
BASE_DEX_CSV_PATH = 'pokedex_stuff/pokedexes/if-base-dex.csv'
SPRITES_CREDITS_PATH = 'pokedex_stuff/sprite_credits/Sprite Credits.csv'

REMOVED_DEX_CSV_PATH = 'pokedex_stuff/pokedexes/removed-dex.csv'
POKEDEX_UPDATES_PATH = 'pokedex_stuff/logs/pokedex_updates/'
ARTISTS_UPDATES_PATH = 'pokedex_stuff/logs/artists_updates/'
SPRITES_UPDATES_PATH = 'pokedex_stuff/logs/sprites_updates/'

# Constants
TMP_NUM = '000'
STATS_LIST = ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']


# Load ENV variables
load_dotenv()

def main() -> None:
    with app.app_context():
        # Program start time
        START_TIME =  datetime.now().strftime('%Y-%b-%d_T%H-%M-%S')
        full_time_t0 = time.perf_counter()
        # Checks for Duplicates
        new_pokedex = {}
        new_pokedex_stats = {}
        duplicates= {}
        new_pokedex_numbers = {}
        pokedex_stats_dict = {}
        with open(BASE_DEX_CSV_PATH, newline='') as dexfile, open(REMOVED_DEX_CSV_PATH, newline='') as rdexfile:
            dexreader = csv.DictReader(dexfile)
            rdexreader = csv.DictReader(rdexfile)
            for dex in [dexreader, rdexreader]:
                for row in dex:
                    number, species = row['number'], row['species']
                    if species in new_pokedex:
                        print(f"DUPLICATE NAME FOUND: [{number} - {species}] -> [{new_pokedex[species].number} - {species}]\nPLEASE ADDRESS DUPLICATE NAME FROM 'if-base-dex.csv'")
                        exit()
                    if number in duplicates: 
                        print(f"DUPLICATE FOUND: {number}\nPLEASE REMOVE DUPLICATE FROM 'if-base-dex.csv'")
                        exit()
                    duplicates[number] = ''
                    new_pokedex[species] = {}
                    new_pokedex[species] = Pokedex(number=number, species=species, type_primary=row['type_primary'], 
                                                       type_secondary=row['type_secondary'], family=row['family'], family_order=row['family_order'], 
                                                       name_1=row['name_1'], name_2=row['name_2'])
                    new_pokedex_stats[species] = PokedexStats(info=new_pokedex[species], hp=int(row['hp']), attack=int(row['attack']), 
                                                         defense=int(row['defense']), sp_attack=int(row['sp_attack']), 
                                                         sp_defense=int(row['sp_defense']), speed=int(row['speed']))
                    new_pokedex_numbers[number] = [species]
        old_pokedex_query, old_pokedex = get_db_pokedex('base', 'species')
        old_pokedex_nums = {entry.number:entry.species for entry in old_pokedex_query}
        pokedex_to_remove = {}
        species_to_update = {}
        numbers_to_change = {}
        new_species_to_add = {}
        numbers_and_species_to_change = {}
        pokedex_to_delete = {}

        tmp_numbers_to_change = []
        
        # Only manual part of the program. When a name from the previous pokedex is not detected in the new pokedex, 
        # admin needs to determine whether this is simply a name being updated to a correct name, or if the pokemon should actually be deleted/removed
        # from the pokedex

        # CHECKS FOR ANY CHANGES IN NUMBERS OR SPECIES BETWEEN OLD AND NEW POKEDEXES
        if len(old_pokedex) > 0:
            for new_species, new_pokedex_entry in new_pokedex.items(): 
                print(f"[{new_pokedex_entry.number} - {new_species}]", end=' ')
            print("\n")
            for old_species, old_pokedex_entry in old_pokedex.copy().items():
                if old_species in new_pokedex:
                    if old_pokedex[old_species].number != new_pokedex[old_species].number:
                        numbers_to_change[old_pokedex_entry.number] = new_pokedex[old_species].number
                elif not 'r' in old_pokedex_entry.number:
                    replacement_species = False
                    if old_pokedex_entry.number in new_pokedex_numbers:
                        replacement_species = new_pokedex_numbers[old_pokedex_entry.number] 
                    answer_1 = ''
                    if replacement_species:
                        while not answer_1 in ["r", "u", "c"]:
                            answer_1 = input(f" Should [{old_pokedex[old_species].number} - {old_species.upper()}] be removed or \
                                             species name updated to [{old_pokedex_entry.number} - {replacement_species.upper()}] or \
                                             number and species changed? [R (removed) / U (name updated) / C (number and species change)] ").lower()
                    else:
                        while not answer_1 in ["r", "c"]:
                            answer_1 = input(f" Should [{old_pokedex[old_species].number} - {old_species.upper()}] be removed or \
                                             number and species changed? [R (removed) / C (number and species change)] ").lower()
                    print("")
                    if answer_1 == "u":
                        species_to_update[old_pokedex_entry.species] = replacement_species
                    elif answer_1 == "r":
                        pokedex_to_remove[old_pokedex_entry.number] = old_species
                    else:
                        answer_2 = ''
                        while not answer_2 in old_pokedex_nums:
                            answer_2 = input(f" Please specify which pokedex number + species combo that \
                                             [{old_pokedex_entry.number} - {old_species.upper()}] should be updated to: ")
                        print("\n")
                        numbers_and_species_to_change[old_pokedex_entry.number] = {answer_2:old_pokedex_nums[answer_2]}
                else:
                    pokedex_to_delete[old_pokedex_entry.number] = ''
                
            print(f"Pokemon to be added to Removed Dex:\n{pokedex_to_remove}")
            print(f"Pokemon whose species name need to be updated to a new species name:\n{species_to_update}")
            print(f"Pokemon whose number needs to be updated to a new number:\n{numbers_to_change}")
            print(f"Pokemon to be deleted:\n{pokedex_to_delete}")
        else:
            print("Initial Pokedex Upload")

        continue_with_changes()

        # BACKUP DATABASE
        backup_question = input('Backup Database [y/n]? ')
        if backup_question == 'y':
            db_backup_filename = 'pifsm_db_' + datetime.now().strftime('%Y-%b-%d_T%H-%M-%S') + '.sql'
            subprocess.run(f"mysqldump -u root -p pif_game_manager > {os.getenv('DB_BACKUP_PATH')}{db_backup_filename}", shell=True)
        
        if len(pokedex_to_remove) > 0:
            print(f"Adding {pokedex_to_remove} to the Removed Pokedex\n")
            with open(REMOVED_DEX_CSV_PATH, 'a') as removeddex:
                for number in pokedex_to_remove:
                    pokemon_to_remove = db.session.execute(db.select(Pokedex).where(Pokedex.number==number)).scalar()
                    pokemon_to_remove.number = number + 'r'
                    removeddex.write(f"{pokemon_to_remove.number},{pokemon_to_remove.species},"
                                     f"{pokemon_to_remove.type_primary},{pokemon_to_remove.type_secondary},"
                                     f"{pokemon_to_remove.name_1},{pokemon_to_remove.name_2},"
                                     f"{pokemon_to_remove.family},{pokemon_to_remove.family_order},"
                                     f"{pokemon_to_remove.stats.hp},{pokemon_to_remove.stats.attack},"
                                     f"{pokemon_to_remove.stats.defense},{pokemon_to_remove.stats.sp_attack},"
                                     f"{pokemon_to_remove.stats.sp_defense},{pokemon_to_remove.stats.speed}\n")
                db.session.commit()
        if len(species_to_update) > 0:
            print(f"Updating the following pokedex entries {species_to_update}\n")
            for old_species, new_species in species_to_update.items():
                entry_update_species = db.session.execute(db.select(Pokedex).where(Pokedex.species==old_species, Pokedex.head==None)).scalar()
                entry_update_species.species = new_species
            db.session.commit()
        if len(numbers_to_change) > 0:
            print(f"Updating the following numbers {numbers_to_change}\n")
            number_change_all(numbers_to_change.copy())

        # UPDATE HERE
        if len(numbers_and_species_to_change) > 0:
            print(f"Updating the following numbers and species {numbers_and_species_to_change}\n")
            for number, new in numbers_and_species_to_change.items():
                for new_number, new_species in new.items():
                    pokemon_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==new_species)).scalar()
                    new_number = db.session.scalar(db.select(Pokedex).where(Pokedex.number==new_number))
                    pokemon_to_update.number = new_number
                    pokemon_to_update.species = new_species
            db.session.commit()   
        
        print("Checking for any updated Pokedex Entry info . . .\n")
        new_family_order_arr, new_stats_arr, new_type_arr, new_naming_arr = [], [], [], []
        for old_species in old_pokedex:
            if old_species in new_pokedex:
                new_entry, old_entry = new_pokedex[old_species], old_pokedex[old_species]
                if not new_entry.__eq__(old_entry, 'family_order'):
                    new_family_order_arr.append(old_species)
                for stat in STATS_LIST:
                    if not new_entry.stats.__eq__(old_entry.stats, stat):
                        new_stats_arr.append(old_species)
                        break
                if not new_entry.__eq__(old_entry, 'type_primary', 'type_secondary'):
                    new_type_arr.append(old_species)
                if not new_entry.__eq__(old_entry, 'name_1', 'name_2'):
                    new_naming_arr.append(old_species)

        print(f"Pokedex Numbers that require info updates:\n"
              f"Stats: {new_stats_arr}\n"
              f"Typing: {new_type_arr}\n"
              f"Family Order: {new_family_order_arr}\n"
              f"Naming Scheme: {new_naming_arr}\n")
        update_stats(new_stats_arr, new_pokedex)
        update_typing(new_type_arr, new_pokedex)
        update_family_order(new_family_order_arr, new_pokedex)
        update_naming(new_naming_arr, new_pokedex)

        print("Pokedex info updates completed")

        # if len(new_stats_arr) > 0:
        #     print(f"Updating stats for Base + Fusions for the following Pokedex numbers: {new_stats_arr}")
            
        #     print(f"stats updated for Base + Fusions")
        # if len(new_family_order_arr) > 0:
        #     print(f"Updating family_order for Base + Fusions for the following Pokedex numbers: {new_family_order_arr}")
            
        #     print(f"family_orders udpated for Base + Fusions")
        # if len(new_type_arr) > 0:
        #     print(f"Updating typing for the following Pokedex numbers: {new_type_arr}")
            
        #     print(f"typing updated for Base + Fusions")
        # if len(new_naming_arr) > 0:
        #     print(f"Updating Species Names for Base + Fusions for following Pokedex entries: {new_naming_arr}")
           
        #     print(f"species updated for Base + Fusions")
        # print("Existing Pokedex updated!")

        print("Checking for any new Pokemon. . .")
        old_pokedex_query, old_pokedex = get_db_pokedex('base', 'species')
        for new_species, pokemon in new_pokedex.items():
            if not new_species in old_pokedex:
                new_species_to_add[new_species] = pokemon
        if len(new_species_to_add) > 0:
            print(f"New Pokemon found {new_species_to_add.keys()}\n")
        else:
            print("No new pokemon found\n")
        continue_with_changes()
        pokemon_to_add, stats_to_add = [], []
        pokedex_base, pokedex_base_dict = get_db_pokedex('base', 'species')
        for species_1, pokemon_1 in new_species_to_add.items():
            db.session.add(pokemon_1)
            db.session.add(new_pokedex_stats[species_1])
            fusion, stats = create_fusion(pokemon_1, pokemon_1)
            db.session.add(fusion)
            db.session.add(stats)
            for pokemon_2 in new_species_to_add.values():
                if pokemon_1 != pokemon_2:
                    fusion, stats = create_fusion(pokemon_1, pokemon_2)
                    pokemon_to_add.append(fusion)
                    stats_to_add.append(stats)
            for pokemon_2 in pokedex_base:
                print(pokemon_1)
                print(pokemon_2)
                fusion, stats = create_fusion(pokemon_1, pokemon_2)
                pokemon_to_add.append(fusion)
                stats_to_add.append(stats)
                fusion_inv, stats_inv = create_fusion(pokemon_2, pokemon_1)
                pokemon_to_add.append(fusion_inv)
                stats_to_add.append(stats_inv)
        db.session.add_all(pokemon_to_add)
        db.session.add_all(stats_to_add)
        db.session.commit()

        pokedex_base, pokedex_base_dict = get_db_pokedex('base')
        pokedex_lst_path = os.getenv('POKEDEX_HTML_PATH')
        with open(pokedex_lst_path, 'w') as pokedex_list:
            pokedex_list.write('<datalist id="pokedex">\n')
            for entry in pokedex_base:
                pokedex_list.write(f'    <option value="{entry.species}"></option>\n')
            pokedex_list.write("</datalist>")
        
        print("Adding Sprites and their Artists. . .\n")
        artist_query = db.session.execute(db.select(Artist)).scalars()
        artists = {artist.name: None for artist in artist_query}
        artists_to_add = []
        if not 'japeal' in artists:
            artists_to_add.append(Artist(name='japeal'))
        with open(SPRITES_CREDITS_PATH, newline='', errors='ignore') as sprites_file:
            sprite_reader = csv.DictReader(sprites_file)
            for row in sprite_reader:
                artist = row['artist']
                if not artist in artists:
                    artists[artist] = None
                    artists_to_add.append(Artist(name=artist))
            db.session.add_all(artists_to_add)
            db.session.commit()
        print("New Artists Added")

        pokedex_full, pokedex_full_dict = get_db_pokedex('full', 'number')
        artist_full = db.session.execute(db.select(Artist)).scalars()
        artist_full_dict = {artist.name: artist for artist in artist_full}
        sprites_full = db.session.execute(db.select(Sprite)).scalars()
        sprites_full_dict = {sprite.sprite_code(): sprite for sprite in sprites_full}
        sprites_to_delete = sprites_full_dict.copy()
        sprites_to_add = []
        artist_changes = {}

        with open(SPRITES_CREDITS_PATH, newline='', errors='ignore') as sprites_file:
            sprite_reader = csv.DictReader(sprites_file)
            dna_dict = {'TRIPLE': [], 'INVALID NUMBER': [], 'INVALID VARIANT': [], 'DUPLICATE': []}
            dupe_check_dict = {}
            for sprite in sprite_reader:
                sprite_code = sprite['sprite']
                if sprite_code in dupe_check_dict:
                    dna_dict['DUPLICATE'].append(sprite)
                    continue
                else:
                    dupe_check_dict[sprite_code] = ''
                try:
                    if sprites_full_dict[sprite_code].artists.name != sprite['artist']:
                        print(sprite_code, sprites_full_dict[sprite_code], sprite['artist'])
                        artist_changes[sprite_code] = {'id':sprites_full_dict[sprite_code].id, 'before':sprites_full_dict[sprite_code], 'after':artist_full_dict[sprite['artist']]}
                        del sprites_to_delete[sprite_code]
                    else:
                        del sprites_to_delete[sprite_code]   
                except KeyError:
                    prepped_sprite = prep_number(sprite_code)
                    if prepped_sprite == 'TRIPLE' or prepped_sprite == 'INVALID NUMBER' or prepped_sprite == 'INVALID VARIANT':
                        dna_dict[prepped_sprite].append(sprite)
                        continue
                    elif not prepped_sprite['number'] in pokedex_full_dict:
                        dna_dict['INVALID NUMBER'].append(sprite)
                        continue
                    else:
                        sprite_to_add = Sprite(variant_let=prepped_sprite['variant'], info=pokedex_full_dict[prepped_sprite['number']], 
                                                artists=artist_full_dict[sprite['artist']])
                        sprites_to_add.append(sprite_to_add)

            print(f"Artists to Change: {artist_changes}")
            for sprite_code, sprite in artist_changes.items():
                artist_to_change = db.session.scalar(db.select(Sprite).where(Sprite.id==sprite['id']))
                artist_to_change.artists = sprite['after']
            db.session.commit()

            japeal = db.session.scalar(db.select(Artist).where(Artist.name=='japeal'))
            for sprite_code, sprite in sprites_to_delete.copy().items():
                if sprite.artists == japeal and sprite.number in pokedex_full_dict:
                    del sprites_to_delete[sprite_code]
            
            print(f"Sprites Deleted: {sprites_to_delete}")
            for sprite_code, sprite in sprites_to_delete.items():
                db.session.delete(sprite)
            
            print(f"Number of Sprites Added {sprites_to_add}")
            db.session.add_all(sprites_to_add)
            db.session.commit()
        
        japeal = db.session.scalar(db.select(Artist).where(Artist.name=='japeal'))
        pokedex_needs_sprites = db.session.execute(db.select(Pokedex).where(Pokedex.sprites==None)).scalars()
        japeal_sprites_to_add = []
        for entry in pokedex_needs_sprites:
            basic_sprite = Sprite(variant_let='', artists=japeal, number=entry)
            japeal_sprites_to_add.append(basic_sprite)
        db.session.add_all(japeal_sprites_to_add)
        db.session.commit()
        
        full_time_t1 = time.perf_counter()

        with open(f"{SPRITES_UPDATES_PATH}{START_TIME}_sprites-updates.txt", 'w') as sprites_updates_log:
            sprites_updates_log.write(f"SPRITES UPDATES - {START_TIME}\n\n")
            if len(sprites_to_add) > 0:
                sprites_updates_log.write(f"SPRITES ADDED:\n")
                for sprite in sprites_to_add:
                    sprites_updates_log.write(f"{sprite}\n")
            if len(sprites_to_delete) > 0:
                sprites_updates_log.write(f"SPRITES DELETED:\n")
                for sprite in sprites_to_delete:
                    sprites_updates_log.write(f"{sprite}\n")
            if len(dna_dict) > 0:
                sprites_updates_log.write(f"SPRITES NOT ADDED (DNA):\n")
                for reason, sprites in dna_dict.items():
                    sprites_updates_log.write(f"{reason}:\n")
                    for sprite in sprites:
                        sprites_updates_log.write(f"{sprite}\n")
            
        with open(f"{ARTISTS_UPDATES_PATH}{START_TIME}_artists-updates.txt", 'w') as artist_updates_log:
            artist_updates_log.write(f"ARTISTS UPDATES - {START_TIME}\n\n")
            if len(artists_to_add) > 0:
                artist_updates_log.write(f"ARTISTS ADDED:\n")
                for artist in artists_to_add:
                    artist_updates_log.write(f"{artist}\n")
            if len(artist_changes) > 0:
                artist_updates_log.write(f"ARTISTS CHANGES:\n")
                for sprite_code, artist_switch in artist_changes.items():
                    artist_updates_log.write(f"{sprite_code}: {artist_switch['before']} -> {artist_switch['after']}\n")

        with open(f"{POKEDEX_UPDATES_PATH}{START_TIME}_pokedex-updates.txt", 'w') as pokedex_updates_log:
            pokedex_updates_log.write(f"POKEDEX UPDATES - {START_TIME}\n")
            pokedex_updates_log.write(f"POKEMON ADDED:\n")
            pokedex_updates_log.write(f"POKEMON MOVED TO REMOVED DEX:\n")
            pokedex_updates_log.write(f"POKEMON DELETED:\n")
            pokedex_updates_log.write(f"POKEDEX NUMBER CHANGES:\n")
            pokedex_updates_log.write(f"POKEDEX SPECIES UPDATES:\n")
            pokedex_updates_log.write(f"POKEDEX NUMBER AND SPECIES CHANGES:\n")
            pokedex_updates_log.write(f"POKEDEX TYPE CHANGES\n")
        print(f"FULL TIME: {full_time_t1-full_time_t0} s")

        exit()
        # Move sprites to sprites directory
        confirm_sprite_additions = input("ADD NEW SPRITES [y/n]? ")
        if confirm_sprite_additions == 'y':
            # new_sprites_path = input("ENTER PATH OF NEW SPRITES: ")
            new_sprites_path = input("Input sprite folder to upload: ")
            
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


def continue_with_changes():
    continue_ans = ''
    while not continue_ans in ["y", "n"]:
        continue_ans = input("Continue with the above changes [Y / N]? ").lower()
    if continue_ans == "n":
        print("UPDATER CANCELED\n")
        exit()


def create_fusion_typing(pokemon_1, pokemon_2):
    # If pokemon is a Normal/Flying primary typing needs to be Flying
    if pokemon_1.type_primary == 'Normal' and pokemon_1.type_secondary == 'Flying':
        fusion_type_primary = pokemon_1.type_secondary
    else:
        fusion_type_primary = pokemon_1.type_primary
    # As of version 6.0 of Infinite Fusion some pokemon no longer has a dominant typing
    # if pokemon_2['number'] in FUSION_EXCEPTIONS:
    #     fusion_type_secondary = pokemon_2["type_primary"]
    # If body Pokemon only has one type, the secondary typing of the new fused pokemon uses the primary typing of the body Pokemon
    if pokemon_2.type_secondary == "":
        fusion_type_secondary = pokemon_2.type_primary
    # If the body Pokemon's secondary type is the same as the head Pokemon's primary type, the body Pokemon's primary type is instead used for the fused Pokemon's secondary type
    elif pokemon_2.type_secondary == fusion_type_primary:
        fusion_type_secondary = pokemon_2.type_primary
    # If none of the above apply then the fused Pokemon's secondary type is the body Pokemon's secondary type. 
    else:
        fusion_type_secondary = pokemon_2.type_secondary
    # If the newly fused Pokemon has two typings that are the same, the secondary typing is removed
    if fusion_type_secondary == fusion_type_primary:
        fusion_type_secondary = ""

    return fusion_type_primary, fusion_type_secondary


def create_fusion_species(name_1, name_2):
    if name_1[-1] == name_2[0]:
        species = name_1 + name_2[1:]
    else:
        species = name_1 + name_2
    return species


def create_fusion_stats(pokemon_1, pokemon_2):
    fused_stats = PokedexStats(hp=int(2 * (pokemon_1.stats.hp)/3 + (pokemon_2.stats.hp)/3),
                          attack=int(2 * (pokemon_2.stats.attack)/3 + (pokemon_1.stats.attack)/3),
                          defense=int(2 * (pokemon_2.stats.defense)/3 + (pokemon_1.stats.defense)/3),
                          sp_attack=int(2 * pokemon_1.stats.sp_attack/3 + pokemon_2.stats.sp_attack/3),
                          sp_defense=int(2 * pokemon_1.stats.sp_defense/3 + pokemon_2.stats.sp_defense/3),
                          speed=int(2 * pokemon_2.stats.speed/3 + pokemon_1.stats.speed/3))
    return fused_stats


def prep_number(sprite):
    prepped_number_dict = {}
    try:
        number, variant = split_sprite_code(sprite)
    except ValueError:
        return 'INVALID VARIANT'
    split_number = number.split('.')
    if '' in split_number or len(split_number) > 3:
        return 'INVALID NUMBER'
    elif len(split_number) == 3:
        return 'TRIPLE'
    else:
        prepped_number_dict['number'] = number
    prepped_number_dict['variant'] = variant
    return prepped_number_dict


def split_sprite_code(s):
    number = s.rstrip('abcdefghijklmnopqrstuvwxyz')
    variant = s[len(number):]
    if len(variant) > 2:
        raise ValueError("Variant letter length greater than 2")
    return number, variant        


def create_fusion(head_pokemon, body_pokemon):
    type_primary, type_secondary = create_fusion_typing(head_pokemon, body_pokemon)
    fused_stats = create_fusion_stats(head_pokemon, body_pokemon)
    fused_species = create_fusion_species(head_pokemon.name_1, body_pokemon.name_2)
    fusion = Pokedex(number=f"{head_pokemon.number}.{body_pokemon.number}", species=fused_species,
                     type_primary=type_primary, type_secondary=type_secondary,
                     head=head_pokemon, body=body_pokemon, family=f"{head_pokemon.family}.{body_pokemon.family}",
                     family_order=f"{head_pokemon.family_order}.{body_pokemon.family_order}",
                     stats=fused_stats)
    return fusion, fused_stats


def number_change_all(numbers_to_change) -> None:
    while len(numbers_to_change) > 0:
        for old_number, new_number in numbers_to_change.copy().items():
            if new_number in numbers_to_change:
                numbers_to_change = recursive_number_change(starter_number=old_number, 
                                                            saved_number=False, 
                                                            numbers_to_change=numbers_to_change)
                break
            else:
                number_change_db_updates(old_number, new_number)
                print(f"{old_number} -> {new_number}")
                numbers_to_change.pop(old_number)


def recursive_number_change(starter_number, saved_number, numbers_to_change):
    if saved_number == starter_number:
        numbers_to_change[TMP_NUM] = numbers_to_change[starter_number]
        number_change_db_updates(starter_number, TMP_NUM)
        print(f"{starter_number} -> {TMP_NUM}")
        numbers_to_change.pop(starter_number)
        return numbers_to_change
    if saved_number == False:
        saved_number = starter_number
    if numbers_to_change[saved_number] in numbers_to_change:
        numbers_to_change = recursive_number_change(starter_number, numbers_to_change[saved_number], numbers_to_change) 
        if saved_number == starter_number:
            number_change_db_updates(TMP_NUM, numbers_to_change[TMP_NUM])
            print(f"{TMP_NUM} -> {numbers_to_change[TMP_NUM]}")
            numbers_to_change.pop(TMP_NUM)
        else:
            number_change_db_updates(saved_number, numbers_to_change[saved_number])
            print(f"{saved_number} -> {numbers_to_change[saved_number]}")
            numbers_to_change.pop(saved_number)
        return numbers_to_change
    else:
        number_change_db_updates(saved_number, numbers_to_change[saved_number])
        print(f"{saved_number} -> {numbers_to_change[saved_number]}")
        numbers_to_change.pop(saved_number)
        return numbers_to_change


def number_change_db_updates(old_number, new_number) -> None:
    base_number_to_change = db.session.execute(db.select(Pokedex).where(Pokedex.number==old_number)).scalar()
    base_number_to_change.number = new_number
    db.session.commit()
    fusions_numbers_to_change = base_number_to_change.fusions_head + \
        base_number_to_change.fusions_body
    for fusion in fusions_numbers_to_change:
        fusion.number = f"{fusion.head.number}.{fusion.body.number}"
    db.session.commit()


def update_family_order(new_family_order_arr, new_pokedex):
    for species in new_family_order_arr:
        pokemon_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar()
        pokemon_to_update.family_order = new_pokedex[species].family_order
    db.session.commit()
    for species in new_family_order_arr:
        head_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar().fusions_head
        body_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar().fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            fusion.family_order = f"{fusion.head.family_order}.{fusion.body.family_order}"
    db.session.commit()


def update_stats(new_stats_arr, new_pokedex):
    for species in new_stats_arr:
        new_stats = new_pokedex[species].stats
        pokemon_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar().stats
        pokemon_to_update.hp, pokemon_to_update.attack, pokemon_to_update.defense, \
            pokemon_to_update.sp_attack, pokemon_to_update.sp_defense, pokemon_to_update.speed = \
        new_stats.hp, new_stats.attack, new_stats.defense, new_stats.sp_attack, new_stats.sp_defense, new_stats.speed
    db.session.commit()
    for species in new_stats_arr:
        head_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar().fusions_head
        body_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar().fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            fusion.stats.hp = int(2 * fusion.head.stats.hp/3 + fusion.body.stats.hp/3)
            fusion.stats.attack = int(2 * fusion.body.stats.attack/3 + fusion.head.stats.attack/3)
            fusion.stats.defense = int(2 * fusion.body.stats.defense/3 + fusion.head.stats.defense/3)
            fusion.stats.sp_attack = int(2 * fusion.head.stats.sp_attack/3 + fusion.body.stats.sp_attack/3)
            fusion.stats.sp_defense = int(2 * fusion.head.stats.sp_defense/3 + fusion.body.stats.sp_defense/3)
            fusion.stats.speed = int(2 * fusion.body.stats.speed/3 + fusion.head.stats.speed/3)
    db.session.commit()


def update_typing(new_type_arr, new_pokedex):
    for species in new_type_arr:
        new_type_primary, new_type_secondary = new_pokedex[species].type_primary, new_pokedex[species].type_secondary 
        pokemon_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar()
        pokemon_to_update.type_primary, pokemon_to_update.type_secondary = new_type_primary, new_type_secondary
    db.session.commit()
    for species in new_type_arr:
        head_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar().fusions_head
        body_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar().fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            type_primary, type_secondary = create_fusion_typing(fusion.head, fusion.body)
            fusion.type_primary = type_primary
            fusion.type_secondary = type_secondary
        db.session.commit()


def update_naming(new_naming_arr, new_pokedex):
    for species in new_naming_arr:
        new_name_1, new_name_2 = new_pokedex[species].name_1, new_pokedex[species].name_2
        pokemon_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar()
        pokemon_to_update.name_1 = new_name_1
        pokemon_to_update.name_2 = new_name_2
    db.session.commit()
    for species in new_naming_arr:
        head_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar().fusions_head
        body_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==species, Pokedex.head==None)).scalar().fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            fusion.species = create_fusion_species(fusion.head.name_1, fusion.body.name_2)
        db.session.commit()


def get_db_pokedex(pokedex_type, dict_key):
    if pokedex_type == 'base':
        db_pokedex_query = db.session.scalars(db.select(Pokedex).where(Pokedex.head==None))
    elif pokedex_type == 'full':
        db_pokedex_query = db.session.scalars(db.select(Pokedex))
    else:
        raise ValueError("get_db_pokedex() pokedex_type parameter must be 'base' or 'full'")
    
    if dict_key == 'species':
        db_pokedex = {entry.species: entry for entry in db_pokedex_query}
    elif dict_key == 'number':
        db_pokedex = {entry.number: entry for entry in db_pokedex_query}
    else:
        raise ValueError("get_db_pokedex() dict_type parameter must be 'species' or 'number'") 
    
    return db_pokedex_query, db_pokedex

if __name__ == "__main__":
    main()