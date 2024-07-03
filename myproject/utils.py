from .extensions import db
from .models import Players, Pokedex, Pokemon, Sessions, Users
from flask import flash, request, redirect, url_for

def get_default_vars(id):
    current_session = Sessions.query.get(
        Users.query.get_or_404(id).current_session)
    if not current_session:
        return redirect(url_for('main.select_session'))
    current_session_id = current_session.id
    ruleset = current_session.ruleset
    return current_session, current_session_id, ruleset

