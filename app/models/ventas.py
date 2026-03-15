from app import db
from datetime import datetime
from app.utils.hora_peru import obtener_hora_peru

class MovimientoSaldo(db.Model):
    __tablename__ = 'movimientos_saldo'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    tipo = db.Column(db.Enum('Recarga', 'Compra', 'Reembolso'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    saldo_resultante = db.Column(db.Numeric(10, 2), nullable=False)
    descripcion = db.Column(db.String(255))
    fecha_movimiento = db.Column(db.DateTime, default=obtener_hora_peru)
    estado = db.Column(db.Boolean, default=True)

class ServicioAdquirido(db.Model):
    __tablename__ = 'servicios_adquiridos'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    inventario_id = db.Column(db.Integer, db.ForeignKey('inventario_stock.id'), nullable=False)
    precio_pagado = db.Column(db.Numeric(10, 2), nullable=False)
    
    estado_invitacion = db.Column(db.Enum('No Aplica', 'Pendiente de Envío', 'Invitación Enviada'), default='No Aplica')
    fecha_compra = db.Column(db.DateTime, default=obtener_hora_peru)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    estado_servicio = db.Column(db.Enum('Activo', 'Por Vencer', 'Vencido', 'Suspendido', 'Completado'), default='Activo')
    renovacion_solicitada = db.Column(db.Boolean, default=False)
    estado = db.Column(db.Boolean, default=True)
    
    # Relaciones para acceder fácilmente al detalle del producto e inventario desde una compra
    producto = db.relationship('Producto')
    inventario = db.relationship('InventarioStock')

class AuditoriaLog(db.Model):
    __tablename__ = 'auditoria_logs'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id')) # Puede ser NULL si lo hace un cliente
    accion = db.Column(db.String(50), nullable=False)
    tabla_afectada = db.Column(db.String(50), nullable=False)
    detalles = db.Column(db.Text)
    ip_origen = db.Column(db.String(45), nullable=False)
    dispositivo = db.Column(db.String(255))
    fecha_accion = db.Column(db.DateTime, default=obtener_hora_peru)
    estado = db.Column(db.Boolean, default=True)


class Venta(db.Model):
    __tablename__ = 'ventas'
    
    id = db.Column(db.Integer, primary_key=True)
    # Código único aleatorio para identificar la venta (formato: CS-XXXXXXXX)
    codigo_unico = db.Column(db.String(20), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    
    # ID de la cuenta exacta que se sacó del stock (para entrega automática)
    inventario_id = db.Column(db.Integer, db.ForeignKey('inventario_stock.id'), nullable=True) 
    
    precio_final = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_venta = db.Column(db.DateTime, default=obtener_hora_peru)
    
    # Fechas de suscripción del cliente
    fecha_inicio_servicio = db.Column(db.Date, nullable=True)
    fecha_fin_servicio = db.Column(db.Date, nullable=True)
    estado_servicio = db.Column(db.Enum('Activo', 'Por Vencer', 'Vencido', 'Suspendido', 'Completado'), default='Activo')
    
    # Fecha de expiración de la cuenta que el proveedor pagó a la plataforma
    fecha_expiracion_cuenta_proveedor = db.Column(db.Date, nullable=True)
    
    # Código de verificación (para productos tipo 'codigo' - el cliente lo solicita después)
    codigo_verificacion = db.Column(db.String(50), nullable=True)
    codigo_verificacion_enviado = db.Column(db.Boolean, default=False)
    fecha_codigo_enviado = db.Column(db.DateTime, nullable=True)
    
    # Campos para gestión de entrega
    # Correo del cliente (para Netflix cuenta completa, YouTube, Canva)
    correo_cliente = db.Column(db.String(255), nullable=True)
    # Estado de entrega: Pendiente (requiere acción) / Entregado
    estado_entrega = db.Column(db.Enum('Pendiente', 'Entregado'), default='Pendiente')
    fecha_entrega = db.Column(db.DateTime, nullable=True)
    # Notas opcionales del proveedor al entregar
    notas_entrega = db.Column(db.Text, nullable=True)
    # Campo opcional para mostrar credenciales al cliente (el proveedor decide)
    credenciales_mostrar = db.Column(db.Boolean, default=False)

    cliente = db.relationship('Cliente', backref='compras', lazy=True)
    proveedor = db.relationship('Proveedor', backref='mis_ventas_realizadas', lazy=True)
    producto = db.relationship('Producto', backref='historial_ventas', lazy=True)
    inventario_entregado = db.relationship('InventarioStock', foreign_keys='Venta.inventario_id', backref='venta_asociada', lazy=True)
