# app.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# --- 1. INITIALIZE EXTENSIONS (WITHOUT AN APP) ---
# We create the extension objects here, but they are not yet connected to a specific app.
db = SQLAlchemy()
migrate = Migrate()  # Initialize Migrate here as well
login_manager = LoginManager()
login_manager.login_view = 'auth_bp.login'  # We will use a blueprint for auth routes

# --- 2. THE APPLICATION FACTORY ---
def create_app():
    """
    Creates and configures an instance of the Flask application.
    This is the most important part of the structure.
    """
    app = Flask(__name__)

    # --- 3. CONFIGURE THE APP ---
    # Load configuration from a file or environment variables.
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SECRET_KEY'] = 'a-very-secret-key-that-you-should-change'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'cu_project.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static/uploads')

    # Ensure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # --- 4. CONNECT EXTENSIONS TO THE APP ---
    # Now we call init_app() to link our extensions to the created app instance.
    db.init_app(app)
    migrate.init_app(app, db) # Connect Flask-Migrate to the app and the database
    login_manager.init_app(app)

    # --- 5. DEFINE MODELS AND USER LOADER ---
    from models import User # Import your models here
    
    @login_manager.user_loader
    def load_user(user_id):
        # This function is required by Flask-Login to manage user sessions.
        return User.query.get(int(user_id))

    # --- 6. REGISTER BLUEPRINTS (YOUR ROUTES) ---
    # Instead of defining all routes in one giant file, we use Blueprints.
    # This keeps your project organized.
    with app.app_context():
        # Import your routes file (we will create this next)
        from routes import main_bp
        # from auth_routes import auth_bp # Example for auth routes
        
        app.register_blueprint(main_bp)
        # app.register_blueprint(auth_bp, url_prefix='/auth')

    return app