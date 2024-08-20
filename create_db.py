import mysql.connector
from myproject import create_app
from myproject.models import User
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

import os

load_dotenv()

con = mysql.connector.connect(
    host = os.getenv('MYSQL_HOST'),
    user = os.getenv('MYSQL_USER'),
    password = os.getenv('MYSQL_PASSWORD')
)

cur = con.cursor()

cur.execute("CREATE DATABASE pif_game_manager")

cur.execute("SHOW DATABASES")

for db in cur:
    print(db)

app = create_app()

with app.app_context():

    from myproject.extensions import db

    db.create_all()
    admin_user = User(username='Admin', hash=generate_password_hash(os.getenv('ADMIN_PASSWORD'), method='pbkdf2', salt_length=16))
    db.session.add(admin_user)
    db.session.commit()

    

