
from sqlalchemy import exists
from sqlalchemy.orm import joinedload
from flask import Blueprint, render_template, jsonify
from flask import session, flash, redirect, url_for, request
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.usuarios import Cliente, Proveedor
from app.models.productos import Producto, InventarioStock
from app.models.ventas import Venta, MovimientoSaldo
from app.models.notificaciones import Notificacion
from datetime import datetime, date
from urllib.parse import quote
import random
import string

public_bp = Blueprint('public', __name__)

def generar_codigo_unico():
    """Genera un código único aleatorio para ventas (formato: CS-XXXXXXXX)"""
    while True:
        caracteres = string.ascii_uppercase + string.digits
        codigo_aleatorio = ''.join(random.choices(caracteres, k=8))
        codigo = f"CS-{codigo_aleatorio}"
        # Verificar que no exista ya
        if not Venta.query.filter_by(codigo_unico=codigo).first():
            return codigo

@public_bp.route('/')
def index():
    # Solo productos activos de proveedores activos
    productos = Producto.query.filter_by(estado=True).join(Proveedor).filter(Proveedor.estado == True).all()
    
    user_obj = None
    compra_exitosa_id = request.args.get('compra_exitosa', type=int)
    
    if session.get('rol') == 'Cliente':
        user_obj = Cliente.query.get(session.get('usuario_id'))
    
    return render_template('index.html', productos=productos, current_user_obj=user_obj, compra_exitosa_id=compra_exitosa_id)

@public_bp.route('/catalogo')
def catalogo():
    # Obtener parámetros de búsqueda y filtro
    busqueda = request.args.get('busqueda', '').strip()
    categoria_id = request.args.get('categoria', type=int)
    
    # Consulta base - solo productos activos de proveedores activos
    query = Producto.query.filter_by(estado=True).join(Proveedor).filter(Proveedor.estado == True)
    
    # Aplicar filtro de búsqueda por nombre
    if busqueda:
        query = query.filter(Producto.nombre_producto.ilike(f'%{busqueda}%'))
    
    # Aplicar filtro de categoría  
    if categoria_id:
        query = query.filter(Producto.categoria_id == categoria_id)
    
    productos = query.all()
    
    # Obtener todas las categorías para el filtro
    from app.models.productos import Categoria
    categorias = Categoria.query.filter_by(estado=True).all()
    
    # Obtener el usuario actual si es cliente
    user_obj = None
    if session.get('rol') == 'Cliente':
        user_obj = Cliente.query.get(session.get('usuario_id'))
    
    return render_template('catalogo.html', productos=productos, categorias=categorias, 
                          busqueda_actual=busqueda, categoria_actual=categoria_id,
                          current_user_obj=user_obj)

@public_bp.route('/buscar-productos')
def buscar_productos():
    """API para buscar productos en tiempo real sin recargar la página"""
    busqueda = request.args.get('busqueda', '').strip()
    categoria_id = request.args.get('categoria', type=int)
    orden = request.args.get('orden', 'default')
    
    # Consulta base - solo productos activos de proveedores activos
    query = Producto.query.filter_by(estado=True).join(Proveedor).filter(Proveedor.estado == True)
    
    # Aplicar filtro de búsqueda por nombre
    if busqueda:
        query = query.filter(Producto.nombre_producto.ilike(f'%{busqueda}%'))
    
    # Aplicar filtro de categoría
    if categoria_id:
        query = query.filter(Producto.categoria_id == categoria_id)
    
    # Aplicar ordenamiento
    if orden == 'precio_asc':
        query = query.order_by(Producto.precio.asc())
    elif orden == 'precio_desc':
        query = query.order_by(Producto.precio.desc())
    elif orden == 'nombre_asc':
        query = query.order_by(Producto.nombre_producto.asc())
    elif orden == 'nombre_desc':
        query = query.order_by(Producto.nombre_producto.desc())
    elif orden == 'mas_vendidos':
        # Ordenar por cantidad de ventas (más vendidos primero)
        from app.models.ventas import Venta
        query = query.outerjoin(Venta).group_by(Producto.id).order_by(db.func.count(Venta.id).desc())
    else:
        # Orden por defecto: más recientes primero
        query = query.order_by(Producto.id.desc())
    
    productos = query.all()
    
    # Devolver datos en JSON
    return jsonify({
        'productos': [
            {
                'id': p.id,
                'nombre_producto': p.nombre_producto,
                'precio': float(p.precio),
                'imagen_url': p.imagen_url,
                'categoria_nombre': p.categoria.nombre if p.categoria else '',
                'proveedor_nombre': p.proveedor.nombre if p.proveedor else '',
                'tipo_producto': p.tipo_producto,
                'tipo_entrega': p.tipo_entrega,
                'es_renovable': p.es_renovable,
                'stock': p.stock_disponible()
            }
            for p in productos
        ]
    })

