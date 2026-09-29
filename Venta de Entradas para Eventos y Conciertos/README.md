# Venta de Entradas para Eventos y Conciertos

Plataforma de boletería para eventos masivos construida con **Django + Django REST Framework**,
autenticación **JWT por roles**, **PostgreSQL** y documentación **Swagger/OpenAPI**.

**Alumno:** Benjamin Jaque • **Sección:** IEC-N4-C2 • **Año:** 2026

---

## Roles

| Rol | Permisos |
| --- | --- |
| **Espectador** | Consultar el catálogo, armar su *Reserva Temporal de Entradas* (carro persistente), pagar y ver sus entradas. |
| **Organizador** | Registrar recintos/sectores, crear/editar/desactivar eventos, consultar las ventas y cambiar el estado de las órdenes (ENTREGADO / CANCELADO). |

## Puesta en marcha

```bash
pip install -r requirements.txt

# PostgreSQL (motor por defecto): crear la base y exportar las variables de .env.example
createdb venta_entradas
python manage.py migrate
python manage.py seed_data          # datos de demostración
python manage.py runserver
```

Sin PostgreSQL (solo desarrollo local):

```powershell
$env:DB_ENGINE='sqlite'
python manage.py migrate
python manage.py runserver
```

Usuarios de la semilla:

* `organizador` / `organizador123` (Organizador)
* `espectador` / `espectador123` (Espectador)

## Pantallas

* `/eventos/` – catálogo público con filtros (categoría, rango de precios, fechas, estado) y búsqueda.
* `/eventos/{id}/` – detalle del evento y sus sectores/localidades.
* `/login/`, `/registro/` – autenticación JWT con claims de rol.
* `/carro/` – carro de compras persistente (1 a 1 con el usuario).
* `/mis-entradas/` – entradas emitidas con código Hash/UUID.
* `/organizador/eventos/` – alta/edición/baja de eventos y sectores.
* `/organizador/ventas/` – ventas, detalle de órdenes y cambio de estado.
* `/docs/` – documentación Swagger (enlazada desde el pie de página de cada pantalla).

Todas las pantallas muestran en el pie: **Benjamin Jaque • IEC-N4-C2 • 2026**.

## Endpoints del API (internos, JSON)

* **Público:** `GET /api/eventos/`, `GET /api/eventos/{id}/sectores/`
* **Espectador:** `GET|POST|DELETE /api/carro-tickets/`, `POST /api/compras/pagar/`, `GET /api/mis-entradas/`
* **Organizador:** `POST|PUT|DELETE /api/eventos/`, `PATCH /api/compras/{id}/estado/`
* **Auth:** `POST /api/token/`, `POST /api/token/refresh/`, `POST /api/registro/`

## Reglas de negocio

* El stock **no** se descuenta al agregar al carro: se descuenta **solo** cuando la orden pasa a **PAGADO**.
* Si el stock es insuficiente al pagar, la transacción se rechaza completa (rollback).
* Al pasar a **CANCELADO** se repone el stock y se anulan los tickets; **ENTREGADO** marca la asistencia.
* Esos efectos los aplican las **señales** de `boletos/signals.py` dentro de la misma transacción (rollback si algo falla).
* El carro vive en PostgreSQL: conserva sus ítems al cerrar sesión o entrar desde otro dispositivo.

## Estructura

```
boletos_project/     settings, urls, wsgi/asgi (sin admin de Django)
boletos/
  models.py          User(rol), Recinto, Evento, Sector, Carro, CarroItem,
                     Compra, CompraHistorial, Ticket (CHOICES + FKs)
  api_views.py       Endpoints JSON (DRF + permisos por rol)
  views.py           Vistas HTML (templates)
  serializers.py     Serializadores y token JWT con claim `rol`
  permissions.py     Permisos personalizados (EsOrganizador / EsEspectador)
  filters.py         django-filter (categoría, precios, fechas, estado)
  services.py        Checkout: orden y pago (los efectos van por señal)
  signals.py         SEÑALES: descuento/emisión al PAGADO, reposición y
                     anulación al CANCELADO, asistencia al ENTREGADO
  templates/boletos/ Plantillas (base con pie de página y footer a /docs/)
  static/js/         Núcleo JWT + lógica de cada pantalla
```

## Pruebas

```powershell
$env:DB_ENGINE='sqlite'; python manage.py test boletos
```

58 pruebas: JWT y claims de rol, permisos por rol, filtros, carro persistente,
ciclo de vida de la orden con stock, SEÑALES de transición, vistas HTML,
pie de página y ausencia de admin/API navegable.
