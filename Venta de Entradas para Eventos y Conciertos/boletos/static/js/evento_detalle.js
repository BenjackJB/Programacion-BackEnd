/**
 * Detalle de un evento (evento_detalle.html).
 *
 * Responsabilidades:
 * - Consultar GET /api/eventos/{id}/sectores/ (respuesta: arreglo directo).
 * - Pintar la tabla de localidades/sectores con precio y disponibilidad.
 * - Según la sesión (data-rol): invitar a iniciar sesión, mostrar el aviso
 *   para organizadores o permitir agregar al carro (POST /api/carro-tickets/).
 */
(function () {
    'use strict';

    // =========================================================================
    // REFERENCIAS Y CONFIGURACIÓN (inyectada por Django vía data-*)
    // =========================================================================

    const contenedor = document.getElementById('sectoresContainer');
    if (!contenedor) return; // La página no tiene la sección de sectores.

    const cuerpo = document.getElementById('sectoresCuerpo');
    const API_SECTORES = contenedor.dataset.api;
    const API_CARRO = contenedor.dataset.apiCarro;
    const LOGIN_URL = contenedor.dataset.loginUrl || '/login/';
    const ROL = contenedor.dataset.rol || '';

    // El rol vacío significa que no hay sesión JWT vigente.
    const ES_ORGANIZADOR = ROL === 'organizador';
    const ES_ESPECTADOR = ROL === 'espectador';
    const SESION_ACTIVA = ES_ORGANIZADOR || ES_ESPECTADOR;

    // =========================================================================
    // RENDER DE LA TABLA DE SECTORES
    // =========================================================================

    /** Celda de disponibilidad: badge "Agotado" o cantidad disponible. */
    function celdaDisponibilidad(sector) {
        if (sector.agotado) {
            return '<span class="badge badge-estado CANCELADO">Agotado</span>';
        }
        return `<span class="text-success fw-semibold">${sector.stock_disponible} disponibles</span>`;
    }

    /**
     * Acción disponible en cada fila según la sesión:
     * - Sin sesión -> enlace al login con la URL de retorno.
     * - Organizador -> aviso (no puede comprar entradas).
     * - Espectador -> botón "Agregar al carro".
     */
    function celdaAccion(sector) {
        if (sector.agotado) {
            return '<button type="button" class="btn btn-sm btn-secondary" disabled>Sin stock</button>';
        }
        if (ES_ORGANIZADOR) {
            return '<span class="badge badge-estado proximo">Los organizadores no pueden comprar entradas</span>';
        }
        if (!SESION_ACTIVA) {
            return `<a class="btn btn-sm btn-outline-primary" href="${Boletos.esc(LOGIN_URL)}">
                        <i class="bi bi-box-arrow-in-right me-1" aria-hidden="true"></i>Inicia sesión para comprar
                    </a>`;
        }
        return `<button type="button" class="btn btn-sm btn-accent btnAgregar"
                        data-sector="${sector.id}"
                        aria-label="Agregar ${Boletos.esc(sector.nombre)} al carro">
                    <i class="bi bi-cart-plus me-1" aria-hidden="true"></i>Agregar al carro
                </button>`;
    }

    /** Tabla completa con todos los sectores del evento. */
    function tablaSectores(sectores) {
        const filas = sectores.map((sector) => `
            <tr>
                <th scope="row">${Boletos.esc(sector.nombre)}</th>
                <td>${Boletos.fmtMoney(sector.precio)}</td>
                <td>${celdaDisponibilidad(sector)}</td>
                <td>
                    <label class="visually-hidden" for="cantidad-${sector.id}">
                        Cantidad de entradas para ${Boletos.esc(sector.nombre)}
                    </label>
                    <input type="number" class="form-control form-control-sm cantidad-sector"
                           id="cantidad-${sector.id}" data-sector-input="${sector.id}"
                           min="1" max="20" step="1" value="1" inputmode="numeric"
                           style="max-width: 6.5rem"
                           ${sector.agotado ? 'disabled' : ''}>
                </td>
                <td class="text-end">${celdaAccion(sector)}</td>
            </tr>`).join('');

        return `
            <div class="table-responsive">
                <table class="table mb-0 align-middle">
                    <caption class="visually-hidden">Localidades disponibles para este evento</caption>
                    <thead>
                        <tr>
                            <th scope="col">Sector</th>
                            <th scope="col">Precio</th>
                            <th scope="col">Disponibles</th>
                            <th scope="col">Cantidad</th>
                            <th scope="col" class="text-end">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>${filas}</tbody>
                </table>
            </div>`;
    }

    // =========================================================================
    // CARGA DE DATOS
    // =========================================================================

    /** Carga los sectores del evento y los pinta dentro del contenedor. */
    async function cargarSectores() {
        try {
            // Respuesta del API: arreglo directo (sin paginar).
            const sectores = await Boletos.apiGet(API_SECTORES);

            if (!Array.isArray(sectores) || !sectores.length) {
                cuerpo.innerHTML = Boletos.estadoVacio(
                    'bi-diagram-3',
                    'Este evento no tiene localidades',
                    'Pronto podrás ver aquí sus sectores disponibles'
                );
                return;
            }

            cuerpo.innerHTML = tablaSectores(sectores);
        } catch (err) {
            const mensaje = (err && err.message) || Boletos.extraerMensaje(err);
            cuerpo.innerHTML = Boletos.estadoVacio(
                'bi-exclamation-triangle',
                'No se pudieron cargar las localidades',
                mensaje
            );
            Boletos.toast('danger', mensaje);
        }
    }

    // =========================================================================
    // AGREGAR AL CARRO
    // =========================================================================

    /** Limita el input de cantidad al rango permitido por el API (1..20). */
    function cantidadValida(input) {
        let cantidad = parseInt(input.value, 10);
        if (!Number.isFinite(cantidad) || cantidad < 1) cantidad = 1;
        if (cantidad > 20) cantidad = 20;
        input.value = cantidad;
        return cantidad;
    }

    /** POST /api/carro-tickets/ {sector, cantidad} y refresco de la interfaz. */
    async function agregarAlCarro(boton, sectorId) {
        const input = contenedor.querySelector(`[data-sector-input="${sectorId}"]`);
        const cantidad = cantidadValida(input);

        boton.disabled = true;
        try {
            await Boletos.apiPost(API_CARRO, { sector: sectorId, cantidad });
            Boletos.toast('success', 'Agregado al carro');
            // Actualiza el contador del navbar y asegura visible el acceso al carro.
            Boletos.refrescarBadgeCarro();
            const btnIrCarro = document.getElementById('btnIrCarro');
            if (btnIrCarro) btnIrCarro.classList.remove('d-none');
        } catch (err) {
            const mensaje = (err && err.message) || Boletos.extraerMensaje(err);
            Boletos.toast('danger', mensaje);
        } finally {
            boton.disabled = false;
        }
    }

    // =========================================================================
    // EVENTOS DE INTERFAZ (DELEGACIÓN)
    // =========================================================================

    // Botones "Agregar al carro" de cualquier fila.
    contenedor.addEventListener('click', (evento) => {
        const boton = evento.target.closest('.btnAgregar');
        if (!boton) return;
        agregarAlCarro(boton, Number(boton.dataset.sector));
    });

    // Normaliza la cantidad escrita al salir del input.
    contenedor.addEventListener('change', (evento) => {
        const input = evento.target.closest('.cantidad-sector');
        if (input) cantidadValida(input);
    });

    // =========================================================================
    // ARRANQUE
    // =========================================================================

    cargarSectores();
})();
