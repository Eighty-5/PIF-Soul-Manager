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
from pokedex_stuff.pokedex_helpers import prep_number, create_master_dex, change_numbers, delete_numbers
from sqlalchemy import create_engine, text

app = create_app()
PASS_LST = ['450_1']
# FUSION_EXCEPTIONS = [1, 2, 3, 6, 74, 75, 76, 92, 93, 94, 95, 123, 130, 144, 145, 146, 149, 208]

# Load ENV variables
load_dotenv()

def bulk_save_into_db(lst):
    db.session.bulk_save_objects(lst)
    db.session.commit()
    lst.clear()

with app.app_context():

    # BACKUP DATABASE
    backup_question = input('Backup Database [y/n]? ')
    if backup_question == 'y':
        db_backup_filename = 'pifgm_db_' + datetime.now().strftime('%Y-%m-%d_T%H-%M-%S') + '.sql'
        subprocess.run(f"mysqldump -u root -p pif_game_manager > {os.getenv('DB_BACKUP_PATH')}{db_backup_filename}", shell=True)

    new_pokedex = {}
    pokedex_names, duplicates, duplicate_names = [], {}, {}
    with open('pokedex_stuff/if-base-dex.csv', newline='') as dexfile, open('pokedex_stuff/removed-dex.csv', newline='') as rdexfile:
        dexreader = csv.DictReader(dexfile)
        rdexreader = csv.DictReader(rdexfile)
        for dex in [dexreader, rdexreader]:
            for row in dex:
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
    # Infinite Fusion Dev usually just adds new entry instead of updating existing pokedex entries, 
    # however we will check just in case that changes in the future and update users recorded pokemon accordingly
    pokedex_query = PokedexBase.query.all()
    old_pokedex = {entry.number: entry.species for entry in pokedex_query}

    pokemon_number_change, pokemon_species_change, pokemon_added_species, pokemon_removed, pokemon_delete = {}, {}, {}, {}, {}

    for number, info in new_pokedex.items():
        new_species = info['species']
        if not new_species in old_pokedex.values():
            pokemon_added_species[number] = info
            if not number in old_pokedex:
                continue
        try:
            old_species = old_pokedex[number]
            if new_species != old_species:
                # https://stackoverflow.com/questions/50698390/find-a-key-if-a-value-exists-in-a-nested-dictionary
                new_number = [number for number, info in new_pokedex.items() if any(old_species == new_species for new_species in info.values())][0]
                pokemon_number_change[number] = new_number
        except KeyError:
            old_number = [k for k, v in old_pokedex.items() if v == new_species][0]
            pokemon_number_change[old_number] = number
        except IndexError:
            pokemon_delete[number] = old_pokedex[number]
    
    missing_numbers = set(old_pokedex) - set(new_pokedex)
    for number in missing_numbers:
        try:
            new_number = [k for k, v in new_pokedex.items() if any(old_pokedex[number] == l for l in v.values())][0]
            pokemon_number_change[number] = new_number
        except IndexError:
            if not number + 'r' in new_pokedex:
                pokemon_delete[number] = old_pokedex[number]
            else:
                pokemon_removed[number] = old_pokedex[number]
                
    print("ADDED SPECIES:\n", pokemon_added_species)
    print("NUMBER CHANGES:\n", pokemon_number_change)
    print("SPECIES CHANGES:\n", pokemon_species_change)
    print("TO BE DELETED:\n", pokemon_delete)
    master_changes = pokemon_removed | pokemon_number_change
    print("MASTER CHANGES: ", master_changes)

    continue_changes = input("CONTINUE WITH CHANGES [y/n]? ")
    pokedex_lst_path = os.getenv('POKEDEX_HTML_PATH')
    with open(pokedex_lst_path, 'w') as pokedex_list:
        pokedex_list.write('<datalist id="pokedex">\n')
        for number, info in new_pokedex.items():
            pokedex_list.write(f'    <option value="{info['species']}"></option>\n')
        pokedex_list.write("</datalist>")

    # UPDATE DATABASE TABLES
    if continue_changes.lower() == 'y':
        print("CREATING MASTER POKEDEX DICTIONARY. . .")
        master_pokedex = {}
        create_master_dex(master_pokedex, new_pokedex)
        print("INFINITE FUSION POKEDEX ADDED. . .")

        print("ADDING VARIANTS AND THEIR ARTISTS. . .")
        with open('pokedex_stuff/temp-sprite-credits.csv', newline='', errors='ignore') as temp_sprites_file, open('pokedex_stuff/sprite-credits.csv', 'w') as sprites_file:
            sprite_reader = csv.DictReader(temp_sprites_file)
            sprites_file.write('sprite,artist,var,reference\n')
            dna_dict = {'TRIPLE': [], 'INVALID NUMBER': [], 'EXTRA VARIANT': [], 'DUPLICATE': []}
            for sprite in sprite_reader:
                prepped_sprite = prep_number(sprite['sprite'])
                if prepped_sprite == 'TRIPLE' or prepped_sprite == 'INVALID NUMBER' or prepped_sprite == 'EXTRA VARIANT':
                    dna_dict[prepped_sprite].append(sprite)
                    continue
                elif not prepped_sprite['base_1'] in master_pokedex:
                    dna_dict['INVALID NUMBER'].append(sprite)
                    continue
                base_1 = prepped_sprite['base_1']
                if 'base_2' in prepped_sprite:
                    base_2 = prepped_sprite['base_2']
                    if not base_2 in master_pokedex:
                        dna_dict['INVALID NUMBER'].append(sprite)
                        continue
                else: 
                    base_2 = 'base'
                if 'var' in prepped_sprite:
                    if prepped_sprite['var'] in master_pokedex[base_1][base_2]['variants']:
                        dna_dict['DUPLICATE'].append(sprite)
                    else:
                        var = prepped_sprite['var']
                        master_pokedex[base_1][base_2]['variants_dict'][var] = sprite['artist']
                        master_pokedex[base_1][base_2]['variants'] = master_pokedex[base_1][base_2]['variants'] + var
                        sprites_file.write(f"{base_1}.{base_2}{var},{sprite['artist']},\n")
                else:
                    master_pokedex[base_1][base_2]['variants_dict'][''] = sprite['artist']
                    sprites_file.write(f"{base_1}.{base_2},{sprite['artist']},\n")
        print("MASTER POKEDEX DICTIONARY COMPLETE")

        with open('pokedex_stuff/dna_sprites.txt', 'w') as dna_file:
            dna_file.write(f"SPRITES NOT ADDED - {datetime.now().strftime('%Y-%m-%d_T%H-%M-%S')}\n")
            for key, sprites in dna_dict.items():
                dna_file.write(f"{key}:\n")
                for sprite in sprites:
                    dna_file.write(f"{sprite}\n")

        changes_exist = True
        if len(master_changes) == 0 and len(pokemon_delete) == 0:
            changes_exist = False
        
        engine = create_engine(os.getenv('SQLALCHEMY_DATABASE_URI'))
        with engine.connect() as connection:
            connection.execute(text("set global foreign_key_checks = 0;"))
            connection.commit()
        
        if changes_exist:
            print("UPDATING POKEMON DB TABLE WITH CHANGES TO POKEDEX. . .")
            delete_numbers(pokemon_delete)
            change_numbers(master_changes)
            print("POKEMON DB TABLE UPDATE COMPLETE")
    
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
            print("UPLOADING MASTER POKEDEX DICTIONARY AND ARTISTS TABLE TO DATABASE. . .")
            for base_id_1, base1_dict in master_pokedex.items():
                for base_id_2, base2_dict in base1_dict.items():
                    if base_id_2 == 'base':
                        if len(bulk_artists) > 0 and len(bulk_pokemon) > 0:
                            try:
                                bulk_save_into_db(bulk_pokemon)
                                bulk_save_into_db(bulk_artists)
                            except:
                                print(f"POKEDEX TABLE OR ARTIST TABLE COULD NOT BE UPDATED")
                                exit()
                        base_addition = PokedexBase(number=base_id_1, species=base2_dict['species'])
                        db.session.add(base_addition)
                        db.session.commit()
                        pokedex_number = base_id_1
                        base_id_2 = None
                    else:
                        pokedex_number = f"{base_id_1}.{base_id_2}"
                    pokemon_addition = Pokedex(number=pokedex_number, species=base2_dict['species'], base_id_1=base_id_1, base_id_2=base_id_2,
                                               type_primary=base2_dict['type_primary'], type_secondary=base2_dict['type_secondary'], 
                                               family=base2_dict['family'], family_order=base2_dict['family_order'], variants=base2_dict['variants'])
                    bulk_pokemon.append(pokemon_addition)
                    dexfile.write(f"{pokedex_number},{base2_dict['species']},{base_id_1},{base_id_2},{base2_dict['type_primary']},{base2_dict['type_secondary']},{base2_dict['family']},{base2_dict['family_order']},{base2_dict['variants']},\n")
                    for variant, artist in base2_dict['variants_dict'].items():
                        artists_addition = Artists(sprite=f"{pokedex_number}{variant}",
                                                    artist=artist)
                        bulk_artists.append(artists_addition)
                        spritesfile.write(f"{pokedex_number}{variant},{artist},\n")
            # One last upload for last pokedex entry
            bulk_save_into_db(bulk_pokemon)
            bulk_save_into_db(bulk_artists)
        print("POKEDEX TABLE AND ARTISTS TABLE SUCCESSFULLY UPDATED")
        with engine.connect() as connection:
            connection.execute(text("set global foreign_key_checks = 1;"))
            connection.commit()
    else:
        print("UPDATE CANCELED")

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
