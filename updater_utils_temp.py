def update_fusion_family_order(pokemon):
    head_fusions_to_update = pokemon.fusions_head
    body_fusions_to_update = pokemon.fusions_body
    for fusion in head_fusions_to_update + body_fusions_to_update:
        fusion.family_order = f"{fusion.head_pokemon.family_order}.{fusion.body_pokemon.family_order}"


def update_stats(pokemon):
    head_fusions_to_update = pokemon.fusions_head
    body_fusions_to_update = pokemon.fusions_body
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



