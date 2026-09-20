/**
 * Asignaturas Module - Specific logic for subject management
 * Depends on AcademicCore (academic-core.js)
 * Lectura publica (sin login); ediciones exigen JWT/sesion.
 */

(function() {
    'use strict';

    const { apiFetch, toast, TableRenderer, FormHandler, confirmDelete, confirmToggle, confirmRestore, escapeHtml, formatDate } = window.AcademicCore;

    let asignaturasTable;
    let asignaturaFormHandler;
    let showInactive = false;

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        initAsignaturasTable();
        initAsignaturaForm();
        initSearchAndOrderingUI();
        initNewAsignaturaButton();
        initInactiveFilter();
    }

    function initAsignaturasTable() {
        asignaturasTable = new TableRenderer({
            tableId: 'asignaturas-table',
            tbodyId: 'asignaturas-tbody',
            loadingId: 'asignaturas-loading',
            emptyId: 'asignaturas-empty',
            countId: 'asignaturas-count',
            apiEndpoint: '/api/asignaturas/',
            rowClass: 'asignatura-row',
            columns: [
                { key: 'id', class: 'text-center', format: v => `<strong>${v}</strong>` },
                {
                    key: 'nombre',
                    format: (v, asignatura) => `
                        <div class="fw-medium">${escapeHtml(v || '')}</div>
                        <small class="text-muted">${escapeHtml(asignatura.codigo || 'Sin codigo')} - Creado: ${formatDate(asignatura.fecha_creacion)}</small>
                    `
                },
                {
                    key: 'tipo',
                    class: 'text-center',
                    format: (v) => {
                        const labels = { 'O': 'Obligatoria', 'E': 'Electiva' };
                        const icons = { 'O': 'bi-bookmark-check', 'E': 'bi-bookmark-star' };
                        const colors = { 'O': 'bg-primary', 'E': 'bg-info' };
                        return `<span class="badge ${colors[v] || 'bg-secondary'}"><i class="bi ${icons[v] || 'bi-book'} me-1"></i>${labels[v] || v}</span>`;
                    }
                },
                {
                    key: 'nivel',
                    class: 'text-center',
                    format: v => {
                        const labels = { '1': 'Primer ano', '2': 'Segundo ano', '3': 'Tercer ano', '4': 'Cuarto ano', '5': 'Quinto ano' };
                        return `<span class="badge bg-secondary"><i class="bi bi-bar-chart me-1"></i>${labels[v] || v}</span>`;
                    }
                },
                {
                    key: 'creditos',
                    class: 'text-center',
                    format: v => `<span class="badge badge-status bg-warning text-dark"><i class="bi bi-award me-1"></i>${v ?? 0} cr.</span>`
                },
                {
                    key: 'activo',
                    class: 'text-center',
                    format: v => v
                        ? '<span class="badge bg-success badge-status"><i class="bi bi-check-circle me-1"></i>Activo</span>'
                        : '<span class="badge bg-secondary badge-status"><i class="bi bi-x-circle me-1"></i>Inactivo</span>'
                },
            ],
            actionsColumn: (asignatura) => {
                if (showInactive) {
                    return `<td class="text-center">
                        <button type="button" class="btn btn-sm btn-outline-warning action-btn restore-asignatura" data-id="${asignatura.id}" title="Restaurar" aria-label="Restaurar asignatura ${asignatura.nombre}"><i class="bi bi-arrow-counterclockwise"></i></button>
                    </td>`;
                }
                return `<td class="text-center">
                    <button type="button" class="btn btn-sm btn-outline-primary action-btn edit-asignatura" data-id="${asignatura.id}" title="Editar" aria-label="Editar asignatura ${asignatura.nombre}"><i class="bi bi-pencil"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-success action-btn toggle-asignatura" data-id="${asignatura.id}" data-active="${asignatura.activo}" title="${asignatura.activo ? 'Desactivar' : 'Activar'}" aria-label="${asignatura.activo ? 'Desactivar' : 'Activar'} asignatura ${asignatura.nombre}"><i class="bi ${asignatura.activo ? 'bi-toggle-on' : 'bi-toggle-off'}"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-danger action-btn delete-asignatura" data-id="${asignatura.id}" title="Borrado logico" aria-label="Eliminar asignatura ${asignatura.nombre}"><i class="bi bi-trash"></i></button>
                </td>`;
            },
            emptyMessage: 'No hay asignaturas registradas',
            emptyIcon: 'bi-book',
        });

        asignaturasTable.load();
    }

    function initSearchAndOrderingUI() {
        const searchInput = document.getElementById('asignaturas-search');
        const orderingSelect = document.getElementById('asignaturas-ordering');
        const tipoFilter = document.getElementById('asignaturas-tipo-filter');
        const nivelFilter = document.getElementById('asignaturas-nivel-filter');

        if (searchInput) {
            const debouncedSearch = AcademicCore.debounce((term) => asignaturasTable.setSearch(term), 300);
            searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value.trim()));
        }
        if (orderingSelect) {
            orderingSelect.addEventListener('change', (e) => {
                if (e.target.value) asignaturasTable.setOrdering(e.target.value);
            });
        }
        if (tipoFilter) {
            tipoFilter.addEventListener('change', (e) => asignaturasTable.setFilter('tipo', e.target.value));
        }
        if (nivelFilter) {
            nivelFilter.addEventListener('change', (e) => asignaturasTable.setFilter('nivel', e.target.value));
        }
    }

    function initAsignaturaForm() {
        asignaturaFormHandler = new FormHandler({
            formId: 'asignatura-form',
            modalId: 'asignaturaModal',
            apiEndpoint: '/api/asignaturas/',
            fields: [
                { name: 'codigo', id: 'asignatura-codigo', type: 'text' },
                { name: 'nombre', id: 'asignatura-nombre', type: 'text', required: true },
                { name: 'descripcion', id: 'asignatura-descripcion', type: 'text' },
                { name: 'tipo', id: 'asignatura-tipo', type: 'select', required: true },
                { name: 'nivel', id: 'asignatura-nivel', type: 'select', required: true },
                { name: 'creditos', id: 'asignatura-creditos', type: 'number' },
            ],
            onSuccess: () => asignaturasTable.load(),
            validate: (data) => {
                if (!data.nombre?.trim()) {
                    toast.error('El nombre es obligatorio');
                    return false;
                }
                if (!['O', 'E'].includes(data.tipo)) {
                    toast.error('Selecciona un tipo valido');
                    return false;
                }
                if (!['1', '2', '3', '4', '5'].includes(String(data.nivel))) {
                    toast.error('Selecciona un nivel valido');
                    return false;
                }
                return true;
            },
        });
        asignaturaFormHandler.bind();
    }

    function initNewAsignaturaButton() {
        const btn = document.getElementById('new-asignatura-btn');
        if (!btn) return;

        btn.addEventListener('click', () => {
            asignaturaFormHandler.clear();
            asignaturaFormHandler.show('Nueva asignatura');
        });
    }

    document.addEventListener('click', async (e) => {
        const editBtn = e.target.closest('.edit-asignatura');
        const deleteBtn = e.target.closest('.delete-asignatura');
        const toggleBtn = e.target.closest('.toggle-asignatura');
        const restoreBtn = e.target.closest('.restore-asignatura');

        if (editBtn) {
            await openAsignaturaModal(editBtn.dataset.id);
        } else if (deleteBtn) {
            await deleteAsignatura(deleteBtn.dataset.id);
        } else if (toggleBtn) {
            await toggleAsignatura(toggleBtn.dataset.id, toggleBtn.dataset.active === 'true');
        } else if (restoreBtn) {
            await restoreAsignatura(restoreBtn.dataset.id);
        }
    });

    async function openAsignaturaModal(asignaturaId) {
        if (asignaturaId) {
            try {
                const response = await apiFetch(`/api/asignaturas/${asignaturaId}/`);
                if (!response) return;

                asignaturaFormHandler.setEditing(asignaturaId, response);
                asignaturaFormHandler.show('Editar asignatura');
            } catch (error) {
                toast.error('Error cargando asignatura: ' + error.message);
            }
        } else {
            asignaturaFormHandler.clear();
            asignaturaFormHandler.show('Nueva asignatura');
        }
    }

    async function deleteAsignatura(asignaturaId) {
        confirmDelete('esta asignatura', async () => {
            try {
                await apiFetch(`/api/asignaturas/${asignaturaId}/`, { method: 'DELETE' });
                asignaturasTable.load();
            } catch (error) {
                toast.error(error.message);
            }
        });
    }

    async function toggleAsignatura(asignaturaId, isActive) {
        confirmToggle('esta asignatura', isActive, async () => {
            try {
                if (isActive) {
                    await apiFetch(`/api/asignaturas/${asignaturaId}/`, {
                        method: 'PATCH',
                        body: JSON.stringify({ activo: false }),
                    });
                } else {
                    await apiFetch(`/api/asignaturas/${asignaturaId}/restore/`, { method: 'POST' });
                }
                asignaturasTable.load();
            } catch (error) {
                toast.error(error.message);
            }
        });
    }

    async function restoreAsignatura(asignaturaId) {
        confirmRestore('esta asignatura', async () => {
            try {
                await apiFetch(`/api/asignaturas/${asignaturaId}/restore/`, { method: 'POST' });
                asignaturasTable.load();
            } catch (error) {
                toast.error(error.message);
            }
        });
    }

    function initInactiveFilter() {
        const checkbox = document.getElementById('asignaturas-inactive-filter');
        if (!checkbox) return;
        checkbox.addEventListener('change', (e) => {
            showInactive = e.target.checked;
            asignaturasTable.setFilter('include_inactive', showInactive ? 'true' : '');
        });
    }

    window.AsignaturasModule = {
        load: () => asignaturasTable?.load(),
        openAsignaturaModal,
    };
})();