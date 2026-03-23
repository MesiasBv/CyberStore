import logging
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
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()
with app.app_context():
    db.create_all()

BOT_TOKEN = Config.BOT_TOKEN
ADMIN_TELEGRAM_ID = Config.ADMIN_TELEGRAM_ID

processed_ids = set()
user_sessions = {}

def start(update, context):
    update.message.reply_text('🤖 CyberStore Bot Avanzado\n\nComandos:\n/login usuario pass\n/ventas_hoy\n/ultimos_clientes\n/stock\n/pendientes\n/stats')

def login(update, context):
    if not context.args or len(context.args) < 2:
        update.message.reply_text('Uso: /login nombre_usuario password')
        return
    nombre_usuario = context.args[0]
    password = ' '.join(context.args[1:])
    with app.app_context():
        cliente = Cliente.query.filter_by(nombre_usuario=nombre_usuario).first()
        if cliente and check_password_hash(cliente.password_hash, password):
            user_sessions[update.effective_user.id] = {'role': 'Cliente', 'id': cliente.id}
            update.message.reply_text(f'✅ Login Cliente {nombre_usuario} OK')
            return
        proveedor = Proveedor.query.filter_by(nombre_usuario=nombre_usuario).first()
        if proveedor and check_password_hash(proveedor.password_hash, password):
            user_sessions[update.effective_user.id] = {'role': 'Proveedor', 'id': proveedor.id}
            update.message.reply_text(f'✅ Login Proveedor {nombre_usuario} OK')
            return
        update.message.reply_text('❌ Credenciales inválidas')

def ventas_hoy(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_TELEGRAM_ID:
        update.message.reply_text('No autorizado')
        return
    with app.app_context():
        hoy = obtener_hora_peru().date()
        ventas = Venta.query.filter(db.func.date(Venta.fecha_venta) == hoy).all()
        text = f'📊 Ventas hoy: {len(ventas)}\n\n'
        for v in ventas[:10]:
            text += f'ID {v.id} {v.codigo_unico}: {v.producto.nombre_producto} S/ {v.precio_final}\n'
        update.message.reply_text(text or 'Sin ventas hoy')

def ultimos_clientes(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_TELEGRAM_ID:
        update.message.reply_text('No autorizado')
        return
    with app.app_context():
        clientes = Cliente.query.order_by(Cliente.fecha_registro.desc()).limit(10).all()
        text = '👥 Últimos clientes:\n'
        for c in clientes:
            text += f'{c.nombre_usuario} - S/ {c.saldo:.2f}\n'
        update.message.reply_text(text)

def stock(update, context):
    session_data = user_sessions.get(update.effective_user.id)
    if not session_data or session_data['role'] != 'Proveedor':
        update.message.reply_text('Login /login primero')
        return
    prov_id = session_data['id']
    with app.app_context():
        productos = Producto.query.filter_by(proveedor_id=prov_id).all()
        text = f'Stock:\n'
        for p in productos:
            text += f'{p.nombre_producto}: {p.stock_disponible()}\n'
        update.message.reply_text(text or 'Sin stock')

def pendientes(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_TELEGRAM_ID:
        update.message.reply_text('No autorizado')
        return
    with app.app_context():
        pendientes = SolicitudRecarga.query.filter_by(estado='Pendiente').all()
        text = f'Pendientes ({len(pendientes)}):\n'
        for sol in pendientes:
            cliente = Cliente.query.get(sol.usuario_id)
            text += f'{cliente.nombre_usuario}: S/ {sol.monto} {sol.nombre_titular_pago}\n'
        update.message.reply_text(text or 'Ninguna')

def stats(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_TELEGRAM_ID:
        update.message.reply_text('No autorizado')
        return
    with app.app_context():
        clientes = Cliente.query.count()
        ventas = Venta.query.count()
        text = f'Estadísticas:\nClientes: {clientes}\nVentas: {ventas}'
        update.message.reply_text(text)

def check_pending(context):
    with app.app_context():
        pendientes = SolicitudRecarga.query.filter_by(estado='Pendiente').all()
        for sol in pendientes:
            if sol.id not in processed_ids:
                keyboard = [[InlineKeyboardButton("✅ APROBAR", callback_data=f"approve_{sol.id}"),
                             InlineKeyboardButton("❌ RECHAZAR", callback_data=f"reject_{sol.id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                cliente = Cliente.query.get(sol.usuario_id)
                text = f"Nueva recarga:\n{cliente.nombre_usuario}\n{sol.nombre_titular_pago}\nS/ {sol.monto}"
                context.bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=text, reply_markup=reply_markup)
                processed_ids.add(sol.id)

def button_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    with app.app_context():
        if data.startswith('approve_'):
            sol_id = int(data.split('_')[1])
            sol = SolicitudRecarga.query.get(sol_id)
            if sol:
                sol.estado = 'Aprobado'
                cliente = Cliente.query.get(sol.usuario_id)
                cliente.saldo += float(sol.monto)
                mov = MovimientoSaldo(cliente_id=sol.usuario_id, tipo='Recarga', monto=sol.monto, saldo_resultante=cliente.saldo, descripcion='Recarga aprobada via Bot')
                db.session.add(mov)
                db.session.commit()
                query.edit_message_text(f'✅ Aprobada ID{sol_id} +S/ {sol.monto} Saldo S/ {cliente.saldo}')
        elif data.startswith('reject_'):
            sol_id = int(data.split('_')[1])
            sol = SolicitudRecarga.query.get(sol_id)
            if sol:
                sol.estado = 'Rechazado'
                db.session.commit()
                query.edit_message_text(f'❌ Rechazada ID{sol_id}')

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("ventas_hoy", ventas_hoy))
    application.add_handler(CommandHandler("ultimos_clientes", ultimos_clientes))
    application.add_handler(CommandHandler("stock", stock))
    application.add_handler(CommandHandler("pendientes", pendientes))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.job_queue.run_repeating(check_pending, interval=30)

    print("🤖 Bot CyberStore FIXED iniciado!")
    application.run_polling()

if __name__ == '__main__':
    main()

