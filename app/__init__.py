from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from config import Config

# Inicializamos la base de datos
db = SQLAlchemy()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    mail.init_app(app)
    
    with app.app_context():
        # 1. Importar los modelos (para que SQLAlchemy los reconozca al iniciar)
        from .models import usuarios, productos, ventas, sugerencias
        
        # 2. Importar los Blueprints de las rutas
        from .routes.public import public_bp
        from .routes.auth import auth_bp
        from .routes.admin import admin_bp
        from .routes.proveedor import proveedor_bp
        
        # 3. Registrar los Blueprints en la aplicación
        app.register_blueprint(public_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(proveedor_bp)
        
        # Opcional: Crear las tablas en MySQL si no existen (solo para desarrollo)
        db.create_all()

    return app