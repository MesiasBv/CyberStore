from datetime import datetime, timedelta

from datetime import timedelta

def obtener_hora_peru():
    """Retorna datetime actual en zona horaria de Lima, Perú UTC-5 exacto"""
    return datetime.utcnow() - timedelta(hours=5)

