import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sys
sys.path.insert(0, '.')
from config import Config
from app import db
from app.models.solicitudes_recarga import SolicitudRecarga
from app.models.usuarios import Cliente, Usuario, Proveedor
from app.utils.hora_peru import obtener_hora_peru
from app import create_app
from werkzeug.security import check_password_hash
from app.models.ventas import Venta, MovimientoSaldo
from app.models.productos import Producto
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()
with app.app_context():
    db.create_all()

BOT_TOKEN = Config.BOT_TOKEN
ADMIN_TELEGRAM_ID = Config.ADMIN_TELEGRAM_ID

# Global session data
user_sessions = {}

# --- REEMPLAZA ESTAS FUNCIONES EN TU ARCHIVO ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **CyberStore Bot Avanzado**\n\n"
        "Este es un bot de gestión privada.\n"
        "Usa `/login usuario password` para acceder."
    )

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text('❌ Uso: /login usuario password')
        return

    nombre_usuario = context.args[0]
    password = ' '.join(context.args[1:])
    user_id_telegram = update.effective_user.id

    with app.app_context():
        # 1. INTENTO COMO ADMIN (Tabla Usuario)
        usuario = Usuario.query.filter_by(nombre_usuario=nombre_usuario).first()
        if usuario and check_password_hash(usuario.password_hash, password):
            # EL CAMBIO CLAVE: Convertimos ambos a texto (str) para evitar confusiones de Python
            if str(user_id_telegram) == str(ADMIN_TELEGRAM_ID):
                user_sessions[user_id_telegram] = {'role': 'Admin', 'id': usuario.id}
                menu_admin = (
                    "👑 **ACCESO TOTAL: ADMINISTRADOR**\n\n"
                    "Comandos habilitados:\n"
                    "/ventas_hoy - Reporte diario\n"
                    "/pendientes - Gestionar recargas\n"
                    "/stats - Estadísticas generales\n"
                    "/ultimos_clientes - Ver registros\n"
                    "/logout - Cerrar sesión"
                )
                await update.message.reply_text(menu_admin) # (Asegúrate de no usar parse_mode='Markdown' si hay símbolos raros)
            else:
                await update.message.reply_text("🚫 Credenciales válidas, pero tu cuenta de Telegram no está autorizada como Admin.")
            return

        # 2. INTENTO COMO PROVEEDOR
        proveedor = Proveedor.query.filter_by(nombre_usuario=nombre_usuario).first()
        if proveedor and check_password_hash(proveedor.password_hash, password):
            user_sessions[user_id_telegram] = {'role': 'Proveedor', 'id': proveedor.id}
            
            # Usamos un texto simple sin tantos símbolos raros para evitar el error de parseo
            menu_prov = (
                f"✅ ACCESO PROVEEDOR: {nombre_usuario}\n\n"
                "Comandos habilitados:\n"
                "/stock - Ver mis productos y stock\n"
                "/ventas_hoy - Mis ventas del día\n"
                "/logout - Cerrar sesión"
            )
            # Quitamos el parse_mode='Markdown' temporalmente para asegurar que funcione
            await update.message.reply_text(menu_prov) 
            return

        # 3. RECHAZO A CLIENTES O CREDENCIALES FALSAS
        await update.message.reply_text("❌ **ACCESO DENEGADO**: No tienes permisos para usar esta herramienta.")

# --- MODIFICA TAMBIÉN TUS HANDLERS EN MAIN ---
async def ventas_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Validación de sesión
    session_data = user_sessions.get(update.effective_user.id)
    if not session_data or session_data.get('role') != 'Admin':
        await update.message.reply_text('🚫 No autorizado. Inicia sesión como Admin.')
        return

    # 2. Intento de ejecución segura
    try:
        with app.app_context():
            hoy = obtener_hora_peru().date()
            # Buscamos las ventas
            ventas = Venta.query.filter(db.func.date(Venta.fecha_venta) == hoy).all()
            
            text = f'📊 Ventas de hoy: {len(ventas)}\n\n'
            for v in ventas[:10]:
                text += f'ID {v.id}: {v.producto.nombre_producto} - S/ {v.precio_final}\n'
            
            await update.message.reply_text(text)
            
    except Exception as e:
        # Si algo falla, el bot te mandará el error directamente a tu celular
        error_msg = f"⚠️ Fallo en el código de ventas_hoy:\n{str(e)}"
        await update.message.reply_text(error_msg)
        print(error_msg) # También lo imprime en la terminal

