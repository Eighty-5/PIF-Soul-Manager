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
# FUSION_EXCEPTIONS = [1, 2, 3, 6, 74, 75, 76, 92, 93, 94, 95, 123, 130, 144, 145, 146, 149, 208]

# Path Variables
BASE_DEX_CSV_PATH = 'pokedex_stuff/if-base-dex.csv'
REMOVED_DEX_CSV_PATH = 'pokedex_stuff/removed-dex.csv'
SPRITE_CREDITS_PATH = 'pokedex_stuff/Sprite Credits.csv'
SPRITE_CREDITS_DNA_PATH = 'pokedex_stuff/sprite-credits-dna.csv'

# Load ENV variables
load_dotenv()

def check_for_updates(old_pokedex_dict, new_pokedex_dict):
    new_family_order_arr, new_stats_arr, new_type_arr, new_naming_arr = [], [], [], [] 
    for key in old_pokedex_dict:
        new_entry, old_entry = new_pokedex_dict[key], old_pokedex_dict[key]
        if new_entry.family_order != old_entry.family_order:
            new_family_order_arr.append(key)
        for stat in ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']:
            if vars(new_entry.stats)[stat] != vars(old_entry.stats)[stat]:
                new_stats_arr.append(key)
        if new_entry.type_primary != old_entry.type_primary or new_entry.type_secondary != old_entry.type_secondary:
            new_type_arr.append(key)
        if new_entry.name_1 != old_entry.name_1 or new_entry.name_2 != new_entry.name_2:
            new_naming_arr.append(key)
    return new_family_order_arr, new_stats_arr, new_type_arr, new_naming_arr

def update_family_order(new_family_order_arr, new_pokedex_dict):
    for pokemon_number in new_family_order_arr:
        pokemon_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==pokemon_number)).scalar()
        pokemon_to_update.family_order = new_pokedex_dict[pokemon_number].family_order
    db.session.commit()
    for pokemon_number in new_family_order_arr:
        head_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==pokemon_number)).scalar().fusions_head
        body_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==pokemon_number)).scalar().fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            fusion.family_order = f"{fusion.head.family_order}.{fusion.body.family_order}"
        db.session.commit()

def update_stats(new_stats_arr, new_pokedex_dict):
    for pokemon_number in new_stats_arr:
        new_stats = new_pokedex_dict[pokemon_number].stats
        pokemon_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==pokemon_number)).scalar().stats
        pokemon_to_update.hp, pokemon_to_update.attack, pokemon_to_update.defense, \
            pokemon_to_update.sp_attack, pokemon_to_update.sp_defense, pokemon_to_update.speed = \
        new_stats.hp, new_stats.attack, new_stats.defense, new_stats.sp_attack, new_stats.sp_defense, new_stats.speed
    db.session.commit()
    for pokemon_number in new_stats_arr:
        head_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==pokemon_number)).scalar().fusions_head
        body_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==pokemon_number)).scalar().fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            fusion.stats.hp = int(2 * fusion.head.stats.hp/3 + fusion.body.stats.hp/3)
            fusion.stats.attack = int(2 * fusion.body.stats.attack/3 + fusion.head.stats.attack/3)
            fusion.stats.defense = int(2 * fusion.body.stats.defense/3 + fusion.head.stats.defense/3)
            fusion.stats.sp_attack = int(2 * fusion.head.stats.sp_attack/3 + fusion.body.stats.sp_attack/3)
            fusion.stats.sp_defense = int(2 * fusion.head.stats.sp_defense/3 + fusion.body.stats.sp_defense/3)
            fusion.stats.speed = int(2 * fusion.body.stats.speed/3 + fusion.head.stats.speed/3)
        db.session.commit()

