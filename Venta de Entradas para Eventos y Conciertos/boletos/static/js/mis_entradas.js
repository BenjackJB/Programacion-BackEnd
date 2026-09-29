/**
 * Mis entradas (mis_entradas.html).
 *
 * Responsabilidades:
 * - Consultar GET /api/mis-entradas/?page=N (respuesta paginada de tickets).
 * - Pintar una tarjeta por entrada con código copiable, evento, sector,
 *   estado del ticket y estado de la orden de compra.
 * - Manejar la paginación y el estado vacío con enlace al catálogo.
 */
(function () {
    'use strict';

    // =========================================================================
    // REFERENCIAS Y ESTADO
    // =========================================================================

    const seccion = document.getElementById('paginaEntradas');
    if (!seccion) return;

    const grid = document.getElementById('gridEntradas');
    const contenedorPaginacion = document.getElementById('paginacionEntradas');
    const API = seccion.dataset.api;
    const URL_CATALOGO = seccion.dataset.catalogo || '/eventos/';

    // Tamaño de página fijo del API (boletos/pagination.py).
    const TAMANO_PAGINA = 20;
    let paginaActual = 1;

    // =========================================================================
    // RENDER DE TARJETAS
    // =========================================================================

    /** Tarjeta individual de una entrada (ticket). */
    function tarjetaEntrada(ticket) {
        const evento = ticket.evento || {};
        const orden = String(ticket.orden || '').slice(0, 8);

        return `
            <div class="col">
                <article class="card h-100">
                    <div class="card-body d-flex flex-column">
                        <!-- Código de la entrada + botón copiar -->
                        <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
                            <span class="codigo-entrada">${Boletos.esc(ticket.codigo)}</span>
                            <button type="button" class="btn btn-sm btn-outline-secondary btn-action btnCopiar"
                                    data-codigo="${Boletos.esc(ticket.codigo)}"
                                    title="Copiar código" aria-label="Copiar código de la entrada">
                                <i class="bi bi-clipboard" aria-hidden="true"></i>
                            </button>
                        </div>

                        <!-- Evento y fecha -->
                        <h5 class="mb-1">${Boletos.esc(evento.nombre || 'Evento')}</h5>
                        <div class="evento-fecha mb-2">
                            <i class="bi bi-calendar3 me-1" aria-hidden="true"></i>${Boletos.fmtFecha(evento.fecha, true)}
                        </div>

                        <!-- Sector y precio -->
                        <p class="small mb-0">
                            <i class="bi bi-geo-alt me-1" aria-hidden="true"></i>${Boletos.esc(ticket.sector_nombre)}
                            · <span class="fw-bold">${Boletos.fmtMoney(ticket.sector_precio)}</span>
                        </p>

                        <!-- Estado del ticket y de la orden -->
                        <div class="entrada-pie d-flex justify-content-between align-items-center gap-2 mt-auto">
                            ${Boletos.badgeEstado(ticket.estado, Boletos.ESTADOS_TICKET)}
                            <span class="small text-muted text-end">
                                Orden ${Boletos.esc(orden)}
                                ${Boletos.badgeEstado(ticket.estado_orden)}
                            </span>
                        </div>
                    </div>
                </article>
            </div>`;
    }

    /** Pinta el grid o el estado vacío cuando aún no hay entradas. */
    function pintarEntradas(tickets) {
        if (!tickets.length) {
            grid.innerHTML = `
                <div class="col-12">
                    ${Boletos.estadoVacio('bi-upc-scan', 'No tienes entradas', 'Tu próxima entrada te espera en el catálogo')}
                    <div class="text-center">
                        <a class="btn btn-accent" href="${Boletos.esc(URL_CATALOGO)}">
                            <i class="bi bi-ticket-detailed me-1" aria-hidden="true"></i>Explorar catálogo
                        </a>
                    </div>
                </div>`;
            return;
        }
        grid.innerHTML = tickets.map(tarjetaEntrada).join('');
    }

    // =========================================================================
    // CARGA DE DATOS
    // =========================================================================

    /** GET /api/mis-entradas/ con la página activa; repinta grid y paginación. */
    async function cargarEntradas() {
        grid.innerHTML = '<div class="col-12"><p class="text-center text-muted mb-0">Cargando tus entradas…</p></div>';

        try {
            const params = paginaActual > 1 ? { page: paginaActual } : {};
            const datos = await Boletos.apiGet(API, params);
            const tickets = Array.isArray(datos.results) ? datos.results : [];
            const totalPaginas = Math.ceil((datos.count || 0) / TAMANO_PAGINA);

            pintarEntradas(tickets);
            contenedorPaginacion.innerHTML = Boletos.paginacion(datos, paginaActual, totalPaginas);
        } catch (err) {
            const mensaje = (err && err.message) || Boletos.extraerMensaje(err);
            grid.innerHTML = `<div class="col-12">${Boletos.estadoVacio(
                'bi-exclamation-triangle',
                'No se pudieron cargar tus entradas',
                mensaje
            )}</div>`;
            contenedorPaginacion.innerHTML = '';
            Boletos.toast('danger', mensaje);
        }
    }

    // =========================================================================
    // COPIAR CÓDIGO AL PORTAPAPELES
    // =========================================================================

    /** Copia el código; usa la API moderna y recurre a un textarea si falla. */
    async function copiarCodigo(texto) {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(texto);
            } else {
                // Respaldo para contextos sin clipboard API (p. ej. http).
                const temporal = document.createElement('textarea');
                temporal.value = texto;
                temporal.setAttribute('readonly', '');
                temporal.style.position = 'fixed';
                temporal.style.opacity = '0';
                document.body.appendChild(temporal);
                temporal.select();
                const ok = document.execCommand('copy');
                temporal.remove();
                if (!ok) throw new Error('no-disponible');
            }
            Boletos.toast('success', 'Código copiado al portapapeles');
        } catch (e) {
            Boletos.toast('danger', 'No se pudo copiar el código');
        }
    }

    // =========================================================================
    // EVENTOS DE INTERFAZ (DELEGACIÓN)
    // =========================================================================

    // Botón de copiar en cualquier tarjeta.
    grid.addEventListener('click', (evento) => {
        const boton = evento.target.closest('.btnCopiar');
        if (boton) copiarCodigo(boton.dataset.codigo || '');
    });

    // Paginación generada por Boletos.paginacion (enlaces con data-pagina).
    contenedorPaginacion.addEventListener('click', (evento) => {
        const enlace = evento.target.closest('[data-pagina]');
        if (!enlace) return;
        evento.preventDefault();

        const nueva = parseInt(enlace.dataset.pagina, 10);
        if (!Number.isFinite(nueva) || nueva === paginaActual) return;

        paginaActual = nueva;
        cargarEntradas().then(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
    });

    // =========================================================================
    // ARRANQUE
    // =========================================================================

    cargarEntradas();
})();
