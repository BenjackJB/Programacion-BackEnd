"""
Administrador de Django — personalizado con filtros, búsquedas,
listados optimizados y templates propios.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import F
from django.utils.html import format_html

from .models import (
    Categoria,
    Cliente,
    ComponenteProducto,
    Despacho,
    DetallePedido,
    Insumo,
    MovimientoInsumo,
    Perfil,
    Pedido,
    Producto,
)


# ---------------------------------------------------------------------------
# Insumos + BOM
# ---------------------------------------------------------------------------
class StockBajoFilter(admin.SimpleListFilter):
    """Filtro lateral: insumos con stock igual o bajo el mínimo."""

    title = "nivel de stock"
    parameter_name = "stock_bajo"

    def lookups(self, request, model_admin):
        return (
            ("si", "Solo con stock bajo"),
            ("ok", "Con stock suficiente"),
        )

    def queryset(self, request, queryset):
        if self.value() == "si":
            return queryset.filter(stock_actual__lte=F("stock_minimo"))
        if self.value() == "ok":
            return queryset.filter(stock_actual__gt=F("stock_minimo"))
        return queryset


class ComponenteInline(admin.TabularInline):
    model = ComponenteProducto
    extra = 1
    autocomplete_fields = ["insumo"]
    fields = ["insumo", "cantidad", "costo_linea"]
    readonly_fields = ["costo_linea"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio_base", "costo_insumos", "margen", "activo", "emoji")
    list_filter = ("categoria", "activo", "unidad")
    search_fields = ("nombre", "descripcion", "categoria__nombre")
    list_editable = ("precio_base", "activo")
    list_per_page = 25
    autocomplete_fields = ["categoria"]
    inlines = [ComponenteInline]
    readonly_fields = ("costo_insumos", "margen", "creado", "actualizado")
    fieldsets = (
        ("Información del producto", {
            "fields": ("categoria", "nombre", "descripcion", "imagen", "activo"),
        }),
        ("Precio y unidad", {
            "fields": ("precio_base", "unidad", "costo_insumos", "margen"),
        }),
        ("Auditoría", {"fields": ("creado", "actualizado")}),
    )

    @admin.display(description="Costo insumos")
    def costo_insumos(self, obj):
        return f"${obj.costo_insumos:,.0f}"

    @admin.display(description="Margen")
    def margen(self, obj):
        valor = obj.margen
        color = "#2e7d32" if valor >= 0 else "#c62828"
        # Nota: format_html escapa los args antes de formatear, por eso el
        # número se formatea a string ANTES (Django 5.x no admite :,.0f sobre
        # Decimal ya escapado).
        return format_html('<b style="color:{}">${}</b>', color, f"{valor:,.0f}")

    @admin.display(description="Emoji")
    def emoji(self, obj):
        return obj.imagen or "🍰"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa", "total_productos")
    list_filter = ("activa",)
    search_fields = ("nombre",)
    list_editable = ("activa",)

    @admin.display(description="Productos")
    def total_productos(self, obj):
        return obj.productos.count()


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre", "unidad", "stock_actual", "stock_minimo",
        "badge_stock", "precio_unitario", "valor_total", "proveedor", "activo",
    )
    list_filter = ("unidad", "activo", StockBajoFilter)
    search_fields = ("nombre", "proveedor")
    list_editable = ("precio_unitario", "stock_minimo", "activo")
    list_per_page = 25
    readonly_fields = ("valor_total", "creado", "actualizado")
    actions = ["reponer_stock"]

    @admin.display(boolean=True, description="Stock bajo")
    def stock_bajo_filtro(self, obj):
        return obj.stock_bajo

    @admin.display(description="Estado")
    def badge_stock(self, obj):
        if obj.stock_bajo:
            return format_html(
                '<span style="background:#fa7864;color:#fff;padding:2px 8px;'
                'border-radius:999px;font-size:11px">BAJO</span>'
            )
        return format_html(
            '<span style="background:#e8e8e1;color:#282828;padding:2px 8px;'
            'border-radius:999px;font-size:11px">OK</span>'
        )

    @admin.display(description="Valor total")
    def valor_total(self, obj):
        return f"${obj.valor_total:,.0f}"

    @admin.action(description="Reponer stock seleccionado (+10)")
    def reponer_stock(self, request, queryset):
        for insumo in queryset:
            insumo.reponer(10, motivo=f"Reposición masiva por {request.user.username}")
        self.message_user(request, f"{queryset.count()} insumos repuestos (+10 cada uno).")


@admin.register(MovimientoInsumo)
class MovimientoInsumoAdmin(admin.ModelAdmin):
    list_display = ("insumo", "tipo_badge", "cantidad", "motivo", "pedido", "registrado_por", "creado")
    list_filter = ("tipo", "creado")
    search_fields = ("insumo__nombre", "motivo", "pedido__numero")
    readonly_fields = ("insumo", "tipo", "cantidad", "motivo", "pedido", "registrado_por", "creado", "actualizado")
    date_hierarchy = "creado"

    @admin.display(description="Tipo")
    def tipo_badge(self, obj):
        if obj.tipo == MovimientoInsumo.Tipo.ENTRADA:
            color, texto = "#2e7d32", "ENTRADA"
        else:
            color, texto = "#fa7864", "SALIDA"
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:999px;font-size:11px">{}</span>',
            color, texto,
        )

    def has_add_permission(self, request):
        return False  # Solo se crean desde la lógica de negocio


# ---------------------------------------------------------------------------
# Pedidos + Kanban
# ---------------------------------------------------------------------------
class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1
    autocomplete_fields = ["producto"]
    fields = ("producto", "cantidad", "precio_unitario", "subtotal")
    readonly_fields = ("subtotal",)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "numero", "cliente", "estado_badge", "prioridad_badge",
        "fecha_entrega", "total", "estado_despacho", "atrasado_badge",
    )
    list_filter = ("estado", "prioridad", "estado_despacho", "fecha_entrega", "creado")
    search_fields = ("numero", "cliente__nombre", "cliente__email", "descripcion_diseño")
    list_per_page = 25
    autocomplete_fields = ["cliente"]
    inlines = [DetallePedidoInline]
    readonly_fields = (
        "numero", "subtotal", "total", "insumos_descontados",
        "creado", "actualizado", "creador",
    )
    date_hierarchy = "fecha_entrega"
    save_on_top = True
    actions = ["avanzar_kanban", "retroceder_kanban", "descontar_insumos"]

    fieldsets = (
        ("Pedido", {
            "fields": ("numero", "cliente", "creador", "estado", "prioridad"),
        }),
        ("Diseño personalizado", {
            "fields": ("descripcion_diseño", "ingredientes_especiales"),
        }),
        ("Entrega", {
            "fields": ("fecha_entrega", "direccion_despacho", "estado_despacho"),
        }),
        ("Costos", {
            "fields": ("subtotal", "descuento", "total"),
        }),
        ("Inventario", {
            "fields": ("insumos_descontados",),
        }),
        ("Notas", {"fields": ("notas",)}),
        ("Auditoría", {"fields": ("creado", "actualizado")}),
    )

    @admin.display(description="Estado")
    def estado_badge(self, obj):
        colores = {
            "recibido": "#707070",
            "preparacion": "#dc8264",
            "horneado": "#fa7864",
            "control": "#282828",
            "listo": "#2e7d32",
        }
        color = colores.get(obj.estado, "#707070")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:999px;font-size:11px;white-space:nowrap">{}</span>',
            color, obj.get_estado_display(),
        )

    @admin.display(description="Prioridad")
    def prioridad_badge(self, obj):
        colores = {"normal": "#e8e8e1", "alta": "#dc8264", "urgente": "#fa7864"}
        bg = colores.get(obj.prioridad, "#e8e8e1")
        fg = "#fff" if obj.prioridad != "normal" else "#282828"
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;'
            'border-radius:999px;font-size:11px">{}</span>',
            bg, fg, obj.get_prioridad_display(),
        )

    @admin.display(boolean=True, description="Atrasado")
    def atrasado_badge(self, obj):
        return obj.atrasado

    @admin.action(description="▲ Avanzar estado Kanban seleccionados")
    def avanzar_kanban(self, request, queryset):
        exito, error = 0, 0
        for pedido in queryset:
            try:
                pedido.avanzar_estado()
                exito += 1
            except Exception:
                error += 1
        self.message_user(request, f"{exito} pedidos avanzados. {error} no pudieron avanzar.")

    @admin.action(description="▼ Retroceder estado Kanban seleccionados")
    def retroceder_kanban(self, request, queryset):
        exito, error = 0, 0
        for pedido in queryset:
            try:
                pedido.retroceder_estado()
                exito += 1
            except Exception:
                error += 1
        self.message_user(request, f"{exito} pedidos retrocedidos. {error} no pudieron retroceder.")

    @admin.action(description="Descuento de insumos por BOM")
    def descontar_insumos(self, request, queryset):
        exito, error = 0, 0
        for pedido in queryset:
            try:
                pedido.descontar_insumos()
                exito += 1
            except Exception as e:
                error += 1
                self.message_user(request, f"Error en {pedido.numero}: {e}", level="error")
        self.message_user(request, f"{exito} pedidos con inventario descontado.")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "telefono", "comuna", "total_pedidos", "activo")
    list_filter = ("activo", "comuna")
    search_fields = ("nombre", "email", "telefono", "direccion")
    list_editable = ("activo",)
    list_per_page = 25
    fieldsets = (
        ("Datos de contacto", {"fields": ("nombre", "email", "telefono", "activo")}),
        ("Dirección", {"fields": ("direccion", "comuna")}),
        ("Notas", {"fields": ("notas",)}),
    )

    @admin.display(description="Pedidos")
    def total_pedidos(self, obj):
        return obj.pedidos.count()


# ---------------------------------------------------------------------------
# Despachos con firma
# ---------------------------------------------------------------------------
@admin.register(Despacho)
class DespachoAdmin(admin.ModelAdmin):
    list_display = (
        "pedido", "transportista", "fecha_programada",
        "estado_badge", "recibido_por", "firma_ok", "entregado_en",
    )
    list_filter = ("estado", "fecha_programada", "creado")
    search_fields = ("pedido__numero", "transportista", "direccion", "recibido_por")
    readonly_fields = ("entregado_en", "creado", "actualizado")
    date_hierarchy = "fecha_programada"
    actions = ["marcar_entregado"]

    @admin.display(description="Estado")
    def estado_badge(self, obj):
        colores = {
            "pendiente": "#707070",
            "en_ruta": "#dc8264",
            "entregado": "#2e7d32",
            "rechazado": "#c62828",
        }
        color = colores.get(obj.estado, "#707070")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:999px;font-size:11px">{}</span>',
            color, obj.get_estado_display(),
        )

    @admin.display(boolean=True, description="Firma")
    def firma_ok(self, obj):
        return bool(obj.firma_digital) or bool(obj.comprobante)

    @admin.action(description="Confirmar entrega con firma existente")
    def marcar_entregado(self, request, queryset):
        exito, error = 0, 0
        for d in queryset:
            try:
                d.confirmar_entrega(recibido_por=d.recibido_por or "—", firma=d.firma_digital)
                exito += 1
            except Exception:
                error += 1
        self.message_user(request, f"{exito} entregas confirmadas. {error} requieren firma.")


# ---------------------------------------------------------------------------
# Perfiles de usuario (extiende el User nativo)
# ---------------------------------------------------------------------------
class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    verbose_name_plural = "Perfil / Rol"


class UserAdmin(BaseUserAdmin):
    inlines = (PerfilInline,)
    list_display = ("username", "email", "first_name", "last_name", "rol", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "perfil__rol")

    @admin.display(description="Rol")
    def rol(self, obj):
        perfil = getattr(obj, "perfil", None)
        return perfil.get_rol_display() if perfil else "—"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.site_header = "Dulce Arte · Administración"
admin.site.site_title = "Dulce Arte Admin"
admin.site.index_title = "Gestión de la pastelería artesanal"
