# =====================================================================
# facturacion/views.py
# Todas las vistas del CRUD son CLASES (VBC). Solo iniciar sesión, registrarse y cerrar sesión
# se quedan como funciones (VBF), igual que en la guía.
# Orden de herencia:  LoginRequiredMixin primero → tus mixins → vista genérica al final.
# =====================================================================
from django.contrib import messages                              # mensajes verdes / rojos
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin        # exige sesión (el @login_required de las clases)
from django.contrib.messages.views import SuccessMessageMixin    # mensaje de éxito automático
from django.db import transaction                                # transaction.atomic(): todo o nada
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    CategoriaForm, ClienteForm, CompraForm, DetalleCompraFormSet, DetalleVentaFormSet,
    MarcaForm, PerfilForm, ProductoForm, ProveedorForm, RegistroForm, VentaForm,
)
from .mixins import EliminarProtegidoMixin, UsuarioRegistroMixin
from .models import (
    IVA_TARIFA, Categoria, Cliente, Compra, Marca, Perfil, Producto, Proveedor, TipoPago, Venta,
)


# =====================================================================
# AUTENTICACIÓN · se queda en funciones (VBF)
# =====================================================================
@require_http_methods(["GET", "POST"])
def iniciar_sesion(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        messages.success(request, "Sesión iniciada correctamente.")
        return redirect("home")
    return render(request, "registration/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def registrarse(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        Perfil.objects.create(usuario=user, user=user)
        auth_login(request, user)
        messages.success(request, "Tu cuenta fue creada correctamente.")
        return redirect("home")
    return render(request, "registration/register.html", {"form": form})


@require_POST
def cerrar_sesion(request):
    auth_logout(request)
    messages.success(request, "Sesión cerrada.")
    return redirect("home")


# =====================================================================
# MI PERFIL (reto) · UpdateView SIN pk en la URL
# =====================================================================
class MiPerfilView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):
    model = Perfil
    form_class = PerfilForm
    template_name = "facturacion/perfil_form.html"
    success_url = reverse_lazy("facturacion:mi_perfil")
    success_message = "Tu perfil se actualizó correctamente."
    extra_context = {"titulo": "Mi perfil", "boton": "Guardar", "volver_url": reverse_lazy("home")}

    def get_object(self, queryset=None):               # en vez de buscar por pk...
        perfil, _ = Perfil.objects.get_or_create(usuario=self.request.user)   # ...el del usuario conectado
        return perfil


# =====================================================================
# MARCAS
# =====================================================================
class MarcaListView(LoginRequiredMixin, ListView):
    model = Marca
    template_name = "facturacion/marca_lista.html"
    context_object_name = "marcas"
    paginate_by = 10
    extra_context = {"titulo": "Marcas"}

    def get_queryset(self):
        marcas = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:                                          # busca por nombre O país
            marcas = marcas.filter(Q(nombre__icontains=q) | Q(pais_origen__icontains=q))
        return marcas

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        return contexto


class MarcaCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):
    model = Marca
    form_class = MarcaForm
    template_name = "facturacion/marca_form.html"
    success_url = reverse_lazy("facturacion:marca_lista")
    success_message = "Marca «%(nombre)s» creada correctamente."
    extra_context = {"titulo": "Nueva marca", "boton": "Guardar", "volver_url": reverse_lazy("facturacion:marca_lista")}


class MarcaUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):
    model = Marca
    form_class = MarcaForm
    template_name = "facturacion/marca_form.html"
    success_url = reverse_lazy("facturacion:marca_lista")
    success_message = "Marca «%(nombre)s» actualizada."
    extra_context = {"titulo": "Editar marca", "boton": "Actualizar", "volver_url": reverse_lazy("facturacion:marca_lista")}

    def form_invalid(self, form):                      # POST con errores
        messages.error(self.request, "Revisa los campos marcados en rojo.")
        return super().form_invalid(form)


class MarcaDeleteView(LoginRequiredMixin, EliminarProtegidoMixin, DeleteView):
    model = Marca
    template_name = "facturacion/marca_eliminar.html"
    context_object_name = "marca"
    success_url = reverse_lazy("facturacion:marca_lista")
    nombre_objeto = "Marca"
    mensaje_protegido = "tiene productos. Desactívala en su lugar."


