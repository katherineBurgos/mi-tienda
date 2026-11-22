# =====================================================================
# python manage.py cargar_datos_ejemplo
# Crea datos de prueba: marcas, categorías, clientes, proveedores con logo, productos con foto,
# 2 compras y 3 ventas (usando los mismos métodos del modelo que usan las vistas).
# Se puede ejecutar varias veces: no duplica lo que ya existe.
# =====================================================================
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from PIL import Image, ImageDraw

from facturacion.models import (
    Categoria, Cliente, Compra, DetalleCompra, DetalleVenta, Marca, Producto, Proveedor, Venta,
)


def imagen_png(texto, color, forma):
    """Dibuja una imagen sencilla (fondo de color + figura + iniciales) y la devuelve como bytes PNG."""
    img = Image.new("RGB", (400, 400), color)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((30, 30, 370, 370), radius=48, outline="white", width=8)
    if forma == "laptop":
        d.rounded_rectangle((90, 110, 310, 250), radius=14, fill="white")
        d.polygon([(60, 270), (340, 270), (310, 300), (90, 300)], fill="white")
    elif forma == "monitor":
        d.rounded_rectangle((70, 90, 330, 250), radius=14, fill="white")
        d.rectangle((185, 250, 215, 290), fill="white")
        d.rectangle((140, 290, 260, 305), fill="white")
    elif forma == "teclado":
        d.rounded_rectangle((60, 150, 340, 260), radius=14, fill="white")
        for fila in range(3):
            for col in range(8):
                d.rectangle((78 + col * 33, 168 + fila * 28, 98 + col * 33, 182 + fila * 28), fill=color)
    elif forma == "audio":
        d.arc((95, 80, 305, 290), 180, 360, fill="white", width=18)
        d.rounded_rectangle((80, 170, 125, 270), radius=14, fill="white")
        d.rounded_rectangle((275, 170, 320, 270), radius=14, fill="white")
    else:  # logo: círculo con iniciales
        d.ellipse((110, 90, 290, 270), fill="white")
    d.text((200, 335), texto, fill="white", anchor="mm")
    salida = BytesIO()
    img.save(salida, "PNG")
    return salida.getvalue()


class Command(BaseCommand):
    help = "Carga datos de ejemplo (con fotos y logos)."

    @transaction.atomic
    def handle(self, *args, **options):
        usuario = User.objects.order_by("pk").first()          # quien "registró" los datos (si ya existe alguien)

        categorias = {}
        for nombre in ("Computadoras", "Accesorios", "Audio", "Ofertas"):
            categorias[nombre], _ = Categoria.objects.get_or_create(
                nombre=nombre, defaults={"descripcion": f"Productos de la categoría {nombre}.", "user": usuario})

        marcas = {}
        for nombre, pais in (("Acer", "Taiwán"), ("Asus", "Taiwán"), ("Dell", "Estados Unidos"),
                             ("Samsung", "Corea del Sur"), ("Sony", "Japón")):
            marcas[nombre], _ = Marca.objects.get_or_create(nombre=nombre, defaults={"pais_origen": pais, "user": usuario})

        for cedula, nombres, apellidos in (
            ("0100000001", "Ana", "Pérez"), ("0100000002", "Luis", "Gómez"), ("0100000003", "María", "Torres"),
            ("0100000004", "Carlos", "Vega"), ("0100000005", "Sofía", "Molina"),
        ):
            Cliente.objects.get_or_create(cedula=cedula, defaults={
                "nombres": nombres, "apellidos": apellidos, "user": usuario,
                "email": f"{nombres.lower().replace('í', 'i')}@ejemplo.ec", "telefono": "0990000000",
                "direccion": "Quito, Ecuador"})

        proveedores = []
        for nombre, apellido, ruc, color in (
            ("Distribuidora", "Andina", "1790000000001", "#7251a3"),
            ("Importadora", "Pacífico", "0990000000001", "#2f7f79"),
        ):
            prov, creado = Proveedor.objects.get_or_create(ruc=ruc, defaults={
                "nombre": nombre, "apellido": apellido, "email": f"{nombre.lower()}@ejemplo.ec",
                "contacto": "022000000", "user": usuario})
            if creado or not prov.logo:
                prov.logo.save(f"logo_{slugify(nombre)}.png",
                               ContentFile(imagen_png((nombre[0] + apellido[0]).upper(), color, "logo")), save=True)
            proveedores.append(prov)

        productos = {}
        for nombre, desc, precio, marca, cats, forma, color in (
            ("Laptop Aspire 5", "Portátil para trabajo y estudio.", "649.99", "Acer", ("Computadoras", "Ofertas"), "laptop", "#7251a3"),
            ("Monitor ProArt", "Monitor de alta resolución.", "329.00", "Asus", ("Computadoras",), "monitor", "#2f7f79"),
            ("Teclado inalámbrico", "Teclado compacto para oficina.", "39.90", "Dell", ("Accesorios",), "teclado", "#c0558f"),
            ("Galaxy Buds", "Audífonos inalámbricos.", "89.99", "Samsung", ("Audio", "Ofertas"), "audio", "#d08a2e"),
            ("Audífonos WH-CH520", "Audífonos Bluetooth con micrófono.", "59.99", "Sony", ("Audio",), "audio", "#4a6fb5"),
        ):
            prod, creado = Producto.objects.get_or_create(nombre=nombre, defaults={
                "descripcion": desc, "precio": precio, "stock": 0, "marca": marcas[marca], "user": usuario})
            if creado:
                prod.categorias.add(*(categorias[c] for c in cats))
            if not prod.imagen:
                prod.imagen.save(f"{slugify(nombre)}.png",
                                 ContentFile(imagen_png(nombre, color, forma)), save=True)
            productos[nombre] = prod

        if Compra.objects.exists() or Venta.objects.exists():
            self.stdout.write("Ya hay compras o ventas: no se crean más.")
            return

        # ---------- 2 COMPRAS: el stock SUBE ----------
        for proveedor, pago, lineas in (
            (proveedores[0], "credito", (("Laptop Aspire 5", 10, "520.00"), ("Monitor ProArt", 8, "260.00"), ("Teclado inalámbrico", 20, "28.00"))),
            (proveedores[1], "transferencia", (("Galaxy Buds", 15, "70.00"), ("Audífonos WH-CH520", 12, "44.00"))),
        ):
            compra = Compra.objects.create(proveedor=proveedor, tipo_pago=pago, user=usuario)
            for nombre, cantidad, costo in lineas:
                DetalleCompra.objects.create(compra=compra, producto=productos[nombre], cantidad=cantidad, precio=costo, user=usuario)
            compra.ingresar_stock()
            compra.calcular_totales()

        # ---------- 3 VENTAS: el stock BAJA ----------
        clientes = list(Cliente.objects.order_by("cedula")[:3])
        for cliente, pago, lineas in (
            (clientes[0], "contado", (("Laptop Aspire 5", 1), ("Teclado inalámbrico", 2))),
            (clientes[1], "tarjeta", (("Galaxy Buds", 2),)),
            (clientes[2], "transferencia", (("Monitor ProArt", 1), ("Audífonos WH-CH520", 1))),
        ):
            venta = Venta.objects.create(cliente=cliente, tipo_pago=pago, user=usuario)
            for nombre, cantidad in lineas:
                p = productos[nombre]
                DetalleVenta.objects.create(venta=venta, producto=p, cantidad=cantidad, precio=p.precio, user=usuario)
            venta.descontar_stock()
            venta.calcular_totales()

        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados."))
