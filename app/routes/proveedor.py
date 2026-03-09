import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.models.productos import Producto, Categoria, InventarioStock
from app.models.usuarios import Cliente, Usuario, Proveedor
from app.models.ventas import Venta, ServicioAdquirido
from app.models.notificaciones import Notificacion
from functools import wraps
from datetime import datetime, date, timedelta
from app import db

proveedor_bp = Blueprint('proveedor', __name__, url_prefix='/proveedor')

def proveedor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') != 'Proveedor':
            flash('Acceso denegado. Area exclusiva para proveedores.', 'danger')
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function

@proveedor_bp.route('/dashboard')
@proveedor_required
def dashboard():
    mi_id = session.get('usuario_id')
    
    # Obtener la fecha de hoy usando hora local del servidor
    ahora = datetime.now()
    fecha_hoy_peru = ahora.date()
    
    today_start = datetime.combine(fecha_hoy_peru, datetime.min.time())
    today_end = datetime.combine(fecha_hoy_peru, datetime.max.time())
    
    # 1. Ventas del día (ventas directas de cuentas)
    ventas_hoy = Venta.query.filter(
        Venta.proveedor_id == mi_id,
        Venta.fecha_venta >= today_start,
        Venta.fecha_venta <= today_end
    ).all()
    
    # DEBUG: Verificar si hay ventas totales para este proveedor
    ventas_total = Venta.query.filter_by(proveedor_id=mi_id).all()
    print(f"DEBUG: Total de ventas para proveedor {mi_id}: {len(ventas_total)}")
    for v in ventas_total:
        print(f"  - Venta ID {v.id}: fecha={v.fecha_venta}, proveedor={v.proveedor_id}, producto={v.producto_id}")
    
    # 2. Obtener IDs del inventario del proveedor para servicios
    inventario_ids = [inv.id for inv in InventarioStock.query.filter_by(proveedor_id=mi_id).all()]
    
    # 3. Servicios adquiridos hoy
    servicios_hoy = ServicioAdquirido.query.filter(
        ServicioAdquirido.inventario_id.in_(inventario_ids),
        ServicioAdquirido.fecha_compra >= today_start,
        ServicioAdquirido.fecha_compra <= today_end
    ).all() if inventario_ids else []
    
    # Calcular totales de HOY
    cuentas_vendidas = len(ventas_hoy) + len(servicios_hoy)
    
    # Calcular ingresos del día (suma de precios de ventas + servicios)
    ingresos_hoy = sum(float(v.precio_final) for v in ventas_hoy)
    ingresos_hoy += sum(float(s.precio_pagado) for s in servicios_hoy)
    
    # 4. Stock disponible
    stock_disponible = InventarioStock.query.filter_by(
        proveedor_id=mi_id,
        estado='Disponible'
    ).count()
    
    # 5. Últimas ventas del día (para mostrar en la lista)
    ultimas_ventas = []
    for v in ventas_hoy:
        ultimas_ventas.append({
            'tipo': 'Venta',
            'producto': v.producto.nombre_producto if v.producto else 'N/A',
            'cliente': v.cliente.nombre_completo if v.cliente else 'N/A',
            'precio': v.precio_final,
            'fecha': v.fecha_venta
        })
    for s in servicios_hoy:
        ultimas_ventas.append({
            'tipo': 'Servicio',
            'producto': s.producto.nombre_producto if s.producto else 'N/A',
            'cliente': s.cliente.nombre_completo if s.cliente else 'N/A',
            'precio': s.precio_pagado,
            'fecha': s.fecha_compra
        })
    
    # Ordenar por fecha descendente
    ultimas_ventas.sort(key=lambda x: x['fecha'], reverse=True)
    
    # 6. Obtener TODAS las ventas (historial completo)
    todas_ventas = Venta.query.filter_by(proveedor_id=mi_id).order_by(Venta.fecha_venta.desc()).limit(20).all()
    inventario_ids_all = [inv.id for inv in InventarioStock.query.filter_by(proveedor_id=mi_id).all()]
    todos_servicios = ServicioAdquirido.query.filter(
        ServicioAdquirido.inventario_id.in_(inventario_ids_all)
    ).order_by(ServicioAdquirido.fecha_compra.desc()).limit(20).all() if inventario_ids_all else []
    
    # Combinar todas las ventas para mostrar
    ventas_historial = []
    for v in todas_ventas:
        ventas_historial.append({
            'tipo': 'Venta',
            'producto': v.producto.nombre_producto if v.producto else 'N/A',
            'cliente': v.cliente.nombre_completo if v.cliente else 'N/A',
            'precio': v.precio_final,
            'fecha': v.fecha_venta
        })
    for s in todos_servicios:
        ventas_historial.append({
            'tipo': 'Servicio',
            'producto': s.producto.nombre_producto if s.producto else 'N/A',
            'cliente': s.cliente.nombre_completo if s.cliente else 'N/A',
            'precio': s.precio_pagado,
            'fecha': s.fecha_compra
        })
    
    # Ordenar por fecha descendente
    ventas_historial.sort(key=lambda x: x['fecha'], reverse=True)
    ventas_historial = ventas_historial[:20]
    
    # Calcular totales históricos
    ventas_totales_count = len(todas_ventas) + len(todos_servicios)
    ingresos_totales = sum(float(v.precio_final) for v in todas_ventas)
    ingresos_totales += sum(float(s.precio_pagado) for s in todos_servicios)
    
    return render_template(
        'proveedor/dashboard.html',
        cuentas_vendidas=cuentas_vendidas,
        ingresos_hoy=ingresos_hoy,
        stock_disponible=stock_disponible,
        ultimas_ventas=ultimas_ventas[:10],
        fecha_hoy=fecha_hoy_peru,
        ventas_historial=ventas_historial,
        ventas_totales_count=ventas_totales_count,
        ingresos_totales=ingresos_totales
    )