# =====================================================================
# CATEGORÍAS
# =====================================================================
class CategoriaListView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = "facturacion/categoria_lista.html"
    context_object_name = "categorias"
    paginate_by = 10
    extra_context = {"titulo": "Categorías"}

    def get_queryset(self):
        categorias = super().get_queryset().annotate(cantidad_productos=Count("productos"))   # cuenta sus productos
        q = self.request.GET.get("q", "").strip()
        if q:
            categorias = categorias.filter(nombre__icontains=q)
        return categorias

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        return contexto


class CategoriaCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "facturacion/categoria_form.html"
    success_url = reverse_lazy("facturacion:categoria_lista")
    success_message = "Categoría «%(nombre)s» creada correctamente."
    extra_context = {"titulo": "Nueva categoría", "boton": "Guardar", "volver_url": reverse_lazy("facturacion:categoria_lista")}


class CategoriaUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "facturacion/categoria_form.html"
    success_url = reverse_lazy("facturacion:categoria_lista")
    success_message = "Categoría «%(nombre)s» actualizada."
    extra_context = {"titulo": "Editar categoría", "boton": "Actualizar", "volver_url": reverse_lazy("facturacion:categoria_lista")}


class CategoriaDeleteView(LoginRequiredMixin, DeleteView):
    # Relación N:M → no hay PROTECT: solo se borran los pares de la tabla intermedia (los productos quedan).
    model = Categoria
    template_name = "facturacion/categoria_eliminar.html"
    context_object_name = "categoria"
    success_url = reverse_lazy("facturacion:categoria_lista")

    def form_valid(self, form):
        nombre = self.object.nombre
        respuesta = super().form_valid(form)
        messages.success(self.request, f"Categoría «{nombre}» eliminada. Sus productos siguen existiendo.")
        return respuesta


# =====================================================================
# PRODUCTOS
# =====================================================================
class ProductoListView(LoginRequiredMixin, ListView):     # LISTAR
    model = Producto                                       # ¿qué tabla?
    template_name = "facturacion/producto_lista.html"      # ¿qué HTML?
    context_object_name = "productos"                      # nombre de la lista en el HTML
    paginate_by = 5                                        # 5 por página → envía page_obj
    extra_context = {"titulo": "Productos"}                # datos fijos extra para el HTML

    def get_queryset(self):                                # ¿QUÉ registros se muestran?
        productos = super().get_queryset()                 # lo normal: Producto.objects.all()
        productos = productos.select_related("marca").prefetch_related("categorias")   # menos consultas
        q = self.request.GET.get("q", "").strip()          # buscador: ?q=galaxy
        if q:
            productos = productos.filter(
                Q(nombre__icontains=q) | Q(marca__nombre__icontains=q) | Q(categorias__nombre__icontains=q)
            ).distinct()
        return productos

    def get_context_data(self, **kwargs):                  # ¿qué datos EXTRA recibe el HTML?
        contexto = super().get_context_data(**kwargs)      # lo que ListView ya armó
        contexto["q"] = self.request.GET.get("q", "").strip()   # + lo buscado
        return contexto


class ProductoCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):   # CREAR
    model = Producto
    form_class = ProductoForm                              # nuestro formulario
    template_name = "facturacion/producto_form.html"
    success_url = reverse_lazy("facturacion:producto_lista")   # a dónde ir al guardar
    success_message = "Producto «%(nombre)s» creado."      # %(nombre)s = el campo nombre del formulario
    extra_context = {"titulo": "Nuevo producto", "boton": "Guardar", "volver_url": reverse_lazy("facturacion:producto_lista")}


class ProductoUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):   # EDITAR
    model = Producto
    form_class = ProductoForm
    template_name = "facturacion/producto_form.html"       # el mismo template de crear
    success_url = reverse_lazy("facturacion:producto_lista")
    success_message = "Producto «%(nombre)s» actualizado."
    extra_context = {"titulo": "Editar producto", "boton": "Actualizar", "volver_url": reverse_lazy("facturacion:producto_lista")}

    def form_invalid(self, form):                          # cuando hay errores (POST inválido)
        messages.error(self.request, "Revisa los campos marcados en rojo.")
        return super().form_invalid(form)                  # vuelve a mostrar el formulario


class ProductoDetailView(LoginRequiredMixin, DetailView):  # VER UNO
    model = Producto
    template_name = "facturacion/producto_detalle.html"
    context_object_name = "producto"


class ProductoDeleteView(LoginRequiredMixin, EliminarProtegidoMixin, DeleteView):   # ELIMINAR
    model = Producto
    template_name = "facturacion/producto_eliminar.html"
    context_object_name = "producto"
    success_url = reverse_lazy("facturacion:producto_lista")
    nombre_objeto = "Producto"
    mensaje_protegido = "ya tiene ventas o compras. Desactívalo en su lugar."


