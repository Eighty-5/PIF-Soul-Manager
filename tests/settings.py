ENV = "development"
TESTING = True
SQLALCHEMY_DATABASE_URI = "sqlite://"
SECRET_KEY = "not-so-secret"
DEBUG_TB_ENABLED = False
CACHE_TYPE = "flask_caching.backends.SimpleCache"
SQLALCHEMY_TRACK_MODIFICATIONS = False
WTF_CSRF_ENABLED = False