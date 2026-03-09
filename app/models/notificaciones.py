from app import db
from datetime import datetime

def hora_peru():
    """Función para obtener la hora actual de Perú (hora local del servidor)"""
    return datetime.now()

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    titulo = db.Column(db.String(100), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default='info')  # info, warning, success, danger
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=hora_peru)
    # Campo para almacenar información de redirección
    venta_id = db.Column(db.Integer, nullable=True)  # ID de la venta para redirigir al modal de credenciales
    
    cliente = db.relationship('Cliente', backref='notificaciones', lazy=True)
