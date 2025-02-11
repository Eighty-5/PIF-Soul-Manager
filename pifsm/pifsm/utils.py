from .extensions import db
from flask import flash, request, redirect, url_for
import time
from functools import wraps
import logging


def pokemon_verification(pokemon_id, save_file):
    pokemon_to_check = db.session.get(Pokemon, pokemon_id)
    if not pokemon_to_check or pokemon_to_check.player_info.save_info != save_file:
        return False
    else:
        return pokemon_to_check


