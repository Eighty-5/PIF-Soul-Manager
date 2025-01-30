from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from ...extensions import db
from ...models import User, Player, Pokedex, Pokemon, Save, Artist, RouteList, SoulLink, Route, PokedexStats
from ...webforms import CreateSaveForm
from .main_utils import get_column_widths, missing_numbers
from ...utils import func_timer
from ..pokemon.pokemon import MANUAL_RULESET, AUTO_RULESET, ROUTE_RULESET, SPECIAL_RULESET
from ..pokemon.pokemon_utils import pokemon_verification
from sqlalchemy import func
import sys

TEST_DEX_NUMS = ['1.1', '2.2', '3.3', '10.10', '20.20']
main = Blueprint('main', __name__, template_folder='templates', static_folder='static', static_url_path='/main/static')

# Index
@main.route('/')
def index():
    return render_template('about.html')


# Create a New Save route
@main.route('/save/create', methods=['GET', 'POST'])
@login_required
def create_save():

    current_save = current_user.current_save()

    # Set variables
    form = CreateSaveForm()
    # If save count is >=3 return them to the save select page
    if len(current_user.saves) >= 3:
    # if db.session.scalar(db.select(func.count("*")).select_from(User).where(Save.user_info==current_user)) >= 3:
        flash("Already at max save count. Please delete one of your saves to add another")
        return redirect(url_for('main.select_save'))
    players = [{'Player 1': 'Player 1 Name'},
               {'Player 2': 'Player 2 Name'},
               {'Player 3': 'Player 3 Name'},
               {'Player 4': 'Player 4 Name'}]
    form = CreateSaveForm(player_names=players)

    # Validate that form was submited
    if form.validate_on_submit():
        saves = current_user.saves
        save_num_lst = [save.slot for save in saves]
        ruleset=int(form.ruleset.data)
        route_tracking = True if ruleset != 1 else False
        if len(save_num_lst) < 3:
            new_save_num = missing_numbers(save_num_lst, 'first')
            if new_save_num:
                current_save = current_user.current_save()
                if current_save:
                    current_save.current_status = False
                new_save = Save(slot=new_save_num, save_name=form.save_name.data, ruleset=ruleset, route_tracking=route_tracking, user_info=current_user, current_status=True)
                db.session.add(new_save)
                player_count = 1
                for player in form.player_names:
                    if player.player_name.data:
                        new_player = Player(player_number=player_count, player_name=player.player_name.data, save_info=new_save)
                        db.session.add(new_player)
                        player_count = player_count + 1
                db.session.commit()
                flash("Save Added Successfully")
                return redirect(url_for('main.view_save'))
        
        flash("Already at max save count. Please delete one of your saves to add another")
        return redirect('/save/select')
    form.player_num.data = ""
    form.save_name.data = ""
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
        slot = request.form['save_to_delete']
        save_to_delete = db.session.scalar(db.select(Save).where(Save.user_info==current_user, Save.slot==slot))
    if id == save_to_delete.user_info.id or current_user.id == 1:
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
    current_save = current_user.current_save()
    saves = current_user.saves
    if not saves:
        flash("Please Create a Save First")
        return redirect(url_for('main.create_save')) 
    if request.method == 'POST':
        # Server check validity of form request
        new_current_save = db.session.scalar(db.select(Save).where(Save.user_info==current_user, Save.slot==request.form['slot']))
        if not new_current_save in saves:
            flash("Please select a valid save")
            return redirect(url_for('main.select_save'))
        if current_save:
            current_save.current_status = False
        new_current_save.current_status = True
        db.session.commit()
        return redirect(url_for('main.view_save'))
    return render_template('select_save_ver1.html', saves=saves)


# Redirect to Save Manager for Navbar
@main.route('/save/view', methods=['GET', 'POST'])
@func_timer
@login_required
def view_save():
    current_save = current_user.current_save()
    if current_save:
        return redirect(url_for('main.save_manager', save_num=current_save.slot))
    else:
        flash("Please Select a Save to View")
        return redirect(url_for('main.select_save'))


