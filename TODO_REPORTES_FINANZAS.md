# Hacer funcional reportes/finanzas admin

**Nuevo request usuario:** Funcionalidad completa para reportes y finanzas admin (ventas proveedores, pagos, auditoría).

**Información Gathered:**
- Templates existentes: admin/ventas_proveedores.html (completo, functional per logs), admin/auditoria.html (vacío).
- admin.py tiene /ventas-proveedores (completo: filtros fechas/proveedor, stats, tabla transacciones).
- Sidebar admin_base.html tiene "Reportes y Finanzas" sin link.
- Logs muestran /admin/ventas-proveedores 200 OK.

**Plan:**
1. [ ] Crear TODO_REPORTES_FINANZAS.md.
2. [ ] Implementar route/template app/routes/admin.py y app/templates/admin/auditoria.html (logs, movimientos saldo agregados, export CSV).
3. [ ] Agregar link sidebar admin_base.html a auditoría.
4. [ ] Test: /admin/auditoria y /admin/ventas-proveedores como admin.
5. [ ] Completar.

**Progreso:** Auditoría completada + ventas-proveedores mejorada + sidebar links. ¡Listo!
