from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)
manager = LoginManager(app)

from FotoSite import models, routes

app.app_context().push()
db.create_all()
