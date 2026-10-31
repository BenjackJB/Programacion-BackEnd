"""Vistas de plantillas (frontend server-rendered)."""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from api.serializers import (
    CategoriaSerializer,
    ClienteSerializer,
    DespachoSerializer,
    InsumoSerializer,
    MovimientoInsumoSerializer,
    PedidoSerializer,
    ProductoSerializer,
)
from core.models import Categoria, Cliente, Despacho, Insumo, MovimientoInsumo, Pedido, Producto
from core.decorators import ADMIN, COCINA, DESPACHO, roles_required, user_tiene_rol


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:inicio")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get("next") or "core:inicio"
            messages.success(request, f"Bienvenido(a), {user.get_full_name() or user.username}.")
            return redirect(next_url)
        messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()
    return render(request, "core/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect("core:login")


def acceso_restringido(request, exception=None):
    """Manejador 403: página amigable cuando el rol no tiene permiso."""
    return render(request, "core/403.html", status=403)


# ---------------------------------------------------------------------------
# Inicio / Panel
# ---------------------------------------------------------------------------
@login_required
def inicio(request):
    pedidos = Pedido.objects.all()
    insumos = Insumo.objects.all()
    ctx = {
        "pedidos_total": pedidos.count(),
        "pedidos_recibidos": pedidos.filter(estado=Pedido.Estado.RECIBIDO).count(),
        "pedidos_preparacion": pedidos.filter(estado=Pedido.Estado.EN_PREPARACION).count(),
        "pedidos_listos": pedidos.filter(estado=Pedido.Estado.LISTO).count(),
        "pedidos_atrasados": sum(1 for p in pedidos if p.atrasado),
        "ingresos_totales": pedidos.aggregate(t=Sum("total"))["t"] or 0,
        "insumos_stock_bajo": [i for i in insumos if i.stock_bajo],
        "despachos_pendientes": Despacho.objects.filter(
            estado__in=[Despacho.Estado.PENDIENTE, Despacho.Estado.EN_RUTA]
        ).count(),
        "clientes_total": Cliente.objects.filter(activo=True).count(),
        "proximos": pedidos.filter(estado__in=[
            Pedido.Estado.RECIBIDO, Pedido.Estado.EN_PREPARACION,
            Pedido.Estado.HORNEADO, Pedido.Estado.CONTROL,
        ]).select_related("cliente")[:6],
        "movimientos": MovimientoInsumo.objects.select_related(
            "insumo", "registrado_por"
        )[:8],
        "categorias": Categoria.objects.filter(activa=True),
    }
    return render(request, "core/inicio.html", ctx)


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------
@login_required
def productos(request):
    qs = Producto.objects.select_related("categoria")
    categoria_id = request.GET.get("categoria")
    if categoria_id:
        qs = qs.filter(categoria_id=categoria_id)
    search = request.GET.get("q")
    if search:
        qs = qs.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))
    ctx = {
        "productos": qs,
        "categorias": Categoria.objects.filter(activa=True),
        "categoria_activa": categoria_id or "",
        "q": search or "",
    }
    return render(request, "core/productos.html", ctx)


@login_required
def producto_detalle(request, pk):
    producto = get_object_or_404(
        Producto.objects.select_related("categoria").prefetch_related("componentes__insumo"), pk=pk
    )
    return render(request, "core/producto_detalle.html", {"producto": producto})


# ---------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------
@login_required
def insumos(request):
    qs = Insumo.objects.all()
    if request.GET.get("bajo") == "1":
        qs = [i for i in qs if i.stock_bajo]
    search = request.GET.get("q")
    if search:
        qs = [i for i in (qs if isinstance(qs, list) else qs) if search.lower() in i.nombre.lower()]
    ctx = {
        "insumos": qs if isinstance(qs, list) else list(qs),
        "q": search or "",
        "solo_bajo": request.GET.get("bajo") == "1",
        "valor_total": sum(i.valor_total for i in Insumo.objects.all()),
        "stock_bajo_total": sum(1 for i in Insumo.objects.all() if i.stock_bajo),
    }
    return render(request, "core/insumos.html", ctx)


@login_required
def insumo_detalle(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)
    movimientos = insumo.movimientos.select_related("pedido", "registrado_por")[:30]
    return render(
        request, "core/insumo_detalle.html", {"insumo": insumo, "movimientos": movimientos}
    )


# ---------------------------------------------------------------------------
# Pedidos + Kanban
# ---------------------------------------------------------------------------
@login_required
def pedidos(request):
    qs = Pedido.objects.select_related("cliente").prefetch_related("detalles__producto")
    estado = request.GET.get("estado")
    if estado:
        qs = qs.filter(estado=estado)
    search = request.GET.get("q")
    if search:
        qs = qs.filter(
            Q(numero__icontains=search)
            | Q(cliente__nombre__icontains=search)
            | Q(descripcion_diseño__icontains=search)
        )
    ctx = {
        "pedidos": qs,
        "estado_activa": estado or "",
        "q": search or "",
        "estados": Pedido.Estado.choices,
    }
    return render(request, "core/pedidos.html", ctx)


