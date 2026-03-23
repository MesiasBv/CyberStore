# Fix error sugerencias admin - Null fecha.strftime

**Nuevo issue detectado post-task anterior.**

## Pasos:
1. [ ] Agregar TODO_SUGERENCIAS.md.
2. [ ] Editar app/templates/admin/sugerencias.html: Null-safe fecha (if sug.fecha else 'Sin fecha').
3. [ ] Opcional: admin.py - Filtrar/coalesce None fechas.
4. [ ] Test: Enviar sugerencia anónima → /admin/sugerencias sin crash.
5. [ ] Marcar completado.

**Progreso:** Fix template completado. Listo para test.

