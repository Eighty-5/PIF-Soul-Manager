import csv
from dotenv import load_dotenv
import os
import sys
from typing import Type
from werkzeug.security import check_password_hash, generate_password_hash

from pifsm import create_app
from pifsm.models import User, Pokedex, PokedexStats, Family, Artist, Sprite
from pifsm.decorators import func_timer
from pifsm.extensions import db
from database_utils import (
    create_fusion_species,
    create_fusion_typing,
    create_fusion_stats,
    create_pokedex_html,
    sanitized_input,
    backup_database,
    read_pokedex_csv,
    create_family_instances,
    create_fusion,
    session_check
)

load_dotenv()

@func_timer
def main(*args, **kwargs) -> None:
    if sys.argv[1] == 'mysql':
        import mysql.connector
        conn = mysql.connector.connect(
            host = os.getenv('MYSQL_HOST'),
            user = os.getenv('MYSQL_USER'),
            password = os.getenv('MYSQL_PASSWORD')
        )
        cur = conn.cursor()
        cur.execute("CREATE DATABASE pif_save_manager")

    elif sys.argv[1] == 'postgresql':
        import psycopg2
        conn = psycopg2.connect(
            database = "postgres", 
            user = os.getenv('POSTGRESQL_USER'), 
            password = os.getenv('POSTGRESQL_PASSWORD'),
            host = os.getenv('POSTGRESQL_HOST'),
            port = os.getenv('POSTGRESQL_PORT')
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("CREATE DATABASE pif_save_manager")
    elif sys.argv[1] == 'sqlite':
        sqlite_db_path = os.getenv('SQLITE_DB_PATH')
        if os.path.isfile(sqlite_db_path):
            prompt = "Database already exists, would you like to create a backup and overwrite [y, n]? "
            answers = ("y", "n")
            answer = sanitized_input(prompt, type_=str.lower, range_=answers)
            if answer == "y":
                backup_database('sqlite', db_backup_path=os.getenv('DB_BACKUP_PATH'), db_path=os.getenv('SQLITE_DB_PATH'))
                os.remove(sqlite_db_path)
            else:
                print("Database Creation Canceled")
                quit()

    print("Database created successfully...")

    app = create_app()

    with app.app_context():

        db.create_all()
        admin_user = User(username='Admin', hash=generate_password_hash(os.getenv('ADMIN_PASSWORD'), method='pbkdf2', salt_length=16))
        db.session.add(admin_user)

        # Add Pokedex Items
        pokedex = read_pokedex_csv(dict_key='pokedex_number', base_pokedex_path=os.getenv('BASE_DEX_CSV_PATH'))
        pokedex = convert_pokedex(pokedex=pokedex, session_add=True)
        pokedex = create_full_pokedex(pokedex)
        family_dict = create_family_instances(pokedex)
        db.session.add_all(family_dict.values())
        # add_pokedex_to_session(pokedex)

        commit_pokedex()

        # Routes List Creating
        update_routes_list(routes_html_path=os.getenv('ROUTES_HTML_PATH'))

        create_pokedex_html(pokedex_html_path=os.getenv('POKEDEX_HTML_PATH'))


# @func_timer
# def add_pokedex_to_session(pokedex: dict):
#     # Test 1
#     # db.session.add_all(pokedex.values())
#     # Pokedex -> Stat -> Sprite -> Family-1st 

#     # Test 2
#     # for pokedex_number, pokemon in pokedex.items():
#     #     db.session.add(pokemon.family)
#         # db.session.add(pokemon.stats)
#         # db.session.add(pokemon)
#     # Family-1st -> Pokedex-each -> Stat-each -> Sprite-each

#     # Test 3


#     # session_check()

@func_timer
def create_full_pokedex(pokedex: dict) -> dict:
    """Creates all fusions from base pokedex and adds to existing pokedex dictionary."""
    japeal = db.session.scalar(db.select(Artist).where(Artist.artist_name=='japeal'))
    family_dict = {}
    pokedex_full = {}
    for pokedex_number, head_pokemon in pokedex.items():
        for pokedex_number, body_pokemon in pokedex.items():
            fusion = create_fusion(head_pokemon, body_pokemon, japeal)
            db.session.add(fusion)
            pokedex_full[fusion.pokedex_number] = fusion
    pokedex_full = pokedex | pokedex_full
    return pokedex_full


@func_timer
def convert_pokedex(pokedex: dict, session_add: bool = True) -> dict:
    """Converts the pokedex dictionaries into class instances for DB insertion."""
    japeal = db.session.scalar(db.select(Artist).where(Artist.artist_name=='japeal'))
    if not japeal:
        japeal = Artist(artist_name='japeal')

    pokedex_copy = pokedex.copy()
    for key, pokemon in pokedex_copy.items():
        stats = PokedexStats(
            hp=pokemon['hp'],
            attack=pokemon['attack'],
            defense=pokemon['defense'],
            sp_attack=pokemon['sp_attack'],
            sp_defense=pokemon['sp_defense'],
            speed=pokemon['speed']
        )
        pokedex_instance = Pokedex(
            pokedex_number=pokemon['pokedex_number'],
            species=pokemon['species'],
            type_primary=pokemon['type_primary'],
            type_secondary=pokemon['type_secondary'],
            family_order=pokemon['family_order'],
            name_head=pokemon['name_head'],
            name_body=pokemon['name_body'],
            stats=stats
        )
        default_sprite = Sprite(
            variant='',
            artist_info=japeal,
            pokedex_info=pokedex_instance
        )
        pokedex_instance.family_number = pokemon['family_number']
        pokedex[key] = pokedex_instance
    if session_add:
        db.session.add_all(pokedex.values())
    return pokedex


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


@func_timer
def commit_pokedex() -> None:
    """Commits session to DB with func_timer"""
    db.session.commit()


if __name__ == "__main__":
    main()