@main.route('/save/<int:save_num>', methods=['GET', 'POST'])
@func_timer
@login_required
def save_manager(save_num):
    current_save = current_user.current_save()
    save_check = db.session.scalar(db.select(Save).where(Save.user_info==current_user, Save.slot==save_num))
    if save_check is None:
        flash("No record of that save")
        return redirect(url_for('main.select_save'))
    party_length = current_save.player_count()
    party_length = db.session.scalar(db.select(Player).where(Player.save_info==current_save, Player.player_number==1)).party_length()   
    column_widths = get_column_widths(current_save.player_count())
    
    routes = current_save.routes
    route_list = db.session.scalars(db.select(RouteList))
    route_check_dict = {route.route_name:False for route in route_list}
    for route in routes:
        route_check_dict[route.route_info.route_name] = route.complete
    
    return render_template('save_manager.html', 
                           save_num=current_save.slot, 
                           save=current_save,  
                           party_length=party_length,
                           column_widths=column_widths,
                           route_check_dict=route_check_dict)


@main.route('/preview_fusions/<int:id>', methods=['GET', 'POST'])
@login_required
@func_timer
def preview_fusions(id):

    current_save = current_user.current_save()
    ruleset = current_save.ruleset
    selected_pokemon = pokemon_verification(id, current_save)
    column_widths = get_column_widths(len(current_save.players))
    if not selected_pokemon:
        flash("Error: Preview Fusion Failed - Please select a valid pokemon")
        return redirect(url_for('main.view_save'))
    if selected_pokemon.pokedex_info.head_pokemon:
        flash(f"Error: {selected_pokemon.pokedex_info.species} is already fused")
        return redirect(url_for('main.view_save'))
    
    other_selected_pokemon = selected_pokemon.route_caught.caught_pokemons
    other_selected_pokemon = [pokemon for pokemon in other_selected_pokemon if pokemon!=selected_pokemon]
    route_1_pokemon = [selected_pokemon, other_selected_pokemon]
    preview_fusions = {}

    master_dict = {}
    
    # ------------------------------------------------------------------------------------------------------------------
    selected_player = selected_pokemon.player_info
    if ruleset != ROUTE_RULESET:
        possible_partners = db.session.scalars(db.select(Pokemon).join(Pokemon.player_info).join(Pokemon.pokedex_info).where(Pokemon.soul_linked!=selected_pokemon.soul_linked, Pokemon.player_info==selected_player, Pokedex.head_pokemon==None, Pokemon.position!='dead'))
    elif ruleset == ROUTE_RULESET:
        possible_partners = db.session.scalars(db.select(Pokemon).join(Pokemon.player_info).join(Pokemon.pokedex_info).where(Pokemon.soul_linked!=selected_pokemon.soul_linked, Pokemon.player_info==selected_player, Pokedex.head_pokemon==None, Pokemon.position!='dead', Pokemon.route==selected_pokemon.route))
    
    if ruleset == MANUAL_RULESET:
        flash(f"Since save is using Full Freedom Ruleset possible fusions shown only for {selected_player.player_name}")
        players = [selected_player]
    else:
        players = current_save.players
    
    master_dict = {}
    count_1 = 1
    for partner in possible_partners:
        partner_species = partner.pokedex_info.species
        preview_fusions_dict[count_1] = {}
        for player in players:
            preview_fusions_dict[count_1][player.player_number] = {}
            if ruleset == SPECIAL_RULESET:
                if selected_pokemon.player == player:
                    pokemons_1 = [selected_pokemon]
                    pokemons_2 = [partner]
                elif partner.route == selected_pokemon.route:
                    pokemon_same_route = db.session.scalars(db.select(Pokemon).where(Pokemon.player_info==player, Pokemon.route==partner.route))
                    pokemons_1, pokemons_2 = pokemon_same_route[0], pokemon_same_route[1]
                else:
                    pokemons_1 = db.session.scalars(db.select(Pokemon).where(Pokemon.player_info==player, Pokemon.route==selected_pokemon.route))
                    pokemons_2 = db.session.scalars(db.select(Pokemon).where(Pokemon.player_info==player, Pokemon.route==partner.route))
            elif ruleset in AUTO_RULESET:
                pokemons_1 = db.session.scalars(db.select(Pokemon).where(Pokemon.player_info==player, Pokemon.soul_linked==selected_pokemon.soul_linked))
                pokemons_2 = db.session.scalars(db.select(Pokemon).where(Pokemon.player_info==player, Pokemon.soul_linked==partner.soul_linked))
            elif ruleset == ROUTE_RULESET:
                pokemons = db.session.scalars(db.select(Pokemon).where(Pokemon.player_info==player, Pokemon.route==selected_pokemon.route))
                pokemons_1, pokemons_2 = pokemons[0], pokemons[1]
            else:
                pokemons_1, pokemons_2 = [selected_pokemon], [partner]

            
            for pokemon_1 in pokemons_1:
                for pokemon_2 in pokemons_2:
                    fusion_names = f"{pokemon_1.pokedex_info.species} + {pokemon_2.pokedex_info.species}"
                    preview_fusions_dict[count_1][player.player_number] = {'species':f"{pokemon_1.pokedex_info.species} + {pokemon_2.pokedex_info.species}",
                                                                    'current':{},
                                                                    'final':{}}
                    preview_fusions_dict[count_1][player.player_number]['current']['norm'] = db.session.scalar(db.select(Pokedex).where(Pokedex.head_pokemon==pokemon_1.pokedex_info, Pokedex.body_pokemon==pokemon_2.pokedex_info))
                    preview_fusions_dict[count_1][player.player_number]['current']['swap'] = db.session.scalar(db.select(Pokedex).where(Pokedex.head_pokemon==pokemon_2.pokedex_info, Pokedex.body_pokemon==pokemon_1.pokedex_info))
                    preview_fusions_dict[count_1][player.player_number]['final']['norm'] = db.session.scalar(db.select(Pokedex).where(Pokedex.family==f"{pokemon_1.pokedex_info.family}.{pokemon_2.pokedex_info.family}").order_by(Pokedex.family_order.desc()))
                    preview_fusions_dict[count_1][player.player_number]['final']['swap'] = db.session.scalar(db.select(Pokedex).where(Pokedex.family==f"{pokemon_2.pokedex_info.family}.{pokemon_1.pokedex_info.family}").order_by(Pokedex.family_order.desc()))
        count_1 = count_1 + 1
    
    return render_template('preview_fusions.html',
                           current_save=current_save,
                           master_dict=master_dict,
                           column_widths=column_widths)


