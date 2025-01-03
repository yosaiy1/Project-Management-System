const teamManagement = {
    init() {
        this.setupFormHandlers();
        this.setupModalHandlers();
    },

    setupFormHandlers() {
        document.querySelectorAll('form[data-ajax]').forEach(form => {
            form.addEventListener('submit', this.handleFormSubmit.bind(this));
        });
    },

    setupModalHandlers() {
        // Role edit modal handler
        const editRoleModal = document.getElementById('editRoleModal');
        if (editRoleModal) {
            editRoleModal.addEventListener('show.bs.modal', this.handleEditRoleModal);
        }

        // Remove member modal handler
        const removeMemberModal = document.getElementById('removeMemberModal');
        if (removeMemberModal) {
            removeMemberModal.addEventListener('show.bs.modal', this.handleRemoveMemberModal);
        }
    },

    async handleFormSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;

        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Processing...`;

            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': form.querySelector('[name="csrfmiddlewaretoken"]').value
                },
                body: new FormData(form)
            });

            const data = await response.json();

            if (data.success) {
                window.projectHub.utils.showNotification(data.message, 'success');
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    window.location.reload();
                }
            } else {
                throw new Error(data.message || 'Operation failed');
            }
        } catch (error) {
            window.projectHub.utils.showNotification(error.message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }
};

const teamSystem = {
    init() {
        this.setupEventListeners();
        this.setupProgressBars();
    },

    setupEventListeners() {
        // Handle member actions
        document.addEventListener('click', e => {
            const target = e.target.closest('[data-action]');
            if (!target) return;

            const action = target.dataset.action;
            const memberId = target.dataset.memberId;

            switch (action) {
                case 'edit-role':
                    this.handleRoleEdit(memberId);
                    break;
                case 'remove-member':
                    this.handleMemberRemoval(memberId);
                    break;
            }
        });
    },

    setupProgressBars() {
        document.querySelectorAll('.progress-bar').forEach(bar => {
            const value = parseFloat(bar.getAttribute('aria-valuenow'));
            bar.style.width = `${value}%`;
            bar.classList.add(`bg-${this.getProgressColor(value)}`);
        });
    },

    getProgressColor(value) {
        if (value >= 75) return 'success';
        if (value >= 50) return 'info';
        if (value >= 25) return 'warning';
        return 'danger';
    }
};

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    teamSystem.init();
});