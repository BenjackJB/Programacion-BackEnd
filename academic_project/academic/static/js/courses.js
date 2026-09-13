/**
 * Courses Module - Specific logic for courses management
 * Depends on AcademicCore (academic-core.js)
 */

(function() {
    'use strict';

    const { apiFetch, toast, modalManager, TableRenderer, FormHandler, initSearchAndOrdering, confirmDelete, confirmToggle, escapeHtml, formatDate } = window.AcademicCore;

    let coursesTable;
    let courseFormHandler;
    let studentsFormHandler;

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        initCoursesTable();
        initCourseForm();
        initStudentsModal();
        initSearchAndOrderingUI();
        initNewCourseButton();
    }

    function initCoursesTable() {
        coursesTable = new TableRenderer({
            tableId: 'courses-table',
            tbodyId: 'courses-tbody',
            loadingId: 'courses-loading',
            emptyId: 'courses-empty',
            countId: 'courses-count',
            apiEndpoint: '/api/courses/',
            rowClass: 'course-row',
            columns: [
                { key: 'id', class: 'text-center', format: v => `<strong>${v}</strong>` },
                {
                    key: 'name',
                    format: (v, course) => `
                        <div class="fw-medium">${escapeHtml(v)}</div>
                        <small class="text-muted">Creado: ${formatDate(course.fecha_creacion)}</small>
                    `
                },
                {
                    key: 'teacher_name',
                    format: (v, course) => {
                        const name = v || course.teacher?.full_name || 'Sin asignar';
                        return `<span class="badge bg-primary teacher-badge text-white">${escapeHtml(name)}</span>`;
                    }
                },
                {
                    key: 'students_count',
                    format: (v, course) => {
                        const students = course.students || [];
                        const badges = students.length
                            ? students.map(s => `<span class="badge bg-success-subtle text-success-emphasis me-1 mb-1">${escapeHtml(s.full_name)}</span>`).join('')
                            : '<span class="text-muted">Sin alumnos</span>';
                        return `
                            <div class="small mb-1">${v || 0} alumno${(v || 0) !== 1 ? 's' : ''}</div>
                            <div>${badges}</div>
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
            actionsColumn: (course) => `
                <td class="text-center">
                    <button type="button" class="btn btn-sm btn-outline-primary action-btn edit-course" data-id="${course.id}" title="Editar" aria-label="Editar curso ${course.name}"><i class="bi bi-pencil"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-info action-btn manage-students" data-id="${course.id}" data-name="${escapeHtml(course.name)}" title="Gestionar estudiantes" aria-label="Gestionar estudiantes de ${course.name}"><i class="bi bi-person-plus"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-success action-btn toggle-course" data-id="${course.id}" data-active="${course.activo}" title="${course.activo ? 'Desactivar' : 'Activar'}" aria-label="${course.activo ? 'Desactivar' : 'Activar'} curso ${course.name}"><i class="bi ${course.activo ? 'bi-toggle-on' : 'bi-toggle-off'}"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-danger action-btn delete-course" data-id="${course.id}" title="Borrado lógico" aria-label="Eliminar curso ${course.name}"><i class="bi bi-trash"></i></button>
                </td>
            `,
            emptyMessage: 'No hay cursos registrados',
            emptyIcon: 'bi-journal-x',
        });

        coursesTable.load();
    }

    function initSearchAndOrderingUI() {
        const searchInput = document.getElementById('courses-search');
        const orderingSelect = document.getElementById('courses-ordering');

        if (searchInput) {
            const debouncedSearch = AcademicCore.debounce((term) => coursesTable.setSearch(term), 300);
            searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value.trim()));
        }

        if (orderingSelect) {
            orderingSelect.addEventListener('change', (e) => {
                if (e.target.value) coursesTable.setOrdering(e.target.value);
            });
        }
    }

    function initCourseForm() {
        courseFormHandler = new FormHandler({
            formId: 'course-form',
            modalId: 'courseModal',
            apiEndpoint: '/api/courses/',
            fields: [
                { name: 'name', id: 'course-name', type: 'text', required: true },
                { name: 'teacher_id', id: 'course-teacher', type: 'number', required: true },
            ],
            onSuccess: () => coursesTable.load(),
            validate: (data) => {
                if (!data.name?.trim()) {
                    toast.error('El nombre del curso es obligatorio');
                    return false;
                }
                if (!data.teacher_id) {
                    toast.error('Debes seleccionar un docente');
                    return false;
                }
                return true;
            },
        });
        courseFormHandler.bind();
    }

    async function loadTeachersForSelect(selectedId = null) {
        const select = document.getElementById('course-teacher');
        if (!select) return;

        select.innerHTML = '<option value="">Selecciona un docente</option>';

        try {
            const response = await apiFetch('/api/teachers/');
            if (!response) return;

            const teachers = response.results || response;
            teachers.forEach(teacher => {
                const option = document.createElement('option');
                option.value = teacher.id;
                option.textContent = teacher.full_name || `${teacher.first_name} ${teacher.last_name}`;
                if (String(selectedId) === String(teacher.id)) option.selected = true;
                select.appendChild(option);
            });
        } catch (error) {
            toast.error('Error cargando docentes: ' + error.message);
        }
    }

    function initNewCourseButton() {
        const btn = document.getElementById('new-course-btn');
        if (!btn) return;

        btn.addEventListener('click', async () => {
            await loadTeachersForSelect();
            courseFormHandler.clear();
            courseFormHandler.show('Nuevo curso');
        });
    }

    // Event delegation for table actions
    document.addEventListener('click', async (e) => {
        const editBtn = e.target.closest('.edit-course');
        const manageBtn = e.target.closest('.manage-students');
        const deleteBtn = e.target.closest('.delete-course');
        const toggleBtn = e.target.closest('.toggle-course');

        if (editBtn) {
            await openCourseModal(editBtn.dataset.id);
        } else if (manageBtn) {
            await openStudentsModal(manageBtn.dataset.id, manageBtn.dataset.name);
        } else if (deleteBtn) {
            await deleteCourse(deleteBtn.dataset.id);
        } else if (toggleBtn) {
            await toggleCourse(toggleBtn.dataset.id, toggleBtn.dataset.active === 'true');
        }
    });

    async function openCourseModal(courseId) {
        await loadTeachersForSelect();

        if (courseId) {
            try {
                const response = await apiFetch(`/api/courses/${courseId}/`);
                if (!response) return;

                courseFormHandler.setEditing(courseId, response);
                courseFormHandler.show('Editar curso');
            } catch (error) {
                toast.error('Error cargando curso: ' + error.message);
            }
        } else {
            courseFormHandler.clear();
            courseFormHandler.show('Nuevo curso');
        }
    }

    async function deleteCourse(courseId) {
        confirmDelete('este curso', async () => {
            try {
                await apiFetch(`/api/courses/${courseId}/`, { method: 'DELETE' });
                coursesTable.load();
            } catch (error) {
                toast.error(error.message);
            }
        });
    }

    async function toggleCourse(courseId, isActive) {
        confirmToggle('este curso', isActive, async () => {
            try {
                if (isActive) {
                    await apiFetch(`/api/courses/${courseId}/`, {
                        method: 'PATCH',
                        body: JSON.stringify({ activo: false }),
                    });
                } else {
                    await apiFetch(`/api/courses/${courseId}/restore/`, { method: 'POST' });
                }
                coursesTable.load();
            } catch (error) {
                toast.error(error.message);
            }
        });
    }

    // Students Modal for Course
    function initStudentsModal() {
        studentsFormHandler = new FormHandler({
            formId: 'students-form',
            modalId: 'studentsModal',
            apiEndpoint: '/api/enrollments/',
            fields: [],
            onSuccess: () => {
                modalManager.hide('studentsModal');
                coursesTable.load();
            },
        });
        studentsFormHandler.bind();
    }

    async function openStudentsModal(courseId, courseName) {
        const modalEl = document.getElementById('studentsModal');
        if (!modalEl) return;

        const studentsList = document.getElementById('course-students');
        const titleEl = document.getElementById('studentsModalTitle');
        const courseIdInput = document.getElementById('students-course-id');

        if (titleEl) titleEl.textContent = `Estudiantes de ${courseName}`;
        if (courseIdInput) courseIdInput.value = courseId;
        if (studentsList) studentsList.innerHTML = '<div class="p-3 text-muted"><div class="spinner-border spinner-border-sm me-2" role="status"></div>Cargando estudiantes...</div>';

        try {
            const [studentsResponse, enrollmentsResponse] = await Promise.all([
                apiFetch('/api/students/'),
                apiFetch(`/api/enrollments/?course_id=${courseId}`),
            ]);

            if (!studentsResponse || !enrollmentsResponse) return;

            const students = studentsResponse.results || studentsResponse;
            const enrollments = enrollmentsResponse.results || enrollmentsResponse;
            const enrollmentByStudent = new Map(
                enrollments.map(enrollment => [String(enrollment.student.id), enrollment])
            );

            if (!studentsList) return;
            studentsList.innerHTML = '';

            const activeStudents = students.filter(s => s.activo);
            if (!activeStudents.length) {
                studentsList.innerHTML = '<div class="p-3 text-muted">No hay estudiantes activos</div>';
            } else {
                activeStudents.forEach(student => {
                    const studentId = String(student.id);
                    const isEnrolled = enrollmentByStudent.get(studentId)?.activo === true;
                    const option = document.createElement('label');
                    option.className = 'student-option d-flex align-items-center justify-content-between gap-2 p-2 border-bottom';
                    option.innerHTML = `
                        <span class="d-flex align-items-center gap-2">
                            <input class="form-check-input student-checkbox" type="checkbox" value="${studentId}" data-name="${escapeHtml(student.full_name)}" ${isEnrolled ? 'checked' : ''}>
                            <span>${escapeHtml(student.full_name || `${student.first_name} ${student.last_name}`)}</span>
                        </span>
                        <span class="badge ${isEnrolled ? 'bg-success' : 'bg-secondary'} student-status">${isEnrolled ? 'Inscrito' : 'No inscrito'}</span>
                    `;
                    const checkbox = option.querySelector('.student-checkbox');
                    checkbox.addEventListener('change', () => {
                        const status = option.querySelector('.student-status');
                        status.textContent = checkbox.checked ? 'Inscrito' : 'No inscrito';
                        status.className = `badge ${checkbox.checked ? 'bg-success' : 'bg-secondary'} student-status`;
                    });
                    studentsList.appendChild(option);
                });
            }

            if (studentsList) {
                studentsList.dataset.enrollments = JSON.stringify(Object.fromEntries(enrollmentByStudent));
                studentsList.dataset.courseId = courseId;
            }

            modalManager.show('studentsModal');
        } catch (error) {
            toast.error('Error cargando estudiantes: ' + error.message);
        }
    }

    // Override students form submit
    document.addEventListener('submit', async (e) => {
        if (e.target.id !== 'students-form') return;
        e.preventDefault();

        const studentsList = document.getElementById('course-students');
        const courseId = document.getElementById('students-course-id')?.value;
        if (!studentsList || !courseId) return;

        const enrollments = JSON.parse(studentsList.dataset.enrollments || '{}');
        const checkboxes = Array.from(studentsList.querySelectorAll('.student-checkbox'));
        const selectedIds = new Set(checkboxes.filter(cb => cb.checked).map(cb => cb.value));
        const removedStudents = Object.entries(enrollments)
            .filter(([studentId, enrollment]) => enrollment.activo && !selectedIds.has(studentId));

        if (removedStudents.length) {
            const confirmMsg = `Se quitará${removedStudents.length === 1 ? '' : 'n'} ${removedStudents.length} estudiante${removedStudents.length === 1 ? '' : 's'} del curso. ¿Continuar?`;
            if (!confirm(confirmMsg)) return;
        }

        try {
            for (const checkbox of checkboxes) {
                if (!checkbox.checked) continue;
                const existing = enrollments[checkbox.value];
                if (existing?.activo) continue;

                const url = existing ? `/api/enrollments/${checkbox.value}/${courseId}/` : '/api/enrollments/';
                await apiFetch(url, {
                    method: existing ? 'PATCH' : 'POST',
                    body: JSON.stringify(existing ? { activo: true } : { student_id: checkbox.value, course_id: courseId }),
                });
            }

            for (const [studentId] of removedStudents) {
                await apiFetch(`/api/enrollments/${studentId}/${courseId}/`, { method: 'DELETE' });
            }

            toast.success('Estudiantes actualizados correctamente');
            modalManager.hide('studentsModal');
            coursesTable.load();
        } catch (error) {
            toast.error(error.message);
        }
    });

    // Expose for inline onclick if needed
    window.CoursesModule = {
        load: () => coursesTable?.load(),
        openCourseModal,
        openStudentsModal,
    };
})();