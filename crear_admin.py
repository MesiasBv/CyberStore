from app import create_app, db
from app.models.usuarios import Usuario
from werkzeug.security import generate_password_hash

# Inicializamos la aplicación para poder hablar con la base de datos
app = create_app()

with app.app_context():
    # Revisamos si ya existe el usuario 'admin' para no duplicarlo
    admin_existente = Usuario.query.filter_by(nombre_usuario='admin').first()
    
    if not admin_existente:
        nuevo_admin = Usuario(
            nombre_usuario='admin',
            correo='cyberdelincuente@gmail.com',  # <--- ¡Pon tu correo real aquí!
            password_hash=generate_password_hash('admin123'), # Contraseña inicial: admin123
            rol='Admin'
        )
        
        db.session.add(nuevo_admin)
        db.session.commit()
        print("¡Éxito! El usuario Administrador ha sido creado.")
    else:
        print("El usuario Administrador ya existe en la base de datos.")