@public_bp.route('/comprar/<int:id>', methods=['POST'])
def procesar_compra(id):
    if session.get('rol') != 'Cliente':
        flash('Debes ser cliente para comprar.', 'danger')
        return redirect(url_for('auth.login'))

    cliente = Cliente.query.get(session.get('usuario_id'))
    producto = Producto.query.get_or_404(id)
    
    # Determinar el tipo de entrega del producto
    tipo_entrega = producto.tipo_entrega or 'credenciales'
    
    # Variables para la venta
    cuenta_disponible = None
    inventario_id = None
    
    # Para 'credenciales', 'codigo' y 'cliente_propio': buscar en inventario
    # Para 'cuenta_cliente': NO se usa inventario (el proveedor crea la cuenta manualmente)
    if tipo_entrega in ['credenciales', 'codigo', 'cliente_propio']:
        cuenta_disponible = InventarioStock.query.filter_by(
            producto_id=id, 
            estado='Disponible'
        ).first()

        if not cuenta_disponible:
            flash('Lo sentimos, este producto se acaba de agotar.', 'warning')
            return redirect(url_for('public.index'))
        
        inventario_id = cuenta_disponible.id

    if cliente.saldo < producto.precio:
        flash(f'Saldo insuficiente. El producto cuesta S/ {producto.precio} y tú tienes S/ {cliente.saldo}.', 'danger')
        return redirect(url_for('public.index'))

    try:
        # Obtener correo del cliente si el tipo de entrega es 'cliente_propio'
        correo_cliente = request.form.get('correo_cliente', '').strip() if tipo_entrega == 'cliente_propio' else None

        # Restar saldo al cliente
        cliente.saldo -= producto.precio

        # Registrar movimiento de compra en el historial
        movimiento_compra = MovimientoSaldo(
            cliente_id=cliente.id,
            tipo='Compra',
            monto=producto.precio,
            saldo_resultante=cliente.saldo,
            descripcion=f'Compra de: {producto.nombre_producto}'
        )
        db.session.add(movimiento_compra)

        proveedor = Proveedor.query.get(producto.proveedor_id)
        proveedor.saldo += producto.precio

        # Marcar cuenta como vendido solo si se usó inventario
        if cuenta_disponible:
            cuenta_disponible.estado = 'Vendido'
            # Si es cliente_propio, guardar el correo del cliente en el inventario
            if tipo_entrega == 'cliente_propio' and correo_cliente:
                cuenta_disponible.correo_acceso = correo_cliente

        # Obtener fecha y hora actual del servidor (hora local)
        ahora = datetime.now()
        fecha_hoy = ahora.date()

        # Calcular fecha fin: mismo dia, mes siguiente
        mes_siguiente = fecha_hoy.month + 1
        año = fecha_hoy.year
        if mes_siguiente > 12:
            mes_siguiente = 1
            año += 1

        dias_en_mes_siguiente = [31, 29 if (año % 4 == 0 and año % 100 != 0) or (año % 400 == 0) else 28,
                                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        dia = min(fecha_hoy.day, dias_en_mes_siguiente[mes_siguiente - 1])
        fecha_fin = date(año, mes_siguiente, dia)

        # Determinar estado de entrega inicial
        # 'cliente_propio' siempre es Pendiente (cliente debe dar su correo)
        # 'credenciales' y 'codigo' también inician como Pendiente hasta que el proveedor marque entrega
        estado_entrega_inicial = 'Pendiente'

        nueva_venta = Venta(
            codigo_unico=generar_codigo_unico(),
            cliente_id=cliente.id,
            proveedor_id=proveedor.id,
            producto_id=producto.id,
            inventario_id=inventario_id,
            precio_final=producto.precio,
            fecha_inicio_servicio=fecha_hoy,
            fecha_fin_servicio=fecha_fin,
            estado_servicio='Activo',
            fecha_venta=ahora,
            estado_entrega=estado_entrega_inicial,
            correo_cliente=correo_cliente
        )
        
        # Actualizar fecha de expiración solo si hay cuenta en inventario
        if cuenta_disponible:
            cuenta_disponible.fecha_expiracion = fecha_fin
        
        db.session.add(nueva_venta)
        db.session.commit()
        
        # Redireccionar a la página principal con el ID de la nueva venta para mostrar el mensaje
        return redirect(url_for('public.index', compra_exitosa=nueva_venta.id))
            
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG ERROR: {e}")
        flash(f'Error técnico: {e}', 'danger')

    return redirect(url_for('public.index'))

@public_bp.route('/mis-compras')
def mis_compras():
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        flash('Debes iniciar sesión para ver tus compras.', 'warning')
        return redirect(url_for('auth.login'))
    
    cliente_id = session.get('usuario_id')
    user_obj = Cliente.query.get(cliente_id)
    
    # Cargar las relaciones explícitamente para evitar problemas de lazy loading
    compras = Venta.query.filter_by(cliente_id=cliente_id).options(
        joinedload(Venta.producto),
        joinedload(Venta.proveedor)
    ).order_by(Venta.fecha_venta.desc()).all()
    
    # Cargar el inventario para cada compra manualmente
    for compra in compras:
        if compra.inventario_id:
            compra.inventario_cargado = InventarioStock.query.get(compra.inventario_id)
        else:
            compra.inventario_cargado = None
    
    # Obtener todas las notificaciones (leídas y no leídas)
    notificaciones = Notificacion.query.filter_by(cliente_id=cliente_id).order_by(Notificacion.fecha_creacion.desc()).all()
    notificaciones_count = len([n for n in notificaciones if not n.leida])
    
    # Obtener parámetro para abrir modal automáticamente
    abrir_venta_id = request.args.get('abrir_venta', type=int)
    
    return render_template('mis_compras.html', compras=compras, current_user_obj=user_obj, notificaciones=notificaciones, notificaciones_count=notificaciones_count, abrir_venta_id=abrir_venta_id)

@public_bp.route('/notificaciones/marcar-leida/<int:id>')
def marcar_notificacion_leida(id):
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    notificacion = Notificacion.query.get_or_404(id)
    
    if notificacion.cliente_id != session.get('usuario_id'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    
    notificacion.leida = True
    db.session.commit()
    
    return jsonify({'success': True})

@public_bp.route('/notificaciones/json')
def notificaciones_json():
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        return jsonify({'notificaciones': [], 'count': 0})
    
    cliente_id = session.get('usuario_id')
    # Obtener todas las notificaciones (leídas y no leídas)
    notificaciones = Notificacion.query.filter_by(cliente_id=cliente_id).order_by(Notificacion.fecha_creacion.desc()).limit(20).all()
    notificaciones_no_leidas = [n for n in notificaciones if not n.leida]
    
    return jsonify({
        'notificaciones': [
            {
                'id': n.id,
                'titulo': n.titulo,
                'mensaje': n.mensaje,
                'tipo': n.tipo,
                'fecha': n.fecha_creacion.strftime('%d/%m/%Y %H:%M') if n.fecha_creacion else '',
                'fecha_raw': n.fecha_creacion.isoformat() if n.fecha_creacion else None,
                'venta_id': n.venta_id,
                'leida': n.leida
            } for n in notificaciones
        ],
        'count': len(notificaciones_no_leidas)
    })

@public_bp.route('/mi-billetera')
def mi_billetera():
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        flash('Debes iniciar sesión para ver tu billetera.', 'warning')
        return redirect(url_for('auth.login'))
    
    cliente_id = session.get('usuario_id')
    user_obj = Cliente.query.get(cliente_id)
    movimientos = MovimientoSaldo.query.filter_by(cliente_id=cliente_id).order_by(MovimientoSaldo.fecha_movimiento.desc()).all()
    
    return render_template('mi_billetera.html', current_user_obj=user_obj, movimientos=movimientos)

@public_bp.route('/mi-billetera/agregar', methods=['POST'])
def agregar_fondos():
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        flash('Debes iniciar sesión para agregar fondos.', 'warning')
        return redirect(url_for('auth.login'))
    
    monto = request.form.get('monto')
    
    try:
        monto = float(monto)
        if monto < 3:
            flash('El monto mínimo de recarga es de S/ 3.00.', 'danger')
            return redirect(url_for('public.mi_billetera'))
        if monto > 500:
            flash('El monto máximo de recarga es de S/ 500.00.', 'danger')
            return redirect(url_for('public.mi_billetera'))
    except:
        flash('Monto inválido.', 'danger')
        return redirect(url_for('public.mi_billetera'))
    
    cliente = Cliente.query.get(session.get('usuario_id'))
    
    # Actualizar saldo
    cliente.saldo += monto
    
    # Registrar movimiento de recarga en el historial
    nuevo_movimiento = MovimientoSaldo(
        cliente_id=cliente.id,
        tipo='Recarga',
        monto=monto,
        saldo_resultante=cliente.saldo,
        descripcion='Recarga de saldo mediante transferencia/depósito'
    )
    
    db.session.add(nuevo_movimiento)
    db.session.commit()
    
    flash(f'¡Se han agregado S/ {monto:.2f} a tu billetera!', 'success')
    return redirect(url_for('public.mi_billetera'))

@public_bp.route('/obtener-credenciales-venta/<int:venta_id>')
def obtener_credenciales_venta(venta_id):
    """Obtiene las credenciales actualizadas de una venta específica"""
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    # Obtener la venta y verificar que pertenece al cliente
    venta = Venta.query.filter_by(id=venta_id, cliente_id=session.get('usuario_id')).first()
    
    if not venta:
        return jsonify({'success': False, 'message': 'Venta no encontrada'}), 404
    
    # Obtener las credenciales actualizadas desde el inventario
    if venta.inventario_id:
        inventario = InventarioStock.query.get(venta.inventario_id)
        if inventario:
            return jsonify({
                'success': True,
                'correo': inventario.correo_acceso,
                'password': inventario.password_acceso,
                'pin': inventario.pin_seguridad,
                'perfil': inventario.nombre_perfil_asignado
            })
    
    return jsonify({'success': False, 'message': 'No hay credenciales disponibles'}), 404

@public_bp.route('/mi-perfil')
def mi_perfil():
    """Página de perfil del cliente"""
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        flash('Debes iniciar sesión para ver tu perfil.', 'warning')
        return redirect(url_for('auth.login'))
    
    cliente_id = session.get('usuario_id')
    user_obj = Cliente.query.get(cliente_id)
    
    return render_template('cliente/perfil.html', current_user_obj=user_obj)

@public_bp.route('/verificar-estado-usuario')
def verificar_estado_usuario():
    """Verifica si el usuario actual sigue activo en el sistema"""
    if not session.get('usuario_id'):
        return jsonify({'activo': False, 'reason': 'no_session'})
    
    rol = session.get('rol')
    usuario_id = session.get('usuario_id')
    
    try:
        if rol == 'Cliente':
            usuario = Cliente.query.get(usuario_id)
        elif rol == 'Proveedor':
            usuario = Proveedor.query.get(usuario_id)
        elif rol == 'Admin':
            from app.models.usuarios import Usuario
            usuario = Usuario.query.get(usuario_id)
        else:
            return jsonify({'activo': False, 'reason': 'unknown_rol'})
        
        if not usuario:
            return jsonify({'activo': False, 'reason': 'user_not_found'})
        
        if not usuario.estado:
            session.clear()
            return jsonify({'activo': False, 'reason': 'user_inactive'})
        
        return jsonify({'activo': True})
        
    except Exception as e:
        return jsonify({'activo': False, 'reason': str(e)})

@public_bp.route('/mi-perfil/actualizar', methods=['POST'])
def actualizar_perfil():
    """Actualizar perfil del cliente"""
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        flash('Debes iniciar sesión para actualizar tu perfil.', 'warning')
        return redirect(url_for('auth.login'))
    
    cliente = Cliente.query.get(session.get('usuario_id'))
    
    # Obtener datos del formulario
    nombre_completo = request.form.get('nombre_completo', '').strip()
    telefono_whatsapp = request.form.get('telefono_whatsapp', '').strip()
    correo = request.form.get('correo', '').strip()
    password_actual = request.form.get('password_actual', '').strip()
    password_nuevo = request.form.get('password_nuevo', '').strip()
    
    # Validar correo único si se está cambiando
    if correo and correo != cliente.correo:
        existe_correo = Cliente.query.filter(Cliente.correo == correo, Cliente.id != cliente.id).first()
        if existe_correo:
            flash('El correo electrónico ya está en uso por otro usuario.', 'danger')
            return redirect(url_for('public.mi_perfil'))
        cliente.correo = correo
    
    # Actualizar datos
    cliente.nombre_completo = nombre_completo
    cliente.telefono_whatsapp = telefono_whatsapp
    
    # Cambiar contraseña si se proporcionó
    if password_actual or password_nuevo:
        if not password_actual:
            flash('Debes ingresar tu contraseña actual para cambiar la contraseña.', 'danger')
            return redirect(url_for('public.mi_perfil'))
        if not password_nuevo:
            flash('Debes ingresar la nueva contraseña.', 'danger')
            return redirect(url_for('public.mi_perfil'))
        
        # Verificar contraseña actual
        from werkzeug.security import check_password_hash
        if not check_password_hash(cliente.password_hash, password_actual):
            flash('La contraseña actual es incorrecta.', 'danger')
            return redirect(url_for('public.mi_perfil'))
        
        # Actualizar contraseña
        cliente.password_hash = generate_password_hash(password_nuevo)
        flash('Contraseña actualizada correctamente.', 'success')
    
    db.session.commit()
    flash('Perfil actualizado correctamente.', 'success')
    return redirect(url_for('public.mi_perfil'))

@public_bp.route('/solicitar-codigo-verificacion/<int:venta_id>', methods=['POST'])
def solicitar_codigo_verificacion(venta_id):
    """El cliente solicita el código de verificación al proveedor"""
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    venta = Venta.query.filter_by(id=venta_id, cliente_id=session.get('usuario_id')).first()
    
    if not venta:
        return jsonify({'success': False, 'message': 'Venta no encontrada'}), 404
    
    # Verificar que el producto sea de tipo 'codigo'
    if not venta.producto or venta.producto.tipo_entrega != 'codigo':
        return jsonify({'success': False, 'message': 'Esta venta no requiere código de verificación'}), 400
    
    # Crear notificación al proveedor
    proveedor = Proveedor.query.get(venta.proveedor_id)
    
    mensaje = f"El cliente ha solicitado el código de verificación para la compra #{venta.codigo_unico} ({venta.producto.nombre_producto}). Por favor envíale el código."
    
    notificacion = Notificacion(
        cliente_id=session.get('usuario_id'),
        titulo='Código de Verificación Solicitado',
        mensaje=mensaje,
        tipo='warning',
        venta_id=venta.id
    )
    
    db.session.add(notificacion)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Tu solicitud ha sido enviada al proveedor. Te notificaremos cuando envíe el código.'
    })

