from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from functools import wraps
from werkzeug.security import generate_password_hash
from app import db
from app.models.usuarios import Proveedor, Cliente, Usuario
from app.models.ventas import MovimientoSaldo, Venta, ServicioAdquirido
from app.models.productos import InventarioStock
from datetime import datetime, date, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Un "guardia de seguridad" para asegurar que solo entre el Admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') != 'Admin':
            flash('Acceso denegado. Área exclusiva para administradores.', 'danger')
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # 1. Contar clientes activos
    clientes_activos = Cliente.query.filter_by(estado=True).count()
    
    # 2. Calcular ingresos totales de todas las ventas
    ventas_totales = Venta.query.all()
    servicios_totales = ServicioAdquirido.query.all()
    ingresos_totales = sum(float(v.precio_final) for v in ventas_totales)
    ingresos_totales += sum(float(s.precio_pagado) for s in servicios_totales)
    
    # 3. Contar cuentas en stock (disponibles)
    cuentas_stock = InventarioStock.query.filter_by(estado='Disponible').count()
    
    # 4. Contar proveedores activos
    proveedores_activos = Proveedor.query.filter_by(estado=True).count()
    
    # 5. Ventas de hoy
    hoy = date.today()
    hoy_inicio = datetime.combine(hoy, datetime.min.time())
    hoy_fin = datetime.combine(hoy, datetime.max.time())
    
    ventas_hoy = Venta.query.filter(
        Venta.fecha_venta >= hoy_inicio,
        Venta.fecha_venta <= hoy_fin
    ).count()
    
    inventario_ids = [inv.id for inv in InventarioStock.query.all()]
    servicios_hoy = ServicioAdquirido.query.filter(
        ServicioAdquirido.fecha_compra >= hoy_inicio,
        ServicioAdquirido.fecha_compra <= hoy_fin,
        ServicioAdquirido.inventario_id.in_(inventario_ids)
    ).count() if inventario_ids else 0
    
    ventas_hoy_total = ventas_hoy + servicios_hoy
    
    return render_template('admin/dashboard.html', 
        clientes_activos=clientes_activos,
        ingresos_totales=ingresos_totales,
        cuentas_stock=cuentas_stock,
        proveedores_activos=proveedores_activos,
        ventas_hoy=ventas_hoy_total
    )

# --- NUEVO MÓDULO: GESTIÓN DE PROVEEDORES ---

@admin_bp.route('/proveedores')
@admin_required
def gestion_proveedores():
    # Obtenemos todos los proveedores de la base de datos
    proveedores = Proveedor.query.all()
    return render_template('admin/proveedores.html', proveedores=proveedores)

@admin_bp.route('/proveedores/nuevo', methods=['POST'])
@admin_required
def nuevo_proveedor():
    nombre = request.form.get('nombre')
    nombre_usuario = request.form.get('nombre_usuario')
    correo = request.form.get('correo')
    telefono = request.form.get('telefono_contacto')
    password = request.form.get('password')

    # Verificamos que no exista otro con el mismo correo o usuario
    existe = Proveedor.query.filter((Proveedor.correo == correo) | (Proveedor.nombre_usuario == nombre_usuario)).first()
    if existe:
        flash('Error: El correo o nombre de usuario ya está registrado para otro proveedor.', 'danger')
        return redirect(url_for('admin.gestion_proveedores'))

    # Creamos al proveedor
    nuevo = Proveedor(
        nombre=nombre,
        nombre_usuario=nombre_usuario,
        correo=correo,
        telefono_contacto=telefono,
        password_hash=generate_password_hash(password)
    )
    
    db.session.add(nuevo)
    db.session.commit()
    flash(f'¡El proveedor {nombre} fue registrado con éxito!', 'success')
    return redirect(url_for('admin.gestion_proveedores'))

@admin_bp.route('/proveedores/estado/<int:id>')
@admin_required
def estado_proveedor(id):
    # Esto sirve para Activar/Desactivar a un proveedor con un clic
    proveedor = Proveedor.query.get_or_404(id)
    proveedor.estado = not proveedor.estado # Invierte el estado actual
    db.session.commit()
    
    estado_actual = "activado" if proveedor.estado else "desactivado"
    flash(f'El proveedor {proveedor.nombre} ha sido {estado_actual}.', 'info')
    return redirect(url_for('admin.gestion_proveedores'))

