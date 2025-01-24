from myproject import create_app
from myproject.models import User
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
import os
import sys
import uuid

load_dotenv()

def main(*args, **kwargs) -> None:
    if sys.argv[1] == 'mysql':
        import mysql.connector
        conn = mysql.connector.connect(
            host = os.getenv('MYSQL_HOST'),
            user = os.getenv('MYSQL_USER'),
            password = os.getenv('MYSQL_PASSWORD')
        )
        cur = conn.cursor()
        cur.execute("CREATE DATABASE pif_save_manager")

    elif sys.argv[1] == 'postgresql':
        import psycopg2
        conn = psycopg2.connect(
            database = "postgres", 
            user = os.getenv('POSTGRESQL_USER'), 
            password = os.getenv('POSTGRESQL_PASSWORD'),
            host = os.getenv('POSTGRESQL_HOST'),
            port = os.getenv('POSTGRESQL_PORT')
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("CREATE DATABASE pif_save_manager")
    elif sys.argv[1] == 'sqlite':
        pass

    print("Database created successfully...")

    app = create_app()

    with app.app_context():

        from myproject.extensions import db

        db.create_all()
        admin_user = User(username='Admin', hash=generate_password_hash(os.getenv('ADMIN_PASSWORD'), method='pbkdf2', salt_length=16))
        db.session.add(admin_user)
        db.session.commit()


if __name__ == "__main__":
    main()

    

