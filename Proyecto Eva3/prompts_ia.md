# 🤖 Registro de uso de Inteligencia Artificial — Dulce Arte

> **Evaluación Parcial N°3 · Desarrollo Backend** — Este documento registra cómo se utilizó inteligencia artificial como **herramienta de apoyo** al desarrollo del proyecto, siguiendo el criterio de evaluación: *"Utiliza herramientas de inteligencia artificial como apoyo al desarrollo"*.

---

## 📌 Principio de uso

La IA se usó como **par programador** para acelerar tareas repetitivas y resolver dudas puntuales, pero **todas las decisiones de arquitectura, modelo de datos y reglas de negocio fueron revisadas, comprendidas y validadas** por el desarrollador. El código resultante se entiende, se mantendrá y se puede defender en la evaluación en vivo.

**Herramienta utilizada:** asistente de código basado en LLM (OpenCode / modelo de lenguaje).

---

## 🧭 Fases del proyecto y prompts usados

### Fase 1 — Análisis y planificación

**Prompt:**
> "Lee el enunciado de la Evaluación Parcial N°3 y extráeme los requerimientos funcionales, la rúbrica de evaluación y los entregables. Dame un plan de trabajo por fases."

**Uso de la IA:** Lectura del documento `EVA_3_Backend.docx`, extracción de requerimientos y elaboración de un plan de 6 fases. La IA ayudó a organizar, no a decidir el alcance.

**Aprendizaje:** Definir bien el alcance antes de codificar evita retrabajo.

---

### Fase 2 — Diseño del modelo de datos (dominio)

**Prompt:**
> "Necesito modelar una pastelería artesanal. Pedidos personalizados con diseño, tablero Kanban de 5 estados, inventario con lista de materiales (BOM) que descuente insumos, y despachos con firma digital. Propón los modelos de Django y explica las reglas de negocio."

**Uso de la IA:** Propuesta inicial de los modelos `Categoria`, `Producto`, `ComponenteProducto` (BOM), `Insumo`, `MovimientoInsumo` (kardex), `Cliente`, `Pedido`, `DetallePedido`, `Despacho` y `Perfil`.

**Validación del desarrollador:**
- Revisé y ajusté los `choices` de estados y unidades al contexto chileno.
- Implementé y verifiqué la **regla de BOM**: `cantidad_componente × cantidad_producto` sumando por insumo.
- Añadí las **constraints** de unicidad (`unico_producto_por_pedido`, etc.).
- Definí que el Kanban solo permite mover **un paso a la vez** (decisión de negocio mía).

---

### Fase 3 — Django Admin personalizado

**Prompt:**
> "Personaliza el admin de Django para los modelos del proyecto: quiero `list_display` con columnas calculadas, badges de color, `list_filter`, `search_fields`, `fieldsets`, `inlines` y `actions` personalizadas. Que cumpla la rúbrica."

**Uso de la IA:** Generación del `core/admin.py` con todos los componentes.

**Validación del desarrollador:**
- Corregí errores de configuración del admin (`admin.E116`, `admin.E122`) que la IA dejó al primer intento: `list_editable` debe referenciar campos de `list_display`.
- Implementé un **filtro personalizado** `StockBajoFilter` (hereda de `SimpleListFilter`) para cumplir el criterio de "filtros".
- Escribí las **acciones** de negocio (`avanzar_kanban`, `descontar_insumos`) entendiendo su lógica.

---

### Fase 4 — API REST (DRF)

**Prompt:**
> "Crea los serializers y viewsets de DRF para todos los modelos, con autenticación por sesión. Incluye acciones personalizadas para avanzar/retroceder el Kanban, descontar insumos por BOM, reponer stock y confirmar entrega con firma."

**Uso de la IA:** Estructura de `api/serializers.py`, `api/views.py` y `api/urls.py` con `DefaultRouter`.

**Validación del desarrollador:**
- Detecté y corregí un **error de la IA**: declarar `CharField(source="get_x_display")` causaba un `AttributeError` en bucle infinito. Lo cambié a `CharField(read_only=True)`.
- Cambié `registrado_por_nombre` a `SerializerMethodField` para manejar el caso `None`.
- Probé cada endpoint con un **smoke test** (`smoke_test.py`) que verifica 33 rutas — todas responden 200 tras login.

---

### Fase 5 — Frontend e interfaz de usuario

**Prompt:**
> "Quiero que el diseño de la página sea como este estilo de Refero (Beautiful™): lienzo crema, un acento coral por pantalla, bordes negros de 1px, botones pill, tipografía serif + sans + mono. Diseña el CSS y las plantillas del panel, Kanban, pedidos, inventario y despachos."

**Uso de la IA:** Captura de la paleta y tipografía del sitio de referencia, y generación de `static/css/app.css` (design system) + 15 plantillas HTML.

**Validación del desarrollador:**
- Ajusté manualmente el **layout del Kanban**: el botón "Avanzar" se comprimía en columnas angostas. Lo reestructuré a "Avanzar a ancho completo + ←/Ver debajo".
- Verifiqué visualmente cada página en el navegador y corregí detalles de `flex-wrap` y desbordes.
- Implementé el **signature pad** en canvas con JavaScript vanilla y su persistencia en base64.

---

### Fase 6 — Despliegue en AWS

**Prompt:**
> "Adapta la receta de despliegue AWS (Gunicorn + Nginx + DRF) a este proyecto con PostgreSQL. Genera el servicio systemd, la configuración de Nginx y un script que automatice la instalación del servidor."

**Uso de la IA:** Generación de `deploy/gunicorn.service`, `deploy/nginx_dulce_arte`, `deploy/configurar_servidor.sh` y `deploy/actualizar.sh`.

**Validación del desarrollador:**
- Revisé la resolución de **permisos del socket** (grupos `www-data`/`ubuntu`, `chmod 750/770/660`) incluida en la receta original.
- Añadí `collectstatic` y el bloque `location /static/` en Nginx para que el admin y el frontend carguen sus estilos.
- Configuré la lectura de variables desde `.env` y desde `EnvironmentFile=` de systemd.

---

### Fase 7 — Documentación

**Prompt:**
> "Redacta el README con descripción, requerimientos, stack, modelo de datos, instrucciones de instalación local y pasos de despliegue en AWS. Deja un placeholder para la IP elástica."

**Uso de la IA:** Redacción inicial del `README.md` y de este registro.

---

## 🧠 Qué aprendí usando IA

1. **La IA acelera, pero no reemplaza la revisión.** Varias veces propuso código que no corría a la primera (errores de DRF, errores de `admin.E122`). Aprender a **leer los errores y depurarlos** fue clave.
2. **Formular buenos prompts importa.** Pedir "explícame el por qué" además del código produjo soluciones más sólidas.
3. **Verificar con tests.** El `smoke_test.py` me dio confianza de que ningún endpoint se rompió tras cada cambio.
4. **Entender el dominio es lo primero.** La IA modela lo que se le pide; las reglas de negocio (BOM, Kanban, firma) las definí yo.

---

## ✅ Declaración

El uso de inteligencia artificial en este proyecto fue **como herramienta de apoyo al desarrollo**, conforme al aprendizaje esperado de la asignatura. Todo el código fue revisado, entendido, probado y es defendible por el desarrollador en la presentación en vivo.

---

*Dulce Arte — EVA 3 · Desarrollo Backend · Inacap*
