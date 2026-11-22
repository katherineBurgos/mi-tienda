# =====================================================================
# facturacion/mixins.py
# Un MIXIN es una clase pequeña con UNA habilidad, pensada para sumarse a otras clases.
# =====================================================================
from django.contrib import messages                  # mensajes verdes / rojos
from django.db.models import ProtectedError          # error que lanza Django cuando un registro está protegido
from django.shortcuts import redirect


class UsuarioRegistroMixin:
    """Llena el campo user del ModeloBase con el usuario conectado."""

    def form_valid(self, form):                      # se ejecuta cuando el formulario es válido (POST)
        form.instance.user = self.request.user       # form.instance = el objeto que se va a guardar
        return super().form_valid(form)              # sigue la cadena: guarda y redirige


class EliminarProtegidoMixin:
    """Para DeleteView: si el registro tiene hijos con PROTECT, avisa en vez de romperse.

    La vista que lo use define:
        nombre_objeto    → texto para el mensaje (ej. "Marca")
        mensaje_protegido → por qué no se pudo eliminar
    """
    nombre_objeto = "Registro"                       # qué se está eliminando (para el mensaje verde)
    mensaje_protegido = "Tiene registros relacionados. Desactívalo en su lugar."   # mensaje rojo

    def form_valid(self, form):                      # se ejecuta al confirmar la eliminación (POST)
        texto = str(self.object)                     # self.object = el registro a eliminar (lo guardamos antes de borrar)
        try:
            respuesta = super().form_valid(form)     # DELETE + redirect
        except ProtectedError:                       # algún hijo con on_delete=PROTECT lo impide
            messages.error(self.request, f"No se puede eliminar «{texto}»: {self.mensaje_protegido}")
            return redirect(self.get_success_url())  # volvemos a la lista sin borrar nada
        messages.success(self.request, f"{self.nombre_objeto} «{texto}» eliminado.")
        return respuesta
