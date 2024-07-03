from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from ...extensions import db
from ...models import Users, Players, Pokedex, Pokemon, Sessions, Artists
from ...webforms import CreateSessionForm
from .main_utils import find_first_missing_session_number, get_column_widths
from ...utils import get_default_vars
from ..pokemon.pokemon import MANUAL_RULESET, AUTO_RULESET, ROUTE_RULESET, SPECIAL_RULESET
from sqlalchemy import and_

main = Blueprint('main', __name__, template_folder='templates', static_folder='static', static_url_path='/main/static')

# Index
@main.route('/')
def index():
    return render_template('about.html')


# Create a New Session route
@main.route('/session/create', methods=['GET', 'POST'])
@login_required
def create_session():

    # Set variables
    form = CreateSessionForm()
    id = current_user.id
    sessions = Sessions.query.filter(Sessions.user_id==id)
        
    # If session count is >=3 return them to the session select page
    if sessions.count() >= 3:
        flash("Already at max session count. Please delete one of your sessions to add another")
        return redirect(url_for('main.select_session'))
    players = [{'Player 1': 'Player 1 Name'},
               {'Player 2': 'Player 2 Name'},
               {'Player 3': 'Player 3 Name'},
               {'Player 4': 'Player 4 Name'}]
    form = CreateSessionForm(player_names=players)

    # Validate that form was submited
    if form.validate_on_submit():
        session_num_lst = [session.number for session in sessions]
        ruleset=int(form.ruleset.data)
        route_tracking = True if ruleset != 1 else False
        if len(session_num_lst) < 3:
            new_session_num = find_first_missing_session_number(session_num_lst)
            if not new_session_num == False:
                new_session = Sessions(user_id=id, number=new_session_num, ruleset=int(form.ruleset.data), route_tracking=route_tracking)
                db.session.add(new_session)
                db.session.commit()
                player_count = 1
                for player in form.player_names:
                    if player.player_name.data:
                        new_player = Players(session_id=new_session.id, number=player_count, name=player.player_name.data)
                        db.session.add(new_player)
                        db.session.commit()
                        player_count = player_count + 1
                flash("Session Added Successfully")
                return redirect('/session/select')
        
        flash("Already at max session count. Please delete one of your sessions to add another")
        return redirect('/session/select')
    form.player_num.data = ""
    for player in form.player_names:
        player.player_name.data = ""
    form.ruleset.data = ""
    return render_template('create_session.html', form=form)


# Delete a Session route
@main.route('/session/delete', methods=['GET', 'POST'])
@login_required
def delete_session():
    id = current_user.id
    if request.method == 'POST':
        session_number = request.form['session_to_delete']
        session_to_delete = Sessions.query.filter_by(user_id=id, number=session_number).first()
    if id == session_to_delete.user.id or current_user.id == 1:
        db.session.delete(session_to_delete)
        db.session.commit()
        if Users.query.get(id).current_session == session_number:
            Users.query.get(id).current_session = None
            db.session.commit()
        if current_user.id == 1:
            return redirect('/admin/sessions')
        else:
            return redirect('/session/select')
    else:
        flash("You do not have authorization to delete this session")
        return redirect('/session/select')
    

@main.route('/session/select/', methods=['GET', 'POST'])
@login_required
def select_session():
    id = current_user.id
    sessions = Sessions.query.filter_by(user_id=id).order_by(Sessions.number)
    if Sessions.query.filter_by(user_id=id).first() == None:
            flash("Please Create a Session First")
            return redirect(url_for('main.create_session')) 
    if request.method == 'POST':
        current_session_to_update = Users.query.get_or_404(id)
        current_session_id = Sessions.query.filter_by(user_id=id, number=request.form['session_number']).first().id
        current_session_to_update.current_session = current_session_id
        db.session.commit()
        return redirect(url_for('main.view_session'))
    return render_template('select_session.html', sessions=sessions)


# Redirect to Session Manager for Navbar
@main.route('/session/view', methods=['GET', 'POST'])
@login_required
def view_session():
    current_session_id = Users.query.get(current_user.id).current_session
    try:
        current_session_num = Sessions.query.get(current_session_id).number
        return redirect(url_for('main.session_manager', session_num=current_session_num))
    except AttributeError:
        flash("Please Select a Session to View")
        return redirect(url_for('main.select_session'))