async def ultimos_clientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sesion_data = user_sessions.get(update.effective_user.id)
    if not sesion_data or sesion_data.get('role') != 'Admin':
        await update.message.reply_text('🚫 No autorizado. Inicia sesión como Admin.')
        return
    with app.app_context():
        clientes = Cliente.query.order_by(Cliente.fecha_registro.desc()).limit(10).all()
        text = '👥 Últimos clientes:\n\n'
        for c in clientes:
            text += f'{c.nombre_usuario} - {c.nombre_completo}\nSaldo: S/ {c.saldo:.2f}\nTel: {c.telefono_whatsapp}\n\n'
        await update.message.reply_text(text)

async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_sessions.get(update.effective_user.id)
    session_data = user_sessions.get(update.effective_user.id)
    if not session_data or session_data['role'] != 'Proveedor':
        await update.message.reply_text('Login como proveedor /login nombre pass')
        return
    prov_id = session_data['id']
    with app.app_context():
        productos = Producto.query.filter_by(proveedor_id=prov_id).all()
        text = f'📦 Tu Stock ({len(productos)}):\n\n'
        for p in productos:
            stock = p.stock_disponible()
            text += f'{p.nombre_producto}\nPrecio: S/ {p.precio}\nStock: {stock}\n\n'
        await update.message.reply_text(text or 'Sin productos')

async def pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sesion_data = user_sessions.get(update.effective_user.id)
    if not sesion_data or sesion_data.get('role') != 'Admin':
        await update.message.reply_text('🚫 No autorizado. Inicia sesión como Admin.')
        return
    with app.app_context():
        pendientes = SolicitudRecarga.query.filter_by(estado='Pendiente').order_by(SolicitudRecarga.fecha_solicitud.desc()).all()
        text = f'⏳ Recargas Pendientes ({len(pendientes)}):\n\n'
        for sol in pendientes:
            cliente = Cliente.query.get(sol.usuario_id)
            text += f'ID {sol.id}\n{cliente.nombre_usuario}: S/ {sol.monto} - {sol.nombre_titular_pago}\n{sol.fecha_solicitud.strftime("%d/%m %H:%M")}\n\n'
        await update.message.reply_text(text or 'Ninguna pendiente')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sesion_data = user_sessions.get(update.effective_user.id)
    if not sesion_data or sesion_data.get('role') != 'Admin':
        await update.message.reply_text('🚫 No autorizado. Inicia sesión como Admin.')
        return
    with app.app_context():
        total_clientes = Cliente.query.count()
        total_proveedores = Proveedor.query.count()
        ventas_total = Venta.query.count()
        saldo_total = db.session.query(db.func.sum(Cliente.saldo)).scalar() or 0
        text = f'📈 Estadísticas CyberStore:\n\n👥 Clientes: {total_clientes}\n🏪 Proveedores: {total_proveedores}\n🛒 Ventas: {ventas_total}\n💰 Saldo Total Clientes: S/ {saldo_total:.2f}'
        await update.message.reply_text(text)

