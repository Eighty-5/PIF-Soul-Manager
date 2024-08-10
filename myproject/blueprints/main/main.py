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
        possible_partners = db.session.scalars(db.select(Pokemon).join(Pokemon.player).join(Pokemon.info).where(Pokemon.link_id!=link_id, Pokemon.player==selected_player, Pokedex.head==None, Pokemon.position!='dead'))
    elif ruleset == ROUTE_RULESET:
        possible_partners = db.session.scalars(db.select(Pokemon).join(Pokemon.player).join(Pokemon.info).where(Pokemon.link_id!=link_id, Pokemon.player==selected_player, Pokedex.head==None, Pokemon.position!='dead', Pokemon.route==selected_pokemon.route))
    
    if ruleset == MANUAL_RULESET:
        flash(f"Since save is using Full Freedom Ruleset possible fusions shown only for {selected_player.name}")
        players = [selected_player]
    else:
        players = current_save.players
    column_widths = get_column_widths(len(players))
    preview_fusions_dict = {}
    master_dict = {}
    count_1 = 1
    for partner in possible_partners:
        partner_species = partner.info.species
        preview_fusions_dict[count_1] = {}
        for player in players:
            preview_fusions_dict[count_1][player.number] = {}
            if ruleset == SPECIAL_RULESET:
                if selected_pokemon.player == player:
                    pokemons_1 = [selected_pokemon]
                    pokemons_2 = [partner]
                elif partner.route == selected_pokemon.route:
                    pokemon_same_route = db.session.scalars(db.select(Pokemon).where(Pokemon.player==player, Pokemon.route==partner.route))
                    pokemons_1, pokemons_2 = pokemon_same_route[0], pokemon_same_route[1]
                else:
                    pokemons_1 = db.session.scalars(db.select(Pokemon).where(Pokemon.player==player, Pokemon.route==selected_pokemon.route))
                    pokemons_2 = db.session.scalars(db.select(Pokemon).where(Pokemon.player==player, Pokemon.route==partner.route))
            elif ruleset in AUTO_RULESET:
                pokemons_1 = db.session.scalars(db.select(Pokemon).where(Pokemon.player==player, Pokemon.link_id==selected_pokemon.link_id))
                pokemons_2 = db.session.scalars(db.select(Pokemon).where(Pokemon.player==player, Pokemon.link_id==partner.link_id))
            elif ruleset == ROUTE_RULESET:
                pokemons = db.session.scalars(db.select(Pokemon).where(Pokemon.player==player, Pokemon.route==selected_pokemon.route))
                pokemons_1, pokemons_2 = pokemons[0], pokemons[1]
            else:
                pokemons_1, pokemons_2 = [selected_pokemon], [partner]

            
            for pokemon_1 in pokemons_1:
                for pokemon_2 in pokemons_2:
                    fusion_names = f"{pokemon_1.info.species} + {pokemon_2.info.species}"
                    preview_fusions_dict[count_1][player.number][fusion_names] = {'current':{}, 'final':{}}
                    preview_fusions_dict[count_1][player.number][fusion_names]['current']['norm'] = db.session.scalar(db.select(Pokedex).where(Pokedex.head==pokemon_1.info, Pokedex.body==pokemon_2.info))
                    preview_fusions_dict[count_1][player.number][fusion_names]['current']['swap'] = db.session.scalar(db.select(Pokedex).where(Pokedex.head==pokemon_2.info, Pokedex.body==pokemon_1.info))
                    preview_fusions_dict[count_1][player.number][fusion_names]['final']['norm'] = db.session.scalar(db.select(Pokedex).where(Pokedex.family==f"{pokemon_1.info.family}.{pokemon_2.info.family}").order_by(Pokedex.family_order.desc()))
                    preview_fusions_dict[count_1][player.number][fusion_names]['final']['swap'] = db.session.scalar(db.select(Pokedex).where(Pokedex.family==f"{pokemon_2.info.family}.{pokemon_1.info.family}").order_by(Pokedex.family_order.desc()))
        count_1 = count_1 + 1
    for row, player_numbers in preview_fusions_dict.items():
        print(f"Row: {row}")
        for player, fusion_names in player_numbers.items():
            print(f"Player:{player}\nFusion Names:{fusion_names}")
            for fusion_name, fusions in fusion_names.items():
                print(fusion_name)
                print("CURRENT")
                for flip, fusion in fusions['current'].items():
                    print(f"FLIP: {flip}")
                    print(f"FUSION: {fusion}")
                print("FINAL")
                for flip, fusion in fusions['final'].items():
                    print(f"FLIP: {flip}")
                    print(f"FUSION: {fusion}")
    
    return render_template('preview_fusions.html',
                           players=players,
                           selected_pokemon=selected_pokemon, 
                           master_dict=preview_fusions_dict,
                           column_widths=column_widths)