@admin_bp.route('/proveedores/editar/<int:id>', methods=['POST'])
@admin_required
def editar_proveedor(id):
    proveedor = Proveedor.query.get_or_404(id)
    
    nuevo_correo = request.form.get('correo')
    nuevo_usuario = request.form.get('nombre_usuario')
    
    # 1. Verificar que el nuevo correo/usuario no pertenezca a OTRO proveedor
    existe = Proveedor.query.filter(
        (Proveedor.id != id) & 
        ((Proveedor.correo == nuevo_correo) | (Proveedor.nombre_usuario == nuevo_usuario))
    ).first()
    
    if existe:
        flash('Error: El correo o nombre de usuario ya está en uso por otro proveedor.', 'danger')
        return redirect(url_for('admin.gestion_proveedores'))

    # 2. Actualizar los datos
    proveedor.nombre = request.form.get('nombre')
    proveedor.nombre_usuario = nuevo_usuario
    proveedor.correo = nuevo_correo
    proveedor.telefono_contacto = request.form.get('telefono_contacto')
    
    # 3. Solo actualizar contraseña si el Admin escribió una nueva
    nueva_password = request.form.get('password')
    if nueva_password:
        proveedor.password_hash = generate_password_hash(nueva_password)
        
    db.session.commit()
    flash(f'¡El proveedor {proveedor.nombre} fue actualizado correctamente!', 'success')
    return redirect(url_for('admin.gestion_proveedores'))

# ==========================================
#        GESTIÓN DE CLIENTES
# ==========================================

@admin_bp.route('/clientes')
@admin_required
def gestion_clientes():
    clientes = Cliente.query.all()
    return render_template('admin/clientes.html', clientes=clientes)

@admin_bp.route('/clientes/estado/<int:id>')
@admin_required
def estado_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    cliente.estado = not cliente.estado
    db.session.commit()
    
    estado_actual = "activado" if cliente.estado else "desactivado"
    flash(f'El cliente {cliente.nombre_completo} ha sido {estado_actual}.', 'info')
    return redirect(url_for('admin.gestion_clientes'))

@admin_bp.route('/clientes/editar/<int:id>', methods=['POST'])
@admin_required
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    nuevo_correo = request.form.get('correo')
    nuevo_usuario = request.form.get('nombre_usuario')
    
    # Verificar que el nuevo correo/usuario no pertenezca a OTRO cliente
    existe = Cliente.query.filter(
        (Cliente.id != id) & 
        ((Cliente.correo == nuevo_correo) | (Cliente.nombre_usuario == nuevo_usuario))
    ).first()
    
    if existe:
        flash('Error: El correo o nombre de usuario ya está en uso por otro cliente.', 'danger')
        return redirect(url_for('admin.gestion_clientes'))

    # Actualizar datos
    cliente.nombre_completo = request.form.get('nombre_completo')
    cliente.nombre_usuario = nuevo_usuario
    cliente.correo = nuevo_correo
    cliente.telefono_whatsapp = request.form.get('telefono_whatsapp')
    
    # Solo actualizar contraseña si el Admin escribió una nueva
    nueva_password = request.form.get('password')
    if nueva_password:
        cliente.password_hash = generate_password_hash(nueva_password)
        
    db.session.commit()
    flash(f'¡El cliente {cliente.nombre_completo} fue actualizado!', 'success')
    return redirect(url_for('admin.gestion_clientes'))

