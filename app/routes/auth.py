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
    # 1. Obtener IP y limpiar (funciona para Local y cPanel)
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()

    # 2. Nueva lógica de detección de dispositivo (S.O. | Navegador)
    platform = request.user_agent.platform or "PC"
    browser = request.user_agent.browser or "Navegador"
    
    if 'windows' in platform.lower():
        os_name = "Windows"
    elif 'android' in platform.lower():
        os_name = "Android 📱"
    elif 'iphone' in platform.lower() or 'ipad' in platform.lower():
        os_name = "iOS 🍎"
    else:
        os_name = platform.capitalize()

    dispositivo_final = f"{os_name} | {browser.capitalize()}"

    if request.method == 'POST':
        identificador = request.form.get('identificador')
        password = request.form.get('password')

        # 3. Buscar al usuario en las 3 tablas
        usuario = Usuario.query.filter((Usuario.correo == identificador) | (Usuario.nombre_usuario == identificador)).first()
        rol_detectado = 'Admin' if usuario else None

        if not usuario:
            usuario = Proveedor.query.filter((Proveedor.correo == identificador) | (Proveedor.nombre_usuario == identificador)).first()
            rol_detectado = 'Proveedor' if usuario else None

        if not usuario:
            usuario = Cliente.query.filter((Cliente.correo == identificador) | (Cliente.nombre_usuario == identificador)).first()
            rol_detectado = 'Cliente' if usuario else None

        # 4. Verificar credenciales
        if usuario and check_password_hash(usuario.password_hash, password):
            if not usuario.estado:
                flash('Tu cuenta ha sido desactivada. Contacta al administrador.', 'danger')
                return redirect(url_for('auth.login'))
            
            # --- CASO ADMIN / PROVEEDOR (CON 2FA) ---
            if rol_detectado in ['Admin', 'Proveedor']:
                codigo_otp = str(random.randint(100000, 999999))
                usuario.otp_code = codigo_otp
                usuario.otp_expiration = datetime.utcnow() + timedelta(minutes=10)
                db.session.commit()

                try:
                    msg = Message('Código de Seguridad - CyberStore', 
                                  sender=os.environ.get('MAIL_USERNAME'), # Crucial para cPanel
                                  recipients=[usuario.correo])
                    msg.body = f'Hola {usuario.nombre_usuario},\n\nTu código de acceso seguro es: {codigo_otp}\n\nEste código expirará en 10 minutos.'
                    mail.send(msg)
                except Exception as e:
                    print(f"🚨 ERROR ENVÍO CORREO: {str(e)}")
                    flash('Error al enviar el correo de seguridad.', 'danger')
                    return redirect(url_for('auth.login'))

                session['pending_user_id'] = usuario.id
                session['pending_rol'] = rol_detectado
                flash('Hemos enviado un código de 6 dígitos a tu correo.', 'info')
                return redirect(url_for('auth.verificar_2fa'))

            # --- CASO CLIENTE (SIN 2FA - ACCESO DIRECTO) ---
            else:
                import requests
                from app.models.ventas import AuditoriaLog
                
                # Ubicación por defecto (Lima)
                lat, lon = '-12.0464', '-77.0428' 
                if ip not in ['127.0.0.1', '::1', 'localhost']:
                    try:
                        geo_resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=2)
                        if geo_resp.status_code == 200:
                            geo = geo_resp.json()
                            lat = str(geo.get('latitude', lat))
                            lon = str(geo.get('longitude', lon))
                    except:
                        pass # Si falla la API, usa los valores por defecto

                # Registrar Auditoría de éxito para Cliente
                audit_log = AuditoriaLog(
                    usuario_id=usuario.id,
                    accion='login_exitoso',
                    tabla_afectada='autenticación',
                    detalles=f'Login exitoso rol {rol_detectado}',
                    ip_origen=ip,
                    latitud=lat,
                    longitud=lon,
                    dispositivo=dispositivo_final
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
            # --- LOG AUDIT FALLO (Usuario no existe o pass incorrecta) ---
            from app.models.ventas import AuditoriaLog
            import requests
            
            # Ubicación básica para el fallo
            lat, lon = '-12.0464', '-77.0428'
            
            audit_log = AuditoriaLog(
                usuario_id=None, # IMPORTANTE: Permitir NULL en DB
                accion='login_fallido',
                tabla_afectada='autenticación',
                detalles=f'Intento fallido: {identificador[:20]}',
                ip_origen=ip,
                latitud=lat,
                longitud=lon,
                dispositivo=dispositivo_final
            )
            db.session.add(audit_log)
            db.session.commit()
            
            flash('Credenciales incorrectas. Verifica tu usuario/correo y contraseña.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/verificar-2fa', methods=['GET', 'POST'])
def verificar_2fa():
    # 1. Obtener IP y Dispositivo con la nueva lógica
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()

    platform = request.user_agent.platform or "PC"
    browser = request.user_agent.browser or "Navegador"
    
    if 'windows' in platform.lower():
        os_name = "Windows"
    elif 'android' in platform.lower():
        os_name = "Android 📱"
    elif 'iphone' in platform.lower() or 'ipad' in platform.lower():
        os_name = "iOS 🍎"
    else:
        os_name = platform.capitalize()

    dispositivo_final = f"{os_name} | {browser.capitalize()}"

    # Seguridad: Si no hay usuario pendiente, al login
    if 'pending_user_id' not in session:
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        codigo_ingresado = request.form.get('codigo')
        user_id = session.get('pending_user_id')
        rol = session.get('pending_rol')
        
        # Buscar al usuario según el rol
        usuario = Usuario.query.get(user_id) if rol == 'Admin' else Proveedor.query.get(user_id)
            
        if usuario and usuario.otp_code == codigo_ingresado:
            # Comprobar expiración
            if usuario.otp_expiration and usuario.otp_expiration > datetime.utcnow():
                
                # --- AQUÍ ESTÁ LA SEGURIDAD QUE FALTABA ---
                if not usuario.estado:
                    session.clear()
                    flash('Tu cuenta ha sido desactivada. Contacta al administrador.', 'danger')
                    return redirect(url_for('auth.login'))
                
                # ¡Éxito! Limpiamos OTP
                usuario.otp_code = None
                usuario.otp_expiration = None
                db.session.commit()
                
                # Sesión definitiva
                session.pop('pending_user_id', None)
                session.pop('pending_rol', None)
                session['usuario_id'] = usuario.id
                session['usuario'] = usuario.nombre_usuario if rol == 'Admin' else usuario.nombre
                session['rol'] = rol
                session.permanent = True
                
                # LOG AUDIT (Con geolocalización)
                import requests
                from app.models.ventas import AuditoriaLog
                lat, lon = '-12.0464', '-77.0428' # Por defecto Lima
                try:
                    geo_resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=2)
                    if geo_resp.status_code == 200:
                        geo = geo_resp.json()
                        lat = str(geo.get('latitude', lat))
                        lon = str(geo.get('longitude', lon))
                except:
                    pass

                audit_log = AuditoriaLog(
                    usuario_id=usuario.id,
                    accion='login_exitoso',
                    tabla_afectada='autenticación',
                    detalles=f'Login exitoso 2FA rol {rol}',
                    ip_origen=ip,
                    latitud=lat,
                    longitud=lon,
                    dispositivo=dispositivo_final
                )
                db.session.add(audit_log)
                db.session.commit()
                
                flash('¡Autenticación exitosa!', 'success')
                
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
