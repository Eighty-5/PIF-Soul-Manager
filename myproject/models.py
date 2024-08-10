from .extensions import db
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import String, ForeignKey, func
from typing import Optional

# Models
# Create Users model
class User(db.Model, UserMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(20), unique=True)
    hash: Mapped[str] = mapped_column(String(128))

    saves: Mapped[list["Save"]] = relationship(back_populates="users", cascade="all, delete")
 
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, username={self.username!r})"
    
# Create Saves Model
class Save(db.Model):
    __tablename__ = "save"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    number: Mapped[int]
    ruleset: Mapped[int]
    route_tracking: Mapped[bool] = mapped_column(default=False)
    current: Mapped[bool] = mapped_column(default=False)

    players: Mapped[list["Player"]] = relationship(back_populates="saves", cascade="all, delete")
    users: Mapped["User"] = relationship(back_populates="saves")

    def player_count(self):
        return db.session.scalar(db.select(func.count("*")).select_from(Player).where(Player.saves==self))

    def __repr__(self) -> str:
        return f"Save(number={self.number!r}, user={self.users.username!r})"


# Create Players model
class Player(db.Model):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_id: Mapped[int] = mapped_column(ForeignKey("save.id"), index=True)
    number: Mapped[int]
    name: Mapped[str] = mapped_column(String(20))
    
    pokemons: Mapped[list["Pokemon"]] = relationship(back_populates="player", cascade="all, delete")
    saves: Mapped["Save"] = relationship(back_populates="players", foreign_keys=[save_id])

    def party_length(self):
        return db.session.scalar(db.select(func.count("*")).select_from(Pokemon).where(Pokemon.player==self, Pokemon.position=="party"))

    def __repr__(self) -> str:
        return f"Player(number={self.number!r}, name={self.name!r}, user={self.saves.users.username!r})"

# Create Pokemon Model
class Pokemon(db.Model):
    __tablename__ = "pokemon"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), index=True)
    pokedex_id: Mapped[int] = mapped_column(ForeignKey("pokedex.id"), index=True)
    sprite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sprite.id"), index=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(30))
    link_id: Mapped[int]
    linked: Mapped[bool]
    route: Mapped[Optional[int]]
    position: Mapped[str] = mapped_column(String(5))

    player: Mapped["Player"] = relationship(back_populates="pokemons")
    info: Mapped["Pokedex"] = relationship()
    sprite: Mapped[Optional["Sprite"]] = relationship()

    def set_new_sprite(self):
        pass

    def __repr__(self) -> str:
        return (f"Pokemon(id={self.id!r}, player={self.player.name!r}, "
                f"pokedex_number={self.info.number!r}, species={self.info.species!r}, "
                f"nickname={self.nickname!r}, link_id={self.link_id!r}, "
                f"linked={self.linked!r}, route={self.route!r}, position={self.position!r})"
                )

