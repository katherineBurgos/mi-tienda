# Mi Tienda

Aplicación web de gestión de productos, categorías, marcas y clientes creada con Django.

## Requisitos

- Python 3.12
- Django 5.1.15
- Pillow (para las fotos de productos y logos de proveedores)

## Instalación en Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_datos_ejemplo
$env:DJANGO_DEBUG="True"
python manage.py runserver
```

La aplicación queda disponible en <http://127.0.0.1:8000/>. `cargar_datos_ejemplo` crea marcas, categorías, clientes, 2 proveedores con logo, 5 productos con foto, 2 compras y 3 ventas (se puede repetir sin duplicar). Con `DJANGO_DEBUG=True` Django sirve el CSS y las fotos de `media/`; en VS Code, el botón de depurar ya lo trae configurado.

## Estructura (según la guía de Modelos y VBC)

- `facturacion/models.py`: `ModeloBase` abstracto (user, fecha_creacion, fecha_modificacion), `ImageField` en Producto y Proveedor, `TipoPago`, ventas y compras con detalle y métodos de stock.
- `facturacion/mixins.py`: `UsuarioRegistroMixin` y `EliminarProtegidoMixin` (atrapa `ProtectedError`).
- `facturacion/views.py`: todos los CRUD son vistas basadas en clases; solo iniciar sesión, registrarse y cerrar sesión son funciones.
- Compras con formset: el stock sube al comprar y se revierte al editar o eliminar.
- Mi perfil: `UpdateView` sin pk (`get_object`).
- Fondo animado de tulipanes en `templates/base.html` + `static/css/estilos.css`.

Pruebas: `python manage.py test`.

## Configuración

En desarrollo, Django genera una clave secreta aleatoria al iniciar. Para configurar una clave fija, establece `DJANGO_SECRET_KEY` en el entorno. En producción, también configura `DJANGO_DEBUG=False` y los hosts permitidos antes de desplegar.
