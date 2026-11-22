import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import (
    Categoria, Cliente, Compra, DetalleCompra, DetalleVenta, Marca, Perfil, Producto, Proveedor, Venta,
)

MEDIA_TEMPORAL = tempfile.mkdtemp()      # las fotos de las pruebas no ensucian tu carpeta media/


def foto(nombre="foto.png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "purple").save(buffer, "PNG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class TiendaTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="prueba", password="ClaveSegura123")
        cls.marca = Marca.objects.create(nombre="Marca Prueba")
        cls.categoria = Categoria.objects.create(nombre="Tecnología")
        cls.producto = Producto.objects.create(nombre="Producto de prueba", precio="25.00", stock=10, marca=cls.marca)
        cls.cliente = Cliente.objects.create(cedula="0102030405", nombres="Ana", apellidos="Pérez")
        cls.proveedor = Proveedor.objects.create(nombre="Carlos", apellido="Andrade", ruc="1790000000001")

    def setUp(self):
        self.client.force_login(self.user)

    # ---------- generales ----------
    def test_inicio_muestra_numeros_y_productos(self):
        respuesta = self.client.get(reverse("home"))
        self.assertContains(respuesta, "Productos activos")
        self.assertContains(respuesta, "fondo-tulipanes")

    def test_todas_las_vistas_exigen_sesion(self):
        self.client.logout()
        for nombre in ("marca_lista", "producto_lista", "venta_lista", "compra_lista", "cliente_lista",
                       "proveedor_lista", "categoria_lista", "mi_perfil"):
            url = reverse(f"facturacion:{nombre}")
            self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_registro_crea_perfil(self):
        self.client.logout()
        self.client.post(reverse("registro"), {
            "username": "nuevo", "email": "n@e.ec", "password1": "ClaveSegura123", "password2": "ClaveSegura123"})
        self.assertTrue(Perfil.objects.filter(usuario__username="nuevo").exists())

    # ---------- modelo base ----------
    def test_crear_marca_llena_user_y_normaliza(self):
        r = self.client.post(reverse("facturacion:marca_crear"), {"nombre": " logitech ", "pais_origen": "Suiza", "activo": "on"})
        self.assertRedirects(r, reverse("facturacion:marca_lista"))
        marca = Marca.objects.get(nombre="Logitech")
        self.assertEqual(marca.user, self.user)          # UsuarioRegistroMixin
        self.assertIsNotNone(marca.fecha_creacion)

    def test_eliminar_marca_con_productos_esta_protegido(self):
        r = self.client.post(reverse("facturacion:marca_eliminar", args=[self.marca.pk]), follow=True)
        self.assertTrue(Marca.objects.filter(pk=self.marca.pk).exists())
        self.assertContains(r, "No se puede eliminar")

    def test_eliminar_categoria_no_borra_productos(self):
        self.producto.categorias.add(self.categoria)
        self.client.post(reverse("facturacion:categoria_eliminar", args=[self.categoria.pk]))
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())
        self.assertFalse(Categoria.objects.filter(pk=self.categoria.pk).exists())

    # ---------- productos con imagen ----------
    def test_crear_producto_con_foto(self):
        r = self.client.post(reverse("facturacion:producto_crear"), {
            "nombre": "Mouse", "precio": "18.50", "stock": "6", "marca": self.marca.pk,
            "categorias": [self.categoria.pk], "activo": "on", "imagen": foto()})
        self.assertRedirects(r, reverse("facturacion:producto_lista"))
        producto = Producto.objects.get(nombre="Mouse")
        self.assertTrue(producto.imagen.name.startswith("productos/"))
        self.assertEqual(producto.user, self.user)
        self.assertContains(self.client.get(reverse("facturacion:producto_lista")), producto.imagen.url)

    def test_precio_cero_no_es_valido(self):
        r = self.client.post(reverse("facturacion:producto_crear"), {
            "nombre": "X", "precio": "0", "stock": "1", "marca": self.marca.pk})
        self.assertContains(r, "El precio debe ser mayor que 0.")

    def test_producto_con_ventas_no_se_elimina(self):
        venta = Venta.objects.create(cliente=self.cliente)
        DetalleVenta.objects.create(venta=venta, producto=self.producto, cantidad=1, precio=25)
        self.client.post(reverse("facturacion:producto_eliminar", args=[self.producto.pk]))
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())

    # ---------- clientes y proveedores ----------
    def test_cedula_valida(self):
        r = self.client.post(reverse("facturacion:cliente_crear"), {"cedula": "12ab", "nombres": "A", "apellidos": "B"})
        self.assertContains(r, "exactamente 10 dígitos")
        r = self.client.post(reverse("facturacion:cliente_crear"), {"cedula": "12345abcde", "nombres": "A", "apellidos": "B"})
        self.assertContains(r, "solo números")

    def test_buscar_cliente_por_apellido_o_cedula_y_detalle_con_ventas(self):
        self.assertContains(self.client.get(reverse("facturacion:cliente_lista"), {"q": "rez"}), "Pérez")
        self.assertContains(self.client.get(reverse("facturacion:cliente_lista"), {"q": "0102"}), "Pérez")
        self.assertNotContains(self.client.get(reverse("facturacion:cliente_lista"), {"q": "zzz"}), "0102030405")
        Venta.objects.create(cliente=self.cliente)
        self.assertContains(self.client.get(reverse("facturacion:cliente_detalle", args=[self.cliente.pk])), "Ventas del cliente")

    def test_proveedor_ruc_y_logo(self):
        base = {"nombre": "Ana", "apellido": "Ruiz", "contacto": "022"}
        r = self.client.post(reverse("facturacion:proveedor_crear"), {**base, "ruc": "1234567890123"})
        self.assertContains(r, "terminar en 001")
        r = self.client.post(reverse("facturacion:proveedor_crear"), {**base, "ruc": "12345"})
        self.assertContains(r, "13 dígitos")
        r = self.client.post(reverse("facturacion:proveedor_crear"), {**base, "ruc": "0990000000001", "logo": foto("logo.png")})
        self.assertRedirects(r, reverse("facturacion:proveedor_lista"))
        self.assertTrue(Proveedor.objects.get(ruc="0990000000001").logo.name.startswith("proveedores/"))

    def test_proveedor_con_compras_no_se_elimina(self):
        Compra.objects.create(proveedor=self.proveedor)
        self.client.post(reverse("facturacion:proveedor_eliminar", args=[self.proveedor.pk]))
        self.assertTrue(Proveedor.objects.filter(pk=self.proveedor.pk).exists())

    # ---------- ventas ----------
    def datos_venta(self, cantidad=3, prefijo="detalles"):
        return {
            "cliente": self.cliente.pk, "fecha_hora": "2026-11-20T10:00", "tipo_pago": "contado",
            f"{prefijo}-TOTAL_FORMS": "1", f"{prefijo}-INITIAL_FORMS": "0",
            f"{prefijo}-MIN_NUM_FORMS": "1", f"{prefijo}-MAX_NUM_FORMS": "1000",
            f"{prefijo}-0-producto": self.producto.pk, f"{prefijo}-0-cantidad": str(cantidad),
        }

    def test_crear_venta_calcula_totales_y_descuenta_stock(self):
        r = self.client.post(reverse("facturacion:venta_crear"), self.datos_venta(3))
        venta = Venta.objects.get()
        self.assertRedirects(r, reverse("facturacion:venta_detalle", args=[venta.pk]))
        self.assertEqual((str(venta.subtotal), str(venta.iva), str(venta.total)), ("75.00", "11.25", "86.25"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7)
        self.assertEqual(venta.user, self.user)
        self.assertEqual(venta.detalles.get().precio, 25)
        self.assertContains(self.client.get(reverse("facturacion:venta_detalle", args=[venta.pk])), "86,25")

    def test_venta_sin_stock_suficiente_no_se_guarda(self):
        r = self.client.post(reverse("facturacion:venta_crear"), self.datos_venta(11))
        self.assertContains(r, "Stock insuficiente")
        self.assertFalse(Venta.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_editar_y_eliminar_venta_devuelven_stock(self):
        self.client.post(reverse("facturacion:venta_crear"), self.datos_venta(3))
        venta = Venta.objects.get()
        detalle = venta.detalles.get()
        datos = self.datos_venta(5)
        datos.update({"detalles-INITIAL_FORMS": "1", "detalles-0-id": detalle.pk, "detalles-0-venta": venta.pk})
        self.client.post(reverse("facturacion:venta_editar", args=[venta.pk]), datos)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 5)          # 10 - 5
        self.client.post(reverse("facturacion:venta_eliminar", args=[venta.pk]))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
        self.assertFalse(Venta.objects.exists())

    def test_filtrar_ventas(self):
        Venta.objects.create(cliente=self.cliente, tipo_pago="tarjeta")
        Venta.objects.create(cliente=self.cliente, tipo_pago="contado")
        r = self.client.get(reverse("facturacion:venta_lista"), {"tipo_pago": "tarjeta"})
        self.assertEqual(len(r.context["ventas"]), 1)

    # ---------- compras ----------
    def datos_compra(self, cantidad=10, costo="20.00"):
        return {
            "proveedor": self.proveedor.pk, "fecha_hora": "2026-11-20T10:00", "tipo_pago": "credito",
            "detalles-TOTAL_FORMS": "1", "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "1", "detalles-MAX_NUM_FORMS": "1000",
            "detalles-0-producto": self.producto.pk, "detalles-0-cantidad": str(cantidad), "detalles-0-precio": costo,
        }

    def test_compra_sube_stock_y_eliminar_lo_revierte(self):
        r = self.client.post(reverse("facturacion:compra_crear"), self.datos_compra(10))
        compra = Compra.objects.get()
        self.assertRedirects(r, reverse("facturacion:compra_detalle", args=[compra.pk]))
        self.assertEqual((str(compra.subtotal), str(compra.iva), str(compra.total)), ("200.00", "30.00", "230.00"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 20)
        self.client.post(reverse("facturacion:compra_eliminar", args=[compra.pk]))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_editar_compra_ajusta_stock(self):
        self.client.post(reverse("facturacion:compra_crear"), self.datos_compra(10))
        compra = Compra.objects.get()
        datos = self.datos_compra(4)
        datos.update({"detalles-INITIAL_FORMS": "1", "detalles-0-id": compra.detalles.get().pk, "detalles-0-compra": compra.pk})
        self.client.post(reverse("facturacion:compra_editar", args=[compra.pk]), datos)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 14)         # 10 + 4

    def test_no_se_puede_eliminar_compra_si_ya_se_vendio_su_stock(self):
        self.client.post(reverse("facturacion:compra_crear"), self.datos_compra(10))
        compra = Compra.objects.get()
        Producto.objects.filter(pk=self.producto.pk).update(stock=3)    # se vendió casi todo
        self.client.post(reverse("facturacion:compra_eliminar", args=[compra.pk]))
        self.assertTrue(Compra.objects.filter(pk=compra.pk).exists())

    def test_filtrar_compras_por_proveedor(self):
        otro = Proveedor.objects.create(nombre="Otro", apellido="Prov", ruc="0990000000001")
        Compra.objects.create(proveedor=self.proveedor)
        Compra.objects.create(proveedor=otro)
        r = self.client.get(reverse("facturacion:compra_lista"), {"proveedor": otro.pk})
        self.assertEqual(len(r.context["compras"]), 1)

    # ---------- mi perfil ----------
    def test_mi_perfil_edita_el_del_usuario_conectado(self):
        r = self.client.post(reverse("facturacion:mi_perfil"), {"cedula": "0102030405", "telefono": "099", "direccion": "Quito", "cargo": "Vendedor"})
        self.assertRedirects(r, reverse("facturacion:mi_perfil"))
        perfil = Perfil.objects.get(usuario=self.user)
        self.assertEqual(perfil.cargo, "Vendedor")
