/**
 * Teachers Module - Specific logic for teachers management
 * Depends on AcademicCore (academic-core.js)
 */

(function() {
    'use strict';

    const { apiFetch, toast, modalManager, TableRenderer, FormHandler, confirmDelete, confirmToggle, confirmRestore, escapeHtml, formatDate } = window.AcademicCore;

    let teachersTable;
    let teacherFormHandler;
    let showInactive = false;

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        initTeachersTable();
        initTeacherForm();
        initSearchAndOrderingUI();
        initNewTeacherButton();
        initInactiveFilter();
    }

    function initTeachersTable() {
        teachersTable = new TableRenderer({
            tableId: 'teachers-table',
            tbodyId: 'teachers-tbody',
            loadingId: 'teachers-loading',
            emptyId: 'teachers-empty',
            countId: 'teachers-count',
            apiEndpoint: '/api/teachers/',
            rowClass: 'teacher-row',
            columns: [
                { key: 'id', class: 'text-center', format: v => `<strong>${v}</strong>` },
                {
                    key: 'full_name',
                    format: (v, teacher) => `
                        <div class="fw-medium">${escapeHtml(v || '')}</div>
                        <small class="text-muted">Creado: ${formatDate(teacher.fecha_creacion)}</small>
                    `
                },
                {
                    key: 'sexo',
                    class: 'text-center',
                    format: (v) => {
                        const labels = { 'M': 'Masculino', 'F': 'Femenino', 'O': 'Otro' };
                        const icons = { 'M': 'bi-gender-male', 'F': 'bi-gender-female', 'O': 'bi-gender-ambiguous' };
                        const colors = { 'M': 'bg-primary', 'F': 'bg-danger', 'O': 'bg-secondary' };
                        return `<span class="badge ${colors[v] || 'bg-secondary'}"><i class="bi ${icons[v] || 'bi-person'} me-1"></i>${labels[v] || v}</span>`;
                    }
                },
                {
                    key: 'courses_count',
                    class: 'text-center',
                    format: v => `<span class="badge bg-primary teacher-badge text-white"><i class="bi bi-journal-bookmark me-1"></i>${v ?? 0}</span>`
                },
                {
                    key: 'activo',
                    class: 'text-center',
                    format: v => v
                        ? '<span class="badge bg-success badge-status"><i class="bi bi-check-circle me-1"></i>Activo</span>'
                        : '<span class="badge bg-secondary badge-status"><i class="bi bi-x-circle me-1"></i>Inactivo</span>'
                },
            ],
            actionsColumn: (teacher) => {
                if (showInactive) {
                    return `<td class="text-center">
                        <button type="button" class="btn btn-sm btn-outline-warning action-btn restore-teacher" data-id="${teacher.id}" title="Restaurar" aria-label="Restaurar docente ${teacher.full_name}"><i class="bi bi-arrow-counterclockwise"></i></button>
                    </td>`;
                }
                return `<td class="text-center">
                    <button type="button" class="btn btn-sm btn-outline-primary action-btn edit-teacher" data-id="${teacher.id}" title="Editar" aria-label="Editar docente ${teacher.full_name}"><i class="bi bi-pencil"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-success action-btn toggle-teacher" data-id="${teacher.id}" data-active="${teacher.activo}" title="${teacher.activo ? 'Desactivar' : 'Activar'}" aria-label="${teacher.activo ? 'Desactivar' : 'Activar'} docente ${teacher.full_name}"><i class="bi ${teacher.activo ? 'bi-toggle-on' : 'bi-toggle-off'}"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-danger action-btn delete-teacher" data-id="${teacher.id}" title="Borrado lógico" aria-label="Eliminar docente ${teacher.full_name}"><i class="bi bi-trash"></i></button>
                </td>`;
            },
            emptyMessage: 'No hay docentes registrados',
            emptyIcon: 'bi-person-x',
        });

        teachersTable.load();
    }

    function initSearchAndOrderingUI() {
        const searchInput = document.getElementById('teachers-search');
        const orderingSelect = document.getElementById('teachers-ordering');
        const sexoFilter = document.getElementById('teachers-sexo-filter');

        if (searchInput) {
            const debouncedSearch = AcademicCore.debounce((term) => teachersTable.setSearch(term), 300);
            searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value.trim()));
        }
        if (orderingSelect) {
            orderingSelect.addEventListener('change', (e) => {
                if (e.target.value) teachersTable.setOrdering(e.target.value);
            });
        }
        if (sexoFilter) {
            sexoFilter.addEventListener('change', (e) => teachersTable.setFilter('sexo', e.target.value));
        }
    }

    function initTeacherForm() {
        teacherFormHandler = new FormHandler({
            formId: 'teacher-form',
            modalId: 'teacherModal',
            apiEndpoint: '/api/teachers/',
            fields: [
                { name: 'first_name', id: 'teacher-first-name', type: 'text', required: true },
                { name: 'last_name', id: 'teacher-last-name', type: 'text', required: true },
                { name: 'sexo', id: 'teacher-sexo', type: 'select', required: true },
            ],
            onSuccess: () => teachersTable.load(),
            validate: (data) => {
                if (!data.first_name?.trim()) {
                    toast.error('El nombre es obligatorio');
                    return false;
                }
                if (!data.last_name?.trim()) {
                    toast.error('El apellido es obligatorio');
                    return false;
                }
                return true;
            },
        });
        teacherFormHandler.bind();
    }

    function initNewTeacherButton() {
        const btn = document.getElementById('new-teacher-btn');
        if (!btn) return;

        btn.addEventListener('click', () => {
            teacherFormHandler.clear();
            teacherFormHandler.show('Nuevo docente');
        });
    }

    document.addEventListener('click', async (e) => {
        const editBtn = e.target.closest('.edit-teacher');
        const deleteBtn = e.target.closest('.delete-teacher');
        const toggleBtn = e.target.closest('.toggle-teacher');
        const restoreBtn = e.target.closest('.restore-teacher');

        if (editBtn) {
            await openTeacherModal(editBtn.dataset.id);
        } else if (deleteBtn) {
            await deleteTeacher(deleteBtn.dataset.id);
        } else if (toggleBtn) {
            await toggleTeacher(toggleBtn.dataset.id, toggleBtn.dataset.active === 'true');
        } else if (restoreBtn) {
            await restoreTeacher(restoreBtn.dataset.id);
        }
    });

    async function openTeacherModal(teacherId) {
        if (teacherId) {
            try {
                const response = await apiFetch(`/api/teachers/${teacherId}/`);
                if (!response) return;

                teacherFormHandler.setEditing(teacherId, response);
                teacherFormHandler.show('Editar docente');
            } catch (error) {
                toast.error('Error cargando docente: ' + error.message);
            }
        } else {
            teacherFormHandler.clear();
            teacherFormHandler.show('Nuevo docente');
        }
    }

    async function deleteTeacher(teacherId) {
        confirmDelete('este docente', async () => {
            try {
                await apiFetch(`/api/teachers/${teacherId}/`, { method: 'DELETE' });
                teachersTable.load();
            } catch (error) {
                toast.error(error.message);
            }
        });
    }

    async function toggleTeacher(teacherId, isActive) {
        confirmToggle('este docente', isActive, async () => {
            try {
                if (isActive) {
                    await apiFetch(`/api/teachers/${teacherId}/`, {
                        method: 'PATCH',
                        body: JSON.stringify({ activo: false }),
                    });
                } else {
                    await apiFetch(`/api/teachers/${teacherId}/restore/`, { method: 'POST' });
                }
                teachersTable.load();
            } catch (error) {
                toast.error(error.message);
            }
        });
    }

    async function restoreTeacher(teacherId) {
        confirmRestore('este docente', async () => {
            try {
                await apiFetch(`/api/teachers/${teacherId}/restore/`, { method: 'POST' });
                teachersTable.load();
            } catch (error) {
                toast.error(error.message);
            }
        });
    }

    function initInactiveFilter() {
        const checkbox = document.getElementById('teachers-inactive-filter');
        if (!checkbox) return;
        checkbox.addEventListener('change', (e) => {
            showInactive = e.target.checked;
            teachersTable.setFilter('include_inactive', showInactive ? 'true' : '');
        });
    }

    window.TeachersModule = {
        load: () => teachersTable?.load(),
        openTeacherModal,
    };
})();