/**
 * Núcleo JavaScript del sistema de venta de entradas.
 *
 * Responsabilidades:
 * - Gestión de la sesión JWT (cookies access_token / refresh_token).
 * - Wrapper de fetch() que agrega el header Authorization y renueva el
 *   access token automáticamente ante un 401 (refresh token).
 * - Utilidades de interfaz: toasts, formato de dinero/fechas, badges,
 *   estados vacíos, paginación y badge del carro persistente.
 *
 * Todas las pantallas (templates) consumen este archivo vía base.html.
 */

window.Boletos = (function () {
    'use strict';

    // =========================================================================
    // COOKIES (la sesión JWT vive en cookies legibles por JS y por Django)
    // =========================================================================

    function getCookie(name) {
        const valor = `; ${document.cookie}`;
        const partes = valor.split(`; ${name}=`);
        if (partes.length === 2) return partes.pop().split(';').shift();
        return null;
    }

    function setCookie(name, value, dias) {
        let expires = '';
        if (dias) {
            expires = `; expires=${new Date(Date.now() + dias * 864e5).toUTCString()}`;
        }
        document.cookie = `${name}=${encodeURIComponent(value)}${expires}; path=/; SameSite=Lax`;
    }

    function deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Lax`;
    }

    // =========================================================================
    // SESIÓN JWT
    // =========================================================================

    function getAccess() { return getCookie('access_token'); }
    function getRefresh() { return getCookie('refresh_token'); }
    function getRol() { return getCookie('usuario_rol') || ''; }
    function isAuthenticated() { return !!getAccess(); }

    /**
     * Guarda la sesión devuelta por /api/token/ o /api/registro/.
     * @param {{access:string, refresh:string, rol:string, usuario?:object}} data
     */
    function setSession(data) {
        // Las cookies viven más que el token: la expiración real la valida Django/JWT.
        setCookie('access_token', data.access, 1);
        if (data.refresh) setCookie('refresh_token', data.refresh, 7);
        if (data.rol) setCookie('usuario_rol', data.rol, 7);
        const usuario = data.usuario || {};
        const nombre = usuario.nombre_completo || usuario.username || '';
        if (nombre) setCookie('usuario_nombre', nombre, 7);
    }

    function clearSession() {
        ['access_token', 'refresh_token', 'usuario_rol', 'usuario_nombre'].forEach(deleteCookie);
    }

    function logout() {
        clearSession();
        window.location.href = '/logout/';
    }

    // =========================================================================
    // REQUESTS AL API (fetch + JWT + auto-refresh)
    // =========================================================================

    function extraerMensaje(error) {
        if (!error) return 'Error inesperado.';
        if (typeof error === 'string') return error;
        const datos = error.data || {};
        if (datos.detail) return datos.detail;
        if (error.status === 401) return 'Tu sesión expiró. Inicia sesión nuevamente.';
        if (error.status === 403) return datos.detail || 'No tienes permisos para realizar esta acción.';
        // Primer error de campo devuelto por DRF.
        const clave = Object.keys(datos)[0];
        if (clave) {
            const valor = datos[clave];
            return Array.isArray(valor) ? `${clave}: ${valor[0]}` : `${clave}: ${valor}`;
        }
        return 'No se pudo completar la operación.';
    }

    async function parseJSON(respuesta) {
        const texto = await respuesta.text();
        if (!texto) return null;
        try { return JSON.parse(texto); } catch (e) { return { detail: texto }; }
    }

    /** POST /api/token/refresh/ -> nuevo access token (o null si falla). */
    async function renovarAccess() {
        const refresh = getRefresh();
        if (!refresh) return null;
        try {
            const respuesta = await fetch('/api/token/refresh/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh }),
            });
            if (!respuesta.ok) return null;
            const datos = await respuesta.json();
            setSession({ access: datos.access });
            return datos.access;
        } catch (e) {
            return null;
        }
    }

    /**
     * Fetch estandarizado contra el API interno.
     * - Agrega Authorization: Bearer <access>.
     * - Ante 401 intenta renovar el token y reintenta una vez.
     * - Lanza un objeto {status, data} cuando la respuesta no es 2xx.
     */
    async function apiFetch(url, opciones = {}) {
        const opcionesFinales = Object.assign({
            headers: {},
        }, opciones);

        opcionesFinales.headers = Object.assign(
            { 'Accept': 'application/json' },
            opcionesFinales.headers
        );

        if (opcionesFinales.body && typeof opcionesFinales.body !== 'string') {
            opcionesFinales.headers['Content-Type'] = 'application/json';
            opcionesFinales.body = JSON.stringify(opcionesFinales.body);
        }

        const access = getAccess();
        const teniaSesion = !!access;
        if (access) opcionesFinales.headers['Authorization'] = `Bearer ${access}`;

        let respuesta = await fetch(url, opcionesFinales);

        // Reintento automático con refresh token cuando el access venció.
        if (respuesta.status === 401 && getRefresh()) {
            const nuevoAccess = await renovarAccess();
            if (nuevoAccess) {
                opcionesFinales.headers['Authorization'] = `Bearer ${nuevoAccess}`;
                respuesta = await fetch(url, opcionesFinales);
            }
        }

        const datos = await parseJSON(respuesta);

        if (!respuesta.ok) {
            // Solo se cierra la sesión (y se redirige) si había una sesión previa:
            // un login con credenciales inválidas debe mostrar su error en pantalla.
            if (respuesta.status === 401 && teniaSesion) {
                clearSession();
                const destino = encodeURIComponent(window.location.pathname + window.location.search);
                window.location.href = `/login/?next=${destino}`;
            }
            const error = Object.assign(new Error(extraerMensaje({ status: respuesta.status, data: datos })), {
                status: respuesta.status,
                data: datos,
            });
            throw error;
        }

        return datos;
    }

    const apiGet = (url, params) => apiFetch(montarConsulta(url, params), { method: 'GET' });
    const apiPost = (url, body) => apiFetch(url, { method: 'POST', body });
    const apiPut = (url, body) => apiFetch(url, { method: 'PUT', body });
    const apiPatch = (url, body) => apiFetch(url, { method: 'PATCH', body });
    const apiDelete = (url, body) => apiFetch(url, { method: 'DELETE', body });

    /** Construye la URL con query string a partir de un objeto de parámetros. */
    function montarConsulta(url, params) {
        if (!params) return url;
        const limpio = Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined);
        if (!limpio.length) return url;
        const consulta = new URLSearchParams(limpio).toString();
        return `${url}${url.includes('?') ? '&' : '?'}${consulta}`;
    }

    // =========================================================================
    // UTILIDADES DE INTERFAZ
    // =========================================================================

    function toast(tipo, mensaje) {
        let contenedor = document.getElementById('toast-container');
        if (!contenedor) {
            contenedor = document.createElement('div');
            contenedor.id = 'toast-container';
            contenedor.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(contenedor);
        }
        const iconos = {
            success: 'check-circle-fill text-success',
            danger: 'exclamation-triangle-fill text-danger',
            info: 'info-circle-fill text-info',
            warning: 'exclamation-circle-fill text-warning',
        };
        const id = `toast-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
        const plantilla = document.createElement('div');
        plantilla.innerHTML = `
            <div id="${id}" class="toast align-items-center border-0 bg-white shadow" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi ${iconos[tipo] || iconos.info} me-2"></i>${mensaje}
                    </div>
                    <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Cerrar"></button>
                </div>
            </div>`;
        contenedor.appendChild(plantilla.firstElementChild);
        const elemento = document.getElementById(id);
        new bootstrap.Toast(elemento, { delay: 4000 }).show();
        elemento.addEventListener('hidden.bs.toast', () => elemento.remove());
    }

    /** Formato chileno: $ 12.500 */
    function fmtMoney(valor) {
        const numero = Number(valor || 0);
        return `$ ${new Intl.NumberFormat('es-CL').format(numero)}`;
    }

    /** Fecha ISO -> "20 may 2026" (+ hora si se solicita). */
    function fmtFecha(iso, conHora) {
        if (!iso) return '-';
        const fecha = new Date(iso);
        if (Number.isNaN(fecha.getTime())) return iso;
        const opciones = { day: '2-digit', month: 'short', year: 'numeric' };
        if (conHora) Object.assign(opciones, { hour: '2-digit', minute: '2-digit' });
        return new Intl.DateTimeFormat('es-CL', opciones).format(fecha);
    }

    /** Iniciales del usuario para avatares. */
    function iniciales(nombre) {
        if (!nombre) return '?';
        return nombre.split(/\s+/).slice(0, 2).map((p) => p[0]).join('').toUpperCase();
    }

    const ESTADOS_ORDEN = {
        PENDIENTE: 'Pendiente',
        PAGADO: 'Pagado',
        ENTREGADO: 'Entregado',
        CANCELADO: 'Cancelado',
    };
    const ESTADOS_TICKET = {
        VALIDO: 'Válido',
        INGRESADO: 'Ingresó',
        CANCELADO: 'Cancelado',
    };
    const CATEGORIAS = {
        concierto: 'Concierto',
        festival: 'Festival',
        teatro: 'Teatro / Escena',
        deporte: 'Deporte',
        otro: 'Otro',
    };
    const ESTADOS_EVENTO = {
        proximo: 'Próximo',
        en_venta: 'En venta',
        finalizado: 'Finalizado',
        cancelado: 'Cancelado',
    };

    function badgeEstado(estado, mapa) {
        const texto = (mapa || ESTADOS_ORDEN)[estado] || estado || '-';
        return `<span class="badge badge-estado ${estado}">${texto}</span>`;
    }

    function estadoVacio(icono, titulo, detalle) {
        return `
            <div class="empty-state">
                <i class="bi ${icono} d-block"></i>
                <h5 class="mb-1">${titulo}</h5>
                <p class="mb-0 text-muted">${detalle || ''}</p>
            </div>`;
    }

    /** Escapa texto proveniente del API antes de inyectarlo al HTML. */
    function esc(valor) {
        if (valor === null || valor === undefined) return '';
        return String(valor)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    /** Renderiza la paginación de respuestas DRF ({count, next, previous}). */
    function paginacion(meta, paginaActual, totalPaginas, callback) {
        if (totalPaginas <= 1) return '';
        let items = '';
        for (let p = 1; p <= totalPaginas; p++) {
            items += `<li class="page-item ${p === paginaActual ? 'active' : ''}">
                <a class="page-link" href="#" data-pagina="${p}">${p}</a></li>`;
        }
        return `<nav aria-label="Paginación"><ul class="pagination justify-content-center mt-4">${items}</ul></nav>`;
    }

    /** Actualiza el badge del carro en el navbar (solo espectadores). */
    async function refrescarBadgeCarro() {
        const badge = document.getElementById('cartBadge');
        if (!badge || getRol() !== 'espectador' || !isAuthenticated()) return;
        try {
            const carro = await apiGet('/api/carro-tickets/');
            const cantidad = carro.cantidad_entradas || 0;
            badge.textContent = cantidad;
            badge.classList.toggle('d-none', cantidad === 0);
        } catch (e) {
            badge.classList.add('d-none');
        }
    }

    /** Convierte un FormData en objeto plano (para enviar JSON). */
    function formDataAObjeto(form) {
        const objeto = {};
        new FormData(form).forEach((valor, clave) => { objeto[clave] = valor; });
        return objeto;
    }

    // =========================================================================
    // ARRANQUE GLOBAL
    // =========================================================================

    document.addEventListener('DOMContentLoaded', () => {
        refrescarBadgeCarro();
    });

    return {
        getCookie, setCookie, deleteCookie,
        getAccess, getRefresh, getRol, isAuthenticated,
        setSession, clearSession, logout,
        apiFetch, apiGet, apiPost, apiPut, apiPatch, apiDelete, montarConsulta,
        toast, fmtMoney, fmtFecha, iniciales, badgeEstado, estadoVacio, esc,
        paginacion, refrescarBadgeCarro, formDataAObjeto, extraerMensaje,
        ESTADOS_ORDEN, ESTADOS_TICKET, CATEGORIAS, ESTADOS_EVENTO,
    };
})();
