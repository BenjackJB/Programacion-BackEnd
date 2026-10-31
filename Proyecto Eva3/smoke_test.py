"""Smoke test: verifica que todas las rutas respondan 200/302 tras login."""
import os
import sys
import urllib.request
import urllib.parse
import http.cookiejar

BASE = "http://127.0.0.1:8000"

RUTAS = [
    ("/login/", "GET"),
    ("/referencia/", "GET"),
    ("/", "GET"),
    ("/productos/", "GET"),
    ("/insumos/", "GET"),
    ("/pedidos/", "GET"),
    ("/kanban/", "GET"),
    ("/clientes/", "GET"),
    ("/despachos/", "GET"),
    ("/api/auth/whoami/", "GET"),
    ("/api/reportes/dashboard/", "GET"),
    ("/api/reportes/kanban/", "GET"),
    ("/api/pedidos/", "GET"),
    ("/api/insumos/", "GET"),
    ("/api/productos/", "GET"),
    ("/django-admin/", "GET"),
]

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def get_csrf(path):
    opener.open(BASE + path)
    for c in cj:
        if c.name == "csrftoken":
            return c.value
    return ""


def login():
    token = get_csrf("/login/")
    data = urllib.parse.urlencode(
        {"username": "admin", "password": "admin1234", "csrfmiddlewaretoken": token}
    ).encode()
    req = urllib.request.Request(
        BASE + "/login/",
        data=data,
        headers={"Referer": BASE + "/login/", "Cookie": f"csrftoken={token}"},
    )
    try:
        opener.open(req)
        return True
    except urllib.error.HTTPError as e:
        print(f"  login falló: {e}")
        return False


def main():
    print("== Smoke test ==")
    ok = fail = 0

    # Sin sesión: deben redirigir a login
    for ruta, metodo in RUTAS[:6]:
        try:
            resp = opener.open(BASE + ruta)
            code = resp.getcode()
            final = resp.geturl()
            estado = "OK" if code == 200 else f"HTTP {code}"
            if "/login/" in final and ruta != "/login/" and ruta != "/referencia/":
                estado = "REDIRIGE (esperado)"
            print(f"  {estado:24} {ruta}")
            ok += 1
        except urllib.error.HTTPError as e:
            print(f"  FAIL {e.code:4} {ruta}")
            fail += 1

    if not login():
        sys.exit(1)
    print("  sesión iniciada como admin\n")

    for ruta, metodo in RUTAS:
        try:
            resp = opener.open(BASE + ruta)
            code = resp.getcode()
            print(f"  OK   {code:4} {ruta}")
            ok += 1
        except urllib.error.HTTPError as e:
            print(f"  FAIL {e.code:4} {ruta}")
            fail += 1

    # Detalles con IDs reales
    from setup_helpers import ids

    print()
    for ruta in ids():
        try:
            resp = opener.open(BASE + ruta)
            print(f"  OK   {resp.getcode():4} {ruta}")
            ok += 1
        except urllib.error.HTTPError as e:
            print(f"  FAIL {e.code:4} {ruta}")
            fail += 1

    print(f"\nResultado: {ok} OK, {fail} fallos")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