@admin_bp.route('/clientes/recargar-saldo/<int:id>', methods=['POST'])
@admin_required
def recargar_saldo_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    monto_recarga = request.form.get('monto', type=float)
    
    if monto_recarga and monto_recarga > 0:
        try:
            # Aseguramos que el saldo actual no sea None antes de sumar
            saldo_actual = float(cliente.saldo) if cliente.saldo else 0.0
            nuevo_saldo = saldo_actual + monto_recarga
            cliente.saldo = nuevo_saldo 
            
            # Registrar movimiento de recarga en el historial
            movimiento_recarga = MovimientoSaldo(
                cliente_id=cliente.id,
                tipo='Recarga',
                monto=monto_recarga,
                saldo_resultante=nuevo_saldo,
                descripcion='Recarga de saldo validada por el administrador'
            )
            db.session.add(movimiento_recarga)
            
            db.session.commit()
            flash(f'¡Recarga exitosa! Nuevo saldo: S/ {cliente.saldo}', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}") # Esto imprimirá el error real en tu consola de VS Code
            flash('Error al procesar la recarga.', 'danger')
    else:
        flash('El monto debe ser mayor a 0.', 'warning')
        
    return redirect(url_for('admin.gestion_clientes'))


# ==========================================
#        GESTIÓN DE ADMINISTRADORES
# ==========================================

@admin_bp.route('/administradores')
@admin_required
def gestion_administradores():
    # Traemos a todos los usuarios que son administradores
    admins = Usuario.query.all()
    return render_template('admin/administradores.html', admins=admins)

@admin_bp.route('/administradores/nuevo', methods=['POST'])
@admin_required
def nuevo_administrador():
    nombre_usuario = request.form.get('nombre_usuario')
    correo = request.form.get('correo')
    password = request.form.get('password')

    existe = Usuario.query.filter((Usuario.correo == correo) | (Usuario.nombre_usuario == nombre_usuario)).first()
    if existe:
        flash('Error: El correo o nombre de usuario ya está registrado.', 'danger')
        return redirect(url_for('admin.gestion_administradores'))

    nuevo = Usuario(
        nombre_usuario=nombre_usuario,
        correo=correo,
        password_hash=generate_password_hash(password),
        rol='Admin'
    )
    
    db.session.add(nuevo)
    db.session.commit()
    flash(f'¡El administrador {nombre_usuario} fue registrado con éxito!', 'success')
    return redirect(url_for('admin.gestion_administradores'))

@admin_bp.route('/administradores/estado/<int:id>')
@admin_required
def estado_administrador(id):
    # MEDIDA DE SEGURIDAD: Evitar que el admin activo se bloquee a sí mismo
    if id == session.get('usuario_id'):
        flash('¡Peligro! No puedes desactivar tu propia cuenta mientras tienes la sesión iniciada.', 'warning')
        return redirect(url_for('admin.gestion_administradores'))

    admin = Usuario.query.get_or_404(id)
    admin.estado = not admin.estado 
    db.session.commit()
    
    estado_actual = "activado" if admin.estado else "desactivado"
    flash(f'El administrador {admin.nombre_usuario} ha sido {estado_actual}.', 'info')
    return redirect(url_for('admin.gestion_administradores'))

@admin_bp.route('/administradores/editar/<int:id>', methods=['POST'])
@admin_required
def editar_administrador(id):
    admin = Usuario.query.get_or_404(id)
    nuevo_correo = request.form.get('correo')
    nuevo_usuario = request.form.get('nombre_usuario')
    
    existe = Usuario.query.filter(
        (Usuario.id != id) & 
        ((Usuario.correo == nuevo_correo) | (Usuario.nombre_usuario == nuevo_usuario))
    ).first()
    
    if existe:
        flash('Error: El correo o usuario ya está en uso por otro administrador.', 'danger')
        return redirect(url_for('admin.gestion_administradores'))

    admin.nombre_usuario = nuevo_usuario
    admin.correo = nuevo_correo
    
    nueva_password = request.form.get('password')
    if nueva_password:
        admin.password_hash = generate_password_hash(nueva_password)
        
    db.session.commit()
    flash(f'¡Los datos de {admin.nombre_usuario} fueron actualizados!', 'success')
    return redirect(url_for('admin.gestion_administradores'))

@admin_bp.route('/perfil')
@admin_required
def mi_perfil():
    mi_id = session.get('usuario_id')
    admin = Usuario.query.get(mi_id)
    return render_template('admin/perfil.html', admin=admin)

