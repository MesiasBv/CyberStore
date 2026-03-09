import re

# Read the file
with open('app/routes/proveedor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace mis_ventas function with pagination
old_code = """@proveedor_bp.route('/ventas')
@proveedor_required
def mis_ventas():
    mi_id = session.get('usuario_id')
    ventas = Venta.query.filter_by(proveedor_id=mi_id).order_by(Venta.fecha_venta.desc()).all()
    inventario_ids = [inv.id for inv in InventarioStock.query.filter_by(proveedor_id=mi_id).all()]
    servicios = ServicioAdquirido.query.filter(ServicioAdquirido.inventario_id.in_(inventario_ids)).order_by(ServicioAdquirido.fecha_compra.desc()).all() if inventario_ids else []
    return render_template('proveedor/ventas.html', ventas=ventas, servicios=servicios)"""

new_code = """@proveedor_bp.route('/ventas')
@proveedor_required
def mis_ventas():
    mi_id = session.get('usuario_id')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Paginar ventas
    ventas_pagination = Venta.query.filter_by(proveedor_id=mi_id).order_by(Venta.fecha_venta.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    ventas = ventas_pagination.items
    
    # Obtener servicios
    inventario_ids = [inv.id for inv in InventarioStock.query.filter_by(proveedor_id=mi_id).all()]
    servicios = ServicioAdquirido.query.filter(
        ServicioAdquirido.inventario_id.in_(inventario_ids)
    ).order_by(ServicioAdquirido.fecha_compra.desc()).all() if inventario_ids else []
    
    return render_template('proveedor/ventas.html', 
                          ventas=ventas, 
                          servicios=servicios,
                          pagination=ventas_pagination,
                          page=page)"""

content = content.replace(old_code, new_code)

# Write back
with open('app/routes/proveedor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('proveedor.py updated!')