@proveedor_bp.route('/productos')
@proveedor_required
def mis_productos():
    mi_id = session.get('usuario_id')
    productos = Producto.query.filter_by(proveedor_id=mi_id).all()
    categorias = Categoria.query.filter_by(estado=True).all()
    return render_template('proveedor/productos.html', productos=productos, categorias=categorias)

@proveedor_bp.route('/productos/nuevo', methods=['POST'])
@proveedor_required
def nuevo_producto():
    from app.models.productos import generar_gestion_uso, generar_detalle_solicitud
    
    imagen_url = None
    imagen_file = request.files.get('imagen')
    
    if imagen_file and imagen_file.filename != '':
        filename = secure_filename(imagen_file.filename)
        upload_folder = os.path.join('app', 'static', 'uploads', 'productos')
        os.makedirs(upload_folder, exist_ok=True)
        imagen_file.save(os.path.join(upload_folder, filename))
        imagen_url = f"uploads/productos/{filename}"

    es_renovable = request.form.get('es_renovable') == 'True'
    tipo_entrega = request.form.get('tipo_entrega', 'credenciales')
    tipo_producto = request.form.get('tipo_producto', 'Cuenta Completa')
    
    # Obtener la categoría para generar los textos automáticos
    categoria_id = request.form.get('categoria_id')
    categoria_nombre = ""
    if categoria_id:
        from app.models.productos import Categoria
        categoria = Categoria.query.get(categoria_id)
        if categoria:
            categoria_nombre = categoria.nombre
    
    # Generar textos automáticos basados en categoría, tipo de producto y tipo de entrega
    gestion_uso = generar_gestion_uso(categoria_nombre, tipo_producto, tipo_entrega)
    detalle_solic = generar_detalle_solicitud(categoria_nombre, tipo_producto, tipo_entrega)
    
    nuevo = Producto(
        proveedor_id=session.get('usuario_id'),
        categoria_id=categoria_id,
        nombre_producto=request.form.get('nombre_producto'),
        descripcion=request.form.get('descripcion'),
        imagen_url=imagen_url,
        precio=request.form.get('precio'),
        tipo_producto=tipo_producto,
        es_renovable=es_renovable,
        tipo_entrega=tipo_entrega,
        condicion_uso=gestion_uso,
        detalle_solicitud=detalle_solic
    )
    db.session.add(nuevo)
    db.session.commit()
    flash('Producto agregado a tu catalogo con exito!', 'success')
    return redirect(url_for('proveedor.mis_productos'))

