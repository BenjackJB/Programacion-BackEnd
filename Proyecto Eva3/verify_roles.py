"""
Verificación de control de acceso por rol (EVA 3 · Dulce Arte).

Corre contra la BD local de desarrollo:
    python verify_roles.py

Cubre:
  * anónimo -> redirección a login
  * ventas  -> 403 en Kanban (web y API) y en confirmar entrega
  * cocina  -> Kanban OK, avanza/retrocede pedidos (símetro, sin efectos)
  * despacho-> ver despachos OK, confirmar entrega pasa el filtro de rol
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dulce_arte.settings")
django.setup()

from django.conf import settings  # noqa: E402

settings.ALLOWED_HOSTS.append("testserver")  # host del test client

from django.test import Client  # noqa: E402

from core.models import Despacho, Pedido  # noqa: E402

USERS = {
    "admin": "admin1234",
    "cocina": "demo1234",
    "despacho": "demo1234",
    "ventas": "demo1234",
}

ok = fail = 0


def check(nombre, obtenido, esperado):
    global ok, fail
    if obtenido == esperado:
        ok += 1
        print(f"  [OK]   {nombre}: {obtenido}")
    else:
        fail += 1
        print(f"  [FALLO] {nombre}: obtenido {obtenido}, esperado {esperado}")


def cliente(username):
    c = Client()
    assert c.login(username=username, password=USERS[username]), f"login {username}"
    return c


print("=== 1. Anónimo ===")
anon = Client()
r = anon.get("/kanban/")
check("GET /kanban/ anónimo", r.status_code, 302)
check("POST /api/pedidos/1/avanzar/ anónimo", anon.post("/api/pedidos/1/avanzar/").status_code, 403)

print("=== 2. Rol VENTAS (restringido) ===")
v = cliente("ventas")
check("GET /kanban/ -> 403", v.get("/kanban/").status_code, 403)
check("POST /kanban/1/mover/ -> 403", v.post("/kanban/1/mover/", {"paso": "avanzar"}).status_code, 403)
check("GET /api/reportes/kanban/ -> 403", v.get("/api/reportes/kanban/").status_code, 403)
check("GET /api/pedidos/ -> 200 (lectura OK)", v.get("/api/pedidos/").status_code, 200)
check("GET /insumos/ -> 200 (lectura OK)", v.get("/insumos/").status_code, 200)

# Confirmar entrega como ventas -> 403 (cualquier despacho sirve)
d_ok = Despacho.objects.filter(estado=Despacho.Estado.ENTREGADO).first() or Despacho.objects.first()
r = v.post(f"/despachos/{d_ok.pk}/", {"recibido_por": "X", "firma_digital": ""})
check("POST confirmar entrega (ventas) -> 403", r.status_code, 403)
r = v.post(f"/api/despachos/{d_ok.pk}/confirmar-entrega/", {"recibido_por": "X"}, content_type="application/json")
check("API confirmar-entrega (ventas) -> 403", r.status_code, 403)

print("=== 3. Rol COCINA (autorizado en Kanban) ===")
c = cliente("cocina")
check("GET /kanban/ -> 200", c.get("/kanban/").status_code, 200)
check("GET /api/reportes/kanban/ -> 200", c.get("/api/reportes/kanban/").status_code, 200)

# Avanzar y retroceder un pedido (símetro: vuelve al estado original)
pedido = (
    Pedido.objects.exclude(estado=Pedido.Estado.LISTO)
    .exclude(estado=Pedido.Estado.RECIBIDO)  # necesitamos que pueda retroceder
    .first()
)
if pedido:
    estado_inicial = pedido.estado
    r = c.post(f"/api/pedidos/{pedido.pk}/retroceder/")
    check("API retroceder (cocina) -> 200", r.status_code, 200)
    r = c.post(f"/api/pedidos/{pedido.pk}/avanzar/")
    check("API avanzar (cocina) -> 200", r.status_code, 200)
    pedido.refresh_from_db()
    check("estado original restaurado", pedido.estado, estado_inicial)
else:
    print("  [AVISO] sin pedidos intermedios para probar avanzar/retroceder")

print("=== 4. Rol DESPACHO ===")
d = cliente("despacho")
check("GET /despachos/ -> 200", d.get("/despachos/").status_code, 200)
check("GET /kanban/ -> 403", d.get("/kanban/").status_code, 403)

# Un despacho ya entregado: el filtro de rol pasa (no es 403), falla la regla de negocio
d_ent = Despacho.objects.filter(estado=Despacho.Estado.ENTREGADO).first()
if d_ent:
    r = d.post(f"/despachos/{d_ent.pk}/", {"recibido_por": "X"})
    check("POST confirmar entrega ya entregado (despacho) -> NO es 403", r.status_code != 403, True)
    r = d.post(
        f"/api/despachos/{d_ent.pk}/confirmar-entrega/",
        {"recibido_por": "X"},
        content_type="application/json",
    )
    check("API confirmar-entrega ya entregado (despacho) -> NO es 403", r.status_code != 403, True)
else:
    print("  [AVISO] sin despachos entregados para probar el paso de rol")

print("=== 5. Rol ADMIN (todo) ===")
a = cliente("admin")
check("GET /kanban/ -> 200", a.get("/kanban/").status_code, 200)
check("GET /api/reportes/kanban/ -> 200", a.get("/api/reportes/kanban/").status_code, 200)
check("GET /despachos/ -> 200", a.get("/despachos/").status_code, 200)

print("=== 6. Django Admin: changelists de todos los modelos ===")
from django.contrib.admin.sites import site  # noqa: E402
from django.urls import reverse  # noqa: E402

for model in site._registry:
    opts = model._meta
    url = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
    check(f"admin {opts.app_label}.{opts.model_name}", a.get(url).status_code, 200)

print()
print(f"RESULTADO: {ok} OK, {fail} FALLOS")
sys.exit(1 if fail else 0)
