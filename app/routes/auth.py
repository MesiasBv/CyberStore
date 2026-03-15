from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.usuarios import Usuario, Proveedor, Cliente
from app import db, mail
from flask_mail import Message
import random
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Esta sola línea ya hace el trabajo del if/else
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Si la IP es una lista (caso de algunos hostings), limpiamos para quedarnos con la real
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()

    user_agent = request.user_agent.string[:255]
    dispositivo = user_agent.split('(')[0] if '(' in user_agent else user_agent[:255]
        
    if request.method == 'POST':
        identificador = request.form.get('identificador')
        password = request.form.get('password')

        # 1. Buscar al usuario en las 3 tablas
        usuario = Usuario.query.filter((Usuario.correo == identificador) | (Usuario.nombre_usuario == identificador)).first()
        rol_detectado = 'Admin' if usuario else None

        if not usuario:
            usuario = Proveedor.query.filter((Proveedor.correo == identificador) | (Proveedor.nombre_usuario == identificador)).first()
            rol_detectado = 'Proveedor' if usuario else None

        if not usuario:
            usuario = Cliente.query.filter((Cliente.correo == identificador) | (Cliente.nombre_usuario == identificador)).first()
            rol_detectado = 'Cliente' if usuario else None

        # 2. Verificar si el usuario existe y la contraseña es correcta
        if usuario and check_password_hash(usuario.password_hash, password):
            
            # 3. Verificar si el usuario está activo
            if not usuario.estado:
                flash('Tu cuenta ha sido desactivada. Contacta al administrador para más información.', 'danger')
                return redirect(url_for('auth.login'))
            
            # 4. Separar los caminos según el rol
            if rol_detectado in ['Admin', 'Proveedor']:
                # --- RUTA 2FA (ADMINS Y PROVEEDORES) ---
                codigo_otp = str(random.randint(100000, 999999))
                usuario.otp_code = codigo_otp
                usuario.otp_expiration = datetime.utcnow() + timedelta(minutes=10)
                db.session.commit()

                try:
                    msg = Message('Código de Seguridad - CyberStore', recipients=[usuario.correo])
                    msg.body = f'Hola {usuario.nombre_usuario},\n\nTu código de acceso seguro es: {codigo_otp}\n\nEste código expirará en 10 minutos.'
                    mail.send(msg)
                except Exception as e:
                    print(f"🚨 ERROR ENVÍO CORREO: {str(e)}")
                    flash('Error al enviar el correo. Revisa la configuración de tu Gmail.', 'danger')
                    return redirect(url_for('auth.login'))

                session['pending_user_id'] = usuario.id
                session['pending_rol'] = rol_detectado
                flash('Hemos enviado un código de 6 dígitos a tu correo.', 'info')
                return redirect(url_for('auth.verificar_2fa'))

            else:
                # --- RUTA DIRECTA (CLIENTES) ---
                import socket
                import requests
                try:
                    server_name = socket.gethostname()
                except:
                    server_name = 'Unknown'
                
                from app.models.ventas import AuditoriaLog
                
                # Definimos Lima como respaldo INICIAL
                lat, lon = '-12.0464', '-77.0428' 
                
                # Intentamos obtener coordenadas REALES si la IP no es local
                if ip not in ['127.0.0.1', '172.20.10.1', '::1', 'localhost']:
                    try:
                        geo_resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=2)
                        if geo_resp.status_code == 200:
                            geo = geo_resp.json()
                            # Solo si la API devuelve datos válidos, reemplazamos Lima
                            if geo.get('latitude'):
                                lat = str(geo.get('latitude'))
                                lon = str(geo.get('longitude'))
                    except:
                        pass # Si falla la API, se queda con Lima
                
                audit_log = AuditoriaLog(
                    usuario_id=usuario.id,
                    accion='login_exitoso',
                    tabla_afectada='autenticación',
                    detalles=f'Login exitoso rol {rol_detectado}',
                    ip_origen=ip,
                    latitud=lat,
                    longitud=lon,
                    dispositivo=dispositivo + f' | Server: {server_name}'
                )

                db.session.add(audit_log)
                db.session.commit()
                
                session['usuario_id'] = usuario.id
                session['usuario'] = usuario.nombre_completo.upper()
                session['rol'] = rol_detectado
                session.permanent = True
                flash(f'¡Bienvenido a CyberStore, {usuario.nombre_completo}!', 'success')
                return redirect(url_for('public.index'))
                
        else:
            # --- LOG AUDIT FALLO ---
            import socket
            import requests
            try:
                server_name = socket.gethostname()
            except:
                server_name = 'Unknown'
            
            lat, lon = '-12.0464', '-77.0428' # Respaldo inicial
            
            if ip not in ['127.0.0.1', '172.20.10.1', '::1', 'localhost']:
                try:
                    geo_resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=2)
                    if geo_resp.status_code == 200:
                        geo = geo_resp.json()
                        if geo.get('latitude'):
                            lat = str(geo.get('latitude'))
                            lon = str(geo.get('longitude'))
                except:
                    pass
            
            from app.models.ventas import AuditoriaLog
            audit_log = AuditoriaLog(
                accion='login_fallido',
                tabla_afectada='autenticación',
                detalles=f'Intento login fallido identificador: {identificador[:20]}',
                ip_origen=ip,
                latitud=lat,
                longitud=lon,
                dispositivo=dispositivo + f' | Server: {server_name}'
            )

            db.session.add(audit_log)
            db.session.commit()
            
            flash('Credenciales incorrectas. Verifica tu usuario/correo y contraseña.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/verificar-2fa', methods=['GET', 'POST'])
