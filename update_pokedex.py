import csv
import os
import sys
import shutil
import subprocess

from datetime import datetime
from dotenv import load_dotenv
from myproject import create_app
from myproject.models import PokedexBase, Pokedex, Artists
from myproject.extensions import db
from pokedex_stuff.pokedex_helpers import prep_number, extra_var_check, create_master_dex, change_numbers, delete_numbers
from sqlalchemy import create_engine, text

app = create_app()
PASS_LST = ['450_1']

# Load ENV variables
load_dotenv()

with app.app_context():

    # BACKUP DATABASE
    backup_question = input('Backup Database [y/n]? ')
    if backup_question == 'y':
        db_backup_filename = 'pifgm_db_' + datetime.now().strftime('%Y-%m-%d_T%H-%M-%S') + '.sql'
        subprocess.run(f"mysqldump -u root -p pif_game_manager > {os.getenv('DB_BACKUP_PATH')}{db_backup_filename}", shell=True)

    new_pokedex = {}
    pokedex_names, duplicates, duplicate_names = [], {}, {}
    with open('pokedex_stuff/if-base-dex.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            number, species = row['number'], row['species']
            if number in new_pokedex: 
                duplicates[number] = species
            if species in pokedex_names:
                duplicate_names[number] = species
            pokedex_names.append(species)
            new_pokedex[number] = row
        if len(duplicates) > 0:
            print(f"DUPLICATES FOUND:\n{duplicates}\nPLEASE REMOVE DUPLICATES FROM 'if-base-dex.csv'")
            exit()
        else:
            print("NO DUPLICATES FOUND")
            if len(duplicate_names) > 0:
                print(f"HOWEVER DUPLICATE NAMES WERE FOUND:\n{duplicate_names}\nPLEASE ADDRESS DUPLICATE NAMES FROM 'if-base-dex.csv'")
                exit()

    new_pokedex = {i: new_pokedex[i] for i in sorted(list(new_pokedex.keys()))}
    # Download PokedexBase Table to check for updates
    # Infinite Fusion Dev usually just adds new entry instead of updating existing pokedex entries, however we will check just in case that changes in the future and update users recorded pokemon accordingly
    old_pokedex = {}
    pokedex_query = PokedexBase.query.all()
    old_pokedex = {entry.number: entry.species for entry in pokedex_query}

    pokedex_number_change, pokedex_species_change, pokedex_added, pokedex_removed = {}, {}, {}, {}
    for number, info in new_pokedex.items():
        if number in old_pokedex:
            new_species, old_species = info['species'], old_pokedex[number]
            if new_species != old_species:
                # https://stackoverflow.com/questions/50698390/find-a-key-if-a-value-exists-in-a-nested-dictionary
                if not new_species in old_pokedex.values():
                    pokedex_added[number] = info
                try:
                    new_number = [number for number, info in new_pokedex.items() if any(old_species == new_species for new_species in info.values())][0]
                    pokedex_number_change[number] = new_number
                except IndexError:
                    pokedex_removed[number] = old_species
                    pokedex_species_change[number] = {}
                    pokedex_species_change[number] = {'Before':old_pokedex[number], 'After':new_species}
        else:
            pokedex_added[number] = info

    for number in pokedex_added.copy():
        if number in pokedex_number_change.values():
            pokedex_added.pop(number)

    with open('pokedex_stuff/removed-dex.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        removed_pokedex = {row['number']: row for row in reader}
    
    missing_numbers = set(old_pokedex) - set(new_pokedex)
    for number in missing_numbers:
        try:
            new_number = [k for k, v in new_pokedex.items() if any(old_pokedex[number] == l for l in v.values())][0]
            pokedex_number_change[number] = new_number
        except IndexError:
            if not number in removed_pokedex:
                pokedex_removed[number] = old_pokedex[number]

    removed_numbers = [number[:-1] for number in removed_pokedex.keys()]
    pokedex_delete = {}
    for number, species in pokedex_removed.copy().items():
        if not number in removed_numbers:
            pokedex_delete[number] = species
            pokedex_removed.pop(number)

    print("ADDED: ", pokedex_added)
    print("REMOVED: ", pokedex_removed)
    print("NUMBER CHANGE: ", pokedex_number_change)
    print("SPECIES CHANGE: ", pokedex_species_change)
    print("TO BE DELETED: ", pokedex_delete)
    
    cont = True
    
    pokedex_removed = {k: k + 'r' for k in pokedex_removed if not 'r' in k}
    master_changes = pokedex_removed | pokedex_number_change
    print(master_changes)

    continue_changes = input("CONTINUE WITH CHANGES [y/n]? ")
    if continue_changes.lower() != 'y':
        print("UPDATE CANCELED")
        exit()

    # UPDATE DATABASE TABLES
    update_database = input("UPDATE DATABASE TABLES [y/n]? ")
    if update_database.lower() == 'y' and cont == True:
        print("CREATING INFINITE FUSION MAIN POKEDEX CSV FILE. . .\nCHECKING FOR DUPLICATES. . .")
        print("CREATING MASTER DICTIONARY. . .")
        master_pokedex = {}
        create_master_dex(master_pokedex, new_pokedex, removed_pokedex)
        create_master_dex(master_pokedex, removed_pokedex, new_pokedex)
        print("POKEDEX MASTER DICTIONARY CREATED")

        # print_triple = input("Print Triple Fusions print [y/n]? ")
        # print_extra_variants = input("Print Extra Variants print [y/n]? ")

        with open('pokedex_stuff/temp-sprite-credits.csv', newline='', errors='ignore') as temp_sprites_file, open('pokedex_stuff/sprite-credits.csv', 'w') as sprites_file:
            sprite_reader = csv.DictReader(temp_sprites_file)
            # sprites_file.write('sprite,artist,var,reference\n')
            triple_fusions = []
            for sprite in sprite_reader:
                prepped_sprite = prep_number(sprite['sprite'])
                if prepped_sprite != 'TRIPLE' and prepped_sprite != 'INVALID NUMBER':
                    if not prepped_sprite['base_1'] in master_pokedex:
                        extra_var_check(prepped_sprite['base_1'])
                        continue
                    base_1 = prepped_sprite['base_1']
                    if 'base_2' in prepped_sprite:
                        base_2 = prepped_sprite['base_2']
                        if not base_2 in master_pokedex:
                            extra_var_check(base_2)
                            continue
                        if 'var' in prepped_sprite and not prepped_sprite['var'] in master_pokedex[base_1][base_2]['variants']:
                            var = prepped_sprite['var']
                            # ADD DUPLICATE CHECK LATER
                            master_pokedex[base_1][base_2]['variants_dict'][var] = sprite['artist']
                            master_pokedex[base_1][base_2]['variants'] = master_pokedex[base_1][base_2]['variants'] + var
                        else:
                            master_pokedex[base_1][base_2]['variants_dict'][''] = sprite['artist']
                    else:
                        if 'var' in prepped_sprite and not prepped_sprite['var'] in master_pokedex[base_1]['base']['variants']:
                            var = prepped_sprite['var']
                            # ADD DUPLICATE CHECK LATER
                            master_pokedex[base_1]['base']['variants_dict'][var] = sprite['artist']
                            master_pokedex[base_1]['base']['variants'] = master_pokedex[base_1]['base']['variants'] + var
                        else:
                            master_pokedex[base_1]['base']['variants_dict'][''] = sprite['artist']
        print("MASTER DICTIONARY COMPLETE")

        # UPDATE ARTISTS AND POKEDEX TABLES
        changes_exist = True
        if len(master_changes) == 0 and len(pokedex_delete) == 0:
            changes_exist = False
        
        if changes_exist:
            engine = create_engine(os.getenv('SQLALCHEMY_DATABASE_URI'))
            with engine.connect() as connection:
                connection.execute(text("set global foreign_key_checks = 0;"))
            change_numbers(master_changes)
            delete_numbers(pokedex_delete)
        
        # Update Pokemon Table if any changes
        Pokedex.query.delete()
        db.session.commit()
        PokedexBase.query.delete()
        db.session.commit()
        Artists.query.delete()
        db.session.commit()

        with open('pokedex_stuff/if-pokedex.csv', 'w') as dexfile, open('pokedex_stuff/sprite-credits.csv', 'w') as spritesfile:
            dexfile.write('number,species,base_id_1,base_id_2,type_primary,type_secondary,family,family_order,variants,\n')
            spritesfile.write('sprite,artist,\n')
            bulk_artists, bulk_pokemon = [], []
            print("UPLOADING POKEDEX. . .")
            for base_id_1, base1_dict in master_pokedex.items():
                for base_id_2, base2_dict in base1_dict.items():
                    if base_id_2 == 'base':
                        if len(bulk_artists) > 0 and len(bulk_pokemon) > 0:
                            try:
                                db.session.bulk_save_objects(bulk_pokemon)
                                db.session.commit()
                                bulk_pokemon.clear()
                                db.session.bulk_save_objects(bulk_artists)
                                db.session.commit()
                                bulk_artists.clear()
                            except:
                                print(f"POKEDEX TABLE OR ARTIST TABLE COULD NOT BE UPDATED")
                                exit()
                        base_addition = PokedexBase(number=base_id_1, species=base2_dict['species'])
                        db.session.add(base_addition)
                        db.session.commit()
                        pokedex_number = base_id_1
                        base_id_2_adj = None
                    else:
                        pokedex_number = f"{base_id_1}.{base_id_2}"
                        base_id_2_adj = base_id_2
                    pokemon_addition = Pokedex(number=pokedex_number,
                                                species=base2_dict['species'],
                                                base_id_1=base_id_1,
                                                base_id_2=base_id_2_adj,
                                                type_primary=base2_dict['type_primary'],
                                                type_secondary=base2_dict['type_secondary'],
                                                family=base2_dict['family'],
                                                family_order=base2_dict['family_order'],
                                                variants=base2_dict['variants'])
                    bulk_pokemon.append(pokemon_addition)
                    dexfile.write(f"{pokedex_number},{base2_dict['species']},{base_id_1},{base_id_2_adj},{base2_dict['type_primary']},{base2_dict['type_secondary']},{base2_dict['family']},{base2_dict['family_order']},{base2_dict['variants']},\n")
                    for variant, artist in base2_dict['variants_dict'].items():
                        artists_addition = Artists(sprite=f"{pokedex_number}{variant}",
                                                    artist=artist)
                        bulk_artists.append(artists_addition)
                        spritesfile.write(f"{pokedex_number}{variant},{artist},\n")
            # One last upload for last pokedex entry
            db.session.bulk_save_objects(bulk_pokemon)
            db.session.commit()
            bulk_pokemon.clear()
            db.session.bulk_save_objects(bulk_artists)
            db.session.commit()
            bulk_artists.clear()
        print("POKEDEX TABLE AND ARTISTS TABLE SUCCESSFULLY UPDATED")
        if changes_exist:
            with engine.connect() as connection:
                connection.execute(text("set global foreign_key_checks = 1;"))
    else:
        print("WILL NOT UPDATE DATABASE")

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
    
    

