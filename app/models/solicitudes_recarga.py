from app import db
from app.utils.hora_peru import obtener_hora_peru
from sqlalchemy import Enum

class SolicitudRecarga(db.Model):
    __tablename__ = 'solicitudes_recarga'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    nombre_titular_pago = db.Column(db.String(100), nullable=False)
    fecha_solicitud = db.Column(db.DateTime, default=obtener_hora_peru)
    estado = db.Column(Enum('Pendiente', 'Aprobado', 'Rechazado', name='estado_solicitud'), default='Pendiente')

    # Relaciones
    usuario = db.relationship('Cliente', backref='solicitudes_recarga')
