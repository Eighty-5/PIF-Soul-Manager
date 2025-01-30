import csv

# Getting Gen 7 Stats
# 1. Copy HTML body of table from https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_base_stats_in_Generation_VII
# 2. Paste into stats.txt file
# 3. Run script
# 4. A new csv file titled 'if-base-dex-new-stats.csv' that contains all gen 7 stats from pokedex
# 5. If pokemon is not in gen 7 national dex or scripts couldn't determine any matching pokemon stats are left blank
# 6. Will need to fill in stats manually
# 7. Known required corrections:
#       Pumpkaboo and Gourgeist need manualy corrects
#       

# Known incorrect names
KNOWN_INCORRECT_SPECIES = {
    'Nidoran F': 'Nidoran%E2%99%80',
    'Nidoran M': 'Nidoran%E2%99%82',
    "Farfetch'd": 'Farfetch%27d',
    'Mr. Mime': 'Mr._Mime',
    'Mime Jr.': 'Mime_Jr.',
    'Aegislash': 'Shield Forme',
    'Giratina': 'Altered Forme',
    'Deoxys': 'Normal Forme',
    'Oricorio Baile': 'Oricorio',
    'Oricorio Pom-Pom': 'Oricorio',
    "Oricorio Pa'u": 'Oricorio',
    'Oricorio Sensu': 'Oricorio',
    'Lycanroc Midday': 'Midday Form',
    'Lycanroc Midnight': 'Midnight Form',
    'Meloetta Aria': 'Aria Forme',
    'Meloetta Pirouette': 'Pirouette Forme',
    'Minior': 'Meteor Form',
    'Minior Core': 'Core'
}

# KNOWN_INCORRECT_SPECIES = {}

def main():
    full_lst = []
    pokemon_lst = []
    with (open('stats.txt', 'r') as old_file):
        count = 1
        while True:
            line = str(old_file.readline())
            species = find_between(line, '<td class="l"><a href="/wiki/', '_(Pok%')
            if line[:12] == '<td style="b':
                stat = find_between(line, '>', '\n')
                pokemon_lst.append(stat)
                if len(pokemon_lst) == 7:
                    full_lst.append(pokemon_lst)
                    pokemon_lst = []
            if species != "":
                if '<br><small>' in line:
                    species = find_between(line, '<br><small>', '</small>')
                pokemon_lst.append(species)
            if not line:
                break
    new_stats_dict = {}
    for pokemon_lst in full_lst:
        new_stats_dict[pokemon_lst[0]] = {
            'hp': pokemon_lst[1],
            'attack': pokemon_lst[2],
            'defense': pokemon_lst[3],
            'sp_attack': pokemon_lst[4],
            'sp_defense': pokemon_lst[5],
            'speed': pokemon_lst[6],
        }
    full_lst.clear()

    pokedex = {}
    with (open('if-base-dex.csv', 'r') as dexfile, open('if-base-dex-new-stats.csv', 'w') as newdexfile):
        pokedex = csv.DictReader(dexfile)
        newdexfile.write("number,species,type_primary,type_secondary,name_1,name_2,family,family_order,hp,attack,defense,sp_attack,sp_defense,speed\n")
        for pokemon in pokedex:
            species = pokemon['species']
            if species in new_stats_dict:
                pokemon['hp'] = new_stats_dict[species]['hp']
                pokemon['attack'] = new_stats_dict[species]['attack']
                pokemon['defense'] = new_stats_dict[species]['defense']
                pokemon['sp_attack'] = new_stats_dict[species]['sp_attack']
                pokemon['sp_defense'] = new_stats_dict[species]['sp_defense']
                pokemon['speed'] = new_stats_dict[species]['speed']
                new_stats_dict.pop(species)
            elif species in KNOWN_INCORRECT_SPECIES:
                species = KNOWN_INCORRECT_SPECIES[species]
                pokemon['hp'] = new_stats_dict[species]['hp']
                pokemon['attack'] = new_stats_dict[species]['attack']
                pokemon['defense'] = new_stats_dict[species]['defense']
                pokemon['sp_attack'] = new_stats_dict[species]['sp_attack']
                pokemon['sp_defense'] = new_stats_dict[species]['sp_defense']
                pokemon['speed'] = new_stats_dict[species]['speed']
                if not species == 'Oricorio':
                    new_stats_dict.pop(species)
            else:
                pokemon['hp'] = ''
                pokemon['attack'] = ''
                pokemon['defense'] = ''
                pokemon['sp_attack'] = ''
                pokemon['sp_defense'] = ''
                pokemon['speed'] = ''
            newdexfile.write(','.join([col for col in pokemon.values()]) + '\n')
    # for pokemon, stats in new_stats_dict.items():
    #     print(f"{pokemon}: {stats}")

def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


if __name__ == "__main__":
    main()