@public_bp.route('/ingresar-correo-entrega/<int:venta_id>', methods=['POST'])
def ingresar_correo_entrega(venta_id):
    """El cliente ingresa su correo para productos tipo cliente_propio"""
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    venta = Venta.query.filter_by(id=venta_id, cliente_id=session.get('usuario_id')).first()
    
    if not venta:
        return jsonify({'success': False, 'message': 'Venta no encontrada'}), 404
    
    correo = request.form.get('correo', '').strip()
    
    if not correo:
        return jsonify({'success': False, 'message': 'Debes ingresar un correo válido'}), 400
    
    # Guardar el correo del cliente en la venta
    venta.correo_cliente = correo
    
    # También guardar en el inventario si existe
    if venta.inventario_id:
        inventario = InventarioStock.query.get(venta.inventario_id)
        if inventario:
            inventario.correo_acceso = correo
    
    db.session.commit()
    
    # Notificar al proveedor
    proveedor = Proveedor.query.get(venta.proveedor_id)
    mensaje = f"Nuevo cliente ha proporcionado su correo para la compra #{venta.codigo_unico}. Producto: {venta.producto.nombre_producto}. Correo del cliente: {correo}"
    
    notificacion = Notificacion(
        cliente_id=session.get('usuario_id'),
        titulo='Correo del Cliente Recibido',
        mensaje=mensaje,
        tipo='info',
        venta_id=venta.id
    )
    
    db.session.add(notificacion)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Tu correo ha sido enviado al proveedor. Te contactará pronto.'
    })

