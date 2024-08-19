from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_required, login_user, current_user, logout_user
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from ...extensions import db
from ...models import User, Player, Save
from ...webforms import LoginForm, RegisterForm

manage_users = Blueprint('manage_users', __name__, template_folder='templates')

# Index
@manage_users.route('/')
def index():
    return 'Hello Login'


@manage_users.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.username == form.username.data)).scalar()
        if user:
            if check_password_hash(user.hash, form.password.data):
                login_user(user)
                flash("Login Successful!")
                return redirect(url_for('main.select_save'))
            else:
                flash("Incorrect Username/Password - Please Try Again")
        else:
            flash("Incorrect Username/Password - Please Try Again")
    form.username.data=""
    form.password.data=""
    return render_template('login.html', form=form)
        

@manage_users.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    current_save = db.session.scalar(db.select(Save).where(Save.users==current_user, Save.current==True))
    current_save.current = False
    db.session.commit()
    logout_user()
    flash("You have been Logged Out Successfully!")

    return redirect('/login')


@manage_users.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            user = db.session.scalar(db.select(User).where(User.username==form.username.data))
            # If no user with entered username exits:
            if user is None:
                user = User(username=form.username.data, hash=generate_password_hash(form.password.data, method='pbkdf2', salt_length=16))
                db.session.add(user)
                db.session.commit()
                logout_user()
                # Add Flash Message
                flash("User added Successfully!")
                return redirect('/login')
            # If a user with entered username exists:
            else:
                flash("User already Exists")
            # Clear form
            form.username.data = ""
            form.password.data = ""
            form.password_confirm.data = ""
            return render_template('register.html', form=form)
    else:
        return render_template('register.html', form=form)
    

@manage_users.route('/user/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_user(id):
    user_to_delete = User.query.get_or_404(id)
    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash("User Deleted Successfully!")
        users = User.query.order_by(User.last_login)
    except:
        flash("Error there was a problem try again")
    if current_user.id == 8:
        return redirect('/admin/users')
    else:
        return redirect('/login')


@manage_users.route('/users', methods=['GET', 'POST'])
def users():
    our_users = User.query.order_by(User.last_login)
    return render_template('users.html', our_users=our_users)