def update_typing(new_type_arr, new_pokedex_dict):
    for pokemon_number in new_type_arr:
        new_type_primary, new_type_secondary = new_pokedex_dict[pokemon_number].type_primary, new_pokedex_dict[pokemon_number].type_secondary 
        pokemon_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==pokemon_number)).scalar()
        pokemon_to_update.type_primary, pokemon_to_update.type_secondary = new_type_primary, new_type_secondary
    db.session.commit()
    for pokemon_number in new_type_arr:
        head_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==pokemon_number)).scalar().fusions_head
        body_fusions_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==pokemon_number)).scalar().fusions_body
        for fusion in head_fusions_to_update + body_fusions_to_update:
            type_primary, type_secondary = create_fusion_typing(fusion.head, fusion.body)
            fusion.type_primary = type_primary
            fusion.type_secondary = type_secondary
        db.session.commit()

def update_naming(new_naming_arr, new_pokedex_dict):
    for pokemon in new_naming_arr:
        new_name_1, new_name_2 = new_pokedex_dict[pokemon].name_1, new_pokedex_dict[pokemon].name_2
        pokemon_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.species==pokemon, Pokedex.head==None)).scalar()
        pokemon_to_update.name_1 = new_name_1
        pokemon_to_update.name_2 = new_name_2
    db.session.commit()
    for pokemon in new_naming_arr:
        base_pokemon = db.session.execute(db.select(Pokedex).where(Pokedex.species==pokemon, Pokedex.head==None)).scalar()
        head_fusions_to_update = base_pokemon.fusions_head
        body_fusions_to_update = base_pokemon.fusions_body
        for fusion in head_fusions_to_update:
            fusion.species = create_fusion_species(new_pokedex_dict[fusion.head.species].name_1, new_pokedex_dict[fusion.body.species].name_2)
        for fusion in body_fusions_to_update:
            fusion.species = create_fusion_species(new_pokedex_dict[fusion.head.species].name_1, new_pokedex_dict[fusion.body.species].name_2)
        db.session.commit()