@proveedor_bp.route('/productos/editar/<int:id>', methods=['POST'])
@proveedor_required
def editar_producto(id):
    from app.models.productos import generar_gestion_uso, generar_detalle_solicitud
    
    producto = Producto.query.get_or_404(id)
    
    if producto.proveedor_id != session.get('usuario_id'):
        flash('Error de seguridad: No puedes editar un producto que no te pertenece.', 'danger')
        return redirect(url_for('proveedor.mis_productos'))

    imagen_file = request.files.get('imagen')
    if imagen_file and imagen_file.filename != '':
        filename = secure_filename(imagen_file.filename)
        upload_folder = os.path.join('app', 'static', 'uploads', 'productos')
        os.makedirs(upload_folder, exist_ok=True)
        imagen_file.save(os.path.join(upload_folder, filename))
        producto.imagen_url = f"uploads/productos/{filename}"

    producto.categoria_id = request.form.get('categoria_id')
    producto.nombre_producto = request.form.get('nombre_producto')
    producto.descripcion = request.form.get('descripcion')
    producto.precio = request.form.get('precio')
    producto.tipo_producto = request.form.get('tipo_producto')
    producto.es_renovable = request.form.get('es_renovable') == 'True'
    producto.tipo_entrega = request.form.get('tipo_entrega', 'credenciales')
    
    # Regenerar textos automáticos si cambió el tipo de producto o tipo de entrega
    categoria_nombre = ""
    if producto.categoria:
        categoria_nombre = producto.categoria.nombre
    
    producto.condicion_uso = generar_gestion_uso(categoria_nombre, producto.tipo_producto, producto.tipo_entrega)
    producto.detalle_solicitud = generar_detalle_solicitud(categoria_nombre, producto.tipo_producto, producto.tipo_entrega)
    
    db.session.commit()
    flash(f'El producto "{producto.nombre_producto}" fue actualizado!', 'success')
    return redirect(url_for('proveedor.mis_productos'))

@proveedor_bp.route('/productos/estado/<int:id>')
@proveedor_required
def estado_producto(id):
    producto = Producto.query.get_or_404(id)
    if producto.proveedor_id == session.get('usuario_id'):
        producto.estado = not producto.estado 
        db.session.commit()
        flash(f'El estado de "{producto.nombre_producto}" ha cambiado.', 'info')
    return redirect(url_for('proveedor.mis_productos'))

@proveedor_bp.route('/ventas')
@proveedor_required
def mis_ventas():
    mi_id = session.get('usuario_id')
    ventas = Venta.query.filter_by(proveedor_id=mi_id).order_by(Venta.fecha_venta.desc()).all()
    inventario_ids = [inv.id for inv in InventarioStock.query.filter_by(proveedor_id=mi_id).all()]
    servicios = ServicioAdquirido.query.filter(ServicioAdquirido.inventario_id.in_(inventario_ids)).order_by(ServicioAdquirido.fecha_compra.desc()).all() if inventario_ids else []
    return render_template('proveedor/ventas.html', ventas=ventas, servicios=servicios)

@proveedor_bp.route('/ventas/editar-servicio/<int:id>', methods=['GET', 'POST'])
@proveedor_required
def editar_servicio(id):
    servicio = ServicioAdquirido.query.get_or_404(id)
    
    if servicio.inventario.proveedor_id != session.get('usuario_id'):
        flash('No tienes permiso para editar este servicio.', 'danger')
        return redirect(url_for('proveedor.mis_ventas'))
    
    if request.method == 'POST':
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        
        if fecha_inicio and fecha_fin:
            servicio.fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            servicio.fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            hoy = date.today()
            if servicio.fecha_fin < hoy:
                servicio.estado_servicio = 'Vencido'
            elif (servicio.fecha_fin - hoy).days <= 3:
                servicio.estado_servicio = 'Por Vencer'
            else:
                servicio.estado_servicio = 'Activo'
            
            db.session.commit()
            flash('Fechas del servicio actualizadas correctamente!', 'success')
            return redirect(url_for('proveedor.mis_ventas'))
        else:
            flash('Por favor complete ambas fechas.', 'warning')
    
    return render_template('proveedor/editar_servicio.html', servicio=servicio)

