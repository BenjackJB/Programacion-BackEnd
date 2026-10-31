/* ==========================================================================
   Dulce Arte — comportamiento del frontend (vanilla JS)
   ========================================================================== */
(function () {
  "use strict";

  /** Obtiene el token CSRF de la cookie o de un input oculto. */
  function csrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match) return match[1];
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  /** Realiza una petición JSON a la API. */
  async function api(url, method, body) {
    const opts = {
      method: method || "GET",
      headers: {
        "X-CSRFToken": csrfToken(),
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    let data = null;
    try { data = await res.json(); } catch (e) { /* sin cuerpo */ }
    if (!res.ok) {
      const msg = (data && (data.detail || data.non_field_errors)) || "Error en la operación";
      throw new Error(Array.isArray(msg) ? msg.join(" ") : msg);
    }
    return data;
  }

  /** Muestra un aviso efímero arriba del contenido. */
  function toast(text, tipo) {
    let box = document.querySelector(".messages");
    if (!box) {
      box = document.createElement("ul");
      box.className = "messages";
      const main = document.querySelector("main");
      if (main) main.prepend(box);
    }
    const li = document.createElement("li");
    li.className = "msg msg--" + (tipo || "info");
    li.textContent = text;
    box.prepend(li);
    setTimeout(() => li.remove(), 5000);
  }

  /* ------------------------------------------------------- Kanban drag -- */
  function initKanban() {
    const board = document.querySelector("[data-kanban]");
    if (!board) return;

    // Mover con botones (avanzar / retroceder)
    board.addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-move]");
      if (!btn) return;
      e.preventDefault();
      const id = btn.dataset.id;
      const paso = btn.dataset.move;
      const url = `/kanban/${id}/mover/`;
      try {
        const fd = new FormData();
        fd.append("paso", paso);
        fd.append("estado", btn.dataset.estado || "");
        const res = await fetch(url, {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken() },
          body: fd,
          credentials: "same-origin",
        });
        if (res.redirected) {
          window.location.href = res.url;
          return;
        }
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error((data && data.detail) || "No se pudo mover");
        window.location.reload();
      } catch (err) {
        toast(err.message, "error");
      }
    });

    // Drag & drop entre columnas
    let dragged = null;
    board.querySelectorAll(".kcard").forEach((card) => {
      card.setAttribute("draggable", "true");
      card.addEventListener("dragstart", () => {
        dragged = card;
        setTimeout(() => card.style.opacity = ".4", 0);
      });
      card.addEventListener("dragend", () => {
        card.style.opacity = "";
        dragged = null;
      });
    });

    board.querySelectorAll(".kanban__body").forEach((zone) => {
      zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.style.background = "rgba(250,120,100,.08)"; });
      zone.addEventListener("dragleave", () => { zone.style.background = ""; });
      zone.addEventListener("drop", async (e) => {
        e.preventDefault();
        zone.style.background = "";
        if (!dragged) return;
        const destino = zone.closest(".kanban__col").dataset.estado;
        const id = dragged.dataset.id;
        const actual = dragged.dataset.estado;
        if (destino === actual) return;
        // Solo un paso cada vez
        const orden = ["recibido", "preparacion", "horneado", "control", "listo"];
        const salto = Math.abs(orden.indexOf(destino) - orden.indexOf(actual));
        if (salto !== 1) {
          toast("Solo se puede mover de a un paso en el flujo.", "warning");
          return;
        }
        try {
          await api(`/api/pedidos/${id}/mover/`, "POST", { estado: destino });
          window.location.reload();
        } catch (err) {
          toast(err.message, "error");
        }
      });
    });
  }

  /* ------------------------------------------------------ Signature pad -- */
  function initSignaturePads() {
    document.querySelectorAll("canvas.sigpad").forEach((canvas) => {
      const ctx = canvas.getContext("2d");
      const ratio = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * ratio;
      canvas.height = rect.height * ratio;
      ctx.scale(ratio, ratio);
      ctx.lineWidth = 2.2;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.strokeStyle = "#000";

      let drawing = false;
      let dirty = false;

      const pos = (e) => {
        const r = canvas.getBoundingClientRect();
        const p = e.touches ? e.touches[0] : e;
        return { x: p.clientX - r.left, y: p.clientY - r.top };
      };
      const start = (e) => { e.preventDefault(); drawing = true; dirty = true; const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
      const move = (e) => { if (!drawing) return; e.preventDefault(); const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); };
      const end = () => { drawing = false; };

      canvas.addEventListener("mousedown", start);
      canvas.addEventListener("mousemove", move);
      window.addEventListener("mouseup", end);
      canvas.addEventListener("touchstart", start, { passive: false });
      canvas.addEventListener("touchmove", move, { passive: false });
      canvas.addEventListener("touchend", end);

      // Botón limpiar asociado
      const wrap = canvas.parentElement;
      const clear = wrap ? wrap.querySelector("[data-clear-signature]") : null;
      if (clear) {
        clear.addEventListener("click", (e) => {
          e.preventDefault();
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          dirty = false;
        });
      }

      // Guardar la firma en un input oculto antes del submit
      const form = canvas.closest("form");
      if (form) {
        form.addEventListener("submit", () => {
          const hidden = form.querySelector("input[name=firma_digital]");
          if (hidden && dirty) hidden.value = canvas.toDataURL("image/png");
        });
      }
    });
  }

  /* --------------------------------------------------- filtros en vivo --- */
  function initLiveFilters() {
    const form = document.querySelector("[data-autosubmit]");
    if (!form) return;
    let t;
    form.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(() => form.submit(), 450);
    });
    form.addEventListener("change", () => form.submit());
  }

  /* --------------------------------------------------------- arranque ---- */
  document.addEventListener("DOMContentLoaded", () => {
    initKanban();
    initSignaturePads();
    initLiveFilters();

    // Cerrar mensajes automáticamente
    setTimeout(() => {
      document.querySelectorAll(".messages .msg").forEach((m) => {
        m.style.transition = "opacity .4s";
        m.style.opacity = "0";
        setTimeout(() => m.remove(), 420);
      });
    }, 6000);
  });

  // Exponer helpers por si se necesitan en plantillas
  window.DulceArte = { api, toast, csrfToken };
})();