@main.route('/preview_all_fusions', methods=['GET', 'POST'])
@login_required
@func_timer
def preview_all_fusions():

    def get_fusion(pokemon_1, pokemon_2):
        current_normal = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==f"{pokemon_1.pokedex_number}.{pokemon_2.pokedex_number}"))
        current_swap = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==f"{pokemon_2.pokedex_number}.{pokemon_1.pokedex_number}"))
        final_normal = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==f"{pokemon_1.final_evolution().pokedex_number}.{pokemon_2.final_evolution().pokedex_number}"))
        final_swap = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==f"{pokemon_2.final_evolution().pokedex_number}.{pokemon_1.final_evolution().pokedex_number}"))

        fusion_combo = {
            'combo': f"{pokemon_1.species}+{pokemon_2.species}",
            'current': {
                'normal':current_normal,
                'swap':current_swap 
            },
            'final': {
                'normal':final_normal,
                'swap':final_swap
            }
        }
        return fusion_combo


    current_save = current_user.current_save()
    ruleset = current_save.ruleset
    column_widths = get_column_widths(len(current_save.players))
    preview_fusions = {}

    if ruleset == SPECIAL_RULESET:
        for player in current_save.players:
            pokemons = db.session.scalars(
                db.select(Pokemon).join(Pokemon.pokedex_info).where(Pokemon.player_info==player, Pokedex.head_pokemon==None)
            )
            pokemons = [pokemon for pokemon in pokemons]
            while len(pokemons) > 1:
                for pokemon_1 in pokemons[:1]:
                    for pokemon_2 in pokemons[1:]:
                        if pokemon_1 != pokemon_2:
                            [route_1_id, route_2_id] = sorted([pokemon_1.route_caught.route_info.id, pokemon_2.route_caught.route_info.id])
                            print(route_1_id, route_2_id)
                            if route_1_id > route_2_id:
                                route_combo_name = f"{pokemon_1.route_caught.route_info.route_name} & {pokemon_2.route_caught.route_info.route_name}"
                            else:
                                route_combo_name = f"{pokemon_2.route_caught.route_info.route_name} & {pokemon_1.route_caught.route_info.route_name}"
                            key = f"route{route_1_id}-{route_2_id}"
                            try:
                                preview_fusions[key]
                                try:
                                    fusion_combo = get_fusion(pokemon_1.pokedex_info, pokemon_2.pokedex_info)
                                    preview_fusions[key]['data'][player.player_number].append(fusion_combo)
                                except KeyError:
                                    preview_fusions[key]['data'][player.player_number] = []
                                    fusion_combo = get_fusion(pokemon_1.pokedex_info, pokemon_2.pokedex_info)
                                    preview_fusions[key]['data'][player.player_number].append(fusion_combo)
                            except KeyError:
                                preview_fusions[key] = {}
                                preview_fusions[key]['accordian_name'] = route_combo_name
                                preview_fusions[key]['data'] = {}
                                preview_fusions[key]['data'][player.player_number] = []
                                fusion_combo = get_fusion(pokemon_1.pokedex_info, pokemon_2.pokedex_info)
                                preview_fusions[key]['data'][player.player_number].append(fusion_combo)
                pokemons=pokemons[1:]
    elif ruleset in AUTO_RULESET:
        linkages = [link for link in current_save.soul_links]
        while len(linkages) > 1:
            for link_1 in linkages[:1]:
                link_1_id = link_1.id
                for link_2 in linkages[1:]:
                    link_2_id = link_2.id
                    comb_lst = link_1.linked_pokemon + link_2.linked_pokemon
                    if not any([pokemon.pokedex_info.isfusion() for pokemon in comb_lst]):
                        route_combo_name = f"{link_1.linked_pokemon[0].route_caught.route_info.route_name} & {link_2.linked_pokemon[0].route_caught.route_info.route_name}"
                        for pokemon_1 in link_1.linked_pokemon:
                            for pokemon_2 in link_2.linked_pokemon:
                                if pokemon_1.__eq__(pokemon_2, 'player_id') and not pokemon_1.pokedex_info.isfusion() and not pokemon_2.pokedex_info.isfusion():
                                    key = f"route{link_1_id}-{link_2_id}"
                                    try:
                                        preview_fusions[key]
                                        try:
                                            fusion_combo = get_fusion(pokemon_1.pokedex_info, pokemon_2.pokedex_info)
                                            preview_fusions[key]['data'][pokemon_1.player_info.player_number].append(fusion_combo)
                                        except KeyError:
                                            preview_fusions[key]['data'][pokemon_1.player_info.player_number] = []
                                            fusion_combo = get_fusion(pokemon_1.pokedex_info, pokemon_2.pokedex_info)
                                            preview_fusions[key]['data'][pokemon_1.player_info.player_number].append(fusion_combo)
                                    except KeyError:
                                        preview_fusions[key] = {}
                                        preview_fusions[key]['accordian_name'] = route_combo_name
                                        preview_fusions[key]['data'] = {}
                                        preview_fusions[key]['data'][pokemon_1.player_info.player_number] = []
                                        fusion_combo = get_fusion(pokemon_1.pokedex_info, pokemon_2.pokedex_info)
                                        preview_fusions[key]['data'][pokemon_1.player_info.player_number].append(fusion_combo)
            linkages = linkages[1:]
    elif ruleset == ROUTE_RULESET:
        routes = [route for route in current_save.routes]
        for route in routes:
            route_name = route.route_info.route_name
            for player in current_save.players:
                for pokemon in route.caught_pokemons:
                    if pokemon_1.player_info:
                        key = f"route{link_1_id}-{link_2_id}"
                        try:
                            preview_fusions[key]
                            try:
                                fusion_combo = get_fusion(pokemon_1.pokedex_info, pokemon_2.pokedex_info)
                                preview_fusions[key]['data'][pokemon_1.player_info.player_number].append(fusion_combo)
                            except KeyError:
                                preview_fusions[key]['data'][pokemon_1.player_info.player_number] = []
                                fusion_combo = get_fusion(pokemon_1.pokedex_info, pokemon_2.pokedex_info)
                                preview_fusions[key]['data'][pokemon_1.player_info.player_number].append(fusion_combo)
                        except KeyError:
                            preview_fusions[key] = {}
                            preview_fusions[key]['accordian_name'] = route_combo_name
                            preview_fusions[key]['data'] = {}
                            preview_fusions[key]['data'][pokemon_1.player_info.player_number] = []
                            fusion_combo = get_fusion(pokemon_1.pokedex_info, pokemon_2.pokedex_info)
                            preview_fusions[key]['data'][pokemon_1.player_info.player_number].append(fusion_combo)

    return render_template('preview_all_fusions.html',
                           current_save=current_save,
                           master_dict=preview_fusions,
                           column_widths=column_widths) 


