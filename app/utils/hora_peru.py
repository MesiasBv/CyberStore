from datetime import datetime
from zoneinfo import ZoneInfo

def obtener_hora_peru():
    """Retorna datetime actual en zona horaria de Lima, Perú UTC-5"""
    return datetime.now(ZoneInfo("America/Lima"))
