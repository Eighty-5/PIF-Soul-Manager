# Models
class User(db.Model, UserMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(20), unique=True)
    hash: Mapped[str] = mapped_column(String(128))

    saves: Mapped[list["Save"]] = relationship(back_populates="user_info", cascade="all, delete")
    

class Save(db.Model):
    __tablename__ = "save"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    save_number: Mapped[int]
    save_name: Mapped[Optional[str]] = mapped_column(String(32))
    ruleset: Mapped[int]
    route_tracking: Mapped[bool] = mapped_column(default=False)
    current_status: Mapped[bool] = mapped_column(default=False)

    user_info: Mapped["User"] = relationship(back_populates="saves")
    players: Mapped[list["Player"]] = relationship(back_populates="save_info", cascade="all, delete")
    recorded_routes: Mapped[list["Route"]] = relationship(back_populates="save_info", cascade="all, delete-orphan")
    soul_links: Mapped[list["SoulLink"]] = relationship(back_populates="save_info")


class Player(db.Model):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_id: Mapped[int] = mapped_column(ForeignKey("save.id"))
    player_number: Mapped[int]
    player_name: Mapped[str] = mapped_column(String(20))
    
    pokemon_caught: Mapped[list["Pokemon"]] = relationship(back_populates="player_info", cascade="all, delete")
    save_info: Mapped["Save"] = relationship(back_populates="players", foreign_keys=[save_id])


class Pokemon(db.Model):
    __tablename__ = "pokemon"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    pokedex_id: Mapped[int] = mapped_column(ForeignKey("pokedex.id"))
    route_id: Mapped[Optional[int]] = mapped_column(ForeignKey("route.id"))
    sprite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sprite.id"))
    soul_link_id: Mapped[Optional[int]] = mapped_column(ForeignKey("soul_link.id"))
    nickname: Mapped[Optional[str]] = mapped_column(String(30))
    position: Mapped[str] = mapped_column(String(5))

    player_info: Mapped["Player"] = relationship(back_populates="pokemon_caught")
    pokedex_info: Mapped["Pokedex"] = relationship()
    sprite: Mapped[Optional["Sprite"]] = relationship()
    route_caught: Mapped["Route"] = relationship(back_populates="caught_pokemons")
    soul_linked: Mapped[Optional["SoulLink"]] = relationship(back_populates="linked_pokemon", cascade="all, delete")

    

class SoulLink(db.Model):
    __tablename__ = "soul_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_id: Mapped[int] = mapped_column(ForeignKey("save.id"))
    soul_link_number: Mapped[int]

    linked_pokemon: Mapped[list["Pokemon"]] = relationship(back_populates="soul_linked")
    save_info: Mapped["Save"] = relationship(back_populates="soul_links")

class Route(db.Model):
    __tablename__ = "route"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_id: Mapped[int] = mapped_column(ForeignKey("save.id"))
    route_list_id: Mapped[int] = mapped_column(ForeignKey("route_list.id"))
    complete: Mapped[bool]

    caught_pokemons: Mapped[list["Pokemon"]] = relationship(back_populates="route_caught")
    save_info: Mapped["Save"] = relationship(back_populates="recorded_routes")
    route_info: Mapped["RouteList"] = relationship()

    

class RouteList(db.Model):
    __tablename__ = "route_list"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    

class Pokedex(db.Model):
    __tablename__ = "pokedex"

    id: Mapped[int] = mapped_column(primary_key=True)
    pokedex_number: Mapped[str] = mapped_column(String(17), unique=True)
    head_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pokedex.id"))
    body_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pokedex.id"))
    species: Mapped[str] = mapped_column(String(30))
    type_primary: Mapped[str] = mapped_column(String(10))
    type_secondary: Mapped[Optional[str]] = mapped_column(String(10))
    family_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pokedex_family.id"))
    family_order: Mapped[str] = mapped_column(String(10))
    name_1: Mapped[Optional[str]] = mapped_column(String(20))
    name_2: Mapped[Optional[str]] = mapped_column(String(20))

    head_pokemon: Mapped["Pokedex"] = relationship(back_populates="fusions_head", remote_side=[id], foreign_keys=[head_id])
    body_pokemon: Mapped["Pokedex"] = relationship(back_populates="fusions_body", remote_side=[id], foreign_keys=[body_id])
    fusions_head: Mapped[list["Pokedex"]] = relationship(
        back_populates="head_pokemon", remote_side=[head_id], foreign_keys=[head_id], cascade="all, delete-orphan")
    fusions_body: Mapped[list["Pokedex"]] = relationship(
        back_populates="body_pokemon", remote_side=[body_id], foreign_keys=[body_id], cascade="all, delete-orphan")
    stats: Mapped["PokedexStats"] = relationship(back_populates="info", cascade="all, delete-orphan")
    sprites: Mapped[list["Sprite"]] = relationship(back_populates="pokedex_info", cascade="all, delete-orphan")
    evolution_family: Mapped["PokedexFamily"] = relationship(back_populates="evolutions")

    

class PokedexFamily(db.Model):
    __tablename__ = "pokedex_family"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_number: Mapped[str] = mapped_column(String(17))
    evolutions: Mapped[Optional[list["Pokedex"]]] = relationship(back_populates="evolution_family")


class PokedexStats(db.Model):
    __tablename__ = "pokedex_stats"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    pokedex_id: Mapped[int] = mapped_column(ForeignKey("pokedex.id"))
    hp: Mapped[int]
    attack: Mapped[int]
    defense: Mapped[int]
    sp_attack: Mapped[int]
    sp_defense: Mapped[int]
    speed: Mapped[int]

    info: Mapped["Pokedex"] = relationship(back_populates="stats")



class Sprite(db.Model):
    __tablename__ = "sprite"

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_let: Mapped[str] = mapped_column(String(2))
    pokedex_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pokedex.id"))
    artist_id: Mapped[int] = mapped_column(ForeignKey("artist.id"))

    artists: Mapped["Artist"] = relationship(back_populates="sprites")
    pokedex_info: Mapped["Pokedex"] = relationship(back_populates="sprites")

    

class Artist(db.Model):
    __tablename__ = "artist"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    sprites: Mapped[Optional[list["Sprite"]]] = relationship(back_populates="artists", cascade="all, delete-orphan")