async def send_alerts(context: ContextTypes.DEFAULT_TYPE):
    global processed_ids
    with app.app_context():
        pendientes = SolicitudRecarga.query.filter_by(estado='Pendiente').all()
        for sol in pendientes:
            if sol.id not in processed_ids:
                keyboard = [[
                    InlineKeyboardButton("✅ APROBAR", callback_data=f"approve_{sol.id}"),
                    InlineKeyboardButton("❌ RECHAZAR", callback_data=f"reject_{sol.id}")
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                cliente = Cliente.query.get(sol.usuario_id)
                
                # TEXTO LIMPIO: Sin asteriscos de Markdown para que no se rompa con datos del usuario
                text = (
                    f"🔔 NUEVA RECARGA PENDIENTE\n\n"
                    f"👤 Cliente: {cliente.nombre_usuario}\n"
                    f"💳 Titular: {sol.nombre_titular_pago}\n"
                    f"💰 Monto: S/ {sol.monto:.2f}\n"
                    f"⏰ Fecha: {sol.fecha_solicitud.strftime('%d/%m/%Y %H:%M')}"
                )
                
                try:
                    # int() asegura que el ID sea leído como número y no como texto
                    await context.bot.send_message(
                        chat_id=int(ADMIN_TELEGRAM_ID), 
                        text=text, 
                        reply_markup=reply_markup
                    )
                    processed_ids.add(sol.id) # Lo marcamos como enviado
                except Exception as e:
                    print(f"⚠️ Error enviando alerta automática (ID {sol.id}): {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    with app.app_context():
        if data.startswith('approve_'):
            sol_id = int(data.split('_')[1])
            sol = SolicitudRecarga.query.get(sol_id)
            if sol:
                sol.estado = 'Aprobado'
                cliente = Cliente.query.get(sol.usuario_id)
                cliente.saldo += sol.monto
                mov = MovimientoSaldo(
                    cliente_id=sol.usuario_id,
                    tipo='Recarga',
                    monto=sol.monto,
                    saldo_resultante=cliente.saldo,
                    descripcion=f'Recargo aprobada (titular: {sol.nombre_titular_pago})'
                )
                db.session.add(mov)
                db.session.commit()
                await query.edit_message_text(f'✅ *Recarga Aprobada* ID: {sol_id}\n💰 +S/ {sol.monto:.2f}\nNuevo saldo cliente: S/ {cliente.saldo:.2f}', parse_mode='Markdown')
        elif data.startswith('reject_'):
            sol_id = int(data.split('_')[1])
            sol = SolicitudRecarga.query.get(sol_id)
            if sol:
                sol.estado = 'Rechazado'
                
                # ¡EL CAMBIO CLAVE! Buscamos al cliente antes de registrar el movimiento
                cliente = Cliente.query.get(sol.usuario_id)
                
                mov = MovimientoSaldo(
                    cliente_id=sol.usuario_id,
                    tipo='Recarga Rechazada', # Actualizamos el tipo para más claridad
                    monto=0, # Como es rechazada, el movimiento real de dinero es 0
                    saldo_resultante=cliente.saldo, # Ahora sí conoce el saldo actual
                    descripcion=f'Recarga rechazada (titular: {sol.nombre_titular_pago})'
                )
                db.session.add(mov)
                db.session.commit()
                
                # Actualizamos el mensaje en Telegram para que sepas a quién le rechazaste
                await query.edit_message_text(f'❌ *Recarga Rechazada* ID: {sol_id}\nEl saldo de {cliente.nombre_usuario} se mantiene en S/ {cliente.saldo:.2f}', parse_mode='Markdown')
                
                # Quitamos el ID de los procesados por si acaso
                processed_ids.discard(sol.id)

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("🔒 Sesión cerrada con éxito. El bot vuelve a estar bloqueado.")
    else:
        await update.message.reply_text("ℹ️ No tenías ninguna sesión activa.")    
# Agrega esta línea justo antes de la función main si no la tienes
processed_ids = set()

async def main():
    # 1. Construimos la aplicación
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 2. Registramos los comandos (Handlers)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("ventas_hoy", ventas_hoy))
    application.add_handler(CommandHandler("ultimos_clientes", ultimos_clientes))
    application.add_handler(CommandHandler("stock", stock))
    application.add_handler(CommandHandler("pendientes", pendientes))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # 3. Configuramos las alertas repetitivas (Job Queue)
    if application.job_queue:
        application.job_queue.run_repeating(send_alerts, interval=30, first=5)
    
    # 4. EXTREMADAMENTE IMPORTANTE PARA PYTHON 3.14:
    # Usamos el contexto asíncrono para que no haya pelea de loops
    async with application:
        await application.initialize()
        await application.start() # <-- Cambiamos start_polling por start
        
        # Iniciamos el updater para que empiece a recibir mensajes
        await application.updater.start_polling() 
        
        print("🤖 Bot Avanzado CyberStore iniciado y escuchando...")
        
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            print("\n🛑 Apagando el bot...")
            await application.updater.stop()
            await application.stop()

if __name__ == '__main__':
    # Usamos try/except para capturar el cierre manual sin errores rojos
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass