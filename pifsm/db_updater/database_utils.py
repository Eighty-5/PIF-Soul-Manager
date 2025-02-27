from pifsm.extensions import db
from pifsm.decorators import func_timer
from typing import Type
from pifsm.models import *
from datetime import datetime
import os
import shutil
import csv
from itertools import chain


@func_timer
def create_pokedex_html(pokedex_html_path: str) -> None:
    """Creates and saves 'pokedex_list.html' for use in adding pokemon to save"""
    base_pokedex = db.session.scalars(db.select(Pokedex).where(Pokedex.head_pokemon==None))
    # Quick and Dirty sort change later
    base_pokedex = {int(pokemon.pokedex_number):pokemon.species for pokemon in base_pokedex}
    count = 1
    pokedex_lst = []
    while count <= len(base_pokedex):
        pokedex_lst.append(base_pokedex[count])
        count += 1
    with open(pokedex_html_path, 'w') as pokedex_html_file:
        pokedex_html_file.write('<datalist id="pokedex">\n')
        for pokemon in pokedex_lst:
            pokedex_html_file.write(f'  <option value="{pokemon}"></option>\n')
        pokedex_html_file.write('</datalist>')


def create_fusion_pokedex_number(head_pokemon: Type[Pokedex], body_pokemon: Type[Pokedex]) -> str:
    pokedex_number_1 = head_pokemon.pokedex_number
    pokedex_number_2 = body_pokemon.pokedex_number
    fusion_pokedex_number = f"{pokedex_number_1}.{pokedex_number_2}"
    return fusion_pokedex_number


def create_fusion_species(head_pokemon: Type[Pokedex], body_pokemon: Type[Pokedex]) -> str:
    name_head = head_pokemon.name_head
    name_body = body_pokemon.name_body
    if name_head[-1] == name_body[0]:
        fusion_species = name_head + name_body[1:]
    else:
        fusion_species = name_head + name_body
    return fusion_species


def create_fusion_typing(head_pokemon: Type[Pokedex], body_pokemon: Type[Pokedex]) -> (str, str):
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
    return fusion_type_primary, fusion_type_secondary


def create_fusion_family(head_pokemon: Type[Pokedex], body_pokemon: Type[Pokedex]):
    family_1 = head_pokemon.family.family_number
    family_2 = body_pokemon.family.family_number
    new_family_number = f"{family_1}.{family_2}"
    db.session.scalar
    if new_family_number in family_dict:
        fusion_family = family_dict[new_family_number]
    else:
        fusion_family = Family(
            family_number=new_family_number
        )
        db.session.add(fusion_family)
        family_dict[new_family_number] = fusion_family
    return (fusion_family, family_dict)


def create_fusion_family_order(head_pokemon: Type[Pokedex], body_pokemon: Type[Pokedex]):
    family_order_1 = head_pokemon.family_order
    family_order_2 = body_pokemon.family_order
    fusion_family_order = f"{family_order_1}.{family_order_2}"
    return fusion_family_order


def create_fusion_stats(head_pokemon: Type[Pokedex], body_pokemon: Type[Pokedex]):
    fusion_stats = PokedexStats(
        hp = int(2 * (head_pokemon.stats.hp)/3 + (body_pokemon.stats.hp)/3),
        attack = int(2 * (body_pokemon.stats.attack)/3 + (head_pokemon.stats.attack)/3),
        defense = int(2 * (body_pokemon.stats.defense)/3 + (head_pokemon.stats.defense)/3),
        sp_attack = int(2 * (head_pokemon.stats.sp_attack)/3 + (body_pokemon.stats.sp_attack)/3),
        sp_defense = int(2 * (head_pokemon.stats.sp_defense)/3 + (body_pokemon.stats.sp_defense)/3),
        speed = int(2 * (body_pokemon.stats.speed)/3 + (head_pokemon.stats.speed)/3)
    )
    return fusion_stats


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


def sanitized_input(prompt: str, type_=None, min_=None, max_=None, range_=None):
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
        

def backup_database(db_type: str, db_backup_path, db_path=None):
    """Makes a backup of the database"""
    start_time = datetime.now().strftime('%Y-%b-%d_T%H-%M-%S')
    db_backup_filename = start_time + '_pifsm.db'
    db_backup_path = f"{db_backup_path}{db_backup_filename}"

    if db_type == 'sqlite':
        src = db_path
        dst = db_backup_path
        shutil.copyfile(src, dst)
    elif db_type == 'mysql':
        subprocess.run(f"mysqldump -u root -p {os.getenv('DB_NAME')} > {db_backup_path}", shell=True)


@func_timer
def read_pokedex_csv(dict_key: str, base_pokedex_path: str, removed_pokedex_path: str = None) -> dict:
    """Creates a dictionary of form '{PokedexNumber:{Pokemon}}' from a csv pokedex file."""
    """If there are duplicates print all duplicates to console and exit script."""
    assert dict_key in ['species', 'pokedex_number']
    bdexfile = open(base_pokedex_path, newline='')
    pokedex_files = [bdexfile]
    pokedexes = [csv.DictReader(bdexfile)]
    if removed_pokedex_path:
        rdexfile = open(removed_pokedex_path, newline='')
        pokedex_files.append(rdexfile)
        pokedexes.append(csv.DictReader(rdexfile))
    pokedexes = chain.from_iterable(pokedexes)

    pokedex_dict = {}
    pokedex_species = {}
    duplicates = []
    for row in pokedexes:
        pokedex_number, species = row['pokedex_number'], row['species']
        if species in pokedex_species:
            duplicates.append((
                {'pokedex_number':pokedex_number, 'species':species}, 
                {'pokedex_number':pokedex_species[species],'species':species}
            ))
        if pokedex_number in pokedex_dict:
            duplicates.append((
                {'pokedex_number':pokedex_number, 'species':species}, 
                {'pokedex_number':pokedex_number,'species':pokedex_dict[pokedex_number]['species']}
            ))
        pokedex_dict[row[dict_key]] = {
            'pokedex_number': row['pokedex_number'],
            'species': row['species'],
            'type_primary': row['type_primary'],
            'type_secondary': row['type_secondary'],
            'family_number': row['family_number'],
            'family_order': row['family_order'],
            'name_head': row['name_head'],
            'name_body': row['name_body'],
            'hp': int(row['hp']),
            'attack': int(row['attack']),
            'defense': int(row['defense']),
            'sp_attack': int(row['sp_attack']),
            'sp_defense': int(row['sp_defense']),
            'speed': int(row['speed'])
        }
        pokedex_species[species] = pokedex_number

    for dexfile in pokedex_files:
        dexfile.close()

    if duplicates:
        print("Duplicates found, please address and edit csv file and run program again")
        for dupe in duplicates:
            print(dupe)
        quit()
    return pokedex_dict


@func_timer
def create_family_instances(pokedex: dict, family_dict: dict = None) -> dict:
    """Creates family class instances adhering to unique family number constraint."""
    if not family_dict:
        family_dict = {}
    for pokedex_number, pokemon in pokedex.items():
        if pokemon.family_number in family_dict:
            pokemon.family = family_dict[pokemon.family_number]
        else:
            family = Family(
                family_number=pokemon.family_number
            )
            pokemon.family = family
            family_dict[family.family_number] = family
    return family_dict


def create_fusion(head_pokemon: Type[Pokedex], body_pokemon: Type[Pokedex], japeal: Type[Artist]) -> Type[Pokedex]:
    """Creates fusion pokemon from given head and body pokemon."""
    fusion_pokedex_number = f"{head_pokemon.pokedex_number}.{body_pokemon.pokedex_number}"
    fusion_species = create_fusion_species(head_pokemon, body_pokemon)
    fusion_type_primary, fusion_type_secondary = create_fusion_typing(head_pokemon, body_pokemon)
    fusion_family_number = f"{head_pokemon.family_number}.{body_pokemon.family_number}"
    fusion_family_order = f"{head_pokemon.family_order}.{body_pokemon.family_order}"
    stats = create_fusion_stats(head_pokemon, body_pokemon)
    fusion = Pokedex(
        pokedex_number=fusion_pokedex_number,
        species=fusion_species,
        type_primary=fusion_type_primary,
        type_secondary=fusion_type_secondary,
        family_order=fusion_family_order,
        stats=stats,
        head_pokemon=head_pokemon,
        body_pokemon=body_pokemon
    )
    default_sprite = Sprite(
        variant='',
        artist_info=japeal,
        pokedex_info=fusion
    )
    # Temp values
    fusion.family_number = fusion_family_number
    return fusion


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