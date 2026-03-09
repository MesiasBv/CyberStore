from app import db
from datetime import datetime
from flask_login import UserMixin # Nos ayudará con las sesiones más adelante

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    rol = db.Column(db.String(50), default='Admin')
    nombre_usuario = db.Column(db.String(50), unique=True, nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    estado = db.Column(db.Boolean, default=True)
    telefono_contacto = db.Column(db.String(20))
    otp_code = db.Column(db.String(6), nullable=True)
    otp_expiration = db.Column(db.DateTime, nullable=True)

class Proveedor(db.Model):
    __tablename__ = 'proveedores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    nombre_usuario = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    telefono_contacto = db.Column(db.String(20))
    saldo = db.Column(db.Numeric(10, 2), default=0.00)
    estado = db.Column(db.Boolean, default=True)
    
    # Relaciones (Permite acceder a los productos de este proveedor fácilmente)
    productos = db.relationship('Producto', backref='proveedor', lazy=True)
    inventario = db.relationship('InventarioStock', backref='proveedor', lazy=True)

    otp_code = db.Column(db.String(6), nullable=True)
    otp_expiration = db.Column(db.DateTime, nullable=True)
    # Nota: También necesitaríamos su correo para enviarle el código
    correo = db.Column(db.String(100), unique=True, nullable=True)

class Cliente(db.Model, UserMixin):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), unique=True)
    nombre_usuario = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    telefono_whatsapp = db.Column(db.String(20))
    saldo = db.Column(db.Numeric(10, 2), default=0.00)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.Boolean, default=True)
    
    # Relaciones
    movimientos = db.relationship('MovimientoSaldo', backref='cliente', lazy=True)
    servicios = db.relationship('ServicioAdquirido', backref='cliente', lazy=True)