@proveedor_bp.route('/ventas/editar-venta/<int:id>', methods=['GET', 'POST'])
@proveedor_required
def editar_venta(id):
    venta = Venta.query.get_or_404(id)
    
    if venta.proveedor_id != session.get('usuario_id'):
        flash('No tienes permiso para editar esta venta.', 'danger')
        return redirect(url_for('proveedor.mis_ventas'))
    
    if request.method == 'POST':
        nuevo_precio = request.form.get('precio_final')
        if nuevo_precio:
            try:
                venta.precio_final = float(nuevo_precio)
            except ValueError:
                flash('El precio debe ser un numero valido.', 'danger')
                return redirect(url_for('proveedor.mis_ventas'))
        
        fecha_inicio = request.form.get('fecha_inicio_servicio')
        fecha_fin = request.form.get('fecha_fin_servicio')
        
        if fecha_inicio:
            venta.fecha_inicio_servicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        if fecha_fin:
            venta.fecha_fin_servicio = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            hoy = date.today()
            if venta.fecha_fin_servicio < hoy:
                venta.estado_servicio = 'Vencido'
            elif (venta.fecha_fin_servicio - hoy).days <= 3:
                venta.estado_servicio = 'Por Vencer'
            else:
                venta.estado_servicio = 'Activo'
        
        fecha_expiracion = request.form.get('fecha_expiracion_cuenta_proveedor')
        if fecha_expiracion:
            venta.fecha_expiracion_cuenta_proveedor = datetime.strptime(fecha_expiracion, '%Y-%m-%d').date()
        
        db.session.commit()
        flash('Venta actualizada correctamente!', 'success')
        return redirect(url_for('proveedor.mis_ventas'))
    
    return render_template('proveedor/editar_venta.html', venta=venta)

@proveedor_bp.route('/mi-stock')
@proveedor_required
def mi_stock():
    mi_id = session.get('usuario_id')
    inventario = InventarioStock.query.filter_by(proveedor_id=mi_id).order_by(InventarioStock.id.desc()).all()
    productos = Producto.query.filter_by(proveedor_id=mi_id, estado=True).all()
    return render_template('proveedor/mi_stock.html', inventario=inventario, productos=productos)

@proveedor_bp.route('/perfil')
@proveedor_required
def mi_perfil():
    mi_id = session.get('usuario_id') 
    proveedor = Proveedor.query.get(mi_id)
    
    if not proveedor:
        return redirect(url_for('auth.login'))
        
    return render_template('proveedor/perfil.html', proveedor=proveedor)

@proveedor_bp.route('/perfil/editar', methods=['POST'])
@proveedor_required
def editar_perfil():
    mi_id = session.get('usuario_id')
    proveedor = Proveedor.query.get(mi_id)
    
    proveedor.nombre = request.form.get('nombre')
    proveedor.nombre_usuario = request.form.get('nombre_usuario')
    
    nueva_password = request.form.get('password')
    if nueva_password:
        proveedor.password_hash = generate_password_hash(nueva_password)
        
    db.session.commit()
    session['usuario'] = proveedor.nombre
    flash('Perfil actualizado correctamente!', 'success')
    return redirect(url_for('proveedor.mi_perfil'))

@proveedor_bp.route('/cargar-inventario')
@proveedor_required
def cargar_inventario():
    mi_id = session.get('usuario_id')
    mis_productos = Producto.query.filter_by(proveedor_id=mi_id, estado=True).all()
    return render_template('proveedor/cargar_inventario.html', productos=mis_productos)

