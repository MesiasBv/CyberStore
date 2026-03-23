import pytz
from datetime import datetime

def obtener_hora_peru():
    """Retorna datetime actual en zona horaria de Lima, Perú usando pytz"""
    lima_tz = pytz.timezone('America/Lima')
    return datetime.now(lima_tz)