def main() -> None:
    with app.app_context():
        full_time_t0 = time.perf_counter()
        # Checks for Duplicates
        new_pokedex_dict = {}
        duplicates= {}
        new_pokedex_numbers = {}
        pokedex_stats_dict = {}
        with open(BASE_DEX_CSV_PATH, newline='') as dexfile, open(REMOVED_DEX_CSV_PATH, newline='') as rdexfile:
            dexreader = csv.DictReader(dexfile)
            rdexreader = csv.DictReader(rdexfile)
            for dex in [dexreader, rdexreader]:
                for row in dex:
                    number, species = row['number'], row['species']
                    if species in new_pokedex_dict:
                        print(f"DUPLICATE NAME FOUND: [{number} - {species}] -> [{new_pokedex_dict[species].number} - {species}]\nPLEASE ADDRESS DUPLICATE NAME FROM 'if-base-dex.csv'")
                        exit()
                    if number in duplicates: 
                        print(f"DUPLICATE FOUND: {number}\nPLEASE REMOVE DUPLICATE FROM 'if-base-dex.csv'")
                        exit()
                    duplicates[number] = ''
                    new_pokedex_dict[species] = Pokedex(number=number, species=species, type_primary=row['type_primary'], 
                                                       type_secondary=row['type_secondary'], family=row['family'], family_order=row['family_order'], 
                                                       name_1=row['name_1'], name_2=row['name_2'])
                    pokedex_stats_dict[species] = PokedexStats(info=new_pokedex_dict[species], hp=int(row['hp']), attack=int(row['attack']), 
                                                         defense=int(row['defense']), sp_attack=int(row['sp_attack']), 
                                                         sp_defense=int(row['sp_defense']), speed=int(row['speed']))
                    new_pokedex_numbers[number] = [species]
        pokedex_query = db.session.execute(db.select(Pokedex).where(Pokedex.head==None)).scalars().all()
        old_pokedex_dict = {entry.species: entry for entry in pokedex_query}
        old_pokedex_numbers = {entry.number:entry.species for entry in pokedex_query}
        removed_dict, species_update_dict, number_change_dict, new_species_dict, number_and_species_change_dict, delete_dict = {}, {}, {}, {}, {}, {}
        
        # Only manual part of the program. When a name from the previous pokedex is not detected in the new pokedex, 
        # admin needs to determine whether this is simply a name being updated to a correct name, or if the pokemon should actually be deleted/removed
        # from the pokedex
        if len(old_pokedex_dict) > 0:
            for key, dict_ in new_pokedex_dict.items(): 
                print(f"[{dict_.number} - {key}]", end=' ')
            print("\n")
            for species, info in old_pokedex_dict.copy().items():
                if species in new_pokedex_dict:
                    if old_pokedex_dict[species].number != new_pokedex_dict[species].number:
                        number_change_dict[info.number] = new_pokedex_dict[species].number
                elif not 'r' in info.number:
                    replacement_species = False
                    if info.number in new_pokedex_numbers:
                        replacement_species = new_pokedex_numbers[info.number] 
                    answer_1 = ''
                    if replacement_species:
                        while not answer_1 in ["r", "u", "c"]:
                            answer_1 = input(f" Should [{old_pokedex_dict[species].number} - {species.upper()}] be removed or species name updated to [{info.number} - {replacement_species.upper()}] or number and species changed? [R (removed) / U (name updated) / C (number and species change)] ").lower()
                    else:
                        while not answer_1 in ["r", "c"]:
                            answer_1 = input(f" Should [{old_pokedex_dict[species].number} - {species.upper()}] be removed or number and species changed? [R (removed) / C (number and species change)] ").lower()
                    print("")
                    if answer_1 == "u":
                        species_update_dict[info.number] = replacement_species
                    elif answer_1 == "r":
                        removed_dict[info.number] = species
                    else:
                        answer_2 = ''
                        while not answer_2 in old_pokedex_numbers:
                            answer_2 = input(f" Please specify which pokedex number + species combo that [{info.number} - {species.upper()}] should be updated to: ")
                        print("\n")
                        number_and_species_change_dict[info.number] = {answer_2:old_pokedex_numbers[answer_2]}
                else:
                    delete_dict[info.number] = ''
            print(f"Pokemon to be added to Removed Dex:\n{removed_dict}")
            print(f"Pokemon whose species name need to be updated to a new species name:\n{species_update_dict}")
            print(f"Pokemon whose number needs to be udpated to a new number:\n{number_change_dict}")
            print(f"Pokemon to be deleted:\n{delete_dict}")
        else:
            new_species_dict = new_pokedex_dict

        continue_with_changes()

        # BACKUP DATABASE
        backup_question = input('Backup Database [y/n]? ')
        if backup_question == 'y':
            db_backup_filename = 'pifgm_db_' + datetime.now().strftime('%Y-%m-%d_T%H-%M-%S') + '.sql'
            subprocess.run(f"mysqldump -u root -p pif_game_manager > {os.getenv('DB_BACKUP_PATH')}{db_backup_filename}", shell=True)
        
        if len(removed_dict) > 0:
            print(f"Adding {removed_dict} to the Removed Pokedex\n")
            with open(REMOVED_DEX_CSV_PATH, 'a') as removeddex:
                for number in removed_dict:
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
        if len(species_update_dict) > 0:
            print(f"Updating the following pokedex entries {species_update_dict}\n")
            for number, new_species in species_update_dict.items():
                species_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==number)).scalar()
                species_to_update.species = new_species
                db.session.commit()
        if len(number_change_dict) > 0:
            print(f"Updating the following numbers {number_change_dict}\n")
            for number, new_number in number_change_dict.items():
                number_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==number)).scalar()
                number_to_update.number = new_number
                if number_to_update.family_order == 1:
                    familys_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.family==number)).scalars()
                    for pokemon in familys_to_update:
                        pokemon.family = new_number
                db.session.commit() 
        if len(number_and_species_change_dict) > 0:
            print(f"Updating the following numbers and species {number_and_species_change_dict}\n")
            for number, new in number_and_species_change_dict.items():
                for new_number, new_species in new.items():
                    pokemon_to_update = db.session.execute(db.select(Pokedex).where(Pokedex.number==number)).scalar()
                    pokemon_to_update.number = new_number
                    pokemon_to_update.species = new_species
                db.session.commit()    
        
        print("Checking for any updated Pokedex Entry info . . .\n")
        
        new_family_order_arr, new_stats_arr, new_type_arr, new_naming_arr = [], [], [], []
        for key in old_pokedex_dict:
            if key in new_pokedex_dict:
                new_entry, old_entry = new_pokedex_dict[key], old_pokedex_dict[key]
                if new_entry.family_order != old_entry.family_order:
                    new_family_order_arr.append(key)
                for stat in ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']:
                    if vars(new_entry.stats)[stat] != vars(old_entry.stats)[stat]:
                        new_stats_arr.append(key)
                if new_entry.type_primary != old_entry.type_primary or new_entry.type_secondary != old_entry.type_secondary:
                    new_type_arr.append(key)
                if new_entry.name_1 != old_entry.name_1 or new_entry.name_2 != old_entry.name_2:
                    new_naming_arr.append(key)

        if len(new_stats_arr) > 0:
            print(f"Updating stats for Base + Fusions for the following Pokedex numbers: {new_stats_arr}")
            update_stats(new_stats_arr, new_pokedex_dict)
            print(f"stats updated for Base + Fusions")
        if len(new_family_order_arr) > 0:
            print(f"Updating family_order for Base + Fusions for the following Pokedex numbers: {new_family_order_arr}")
            update_family_order(new_family_order_arr, new_pokedex_dict)
            print(f"family_orders udpated for Base + Fusions")
        if len(new_type_arr) > 0:
            print(f"Updating typing for the following Pokedex numbers: {new_type_arr}")
            update_typing(new_type_arr, new_pokedex_dict)
            print(f"typing updated for Base + Fusions")
        if len(new_naming_arr) > 0:
            print(f"Updating Species Names for Base + Fusions for following Pokedex entries: {new_naming_arr}")
            update_naming(new_naming_arr, new_pokedex_dict)
            print(f"species updated for Base + Fusions")
        print("Existing Pokedex updated!")

        print("Checking for any new Pokemon. . .")
        pokedex_query = db.session.execute(db.select(Pokedex).where(Pokedex.head==None)).scalars().all()
        old_pokedex_dict = {entry.species: entry for entry in pokedex_query}
        for pokemon, info in new_pokedex_dict.items():
            if not pokemon in old_pokedex_dict:
                new_species_dict[pokemon] = info
        if len(new_species_dict) > 0:
            print(f"New Pokemon found {new_species_dict.keys()}")
        else:
            print("No new pokemon found")
        continue_with_changes()
        
        pokemon_to_add, stats_to_add = [], []
        pokedex_full = db.session.execute(db.select(Pokedex).where(Pokedex.head==None)).scalars()
        for species_1, pokemon_1 in new_species_dict.items():
            db.session.add(pokemon_1)
            db.session.add(pokedex_stats_dict[species_1])
            fusion, stats = create_fusion(pokemon_1, pokemon_1)
            db.session.add_all([fusion, stats])
            for pokemon_2 in new_species_dict.values():
                if pokemon_1 != pokemon_2:
                    fusion, stats = create_fusion(pokemon_1, pokemon_2)
                    pokemon_to_add.append(fusion)
                    stats_to_add.append(stats)
            for pokemon_2 in pokedex_full:
                fusion, stats = create_fusion(pokemon_1, pokemon_2)
                pokemon_to_add.append(fusion)
                stats_to_add.append(stats)
                fusion_inv, stats_inv = create_fusion(pokemon_2, pokemon_1)
                pokemon_to_add.append(fusion_inv)
                stats_to_add.append(stats_inv)
            
        db.session.add_all(pokemon_to_add)
        db.session.add_all(stats_to_add)
        db.session.commit()

        pokedex_full = db.session.execute(db.select(Pokedex.number, Pokedex.species))
        pokedex_full_dict = {entry.number: entry for entry in pokedex_full}
        pokedex_base = db.session.execute(db.select(Pokedex.number, Pokedex.species).where(Pokedex.head==None))
        pokedex_lst_path = os.getenv('POKEDEX_HTML_PATH')
        with open(pokedex_lst_path, 'w') as pokedex_list:
            pokedex_list.write('<datalist id="pokedex">\n')
            for entry in pokedex_base:
                pokedex_list.write(f'    <option value="{entry.species}"></option>\n')
            pokedex_list.write("</datalist>")
        write_pokedex_list_t1 = time.perf_counter()
        
        print("Adding Sprites and their Artists. . .\n")
        artist_query = db.session.execute(db.select(Artist)).scalars()
        artists = {artist.name: None for artist in artist_query}
        artists_to_add = []
        with open(SPRITE_CREDITS_PATH, newline='', errors='ignore') as sprites_file:
            sprite_reader = csv.DictReader(sprites_file)
            for row in sprite_reader:
                artist = row['artist']
                if not artist in artists:
                    artists[artist] = None
                    artists_to_add.append(Artist(name=artist))
            db.session.add_all(artists_to_add)
            db.session.commit()

        sprites_to_add = []
        db.session.execute(db.delete(Sprite))

        pokedex_full = db.session.execute(db.select(Pokedex)).scalars()
        pokedex_full_dict = {pokemon.number: pokemon for pokemon in pokedex_full}
        artist_full = db.session.execute(db.select(Artist)).scalars()
        artist_full_dict = {artist.name: artist for artist in artist_full}

        with open(SPRITE_CREDITS_PATH, newline='', errors='ignore') as sprites_file, open(SPRITE_CREDITS_DNA_PATH, 'a') as sprites_file_dna:
            sprite_reader = csv.DictReader(sprites_file)
            dna_dict = {'TRIPLE': [], 'INVALID NUMBER': [], 'INVALID VARIANT': [], 'DUPLICATE': []}
            for sprite in sprite_reader:
                sprite_code = sprite['sprite']
                prepped_sprite = prep_number(sprite_code)
                if prepped_sprite == 'TRIPLE' or prepped_sprite == 'INVALID NUMBER' or prepped_sprite == 'INVALID VARIANT':
                    dna_dict[prepped_sprite].append(sprite)
                    continue
                elif not prepped_sprite['number'] in pokedex_full_dict:
                    dna_dict['INVALID NUMBER'].append(sprite)
                    continue
                else:
                    sprite_to_add = Sprite(variant_let=prepped_sprite['variant'], pokedex_info=pokedex_full_dict[prepped_sprite['number']], 
                                               artists=artist_full_dict[sprite['artist']])
                    sprites_to_add.append(sprite_to_add)
            db.session.add_all(sprites_to_add)
            db.session.commit()

            sprites_file_dna.write(f"SPRITES NOT ADDED - {datetime.now().strftime('%Y-%m-%d_T%H-%M-%S')}\n")
            for key, sprites in dna_dict.items():
                sprites_file_dna.write(f"{key}:\n")
                for sprite in sprites:
                    sprites_file_dna.write(f"{sprite}\n")
        
        full_time_t1 = time.perf_counter()

        print(f"FULL TIME: {full_time_t1-full_time_t0} s")

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
                                dst = sprite_dir_path + "/" + split_filename[0]
                                shutil.move(os.path.join(new_sprites_path, filename), os.path.join(dst, filename))
                            elif split_filename[0][-1].isalpha() and (split_filename[0][:-1].isdigit() or split_filename[0][:-1] in PASS_LST):
                                dst = sprite_dir_path + "/" + split_filename[0][:-1]
                                shutil.move(os.path.join(new_sprites_path, filename), os.path.join(dst, filename))
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
        head_type = pokemon_1.type_secondary
    else:
        head_type = pokemon_1.type_primary
    # As of version 6.0 of Infinite Fusion some pokemon no longer has a dominant typing
    # if pokemon_2['number'] in FUSION_EXCEPTIONS:
    #     body_type = pokemon_2["type_primary"]
    # If body Pokemon only has one type, the secondary typing of the new fused pokemon uses the primary typing of the body Pokemon
    if pokemon_2.type_secondary == "":
        body_type = pokemon_2.type_primary
    # If the body Pokemon's secondary type is the same as the head Pokemon's primary type, the body Pokemon's primary type is instead used for the fused Pokemon's secondary type
    elif pokemon_2.type_secondary == head_type:
        body_type = pokemon_2.type_primary
    # If none of the above apply then the fused Pokemon's secondary type is the body Pokemon's secondary type. 
    else:
        body_type = pokemon_2.type_secondary
    # If the newly fused Pokemon has two typings that are the same, the secondary typing is removed
    if body_type == head_type:
        body_type = ""

    return head_type, body_type