@proveedor_bp.route('/guardar-stock', methods=['POST'])
@proveedor_required
def guardar_stock():
    producto_id = request.form.get('producto_id')
    
    producto = Producto.query.get(producto_id)
    if not producto:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('proveedor.cargar_inventario'))
    
    tipo_cuenta = producto.tipo_producto
    
    tipo_cuenta_form = request.form.get('tipo_cuenta')
    if tipo_cuenta_form:
        tipo_cuenta = tipo_cuenta_form
    
    if tipo_cuenta == 'Otro':
        tipo_cuenta = request.form.get('tipo_cuenta_otro') or 'Otro'
    
    correo = request.form.get('correo', '').strip() or None
    password = request.form.get('password', '').strip() or None
    perfil = request.form.get('perfil', '').strip() or None
    pin = request.form.get('pin', '').strip() or None
    licencia = request.form.get('licencia', '').strip() or None
    fecha_expiracion = request.form.get('fecha_expiracion')

    fecha_exp_date = None
    if fecha_expiracion:
        fecha_exp_date = datetime.strptime(fecha_expiracion, '%Y-%m-%d').date()

    nuevo_stock = InventarioStock(
        producto_id=producto_id,
        proveedor_id=session.get('usuario_id'),
        tipo_cuenta=tipo_cuenta,
        correo_acceso=correo,
        password_acceso=password,
        nombre_perfil_asignado=perfil,
        pin_seguridad=pin,
        codigo_licencia=licencia,
        fecha_expiracion=fecha_exp_date,
        estado='Disponible'
    )

    db.session.add(nuevo_stock)
    db.session.commit()
    flash('Cuenta cargada exitosamente al inventario!', 'success')
    return redirect(url_for('proveedor.mi_stock'))

@proveedor_bp.route('/stock/editar/<int:id>', methods=['POST'])
@proveedor_required
def editar_stock(id):
    stock = InventarioStock.query.get_or_404(id)
    
    if stock.proveedor_id != session.get('usuario_id'):
        flash('No tienes permiso para editar esta cuenta.', 'danger')
        return redirect(url_for('proveedor.mi_stock'))
    
    correo_anterior = stock.correo_acceso
    password_anterior = stock.password_acceso
    
    stock.producto_id = request.form.get('producto_id')
    tipo_cuenta = request.form.get('tipo_cuenta')
    
    if tipo_cuenta == 'Otro':
        tipo_cuenta = request.form.get('tipo_cuenta_otro') or 'Otro'
    
    stock.tipo_cuenta = tipo_cuenta
    stock.correo_acceso = request.form.get('correo') or None
    stock.password_acceso = request.form.get('password') or None
    stock.nombre_perfil_asignado = request.form.get('perfil') or None
    stock.pin_seguridad = request.form.get('pin') or None
    stock.codigo_licencia = request.form.get('licencia') or None
    
    fecha_expiracion = request.form.get('fecha_expiracion')
    if fecha_expiracion:
        stock.fecha_expiracion = datetime.strptime(fecha_expiracion, '%Y-%m-%d').date()
    else:
        stock.fecha_expiracion = None
    
    db.session.commit()
    
    if stock.estado == 'Vendido':
        # Buscar la venta asociada al inventario
        venta = Venta.query.filter_by(inventario_id=stock.id).first()
        
        # También buscar si hay un servicio adquirido
        servicio = ServicioAdquirido.query.filter_by(inventario_id=stock.id).first()
        
        cliente_id = None
        nombre_producto = stock.producto.nombre_producto if stock.producto else 'Producto'
        venta_id = None
        
        # Prioridad: primero verificar si es una Venta, luego ServicioAdquirido
        if venta:
            cliente_id = venta.cliente_id
            venta_id = venta.id
        elif servicio:
            cliente_id = servicio.cliente_id
            venta_id = servicio.id  # Usamos el ID del servicio como identificador
        
        if cliente_id:
            cambios = []
            if correo_anterior != stock.correo_acceso:
                cambios.append("correo")
            if password_anterior != stock.password_acceso:
                cambios.append("contraseña")
            
            if cambios:
                mensaje = f"Tu cuenta de {nombre_producto} ha sido actualizada. Cambios: {', '.join(cambios)}"
            else:
                mensaje = f"Los datos de tu cuenta de {nombre_producto} han sido actualizados."
            
            # Crear notificación - el modelo usa hora_peru() por defecto
            notificacion = Notificacion(
                cliente_id=cliente_id,
                titulo='Cuenta Actualizada',
                mensaje=mensaje,
                tipo='info',
                venta_id=venta_id
            )
            db.session.add(notificacion)
            db.session.commit()
            
            flash('Cuenta actualizada y cliente notificado!', 'success')
        else:
            flash('Cuenta actualizada correctamente!', 'success')
    else:
        flash('Cuenta actualizada correctamente!', 'success')
    
    return redirect(url_for('proveedor.mi_stock'))