@admin_bp.route('/perfil/editar', methods=['POST'])
@admin_required
def editar_perfil():
    mi_id = session.get('usuario_id')
    admin = Usuario.query.get(mi_id)
    nuevo_correo = request.form.get('correo')
    nuevo_usuario = request.form.get('nombre_usuario')
    nuevo_telefono = request.form.get('telefono_contacto')
    admin.telefono_contacto = nuevo_telefono
    
    # Verificar que el nuevo correo/usuario no pertenezca a OTRO admin
    existe = Usuario.query.filter(
        (Usuario.id != mi_id) & 
        ((Usuario.correo == nuevo_correo) | (Usuario.nombre_usuario == nuevo_usuario))
    ).first()
    
    if existe:
        flash('Error: El correo o nombre de usuario ya está en uso por otro administrador.', 'danger')
        return redirect(url_for('admin.mi_perfil'))
    
    admin.nombre_usuario = nuevo_usuario
    admin.correo = nuevo_correo
    
    nueva_password = request.form.get('password')
    if nueva_password:
        admin.password_hash = generate_password_hash(nueva_password)
    db.session.commit()
    # Actualizar el nombre en la sesión
    session['usuario'] = admin.nombre_usuario
    flash('Perfil de Admin actualizado correctamente', 'success')
    return redirect(url_for('admin.mi_perfil'))

# ==========================================
#   GESTIÓN DE VENTAS DIARIAS DE PROVEEDORES
# ==========================================

