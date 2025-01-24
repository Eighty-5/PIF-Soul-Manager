from .extensions import db
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import String, ForeignKey, func, Uuid, UUID
from typing import Optional
from uuid import uuid4, UUID
from collections import Counter
from .utils import func_timer
from flask import flash

# Models

class CRUDMixin(object):
    @classmethod
    def create(cls, **kwargs):
        """Create a new record and save it the database."""
        instance = cls(**kwargs)
        return instance.save()

    def update(self, commit=True, **kwargs):
        """Update specific fields of a record."""
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        if commit:
            return self.save()
        return self

    def save(self, commit=True):
        """Save the record."""
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit: bool = True) -> None:
        """Remove the record from the database."""
        db.session.delete(self)
        if commit:
            return db.session.commit()
        return


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(20), unique=True)
    hash: Mapped[str] = mapped_column(String(128))

    saves: Mapped[list["Save"]] = relationship(back_populates="user_info", cascade="all, delete")

    def current_save(self):
        for save in self.saves:
            if save.current_status == True:
                return save
        return None
 
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, username={self.username!r})"
    

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
    soul_links: Mapped[list["SoulLink"]] = relationship(back_populates="save_info", order_by="SoulLink.soul_link_number", cascade="all, delete-orphan")

    def get_routelist_list(self):
        return [route.route_info for route in recorded_routes]

    def player_count(self):
        return len(self.players)
    
    def get_new_link_number(self):
        if len(self.soul_links) > 0:
            return self.soul_links[-1].soul_link_number + 1
        else:
            return 1

    def create_soul_link(self):
        new_soul_link = SoulLink(save_info=self, soul_link_number=self.get_new_link_number())
        db.session.commit()
        return new_soul_link

    def __repr__(self) -> str:
        return f"Save(id={self.id!r}, number={self.save_number!r}, user={self.user_info.username!r}, ruleset={self.ruleset!r})"


class Player(db.Model):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_id: Mapped[int] = mapped_column(ForeignKey("save.id"))
    player_number: Mapped[int]
    player_name: Mapped[str] = mapped_column(String(20))
    
    pokemon_caught: Mapped[list["Pokemon"]] = relationship(back_populates="player_info", order_by="Pokemon.soul_link_id.desc(), Pokemon.route_id", cascade="all, delete")
    save_info: Mapped["Save"] = relationship(back_populates="players", foreign_keys=[save_id])

    def party_length(self):
        return len(db.session.scalars(db.select(Pokemon).where(Pokemon.player_info==self, Pokemon.position=="party")).all())

    def __repr__(self) -> str:
        return f"Player(id={self.id!r}, number={self.player_number!r}, name={self.player_name!r}, user={self.save_info.user_info.username!r})"


class Pokemon(CRUDMixin, db.Model):
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
    route_caught: Mapped[Optional["Route"]] = relationship(back_populates="caught_pokemons")
    soul_linked: Mapped[Optional["SoulLink"]] = relationship(back_populates="linked_pokemon")

    def __eq__(self, other, *attributes):
        if not isinstance(other, type(self)):
            return NotImplemented
        if attributes:
            d = float('NaN')
            return all(self.__dict__.get(a, d) == other.__dict__.get(a, d) for a in attributes)
        return self.__dict__ == other.__dict__
        
    def player_number(self):
        return self.player_info.player_number

    def get_other_pokemon_route(self):
        pokemon_by_route = self.route_caught.caught_pokemon
        for pokemon in pokemon_by_route:
            if pokemon.player_info == self.player_info:
                return pokemon
    def set_default_sprite(self):
        new_sprite = db.session.scalar(db.select(Sprite).where(Sprite.pokedex_info==self.pokedex_info, Sprite.variant_let==''))
        self.sprite = new_sprite
        return db.session.commit()

    def switch_position(self, position):
        switched_pokemon = []
        if self.soul_linked:
            for pokemon in self.soul_linked.linked_pokemon:
                if position == "party" and pokemon.player_info.party_length() >= 6:
                    flash(f"{pokemon.player_info.player_name}'s party is full")
                    return False
                pokemon.position = position
            flash(f"{', '.join([pokemon.pokedex_info.species for pokemon in self.soul_linked.linked_pokemon])} switched position to '{position.title()}'")
        else:
            if position == "party" and self.player_info.party_length() >= 6:
                flash(f"{pokemon.player_info.player_name}'s party is full")
                return False
            self.position = position
            flash(f"{self.pokedex_info.species} switched position to '{position.title()}'")
        
        return db.session.commit()

    # def fusion(self, body_pokemon):
    #     if not isinstance(other, type(self)):
    #         return NotImplemented
    #     fusion_pokedex_info = db.session.scalar(db.select(Pokedex).where(Pokedex.head_pokemon==self.pokedex_info, Pokedex.body_pokemon==body_pokemon.pokedex_info))

    def __repr__(self) -> str:
        return (f"Pokemon(id={self.id!r}, player={self.player_info.player_name!r}, pokedex_number={self.pokedex_info.pokedex_number!r}, "
                f"species={self.pokedex_info.species!r}, nickname={self.nickname!r}, "
                f"position={self.position!r})")
    

class SoulLink(db.Model):
    __tablename__ = "soul_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_id: Mapped[int] = mapped_column(ForeignKey("save.id"))
    soul_link_number: Mapped[int]
    # position: Mapped[str] = mapped_column(String(5))

    linked_pokemon: Mapped[Optional[list["Pokemon"]]] = relationship(back_populates="soul_linked", cascade="all, delete")
    save_info: Mapped["Save"] = relationship(back_populates="soul_links")

    def linked_players(self):
        return [pokemon.player_info for pokemon in self.linked_pokemon]

    def __repr__(self) -> str:
        return f"SoulLink(id={self.id!r}, link_number={self.soul_link_number!r}, save_id={self.save_id!r})"