@main.route('/session/<int:session_num>', methods=['GET', 'POST'])
@login_required
def session_manager(session_num):
    id = current_user.id
    session = Sessions.query.filter(Sessions.user_id==id, Sessions.number==session_num).first()
    if session is None:
        flash("No record of that session")
        return redirect(url_for('main.select_session'))
    players = Players.query.filter(Players.session_id==session.id)
    party_length = Pokemon.query.filter(Pokemon.player_id==players.first().id, Pokemon.position=='party').count()
    column_widths = get_column_widths(players.count())

    # Evolutions
    evolutions_dict = {}
    for player in players:
        for pokemon in player.pokemon:
            evolution_lst = []
            evolutions = Pokedex.query.filter_by(family=pokemon.info.family).order_by(Pokedex.family_order)
            for evolution in evolutions:
            for evolution in evolutions:
                base_pokemon_1 = Pokedex.query.filter_by(number=evolution.base_id_1).first()
                base_pokemon_2 = Pokedex.query.filter_by(number=evolution.base_id_2).first() 
                if base_pokemon_1 is not None:
                    evo_names = f"{base_pokemon_1.species} + {base_pokemon_2.species}"
                    evo_number = evolution.number
                else:
                    evo_names = evolution.species
                    evo_number = evolution.number
                evolution_lst.append({'number':evo_number, 'names':evo_names})
            evolutions_dict[pokemon.pokedex_number] = evolution_lst
            
    return render_template('session_manager.html', 
                           session_num=session_num, 
                           session=session, 
                           evolutions_dict=evolutions_dict,  
                           party_length=party_length,
                           column_widths=column_widths)


