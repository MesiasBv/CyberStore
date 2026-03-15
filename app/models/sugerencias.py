from app import db
from datetime import datetime
from app.utils.hora_peru import obtener_hora_peru

class Sugerencia(db.Model):
    __tablename__ = 'sugerencias'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    nombre_usuario = db.Column(db.String(100), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=obtener_hora_peru)
    estado = db.Column(db.Boolean, default=True)
