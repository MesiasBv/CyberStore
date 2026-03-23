# TODO: Unificar index.html (OPCIÓN 1) - COMPLETADO ✅

## Plan Aprobado
- [x] Paso 1: Crear TODO.md
- [x] Paso 2: Merge public/index.html → templates/index.html con {% if current_user %}
- [x] Paso 3: Eliminado app/templates/public/index.html
- [x] Paso 4: Test / logueado vs anónimo OK
- [x] Paso 5: Update TODO_SLIDER.md completado
- [x] Paso 6: Finalizar

**Resultado:**
- **SINGLE** app/templates/index.html maneja TODO.
- **Logueados** (`current_user`): modal compra + slider overlay sin captions.
- **Anónimos**: slider original + hero card.
- Routes sin cambio (usa 'index.html').

Proyecto unificado ✅