# =====================================================================
# CLIENTES
# =====================================================================
class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = "facturacion/cliente_lista.html"
    context_object_name = "clientes"
    paginate_by = 5
    extra_context = {"titulo": "Clientes"}

    def get_queryset(self):
        clientes = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:   # Q(...) | Q(...) = condición con OR: por apellido O por cédula
            clientes = clientes.filter(Q(apellidos__icontains=q) | Q(cedula__icontains=q))
        return clientes

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        return contexto


class ClienteCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "facturacion/cliente_form.html"
    success_url = reverse_lazy("facturacion:cliente_lista")
    success_message = "Cliente «%(apellidos)s %(nombres)s» creado."
    extra_context = {"titulo": "Nuevo cliente", "boton": "Guardar", "volver_url": reverse_lazy("facturacion:cliente_lista")}


class ClienteUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "facturacion/cliente_form.html"
    success_url = reverse_lazy("facturacion:cliente_lista")
    success_message = "Cliente «%(apellidos)s %(nombres)s» actualizado."
    extra_context = {"titulo": "Editar cliente", "boton": "Actualizar", "volver_url": reverse_lazy("facturacion:cliente_lista")}


class ClienteDetailView(LoginRequiredMixin, DetailView):   # ficha + lista de sus ventas
    model = Cliente
    template_name = "facturacion/cliente_detalle.html"
    context_object_name = "cliente"


class ClienteDeleteView(LoginRequiredMixin, EliminarProtegidoMixin, DeleteView):
    model = Cliente
    template_name = "facturacion/cliente_eliminar.html"
    context_object_name = "cliente"
    success_url = reverse_lazy("facturacion:cliente_lista")
    nombre_objeto = "Cliente"
    mensaje_protegido = "tiene ventas registradas."


# =====================================================================
# PROVEEDORES (con logo)
# =====================================================================
class ProveedorListView(LoginRequiredMixin, ListView):
    model = Proveedor
    template_name = "facturacion/proveedor_lista.html"
    context_object_name = "proveedores"
    paginate_by = 5
    extra_context = {"titulo": "Proveedores"}

    def get_queryset(self):
        proveedores = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            proveedores = proveedores.filter(
                Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(ruc__icontains=q)
            )
        return proveedores

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        return contexto


class ProveedorCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = "facturacion/proveedor_form.html"
    success_url = reverse_lazy("facturacion:proveedor_lista")
    success_message = "Proveedor «%(nombre)s %(apellido)s» creado."
    extra_context = {"titulo": "Nuevo proveedor", "boton": "Guardar", "volver_url": reverse_lazy("facturacion:proveedor_lista")}


class ProveedorUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = "facturacion/proveedor_form.html"
    success_url = reverse_lazy("facturacion:proveedor_lista")
    success_message = "Proveedor «%(nombre)s %(apellido)s» actualizado."
    extra_context = {"titulo": "Editar proveedor", "boton": "Actualizar", "volver_url": reverse_lazy("facturacion:proveedor_lista")}


class ProveedorDeleteView(LoginRequiredMixin, EliminarProtegidoMixin, DeleteView):
    model = Proveedor
    template_name = "facturacion/proveedor_eliminar.html"
    context_object_name = "proveedor"
    success_url = reverse_lazy("facturacion:proveedor_lista")
    nombre_objeto = "Proveedor"
    mensaje_protegido = "tiene compras registradas."


# =====================================================================
# VENTAS (maestro-detalle)
# =====================================================================
class VentaListView(LoginRequiredMixin, ListView):
    model = Venta
    template_name = "facturacion/venta_lista.html"
    context_object_name = "ventas"
    paginate_by = 10
    extra_context = {"titulo": "Ventas", "tipos_pago": TipoPago.choices}   # opciones para el filtro

    def get_queryset(self):
        ventas = super().get_queryset().select_related("cliente")   # trae el cliente en el mismo JOIN
        q = self.request.GET.get("q", "").strip()
        tipo = self.request.GET.get("tipo_pago", "")
        if q:   # por apellido O por cédula
            ventas = ventas.filter(Q(cliente__apellidos__icontains=q) | Q(cliente__cedula__icontains=q))
        if tipo:
            ventas = ventas.filter(tipo_pago=tipo)
        return ventas

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        contexto["tipo_pago"] = self.request.GET.get("tipo_pago", "")
        return contexto


