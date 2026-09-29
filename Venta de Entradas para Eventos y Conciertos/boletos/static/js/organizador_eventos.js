/**
 * organizador_eventos.js — Gestión de eventos y sectores del organizador.
 *
 * Lógica principal:
 * - Carga el listado propio con GET /api/eventos/?organizador=<id>&search=&categoria=&estado=
 *   (paginado, con filtros y paginación).
 * - Modal "Evento": alta (POST /api/eventos/) y edición (PUT /api/eventos/{id}/);
 *   tras crear abre el modal de sectores con el evento recién creado.
 * - Modal "Sectores": lista GET /api/eventos/{id}/sectores/, alta POST /api/sectores/,
 *   edición PUT /api/sectores/{id}/ y baja DELETE /api/sectores/{id}/.
 * - Desactivar (DELETE, borrado lógico) y Restaurar (POST .../restaurar/).
 * - Al cerrar el modal de sectores se recarga la tabla de eventos.
 */

(function () {
    'use strict';

    const vista = document.getElementById('vistaEventos');
    if (!vista) return; // El script solo aplica en organizador_eventos.html

    const ORGANIZADOR = Number(vista.dataset.organizador || 0);
    const PAGE_SIZE = 10;
    const API_EVENTOS = '/api/eventos/';
    const API_SECTORES = '/api/sectores/';

    // =========================================================================
    // ESTADO DE LA PANTALLA
    // =========================================================================

    let pagina = 1;
    let cacheEventos = new Map();    // id -> evento (para editar / sectores)
    let cacheSectores = new Map();   // id -> sector (para editar en el modal)
    let recintosCargados = false;
    let eventoActual = null;         // evento abierto en el modal de sectores
    let sectorEditandoId = null;     // sector en edición (null = creación)

    // =========================================================================
    // REFERENCIAS DOM
    // =========================================================================

    const tablaEventos = document.getElementById('tablaEventos');
    const paginacionEventos = document.getElementById('paginacionEventos');
    const contadorEventos = document.getElementById('contadorEventos');
    const filtroBuscar = document.getElementById('filtroBuscar');
    const filtroCategoria = document.getElementById('filtroCategoria');
    const filtroEstado = document.getElementById('filtroEstado');
    const btnFiltrar = document.getElementById('btnFiltrar');

    const modalEvento = document.getElementById('modalEvento');
    const formEvento = document.getElementById('formEvento');
    const eventoId = document.getElementById('eventoId');
    const eventoError = document.getElementById('eventoError');
    const btnGuardarEvento = document.getElementById('btnGuardarEvento');
    const selectRecinto = document.getElementById('eventoRecinto');

    const modalSectores = document.getElementById('modalSectores');
    const sectoresSubtitulo = document.getElementById('sectoresSubtitulo');
    const tablaSectores = document.getElementById('tablaSectores');
    const formSector = document.getElementById('formSector');
    const sectorId = document.getElementById('sectorId');
    const sectorError = document.getElementById('sectorError');
    const btnGuardarSector = document.getElementById('btnGuardarSector');
    const chkStockCompleto = document.getElementById('sectorStockCompleto');
    const inputStockDisponible = document.getElementById('sectorStockDisponible');

    // =========================================================================
    // UTILIDADES COMPARTIDAS
    // =========================================================================

    /** Llena un <select> con las constantes globales del núcleo. */
    function poblarSelect(select, mapa) {
        const fragmento = document.createDocumentFragment();
        Object.entries(mapa).forEach(([valor, texto]) => {
            const opcion = document.createElement('option');
            opcion.value = valor;
            opcion.textContent = texto;
            fragmento.appendChild(opcion);
        });
        select.appendChild(fragmento);
    }

    /** ISO (UTC) -> valor local para <input type="datetime-local">. */
    function aDatetimeLocal(iso) {
        if (!iso) return '';
        const fecha = new Date(iso);
        if (Number.isNaN(fecha.getTime())) return '';
        const p = (n) => String(n).padStart(2, '0');
        return `${fecha.getFullYear()}-${p(fecha.getMonth() + 1)}-${p(fecha.getDate())}`
            + `T${p(fecha.getHours())}:${p(fecha.getMinutes())}`;
    }

    function limpiarErrores(form, alerta) {
        form.querySelectorAll('[data-error-para]').forEach((el) => { el.textContent = ''; });
        form.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
        form.classList.remove('was-validated');
        if (alerta) {
            alerta.textContent = '';
            alerta.classList.add('d-none');
        }
    }

    /** Pinta los errores 400 de DRF ({campo: ["mensaje"]}) bajo cada campo. */
    function pintarErrores(form, datos) {
        let primero = '';
        let sinDestino = '';
        Object.entries(datos || {}).forEach(([clave, valor]) => {
            const mensaje = Array.isArray(valor) ? valor[0] : String(valor);
            if (!primero) primero = mensaje;
            const destino = form.querySelector(`[data-error-para="${clave}"]`);
            if (destino) destino.textContent = mensaje;
            else if (!sinDestino) sinDestino = `${clave}: ${mensaje}`;
            const input = form.querySelector(`[name="${clave}"]`);
            if (input) input.classList.add('is-invalid');
        });
        return { primero, sinDestino };
    }

    /** Manejo único de errores de API para los dos modales. */
    function manejarErrorApi(form, alerta, err) {
        limpiarErrores(form, alerta);
        if (err.status === 400 && err.data && typeof err.data === 'object') {
            const resultado = pintarErrores(form, err.data);
            alerta.textContent = resultado.sinDestino || resultado.primero || err.message;
            if (alerta.textContent) alerta.classList.remove('d-none');
            Boletos.toast('danger', resultado.primero || err.message);
        } else {
            alerta.textContent = err.message || 'No se pudo completar la operación.';
            alerta.classList.remove('d-none');
            Boletos.toast('danger', err.message);
        }
    }

    function cargandoBoton(btn, activo) {
        btn.disabled = activo;
        const spinner = btn.querySelector('.spinner-border');
        if (spinner) spinner.classList.toggle('d-none', !activo);
    }

    // =========================================================================
    // LISTADO DE EVENTOS
    // =========================================================================

    function filaEvento(evento) {
        const inactivo = !evento.activo;
        const cantidadSectores = Array.isArray(evento.sectores) ? evento.sectores.length : 0;
        const disponibles = Number(evento.entradas_disponibles || 0);

        const acciones = `
            <div class="d-flex flex-wrap gap-1 justify-content-end acciones-evento">
                <button type="button" class="btn btn-sm btn-outline-secondary btn-action"
                        data-sectores="${evento.id}" data-bs-toggle="modal" data-bs-target="#modalSectores"
                        title="Gestionar sectores" aria-label="Gestionar sectores de ${Boletos.esc(evento.nombre)}">
                    <i class="bi bi-diagram-3" aria-hidden="true"></i>Sectores
                </button>
                <button type="button" class="btn btn-sm btn-outline-primary btn-action"
                        data-editar="${evento.id}" data-bs-toggle="modal" data-bs-target="#modalEvento"
                        title="Editar evento" aria-label="Editar evento ${Boletos.esc(evento.nombre)}">
                    <i class="bi bi-pencil" aria-hidden="true"></i>Editar
                </button>
                ${inactivo
                    ? `<button type="button" class="btn btn-sm btn-outline-success btn-action"
                               data-restaurar="${evento.id}" title="Restaurar evento"
                               aria-label="Restaurar evento ${Boletos.esc(evento.nombre)}">
                           <i class="bi bi-arrow-counterclockwise" aria-hidden="true"></i>Restaurar
                       </button>`
                    : `<button type="button" class="btn btn-sm btn-outline-danger btn-action"
                               data-desactivar="${evento.id}" title="Desactivar evento"
                               aria-label="Desactivar evento ${Boletos.esc(evento.nombre)}">
                           <i class="bi bi-eye-slash" aria-hidden="true"></i>Desactivar
                       </button>`}
            </div>`;

        return `
            <tr class="${inactivo ? 'evento-inactivo' : ''}">
                <td>
                    <div class="fw-semibold">${Boletos.esc(evento.nombre)}</div>
                    <span class="badge badge-categoria">${Boletos.esc(Boletos.CATEGORIAS[evento.categoria] || evento.categoria || '—')}</span>
                </td>
                <td>${Boletos.esc(evento.artista)}</td>
                <td class="text-nowrap">${Boletos.fmtFecha(evento.fecha, true)}</td>
                <td>${Boletos.esc(evento.recinto_nombre)}</td>
                <td class="text-nowrap">
                    ${Boletos.badgeEstado(evento.estado, Boletos.ESTADOS_EVENTO)}
                    ${inactivo ? '<span class="badge bg-secondary ms-1">Inactiva</span>' : ''}
                </td>
                <td class="${disponibles === 0 ? 'stock-bajo' : ''}">${disponibles}</td>
                <td>${cantidadSectores}</td>
                <td class="text-end">${acciones}</td>
            </tr>`;
    }

    function pintarCargando() {
        tablaEventos.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted py-4">
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Cargando eventos...
                </td>
            </tr>`;
    }

    /** GET /api/eventos/ con los filtros actuales y la página seleccionada. */
    async function cargarEventos() {
        pintarCargando();
        try {
            const datos = await Boletos.apiGet(API_EVENTOS, {
                organizador: ORGANIZADOR,
                search: filtroBuscar.value.trim(),
                categoria: filtroCategoria.value,
                estado: filtroEstado.value,
                page: pagina,
                page_size: PAGE_SIZE,
            });

            const resultados = Array.isArray(datos.results) ? datos.results : [];
            resultados.forEach((evento) => cacheEventos.set(evento.id, evento));

            contadorEventos.textContent = `${datos.count || 0}`;

            if (!resultados.length) {
                tablaEventos.innerHTML = `<tr><td colspan="8">${
                    Boletos.estadoVacio('bi-calendar-x', 'Sin eventos',
                        'Aún no hay eventos con estos filtros. Crea uno con "Nuevo evento".')
                }</td></tr>`;
            } else {
                tablaEventos.innerHTML = resultados.map(filaEvento).join('');
            }

            const totalPaginas = Math.max(1, Math.ceil((datos.count || 0) / PAGE_SIZE));
            paginacionEventos.innerHTML = Boletos.paginacion(datos, pagina, totalPaginas);
        } catch (err) {
            Boletos.toast('danger', err.message);
            tablaEventos.innerHTML = `<tr><td colspan="8">${
                Boletos.estadoVacio('bi-exclamation-triangle', 'No se pudieron cargar los eventos',
                    Boletos.esc(err.message))
            }</td></tr>`;
            paginacionEventos.innerHTML = '';
        }
    }

    // Filtros: botón Filtrar, Enter en el buscador y cambio de los selects.
    btnFiltrar.addEventListener('click', () => { pagina = 1; cargarEventos(); });
    filtroBuscar.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') { ev.preventDefault(); pagina = 1; cargarEventos(); }
    });
    filtroCategoria.addEventListener('change', () => { pagina = 1; cargarEventos(); });
    filtroEstado.addEventListener('change', () => { pagina = 1; cargarEventos(); });

    // Paginación (los enlaces la generan Boletos.paginacion con data-pagina).
    paginacionEventos.addEventListener('click', (ev) => {
        const enlace = ev.target.closest('[data-pagina]');
        if (!enlace) return;
        ev.preventDefault();
        pagina = Number(enlace.dataset.pagina) || 1;
        cargarEventos();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Acciones por fila (delegación: los botones se generan dinámicamente).
    tablaEventos.addEventListener('click', (ev) => {
        const btn = ev.target.closest('button');
        if (!btn) return;
        if (btn.dataset.editar) prepararEdicion(Number(btn.dataset.editar));
        else if (btn.dataset.sectores) prepararSectores(cacheEventos.get(Number(btn.dataset.sectores)));
        else if (btn.dataset.desactivar) desactivarEvento(Number(btn.dataset.desactivar));
        else if (btn.dataset.restaurar) restaurarEvento(Number(btn.dataset.restaurar));
    });

    // =========================================================================
    // ALTA / EDICIÓN / BAJA DE EVENTOS
    // =========================================================================

    /** Prepara el modal en modo creación (disparado por #btnNuevoEvento). */
    function prepararNuevoEvento() {
        formEvento.reset();
        limpiarErrores(formEvento, eventoError);
        eventoId.value = '';
        document.getElementById('eventoEstado').value = 'proximo';
        document.getElementById('modalEventoLabel').innerHTML =
            '<i class="bi bi-calendar-event me-2" aria-hidden="true"></i>Nuevo evento';
    }

    /** Rellena el modal con los datos del evento a editar. */
    async function prepararEdicion(id) {
        const evento = cacheEventos.get(id);
        if (!evento) return;

        // El select de recintos debe estar cargado para marcar el actual.
        if (!recintosCargados) await cargarRecintos();

        formEvento.reset();
        limpiarErrores(formEvento, eventoError);
        eventoId.value = evento.id;
        document.getElementById('eventoNombre').value = evento.nombre || '';
        document.getElementById('eventoArtista').value = evento.artista || '';
        document.getElementById('eventoCategoria').value = evento.categoria || '';
        document.getElementById('eventoEstado').value = evento.estado || 'proximo';
        document.getElementById('eventoFecha').value = aDatetimeLocal(evento.fecha);
        document.getElementById('eventoImagen').value = evento.imagen_url || '';
        document.getElementById('eventoDescripcion').value = evento.descripcion || '';
        selectRecinto.value = evento.recinto ? String(evento.recinto) : '';
        document.getElementById('modalEventoLabel').innerHTML =
            '<i class="bi bi-pencil me-2" aria-hidden="true"></i>Editar evento';
    }

    document.getElementById('btnNuevoEvento').addEventListener('click', prepararNuevoEvento);

    // Carga de recintos para el select del modal (una sola vez).
    async function cargarRecintos() {
        if (recintosCargados) return;
        try {
            const datos = await Boletos.apiGet('/api/recintos/', { page_size: 100 });
            const recintos = Array.isArray(datos.results) ? datos.results : [];
            selectRecinto.innerHTML = '<option value="">Selecciona un recinto...</option>'
                + recintos.map((r) => `<option value="${r.id}">${Boletos.esc(r.nombre)}${r.ciudad ? ` — ${Boletos.esc(r.ciudad)}` : ''}</option>`).join('');
            recintosCargados = true;
        } catch (err) {
            Boletos.toast('danger', err.message);
        }
    }

    // Submit del modal de evento: POST (alta) o PUT (edición).
    formEvento.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        limpiarErrores(formEvento, eventoError);

        if (!formEvento.checkValidity()) {
            formEvento.classList.add('was-validated');
            return;
        }

        const valorFecha = document.getElementById('eventoFecha').value;
        const fecha = new Date(valorFecha);
        if (Number.isNaN(fecha.getTime())) {
            formEvento.querySelector('[data-error-para="fecha"]').textContent = 'Indica una fecha válida.';
            return;
        }

        if (!recintosCargados) await cargarRecintos();

        const payload = {
            nombre: document.getElementById('eventoNombre').value.trim(),
            artista: document.getElementById('eventoArtista').value.trim(),
            categoria: document.getElementById('eventoCategoria').value,
            estado: document.getElementById('eventoEstado').value,
            fecha: fecha.toISOString(),
            recinto: Number(selectRecinto.value),
            imagen_url: document.getElementById('eventoImagen').value.trim(),
            descripcion: document.getElementById('eventoDescripcion').value.trim(),
        };

        cargandoBoton(btnGuardarEvento, true);
        try {
            if (eventoId.value) {
                // Edición total del evento.
                await Boletos.apiPut(`${API_EVENTOS}${eventoId.value}/`, payload);
                Boletos.toast('success', 'Evento actualizado correctamente.');
                bootstrap.Modal.getOrCreateInstance(modalEvento).hide();
                await cargarEventos();
            } else {
                // Alta: después se gestionan los sectores del evento creado.
                const creado = await Boletos.apiPost(API_EVENTOS, payload);
                Boletos.toast('success', 'Evento creado. Ahora define sus sectores.');
                cacheEventos.set(creado.id, creado);
                ocultarEventoYAbrirSectores(creado);
            }
        } catch (err) {
            manejarErrorApi(formEvento, eventoError, err);
        } finally {
            cargandoBoton(btnGuardarEvento, false);
        }
    });

    /** Cierra el modal de evento y, al terminar, abre el de sectores. */
    function ocultarEventoYAbrirSectores(evento) {
        prepararSectores(evento);
        const instancia = bootstrap.Modal.getInstance(modalEvento);
        if (instancia) {
            modalEvento.addEventListener('hidden.bs.modal',
                () => bootstrap.Modal.getOrCreateInstance(modalSectores).show(),
                { once: true });
            instancia.hide();
        } else {
            bootstrap.Modal.getOrCreateInstance(modalSectores).show();
        }
    }

    async function desactivarEvento(id) {
        const evento = cacheEventos.get(id);
        if (!evento) return;
        if (!window.confirm(`¿Desactivar "${evento.nombre}"? Dejará de mostrarse en el catálogo (podrás restaurarlo luego).`)) return;
        try {
            await Boletos.apiDelete(`${API_EVENTOS}${id}/`);
            Boletos.toast('success', 'Evento desactivado.');
            await cargarEventos();
        } catch (err) {
            Boletos.toast('danger', err.message);
        }
    }

    async function restaurarEvento(id) {
        const evento = cacheEventos.get(id);
        if (!evento) return;
        if (!window.confirm(`¿Restaurar "${evento.nombre}"? Volverá a aparecer en el catálogo.`)) return;
        try {
            await Boletos.apiPost(`${API_EVENTOS}${id}/restaurar/`, {});
            Boletos.toast('success', 'Evento restaurado.');
            await cargarEventos();
        } catch (err) {
            Boletos.toast('danger', err.message);
        }
    }

    // =========================================================================
    // SECTORES DEL EVENTO
    // =========================================================================

    function filaSector(sector) {
        return `
            <tr>
                <td>${Boletos.esc(sector.nombre)}</td>
                <td><span class="badge badge-precio">${Boletos.fmtMoney(sector.precio)}</span></td>
                <td>${Number(sector.stock_total || 0)}</td>
                <td class="${Number(sector.stock_disponible || 0) === 0 ? 'stock-bajo' : ''}">${Number(sector.stock_disponible || 0)}</td>
                <td>${Number(sector.vendidas || 0)}</td>
                <td class="text-end">
                    <div class="d-flex gap-1 justify-content-end">
                        <button type="button" class="btn btn-sm btn-outline-primary btn-action"
                                data-sector-editar="${sector.id}" title="Editar sector"
                                aria-label="Editar sector ${Boletos.esc(sector.nombre)}">
                            <i class="bi bi-pencil" aria-hidden="true"></i>Editar
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger btn-action"
                                data-sector-eliminar="${sector.id}" title="Eliminar sector"
                                aria-label="Eliminar sector ${Boletos.esc(sector.nombre)}">
                            <i class="bi bi-trash" aria-hidden="true"></i>Eliminar
                        </button>
                    </div>
                </td>
            </tr>`;
    }

    /** Abre el modal de sectores con el evento indicado y carga su listado. */
    function prepararSectores(evento) {
        if (!evento) return;
        eventoActual = evento;
        sectoresSubtitulo.innerHTML = `Evento: <strong>${Boletos.esc(evento.nombre)}</strong>`;
        prepararNuevoSector();
        cargarSectores();
    }

    /** GET /api/eventos/{id}/sectores/ -> arreglo directo de sectores. */
    async function cargarSectores() {
        if (!eventoActual) return;
        tablaSectores.innerHTML = `
            <tr><td colspan="6" class="text-center text-muted py-3">
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                Cargando sectores...
            </td></tr>`;
        try {
            const datos = await Boletos.apiGet(`${API_EVENTOS}${eventoActual.id}/sectores/`);
            const sectores = Array.isArray(datos) ? datos : (datos.results || []);
            cacheSectores = new Map(sectores.map((s) => [s.id, s]));

            if (!sectores.length) {
                tablaSectores.innerHTML = `<tr><td colspan="6">${
                    Boletos.estadoVacio('bi-diagram-3', 'Sin sectores',
                        'Agrega el primer sector con el formulario de abajo.')
                }</td></tr>`;
                return;
            }
            tablaSectores.innerHTML = sectores.map(filaSector).join('');
        } catch (err) {
            Boletos.toast('danger', err.message);
            tablaSectores.innerHTML = `<tr><td colspan="6">${
                Boletos.estadoVacio('bi-exclamation-triangle', 'No se pudieron cargar los sectores',
                    Boletos.esc(err.message))
            }</td></tr>`;
        }
    }

    /** Reinicia el formulario de sector en modo creación. */
    function prepararNuevoSector() {
        formSector.reset();
        limpiarErrores(formSector, sectorError);
        sectorId.value = '';
        sectorEditandoId = null;
        chkStockCompleto.checked = true;
        sincronizarStockDisponible();
        document.getElementById('tituloFormSector').innerHTML =
            '<i class="bi bi-plus-square me-2" aria-hidden="true"></i>Nuevo sector';
        document.getElementById('textoBtnSector').textContent = 'Agregar sector';
    }

    /** El checkbox "stock_disponible = stock_total" controla el input extra. */
    function sincronizarStockDisponible() {
        const total = document.getElementById('sectorStockTotal').value;
        inputStockDisponible.disabled = chkStockCompleto.checked;
        if (chkStockCompleto.checked) inputStockDisponible.value = total;
    }

    chkStockCompleto.addEventListener('change', sincronizarStockDisponible);
    document.getElementById('sectorStockTotal').addEventListener('input', sincronizarStockDisponible);
    document.getElementById('btnNuevoSector').addEventListener('click', prepararNuevoSector);

    // Acciones de la tabla de sectores (delegación).
    tablaSectores.addEventListener('click', async (ev) => {
        const btn = ev.target.closest('button');
        if (!btn) return;

        if (btn.dataset.sectorEditar) {
            const sector = cacheSectores.get(Number(btn.dataset.sectorEditar));
            if (!sector) return;
            formSector.reset();
            limpiarErrores(formSector, sectorError);
            sectorEditandoId = sector.id;
            sectorId.value = sector.id;
            document.getElementById('sectorNombre').value = sector.nombre || '';
            document.getElementById('sectorPrecio').value = sector.precio;
            document.getElementById('sectorStockTotal').value = sector.stock_total;
            chkStockCompleto.checked = Number(sector.stock_disponible) === Number(sector.stock_total);
            sincronizarStockDisponible();
            if (!chkStockCompleto.checked) inputStockDisponible.value = sector.stock_disponible;
            document.getElementById('tituloFormSector').innerHTML =
                `<i class="bi bi-pencil-square me-2" aria-hidden="true"></i>Editar sector: ${Boletos.esc(sector.nombre)}`;
            document.getElementById('textoBtnSector').textContent = 'Guardar cambios';
            document.getElementById('sectorNombre').focus();
            return;
        }

        if (btn.dataset.sectorEliminar) {
            const sector = cacheSectores.get(Number(btn.dataset.sectorEliminar));
            if (!sector) return;
            if (!window.confirm(`¿Eliminar el sector "${sector.nombre}"? Esta acción no se puede deshacer.`)) return;
            try {
                await Boletos.apiDelete(`${API_SECTORES}${sector.id}/`);
                Boletos.toast('success', 'Sector eliminado.');
                await cargarSectores();
            } catch (err) {
                Boletos.toast('danger', err.message);
            }
        }
    });

    // Alta / edición de sector.
    formSector.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        limpiarErrores(formSector, sectorError);

        if (!formSector.checkValidity()) {
            formSector.classList.add('was-validated');
            return;
        }
        if (!eventoActual) return;

        const stockTotal = Number(document.getElementById('sectorStockTotal').value);
        const stockDisponible = chkStockCompleto.checked
            ? stockTotal
            : Number(inputStockDisponible.value);

        if (stockDisponible > stockTotal) {
            inputStockDisponible.classList.add('is-invalid');
            document.querySelector('#formSector [data-error-para="stock_disponible"]').textContent =
                'El stock disponible no puede superar al stock total.';
            return;
        }

        const payload = {
            evento: eventoActual.id,
            nombre: document.getElementById('sectorNombre').value.trim(),
            precio: Number(document.getElementById('sectorPrecio').value),
            stock_total: stockTotal,
            stock_disponible: stockDisponible,
        };

        cargandoBoton(btnGuardarSector, true);
        try {
            if (sectorEditandoId) {
                await Boletos.apiPut(`${API_SECTORES}${sectorEditandoId}/`, payload);
                Boletos.toast('success', 'Sector actualizado.');
            } else {
                await Boletos.apiPost(API_SECTORES, payload);
                Boletos.toast('success', 'Sector agregado.');
            }
            prepararNuevoSector();
            await cargarSectores();
        } catch (err) {
            manejarErrorApi(formSector, sectorError, err);
        } finally {
            cargandoBoton(btnGuardarSector, false);
        }
    });

    // Al cerrar el modal de sectores se refresca la tabla de eventos
    // (los cambios de sectores afectan stock y entradas disponibles).
    modalSectores.addEventListener('hidden.bs.modal', () => {
        eventoActual = null;
        cargarEventos();
    });

    // Al cerrar el modal de evento se limpian los mensajes de error.
    modalEvento.addEventListener('hidden.bs.modal', () => {
        limpiarErrores(formEvento, eventoError);
    });

    // =========================================================================
    // ARRANQUE
    // =========================================================================

    poblarSelect(filtroCategoria, Boletos.CATEGORIAS);
    poblarSelect(filtroEstado, Boletos.ESTADOS_EVENTO);
    poblarSelect(document.getElementById('eventoCategoria'), Boletos.CATEGORIAS);
    poblarSelect(document.getElementById('eventoEstado'), Boletos.ESTADOS_EVENTO);
    document.getElementById('eventoEstado').value = 'proximo';
    sincronizarStockDisponible();
    cargarRecintos();
    cargarEventos();
})();
