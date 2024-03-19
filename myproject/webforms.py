from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, SelectField, FieldList, FormField, IntegerField, DecimalField, BooleanField
from wtforms.validators import DataRequired, EqualTo


# Create Form Class
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password_confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords Must Match!')])
    submit = SubmitField('Submit')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')

class PlayerNameForm(FlaskForm):
    player_name = StringField('Player Name')

class CreateSessionForm(FlaskForm):
    player_num = SelectField('Number of Players', choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')], validators=[DataRequired()])
    player_names = FieldList(FormField(PlayerNameForm), min_entries=1)
    ruleset = SelectField('Ruleset', choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')])
    route_tracking = BooleanField('Enable Route Tracking')

class SubmitSessionForm(FlaskForm):
    submit = SubmitField('Submit')

class SelectSessionForm(FlaskForm):
    submit = FieldList(FormField(SubmitSessionForm), min_entries=1)

class PokemonForm(FlaskForm):
    player = StringField('Player name', validators=[DataRequired()])

class AddPokemonForm(FlaskForm):
    new_pokemon = FieldList(FormField(PokemonForm), min_entries=1)
    submit = SubmitField('Submit')

class AddPokedexForm(FlaskForm):
    species = StringField('Species')
    type_1 = StringField('Type 1')
    type_2 = StringField('Type 2')
    submit = SubmitField('Submit')

class AdminAddPokedexForm(FlaskForm):
    pokedex_id = DecimalField('Pokedex Id', places=3, validators=[DataRequired()])
    species = StringField('Species', validators=[DataRequired()])
    base_id_1 = IntegerField('Base Id 1')
    base_id_2 = IntegerField('Base Id 2')
    type_primary = StringField('Type Primary')
    type_secondary = StringField('Type Secondary')
    family = DecimalField('Family', places=2, validators=[DataRequired()])
    family_order = DecimalField('Family Order', places=2, validators=[DataRequired()])

class PokemonEvolveForm(FlaskForm):
    evolution_combo = SelectField('Evolution', choices=[], validators=[DataRequired()])
    submit = SubmitField('Submit')

class SearchNumberForm(FlaskForm):
    number = StringField('Number', validators=[DataRequired()])
    submit = SubmitField('Submit')

class SearchSpeciesForm(FlaskForm):
    species = StringField('Species', validators=[DataRequired()])
    submit = SubmitField('Submit')

