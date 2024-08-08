from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from ...extensions import db
from ...models import User, Player, Pokedex, Pokemon, Save, Artist
from ...webforms import CreateSaveForm
from .main_utils import find_first_missing_save_number, get_column_widths
from ...utils import get_default_vars
from ..pokemon.pokemon import MANUAL_RULESET, AUTO_RULESET, ROUTE_RULESET, SPECIAL_RULESET
from sqlalchemy import func

main = Blueprint('main', __name__, template_folder='templates', static_folder='static', static_url_path='/main/static')

# Index
@main.route('/')
def index():
    return render_template('about.html')


# Create a New Save route
@main.route('/save/create', methods=['GET', 'POST'])
@login_required
def create_save():

    # Set variables
    form = CreateSaveForm()
    # If save count is >=3 return them to the save select page
    if db.session.scalar(db.select(func.count("*")).select_from(User).where(Save.users==current_user)) >= 3:
        flash("Already at max save count. Please delete one of your saves to add another")
        return redirect(url_for('main.select_save'))
    players = [{'Player 1': 'Player 1 Name'},
               {'Player 2': 'Player 2 Name'},
               {'Player 3': 'Player 3 Name'},
               {'Player 4': 'Player 4 Name'}]
    form = CreateSaveForm(player_names=players)

    # Validate that form was submited
    if form.validate_on_submit():
        saves = db.session.scalars(db.select(Save).where(Save.users==current_user))
        save_num_lst = [save.number for save in saves]
        ruleset=int(form.ruleset.data)
        route_tracking = True if ruleset != 1 else False
        if len(save_num_lst) < 3:
            new_save_num = find_first_missing_save_number(save_num_lst)
            if not new_save_num == False:
                new_save = Save(number=new_save_num, ruleset=int(form.ruleset.data), route_tracking=route_tracking, users=current_user)
                db.session.add(new_save)
                player_count = 1
                for player in form.player_names:
                    if player.player_name.data:
                        new_player = Player(number=player_count, name=player.player_name.data, saves=new_save)
                        db.session.add(new_player)
                        player_count = player_count + 1
                db.session.commit()
                flash("Save Added Successfully")
                return redirect('/save/select')
        
        flash("Already at max save count. Please delete one of your saves to add another")
        return redirect('/save/select')
    form.player_num.data = ""
    for player in form.player_names:
        player.player_name.data = ""
    form.ruleset.data = ""
    return render_template('create_save.html', form=form)


# Delete a Save route
@main.route('/save/delete', methods=['GET', 'POST'])
@login_required
def delete_save():
    id = current_user.id
    if request.method == 'POST':
        save_number = request.form['save_to_delete']
        save_to_delete = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.number==save_number))
    if id == save_to_delete.users.id or current_user.id == 1:
        db.session.delete(save_to_delete)
        db.session.commit()
        if current_user.id == 1:
            return redirect('/admin/saves')
        else:
            return redirect('/save/select')
    else:
        flash("You do not have authorization to delete this save")
        return redirect('/save/select')
    

@main.route('/save/select/', methods=['GET', 'POST'])
@login_required
def select_save():
    saves = db.session.scalars(db.select(Save).where(Save.users==current_user))
    if not saves:
        flash("Please Create a Save First")
        return redirect(url_for('main.create_save')) 
    if request.method == 'POST':
        current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
        new_current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.number==request.form['save_number']))
        if current_save:
            current_save.current = False
        new_current_save.current = True
        db.session.commit()
        return redirect(url_for('main.view_save'))
    return render_template('select_save.html', saves=saves)


# Redirect to Save Manager for Navbar
@main.route('/save/view', methods=['GET', 'POST'])
@login_required
def view_save():
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    if current_save:
        return redirect(url_for('main.save_manager', save_num=current_save.number))
    else:
        flash("Please Select a Save to View")
        return redirect(url_for('main.select_save'))


@main.route('/save/<int:save_num>', methods=['GET', 'POST'])
@login_required
def save_manager(save_num):
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    save_check = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.number==save_num))
    if save_check is None:
        flash("No record of that save")
        return redirect(url_for('main.select_save'))
    party_length = db.session.scalar(db.select(Player).where(Player.saves==current_save, Player.number==1)).party_length()   
    column_widths = get_column_widths(current_save.player_count())
    return render_template('save_manager.html', 
                           save_num=current_save.number, 
                           save=current_save,  
                           party_length=party_length,
                           column_widths=column_widths)


@main.route('/preview_fusions/<int:player_num>/<int:link_id>', methods=['GET', 'POST'])
@login_required
def preview_fusions(player_num, link_id):
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    ruleset = current_save.ruleset
    selected_player = db.session.scalar(db.select(Player).where(Player.saves==current_save, Player.number==player_num))
    selected_pokemon = db.session.scalar(db.select(Pokemon).where(Pokemon.link_id==link_id, Pokemon.player==selected_player))
    if ruleset != ROUTE_RULESET:
        possible_partners = db.session.scalars(db.select(Pokemon).join(Pokemon.player, Pokemon.info).where(Pokemon.link_id!=link_id, Pokemon.player==selected_player, Pokedex.head==None, Pokemon.position!='dead'))
    elif ruleset == ROUTE_RULESET:
        possible_partners = db.session.scalars(db.select(Pokemon).join(Pokemon.player, Pokemon.info).where(Pokemon.link_id!=link_id, Pokemon.player==selected_player, Pokedex.head==None, Pokemon.position!='dead', Pokemon.route==selected_pokemon.route))
        # possible_partners = Pokemon.query.join(Save.players).join(Player.pokemon).join(Pokedex).filter(Save.id == current_save_id, Player.number == player_num, Pokemon.link_id != link_id, Pokemon.position != 'dead', Pokemon.route == selected_pokemon.route).filter(Pokedex.base_id_2 == None)
    if ruleset == MANUAL_RULESET:
        flash(f"Since save is using Full Freedom Ruleset possible fusions shown only for {selected_player.name}")
        players = [selected_player]
    else:
        players = current_save.players
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
                    norm = Pokedex.query.join(Artist).filter(Pokedex.number == pokedex_number_norm).first()
                    swap = Pokedex.query.join(Artist).filter(Pokedex.number == pokedex_number_swap).first()
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
                    final_norm = Pokedex.query.join(Artist).filter(Pokedex.family == norm.family).order_by(Pokedex.family_order.desc()).first()
                    final_swap = Pokedex.query.join(Artist).filter(Pokedex.family == swap.family).order_by(Pokedex.family_order.desc()).first()
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