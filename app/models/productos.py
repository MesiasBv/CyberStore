from app import db
from datetime import datetime
from app.utils.hora_peru import obtener_hora_peru

def generar_gestion_uso(categoria_nombre, tipo_producto, tipo_entrega):
    """Genera automáticamente la gestión de uso basada en categoría, tipo de producto y tipo de entrega"""
    categoria = categoria_nombre.lower() if categoria_nombre else ""
    tipo_prod = tipo_producto.lower() if tipo_producto else ""
    tipo_ent = tipo_entrega.lower() if tipo_entrega else ""
    
    gestion = []
    
    # Reglas comunes para todos los tipos
    gestion.append("No cambiar la contraseña de la cuenta.")
    gestion.append("No cambiar el correo de recuperación.")
    
    # Por tipo de producto
    if tipo_prod == "perfil individual" or tipo_prod == "perfil":
        gestion.append("No modificar el nombre del perfil.")
        gestion.append("No eliminar el perfil asignado.")
        gestion.append("Solo puedes gestionar el perfil que te fue asignado.")
    elif tipo_prod == "cuenta completa":
        gestion.append("Puedes gestionar todos los perfiles de la cuenta.")
        gestion.append("Puedes ver y gestionar contenido de la cuenta.")
    elif tipo_prod == "cuenta compartida":
        gestion.append("Gestiona solo tu perfil asignado.")
        gestion.append("No accedas a perfiles de otros usuarios.")
    elif tipo_prod == "licencia":
        gestion.append("La licencia es personal e intransferible.")
        gestion.append("No compartir las credenciales de activación.")
    
    # Por tipo de entrega
    if tipo_ent == "credenciales":
        gestion.append("Las credenciales se entregan de forma automática.")
    elif tipo_ent == "codigo":
        gestion.append("El código de activación es de un solo uso.")
    elif tipo_ent == "cliente_propio":
        gestion.append("Debes proporcionar tu propio correo para la activación.")
        gestion.append("El proveedor creará la cuenta en tu correo.")
    
    # Por categoría (servicio específico)
    if "netflix" in categoria or "spotify" in categoria or "youtube" in categoria or "disney" in categoria:
        gestion.append("No realizar cambios que violen los Términos de Servicio.")
        gestion.append("La cuenta puede ser suspendida si se detecta uso indebido.")
    
    return "<li>" + "</li><li>".join(gestion) + "</li>"

def generar_detalle_solicitud(categoria_nombre, tipo_producto, tipo_entrega):
    """Genera automáticamente el detalle de solicitud basado en categoría, tipo de producto y tipo de entrega"""
    categoria = categoria_nombre.lower() if categoria_nombre else ""
    tipo_prod = tipo_producto.lower() if tipo_producto else ""
    tipo_ent = tipo_entrega.lower() if tipo_entrega else ""
    
    detalle = []
    
    # Por tipo de entrega
    if tipo_ent == "credenciales":
        detalle.append("Entrega inmediata tras verificar el pago.")
        detalle.append("Recibirás las credenciales en 'Mis Compras'.")
        detalle.append("Podrás ver la contraseña al hacer clic en 'Ver Credenciales'.")
    elif tipo_ent == "codigo":
        detalle.append("Recibirás un código de activación único.")
        detalle.append("El código será enviado tras confirmar el pago.")
        detalle.append("Contacta al proveedor si tienes problemas con el código.")
    elif tipo_ent == "cliente_propio":
        detalle.append("Debes proporcionar tu correo electrónico.")
        detalle.append("El proveedor creará la cuenta en tu correo o bien recibirás una invitación al grupo familiar en tu correo.")
        detalle.append("Recibirás una notificación cuando esté listo.")
    
    # Por tipo de producto
    if tipo_prod == "perfil individual" or tipo_prod == "perfil":
        detalle.append("Se te asignará un perfil exclusivo.")
        detalle.append("No puedes cambiar de perfil después de asignado.")
    elif tipo_prod == "cuenta completa":
        detalle.append("Recibirás acceso completo a la cuenta.")
        detalle.append("Podrás gestionar todos los perfiles disponibles.")
    
    # Por categoría específica
    if "netflix" in categoria:
        detalle.append("Netflix puede pedir verificación de dispositivo.")
        detalle.append("Si se bloquea, contacta al proveedor.")
    elif "spotify" in categoria:
        detalle.append("Spotify puede requerir verificación de dispositivo.")
        detalle.append("La cuenta incluye Premium.")
    elif "youtube" in categoria or "music" in categoria:
        detalle.append("Incluye Premium/Music según el plan contratado.")
    elif "chatgpt" in categoria or "openai" in categoria:
        detalle.append("El acceso incluye el plan Plus/Pro.")
        detalle.append("No abuses del uso para evitar bloqueos.")

    return " ".join(detalle)

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    link_acceso = db.Column(db.String(255))
    longitud_pin_requerido = db.Column(db.Integer, nullable=True)
    estado = db.Column(db.Boolean, default=True)
    
    productos = db.relationship('Producto', backref='categoria', lazy=True)

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=False)
    nombre_producto = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    imagen_url = db.Column(db.String(255))
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    tipo_producto = db.Column(db.String(50), nullable=False, default='Cuenta Completa')
    es_renovable = db.Column(db.Boolean, default=False)
    tipo_entrega = db.Column(db.String(20), default='credenciales')
    condicion_uso = db.Column(db.Text, nullable=True)
    detalle_solicitud = db.Column(db.Text, nullable=True)
    estado = db.Column(db.Boolean, default=True)
    
    inventario = db.relationship('InventarioStock', backref='producto', lazy=True)

    def stock_disponible(self):
        from app.models.productos import InventarioStock
        return InventarioStock.query.filter_by(producto_id=self.id, estado='Disponible').count()
    
    def generar_textos_automaticos(self):
        """Genera automáticamente la gestión de uso y detalle de solicitud"""
        categoria_nombre = self.categoria.nombre if self.categoria else ""
        
        self.condicion_uso = generar_gestion_uso(categoria_nombre, self.tipo_producto, self.tipo_entrega)
        self.detalle_solicitud = generar_detalle_solicitud(categoria_nombre, self.tipo_producto, self.tipo_entrega)

class InventarioStock(db.Model):
    __tablename__ = 'inventario_stock'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=False)
    tipo_cuenta = db.Column(db.String(50), nullable=True)
    
    correo_acceso = db.Column(db.String(255), nullable=True)
    password_acceso = db.Column(db.String(255), nullable=True)
    nombre_perfil_asignado = db.Column(db.String(50), nullable=True)
    pin_seguridad = db.Column(db.String(20), nullable=True)
    codigo_licencia = db.Column(db.String(255), nullable=True)
    
    estado = db.Column(db.Enum('Disponible', 'Vendido', 'Baneada/Inactiva'), default='Disponible')
    fecha_ingreso = db.Column(db.DateTime, default=obtener_hora_peru)
    fecha_expiracion = db.Column(db.Date, nullable=True)

