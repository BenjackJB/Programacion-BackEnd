/**
 * registro.js — Pantalla de creación de cuenta.
 *
 * Lógica:
 * 1. Valida en cliente que las contraseñas coincidan y tengan >= 8 caracteres.
 * 2. Envía POST /api/registro/ con {username, email, password, first_name,
 *    last_name, telefono, rol}.
 * 3. Guarda la sesión (Boletos.setSession) y redirige según el rol.
 * 4. Los errores 400 por campo se pintan bajo cada input (data-error-para)
 *    y se muestra un toast con el primer mensaje.
 */

(function () {
    'use strict';

    const formulario = document.getElementById('registroForm');
    if (!formulario) return; // El script solo aplica en registro.html

    const btnRegistrar = document.getElementById('btnRegistrarse');
    const alertaError = document.getElementById('registroError');
    const errPassword2 = document.getElementById('errPassword2');
    const selectRol = document.getElementById('reg-rol');
    const ayudaRol = document.getElementById('rolAyuda');

    const DESCRIPCION_ROL = {
        espectador: 'Compras entradas a los eventos que te interesan.',
        organizador: 'Crea eventos, administra sectores y revisas tus ventas.',
    };

    // =========================================================================
    // AYUDA DINÁMICA DEL ROL SELECCIONADO
    // =========================================================================

    selectRol.addEventListener('change', function () {
        ayudaRol.textContent = DESCRIPCION_ROL[selectRol.value] || DESCRIPCION_ROL.espectador;
    });

    // =========================================================================
    // PINTADO DE ERRORES DEVUELTOS POR EL API
    // =========================================================================

    /** Limpia todos los mensajes de error (cliente y servidor). */
    function limpiarErrores() {
        formulario.querySelectorAll('[data-error-para]').forEach((el) => { el.textContent = ''; });
        formulario.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
        errPassword2.textContent = '';
        alertaError.textContent = '';
        alertaError.classList.add('d-none');
    }

    /**
     * Pinta los errores 400 de DRF ({campo: ["mensaje"]}) bajo cada input.
     * @returns {{primero:string, sinDestino:string}} mensajes para toast/alerta.
     */
    function pintarErrores(datos) {
        let primero = '';
        let sinDestino = '';
        Object.entries(datos || {}).forEach(([clave, valor]) => {
            const mensaje = Array.isArray(valor) ? valor[0] : String(valor);

            const destino = formulario.querySelector(`[data-error-para="${clave}"]`);
            if (destino) {
                destino.textContent = mensaje;
                if (!primero) primero = `${clave}: ${mensaje}`;
                const input = document.getElementById(`reg-${clave}`);
                if (input) input.classList.add('is-invalid');
            } else if (!sinDestino) {
                // Errores sin campo asociado (detail, non_field_errors, ...).
                sinDestino = mensaje;
            }
        });
        return { primero, sinDestino };
    }

    function cargando(activo) {
        btnRegistrar.disabled = activo;
        const spinner = btnRegistrar.querySelector('.spinner-border');
        if (spinner) spinner.classList.toggle('d-none', !activo);
    }

    // =========================================================================
    // ENVÍO -> POST /api/registro/
    // =========================================================================

    formulario.addEventListener('submit', async function (evento) {
        evento.preventDefault();
        limpiarErrores();

        const password = document.getElementById('reg-password').value;
        const confirmacion = document.getElementById('reg-password2').value;

        // Validación nativa (requeridos, email, largo mínimo).
        if (!formulario.checkValidity()) {
            formulario.classList.add('was-validated');
            return;
        }

        // Las contraseñas deben coincidir.
        if (password !== confirmacion) {
            errPassword2.textContent = 'Las contraseñas no coinciden.';
            document.getElementById('reg-password2').focus();
            return;
        }
        if (password.length < 8) {
            document.getElementById('reg-password').setCustomValidity('Mínimo 8 caracteres.');
            formulario.classList.add('was-validated');
            document.getElementById('reg-password').setCustomValidity('');
            return;
        }

        const telefono = document.getElementById('reg-telefono').value.trim();
        const payload = {
            username: document.getElementById('reg-username').value.trim(),
            email: document.getElementById('reg-email').value.trim(),
            password: password,
            first_name: document.getElementById('reg-first_name').value.trim(),
            last_name: document.getElementById('reg-last_name').value.trim(),
            rol: selectRol.value,
        };
        if (telefono) payload.telefono = telefono; // Opcional: solo se envía si tiene valor.

        cargando(true);
        // Limpia cookies residuales para evitar refrescos de token en cadena.
        Boletos.clearSession();

        try {
            const datos = await Boletos.apiPost('/api/registro/', payload);

            // La respuesta ya trae access + refresh + rol: se inicia sesión.
            Boletos.setSession(datos);
            Boletos.toast('success', 'Cuenta creada correctamente.');

            window.location.assign(
                datos.rol === 'organizador' ? '/organizador/eventos/' : '/eventos/'
            );
        } catch (err) {
            // Errores 400 por campo -> mensaje bajo cada input + toast del primero.
            if (err.status === 400 && err.data && typeof err.data === 'object') {
                const resultado = pintarErrores(err.data);
                if (resultado.sinDestino) {
                    alertaError.textContent = resultado.sinDestino;
                    alertaError.classList.remove('d-none');
                }
                Boletos.toast('danger', resultado.primero || err.message);
            } else {
                alertaError.textContent = err.message || 'No se pudo crear la cuenta.';
                alertaError.classList.remove('d-none');
                Boletos.toast('danger', err.message);
            }
        } finally {
            cargando(false);
        }
    });
})();
