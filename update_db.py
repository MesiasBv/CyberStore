from app import create_app, db
from app.models.usuarios import Usuario
from app.models.ventas import Venta
# Importa aquí tu nuevo modelo de solicitudes para que SQL lo reconozca
try:
    from app.models.ventas import SolicitudRecarga 
except:
    print("Asegúrate de haber definido la clase SolicitudRecarga en tus modelos")

app = create_app()

with app.app_context():
    print("Iniciando actualización de base de datos...")
    db.create_all()
    print("✅ Tablas creadas/actualizadas con éxito.")