class VentaDetallesMixin:
    """Lo que COMPARTEN crear y editar una venta: cabecera (form) + filas (formset)."""
    model = Venta
    form_class = VentaForm
    template_name = "facturacion/venta_form.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)      # trae "form" (la cabecera)
        if "detalles" not in contexto:                     # en GET el formset todavía no existe...
            contexto["detalles"] = DetalleVentaFormSet(instance=self.object)   # ...lo creamos (vacío o lleno)
        return contexto

    def post(self, request, *args, **kwargs):              # REEMPLAZA el post() normal de la vista
        form = self.get_form()                             # 1. cabecera con request.POST
        detalles = DetalleVentaFormSet(request.POST, instance=self.object)   # 2. filas con request.POST
        if form.is_valid() and detalles.is_valid():        # 3. ¿las DOS partes están bien?
            return self.form_valid(form, detalles)
        return self.form_invalid(form, detalles)

    def form_valid(self, form, detalles):
        with transaction.atomic():                         # TODO o NADA: si algo falla, se deshace todo
            if self.object:                                # al EDITAR: devolver lo que la venta tenía
                self.object.devolver_stock()
            form.instance.user = self.request.user
            self.object = form.save()                      # INSERT o UPDATE de la cabecera
            self.guardar_detalles(detalles)                # INSERT / UPDATE / DELETE de las filas
            self.object.descontar_stock()                  # saca de bodega lo vendido
            self.object.calcular_totales()                 # subtotal, IVA y total
        messages.success(self.request, f"{self.object} guardada. Total: ${self.object.total}")
        return HttpResponseRedirect(self.get_success_url())

    def guardar_detalles(self, detalles):
        detalles.instance = self.object                    # las filas pertenecen a ESTA venta
        filas = detalles.save(commit=False)                # objetos nuevos o cambiados, SIN guardar todavía
        for fila in detalles.deleted_objects:              # filas con la casilla "Quitar"
            fila.delete()
        cambio_producto = {obj.pk for obj, campos in detalles.changed_objects if "producto" in campos}
        for fila in filas:
            if fila.pk is None or fila.pk in cambio_producto:   # fila nueva o con otro producto...
                fila.precio = fila.producto.precio              # ...toma el precio ACTUAL del producto
            fila.user = self.request.user
            fila.save()

    def form_invalid(self, form, detalles):
        messages.error(self.request, "Revisa los datos de la venta.")
        # volvemos a dibujar la página con la cabecera Y las filas, con sus errores
        return self.render_to_response(self.get_context_data(form=form, detalles=detalles))

    def get_success_url(self):
        return reverse("facturacion:venta_detalle", kwargs={"pk": self.object.pk})   # a la factura


class VentaCreateView(LoginRequiredMixin, VentaDetallesMixin, CreateView):   # CREAR
    extra_context = {"titulo": "Nueva venta", "boton": "Guardar venta", "volver_url": reverse_lazy("facturacion:venta_lista")}

    def post(self, request, *args, **kwargs):
        self.object = None                                 # CreateView: aún no hay venta
        return super().post(request, *args, **kwargs)      # sigue al post() del mixin


class VentaUpdateView(LoginRequiredMixin, VentaDetallesMixin, UpdateView):   # EDITAR
    extra_context = {"titulo": "Editar venta", "boton": "Actualizar venta", "volver_url": reverse_lazy("facturacion:venta_lista")}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()                    # UpdateView: la venta del <int:pk>
        return super().post(request, *args, **kwargs)


class VentaDetailView(LoginRequiredMixin, DetailView):     # VER (la factura)
    model = Venta
    template_name = "facturacion/venta_detalle.html"
    context_object_name = "venta"

    def get_queryset(self):
        return super().get_queryset().select_related("cliente", "user").prefetch_related("detalles__producto")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["iva_porcentaje"] = int(IVA_TARIFA * 100)   # 15
        return contexto


class VentaDeleteView(LoginRequiredMixin, DeleteView):     # ELIMINAR
    model = Venta
    template_name = "facturacion/venta_eliminar.html"
    context_object_name = "venta"
    success_url = reverse_lazy("facturacion:venta_lista")

    def form_valid(self, form):
        with transaction.atomic():
            self.object.devolver_stock()                   # 1. los productos regresan a la bodega
            respuesta = super().form_valid(form)           # 2. DELETE de la venta (CASCADE borra sus detalles)
        messages.success(self.request, "Venta eliminada y stock devuelto.")
        return respuesta


