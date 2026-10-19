/**
 * Carro de compras (carro.html).
 *
 * Responsabilidades:
 * - Cargar el carro con GET /api/carro-tickets/ y pintar su tabla.
 * - "Agregar 1" -> POST {sector, cantidad:1} (el API suma al ítem existente).
 * - "Quitar ítem" -> DELETE /api/carro-tickets/{id}/.
 * - "Vaciar carro" -> DELETE /api/carro-tickets/ (con confirmación previa).
 * - "Pagar con Webpay" -> POST /api/compras/webpay/iniciar/ y envío del
 *   formulario con token_ws hacia la URL de pago de Transbank.
 * - "Pago simulado" -> POST /api/compras/pagar/ y redirigir a mis entradas.
 */
(function () {
    'use strict';

    // =========================================================================
    // REFERENCIAS Y CONFIGURACIÓN (inyectada por Django vía data-*)
    // =========================================================================

    const pagina = document.getElementById('paginaCarro');
    if (!pagina) return;

    const contenido = document.getElementById('carroContenido');
    const resumenEntradas = document.getElementById('resumenEntradas');
    const resumenTotal = document.getElementById('resumenTotal');
    const btnWebpay = document.getElementById('btnWebpay');
    const btnPagar = document.getElementById('btnPagar');
    const btnVaciar = document.getElementById('btnVaciar');

    const API_CARRO = pagina.dataset.api;
    const API_PAGAR = pagina.dataset.pagar;
    const API_WEBPAY = pagina.dataset.webpay;
    const URL_MIS_ENTRADAS = pagina.dataset.misEntradas || '/mis-entradas/';
    const URL_CATALOGO = pagina.dataset.catalogo || '/eventos/';

    // Bloquea los botones mientras hay una petición de pago en curso.
    let pagando = false;

    // =========================================================================
    // RENDER
    // =========================================================================

    /** Fila de la tabla para un ítem del carro. */
    function filaItem(item) {
        const sector = item.sector_detalle || {};
        return `
            <tr>
                <td>${Boletos.esc(item.evento_nombre)}</td>
                <td>${Boletos.esc(sector.nombre || '—')}</td>
                <td>${Boletos.fmtMoney(item.precio_unitario)}</td>
                <td>${item.cantidad}</td>
                <td class="fw-bold">${Boletos.fmtMoney(item.subtotal)}</td>
                <td class="text-end text-nowrap">
                    <button type="button" class="btn btn-sm btn-outline-success btn-action btnAgregar"
                            data-item="${item.id}" data-sector="${item.sector}"
                            aria-label="Agregar una entrada más de ${Boletos.esc(sector.nombre || '')}">
                        <i class="bi bi-plus-lg" aria-hidden="true"></i> Agregar 1
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-danger btn-action btnQuitar"
                            data-item="${item.id}"
                            aria-label="Quitar del carro ${Boletos.esc(sector.nombre || '')}">
                        <i class="bi bi-trash" aria-hidden="true"></i> Quitar ítem
                    </button>
                </td>
            </tr>`;
    }

    /** Tabla de ítems del carro. */
    function tablaItems(items) {
        return `
            <div class="table-responsive">
                <table class="table mb-0 align-middle">
                    <caption class="visually-hidden">Ítems reservados en tu carro</caption>
                    <thead>
                        <tr>
                            <th scope="col">Evento</th>
                            <th scope="col">Sector</th>
                            <th scope="col">Precio unitario</th>
                            <th scope="col">Cantidad</th>
                            <th scope="col">Subtotal</th>
                            <th scope="col" class="text-end">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>${items.map(filaItem).join('')}</tbody>
                </table>
            </div>`;
    }

    /** Estado vacío con acceso directo al catálogo. */
    function estadoVacioCarro() {
        return `
            <div class="p-3">
                ${Boletos.estadoVacio('bi-cart-x', 'Tu carro está vacío', 'Explora el catálogo y agrega entradas')}
                <div class="text-center">
                    <a class="btn btn-accent" href="${Boletos.esc(URL_CATALOGO)}">
                        <i class="bi bi-ticket-detailed me-1" aria-hidden="true"></i>Explorar catálogo
                    </a>
                </div>
            </div>`;
    }

    /** Actualiza la tabla, el resumen y el estado de los botones. */
    function pintarCarro(carro) {
        const items = Array.isArray(carro.items) ? carro.items : [];
        const vacio = items.length === 0;

        resumenEntradas.textContent = String(carro.cantidad_entradas || 0);
        resumenTotal.textContent = Boletos.fmtMoney(carro.total || 0);

        contenido.innerHTML = vacio ? estadoVacioCarro() : tablaItems(items);

        btnWebpay.disabled = vacio || pagando;
        btnPagar.disabled = vacio || pagando;
        btnVaciar.disabled = vacio;
    }

    // =========================================================================
    // CARGA DEL CARRO
    // =========================================================================

    /** GET /api/carro-tickets/ -> repinta la pantalla completa. */
    async function cargarCarro() {
        try {
            const carro = await Boletos.apiGet(API_CARRO);
            pintarCarro(carro);
        } catch (err) {
            const mensaje = (err && err.message) || Boletos.extraerMensaje(err);
            contenido.innerHTML = Boletos.estadoVacio(
                'bi-exclamation-triangle',
                'No se pudo cargar tu carro',
                mensaje
            );
            btnWebpay.disabled = true;
            btnPagar.disabled = true;
            btnVaciar.disabled = true;
            Boletos.toast('danger', mensaje);
        }
    }

    // =========================================================================
    // ACCIONES SOBRE LOS ÍTEMS
    // =========================================================================

    /** Agrega una entrada más al mismo sector (el API suma la cantidad). */
    async function agregarUno(boton) {
        boton.disabled = true;
        try {
            const carro = await Boletos.apiPost(API_CARRO, {
                sector: Number(boton.dataset.sector),
                cantidad: 1,
            });
            Boletos.toast('success', 'Se agregó 1 entrada al carro');
            Boletos.refrescarBadgeCarro();
            pintarCarro(carro);
        } catch (err) {
            const mensaje = (err && err.message) || Boletos.extraerMensaje(err);
            Boletos.toast('danger', mensaje);
        } finally {
            boton.disabled = false;
        }
    }

    /** Elimina el ítem completo del carro. */
    async function quitarItem(boton) {
        boton.disabled = true;
        try {
            const carro = await Boletos.apiDelete(`${API_CARRO}${boton.dataset.item}/`);
            Boletos.toast('info', 'Ítem eliminado del carro');
            Boletos.refrescarBadgeCarro();
            pintarCarro(carro);
        } catch (err) {
            const mensaje = (err && err.message) || Boletos.extraerMensaje(err);
            Boletos.toast('danger', mensaje);
            boton.disabled = false;
        }
    }

    // =========================================================================
    // VACIAR CARRO Y PAGO
    // =========================================================================

    /** DELETE /api/carro-tickets/ luego de confirmar con el usuario. */
    async function vaciarCarro() {
        const confirmado = window.confirm('¿Seguro que deseas vaciar tu carro de compras?');
        if (!confirmado) return;

        btnVaciar.disabled = true;
        try {
            const carro = await Boletos.apiDelete(API_CARRO);
            Boletos.toast('info', 'Carro vaciado');
            Boletos.refrescarBadgeCarro();
            pintarCarro(carro);
        } catch (err) {
            const mensaje = (err && err.message) || Boletos.extraerMensaje(err);
            Boletos.toast('danger', mensaje);
            btnVaciar.disabled = false;
        }
    }

    /**
     * POST /api/compras/pagar/: emite los tickets (descuenta stock) y
     * redirige a "Mis entradas" después de mostrar el toast de éxito.
     * (Pago simulado de demostración, alternativa al pago con Webpay.)
     */
    async function pagar() {
        if (pagando) return;
        pagando = true;
        btnWebpay.disabled = true;
        btnPagar.disabled = true;
        btnVaciar.disabled = true;

        const htmlOriginal = btnPagar.innerHTML;
        btnPagar.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>Procesando…';

        try {
            await Boletos.apiPost(API_PAGAR, {});
            Boletos.toast('success', '¡Pago realizado! Entradas emitidas');
            Boletos.refrescarBadgeCarro();
            // Breve pausa para que el usuario lea el mensaje antes de salir.
            window.setTimeout(() => { window.location.href = URL_MIS_ENTRADAS; }, 1200);
        } catch (err) {
            const mensaje = (err && err.message) || Boletos.extraerMensaje(err);
            Boletos.toast('danger', mensaje);
            pagando = false;
            btnPagar.innerHTML = htmlOriginal;
            // Errores de stock (400): recargar para reflejar la disponibilidad real.
            if (err && err.status === 400) {
                await cargarCarro();
            } else {
                btnWebpay.disabled = false;
                btnPagar.disabled = false;
                btnVaciar.disabled = false;
            }
        }
    }

    /**
     * POST /api/compras/webpay/iniciar/: crea la orden PENDIENTE y la
     * transacción en el ambiente de integración de Webpay Plus, y envía el
     * navegador a la página de pago de Transbank mediante un formulario POST
     * con el campo `token_ws`. El resultado vuelve a /pagos/webpay/retorno/.
     */
    async function pagarWebpay() {
        if (pagando) return;
        pagando = true;
        btnWebpay.disabled = true;
        btnPagar.disabled = true;
        btnVaciar.disabled = true;

        const htmlOriginal = btnWebpay.innerHTML;
        btnWebpay.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>Abriendo Webpay…';

        try {
            const transaccion = await Boletos.apiPost(API_WEBPAY, {});
            // Formulario invisible: POST con token_ws hacia la URL de Webpay.
            const formulario = document.createElement('form');
            formulario.method = 'POST';
            formulario.action = transaccion.url;
            const campo = document.createElement('input');
            campo.type = 'hidden';
            campo.name = 'token_ws';
            campo.value = transaccion.token;
            formulario.appendChild(campo);
            document.body.appendChild(formulario);
            formulario.submit();
        } catch (err) {
            const mensaje = (err && err.message) || Boletos.extraerMensaje(err);
            Boletos.toast('danger', mensaje);
            pagando = false;
            btnWebpay.innerHTML = htmlOriginal;
            await cargarCarro();
        }
    }

    // =========================================================================
    // EVENTOS DE INTERFAZ (DELEGACIÓN)
    // =========================================================================

    contenido.addEventListener('click', (evento) => {
        const btnAgregar = evento.target.closest('.btnAgregar');
        if (btnAgregar) {
            agregarUno(btnAgregar);
            return;
        }
        const btnQuitar = evento.target.closest('.btnQuitar');
        if (btnQuitar) quitarItem(btnQuitar);
    });

    btnWebpay.addEventListener('click', pagarWebpay);
    btnPagar.addEventListener('click', pagar);
    btnVaciar.addEventListener('click', vaciarCarro);

    // =========================================================================
    // ARRANQUE
    // =========================================================================

    cargarCarro();
})();
