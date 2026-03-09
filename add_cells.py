# Script para agregar celdas de datos a mis_compras.html
import os

# Read the file
with open('app/templates/mis_compras.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the line with fecha_venta and add new td cells after it
old_text = '''                            <td class="text-secondary small">{{ c.fecha_venta.strftime('%d/%m/%Y %H:%M') }}</td>
                            <td class="text-center">'''

new_text = '''                            <td class="text-secondary small">{{ c.fecha_venta.strftime('%d/%m/%Y %H:%M') }}</td>
                            <td class="text-center">
                                {% if c.estado_entrega == 'Pendiente' %}
                                <span class="badge bg-warning text-dark">Pendiente</span>
                                {% elif c.estado_entrega == 'Entregado' %}
                                <span class="badge bg-success">Entregado</span>
                                {% else %}
                                <span class="badge bg-secondary">{{ c.estado_entrega }}</span>
                                {% endif %}
                            </td>
                            <td class="text-center">
                                {% if c.proveedor and c.proveedor.telefono_contacto %}
                                <a href="https://wa.me/51{{ c.proveedor.telefono_contacto }}?text=Hola,%20tengo%20una%20consulta%20sobre%20mi%20compra%20{{ c.codigo_unico }}" 
                                   target="_blank" class="btn btn-outline-success btn-sm" title="Contactar por WhatsApp">
                                    <i class="fa-brands fa-whatsapp"></i>
                                </a>
                                {% else %}
                                <span class="text-secondary">-</span>
                                {% endif %}
                            </td>
                            <td class="text-center">'''

content = content.replace(old_text, new_text)

# Write the file back
with open('app/templates/mis_compras.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Archivo actualizado exitosamente!")