# Create Pokedex Model
class Pokedex(db.Model):
    __tablename__ = "pokedex"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(17), unique=True, nullable=False)
    head_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pokedex.id"), index=True)
    body_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pokedex.id"), index=True)
    species: Mapped[str] = mapped_column(String(30))
    type_primary: Mapped[str] = mapped_column(String(10))
    type_secondary: Mapped[Optional[str]] = mapped_column(String(10))
    family: Mapped[str] = mapped_column(String(17), index=True)
    family_order: Mapped[str] = mapped_column(String(10))
    name_1: Mapped[Optional[str]] = mapped_column(String(20))
    name_2: Mapped[Optional[str]] = mapped_column(String(20))

    head: Mapped["Pokedex"] = relationship(back_populates="fusions_head", remote_side=[id], foreign_keys=[head_id])
    body: Mapped["Pokedex"] = relationship(back_populates="fusions_body", remote_side=[id], foreign_keys=[body_id])
    fusions_head: Mapped[list["Pokedex"]] = relationship(back_populates="head", remote_side=[head_id], foreign_keys=[head_id], cascade="all, delete-orphan")
    fusions_body: Mapped[list["Pokedex"]] = relationship(back_populates="body", remote_side=[body_id], foreign_keys=[body_id], cascade="all, delete-orphan")
    stats: Mapped["PokedexStats"] = relationship(back_populates="info", cascade="all, delete-orphan")
    sprites: Mapped[list["Sprite"]] = relationship(back_populates="pokedex_info", cascade="all, delete-orphan")

    def evolutions(self) -> str:
        return db.session.scalars(db.select(Pokedex).where(Pokedex.family==self.family).order_by(Pokedex.family_order))

    def split_names(self) -> str:
        if self.head:
            return f"{self.head.species} + {self.body.species}"
        else:
            return self.species
        
    def typing(self) -> str:
        if self.type_secondary:
            return f"{self.type_primary} / {self.type_secondary}"
        else:
            return f"{self.type_primary}"

    def __repr__(self) -> str:
        if self.head:
            return (f"Pokedex(id={self.id!r}, number={self.number!r}, "
                    f"species={self.species!r}, head={self.head.species!r}, "
                    f"body={self.body.species!r}, type_primary={self.type_primary!r}, "
                    f"type_secondary={self.type_secondary!r}, family={self.family!r}, "
                    f"family_order={self.family_order!r})"
                    )
        else:
            return (f"Pokedex(id={self.id!r}, number={self.number!r}, "
                    f"species={self.species!r}, type_primary={self.type_primary!r}, "
                    f"type_secondary={self.type_secondary!r}, "
                    f"family={self.family!r}, family_order={self.family_order!r}, "
                    f"name_1={self.name_1}, name_2={self.name_2})"
                    )


class PokedexStats(db.Model):
    __tablename__ = "pokedex_stats"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    pokedex_id: Mapped[int] = mapped_column(ForeignKey("pokedex.id"), index=True)
    hp: Mapped[int]
    attack: Mapped[int]
    defense: Mapped[int]
    sp_attack: Mapped[int]
    sp_defense: Mapped[int]
    speed: Mapped[int]

    info: Mapped["Pokedex"] = relationship(back_populates="stats")

    def total(self):
        return self.attack + self.defense + self.sp_attack + self.sp_defense + self.speed

    def __repr__(self) -> str:
        return (f"Stat(id={self.id!r}, species={self.info.species!r}, "
                f"hp={self.hp!r}, attack={self.attack!r}, "
                f"defense={self.defense!r}, sp_attack={self.sp_attack!r}, "
                f"sp_defense={self.sp_defense!r}, speed={self.speed!r}, "
                f"total={self.total()!r})")


# Sprite/Artist Model
class Sprite(db.Model):
    __tablename__ = "sprite"

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_let: Mapped[str] = mapped_column(String(2))
    pokedex_id: Mapped[int] = mapped_column(ForeignKey("pokedex.id"), index=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artist.id"), index=True)

    artists: Mapped["Artist"] = relationship(back_populates="sprites")
    pokedex_info: Mapped["Pokedex"] = relationship(back_populates="sprites")

    def sprite_group(self):
        if self.pokedex_info.head:
            return f"{self.pokedex_info.head.number}"
        else:
            return f"{self.pokedex_info.number}"

    def sprite_code(self):
        return f"{self.pokedex_info.number}{self.variant_let}"
    
    def __repr__(self) -> str:
        return (f"Sprite(id={self.id!r}, sprite_code={self.sprite_code()!r}, "
                f"artist={self.artists.name!r}), "
                f"sprite_group={self.sprite_group()!r}"
                )
    

class Artist(db.Model):
    __tablename__ = "artist"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100, collation='utf8mb4_0900_as_cs'), unique=True, index=True)

    sprites: Mapped[Optional[list["Sprite"]]] = relationship(back_populates="artists", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Artist(id={self.id!r}, name={self.name!r})"
    
