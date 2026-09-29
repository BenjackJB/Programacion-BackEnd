/**
 * Catálogo público de eventos (eventos.html).
 *
 * Responsabilidades:
 * - Poblar los selects de categoría/estado con los mapas globales de Boletos.
 * - Leer los filtros desde location.search al cargar la página.
 * - Consultar GET /api/eventos/ con los filtros y la página activas.
 * - Pintar las tarjetas de eventos y la paginación.
 * - Persistir los filtros en la URL con history.replaceState (sin recargar).
 */
(function () {
    'use strict';

    // =========================================================================
    // REFERENCIAS Y ESTADO
    // =========================================================================

    const seccion = document.getElementById('seccionResultados');
    const grid = document.getElementById('gridEventos');
    const contenedorPaginacion = document.getElementById('paginacionEventos');
    const form = document.getElementById('formFiltros');
    const btnLimpiar = document.getElementById('btnLimpiar');

    // Endpoint del API inyectado por Django en el template.
    const API = (seccion && seccion.dataset.api) || '/api/eventos/';
    // Tamaño de página fijo del API (boletos/pagination.py).
    const TAMANO_PAGINA = 20;

    // Página visible actualmente (1 por defecto).
    let paginaActual = 1;

    // =========================================================================
    // SELECTS DINÁMICOS (CATEGORÍA Y ESTADO)
    // =========================================================================

    /** Agrega al DOM las opciones de categoría y estado desde los mapas globales. */
    function poblarSelects() {
        const selCategoria = document.getElementById('filtroCategoria');
        const selEstado = document.getElementById('filtroEstado');

        Object.entries(Boletos.CATEGORIAS).forEach(([valor, texto]) => {
            const opcion = document.createElement('option');
            opcion.value = valor;
            opcion.textContent = texto;
            selCategoria.appendChild(opcion);
        });

        Object.entries(Boletos.ESTADOS_EVENTO).forEach(([valor, texto]) => {
            const opcion = document.createElement('option');
            opcion.value = valor;
            opcion.textContent = texto;
            selEstado.appendChild(opcion);
        });
    }

    // =========================================================================
    // FILTROS: LECTURA DESDE LA URL Y PERSISTENCIA
    // =========================================================================

    /** Restaura en el formulario los filtros guardados en location.search. */
    function leerFiltrosDeURL() {
        const params = new URLSearchParams(window.location.search);
        document.getElementById('filtroBusqueda').value = params.get('search') || '';
        document.getElementById('filtroCategoria').value = params.get('categoria') || '';
        document.getElementById('filtroPrecioMin').value = params.get('precio_min') || '';
        document.getElementById('filtroPrecioMax').value = params.get('precio_max') || '';
        document.getElementById('filtroEstado').value = params.get('estado') || '';
        document.getElementById('filtroOrden').value = params.get('ordering') || '';

        const pagina = parseInt(params.get('page') || '1', 10);
        paginaActual = Number.isFinite(pagina) && pagina > 0 ? pagina : 1;
    }

    /** Devuelve solo los parámetros con valor (el API ignora los vacíos igual). */
    function filtrosActuales() {
        const datos = new FormData(form);
        const params = {};
        datos.forEach((valor, clave) => {
            if (valor !== '') params[clave] = valor;
        });
        return params;
    }

    /**
     * Guarda los filtros + página en la barra de direcciones sin recargar.
     * Mantiene el botón "atrás" del navegador coherente con lo mostrado.
     */
    function guardarFiltrosEnURL() {
        const params = filtrosActuales();
        if (paginaActual > 1) params.page = paginaActual;
        const consulta = new URLSearchParams(params).toString();
        history.replaceState(null, '', `${window.location.pathname}${consulta ? `?${consulta}` : ''}`);
    }

    // =========================================================================
    // CARGA DE DATOS
    // =========================================================================

    /** Consulta el API y vuelve a pintar el grid y la paginación. */
    async function cargarEventos() {
        seccion.setAttribute('aria-busy', 'true');
        grid.innerHTML = '<div class="col-12"><p class="text-center text-muted mb-0">Cargando eventos…</p></div>';

        try {
            const params = filtrosActuales();
            if (paginaActual > 1) params.page = paginaActual;

            const datos = await Boletos.apiGet(API, params);
            const eventos = Array.isArray(datos.results) ? datos.results : [];
            const totalPaginas = Math.ceil((datos.count || 0) / TAMANO_PAGINA);

            pintarEventos(eventos);
            contenedorPaginacion.innerHTML = Boletos.paginacion(datos, paginaActual, totalPaginas);
        } catch (err) {
            const mensaje = (err && err.message) || Boletos.extraerMensaje(err);
            grid.innerHTML = `<div class="col-12">${Boletos.estadoVacio(
                'bi-exclamation-triangle',
                'No se pudieron cargar los eventos',
                mensaje
            )}</div>`;
            contenedorPaginacion.innerHTML = '';
            Boletos.toast('danger', mensaje);
        } finally {
            seccion.setAttribute('aria-busy', 'false');
        }
    }

    // =========================================================================
    // RENDER DE TARJETAS
    // =========================================================================

    /** Imagen de portada o placeholder con ícono (clase .evento-img). */
    function imagenEvento(evento) {
        if (evento.imagen_url) {
            return `<img class="evento-img" src="${Boletos.esc(evento.imagen_url)}"
                         alt="Portada de ${Boletos.esc(evento.nombre)}" loading="lazy">`;
        }
        return `<div class="evento-img" role="img" aria-label="Sin imagen de portada">
                    <i class="bi bi-music-note-beamed" aria-hidden="true"></i>
                </div>`;
    }

    /** Línea de stock: agotado / stock bajo (<10) / disponible. */
    function lineaStock(evento) {
        const disponibles = Number(evento.entradas_disponibles || 0);
        if (evento.agotado) {
            return '<span class="stock-bajo"><i class="bi bi-x-octagon me-1" aria-hidden="true"></i>Agotado</span>';
        }
        if (disponibles < 10) {
            return `<span class="stock-bajo">Quedan ${disponibles} entradas</span>`;
        }
        return `<span class="text-muted">${disponibles} entradas disponibles</span>`;
    }

    /** Tarjeta de un evento del catálogo. */
    function tarjetaEvento(evento) {
        return `
            <div class="col">
                <article class="card evento-card">
                    ${imagenEvento(evento)}
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
                            <span class="badge badge-categoria">${Boletos.esc(
                                Boletos.CATEGORIAS[evento.categoria] || evento.categoria
                            )}</span>
                            ${Boletos.badgeEstado(evento.estado, Boletos.ESTADOS_EVENTO)}
                        </div>
                        <div class="evento-fecha mb-1">
                            <i class="bi bi-calendar3 me-1" aria-hidden="true"></i>${Boletos.fmtFecha(evento.fecha, true)}
                        </div>
                        <h5 class="mb-1">${Boletos.esc(evento.nombre)}</h5>
                        <p class="fw-bold mb-1">${Boletos.esc(evento.artista)}</p>
                        <p class="small text-muted mb-2">
                            <i class="bi bi-geo-alt me-1" aria-hidden="true"></i>${Boletos.esc(evento.recinto_nombre)}
                        </p>
                        <p class="small mb-2">${lineaStock(evento)}</p>
                        <div class="d-flex justify-content-between align-items-center mt-auto">
                            <span class="badge badge-precio">Desde ${Boletos.fmtMoney(evento.precio_minimo)}</span>
                            <a class="btn btn-sm btn-outline-primary" href="/eventos/${encodeURIComponent(evento.id)}/">
                                Ver detalle
                            </a>
                        </div>
                    </div>
                </article>
            </div>`;
    }

    /** Pinta el grid completo o el estado vacío cuando no hay resultados. */
    function pintarEventos(eventos) {
        if (!eventos.length) {
            grid.innerHTML = `<div class="col-12">${Boletos.estadoVacio(
                'bi-calendar-x',
                'No hay eventos',
                'Intenta con otros filtros'
            )}</div>`;
            return;
        }
        grid.innerHTML = eventos.map(tarjetaEvento).join('');
    }

    // =========================================================================
    // EVENTOS DE INTERFAZ
    // =========================================================================

    // Aplicar filtros: nueva búsqueda, siempre desde la página 1.
    form.addEventListener('submit', (evento) => {
        evento.preventDefault();
        paginaActual = 1;
        guardarFiltrosEnURL();
        cargarEventos();
    });

    // Limpiar: restablece el formulario y la URL, y recarga sin filtros.
    btnLimpiar.addEventListener('click', () => {
        form.reset();
        paginaActual = 1;
        guardarFiltrosEnURL();
        cargarEventos();
    });

    // Paginación generada por Boletos.paginacion (enlaces con data-pagina).
    contenedorPaginacion.addEventListener('click', (evento) => {
        const enlace = evento.target.closest('[data-pagina]');
        if (!enlace) return;
        evento.preventDefault();

        const nueva = parseInt(enlace.dataset.pagina, 10);
        if (!Number.isFinite(nueva) || nueva === paginaActual) return;

        paginaActual = nueva;
        guardarFiltrosEnURL();
        cargarEventos().then(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
    });

    // =========================================================================
    // ARRANQUE
    // =========================================================================

    poblarSelects();
    leerFiltrosDeURL();
    cargarEventos();
})();
