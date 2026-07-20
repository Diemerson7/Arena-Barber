from flask import Flask
from config import Config
from app.models import db
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from app.models import db, Service, User

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "info"

    with app.app_context():
        from . import routes
        db.create_all()  # Cria o banco SQLite automaticamente
        return app