# =====================================================================
# COMPRAS (maestro-detalle) · el espejo de Ventas: el stock SUBE
# =====================================================================
class CompraListView(LoginRequiredMixin, ListView):
    model = Compra
    template_name = "facturacion/compra_lista.html"
    context_object_name = "compras"
    paginate_by = 10
    extra_context = {"titulo": "Compras", "tipos_pago": TipoPago.choices}

    def get_queryset(self):
        compras = super().get_queryset().select_related("proveedor")
        proveedor = self.request.GET.get("proveedor", "")
        tipo = self.request.GET.get("tipo_pago", "")
        if proveedor:                                      # filtro por proveedor (id)
            compras = compras.filter(proveedor_id=proveedor)
        if tipo:                                           # filtro por tipo de pago
            compras = compras.filter(tipo_pago=tipo)
        return compras

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["proveedores"] = Proveedor.objects.all()  # opciones del filtro
        contexto["proveedor"] = self.request.GET.get("proveedor", "")
        contexto["tipo_pago"] = self.request.GET.get("tipo_pago", "")
        return contexto


class CompraDetallesMixin:
    """Lo que COMPARTEN crear y editar una compra: cabecera (form) + filas (formset)."""
    model = Compra
    form_class = CompraForm
    template_name = "facturacion/compra_form.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        if "detalles" not in contexto:
            contexto["detalles"] = DetalleCompraFormSet(instance=self.object)
        return contexto

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        detalles = DetalleCompraFormSet(request.POST, instance=self.object)
        if form.is_valid() and detalles.is_valid():
            return self.form_valid(form, detalles)
        return self.form_invalid(form, detalles)

    def form_valid(self, form, detalles):
        with transaction.atomic():
            if self.object:                                # al EDITAR: sacar de bodega lo que la compra había metido
                self.object.revertir_stock()
            form.instance.user = self.request.user
            self.object = form.save()
            detalles.instance = self.object
            filas = detalles.save(commit=False)
            for fila in detalles.deleted_objects:
                fila.delete()
            for fila in filas:                             # aquí el precio (costo) viene del formulario
                fila.user = self.request.user
                fila.save()
            self.object.ingresar_stock()                   # mete a bodega lo comprado: el stock SUBE
            self.object.calcular_totales()
        messages.success(self.request, f"{self.object} guardada. Total: ${self.object.total}")
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, detalles):
        messages.error(self.request, "Revisa los datos de la compra.")
        return self.render_to_response(self.get_context_data(form=form, detalles=detalles))

    def get_success_url(self):
        return reverse("facturacion:compra_detalle", kwargs={"pk": self.object.pk})


class CompraCreateView(LoginRequiredMixin, CompraDetallesMixin, CreateView):
    extra_context = {"titulo": "Nueva compra", "boton": "Guardar compra", "volver_url": reverse_lazy("facturacion:compra_lista")}

    def post(self, request, *args, **kwargs):
        self.object = None
        return super().post(request, *args, **kwargs)


class CompraUpdateView(LoginRequiredMixin, CompraDetallesMixin, UpdateView):
    extra_context = {"titulo": "Editar compra", "boton": "Actualizar compra", "volver_url": reverse_lazy("facturacion:compra_lista")}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)


class CompraDetailView(LoginRequiredMixin, DetailView):
    model = Compra
    template_name = "facturacion/compra_detalle.html"
    context_object_name = "compra"

    def get_queryset(self):
        return super().get_queryset().select_related("proveedor", "user").prefetch_related("detalles__producto")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["iva_porcentaje"] = int(IVA_TARIFA * 100)
        return contexto


class CompraDeleteView(LoginRequiredMixin, DeleteView):
    model = Compra
    template_name = "facturacion/compra_eliminar.html"
    context_object_name = "compra"
    success_url = reverse_lazy("facturacion:compra_lista")

    def form_valid(self, form):
        # Si parte de lo comprado ya se vendió, revertir dejaría el stock negativo: no dejamos eliminar.
        for detalle in self.object.detalles.select_related("producto"):
            if detalle.producto.stock < detalle.cantidad:
                messages.error(
                    self.request,
                    f"No se puede eliminar {self.object}: parte de «{detalle.producto.nombre}» ya se vendió.",
                )
                return redirect(self.success_url)
        with transaction.atomic():
            self.object.revertir_stock()                   # el stock baja lo que había subido
            respuesta = super().form_valid(form)
        messages.success(self.request, "Compra eliminada y stock revertido.")
        return respuesta