def create_fusion_species(name_1, name_2):
    if name_1[-1] == name_2[0]:
        species = name_1 + name_2[1:]
    else:
        species = name_1 + name_2
    return species


def create_fusion_stats(pokemon_1, pokemon_2):
    fused_stats = {}
    fused_stats['hp'] = int(2 * (pokemon_1.stats.hp)/3 + (pokemon_2.stats.hp)/3)
    fused_stats['attack'] = int(2 * (pokemon_2.stats.attack)/3 + (pokemon_1.stats.attack)/3)
    fused_stats['defense'] = int(2 * (pokemon_2.stats.defense)/3 + (pokemon_1.stats.defense)/3)
    fused_stats['sp_attack'] = int(2 * pokemon_1.stats.sp_attack/3 + pokemon_2.stats.sp_attack/3)
    fused_stats['sp_defense'] = int(2 * pokemon_1.stats.sp_defense/3 + pokemon_2.stats.sp_defense/3)
    fused_stats['speed'] = int(2 * pokemon_2.stats.speed/3 + pokemon_1.stats.speed/3)
    return fused_stats


def prep_number(sprite):
    prep_dict = {}
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
        prep_dict['number'] = number
    prep_dict['variant'] = variant
    return prep_dict


def create_fusion(head_pokemon, body_pokemon):
    type_primary, type_secondary = create_fusion_typing(head_pokemon, body_pokemon)
    fused_stats = create_fusion_stats(head_pokemon, body_pokemon)
    fused_species = create_fusion_species(head_pokemon.name_1, body_pokemon.name_2)
    fusion = Pokedex(number=f"{head_pokemon.number}.{body_pokemon.number}", species=fused_species,
                     type_primary=type_primary, type_secondary=type_secondary,
                     head=head_pokemon, body=body_pokemon, family=f"{head_pokemon.family}.{body_pokemon.family}",
                     family_order=f"{head_pokemon.family_order}.{body_pokemon.family_order}")
    stats = PokedexStats(hp=fused_stats["hp"], attack=fused_stats["attack"], defense=fused_stats["defense"],
                         sp_attack=fused_stats["sp_attack"], sp_defense=fused_stats["sp_defense"],
                         speed=fused_stats["speed"], info=fusion)
    return fusion, stats


def split_sprite_code(s):
    number = s.rstrip('abcdefghijklmnopqrstuvwxyz')
    variant = s[len(number):]
    if len(variant) > 2:
        raise ValueError("Variant letter length greater than 2")
    return number, variant


if __name__ == "__main__":
    main()