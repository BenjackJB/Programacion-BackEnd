# 🍰 Dulce Arte — Sistema de Trazabilidad y Pedidos para Pastelería Artesanal

> **Evaluación Parcial N°3 · Desarrollo Backend** — Aplicación web fullstack con **Django + Django REST Framework**, **PostgreSQL** y despliegue en **AWS EC2**.

🌐 **Aplicación en línea:** `http://<IP_ELÁSTICA>/` *(se completa el domingo al asignar la IP elástica)*

🖥️ **Django Admin:** `http://<IP_ELÁSTICA>/django-admin/`
🔌 **API REST:** `http://<IP_ELÁSTICA>/api/`

---

## 📋 Índice

1. [Descripción del problema](#-descripción-del-problema)
2. [Requerimientos cubiertos](#-requerimientos-cubiertos)
3. [Stack tecnológico](#-stack-tecnológico)
4. [Modelo de datos](#-modelo-de-datos)
5. [Funcionalidades](#-funcionalidades)
6. [Django Admin personalizado](#-django-admin-personalizado)
7. [API REST](#-api-rest)
8. [Usuarios de prueba](#-usuarios-de-prueba)
9. [Instalación local](#-instalación-local)
10. [Despliegue en AWS EC2](#-despliegue-en-aws-ec2)
11. [Diseño de interfaz](#-diseño-de-interfaz)
12. [Estructura del proyecto](#-estructura-del-proyecto)

---

## 🎯 Descripción del problema

**Dulce Arte** es una pastelería artesanal que necesita digitalizar su operación. Los pedidos llegan por teléfono y redes sociales, se anotan en cuadernos, el inventario de ingredientes se controla "de memoria" y los pedidos se pierden entre la cocina y el reparto.

El sistema resuelve:

- **Cotización y registro de pedidos personalizados** (diseño, ingredientes especiales, fecha de entrega).
- **Tablero Kanban** para seguir cada pedido desde que entra hasta que sale a reparto.
- **Descuento automático de inventario** según la lista de materiales (BOM) de cada producto.
- **Rutas de despacho** con **firma digital** y comprobante de entrega.
- **Trazabilidad completa**: quién hizo qué y cuándo.

---

## ✅ Requerimientos cubiertos

| # | Requerimiento | Dónde está |
|---|---------------|------------|
| 1 | Cotización y registro de pedidos personalizados | `Pedido` + `DetallePedido` · vistas `/pedidos/` |
| 2 | Tablero Kanban con 5 estados (Recibido → En Preparación → Horneado/Decorado → Control de Calidad → Listo) | `/kanban/` · `Pedido.avanzar_estado()` |
| 3 | Descuento de inventario vía **BOM** (Bill of Materials) | `ComponenteProducto` · `Pedido.descontar_insumos()` |
| 4 | Rutas de despacho con **firma digital** / comprobante | `/despachos/` · `Despacho.confirmar_entrega()` |
| 5 | PostgreSQL como base de datos | `settings.py` (producción) |
| 6 | Django Admin personalizado con templates | `/django-admin/` · `core/admin.py` |
| 7 | CRUD completos | API DRF + vistas de plantilla |
| 8 | Seguridad y sesiones | `SessionAuthentication`, login/logout, roles |
| 9 | Despliegue en AWS EC2 | carpeta `deploy/` |

---

## 🛠 Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.11+ |
| Framework backend | Django 5.2 |
| API REST | Django REST Framework 3.16 |
| Base de datos | PostgreSQL 14+ (AWS) · SQLite (desarrollo local) |
| Servidor WSGI | Gunicorn |
| Servidor web / proxy | Nginx (proxy inverso + estáticos) |
| Infraestructura | AWS EC2 (Ubuntu 22.04 LTS, t2.micro) + IP elástica |
| Frontend | HTML/CSS/JS (Django templates) — sin frameworks pesados |
| Firma digital | Canvas HTML5 + JavaScript |

---

## 🗄 Modelo de datos

```
Categoria ──< Producto ──< ComponenteProducto >── Insumo ──< MovimientoInsumo
                                                        
Cliente ──< Pedido ──< DetallePedido >── Producto
              │
              └── 1:1 Despacho (firma digital / comprobante)

User ── 1:1 Perfil (rol: admin / cocina / despacho / ventas)
```

**Reglas de negocio clave:**

- **Kanban:** los estados siguen un orden fijo. Solo se puede avanzar o retroceder **un paso a la vez** (`mover_a()` valida esto).
- **BOM / inventario:** al marcar un pedido como **Listo** (o al pulsar "Descontar inventario"), se recorre la lista de materiales de cada producto y se descuentan los insumos multiplicando `cantidad_componente × cantidad_producto`. Cada descuento genera un **movimiento de kardex** trazable.
- **Stock bajo:** un insumo se marca "stock bajo" cuando `stock_actual <= stock_minimo`.
- **Firma digital:** la entrega requiere **firma dibujada en canvas** (guardada como base64) o un **comprobante** adjunto. No se puede confirmar la entrega sin uno de los dos.

---

## 🚀 Funcionalidades

### Frontend (vistas de plantilla)
- **Panel de control** con KPIs: pedidos, listos, ingresos, clientes, alertas de stock y pedidos atrasados.
- **Tablero Kanban** interactivo: arrastrar y soltar tarjetas + botones avanzar/retroceder.
- **Lista de pedidos** con filtros por estado y búsqueda.
- **Detalle de pedido**: diseño, productos, totales, ingredientes requeridos (BOM) y progreso.
- **Catálogo de productos** con ficha y desglose de BOM + costo y margen.
- **Inventario** con barra de nivel de stock, filtro "solo stock bajo" y **kardex** de movimientos.
- **Clientes** con ficha e historial de pedidos.
- **Despachos** con formulario de **firma digital** en canvas.

### API REST
CRUD completo para `categorias`, `insumos`, `productos`, `clientes`, `pedidos`, `detalles` y `despachos`, más acciones especiales (ver [API REST](#-api-rest)).

---

## 🎛 Django Admin personalizado

Ruta: **`/django-admin/`** (cambiada de `/admin/` para distinguir la API).

Implementa los 4 puntos de la rúbrica:

1. **`list_display`** con columnas calculadas y **badges de color** (estado, prioridad, stock).
2. **`list_filter`** y **`search_fields`**, incluido un filtro personalizado `SimpleListFilter` de "nivel de stock".
3. **`fieldsets`** organizados por secciones e **`inlines`** (BOM dentro de Producto, detalles dentro de Pedido, perfil dentro de Usuario).
4. **`actions`** personalizadas: *Avanzar/Retroceder Kanban*, *Descuento de insumos por BOM*, *Reponer stock*.

También se personalizaron los títulos del admin (`site_header`, `site_title`, `index_title`).

---

## 🔌 API REST

Base: **`/api/`** — requiere sesión (login) o autenticación básica.

### Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/POST | `/api/productos/` | Listar y crear productos |
| GET/POST | `/api/insumos/` | Listar y crear insumos |
| POST | `/api/insumos/{id}/reponer/` | Reponer stock de un insumo |
| GET/POST | `/api/pedidos/` | Listar y crear pedidos |
| POST | `/api/pedidos/{id}/avanzar/` | Avanzar estado Kanban |
| POST | `/api/pedidos/{id}/retroceder/` | Retroceder estado Kanban |
| POST | `/api/pedidos/{id}/mover/` | Mover a un estado específico |
| GET | `/api/pedidos/{id}/ingredientes/` | Insumos requeridos (BOM) |
| POST | `/api/pedidos/{id}/descontar-insumos/` | Descontar inventario por BOM |
| GET | `/api/despachos/` | Listar despachos |
| POST | `/api/despachos/{id}/confirmar-entrega/` | Confirmar entrega con firma |
| GET | `/api/reportes/kanban/` | Pedidos agrupados por columna |
| GET | `/api/reportes/dashboard/` | KPIs del panel |
| POST | `/api/auth/login/` | Iniciar sesión |
| POST | `/api/auth/logout/` | Cerrar sesión |
| GET | `/api/auth/whoami/` | Usuario actual |

### Ejemplo con `curl`

```bash
# Login (guarda la cookie de sesión)
curl -c cookies.txt -X POST http://IP/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin1234"}'

# Listar pedidos
curl -b cookies.txt http://IP/api/pedidos/

# Avanzar un pedido en el Kanban
curl -b cookies.txt -X POST http://IP/api/pedidos/1/avanzar/
```

---

## 👥 Usuarios de prueba

Creados por `setup_demo.py`:

| Usuario | Contraseña | Rol | Acceso |
|---------|-----------|-----|--------|
| `admin` | `admin1234` | Administración | Admin + todo |
| `cocina` | `demo1234` | Cocina | Pedidos, Kanban |
| `despacho` | `demo1234` | Despacho | Despachos, firma |
| `ventas` | `demo1234` | Ventas | Clientes, pedidos |

> ⚠ En producción, cambia estas contraseñas antes de exponer la instancia.

---

## 💻 Instalación local

```bash
# 1. Clonar el repositorio
git clone <URL_DEL_REPO>
cd <carpeta_del_proyecto>

# 2. Entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Configurar entorno (opcional en local — usa SQLite si no hay DATABASE_URL)
cp .env.example .env

# 5. Migraciones + datos demo
python manage.py migrate
python manage.py setup_demo.py

# 6. Ejecutar
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/` e iniciar sesión con `admin` / `admin1234`.

> En local se usa **SQLite** automáticamente si no defines `DATABASE_URL`. En AWS se usa **PostgreSQL**.

---

## ☁ Despliegue en AWS EC2

### ETAPA 1 — Lanzar la instancia

1. Consola AWS → **EC2** → *Lanzar instancia*.
2. **AMI:** Ubuntu Server 22.04 LTS (x64).
3. **Tipo:** `t2.micro` (capa gratuita).
4. **Key Pair:** crea o usa uno existente (`claves.pem`).
5. **Red:** usa la VPC por defecto y **habilita IP pública automática**.
6. **Grupo de seguridad:** abre **SSH (22)** desde tu IP y **HTTP (80)** desde cualquier IP.
7. Crea la instancia.

### ETAPA 2 — Conectarte (desde Windows)

```bash
# Proteger la clave (PowerShell)
mkdir C:\AWS_KEYS
copy "C:\Users\<TU_USUARIO>\Downloads\claves.pem" C:\AWS_KEYS\
icacls "C:\AWS_KEYS\claves.pem" /inheritance:r
icacls "C:\AWS_KEYS\claves.pem" /grant:r "%username%:R"

# Conectar
cd C:\AWS_KEYS
ssh -i "claves.pem" ubuntu@<TU_IP_PUBLICA>
```

### ETAPA 3 — Clonar el proyecto

```bash
sudo apt update && sudo apt upgrade -y
mkdir -p ~/apps && cd ~/apps
git clone <URL_DEL_REPO> .
```

### ETAPA 4 — Configurar todo con un solo script

```bash
chmod +x deploy/configurar_servidor.sh
sudo ./deploy/configurar_servidor.sh
```

El script instala Python, Nginx y PostgreSQL; crea la base de datos; genera el `.env`; aplica migraciones; siembra datos; recopila estáticos; y arranca **Gunicorn** + **Nginx**.

### ETAPA 5 — Asignar la IP elástica *(domingo en la noche)*

1. Consola AWS → **EC2** → *IP elásticas* → *Asignar IP elástica* → **Asociar** con tu instancia.
2. Edita el `.env` con la IP nueva:

```bash
sudo nano ~/apps/.env
```

```
ALLOWED_HOSTS=localhost,127.0.0.1,<TU_IP_ELASTICA>
PUBLIC_HOST=<TU_IP_ELASTICA>
```

3. Reinicia los servicios:

```bash
sudo systemctl restart gunicorn && sudo systemctl restart nginx
```

4. Abre `http://<TU_IP_ELASTICA>/` 🎉

### Actualizar el despliegue (cuando hagas `git pull`)

```bash
cd ~/apps
git pull
./deploy/actualizar.sh
```

### Precios de insumos en CLP

Los precios de referencia viven en `core/precios_referencia.py` (pesos chilenos
por kilo, litro, mililitro o unidad, según la unidad del insumo). Si la base ya
tiene datos con precios en otra escala, se corrigen sin volver a sembrar:

```bash
python manage.py precios_clp --dry-run   # ver qué cambiaría
python manage.py precios_clp             # aplicar + resumen de márgenes
```

Es idempotente y no toca pedidos, stock ni kardex; sirve igual en SQLite local y
en PostgreSQL de la EC2 (ejecútalo dentro del `venv` del servidor).

### Solución de problemas

| Error | Causa probable | Solución |
|-------|----------------|----------|
| `502 Bad Gateway` | Socket no creado | Revisar `gunicorn.service` y reiniciar |
| `(13) Permission denied` | Permisos del socket | `chown ubuntu:www-data` + `chmod 660` |
| `(2) No such file` | Ruta del socket incorrecta | Verificar `proxy_pass` en Nginx |
| `(111) Connection refused` | Gunicorn no corre | `sudo systemctl restart gunicorn` |
| Página sin estilos | Estáticos no recopilados | `python manage.py collectstatic` |

Verificar permisos del árbol de carpetas:

```bash
namei -l /home/ubuntu/apps/dulce_arte.sock
```

---

## 🎨 Diseño de interfaz

La interfaz sigue el design system **"Beautiful™"** (estilo minimalista editorial):

- **Lienzo crema** `#fff5e6` · **coral** `#fa7864` (un acento por pantalla) · **terracota** `#dc8264`
- **Bordes negros de 1px**, botones tipo **pill** (`border-radius: 999px`)
- Tipografía: **Instrument Serif** (titulares) + **Space Grotesk** (cuerpo) + **JetBrains Mono** (metadatos y números)
- "Eyebrow" en mayúsculas mono coral con amplio *letter-spacing*

La página `/referencia/` muestra la paleta y componentes del sistema de diseño.

---

## 📁 Estructura del proyecto

```
.
├── dulce_arte/            # Proyecto Django (settings, urls, wsgi)
├── core/                  # App principal: modelos, admin, vistas, tags
│   ├── models.py          #   10 modelos del dominio
│   ├── admin.py           #   Django Admin personalizado
│   ├── views.py           #   Vistas de plantilla
│   ├── urls.py
│   └── templatetags/      #   Filtros de plantilla (badges)
├── api/                   # App de la API REST
│   ├── serializers.py
│   ├── views.py           #   ViewSets + acciones
│   └── urls.py
├── templates/core/        # Plantillas HTML
├── static/                # CSS y JS del frontend
├── deploy/                # Configuración de despliegue AWS
│   ├── configurar_servidor.sh   # Setup completo del servidor
│   ├── actualizar.sh            # Actualización tras git pull
│   ├── gunicorn.service         # Servicio systemd
│   └── nginx_dulce_arte         # Configuración de Nginx
├── requirements.txt
├── .env.example
├── setup_demo.py          # Siembra de datos demo
├── smoke_test.py          # Verificación de rutas
└── prompts_ia.md          # Registro de uso de IA
```

---

## 📄 Licencia

Proyecto académico — Evaluación Parcial N°3 · Desarrollo Backend · Inacap.

**Dulce Arte** 🍰 — *Cada pedido tiene su historia: del batido a la puerta.*
