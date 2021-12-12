from datetime import timedelta
import toml
from flask import Flask, sessions
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, instance_relative_config=True)
app.config.from_file("config.toml", load=toml.load)
db = SQLAlchemy(app)

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
sessions.permanent = True


@app.before_first_request
def create_table():
    db.create_all()


from twogplus import views
