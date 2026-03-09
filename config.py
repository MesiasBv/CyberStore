import os
from dotenv import load_dotenv
from datetime import timedelta

# Cargar las variables del archivo .env
load_dotenv()

class Config:
    # Clave secreta para proteger las sesiones de los usuarios
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave_por_defecto_para_desarrollo'
    
    # Configuración de sesión persistente
    # La sesión durará 30 días (720 horas) por defecto
    PERMANENT_SESSION_LIFETIME = timedelta(hours=720)  # 30 días
    SESSION_COOKIE_HTTPONLY = True  # Previene acceso a cookies desde JavaScript
    SESSION_COOKIE_SECURE = False  # Cambiar a True en producción con HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'  # Protege contra CSRF
    SESSION_COOKIE_NAME = 'cyberstore_session'  # Nombre personalizado para la cookie
    
    # Construir la URL de conexión a MySQL
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_NAME = os.environ.get('DB_NAME', 'sistema_ventas')
    
    # URI de conexión para SQLAlchemy usando PyMySQL
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    
    # Desactivar notificaciones innecesarias de SQLAlchemy para ahorrar memoria
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuración de correos (Flask-Mail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')
    
    # Configuración de Yape
    YAPE_NUMERO = os.environ.get('YAPE_NUMERO', '910016266')
    YAPE_NOMBRE = os.environ.get('YAPE_NOMBRE', 'Adbeel Bar*')
    YAPE_LINK_QR = os.environ.get('YAPE_LINK_QR', '/static/uploads/qr/qr_yape.png')
    
    # WhatsApp del admin para recibir vouchers
    WHATSAPP_ADMIN = os.environ.get('WHATSAPP_ADMIN', '51910016266')
