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

processed_ids = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text('No autorizado. Solo admin.')
        return
    await update.message.reply_text('CyberStore Bot listo. Comandos: /ventas_hoy /ultimos_clientes /login nombre_usuario pass')

async def ventas_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text('No autorizado.')
        return
    hoy = obtener_hora_peru().date()
    with app.app_context():
        ventas = Venta.query.filter(db.func.date(Venta.fecha_venta) == hoy).all()
        text = f"Ventas hoy: {len(ventas)}\n"
        for v in ventas[:10]:
            text += f"{v.codigo_unico}: {v.producto.nombre_producto} S/ {v.precio_final}\n"
        await update.message.reply_text(text or 'Sin ventas hoy.')

async def ultimos_clientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text('No autorizado.')
        return
    with app.app_context():
        clientes = Cliente.query.order_by(Cliente.fecha_registro.desc()).limit(10).all()
        text = 'Últimos clientes:\n'
        for c in clientes:
            text += f"{c.nombre_usuario} ({c.nombre_completo}) - S/ {c.saldo}\n"
        await update.message.reply_text(text)

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args or len(context.args) < 2:
        await update.message.reply_text('Uso: /login nombre_usuario password')
        return
    nombre_usuario = context.args[0]
    password = ' '.join(context.args[1:])
    with app.app_context():
        cliente = Cliente.query.filter_by(nombre_usuario=nombre_usuario).first()
        if cliente and check_password_hash(cliente.password_hash, password):
            context.user_data['logged_user'] = ('Cliente', cliente.id)
            await update.message.reply_text(f'Login OK como Cliente {nombre_usuario}. Comandos OK.')
            return
        proveedor = Proveedor.query.filter_by(nombre_usuario=nombre_usuario).first()
        if proveedor and check_password_hash(proveedor.password_hash, password):
            context.user_data['logged_user'] = ('Proveedor', proveedor.id)
            await update.message.reply_text(f'Login OK como Proveedor {nombre_usuario}. Comandos OK.')
            return
    await update.message.reply_text('Credenciales inválidas.')

async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logged = context.user_data.get('logged_user')
    if not logged or logged[0] != 'Proveedor':
        await update.message.reply_text('Login /login nombre pass primero.')
        return
    prov_id = logged[1]
    with app.app_context():
        productos = Producto.query.filter_by(proveedor_id=prov_id).all()
        text = f'Stock ({len(productos)}):\n'
        for p in productos:
            text += f"{p.nombre_producto}: {p.stock_disponible()}\n"
        await update.message.reply_text(text or 'Sin stock.')

async def send_pending_alerts(context: ContextTypes.DEFAULT_TYPE):
    global processed_ids
    with app.app_context():
        pendientes = SolicitudRecarga.query.filter_by(estado='Pendiente').all()
        for sol in pendientes:
            if sol.id not in processed_ids:
                keyboard = [[InlineKeyboardButton("✅ APROBAR", callback_data=f"approve_{sol.id}"),
                             InlineKeyboardButton("❌ RECHAZAR", callback_data=f"reject_{sol.id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                cliente = Cliente.query.get(sol.usuario_id)
                text = f"🔔 Nueva recarga:\n👤 Usuario: {cliente.nombre_usuario}\n💳 Titular: {sol.nombre_titular_pago}\n💰 Monto: S/ {sol.monto}\n⏰ {sol.fecha_solicitud.strftime('%d/%m %H:%M')}"
                context.bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=text, reply_markup=reply_markup)
                processed_ids.add(sol.id)

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
                saldo_anterior = cliente.saldo
                cliente.saldo += sol.monto
                mov = MovimientoSaldo(
                    cliente_id=sol.usuario_id,
                    tipo='Recarga',
                    monto=sol.monto,
                    saldo_resultante=cliente.saldo,
                    descripcion=f'Recargo aprobada via Bot (ID:{sol.id})'
                )
                db.session.add(mov)
                db.session.commit()
                await query.edit_message_text(f'✅ APROBADA ID:{sol_id}\n💰 +S/ {sol.monto}\nNuevo saldo: S/ {cliente.saldo}')
        elif data.startswith('reject_'):
            sol_id = int(data.split('_')[1])
            sol = SolicitudRecarga.query.get(sol_id)
            if sol:
                sol.estado = 'Rechazado'
                db.session.commit()
                await query.edit_message_text(f'❌ RECHAZADA ID:{sol_id}')

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ventas_hoy", ventas_hoy))
    application.add_handler(CommandHandler("ultimos_clientes", ultimos_clientes))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("stock", stock))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Job queue for polling
    application.job_queue.run_repeating(send_pending_alerts, interval=30, first=5)
    
    print("Bot starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
