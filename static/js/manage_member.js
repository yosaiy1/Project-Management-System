document.addEventListener('DOMContentLoaded', function() {
    const manageMembersSystem = {
        elements: {
            editRoleModal: document.getElementById('editRoleModal'),
            removeMemberModal: document.getElementById('removeMemberModal'),
            addMemberForm: document.getElementById('addMemberForm'),
            editRoleForm: document.getElementById('editRoleForm'),
            removeMemberForm: document.getElementById('removeMemberForm')
        },

        init() {
            this.bindEvents();
            this.setupTooltips();
        },

        bindEvents() {
            // Edit Role Modal
            this.elements.editRoleModal?.addEventListener('show.bs.modal', (e) => {
                const button = e.relatedTarget;
                const memberId = button.dataset.memberId;
                const memberName = button.dataset.memberName;
                const currentRole = button.dataset.currentRole;
                
                const form = this.elements.editRoleForm;
                const roleSelect = form.querySelector('select[name="role"]');
                const nameSpan = document.getElementById('memberNameRole');
                
                form.querySelector('[name="member_id"]').value = memberId;
                roleSelect.value = currentRole;
                nameSpan.textContent = memberName;
            });

            // Remove Member Modal
            this.elements.removeMemberModal?.addEventListener('show.bs.modal', (e) => {
                const button = e.relatedTarget;
                const memberId = button.dataset.memberId;
                const memberName = button.dataset.memberName;
                
                const form = this.elements.removeMemberForm;
                const nameSpan = document.getElementById('memberName');
                
                form.querySelector('[name="member_id"]').value = memberId;
                nameSpan.textContent = memberName;
            });

            // Form Submissions
            this.setupFormHandler(this.elements.addMemberForm, 'Adding member...');
            this.setupFormHandler(this.elements.editRoleForm, 'Updating role...');
            this.setupFormHandler(this.elements.removeMemberForm, 'Removing member...');
        },

        setupFormHandler(form, loadingText) {
            form?.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                if (!form.checkValidity()) {
                    form.classList.add('was-validated');
                    return;
                }

                const submitButton = form.querySelector('button[type="submit"]');
                const originalText = submitButton.innerHTML;
                
                try {
                    submitButton.disabled = true;
                    submitButton.innerHTML = `
                        <span class="spinner-border spinner-border-sm me-2"></span>
                        ${loadingText}
                    `;

                    const response = await fetch(form.action, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: new FormData(form)
                    });

                    const data = await response.json();

                    if (data.success) {
                        window.projectHub.utils.showNotification(data.message, 'success');
                        
                        // Close modal if exists
                        const modal = form.closest('.modal');
                        if (modal) {
                            const bsModal = bootstrap.Modal.getInstance(modal);
                            bsModal?.hide();
                        }

                        // Reload page after short delay
                        setTimeout(() => window.location.reload(), 500);
                    } else {
                        throw new Error(data.message || 'Operation failed');
                    }
                } catch (error) {
                    console.error('Form submission error:', error);
                    window.projectHub.utils.showNotification(
                        error.message || 'An error occurred',
                        'error'
                    );
                } finally {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalText;
                }
            });
        },

        setupTooltips() {
            const tooltipTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="tooltip"]')
            );
            tooltipTriggerList.forEach(tooltipTriggerEl => {
                new bootstrap.Tooltip(tooltipTriggerEl, {
                    boundary: document.body
                });
            });
        }
    };

    // Initialize the system
    try {
        manageMembersSystem.init();
    } catch (error) {
        console.error('Team member management initialization error:', error);
        window.projectHub?.utils?.showNotification(
            'Failed to initialize team member management',
            'error'
        );
    }
});