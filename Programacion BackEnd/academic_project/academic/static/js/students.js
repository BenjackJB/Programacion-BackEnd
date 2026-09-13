/**
 * Students Module - Specific logic for students management
 * Depends on AcademicCore (academic-core.js)
 */

(function() {
    'use strict';

    const { apiFetch, toast, modalManager, TableRenderer, FormHandler, confirmDelete, confirmToggle, escapeHtml, formatDate } = window.AcademicCore;

    let studentsTable;
    let studentFormHandler;

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        initStudentsTable();
        initStudentForm();
        initSearchAndOrderingUI();
        initNewStudentButton();
    }

    function initStudentsTable() {
        studentsTable = new TableRenderer({
            tableId: 'students-table',
            tbodyId: 'students-tbody',
            loadingId: 'students-loading',
            emptyId: 'students-empty',
            countId: 'students-count',
            apiEndpoint: '/api/students/',
            rowClass: 'student-row',
            columns: [
                { key: 'id', class: 'text-center', format: v => `<strong>${v}</strong>` },
                {
                    key: 'full_name',
                    format: (v, student) => `
                        <div class="fw-medium">${escapeHtml(v || '')}</div>
                        <small class="text-muted">Creado: ${formatDate(student.fecha_creacion)}</small>
                    `
                },
                {
                    key: 'courses_count',
                    class: 'text-center',
                    format: (v) => {
                        const count = v ?? 0;
                        return `
                            <span class="badge bg-success student-badge text-white fs-6">
                                <i class="bi bi-journal-bookmark me-1"></i>${count}
                            </span>
                            <div class="text-muted small mt-1">${count} curso${count !== 1 ? 's' : ''}</div>
                        `;
                    }
                },
                {
                    key: 'activo',
                    class: 'text-center',
                    format: v => v
                        ? '<span class="badge bg-success badge-status"><i class="bi bi-check-circle me-1"></i>Activo</span>'
                        : '<span class="badge bg-secondary badge-status"><i class="bi bi-x-circle me-1"></i>Inactivo</span>'
                },
            ],
            actionsColumn: (student) => `
                <td class="text-center">
                    <button type="button" class="btn btn-sm btn-outline-primary action-btn edit-student" data-id="${student.id}" title="Editar" aria-label="Editar estudiante ${student.full_name}"><i class="bi bi-pencil"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-success action-btn toggle-student" data-id="${student.id}" data-active="${student.activo}" title="${student.activo ? 'Desactivar' : 'Activar'}" aria-label="${student.activo ? 'Desactivar' : 'Activar'} estudiante ${student.full_name}"><i class="bi ${student.activo ? 'bi-toggle-on' : 'bi-toggle-off'}"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-danger action-btn delete-student" data-id="${student.id}" title="Borrado lógico" aria-label="Eliminar estudiante ${student.full_name}"><i class="bi bi-trash"></i></button>
                </td>
            `,
            emptyMessage: 'No hay estudiantes registrados',
            emptyIcon: 'bi-people',
        });

        studentsTable.load();
    }

    function initSearchAndOrderingUI() {
        const searchInput = document.getElementById('students-search');
        const orderingSelect = document.getElementById('students-ordering');

        if (searchInput) {
            const debouncedSearch = AcademicCore.debounce((term) => studentsTable.setSearch(term), 300);
            searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value.trim()));
        }

        if (orderingSelect) {
            orderingSelect.addEventListener('change', (e) => {
                if (e.target.value) studentsTable.setOrdering(e.target.value);
            });
        }
    }

    function initStudentForm() {
        studentFormHandler = new FormHandler({
            formId: 'student-form',
            modalId: 'studentModal',
            apiEndpoint: '/api/students/',
            fields: [
                { name: 'first_name', id: 'student-first-name', type: 'text', required: true },
                { name: 'last_name', id: 'student-last-name', type: 'text', required: true },
            ],
            onSuccess: () => studentsTable.load(),
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
        studentFormHandler.bind();
    }

    function initNewStudentButton() {
        const btn = document.getElementById('new-student-btn');
        if (!btn) return;

        btn.addEventListener('click', () => {
            studentFormHandler.clear();
            studentFormHandler.show('Nuevo estudiante');
        });
    }

    document.addEventListener('click', async (e) => {
        const editBtn = e.target.closest('.edit-student');
        const deleteBtn = e.target.closest('.delete-student');
        const toggleBtn = e.target.closest('.toggle-student');

        if (editBtn) {
            await openStudentModal(editBtn.dataset.id);
        } else if (deleteBtn) {
            await deleteStudent(deleteBtn.dataset.id);
        } else if (toggleBtn) {
            await toggleStudent(toggleBtn.dataset.id, toggleBtn.dataset.active === 'true');
        }
    });

    async function openStudentModal(studentId) {
        if (studentId) {
            try {
                const response = await apiFetch(`/api/students/${studentId}/`);
                if (!response) return;

                studentFormHandler.setEditing(studentId, response);
                studentFormHandler.show('Editar estudiante');
            } catch (error) {
                toast.error('Error cargando estudiante: ' + error.message);
            }
        } else {
            studentFormHandler.clear();
            studentFormHandler.show('Nuevo estudiante');
        }
    }

    async function deleteStudent(studentId) {
        confirmDelete('este estudiante', async () => {
            try {
                await apiFetch(`/api/students/${studentId}/`, { method: 'DELETE' });
                studentsTable.load();
            } catch (error) {
                toast.error(error.message);
            }
        });
    }

    async function toggleStudent(studentId, isActive) {
        confirmToggle('este estudiante', isActive, async () => {
            try {
                if (isActive) {
                    await apiFetch(`/api/students/${studentId}/`, {
                        method: 'PATCH',
                        body: JSON.stringify({ activo: false }),
                    });
                } else {
                    await apiFetch(`/api/students/${studentId}/restore/`, { method: 'POST' });
                }
                studentsTable.load();
            } catch (error) {
                toast.error(error.message);
            }
        });
    }

    window.StudentsModule = {
        load: () => studentsTable?.load(),
        openStudentModal,
    };
})();