@public_bp.route('/guardar-correo-y-contactar', methods=['POST'])
def guardar_correo_y_contactar():
    """Guarda el correo del cliente y retorna la URL de WhatsApp"""
    if not session.get('usuario_id') or session.get('rol') != 'Cliente':
        return jsonify({'success': False, 'message': 'No autorizado', 'whatsapp_url': ''}), 401

    venta_id = request.form.get('venta_id', type=int)
    correo = request.form.get('correo', '').strip()

    if not venta_id:
        return jsonify({'success': False, 'message': 'ID de venta inválido', 'whatsapp_url': ''}), 400

    venta = Venta.query.filter_by(id=venta_id, cliente_id=session.get('usuario_id')).first()

    if not venta:
        return jsonify({'success': False, 'message': 'Venta no encontrada', 'whatsapp_url': ''}), 404

    # Guardar el correo si se proporcionó
    if correo:
        venta.correo_cliente = correo
        
        # También guardar en el inventario si existe
        if venta.inventario_id:
            inventario = InventarioStock.query.get(venta.inventario_id)
            if inventario:
                inventario.correo_acceso = correo
        
        db.session.commit()

        # Notificar al proveedor
        proveedor = Proveedor.query.get(venta.proveedor_id)
        mensaje = f"Nuevo cliente ha proporcionado su correo para la compra #{venta.codigo_unico}. Producto: {venta.producto.nombre_producto}. Correo del cliente: {correo}"

        notificacion = Notificacion(
            cliente_id=session.get('usuario_id'),
            titulo='Correo del Cliente Recibido',
            mensaje=mensaje,
            tipo='info',
            venta_id=venta.id
        )
        db.session.add(notificacion)
        db.session.commit()

    # Generar URL de WhatsApp
    whatsapp_url = ''
    if venta.proveedor and venta.proveedor.telefono_contacto:
        mensaje = f'Hola, vengo de CyberStore y adquirí {venta.producto.nombre_producto} (código: {venta.codigo_unico}).'
        if correo:
            mensaje += f' Mi correo es: {correo}'
        whatsapp_url = f'https://wa.me/51{venta.proveedor.telefono_contacto}?text={quote(mensaje)}'

    return jsonify({
        'success': True, 
        'message': 'Correo guardado correctamente',
        'whatsapp_url': whatsapp_url
    })