@main.route('/testing1', methods=['GET', 'POST'])
@login_required
@func_timer
def testing1():

    def get_fusion(pokemon_1, pokemon_2):
        normal = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==f"{pokemon_1.pokedex_info.pokedex_number}.{pokemon_2.pokedex_info.pokedex_number}"))
        swap = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==f"{pokemon_2.pokedex_info.pokedex_number}.{pokemon_1.pokedex_info.pokedex_number}"))

        fusion_combo = {
            'pokemon_1':pokemon_1,
            'pokemon_2':pokemon_2,
            'normal':normal,
            'swap':swap
        }
        return fusion_combo
    
    current_save = current_user.current_save()
    ruleset = current_save.ruleset
    column_widths = get_column_widths(len(current_save.players))
    preview_fusions = {}

    if ruleset == SPECIAL_RULESET:
        for player in current_save.players:
            pokemons = db.session.scalars(
                db.select(Pokemon).where(Pokemon.player_info==player)
            )
            pokemons = [pokemon for pokemon in pokemons]
            while len(pokemons) > 1:
                for pokemon_1 in pokemons[:1]:
                    for pokemon_2 in pokemons[1:]:
                        if pokemon_1 != pokemon_2:
                            route_1_id = pokemon_1.route_caught.route_info.id
                            route_2_id = pokemon_2.route_caught.route_info.id
                            route_combo_name = f"{pokemon_1.route_caught.route_info.route_name} & {pokemon_2.route_caught.route_info.route_name}"
                            key = f"route{route_1_id}-{route_2_id}"
                            try:
                                preview_fusions[key]
                                try:
                                    fusion_combo = get_fusion(pokemon_1, pokemon_2)
                                    preview_fusions[key]['data'][player.player_number].append(fusion_combo)
                                except KeyError:
                                    preview_fusions[key]['data'][player.player_number] = []
                                    fusion_combo = get_fusion(pokemon_1, pokemon_2)
                                    preview_fusions[key]['data'][player.player_number].append(fusion_combo)
                            except KeyError:
                                preview_fusions[key] = {}
                                preview_fusions[key]['accordian_name'] = route_combo_name
                                preview_fusions[key]['data'] = {}
                                preview_fusions[key]['data'][player.player_number] = []
                                fusion_combo = get_fusion(pokemon_1, pokemon_2)
                                preview_fusions[key]['data'][player.player_number].append(fusion_combo)
                pokemons=pokemons[1:]

    return render_template('testing.html',
                           current_save=current_save,
                           preview_fusions=preview_fusions,
                           column_widths=column_widths) 

    
