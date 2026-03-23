import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sys
sys.path.insert(0, '.')
from config import Config
from app import db
from app.models.solicitudes_recarga import SolicitudRecarga
from app.models.usuarios import Cliente
from app.utils.hora_peru import obtener_hora_peru
from app import create_app
from werkzeug.security import check_password_hash
from app.models.ventas import Venta, MovimientoSaldo
from app.models.productos import Producto

logging.basicConfig(level=logging.INFO)

app = create_app()
with app.app_context():
    db.create_all()

BOT_TOKEN = Config.BOT_TOKEN
ADMIN_TELEGRAM_ID = Config.ADMIN_TELEGRAM_ID

processed = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('CyberStore Bot. /test')

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Test", callback_data="test")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Test bot:', reply_markup=reply_markup)

async def check_pending(context: ContextTypes.DEFAULT_TYPE):
    global processed
    with app.app_context():
        pendientes = SolicitudRecarga.query.filter_by(estado='Pendiente').all()
        for sol in pendientes:
            if sol.id not in processed:
                keyboard = [[InlineKeyboardButton("✅ APROBAR", callback_data=f"approve_{sol.id}"),
                             InlineKeyboardButton("❌ RECHAZAR", callback_data=f"reject_{sol.id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                cliente = Cliente.query.get(sol.usuario_id)
                text = f"🔔 Nueva recarga ID:{sol.id}\n👤 {cliente.nombre_usuario}\n💳 {sol.nombre_titular_pago}\n💰 S/ {sol.monto}"
                await context.bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=text, reply_markup=reply_markup)
                processed.add(sol.id)

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                mov = MovimientoSaldo(cliente_id=sol.usuario_id, tipo='Recarga', monto=sol.monto, saldo_resultante=cliente.saldo, descripcion='Bot approve')
                db.session.add(mov)
                db.session.commit()
                await query.edit_message_text(f'✅ APROBADA {sol_id} +S/ {sol.monto} Saldo S/ {cliente.saldo}')
        elif data.startswith('reject_'):
            sol_id = int(data.split('_')[1])
            sol = SolicitudRecarga.query.get(sol_id)
            if sol:
                sol.estado = 'Rechazado'
                db.session.commit()
                await query.edit_message_text(f'❌ RECHAZADA {sol_id}')

async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test))
    application.add_handler(CallbackQueryHandler(callback))
    application.job_queue.run_repeating(check_pending, interval=30)
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    # Keep running
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())