# ============================================
# RUTAS DE PÁGINAS LEGALES
# ============================================

@public_bp.route('/terminos')
def terminos():
    return render_template('legal/terminos.html')

@public_bp.route('/privacidad')
def privacidad():
    return render_template('legal/privacidad.html')

@public_bp.route('/ayuda')
def ayuda():
    return render_template('legal/ayuda.html')


@public_bp.route('/enviar-sugerencia', methods=['POST'])
def enviar_sugerencia():
    """Guarda una sugerencia del usuario"""
    mensaje = request.form.get('mensaje', '').strip()
    
    if not mensaje:
        return jsonify({'success': False, 'message': 'El mensaje no puede estar vacío'}), 400
    
    usuario_id = session.get('usuario_id')
    nombre_usuario = session.get('usuario', 'Anónimo')
    
    # Guardar usando SQLAlchemy
    try:
        cursor = db.session.execute(
            db.text("INSERT INTO sugerencias (usuario_id, nombre_usuario, mensaje) VALUES (:uid, :nombre, :msg)"),
            {"uid": usuario_id, "nombre": nombre_usuario, "msg": mensaje}
        )
        db.session.commit()
        
        return jsonify({'success': True, 'message': '¡Gracias por tu sugerencia!'})
    except Exception as e:
        print(f"Error en sugerir: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