class Route(db.Model):
    __tablename__ = "route"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_id: Mapped[int] = mapped_column(ForeignKey("save.id"))
    route_list_id: Mapped[int] = mapped_column(ForeignKey("route_list.id"))
    complete: Mapped[bool]

    caught_pokemons: Mapped[list["Pokemon"]] = relationship(back_populates="route_caught")
    save_info: Mapped["Save"] = relationship(back_populates="recorded_routes")
    route_info: Mapped["RouteList"] = relationship()

    def __repr__(self) -> str:
        return f"Route(id={self.id!r}, save_id={self.save_id!r}, route_name={self.route_info.name!r})"
    

class RouteList(db.Model):
    __tablename__ = "route_list"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    # soft_delete: Mapped[bool]


    # @classmethod
    # def total_count(cls) -> int:
    #     return db.session.scalar(db.select(func.count("*")).select_from(RouteList))

    def __repr__(self) -> str:
        return f"RouteList(id={self.id!r}, name={self.name!r})"
    

class Pokedex(CRUDMixin, db.Model):
    __tablename__ = "pokedex"

    id: Mapped[int] = mapped_column(primary_key=True)
    pokedex_number: Mapped[str] = mapped_column(String(17), unique=True)
    head_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pokedex.id"), index=True)
    body_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pokedex.id"), index=True)
    species: Mapped[str] = mapped_column(String(30))
    type_primary: Mapped[str] = mapped_column(String(10))
    type_secondary: Mapped[Optional[str]] = mapped_column(String(10))
    family: Mapped[str] = mapped_column(String(17))
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

    def evolutions(self):
        return self.evolution_family.evolutions

    def final_evolution(self):
        return self.evolutions()[-1]

    def first_evolution(self):
        return self.evolutions()[0]

    def split_names(self) -> str:
        if self.head_pokemon:
            return f"{self.head_pokemon.species} + {self.body_pokemon.species}"
        else:
            return self.species 
        
    def typing(self) -> str:
        if self.type_secondary:
            return f"{self.type_primary} / {self.type_secondary}"
        else:
            return f"{self.type_primary}"
    
    def __eq__(self, other, *attributes):
        if not isinstance(other, type(self)):
            return NotImplemented
        if attributes:
            d = float('NaN')
            return all(self.__dict__.get(a, d) == other.__dict__.get(a, d) for a in attributes)
        return self.__dict__ == other.__dict__
    

    def __repr__(self) -> str:
        if self.head_pokemon:
            return (f"Pokedex(id={self.id!r}, pokedex_number={self.pokedex_number!r}, species={self.species!r}, "
                    f"head_pokemon={self.head_pokemon.species!r}, body_pokemon={self.body_pokemon.species!r}, "
                    f"type_primary={self.type_primary!r}, type_secondary={self.type_secondary!r}, "
                    f"family={self.family!r}, family_order={self.family_order!r})"
                    )
        else:
            return (f"Pokedex(id={self.id!r}, pokedex_number={self.pokedex_number!r}, species={self.species!r}, "
                    f"type_primary={self.type_primary!r}, type_secondary={self.type_secondary!r}, "
                    f"family={self.family!r}, family_order={self.family_order!r}, "
                    f"name_1={self.name_1}, name_2={self.name_2})"
                    )
    

class PokedexFamily(db.Model):
    __tablename__ = "pokedex_family"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_number: Mapped[str] = mapped_column(String(17))
    evolutions: Mapped[Optional[list["Pokedex"]]] = relationship(back_populates="evolution_family", order_by="Pokedex.family_order")


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
    
    def __eq__(self, other, *attributes):
        if not isinstance(other, type(self)):
            return NotImplemented
        
        if attributes:
            d = float('NaN')
            return all(self.__dict__.get(a, d) == other.__dict__.get(a, d) for a in attributes)
        
        return self.__dict__ == other.__dict__
    

    def __repr__(self) -> str:
        return (f"Stat(id={self.id!r}, species={self.info.species!r}, hp={self.hp!r}, attack={self.attack!r}, "
                f"defense={self.defense!r}, sp_attack={self.sp_attack!r}, sp_defense={self.sp_defense!r}, "
                f"speed={self.speed!r}, total={self.total()!r})")


class Sprite(db.Model):
    __tablename__ = "sprite"

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_let: Mapped[str] = mapped_column(String(2))
    pokedex_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pokedex.id"))
    artist_id: Mapped[int] = mapped_column(ForeignKey("artist.id"))

    artists: Mapped["Artist"] = relationship(back_populates="sprites")
    pokedex_info: Mapped["Pokedex"] = relationship(back_populates="sprites")

    def sprite_group(self):
        if self.pokedex_info.head_pokemon:
            return f"{self.pokedex_info.head_pokemon.pokedex_number}"
        else:
            return f"{self.pokedex_info.pokedex_number}"

    def sprite_code(self):
        return f"{self.pokedex_info.pokedex_number}{self.variant_let}"
    
    def __repr__(self) -> str:
        return (f"Sprite(id={self.id!r}, sprite_code={self.sprite_code()!r}, species={self.pokedex_info.species}, "
                f"artist={self.artists.name!r}), sprite_group={self.sprite_group()!r}")
    

class Artist(db.Model):
    __tablename__ = "artist"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    sprites: Mapped[Optional[list["Sprite"]]] = relationship(back_populates="artists", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Artist(id={self.id!r}, name={self.name!r})"
    