@admin_bp.route('/ventas-proveedores')
@admin_required
def ventas_proveedores():
    # Obtener parámetros de filtro
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    proveedor_id = request.args.get('proveedor_id')
    
    # Determinar rango de fechas por defecto (hoy)
    hoy = date.today()
    
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato de fecha inválido.', 'warning')
            fecha_inicio = hoy
            fecha_fin = hoy
    else:
        # Por defecto: últimos 7 días
        fecha_inicio = hoy - timedelta(days=7)
        fecha_fin = hoy
    
    # Convertir a datetime para сравнение
    fecha_inicio_dt = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin_dt = datetime.combine(fecha_fin, datetime.max.time())
    
    # Construir query base
    query_ventas = Venta.query.filter(
        Venta.fecha_venta >= fecha_inicio_dt,
        Venta.fecha_venta <= fecha_fin_dt
    )
    
    # Filtrar por proveedor si se seleccionó
    if proveedor_id and proveedor_id != 'todos':
        query_ventas = query_ventas.filter(Venta.proveedor_id == int(proveedor_id))
    
    # Obtener todas las ventas en el rango
    ventas = query_ventas.order_by(Venta.fecha_venta.desc()).all()
    
    # Obtener todos los proveedores para el filtro
    proveedores = Proveedor.query.filter_by(estado=True).all()
    
    # Obtener IDs de inventario para servicios
    inventario_ids = [inv.id for inv in InventarioStock.query.all()]
    
    # Obtener servicios adquiridos en el rango
    query_servicios = ServicioAdquirido.query.filter(
        ServicioAdquirido.fecha_compra >= fecha_inicio_dt,
        ServicioAdquirido.fecha_compra <= fecha_fin_dt
    )
    
    if proveedor_id and proveedor_id != 'todos':
        # Filtrar servicios por proveedor del inventario
        inventario_ids_prov = [inv.id for inv in InventarioStock.query.filter_by(proveedor_id=int(proveedor_id)).all()]
        query_servicios = query_servicios.filter(ServicioAdquirido.inventario_id.in_(inventario_ids_prov))
    
    servicios = query_servicios.order_by(ServicioAdquirido.fecha_compra.desc()).all()
    
    # Calcular estadísticas
    # 1. Total de ventas directas
    total_ventas = len(ventas)
    ingresos_ventas = sum(float(v.precio_final) for v in ventas)
    
    # 2. Total de servicios
    total_servicios = len(servicios)
    ingresos_servicios = sum(float(s.precio_pagado) for s in servicios)
    
    # 3. Total general
    total_transacciones = total_ventas + total_servicios
    ingresos_totales = ingresos_ventas + ingresos_servicios
    
    # 4. Ventas por proveedor
    ventas_por_proveedor = {}
    for v in ventas:
        prov_nombre = v.proveedor.nombre if v.proveedor else 'Desconocido'
        if prov_nombre not in ventas_por_proveedor:
            ventas_por_proveedor[prov_nombre] = {'count': 0, 'ingresos': 0}
        ventas_por_proveedor[prov_nombre]['count'] += 1
        ventas_por_proveedor[prov_nombre]['ingresos'] += float(v.precio_final)
    
    for s in servicios:
        prov_nombre = s.inventario.proveedor.nombre if s.inventario and s.inventario.proveedor else 'Desconocido'
        if prov_nombre not in ventas_por_proveedor:
            ventas_por_proveedor[prov_nombre] = {'count': 0, 'ingresos': 0}
        ventas_por_proveedor[prov_nombre]['count'] += 1
        ventas_por_proveedor[prov_nombre]['ingresos'] += float(s.precio_pagado)
    
    # 5. Proveedor top
    proveedor_top = max(ventas_por_proveedor.items(), key=lambda x: x[1]['ingresos']) if ventas_por_proveedor else None
    
    # 6. Ventas de hoy (para mostrar en cards)
    hoy_inicio = datetime.combine(hoy, datetime.min.time())
    hoy_fin = datetime.combine(hoy, datetime.max.time())
    
    ventas_hoy = Venta.query.filter(
        Venta.fecha_venta >= hoy_inicio,
        Venta.fecha_venta <= hoy_fin
    ).all()
    
    inventario_hoy = [inv.id for inv in InventarioStock.query.all()]
    servicios_hoy = ServicioAdquirido.query.filter(
        ServicioAdquirido.fecha_compra >= hoy_inicio,
        ServicioAdquirido.fecha_compra <= hoy_fin,
        ServicioAdquirido.inventario_id.in_(inventario_hoy)
    ).all() if inventario_hoy else []
    
    ventas_hoy_count = len(ventas_hoy) + len(servicios_hoy)
    ingresos_hoy = sum(float(v.precio_final) for v in ventas_hoy) + sum(float(s.precio_pagado) for s in servicios_hoy)
    
    # Combinar ventas y servicios para la tabla
    transacciones = []
    for v in ventas:
        transacciones.append({
            'tipo': 'Venta Directa',
            'codigo': v.codigo_unico,
            'producto': v.producto.nombre_producto if v.producto else 'N/A',
            'proveedor': v.proveedor.nombre if v.proveedor else 'N/A',
            'cliente': v.cliente.nombre_completo if v.cliente else 'N/A',
            'precio': v.precio_final,
            'fecha': v.fecha_venta,
            'estado': v.estado_servicio
        })
    for s in servicios:
        transacciones.append({
            'tipo': 'Servicio',
            'codigo': f'SRV-{s.id}',
            'producto': s.producto.nombre_producto if s.producto else 'N/A',
            'proveedor': s.inventario.proveedor.nombre if s.inventario and s.inventario.proveedor else 'N/A',
            'cliente': s.cliente.nombre_completo if s.cliente else 'N/A',
            'precio': s.precio_pagado,
            'fecha': s.fecha_compra,
            'estado': s.estado_servicio
        })
    
    # Ordenar por fecha descendente
    transacciones.sort(key=lambda x: x['fecha'], reverse=True)
    
    return render_template(
        'admin/ventas_proveedores.html',
        ventas=transacciones,
        proveedores=proveedores,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        proveedor_id=proveedor_id,
        total_ventas=total_ventas,
        total_servicios=total_servicios,
        total_transacciones=total_transacciones,
        ingresos_ventas=ingresos_ventas,
        ingresos_servicios=ingresos_servicios,
        ingresos_totales=ingresos_totales,
        ventas_por_proveedor=ventas_por_proveedor,
        proveedor_top=proveedor_top,
        ventas_hoy_count=ventas_hoy_count,
        ingresos_hoy=ingresos_hoy,
        hoy=hoy.strftime('%Y-%m-%d'),
        date=date,
        timedelta=timedelta
    )