@main.route('/testing2', methods=['GET', 'POST'])
@login_required
@func_timer
def testing2():
    for number in TEST_DEX_NUMS:
        pokedex = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==number))
        print(pokedex.evolution_family.evolutions)
    return render_template('testing.html')

@main.route('/testing3', methods=['GET', 'POST'])
@login_required
@func_timer
def testing3():

    for number in TEST_DEX_NUMS:
        pokedex = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==number))
        print(pokedex.final_evolution_1())
    return render_template('testing.html')

@main.route('/testing4', methods=['GET', 'POST'])
@login_required
@func_timer
def testing4():
    
    for number in TEST_DEX_NUMS:
        pokedex = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==number))
        print(pokedex.first_evolution())
    return render_template('testing.html')

@main.route('/testing5', methods=['GET', 'POST'])
@login_required
@func_timer
def testing5():
    
    for number in TEST_DEX_NUMS:
        pokedex = db.session.scalar(db.select(Pokedex).where(Pokedex.pokedex_number==number))
        print(pokedex.final_evolution_3())
    return render_template('testing.html')

@main.route('/testing6', methods=['GET', 'POST'])
@login_required
def testing6(pokedex_id):
    
    @func_timer
    def test(pokedex):
        print(pokedex.evolutions())
    pokedex = db.get_or_404(Pokedex, 1)
    print(pokedex)
    test(pokedex)
    return render_template('testing.html')

@main.route('/testing7', methods=['GET', 'POST'])
@login_required
def testing7(pokedex_id):
    
    @func_timer
    def test(pokedex):
        print(pokedex.evolutions())
    pokedex = db.get_or_404(Pokedex, 1)
    print(pokedex)
    test(pokedex)
    return render_template('testing.html')

@main.route('/testing8', methods=['GET', 'POST'])
@login_required
def testing8(pokedex_id):
    
    @func_timer
    def test(pokedex):
        print(pokedex.evolutions())
    pokedex = db.get_or_404(Pokedex, 1)
    print(pokedex)
    test(pokedex)
    return render_template('testing.html')