/**
 * Academic Core - Shared JavaScript utilities for the academic management system
 * Provides: apiFetch, Toast notifications, Modal management, Table rendering, Pagination, Search/Ordering
 */

(function() {
    'use strict';

    // =============================================================================
    // UTILITIES
    // =============================================================================

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        return parts.length === 2 ? parts.pop().split(';').shift() : '';
    }

    function formatDate(isoString, locale = 'es-CL') {
        if (!isoString) return '-';
        const date = new Date(isoString);
        return date.toLocaleDateString(locale, {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    function formatDateShort(isoString, locale = 'es-CL') {
        if (!isoString) return '-';
        const date = new Date(isoString);
        return date.toLocaleDateString(locale, {
            day: '2-digit', month: '2-digit', year: 'numeric'
        });
    }

    function debounce(fn, delay) {
        let timeoutId;
        return (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // =============================================================================
    // API FETCH WRAPPER
    // =============================================================================

    async function apiFetch(url, options = {}) {
        const csrfToken = getCookie('csrftoken');
        const defaultOptions = {
            credentials: 'same-origin',
            headers: {
                'Accept': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...(options.headers || {}),
            },
        };

        if (mergedOptions.body && !(mergedOptions.body instanceof FormData)) {
            mergedOptions.headers['Content-Type'] = 'application/json';
        }

        try {
            const response = await fetch(url, mergedOptions);

            if (response.status === 401) {
                const loginUrl = '/login/?next=' + encodeURIComponent(window.location.pathname + window.location.search);
                window.location.href = loginUrl;
                return null;
            }

            if (response.status === 403) {
                toast.error('No tienes permisos para realizar esta acción');
                return null;
            }

            const contentType = response.headers.get('content-type');
            const data = contentType?.includes('application/json') ? await response.json() : await response.text();

            if (!response.ok) {
                const errorMsg = data?.detail || data?.non_field_errors?.[0] || data?.message || `Error ${response.status}: ${response.statusText}`;
                throw new Error(errorMsg);
            }

            return data;
        } catch (error) {
            if (error instanceof TypeError && error.message.includes('fetch')) {
                throw new Error('Error de conexión. Verifica tu red.');
            }
            throw error;
        }
    }

    // =============================================================================
    // TOAST NOTIFICATIONS (Bootstrap 5)
    // =============================================================================

    const toastContainer = (() => {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            container.style.zIndex = '1080';
            document.body.appendChild(container);
        }
        return container;
    })();

    const toast = {
        show(message, type = 'info', delay = 5000) {
            const id = 'toast-' + Date.now();
            const icons = {
                success: 'bi-check-circle-fill',
                error: 'bi-exclamation-triangle-fill',
                warning: 'bi-exclamation-triangle-fill',
                info: 'bi-info-circle-fill',
            };
            const bgClasses = {
                success: 'bg-success',
                error: 'bg-danger',
                warning: 'bg-warning text-dark',
                info: 'bg-info',
            };

            const toastEl = document.createElement('div');
            toastEl.id = id;
            toastEl.className = `toast align-items-center ${bgClasses[type] || 'bg-info'} text-white border-0`;
            toastEl.setAttribute('role', 'alert');
            toastEl.setAttribute('aria-live', 'assertive');
            toastEl.setAttribute('aria-atomic', 'true');
            toastEl.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body d-flex align-items-center gap-2">
                        <i class="bi ${icons[type] || icons.info} fs-5"></i>
                        <span>${escapeHtml(message)}</span>
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Cerrar"></button>
                </div>
            `;
            toastContainer.appendChild(toastEl);
            const bsToast = new bootstrap.Toast(toastEl, { delay });
            bsToast.show();
            toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
            return bsToast;
        },
        success(msg, delay) { return this.show(msg, 'success', delay); },
        error(msg, delay) { return this.show(msg, 'error', delay); },
        warning(msg, delay) { return this.show(msg, 'warning', delay); },
        info(msg, delay) { return this.show(msg, 'info', delay); },
    };

    // =============================================================================
    // MODAL MANAGEMENT
    // =============================================================================

    const modalManager = {
        modals: new Map(),

        get(modalId) {
            if (!this.modals.has(modalId)) {
                const el = document.getElementById(modalId);
                if (el) this.modals.set(modalId, new bootstrap.Modal(el));
            }
            return this.modals.get(modalId);
        },

        show(modalId) {
            const modal = this.get(modalId);
            if (modal) modal.show();
            return modal;
        },

        hide(modalId) {
            const modal = this.get(modalId);
            if (modal) modal.hide();
            return modal;
        },

        setLoading(modalId, loading) {
            const modalEl = document.getElementById(modalId);
            if (!modalEl) return;
            const title = modalEl.querySelector('.modal-title');
            const submitBtn = modalEl.querySelector('button[type="submit"]');
            if (loading) {
                modalEl.dataset.loading = 'true';
                if (title && !title.dataset.originalTitle) title.dataset.originalTitle = title.textContent;
                if (title) title.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Cargando...';
                if (submitBtn) submitBtn.disabled = true;
            } else {
                delete modalEl.dataset.loading;
                if (title && title.dataset.originalTitle) title.textContent = title.dataset.originalTitle;
                if (submitBtn) submitBtn.disabled = false;
            }
        },

        resetForm(modalId) {
            const modalEl = document.getElementById(modalId);
            if (!modalEl) return;
            const form = modalEl.querySelector('form');
            if (form) form.reset();
            const hiddenInputs = modalEl.querySelectorAll('input[type="hidden"]');
            hiddenInputs.forEach(input => input.value = '');
        },
    };

    // =============================================================================
    // TABLE RENDERER (Generic)
    // =============================================================================

    class TableRenderer {
        constructor(config) {
            this.config = {
                tableId: config.tableId,
                tbodyId: config.tbodyId,
                loadingId: config.loadingId,
                emptyId: config.emptyId,
                countId: config.countId,
                apiEndpoint: config.apiEndpoint,
                columns: config.columns,
                rowClass: config.rowClass || '',
                actionsColumn: config.actionsColumn || null,
                onRowClick: config.onRowClick || null,
                emptyMessage: config.emptyMessage || 'No hay registros',
                emptyIcon: config.emptyIcon || 'bi-database-x',
            };
            this.data = [];
            this.currentPage = 1;
            this.totalCount = 0;
            this.totalPages = 1;
            this.searchTerm = '';
            this.ordering = '';
            this.filters = {};
        }

        setFilter(key, value) {
            if (value) this.filters[key] = value;
            else delete this.filters[key];
            this.currentPage = 1;
            this.load();
        }

        getLoadingEl() { return document.getElementById(this.config.loadingId); }
        getEmptyEl() { return document.getElementById(this.config.emptyId); }
        getTableEl() { return document.getElementById(this.config.tableId); }
        getTbodyEl() { return document.getElementById(this.config.tbodyId); }
        getCountEl() { return document.getElementById(this.config.countId); }

        setLoading(show) {
            const loading = this.getLoadingEl();
            const table = this.getTableEl();
            const empty = this.getEmptyEl();
            if (loading) loading.classList.toggle('d-none', !show);
            if (table) table.classList.toggle('d-none', show);
            if (empty) empty.classList.add('d-none');
        }

        showEmpty(show) {
            const empty = this.getEmptyEl();
            const table = this.getTableEl();
            if (empty) empty.classList.toggle('d-none', !show);
            if (table) table.classList.toggle('d-none', show);
        }

        updateCount(count) {
            const countEl = this.getCountEl();
            if (countEl) {
                countEl.textContent = `${count} registro${count !== 1 ? 's' : ''}`;
                countEl.className = count > 0 ? 'badge bg-primary' : 'badge bg-secondary';
            }
        }

        buildQueryParams() {
            const params = new URLSearchParams();
            params.set('page', this.currentPage);
            if (this.searchTerm) params.set('search', this.searchTerm);
            if (this.ordering) params.set('ordering', this.ordering);
            Object.entries(this.filters).forEach(([key, val]) => params.set(key, val));
            return params.toString();
        }

        async load() {
            this.setLoading(true);
            try {
                const query = this.buildQueryParams();
                const url = `${this.config.apiEndpoint}?${query}`;
                const response = await apiFetch(url);
                if (!response) return;

                this.data = response.results || response;
                this.totalCount = response.count ?? this.data.length;
                const pageSize = response.results ? (response.results.length || 20) : this.data.length;
                this.totalPages = Math.ceil(this.totalCount / pageSize) || 1;

                this.render();
                this.updateCount(this.totalCount);
                this.renderPagination();
            } catch (error) {
                this.renderError(error.message);
                this.updateCount(0);
            } finally {
                this.setLoading(false);
            }
        }

        render() {
            const tbody = this.getTbodyEl();
            if (!tbody) return;

            tbody.innerHTML = '';

            if (!this.data.length) {
                this.showEmpty(true);
                return;
            }

            this.showEmpty(false);
            const isSuperuser = document.body.dataset.isSuperuser === 'true';
            this.data.forEach(item => {
                const tr = document.createElement('tr');
                if (this.config.rowClass) tr.className = this.config.rowClass;
                if (item.id) tr.dataset.id = item.id;

                let rowHtml = '';
                this.config.columns.forEach(col => {
                    const value = this.getNestedValue(item, col.key);
                    let formatted = col.format ? col.format(value, item) : escapeHtml(value ?? '');
                    rowHtml += `<td${col.class ? ` class="${col.class}"` : ''}>${formatted}</td>`;
                });

                if (this.config.actionsColumn && isSuperuser) {
                    rowHtml += this.config.actionsColumn(item);
                }

                tr.innerHTML = rowHtml;
                tbody.appendChild(tr);
            });

            this.bindRowActions();
        }

        getNestedValue(obj, path) {
            return path.split('.').reduce((o, k) => (o || {})[k], obj);
        }

        renderError(message) {
            const tbody = this.getTbodyEl();
            const colCount = this.config.columns.length + (this.config.actionsColumn ? 1 : 0);
            tbody.innerHTML = `
                <tr>
                    <td colspan="${colCount}" class="text-center text-danger py-4">
                        <i class="bi bi-exclamation-triangle me-2"></i> ${escapeHtml(message)}
                    </td>
                </tr>
            `;
        }

        bindRowActions() {
            const tbody = this.getTbodyEl();
            if (!tbody) return;

            if (this.config.onRowClick) {
                tbody.querySelectorAll('tr[data-id]').forEach(tr => {
                    tr.style.cursor = 'pointer';
                    tr.addEventListener('click', (e) => {
                        if (!e.target.closest('button, a, input, select')) {
                            this.config.onRowClick(tr.dataset.id, this.data.find(d => String(d.id) === tr.dataset.id));
                        }
                    });
                });
            }
        }

        // Pagination
        renderPagination() {
            const containerId = this.config.paginationId || `${this.config.tableId}-pagination`;
            let container = document.getElementById(containerId);
            if (!container) {
                container = document.createElement('nav');
                container.id = containerId;
                container.className = 'mt-3';
                container.setAttribute('aria-label', 'Paginación');
                const table = this.getTableEl();
                if (table && table.parentNode) {
                    table.parentNode.insertBefore(container, table.nextSibling);
                }
            }

            if (this.totalPages <= 1) {
                container.innerHTML = '';
                return;
            }

            let html = '<ul class="pagination pagination-sm justify-content-center">';
            html += `<li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">`;
            html += `<button class="page-link" data-page="${this.currentPage - 1}" aria-label="Anterior"><i class="bi bi-chevron-left"></i></button></li>`;

            const start = Math.max(1, this.currentPage - 2);
            const end = Math.min(this.totalPages, this.currentPage + 2);

            for (let i = start; i <= end; i++) {
                html += `<li class="page-item ${i === this.currentPage ? 'active' : ''}">`;
                html += `<button class="page-link" data-page="${i}" ${i === this.currentPage ? 'aria-current="page"' : ''}>${i}</button></li>`;
            }

            html += `<li class="page-item ${this.currentPage === this.totalPages ? 'disabled' : ''}">`;
            html += `<button class="page-link" data-page="${this.currentPage + 1}" aria-label="Siguiente"><i class="bi bi-chevron-right"></i></button></li>`;
            html += '</ul>';

            container.innerHTML = html;

            container.querySelectorAll('.page-link[data-page]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const page = parseInt(btn.dataset.page, 10);
                    if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
                        this.goToPage(page);
                    }
                });
            });
        }

        goToPage(page) {
            this.currentPage = page;
            this.load();
        }

        setSearch(term) {
            this.searchTerm = term;
            this.currentPage = 1;
            this.load();
        }

        setOrdering(field) {
            if (this.ordering === field) {
                this.ordering = field.startsWith('-') ? field.slice(1) : '-' + field;
            } else {
                this.ordering = field;
            }
            this.currentPage = 1;
            this.load();
        }

        getOrderingIcon(field) {
            if (!this.ordering) return 'bi-arrow-down-up';
            const currentField = this.ordering.replace('-', '');
            if (currentField !== field) return 'bi-arrow-down-up';
            return this.ordering.startsWith('-') ? 'bi-arrow-down' : 'bi-arrow-up';
        }
    }

    // =============================================================================
    // FORM HANDLER (Generic)
    // =============================================================================

    class FormHandler {
        constructor(config) {
            this.config = {
                formId: config.formId,
                modalId: config.modalId,
                apiEndpoint: config.apiEndpoint,
                fields: config.fields,
                onSuccess: config.onSuccess || (() => {}),
                onError: config.onError || ((msg) => toast.error(msg)),
                validate: config.validate || (() => true),
                transformData: config.transformData || (data => data),
            };
            this.editingId = null;
        }

        getForm() { return document.getElementById(this.config.formId); }
        getModal() { return modalManager.get(this.config.modalId); }

        setEditing(id, data) {
            this.editingId = id;
            const form = this.getForm();
            if (!form) return;

            this.config.fields.forEach(field => {
                const input = form.querySelector(`[name="${field.name}"], #${field.id}`);
                if (input) {
                    const value = data[field.name] ?? data[field.id] ?? '';
                    if (input.type === 'checkbox') {
                        input.checked = Boolean(value);
                    } else if (input.type === 'select-one') {
                        input.value = value;
                    } else {
                        input.value = value ?? '';
                    }
                }
            });
        }

        clear() {
            this.editingId = null;
            const form = this.getForm();
            if (form) form.reset();
            const hiddenInputs = form?.querySelectorAll('input[type="hidden"]');
            hiddenInputs?.forEach(input => input.value = '');
        }

        getData() {
            const form = this.getForm();
            if (!form) return {};
            const formData = new FormData(form);
            const data = {};
            formData.forEach((value, key) => {
                const field = this.config.fields.find(f => f.name === key);
                if (field?.type === 'number') data[key] = Number(value);
                else if (field?.type === 'boolean') data[key] = value === 'on';
                else data[key] = value;
            });
            return this.config.transformData(data);
        }

        setErrors(errors) {
            const form = this.getForm();
            if (!form) return;

            form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());

            Object.entries(errors).forEach(([field, messages]) => {
                const input = form.querySelector(`[name="${field}"], #${field}`);
                if (input) {
                    input.classList.add('is-invalid');
                    const feedback = document.createElement('div');
                    feedback.className = 'invalid-feedback';
                    feedback.textContent = Array.isArray(messages) ? messages[0] : messages;
                    input.parentNode.appendChild(feedback);
                }
            });
        }

        clearErrors() {
            const form = this.getForm();
            if (!form) return;
            form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
        }

        async submit() {
            this.clearErrors();

            if (!this.config.validate(this.getData())) {
                return false;
            }

            const submitBtn = this.getForm()?.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;

            try {
                const data = this.getData();
                const url = this.editingId ? `${this.config.apiEndpoint}${this.editingId}/` : this.config.apiEndpoint;
                const method = this.editingId ? 'PATCH' : 'POST';

                const response = await apiFetch(url, { method, body: JSON.stringify(data) });
                if (!response) return false;

                toast.success(this.editingId ? 'Actualizado correctamente' : 'Creado correctamente');
                this.config.onSuccess(response);
                this.hide();
                return true;
            } catch (error) {
                if (error.errors) {
                    this.setErrors(error.errors);
                }
                this.config.onError(error.message);
                return false;
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        }

        show(title) {
            const modalEl = document.getElementById(this.config.modalId);
            if (modalEl) {
                const titleEl = modalEl.querySelector('.modal-title');
                if (titleEl && title) titleEl.textContent = title;
            }
            this.getModal()?.show();
        }

        hide() {
            this.getModal()?.hide();
            this.clear();
        }

        bind() {
            const form = this.getForm();
            if (!form) return;

            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.submit();
            });

            const modalEl = document.getElementById(this.config.modalId);
            if (modalEl) {
                modalEl.addEventListener('hidden.bs.modal', () => this.clear());
            }
        }
    }

    // =============================================================================
    // SEARCH & ORDERING UI
    // =============================================================================

    function initSearchAndOrdering(tableRenderer, config) {
        const searchInput = document.getElementById(config.searchInputId);
        const searchBtn = document.getElementById(config.searchBtnId);
        const orderingSelect = document.getElementById(config.orderingSelectId);

        if (searchInput) {
            const debouncedSearch = debounce((term) => tableRenderer.setSearch(term), 300);
            searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value.trim()));
            searchInput.addEventListener('search', (e) => debouncedSearch(e.target.value.trim()));
        }

        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                if (searchInput) tableRenderer.setSearch(searchInput.value.trim());
            });
        }

        if (orderingSelect) {
            orderingSelect.addEventListener('change', (e) => {
                if (e.target.value) tableRenderer.setOrdering(e.target.value);
            });
        }

        // Update ordering icons in table headers
        document.querySelectorAll('th[data-order]').forEach(th => {
            const field = th.dataset.order;
            const icon = th.querySelector('.order-icon');
            if (icon) {
                const updateIcon = () => {
                    icon.className = `bi ${tableRenderer.getOrderingIcon(field)} order-icon ms-1`;
                };
                updateIcon();
                const originalLoad = tableRenderer.load.bind(tableRenderer);
                tableRenderer.load = async function() {
                    await originalLoad();
                    updateIcon();
                };
            }
        });
    }

    // =============================================================================
    // CONFIRMATION DIALOG
    // =============================================================================

    function confirmAction(message, callback) {
        if (confirm(message)) callback();
    }

    async function confirmDelete(itemName, deleteFn) {
        if (!confirm(`¿Seguro que quieres eliminar ${itemName} con borrado lógico?`)) return;
        try {
            await deleteFn();
            toast.success('Eliminado correctamente');
        } catch (error) {
            toast.error(error.message);
        }
    }

    async function confirmToggle(itemName, isActive, toggleFn) {
        const action = isActive ? 'desactivar' : 'activar';
        if (!confirm(`¿Seguro que quieres ${action} ${itemName}?`)) return;
        try {
            await toggleFn();
            toast.success(`${action.charAt(0).toUpperCase() + action.slice(1)} correctamente`);
        } catch (error) {
            toast.error(error.message);
        }
    }

    // =============================================================================
    // EXPORTS
    // =============================================================================

    window.AcademicCore = {
        getCookie,
        formatDate,
        formatDateShort,
        debounce,
        escapeHtml,
        apiFetch,
        toast,
        modalManager,
        TableRenderer,
        FormHandler,
        initSearchAndOrdering,
        confirmAction,
        confirmDelete,
        confirmToggle,
    };
})();