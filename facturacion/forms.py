# =====================================================================
# facturacion/forms.py
# Un ModelForm convierte un MODELO en un FORMULARIO HTML y valida lo que se escribe.
# Los métodos clean_<campo>() agregan reglas propias: si algo está mal, lanzan ValidationError.
# =====================================================================
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import (
    Categoria, Cliente, Compra, DetalleCompra, DetalleVenta, Marca,
    Perfil, Producto, Proveedor, Venta,
)


# =====================================================================
# MARCA
# =====================================================================
class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ["nombre", "pais_origen", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej.: Samsung"}),
            "pais_origen": forms.TextInput(attrs={"placeholder": "Ej.: Corea del Sur"}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 2:
            raise forms.ValidationError("El nombre debe tener al menos 2 letras.")
        return nombre.title()


# =====================================================================
# CATEGORÍA
# =====================================================================
class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "activo"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 letras.")
        return nombre.title()


# =====================================================================
# PRODUCTO (con imagen)
# =====================================================================
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        # user, fecha_creacion y fecha_modificacion NO van: los llena el sistema
        fields = ["nombre", "descripcion", "marca", "categorias", "precio", "stock", "imagen", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej.: Galaxy A55"}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "marca": forms.Select(),                                    # 1:N → una opción
            "categorias": forms.CheckboxSelectMultiple(),               # N:M → varias
            "precio": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"min": "0"}),
            # ClearableFileInput = <input type="file"> + casilla "Limpiar" para quitar la foto actual
            "imagen": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        marcas = Marca.objects.filter(activo=True)                      # solo marcas activas...
        if self.instance.pk:                                            # ...más la que ya tiene el producto al editar
            marcas = Marca.objects.filter(activo=True) | Marca.objects.filter(pk=self.instance.marca_id)
        self.fields["marca"].queryset = marcas.distinct()
        self.fields["marca"].empty_label = "— Elige una marca —"

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 2:
            raise forms.ValidationError("El nombre debe tener al menos 2 letras.")
        return nombre

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor que 0.")
        return precio


# =====================================================================
# CLIENTE
# =====================================================================
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["cedula", "nombres", "apellidos", "email", "telefono", "direccion"]
        widgets = {"direccion": forms.Textarea(attrs={"rows": 2})}

    def clean_cedula(self):
        cedula = self.cleaned_data["cedula"].strip()
        if len(cedula) != 10:
            raise forms.ValidationError("La cédula debe tener exactamente 10 dígitos.")
        if not cedula.isdigit():
            raise forms.ValidationError("La cédula debe contener solo números.")
        return cedula


# =====================================================================
# PROVEEDOR (con logo)
# =====================================================================
class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre", "apellido", "ruc", "email", "contacto", "logo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej.: Carlos"}),
            "apellido": forms.TextInput(attrs={"placeholder": "Ej.: Andrade"}),
            "ruc": forms.TextInput(attrs={"placeholder": "Ej.: 1790000000001", "maxlength": "13"}),
            "logo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_ruc(self):
        ruc = self.cleaned_data["ruc"].strip()
        if not ruc.isdigit():
            raise forms.ValidationError("El RUC debe contener solo números.")
        if len(ruc) != 13:
            raise forms.ValidationError("El RUC debe tener exactamente 13 dígitos.")
        if not ruc.endswith("001"):
            raise forms.ValidationError("El RUC debe terminar en 001.")
        return ruc


# =====================================================================
# VENTA: cabecera (maestro)
# =====================================================================
class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ["cliente", "fecha_hora", "tipo_pago"]   # subtotal, iva y total los calcula el sistema
        widgets = {
            # type="datetime-local" → el navegador muestra un calendario con hora
            "fecha_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_hora"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["cliente"].empty_label = "— Elige un cliente —"


# =====================================================================
# VENTA: filas del detalle
# =====================================================================
class ProductoConPrecioField(forms.ModelChoiceField):
    """Lista desplegable de productos que muestra también el precio y el stock."""

    def label_from_instance(self, obj):               # Django llama a este método para escribir cada <option>
        return f"{obj.nombre} · ${obj.precio} · stock: {obj.stock}"


class DetalleVentaForm(forms.ModelForm):
    producto = ProductoConPrecioField(
        queryset=Producto.objects.filter(activo=True),
        empty_label="— Elige un producto —",
    )

    class Meta:
        model = DetalleVenta
        fields = ["producto", "cantidad"]             # el precio NO: lo pone la vista con el precio actual
        widgets = {"cantidad": forms.NumberInput(attrs={"min": "1"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:                          # al editar, el producto ya vendido siempre aparece
            self.fields["producto"].queryset = (
                Producto.objects.filter(activo=True) | Producto.objects.filter(pk=self.instance.producto_id)
            ).distinct()


class BaseDetalleVentaFormSet(BaseInlineFormSet):
    """Validación de TODAS las filas juntas: ¿hay stock para lo que se pide?"""

    def clean(self):
        super().clean()                               # primero las validaciones normales de cada fila
        if any(self.errors):                          # si alguna fila ya tiene errores, no seguimos
            return
        pedido = {}                                   # {producto: cantidad total pedida}
        for fila in self.forms:
            datos = fila.cleaned_data
            if not datos or datos.get("DELETE"):      # fila vacía o marcada para quitar → se ignora
                continue
            producto = datos["producto"]
            pedido[producto] = pedido.get(producto, 0) + datos["cantidad"]   # suma si el producto se repite
        anterior = {}                                 # al EDITAR: lo que esta venta ya tenía reservado
        if self.instance.pk:
            for detalle in self.instance.detalles.all():
                anterior[detalle.producto_id] = anterior.get(detalle.producto_id, 0) + detalle.cantidad
        for producto, cantidad in pedido.items():
            disponible = producto.stock + anterior.get(producto.pk, 0)
            if cantidad > disponible:
                raise ValidationError(
                    f"Stock insuficiente de «{producto.nombre}»: pides {cantidad} y hay {disponible}."
                )


# inlineformset_factory crea una CLASE de formset: muchos DetalleVentaForm unidos a UNA Venta
DetalleVentaFormSet = inlineformset_factory(
    Venta,                                            # el maestro
    DetalleVenta,                                     # el detalle (tiene la ForeignKey venta)
    form=DetalleVentaForm,                            # el formulario de cada fila
    formset=BaseDetalleVentaFormSet,                  # nuestra validación de stock
    extra=0,                                          # filas vacías extra (las agrega el botón con JavaScript)
    min_num=1,                                        # mínimo 1 fila...
    validate_min=True,                                # ...y se valida que exista
    can_delete=True,                                  # cada fila tiene la casilla "Quitar"
)


# =====================================================================
# COMPRA: cabecera (maestro)
# =====================================================================
class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ["proveedor", "fecha_hora", "tipo_pago"]   # subtotal, iva y total los calcula el sistema
        widgets = {
            "fecha_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_hora"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["proveedor"].empty_label = "— Elige un proveedor —"


# =====================================================================
# COMPRA: filas del detalle (aquí el precio SÍ lo escribe la persona: es el costo)
# =====================================================================
class DetalleCompraForm(forms.ModelForm):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(activo=True),
        empty_label="— Elige un producto —",
    )

    class Meta:
        model = DetalleCompra
        fields = ["producto", "cantidad", "precio"]   # precio = costo unitario que cobró el proveedor
        widgets = {
            "cantidad": forms.NumberInput(attrs={"min": "1"}),
            "precio": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["producto"].queryset = (
                Producto.objects.filter(activo=True) | Producto.objects.filter(pk=self.instance.producto_id)
            ).distinct()

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio <= 0:
            raise forms.ValidationError("El costo debe ser mayor que 0.")
        return precio


class BaseDetalleCompraFormSet(BaseInlineFormSet):
    """Al comprar no hace falta revisar stock. Al EDITAR sí: al revertir la compra vieja no puede quedar negativo."""

    def clean(self):
        super().clean()
        if any(self.errors) or not self.instance.pk:      # compra nueva: nada que revertir
            return
        nuevo = {}                                        # lo que la compra tendrá después de editar
        for fila in self.forms:
            datos = fila.cleaned_data
            if not datos or datos.get("DELETE"):
                continue
            producto = datos["producto"]
            nuevo[producto] = nuevo.get(producto, 0) + datos["cantidad"]
        anterior = {}                                     # lo que la compra tenía antes de editar
        for detalle in self.instance.detalles.select_related("producto"):
            anterior[detalle.producto] = anterior.get(detalle.producto, 0) + detalle.cantidad
        for producto in set(nuevo) | set(anterior):
            stock_final = producto.stock - anterior.get(producto, 0) + nuevo.get(producto, 0)
            if stock_final < 0:
                raise ValidationError(
                    f"No puedes reducir tanto «{producto.nombre}»: parte de ese stock ya se vendió."
                )


DetalleCompraFormSet = inlineformset_factory(
    Compra, DetalleCompra,
    form=DetalleCompraForm,
    formset=BaseDetalleCompraFormSet,
    extra=0, min_num=1, validate_min=True, can_delete=True,
)


# =====================================================================
# PERFIL
# =====================================================================
class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ["cedula", "telefono", "direccion", "cargo"]
        widgets = {"direccion": forms.Textarea(attrs={"rows": 2})}


# =====================================================================
# REGISTRO (crear cuenta)
# =====================================================================
class RegistroForm(forms.Form):
    username = forms.CharField(max_length=150, strip=False, label="Nombre de usuario")
    email = forms.EmailField(required=True, label="Correo electrónico")
    password1 = forms.CharField(
        required=True,
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ese nombre de usuario ya está registrado.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        if self.errors:
            raise ValueError("No se puede guardar el formulario con errores.")
        user = User(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
        )
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