@main.route('/preview_fusions/<int:player_num>/<int:link_id>', methods=['GET', 'POST'])
@login_required
def preview_fusions(player_num, link_id):
    current_session, current_session_id, ruleset = get_default_vars(current_user.id)
    selected_player = Players.query.join(Sessions).filter(Sessions.id == current_session_id, Players.number == player_num).first()
    selected_pokemon = Pokemon.query.join(Sessions.players).join(Players.pokemon).filter(Sessions.id == current_session_id, Players.number == player_num, Pokemon.link_id == link_id).first()
    if ruleset != ROUTE_RULESET:
        possible_partners = Pokemon.query.join(Sessions.players).join(Players.pokemon).join(Pokedex).filter(Sessions.id == current_session_id, Players.number == player_num, Pokemon.link_id != link_id, Pokemon.position != 'dead').filter(Pokedex.base_id_2 == None)
    elif ruleset == ROUTE_RULESET:
        possible_partners = Pokemon.query.join(Sessions.players).join(Players.pokemon).join(Pokedex).filter(Sessions.id == current_session_id, Players.number == player_num, Pokemon.link_id != link_id, Pokemon.position != 'dead', Pokemon.route == selected_pokemon.route).filter(Pokedex.base_id_2 == None)
    if ruleset == MANUAL_RULESET:
        flash(f"Since session is using Full Freedom Ruleset possible fusions shown only for {selected_player.name}")
        players = [selected_player]
    else:
        players = current_session.players
    column_widths = get_column_widths(len(players))
    master_dict = {}
    for partner in possible_partners:
        partner_species = partner.info.species
        master_dict[partner_species] = {
                'info':{
                    'number':partner.pokedex_number, 
                    'typing':partner.info.type_primary if not partner.info.type_secondary else partner.info.type_primary + ' / ' + partner.info.type_secondary,
                    'base_id_1':partner.info.base_id_1}, 
                'fusions': {}}
        for player in players:
            if ruleset == SPECIAL_RULESET:
                if partner.route == selected_pokemon.route:
                    pokemon_same_route = Pokemon.query.filter(Pokemon.player_id == player.id, Pokemon.route == partner.route)
                    pokemons_1, pokemons_2 = [pokemon_same_route[0]], [pokemon_same_route[1]]
                elif player.id == selected_pokemon.player_id:
                    pokemons_1 = [selected_pokemon]
                    pokemons_2 = [partner]
                else:
                    pokemons_1 = Pokemon.query.filter(Pokemon.player_id == player.id, Pokemon.route == selected_pokemon.route)
                    pokemons_2 = Pokemon.query.filter(Pokemon.player_id == player.id, Pokemon.route == partner.route)
            elif ruleset in AUTO_RULESET:
                pokemons_1 = Pokemon.query.filter(Pokemon.player_id == player.id, Pokemon.link_id == selected_pokemon.link_id)
                pokemons_2 = Pokemon.query.filter(Pokemon.player_id == player.id, Pokemon.link_id == partner.link_id)
            elif ruleset == ROUTE_RULESET:
                pokemons = Pokemon.query.filter(Pokemon.player_id == player.id, Pokemon.route == selected_pokemon.route)
                pokemons_1, pokemons_2 = [pokemons[0]], [pokemons[1]]
            else:
                pokemons_1, pokemons_2 = [selected_pokemon], [partner]  
            master_dict[partner_species]['fusions'][player.name] = {}
            for pokemon_1 in pokemons_1:
                for pokemon_2 in pokemons_2:
                    pokedex_number_norm = pokemon_1.pokedex_number + '.' + pokemon_2.pokedex_number
                    pokedex_number_swap = pokemon_2.pokedex_number + '.' + pokemon_1.pokedex_number
                    combo = pokemon_1.info.species + ' + ' + pokemon_2.info.species
                    norm = Pokedex.query.join(Artists).filter(Pokedex.number == pokedex_number_norm).first()
                    swap = Pokedex.query.join(Artists).filter(Pokedex.number == pokedex_number_swap).first()
                    curr_fusion = {
                        'norm':{
                            'number':norm.number, 
                            'species':norm.species, 
                            'typing':norm.type_primary if not norm.type_secondary else norm.type_primary + ' / ' + norm.type_secondary, 
                            'base_id_1':norm.base_id_1,
                            'artist':norm.artists[0].artist,
                            'hp':norm.hp,
                            'attack':norm.attack,
                            'defense':norm.defense,
                            'sp_attack':norm.sp_attack,
                            'sp_defense':norm.sp_defense,
                            'speed':norm.speed,
                            'total':norm.total},
                        'swap':{
                            'number':swap.number, 
                            'species':swap.species, 
                            'typing':swap.type_primary if not swap.type_secondary else swap.type_primary + ' / ' + swap.type_secondary, 
                            'base_id_1':swap.base_id_1,
                            'artist':swap.artists[0].artist,
                            'hp':swap.hp,
                            'attack':swap.attack,
                            'defense':swap.defense,
                            'sp_attack':swap.sp_attack,
                            'sp_defense':swap.sp_defense,
                            'speed':swap.speed,
                            'total':swap.total}}
                    final_norm = Pokedex.query.join(Artists).filter(Pokedex.family == norm.family).order_by(Pokedex.family_order.desc()).first()
                    final_swap = Pokedex.query.join(Artists).filter(Pokedex.family == swap.family).order_by(Pokedex.family_order.desc()).first()
                    final_fusion = {
                        'norm':{
                            'number':final_norm.number, 
                            'species':final_norm.species, 
                            'typing':final_norm.type_primary if not final_norm.type_secondary else final_norm.type_primary + ' / ' + final_norm.type_secondary, 
                            'base_id_1':final_norm.base_id_1,
                            'artist':final_norm.artists[0].artist,
                            'hp':final_norm.hp,
                            'attack':final_norm.attack,
                            'defense':final_norm.defense,
                            'sp_attack':final_norm.sp_attack,
                            'sp_defense':final_norm.sp_defense,
                            'speed':final_norm.speed,
                            'total':final_norm.total}, 
                        'swap':{
                            'number':final_swap.number, 
                            'species':final_swap.species, 
                            'typing':final_swap.type_primary if not final_swap.type_secondary else final_swap.type_primary + ' / ' + final_swap.type_secondary, 
                            'base_id_1':final_swap.base_id_1,
                            'artist':final_swap.artists[0].artist,
                            'hp':final_swap.hp,
                            'attack':final_swap.attack,
                            'defense':final_swap.defense,
                            'sp_attack':final_swap.sp_attack,
                            'sp_defense':final_swap.sp_defense,
                            'speed':final_swap.speed,
                            'total':final_swap.total}}
                    master_dict[partner_species]['fusions'][player.name][combo] = {'current':curr_fusion, 'final':final_fusion}           
    return render_template('preview_fusions.html',
                           players=players,
                           selected_pokemon=selected_pokemon, 
                           master_dict=master_dict,
                           column_widths=column_widths)