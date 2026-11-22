# =====================================================================
# mi_tienda/views.py · página de inicio (VBC)
# =====================================================================
from django.db.models import Sum                       # SUM() de SQL
from django.utils import timezone
from django.views.generic import TemplateView          # VBC que muestra un template

from facturacion.models import Producto, Venta


class InicioView(TemplateView):                        # TemplateView: "muestra un template con datos"
    template_name = "home.html"                        # ATRIBUTO: ¿qué HTML?

    def get_context_data(self, **kwargs):              # MÉTODO: ¿qué datos recibe el HTML?
        contexto = super().get_context_data(**kwargs)  # 1. lo que TemplateView ya prepara
        activos = Producto.objects.filter(activo=True)
        hoy = timezone.localdate()                     # 2. la fecha de hoy en Ecuador
        ventas_hoy = Venta.objects.filter(fecha_hora__date=hoy)
        contexto["productos"] = activos.select_related("marca")[:4]            # destacados
        contexto["total_productos"] = activos.count()
        contexto["ventas_hoy"] = ventas_hoy.count()
        contexto["vendido_hoy"] = ventas_hoy.aggregate(suma=Sum("total"))["suma"] or 0   # SUM(total)
        contexto["stock_bajo"] = activos.filter(stock__lt=5)                   # menos de 5 unidades
        return contexto                                # 3. entregamos todo
