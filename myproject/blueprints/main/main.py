from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from ...extensions import db
from ...models import Users, Players, Pokedex, Pokemon, Sessions, PokedexBase
from ...webforms import LoginForm, RegisterForm, CreateSessionForm, PokemonEvolveForm
from ...helpers import find_first_missing

main = Blueprint('main', __name__, template_folder='templates', static_folder='static', static_url_path='/main/static')

# Index
@main.route('/')
def index():
    return render_template('index.html')


# Create a New Session route
@main.route('/session/create', methods=['GET', 'POST'])
@login_required
def create_session():

    # Set variables
    form = CreateSessionForm()
    id = current_user.id
    sessions = Sessions.query.filter_by(user_id=id)
        
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
        # If no sessions yet just create new session
        # if sessions.first() is None:
        #     new_session = Sessions(user_id=id, number=1)
        #     db.session.add(new_session)
        #     db.session.commit()
        
        # https://stackoverflow.com/questions/31842159/get-a-list-of-values-of-one-column-from-the-results-of-a-query
        session_num_lst = [session.number for session in sessions]

        # Double check that total session count is less than 3 in case they get to this page
        if len(session_num_lst) < 3:
            # Find first missing session number
            new_session_num = find_first_missing(session_num_lst)
            if not new_session_num == False:
                new_session = Sessions(user_id=id, number=new_session_num)
                db.session.add(new_session)
                db.session.commit()
                # Create the player count and add new players to DB
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
        
    # Clear the Form
    form.player_num.data = ""
    for player in form.player_names:
        player.player_name.data = ""
    form.ruleset.data = ""

    return render_template('create_session.html', form=form)


# Delete a Session route
@main.route('/session/delete/<int:session_number>', methods=['GET', 'POST'])
@login_required
def delete_session(session_number):
    # Set variables
    id = current_user.id
    session_to_delete = Sessions.query.filter_by(user_id=id, number=session_number).first()
    
    # Check whether the current user is an admin or is the user looking to delete the session
    if id == session_to_delete.user.id or current_user.id == 1:
        # Delete the session and commit
        db.session.delete(session_to_delete)
        db.session.commit()
        # If deleted session is the current session set the current session to none
        if Users.query.get(id).current_session == session_number:
            Users.query.get(id).current_session = None
            db.session.commit()
        # If admin deleted the session return to admin/sessions else return to the session select
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
        for key in request.form:
            current_session_to_update = Users.query.get_or_404(id)
            current_session_id = Sessions.query.filter_by(user_id=id, number=key).first().id
            current_session_to_update.current_session = current_session_id
            db.session.commit()
        return redirect(url_for('main.view_session'))
    return render_template('select_session.html', sessions=sessions)


# Redirect to Session Manager for Navbar
@main.route('/session/view', methods=['GET', 'POST'])
@login_required
def view_session():
    id = current_user.id
    current_session = Users.query.get(id).current_session
    if current_session:
        session_num = Sessions.query.get(current_session).number
        return redirect(url_for('main.session_manager', session_num=session_num))
    else:
        flash("Please Select a Session to View")
        return redirect(url_for('main.select_session'))


@main.route('/session/<int:session_num>', methods=['GET', 'POST'])
@login_required
def session_manager(session_num):
    id = current_user.id
    session = Sessions.query.filter_by(user_id=id, number=session_num).first()
    if session is None:
        flash("No record of that session")
        return redirect(url_for('main.select_session'))
        
    players = Players.query.filter_by(session_id=session.id)
    
    # Get party length
    party_length = Pokemon.query.filter_by(player_id=players[0].id, position='party').count()

    width_numbers = []
    width_numbers.append(int(12 / players.count()))
    if width_numbers[0] < 6:
        width_numbers.append(12)
    else:
        width_numbers.append(6)
    
    # Evolutions
    full_evolution_list = []
    for player in players:
        player_evolution_list = []
        for pokemon in player.pokemon:
            evolution_list = []
            evolutions = Pokedex.query.filter_by(family=pokemon.info.family).order_by(Pokedex.family_order)
            for evolution in evolutions:
                # - 3 -
                base_pokemon_1 = PokedexBase.query.filter_by(number=evolution.base_id_1).first()
                base_pokemon_2 = PokedexBase.query.filter_by(number=evolution.base_id_2).first() 
                if base_pokemon_2 is not None:
                    evo_names = f"{base_pokemon_1.species} + {base_pokemon_2.species}"
                    evo_number = f"{str(base_pokemon_1.number)}.{str(base_pokemon_2.number)}"
                else:
                    evo_names = base_pokemon_1.species
                    evo_number = str(base_pokemon_1.number)
                evolution_list.append({'number':evo_number, 'names':evo_names})
            player_evolution_list.append(evolution_list)
        full_evolution_list.append(player_evolution_list)   

    return render_template('session_manager.html', 
                           session_num=session_num, 
                           session=session, 
                           full_evolution_list=full_evolution_list,  
                           party_length=party_length,
                           width_numbers=width_numbers)
            