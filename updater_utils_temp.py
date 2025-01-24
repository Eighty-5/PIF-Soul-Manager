def create_fusion_pokedex_number(head_pokemon, body_pokemon):
    pokedex_number_1 = head_pokemon.pokedex_number
    pokedex_number_2 = body_pokemon.pokedex_number
    return f"{pokedex_number_1}.{pokedex_number_2}"


def create_fusion_species(head_pokemon, body_pokemon):
    name_1 = head_pokemon.name_1
    name_2 = body_pokemon.name_2
    if name_1[-1] == name_2[0]:
        species = name_1 + name_2[1:]
    else:
        species = name_1 + name_2
    return species


def create_fusion_family_number(head_pokemon, body_pokemon):
    family_1 = head_pokemon.evolution_family.family_number
    family_2 = body_pokemon.evolution_family.family_number
    return f"{family_1}.{family_2}"


def create_fusion_family_order(head_pokemon, body_pokemon):
    family_order_1 = head_pokemon.family_order
    family_order_2 = body_pokemon.family_order
    return f"{family_order_1}.{family_order_2}"



def create_fusion_typing(head_pokemon, body_pokemon):
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


def create_fusion_stats(head_pokemon, body_pokemon):
    fused_stats = PokedexStats(
        hp=int(2 * (head_pokemon.stats.hp)/3 + (body_pokemon.stats.hp)/3),
        attack=int(2 * (body_pokemon.stats.attack)/3 + (head_pokemon.stats.attack)/3),
        defense=int(2 * (body_pokemon.stats.defense)/3 + (head_pokemon.stats.defense)/3),
        sp_attack=int(2 * head_pokemon.stats.sp_attack/3 + body_pokemon.stats.sp_attack/3),
        sp_defense=int(2 * head_pokemon.stats.sp_defense/3 + body_pokemon.stats.sp_defense/3),
        speed=int(2 * body_pokemon.stats.speed/3 + head_pokemon.stats.speed/3)
    )
    return fused_stats


def create_fusion(head_pokemon, body_pokemon):
    pokedex_number = create_fusion_pokedex_number(head_pokemon, body_pokemon)
    type_primary, type_secondary = create_fusion_typing(head_pokemon, body_pokemon)
    stats = create_fusion_stats(head_pokemon, body_pokemon)
    species = create_fusion_species(head_pokemon, body_pokemon)
    family_number = create_fusion_family_number(head_pokemon, body_pokemon)
    family = db.session.scalar(db.select(PokedexFamily).where(PokedexFamily.family_number==fusion_family_number))
    family_order = create_fusion_family_order(head_pokemon, body_pokemon)
    if not fusion_family:
        fusion_family = PokedexFamily(
            family_number = fusion_family_number
        )
    fusion = Pokedex(
        pokedex_number=pokedex_number,
        species=species,
        type_primary=type_primary,
        type_secondary=type_secondary,
        family_order=family_order,
        evolution_family=family,
        head_pokemon=head_pokemon,
        body_pokemon=body_pokemon,
        stats=stats
    )
    return fusion
