import csv
import itertools
from string import ascii_lowercase
import os
from dotenv import load_dotenv

from alembic import op
from sqlalchemy import create_engine
from myproject import create_app
from myproject.models import PokedexBase, Pokedex, Artists, Pokemon
from myproject.extensions import db
from pokedex_stuff.pokedex_helpers import create_fusion_typing, create_fusion_name, confirmation, prep_number, extra_var_check

app = create_app()
PASS_LST = ['450_1']

# Load ENV variables
load_dotenv()

with app.app_context():

    engine = create_engine(os.getenv('SQLALCHEMY_DATABASE_URI'))

    # UPDATE DATABASE TABLES
    update_database = input("DEBUG: UPDATE DATABASE TABLES [y/n]? ")
    if update_database == 'y':
        print("CREATING INFINITE FUSION MAIN POKEDEX CSV FILE. . .\nCHECKING FOR DUPLICATES. . .")
        pokedex_1 = [] 
        pokedex_1_names = []
        duplicates = [] 
        duplicate_names = []
        with open('pokedex_stuff/if-base-dex.csv', newline='') as csvfile, open('pokedex_stuff/pokedex.txt', 'w') as pokedexfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row in pokedex_1:
                    duplicates.append(row)
                if row['species'] in pokedex_1_names:
                    duplicate_names.append({row['id'], row['species']})
                pokedex_1.append(row)
                pokedexfile.write(f"<option value='{row['species']}'></option>\n")
                pokedex_1_names.append(row['species'])
        if len(duplicates) > 0:
            print(f"DUPLICATES FOUND:\n{duplicates}\nPLEASE REMOVE DUPLICATES FROM 'if-base-dex.csv'")
            exit()
        else:
            print("NO DUPLICATES FOUND")
            if len(duplicate_names) > 0:
                print(f"HOWEVER DUPLICATE NAMES WERE FOUND:\n{duplicate_names}PLEASE ADDRESS DUPLICATE NAMES FROM 'if-base-dex.csv'")
                exit()
        pokedex_2 = pokedex_1.copy()
        print("CREATING MASTER DICTIONARY. . .")
        pokedex_dict = {}
        for pokemon_1 in pokedex_1:
            base_id_1 = pokemon_1['id']
            pokedex_dict[base_id_1] = {}
            pokedex_dict[base_id_1]['base'] = {}
            pokedex_dict[base_id_1]['base']['species'] = pokemon_1['species']
            pokedex_dict[base_id_1]['base']['type_primary'] = pokemon_1['type_1']
            if pokemon_1['type_2'] == '':
                pokedex_dict[base_id_1]['base']['type_secondary'] = None
            else:
                pokedex_dict[base_id_1]['base']['type_secondary'] = pokemon_1['type_2']
            pokedex_dict[base_id_1]['base']['family'] = pokemon_1['family']
            pokedex_dict[base_id_1]['base']['family_order'] = pokemon_1['family_order']
            pokedex_dict[base_id_1]['base']['variants'] = '-'
            pokedex_dict[base_id_1]['base']['variants_dict'] = {}
            pokedex_dict[base_id_1]['base']['variants_dict'][''] = 'japeal'
            for pokemon_2 in pokedex_1:
                base_id_2 = pokemon_2['id']
                pokedex_dict[base_id_1][base_id_2] = {}
                pokedex_dict[base_id_1][base_id_2]['species'] = create_fusion_name(pokemon_1['name_1'], pokemon_2['name_2'])
                pokedex_dict[base_id_1][base_id_2]['base_id_1'] = base_id_1
                pokedex_dict[base_id_1][base_id_2]['base_id_2'] = base_id_2
                type_primary, type_secondary = create_fusion_typing(pokemon_1, pokemon_2) 
                pokedex_dict[base_id_1][base_id_2]['type_primary'] = type_primary
                if type_secondary == '':
                    pokedex_dict[base_id_1][base_id_2]['type_secondary'] = None
                else:
                    pokedex_dict[base_id_1][base_id_2]['type_secondary'] = pokemon_1['type_2']
                pokedex_dict[base_id_1][base_id_2]['family'] = f"{pokemon_1['family']}.{pokemon_2['family']}"
                pokedex_dict[base_id_1][base_id_2]['family_order'] = f"{pokemon_1['family_order']}.{pokemon_2['family_order']}"
                pokedex_dict[base_id_1][base_id_2]['variants'] = '-'
                pokedex_dict[base_id_1][base_id_2]['variants_dict'] = {}
                pokedex_dict[base_id_1][base_id_2]['variants_dict'][''] = 'japeal'

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
                    if not prepped_sprite['base_1'] in pokedex_dict:
                        extra_var_check(prepped_sprite['base_1'])
                        continue
                    base_1 = prepped_sprite['base_1']
                    if 'base_2' in prepped_sprite:
                        base_2 = prepped_sprite['base_2']
                        if not base_2 in pokedex_dict:
                            extra_var_check(base_2)
                            continue
                        if 'var' in prepped_sprite and not prepped_sprite['var'] in pokedex_dict[base_1][base_2]['variants']:
                            var = prepped_sprite['var']
                            # ADD DUPLICATE CHECK LATER
                            pokedex_dict[base_1][base_2]['variants_dict'][var] = sprite['artist']
                            pokedex_dict[base_1][base_2]['variants'] = pokedex_dict[base_1][base_2]['variants'] + var
                        else:
                            pokedex_dict[base_1][base_2]['variants_dict'][''] = sprite['artist']
                    else:
                        if 'var' in prepped_sprite and not prepped_sprite['var'] in pokedex_dict[base_1]['base']['variants']:
                            var = prepped_sprite['var']
                            # ADD DUPLICATE CHECK LATER
                            pokedex_dict[base_1]['base']['variants_dict'][var] = sprite['artist']
                            pokedex_dict[base_1]['base']['variants'] = pokedex_dict[base_1]['base']['variants'] + var
                        else:
                            pokedex_dict[base_1]['base']['variants_dict'][''] = sprite['artist']

        print("MASTER DICTIONARY COMPLETE")

        # UPDATE ARTISTS AND POKEDEX TABLES
        Pokedex.query.delete()
        db.session.commit()
        PokedexBase.query.delete()
        db.session.commit()
        Artists.query.delete()
        db.session.commit()

        with open('pokedex_stuff/if-pokedex.csv', 'w') as dexfile, open('pokedex_stuff/sprite-credits.csv', 'w') as spritesfile:
            dexfile.write('number,species,base_id_1,base_id_2,type_primary,type_secondary,family,family_order,variants,\n')
            spritesfile.write('sprite,artist,\n')
            bulk_artists = []
            bulk_pokemon = []
            for base_id_1, base1_dict in pokedex_dict.items():
                print(f"UPLOADING POKEDEX NUMBER - {base_id_1}")
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
    else:
        print("WILL NOT UPDATE DATABASE")
                
    # Update Pokemon Table if any changes
    
    # CHANGE: REQUIRE UPDATING ARTISTS TABLE IF UPDATE POKEDEX IS YES
    
    # # Move sprites to sprites directory
    # sprite_confirm = input("Add update sprite .pngs [y/n]? ")
    # if sprite_confirm != 'y':
    #     exit()
    # sprite_path = input("Enter path to sprite folder: ")
    # print(sprite_path)
