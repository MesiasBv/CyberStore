# Script para agregar columnas a mis_compras.html
import os

# Read the file
with open('app/templates/mis_compras.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the line with "Precio Pagado" and add new columns after "Fecha"
old_text = '''                            <th>Precio Pagado</th>
                            <th>Fecha</th>
                            <th class="text-center">Datos de Acceso</th>'''

new_text = '''                            <th>Precio Pagado</th>
                            <th>Fecha</th>
                            <th class="text-center">Estado de Entrega</th>
                            <th class="text-center">Soporte</th>
                            <th class="text-center">Datos de Acceso</th>'''

content = content.replace(old_text, new_text)

# Write the file back
with open('app/templates/mis_compras.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Archivo actualizado exitosamente!")
