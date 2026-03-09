# ⚡ CyberStore - E-commerce de Productos Digitales

![CyberStore](https://img.shields.io/badge/CyberStore-V1.0-green)
![Python](https://img.shields.io/badge/Python-3.14-blue)
![Flask](https://img.shields.io/badge/Flask-2.3-red)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)

## 📝 Descripción

**CyberStore** es una plataforma de comercio electrónico diseñada para la venta de productos digitales, específicamente cuentas de streaming (Netflix, Spotify, Disney+, YouTube, etc.) y otros servicios digitales.

### Características Principales

- **Multi-Rol**: Sistema con tres tipos de usuarios:
  - 👑 **Administradores**: Gestión completa de la plataforma
  - 🚚 **Proveedores**: Venta de cuentas y gestión de inventario
  - 🛒 **Clientes/Revendedores**: Compra de productos con billetera virtual

- **Billetera Virtual**: Sistema de saldo integrado para compras instantáneas
- **Catálogo de Productos**: Amplio catálogo con diferentes categorías de servicios
- **Gestión de Inventario**: Control de stock por proveedor
- **Panel de Control**: Dashboards personalizados para cada rol
- **Sistema de Notificaciones**: Alertas en tiempo real para proveedores y clientes

## 🛠️ Tecnologías Utilizadas

| Tecnología | Descripción |
|------------|-------------|
| **Python 3.14** | Lenguaje de programación principal |
| **Flask 2.3** | Framework web ligero y flexible |
| **MySQL** | Base de datos relacional |
| **Bootstrap 5.3** | Framework CSS para diseño responsive |
| **Font Awesome 6.4** | Iconos vectoriales |
| **Jinja2** | Motor de plantillas |

## 📋 Requisitos del Sistema

- Python 3.8 o superior
- MySQL 8.0 o superior
- Navegador web moderno (Chrome, Firefox, Edge)

## 🚀 Instalación

1. **Clonar el repositorio**
   ```bash
   git clone <url-del-repositorio>
   cd CyberStore
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar base de datos**
   - Crear una base de datos MySQL llamada `cyberstore`
   - Actualizar las credenciales en `config.py`

5. **Ejecutar la aplicación**
   ```bash
   python run.py
   ```

6. **Acceder a la aplicación**
   - Abre tu navegador en: `http://127.0.0.1:5000`

## 📁 Estructura del Proyecto

```
CyberStore/
├── app/
│   ├── __init__.py          # Configuración de la aplicación
│   ├── models/              # Modelos de base de datos
│   │   ├── usuarios.py      # Usuarios, Proveedores, Clientes
│   │   ├── productos.py     # Productos e Inventario
│   │   ├── ventas.py       # Ventas y Servicios
│   │   └── notificaciones.py
│   ├── routes/              # Rutas/Controladores
│   │   ├── admin.py        # Panel de administrador
│   │   ├── auth.py         # Autenticación
│   │   ├── cliente.py      # Panel de cliente
│   │   ├── proveedor.py    # Panel de proveedor
│   │   └── public.py       # Rutas públicas
│   ├── static/             # Archivos estáticos
│   │   ├── css/           # Estilos
│   │   ├── js/            # JavaScript
│   │   └── uploads/       # Imágenes subidas
│   └── templates/         # Plantillas HTML
│       ├── admin/        # Plantillas de admin
│       ├── auth/         # Plantillas de auth
│       ├── cliente/      # Plantillas de cliente
│       ├── proveedor/    # Plantillas de proveedor
│       └── legal/       # Páginas legales
├── config.py             # Configuración
├── run.py               # Punto de entrada
├── requirements.txt     # Dependencias
└── README.md           # Este archivo
```

## 👥 Roles de Usuario

### Administrador
- Gestionar usuarios (clientes, proveedores, admins)
- Ver ventas de todos los proveedores
- Reportes y estadísticas
- Configuración del sistema

### Proveedor
- Cargar productos al catálogo
- Gestionar inventario de cuentas
- Ver sus propias ventas
- Configurar precios y disponibilidad

### Cliente/Revendedor
- Explorar catálogo de productos
- Comprar con saldo de billetera
- Ver historial de compras
- Gestionar sus cuentas adquiridas

## 📱 Capturas de Pantalla

*(Añade aquí capturas de pantalla de tu aplicación)*

## 📄 Licencia

Este proyecto es de uso educativo y personal. Todos los derechos reservados.

---

Desarrollado con ❤️ por CyberStore Team

