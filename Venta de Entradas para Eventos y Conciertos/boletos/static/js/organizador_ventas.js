/**
 * organizador_ventas.js — Ventas y órdenes del organizador.
 *
 * Lógica principal:
 * - GET /api/compras/ con filtros (estado, evento, fecha_desde, fecha_hasta,
 *   search) y paginación; resumen de la página actual calculado en cliente.
 * - Select de eventos propios: GET /api/eventos/?organizador=<id>&page_size=100
 * - "Ver detalle": GET /api/compras/{id}/ (datos, tickets e historial).
 * - "Entregar": PATCH /api/compras/{id}/estado/ {estado: 'ENTREGADO'}.
 * - "Cancelar": prompt de observación + confirm y
 *   PATCH /api/compras/{id}/estado/ {estado: 'CANCELADO', observacion}.
 * Tras cada cambio de estado se recarga la tabla.
 */

(function () {
    'use strict';

    const vista = document.getElementById('vistaVentas');
    if (!vista) return; // El script solo aplica en organizador_ventas.html

    const ORGANIZADOR = Number(vista.dataset.organizador || 0);
    const PAGE_SIZE = 10;
    const API_COMPRAS = '/api/compras/';

    // =========================================================================
    // ESTADO DE LA PANTALLA
    // =========================================================================

    let pagina = 1;
    let cacheCompras = new Map(); // id -> orden (para acciones de fila)
    const filtros = { estado: '', evento: '', fecha_desde: '', fecha_hasta: '', search: '' };

    // =========================================================================
    // REFERENCIAS DOM
    // =========================================================================

    const tablaCompras = document.getElementById('tablaCompras');
    const paginacionCompras = document.getElementById('paginacionCompras');
    const contadorCompras = document.getElementById('contadorCompras');

    const filtroEstado = document.getElementById('filtroEstado');
    const filtroEvento = document.getElementById('filtroEvento');
    const filtroDesde = document.getElementById('filtroDesde');
    const filtroHasta = document.getElementById('filtroHasta');
    const filtroBuscar = document.getElementById('filtroBuscar');

    const detalleCargando = document.getElementById('detalleCargando');
    const detalleContenido = document.getElementById('detalleContenido');
    // Plantilla original del estado "cargando" (se restaura en cada apertura).
    const PLANTILLA_CARGANDO = detalleCargando.innerHTML;

    // =========================================================================
    // UTILIDADES
    // =========================================================================

    function cargandoTabla() {
        tablaCompras.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted py-4">
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Cargando órdenes...
                </td>
            </tr>`;
    }

    /** Rellena las 4 tarjetas de resumen con la página actual. */
    function pintarResumen(resultados, total) {
        let montoPagado = 0;
        let entregadas = 0;
        let canceladas = 0;

        resultados.forEach((orden) => {
            if (orden.estado === 'PAGADO') montoPagado += Number(orden.total || 0);
            if (orden.estado === 'ENTREGADO') entregadas += 1;
            if (orden.estado === 'CANCELADO') canceladas += 1;
        });

        document.getElementById('resTotal').textContent = total || 0;
        document.getElementById('resMonto').textContent = Boletos.fmtMoney(montoPagado);
        document.getElementById('resEntregadas').textContent = entregadas;
        document.getElementById('resCanceladas').textContent = canceladas;
    }

    function filaCompra(orden) {
        const codigoCorto = String(orden.codigo || '').slice(0, 8);

        const acciones = `
            <div class="d-flex flex-wrap gap-1 justify-content-end">
                <button type="button" class="btn btn-sm btn-outline-primary btn-action"
                        data-detalle="${orden.id}" data-bs-toggle="modal" data-bs-target="#modalDetalle"
                        title="Ver detalle" aria-label="Ver detalle de la orden ${Boletos.esc(codigoCorto)}">
                    <i class="bi bi-eye" aria-hidden="true"></i>Ver detalle
                </button>
                ${orden.estado === 'PAGADO'
                    ? `<button type="button" class="btn btn-sm btn-outline-success btn-action"
                               data-entregar="${orden.id}" title="Marcar como entregada"
                               aria-label="Entregar orden ${Boletos.esc(codigoCorto)}">
                           <i class="bi bi-check2-circle" aria-hidden="true"></i>Entregar
                       </button>`
                    : ''}
                ${orden.estado === 'PENDIENTE' || orden.estado === 'PAGADO'
                    ? `<button type="button" class="btn btn-sm btn-outline-danger btn-action"
                               data-cancelar="${orden.id}" title="Cancelar orden"
                               aria-label="Cancelar orden ${Boletos.esc(codigoCorto)}">
                           <i class="bi bi-x-circle" aria-hidden="true"></i>Cancelar
                       </button>`
                    : ''}
            </div>`;

        return `
            <tr>
                <td class="codigo-mono">${Boletos.esc(codigoCorto)}</td>
                <td>${Boletos.esc(orden.comprador_nombre)}</td>
                <td class="text-nowrap">${Boletos.fmtFecha(orden.fecha_creacion, true)}</td>
                <td>${Number(orden.cantidad_tickets || 0)}</td>
                <td class="fw-semibold text-nowrap">${Boletos.fmtMoney(orden.total)}</td>
                <td class="text-nowrap">${Boletos.badgeEstado(orden.estado)}</td>
                <td class="text-end">${acciones}</td>
            </tr>`;
    }

    /** GET /api/compras/ con los filtros aplicados y la página actual. */
    async function cargarCompras() {
        cargandoTabla();
        try {
            const datos = await Boletos.apiGet(API_COMPRAS, Object.assign({}, filtros, {
                page: pagina,
                page_size: PAGE_SIZE,
            }));

            const resultados = Array.isArray(datos.results) ? datos.results : [];
            resultados.forEach((orden) => cacheCompras.set(orden.id, orden));

            contadorCompras.textContent = `${datos.count || 0}`;
            pintarResumen(resultados, datos.count || 0);

            if (!resultados.length) {
                tablaCompras.innerHTML = `<tr><td colspan="7">${
                    Boletos.estadoVacio('bi-receipt', 'Sin órdenes',
                        'No hay órdenes que coincidan con los filtros seleccionados.')
                }</td></tr>`;
            } else {
                tablaCompras.innerHTML = resultados.map(filaCompra).join('');
            }

            const totalPaginas = Math.max(1, Math.ceil((datos.count || 0) / PAGE_SIZE));
            paginacionCompras.innerHTML = Boletos.paginacion(datos, pagina, totalPaginas);
        } catch (err) {
            Boletos.toast('danger', err.message);
            tablaCompras.innerHTML = `<tr><td colspan="7">${
                Boletos.estadoVacio('bi-exclamation-triangle', 'No se pudieron cargar las órdenes',
                    Boletos.esc(err.message))
            }</td></tr>`;
            paginacionCompras.innerHTML = '';
        }
    }

    // =========================================================================
    // FILTROS
    // =========================================================================

    function aplicarFiltros() {
        filtros.estado = filtroEstado.value;
        filtros.evento = filtroEvento.value;
        filtros.fecha_desde = filtroDesde.value;
        filtros.fecha_hasta = filtroHasta.value;
        filtros.search = filtroBuscar.value.trim();
        pagina = 1;
        cargarCompras();
    }

    document.getElementById('btnFiltrar').addEventListener('click', aplicarFiltros);

    document.getElementById('btnLimpiar').addEventListener('click', () => {
        filtroEstado.value = '';
        filtroEvento.value = '';
        filtroDesde.value = '';
        filtroHasta.value = '';
        filtroBuscar.value = '';
        aplicarFiltros();
    });

    filtroBuscar.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') { ev.preventDefault(); aplicarFiltros(); }
    });

    // Paginación generada por Boletos.paginacion (data-pagina).
    paginacionCompras.addEventListener('click', (ev) => {
        const enlace = ev.target.closest('[data-pagina]');
        if (!enlace) return;
        ev.preventDefault();
        pagina = Number(enlace.dataset.pagina) || 1;
        cargarCompras();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // =========================================================================
    // ACCIONES SOBRE LAS FILAS (delegación: se pintan dinámicamente)
    // =========================================================================

    tablaCompras.addEventListener('click', (ev) => {
        const btn = ev.target.closest('button');
        if (!btn) return;
        if (btn.dataset.detalle) verDetalle(Number(btn.dataset.detalle));
        else if (btn.dataset.entregar) entregarOrden(Number(btn.dataset.entregar));
        else if (btn.dataset.cancelar) cancelarOrden(Number(btn.dataset.cancelar));
    });

    // =========================================================================
    // DETALLE DE LA ORDEN (modal)
    // =========================================================================

    function mostrarCargandoDetalle() {
        detalleCargando.innerHTML = PLANTILLA_CARGANDO;
        detalleCargando.classList.remove('d-none');
        detalleContenido.classList.add('d-none');
    }

    function pintarDetalle(orden) {
        document.getElementById('detCodigo').textContent = orden.codigo || '—';
        document.getElementById('detComprador').textContent = orden.comprador_nombre || orden.comprador || '—';
        document.getElementById('detTotal').textContent = Boletos.fmtMoney(orden.total);
        document.getElementById('detCreada').textContent = Boletos.fmtFecha(orden.fecha_creacion, true);
        document.getElementById('detPagada').textContent = Boletos.fmtFecha(orden.fecha_pago, true);
        document.getElementById('detEstado').innerHTML = Boletos.badgeEstado(orden.estado);

        // Observación: solo se muestra si existe.
        const contenedorObservacion = document.getElementById('contenedorObservacion');
        document.getElementById('detObservacion').textContent = orden.observacion || 'Sin observaciones.';
        contenedorObservacion.classList.toggle('d-none', !orden.observacion);

        // Tabla de tickets emitidos en la orden.
        const tickets = Array.isArray(orden.tickets) ? orden.tickets : [];
        const cuerpoTickets = document.getElementById('detalleTickets');
        if (!tickets.length) {
            cuerpoTickets.innerHTML = `<tr><td colspan="4">${
                Boletos.estadoVacio('bi-ticket-detailed', 'Sin entradas',
                    'Esta orden no tiene entradas emitidas.')
            }</td></tr>`;
        } else {
            cuerpoTickets.innerHTML = tickets.map((ticket) => `
                <tr>
                    <td class="codigo-mono">${Boletos.esc(ticket.codigo)}</td>
                    <td>${Boletos.esc(ticket.evento ? ticket.evento.nombre : '')}</td>
                    <td>${Boletos.esc(ticket.sector_nombre)}</td>
                    <td>${Boletos.badgeEstado(ticket.estado, Boletos.ESTADOS_TICKET)}</td>
                </tr>`).join('');
        }

        // Historial de cambios de estado de la orden.
        const historial = Array.isArray(orden.historial) ? orden.historial : [];
        const listaHistorial = document.getElementById('detalleHistorial');
        if (!historial.length) {
            listaHistorial.innerHTML = `<li class="list-group-item">${
                Boletos.estadoVacio('bi-clock-history', 'Sin historial',
                    'Aún no hay cambios de estado registrados.')
            }</li>`;
        } else {
            listaHistorial.innerHTML = historial.map((registro) => `
                <li class="list-group-item d-flex justify-content-between align-items-start flex-wrap gap-1">
                    <div>
                        <div>${Boletos.badgeEstado(registro.estado)}<span class="ms-2">${Boletos.esc(registro.usuario || 'sistema')}</span></div>
                        <div class="historial-fecha">${Boletos.fmtFecha(registro.fecha, true)}${registro.detalle ? ` · ${Boletos.esc(registro.detalle)}` : ''}</div>
                    </div>
                </li>`).join('');
        }

        detalleCargando.classList.add('d-none');
        detalleContenido.classList.remove('d-none');
    }

    async function verDetalle(id) {
        mostrarCargandoDetalle();
        try {
            const orden = await Boletos.apiGet(`${API_COMPRAS}${id}/`);
            pintarDetalle(orden);
        } catch (err) {
            Boletos.toast('danger', err.message);
            detalleCargando.innerHTML = Boletos.estadoVacio(
                'bi-exclamation-triangle', 'No se pudo cargar la orden', Boletos.esc(err.message));
        }
    }

    // =========================================================================
    // CAMBIO DE ESTADO: ENTREGAR Y CANCELAR
    // =========================================================================

    async function entregarOrden(id) {
        const orden = cacheCompras.get(id);
        if (!orden) return;
        const codigo = String(orden.codigo || '').slice(0, 8);
        if (!window.confirm(`¿Marcar la orden ${codigo} como ENTREGADA? Se darán por recibidas sus entradas.`)) return;

        try {
            await Boletos.apiPatch(`${API_COMPRAS}${id}/estado/`, { estado: 'ENTREGADO' });
            Boletos.toast('success', `Orden ${codigo} entregada.`);
            await cargarCompras();
        } catch (err) {
            Boletos.toast('danger', err.message);
        }
    }

    async function cancelarOrden(id) {
        const orden = cacheCompras.get(id);
        if (!orden) return;
        const codigo = String(orden.codigo || '').slice(0, 8);

        if (!window.confirm(`¿Cancelar la orden ${codigo}? Se anularán sus entradas y se repondrá el stock.`)) return;

        // Observación opcional registrada en el historial de la orden.
        const observacion = window.prompt('Observación de la cancelación (opcional):', '');
        if (observacion === null) return;

        try {
            await Boletos.apiPatch(`${API_COMPRAS}${id}/estado/`, {
                estado: 'CANCELADO',
                observacion: observacion,
            });
            Boletos.toast('success', `Orden ${codigo} cancelada.`);
            await cargarCompras();
        } catch (err) {
            Boletos.toast('danger', err.message);
        }
    }

    // =========================================================================
    // CARGA AUXILIAR: ESTADOS Y EVENTOS PROPIOS PARA LOS FILTROS
    // =========================================================================

    /** Opciones del select de estado desde Boletos.ESTADOS_ORDEN. */
    function poblarEstados() {
        Object.entries(Boletos.ESTADOS_ORDEN).forEach(([valor, texto]) => {
            const opcion = document.createElement('option');
            opcion.value = valor;
            opcion.textContent = texto;
            filtroEstado.appendChild(opcion);
        });
    }

    /** Eventos del organizador para filtrar órdenes por evento. */
    async function cargarEventosPropios() {
        try {
            const datos = await Boletos.apiGet('/api/eventos/', {
                organizador: ORGANIZADOR,
                page_size: 100,
            });
            const eventos = Array.isArray(datos.results) ? datos.results : [];
            filtroEvento.innerHTML = '<option value="">Todos</option>'
                + eventos.map((evento) => `<option value="${evento.id}">${Boletos.esc(evento.nombre)}</option>`).join('');
        } catch (err) {
            Boletos.toast('danger', err.message);
        }
    }

    // =========================================================================
    // ARRANQUE
    // =========================================================================

    poblarEstados();
    cargarEventosPropios();
    cargarCompras();
})();