def verificar_2fa():
    ip = request.remote_addr
    user_agent = request.user_agent.string[:255]
    dispositivo = user_agent.split('(')[0] if '(' in user_agent else user_agent[:255]
    
    # Si alguien intenta entrar aquí sin haber pasado por el login primero, lo devolvemos
    if 'pending_user_id' not in session:
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        codigo_ingresado = request.form.get('codigo')
        user_id = session.get('pending_user_id')
        rol = session.get('pending_rol')
        
        # Buscar al usuario según el rol que guardamos temporalmente
        usuario = Usuario.query.get(user_id) if rol == 'Admin' else Proveedor.query.get(user_id)
            
        # Verificar el código
        if usuario and usuario.otp_code == codigo_ingresado:
            # Comprobar si no ha expirado
            if usuario.otp_expiration and usuario.otp_expiration > datetime.utcnow():
                # Verificar si el usuario está activo (para Admin y Proveedor)
                if not usuario.estado:
                    session.clear()
                    flash('Tu cuenta ha sido desactivada. Contacta al administrador para más información.', 'danger')
                    return redirect(url_for('auth.login'))
                
                # ¡Éxito! Limpiamos el código de la base de datos por seguridad
                usuario.otp_code = None
                usuario.otp_expiration = None
                db.session.commit()
                
                # Convertimos la sesión temporal en una sesión real y definitiva
                session.pop('pending_user_id', None)
                session.pop('pending_rol', None)
                session['usuario_id'] = usuario.id
                # Para proveedores usamos el nombre de la empresa, para admin usamos nombre_usuario
                if rol == 'Proveedor':
                    session['usuario'] = usuario.nombre
                elif rol == 'Admin':
                    session['usuario'] = usuario.nombre_usuario
                session['rol'] = rol
                session.permanent = True  # Mantener sesión activa por 30 días
                
                # LOG AUDIT EXITOSO
                try:
                    import socket
                    server_name = socket.gethostname()
                except:
                    server_name = 'Unknown'
                
                import requests
                lat, lon = '', ''
                try:
                    geo_resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=2)
                    if geo_resp.status_code == 200:
                        geo = geo_resp.json()
                        lat = geo.get('latitude', '')
                        lon = geo.get('longitude', '')
                except:
                    pass
                
                from app.models.ventas import AuditoriaLog
                audit_log = AuditoriaLog(
                    usuario_id=usuario.id,
                    accion='login_exitoso',
                    tabla_afectada='autenticación',
                    detalles=f'Login exitoso rol {rol}',
                    ip_origen=ip,
                    dispositivo=dispositivo + f' | Server: {server_name}'
                )
                db.session.add(audit_log)
                db.session.commit()
                
                flash('¡Autenticación exitosa!', 'success')
                # --- NUEVA REDIRECCIÓN INTELIGENTE ---
                if rol == 'Admin':
                    return redirect(url_for('admin.dashboard'))
                elif rol == 'Proveedor':
                    return redirect(url_for('proveedor.dashboard'))
                else:
                    return redirect(url_for('public.index'))
                                
            else:
                flash('El código ha expirado. Por favor, inicia sesión de nuevo.', 'danger')
                return redirect(url_for('auth.login'))
            
        else:
            flash('El código es incorrecto.', 'danger')
            
    return render_template('auth/verificar_2fa.html')

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre_completo = request.form.get('nombre_completo')
        nombre_usuario = request.form.get('nombre_usuario')
        correo = request.form.get('correo')
        telefono = request.form.get('telefono_whatsapp')
        password = request.form.get('password')

        # Verificar si el correo o usuario ya existen para no duplicar
        cliente_existente = Cliente.query.filter((Cliente.correo == correo) | (Cliente.nombre_usuario == nombre_usuario)).first()
        
        if cliente_existente:
            # Determinar cuál campo está duplicado
            duplicado = None
            if cliente_existente.correo == correo and cliente_existente.nombre_usuario == nombre_usuario:
                duplicado = 'ambos'
            elif cliente_existente.correo == correo:
                duplicado = 'correo'
            else:
                duplicado = 'nombre_usuario'
            
            # Eliminar el código de país del teléfono para que no falle la validación
            telefono_sin_codigo = telefono
            if telefono and telefono.startswith('+'):
                # Eliminar el código de país (los primeros caracteres como +51)
                for i in range(1, min(4, len(telefono))):
                    if telefono[i].isdigit():
                        telefono_sin_codigo = telefono[i:]
                        break
            
            # Renderizar el formulario con los datos y el error
            flash('Error: El correo o nombre de usuario ya están en uso.', 'danger')
            return render_template('auth/registro.html', 
                nombre_completo=nombre_completo,
                nombre_usuario=nombre_usuario,
                correo=correo,
                telefono=telefono_sin_codigo,
                duplicado=duplicado
            )

        # Crear al nuevo cliente con su contraseña encriptada
        nuevo_cliente = Cliente(
            nombre_completo=nombre_completo,
            nombre_usuario=nombre_usuario,
            correo=correo,
            telefono_whatsapp=telefono,
            password_hash=generate_password_hash(password)
        )

        db.session.add(nuevo_cliente)
        db.session.commit()
        
        # LOG AUDIT REGISTRO
        ip = request.remote_addr
        user_agent = request.user_agent.string[:255]
        dispositivo = user_agent.split('(')[0] if '(' in user_agent else user_agent[:255]
        
        try:
            import socket
            server_name = socket.gethostname()
        except:
            server_name = 'Unknown'
        
        lat, lon = '', ''
        try:
            geo_resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=2)
            if geo_resp.status_code == 200:
                geo = geo_resp.json()
                lat = geo.get('latitude', '')
                lon = geo.get('longitude', '')
        except:
            pass
        
        from app.models.ventas import AuditoriaLog
        audit_log = AuditoriaLog(
            accion='registro_cliente',
            tabla_afectada='clientes',
            detalles=f'Registro cliente {nuevo_cliente.nombre_completo} id:{nuevo_cliente.id}',
            ip_origen=ip,
            latitud=lat,
            longitud=lon,
            dispositivo=dispositivo + f' | Server: {server_name}'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash('¡Cuenta creada exitosamente! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('public.index'))
