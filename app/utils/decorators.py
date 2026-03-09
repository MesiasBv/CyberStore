from functools import wraps
from flask import session, redirect, url_for, flash

def admin_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica si el usuario actual tiene el rol de Admin
        if session.get('rol') != 'Admin':
            flash('Acceso denegado. Se requieren credenciales de Administrador.', 'danger')
            # Si no es admin, lo patea a la página principal
            return redirect(url_for('public.index')) 
        return f(*args, **kwargs)
    return decorated_function

def proveedor_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica si el usuario actual es un Proveedor
        if session.get('rol') != 'Proveedor':
            flash('Acceso restringido. Esta área es solo para Proveedores.', 'warning')
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function

def cliente_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica si el usuario es un Cliente (para ver su billetera, compras, etc.)
        if session.get('rol') != 'Cliente':
            flash('Por favor, inicia sesión en tu cuenta para realizar esta acción.', 'info')
            # Si no está logueado, lo mandamos directo a la página de login
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function