@proveedor_bp.route('/stock/eliminar/<int:id>')
@proveedor_required
def eliminar_stock(id):
    stock = InventarioStock.query.get_or_404(id)
    
    if stock.proveedor_id != session.get('usuario_id'):
        flash('No tienes permiso para eliminar esta cuenta.', 'danger')
        return redirect(url_for('proveedor.mi_stock'))
    
    if stock.estado != 'Disponible':
        flash('No puedes eliminar una cuenta que ya fue vendida.', 'warning')
        return redirect(url_for('proveedor.mi_stock'))
    
    db.session.delete(stock)
    db.session.commit()
    flash('Cuenta eliminada del inventario!', 'success')
    return redirect(url_for('proveedor.mi_stock'))

@proveedor_bp.route('/enviar-codigo-verificacion/<int:venta_id>', methods=['POST'])
@proveedor_required
def enviar_codigo_verificacion(venta_id):
    """El proveedor envía el código de verificación al cliente"""
    from flask import jsonify
    
    venta = Venta.query.get_or_404(venta_id)
    
    # Verificar que la venta pertenece a este proveedor
    if venta.proveedor_id != session.get('usuario_id'):
        return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
    
    # Obtener el código del formulario
    codigo = request.form.get('codigo', '').strip()
    
    if not codigo:
        return jsonify({'success': False, 'message': 'Debes ingresar el código de verificación'}), 400
    
    # Guardar el código en la venta
    venta.codigo_verificacion = codigo
    venta.codigo_verificacion_enviado = True
    venta.fecha_codigo_enviado = datetime.now()
    
    # Marcar como entregado
    venta.estado_entrega = 'Entregado'
    venta.fecha_entrega = datetime.now()
    
    # Crear notificación para el cliente
    mensaje = f"El proveedor ha enviado el código de verificación para tu compra #{venta.codigo_unico}. Ya puedes usarlo en la plataforma."
    
    notificacion = Notificacion(
        cliente_id=venta.cliente_id,
        titulo='Código de Verificación Enviado',
        mensaje=mensaje,
        tipo='success',
        venta_id=venta.id
    )
    
    db.session.add(notificacion)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Código enviado al cliente correctamente'})

@proveedor_bp.route('/marcar-entregado/<int:venta_id>', methods=['POST'])
@proveedor_required
def marcar_entregado(venta_id):
    """El proveedor marca una venta como entregada"""
    from flask import jsonify
    
    venta = Venta.query.get_or_404(venta_id)
    
    # Verificar que la venta pertenece a este proveedor
    if venta.proveedor_id != session.get('usuario_id'):
        return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
    
    # Obtener notas opcionales
    notas = request.form.get('notas', '').strip()
    mostrar_credenciales = request.form.get('mostrar_credenciales', 'false') == 'true'
    
    # Marcar como entregada
    venta.estado_entrega = 'Entregado'
    venta.fecha_entrega = datetime.now()
    venta.notas_entrega = notas if notas else None
    venta.credenciales_mostrar = mostrar_credenciales
    
    # Crear notificación para el cliente
    if venta.producto and venta.producto.tipo_entrega == 'cliente_propio':
        mensaje = f"Tu suscripción a {venta.producto.nombre_producto} (compra #{venta.codigo_unico}) ha sido activada. Ya puedes disfrutar del servicio."
    else:
        mensaje = f"Tu cuenta de {venta.producto.nombre_producto} (compra #{venta.codigo_unico}) ha sido entregada. Revisa tus credenciales en 'Mis Compras'."
    
    notificacion = Notificacion(
        cliente_id=venta.cliente_id,
        titulo='Entrega Completada',
        mensaje=mensaje,
        tipo='success',
        venta_id=venta.id
    )
    
    db.session.add(notificacion)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Venta marcada como entregada'})
