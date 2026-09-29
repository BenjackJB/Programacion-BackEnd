/**
 * login.js — Pantalla de inicio de sesión.
 *
 * Lógica:
 * 1. Intercepta el submit del formulario y llama a POST /api/token/.
 * 2. Guarda la sesión JWT con Boletos.setSession(datos).
 * 3. Redirige a ?next= (si es una ruta interna) o según el rol del usuario:
 *    organizador -> /organizador/eventos/ , resto -> /eventos/.
 * 4. Ante un 400 del API pinta el mensaje en #loginError y muestra un toast.
 */

(function () {
    'use strict';

    const formulario = document.getElementById('loginForm');
    if (!formulario) return; // El script solo aplica en login.html

    const btnIngresar = document.getElementById('btnIngresar');
    const alertaError = document.getElementById('loginError');
    const inputPassword = document.getElementById('loginPassword');
    const btnMostrar = document.getElementById('btnMostrarPassword');

    // =========================================================================
    // UTILIDADES DE LA PANTALLA
    // =========================================================================

    /** Destino tras autenticarse: ?next= o data-next (solo rutas internas). */
    function obtenerNext() {
        const parametros = new URLSearchParams(window.location.search);
        const next = parametros.get('next') || formulario.dataset.next || '';
        // Se aceptan únicamente rutas relativas internas (evita open redirects).
        if (next && next.startsWith('/') && !next.startsWith('//')) return next;
        return '';
    }

    function mostrarError(mensaje) {
        alertaError.textContent = mensaje;
        alertaError.classList.remove('d-none');
    }

    function ocultarError() {
        alertaError.textContent = '';
        alertaError.classList.add('d-none');
    }

    /** Activa/desactiva el spinner del botón mientras se espera la respuesta. */
    function cargando(activo) {
        btnIngresar.disabled = activo;
        const spinner = btnIngresar.querySelector('.spinner-border');
        if (spinner) spinner.classList.toggle('d-none', !activo);
    }

    // =========================================================================
    // MOSTRAR / OCULTAR CONTRASEÑA
    // =========================================================================

    btnMostrar.addEventListener('click', function () {
        const visible = inputPassword.type === 'text';
        inputPassword.type = visible ? 'password' : 'text';
        btnMostrar.querySelector('i').className = visible ? 'bi bi-eye' : 'bi bi-eye-slash';
        btnMostrar.setAttribute('aria-pressed', String(!visible));
        btnMostrar.setAttribute('aria-label', visible ? 'Mostrar contraseña' : 'Ocultar contraseña');
        inputPassword.focus();
    });

    // =========================================================================
    // ENVÍO DEL FORMULARIO -> POST /api/token/
    // =========================================================================

    formulario.addEventListener('submit', async function (evento) {
        evento.preventDefault();
        ocultarError();

        // Validación nativa del navegador (campos requeridos).
        if (!formulario.checkValidity()) {
            formulario.classList.add('was-validated');
            return;
        }

        cargando(true);

        // Limpia cookies JWT residuales: evita que un refresh_token obsoleto
        // provoque un 401 en cadena durante el intento de login.
        Boletos.clearSession();

        try {
            const datos = await Boletos.apiPost('/api/token/', {
                username: document.getElementById('loginUsername').value.trim(),
                password: inputPassword.value,
            });

            // Persiste access/refresh/rol en cookies (helpers del núcleo).
            Boletos.setSession(datos);

            const nombre = (datos.usuario && (datos.usuario.nombre_completo || datos.usuario.username)) || '';
            Boletos.toast('success', nombre ? `Bienvenido, ${nombre}.` : 'Sesión iniciada correctamente.');

            // Redirección: next -> organizador -> catálogo.
            const destino = obtenerNext()
                || (datos.rol === 'organizador' ? '/organizador/eventos/' : '/eventos/');
            window.location.assign(destino);
        } catch (err) {
            const mensaje = err.message || 'No se pudo iniciar sesión.';
            mostrarError(mensaje);
            Boletos.toast('danger', mensaje);
        } finally {
            cargando(false);
        }
    });
})();
