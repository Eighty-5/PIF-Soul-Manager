from dotenv import load_dotenv
import os

load_dotenv()

ENV = os.getenv('FLASK_ENV')
DEBUG = ENV == 'development'
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
SECRET_KEY = os.getenv('SECRET_KEY')
SQLALCHEMY_TRACK_MODICATIONS = False