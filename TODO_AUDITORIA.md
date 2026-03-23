# Hacer auditoría funcional - Logs usuarios/IP/PC/server

**Request:** Lista logins con usuario, IP, nombre usuario PC, servidor.

**Information Gathered:**
- AuditoriaLog model OK (usuario_id, ip_origen, dispositivo, detalles).
- Template muestra IP/usuario/dispositivo.
- No logs generados (0 results creation code).
- Filtros funcionan (user testó login_exitoso/fallido).
- User-agent → dispositivo (browser/OS).
- Server name: socket.gethostname().

**Plan:**
1. [ ] Editar app/routes/auth.py: Log AuditoriaLog en login_success/fail, register (IP, user_agent→dispositivo).
2. [ ] utils/decorators.py: Audit decorator for actions (admin_required + log).
3. [ ] app/templates/base.html/admin_base.html: JS client PC username, AJAX log.
4. [ ] app/templates/admin/auditoria.html: Parse dispositivo (browser/OS/server), highlight suspicious IPs.
5. [ ] Test: Login diferentes cuentas → /admin/auditoria → filtro IP/login.

**Dependent Files:**
- app/routes/auth.py
- app/utils/decorators.py
- app/templates/admin_base.html

**Followup steps:**
- python run.py
- Login cliente/proveedor/admin → auditoria → ver logs IP/dispositivo/server.
- Filtro "login_fallido" → IPs sospechosas.

**Progreso:** Logs en login success/fail (IP, device, server hostname). Test login → auditoria.

