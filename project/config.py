import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite://")
    # SQLALCHEMY_DATABASE_URI = 'mysql://root:root@localhost/flask_test'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STATIC_FOLDER = f"{os.getenv('APP_FOLDER')}/static"
    SECRET_KEY = '9OLWxND4o83j4K4iuopO'