@login_required
def pedido_detalle(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related("cliente", "creador").prefetch_related(
            "detalles__producto", "movimientos__insumo"
        ),
        pk=pk,
    )
    return render(
        request,
        "core/pedido_detalle.html",
        {
            "pedido": pedido,
            "ingredientes": pedido.ingredientes_requeridos,
            "despacho": getattr(pedido, "despacho", None),
        },
    )


@login_required
@roles_required(COCINA, ADMIN)
def kanban(request):
    columnas = []
    for clave, etiqueta in Pedido.Estado.choices:
        pedidos = (
            Pedido.objects.filter(estado=clave)
            .select_related("cliente")
            .prefetch_related("detalles")
        )
        columnas.append({"clave": clave, "etiqueta": etiqueta, "pedidos": pedidos})
    return render(
        request,
        "core/kanban.html",
        {"columnas": columnas, "estados": Pedido.Estado.choices},
    )


@require_POST
@login_required
@roles_required(COCINA, ADMIN)
def kanban_mover(request, pk):
    """Mueve un pedido en el tablero Kanban (llamado por JS)."""
    pedido = get_object_or_404(Pedido, pk=pk)
    destino = request.POST.get("estado", "")
    paso = request.POST.get("paso", "")
    try:
        if paso == "descontar":
            pedido.descontar_insumos()
            messages.success(request, f"Insumos descontados para el pedido {pedido.numero}.")
        elif paso == "avanzar":
            pedido.avanzar_estado()
            messages.success(request, f"{pedido.numero} movido a {pedido.get_estado_display()}.")
        elif paso == "retroceder":
            pedido.retroceder_estado()
            messages.success(request, f"{pedido.numero} movido a {pedido.get_estado_display()}.")
        else:
            pedido.mover_a(destino)
            messages.success(request, f"{pedido.numero} movido a {pedido.get_estado_display()}.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect(request.META.get("HTTP_REFERER", "core:kanban"))


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
@login_required
def clientes(request):
    qs = Cliente.objects.all()
    search = request.GET.get("q")
    if search:
        qs = qs.filter(
            Q(nombre__icontains=search)
            | Q(email__icontains=search)
            | Q(telefono__icontains=search)
        )
    return render(request, "core/clientes.html", {"clientes": qs, "q": search or ""})


@login_required
def cliente_detalle(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    pedidos = cliente.pedidos.select_related("cliente").prefetch_related("detalles")
    return render(
        request, "core/cliente_detalle.html", {"cliente": cliente, "pedidos": pedidos}
    )


# ---------------------------------------------------------------------------
# Despachos
# ---------------------------------------------------------------------------
@login_required
def despachos(request):
    qs = Despacho.objects.select_related("pedido__cliente", "pedido")
    estado = request.GET.get("estado")
    if estado:
        qs = qs.filter(estado=estado)
    ctx = {
        "despachos": qs,
        "estado_activa": estado or "",
        "estados": Despacho.Estado.choices,
    }
    return render(request, "core/despachos.html", ctx)


@login_required
def despacho_detalle(request, pk):
    despacho = get_object_or_404(
        Despacho.objects.select_related("pedido__cliente", "pedido"), pk=pk
    )
    # Ver el despacho puede cualquier usuario autenticado, pero confirmar
    # la entrega (con firma) es responsabilidad del rol despacho/admin.
    puede_confirmar = user_tiene_rol(request.user, DESPACHO, ADMIN)
    if request.method == "POST" and not puede_confirmar:
        raise PermissionDenied("Solo el rol despacho o administración confirma entregas.")
    if request.method == "POST":
        recibido_por = request.POST.get("recibido_por", "").strip()
        firma = request.POST.get("firma_digital", "")
        observaciones = request.POST.get("observaciones", "")
        if not recibido_por:
            messages.error(request, "Debe indicar quién recibe el pedido.")
        else:
            try:
                despacho.confirmar_entrega(
                    recibido_por=recibido_por,
                    firma=firma,
                    observaciones=observaciones,
                )
                messages.success(
                    request,
                    f"Entrega del pedido {despacho.pedido.numero} confirmada con firma digital.",
                )
                return redirect("core:despacho_detalle", pk=despacho.pk)
            except Exception as e:
                messages.error(request, str(e))
    return render(
        request,
        "core/despacho_detalle.html",
        {"despacho": despacho, "puede_confirmar": puede_confirmar},
    )


# ---------------------------------------------------------------------------
# Ayuda / referencia
# ---------------------------------------------------------------------------
def referencia(request):
    """Página de referencia de diseño (no requiere sesión)."""
    return render(request, "core/referencia.html")
