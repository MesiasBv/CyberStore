# TODO: Módulo de Recarga Automatizada - Progreso

## Pasos Completados
- [x] 1. Actualizar requirements.txt (agregar deps)
- [x] 2. Actualizar config.py (nuevas vars env)
- [x] 3. Actualizar utils/hora_peru.py (pytz)
- [x] 4. Editar app/models/usuarios.py (agregar telegram_id)
- [x] 5. Crear app/models/solicitudes_recarga.py (nuevo model)
- [x] 6. Editar app/models/ventas.py (agregar FK a MovimientoSaldo)
- [x] 7. Editar app/__init__.py (import new model)
- [ ] 6. Editar app/models/ventas.py (agregar FK a MovimientoSaldo)
- [ ] 7. Editar app/__init__.py (import new model)
- [x] 8. Editar app/routes/public.py (nueva ruta /solicitar-recarga)
- [x] 9. Editar app/templates/mi_billetera.html (formulario nuevo)
- [x] 10. Crear app/bot.py (Telegram bot completo)
- [ ] 11. pip install deps + python -c "from app import create_app; create_app().app_context().invoke(db.create_all)" (DB)
- [x] 12. Agregar BOT_TOKEN, ADMIN_TELEGRAM_ID a .env
- [ ] 13. Test completo

**Bot creado. Agrega BOT_TOKEN = 'tu_token' y ADMIN_TELEGRAM_ID = 123456789 a .env. Ejecuta `python app/bot.py` en terminal separado. Próximo: ruta + template.**

*Actualizado por BLACKBOXAI*

