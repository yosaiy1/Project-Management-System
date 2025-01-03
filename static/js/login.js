document.addEventListener('DOMContentLoaded', function() {
    const loginSystem = {
        elements: {
            form: document.getElementById('loginForm'),
            username: document.getElementById('id_username'),
            password: document.getElementById('id_password'),
            togglePassword: document.getElementById('togglePassword'),
            loginButton: document.getElementById('loginButton'),
            rememberMe: document.getElementById('remember')
        },

        init() {
            this.bindEvents();
            this.loadSavedUsername();
        },

        bindEvents() {
            // Password visibility toggle
            this.elements.togglePassword?.addEventListener('click', () => {
                this.togglePasswordVisibility();
            });

            // Form submission
            this.elements.form?.addEventListener('submit', (e) => {
                this.handleSubmit(e);
            });
        },

        togglePasswordVisibility() {
            const type = this.elements.password.getAttribute('type') === 'password' ? 'text' : 'password';
            this.elements.password.setAttribute('type', type);
            this.elements.togglePassword.querySelector('i').classList.toggle('bi-eye');
            this.elements.togglePassword.querySelector('i').classList.toggle('bi-eye-slash');
        },

        handleSubmit(e) {
            e.preventDefault();

            if (!this.elements.form.checkValidity()) {
                this.elements.form.classList.add('was-validated');
                return;
            }

            // Show loading state
            this.elements.loginButton.disabled = true;
            const originalText = this.elements.loginButton.innerHTML;
            this.elements.loginButton.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2"></span>
                Signing in...
            `;

            // Save username if remember me is checked
            if (this.elements.rememberMe.checked) {
                localStorage.setItem('remembered_username', this.elements.username.value);
            } else {
                localStorage.removeItem('remembered_username');
            }

            // Submit the form
            this.elements.form.submit();
        },

        loadSavedUsername() {
            const savedUsername = localStorage.getItem('remembered_username');
            if (savedUsername) {
                this.elements.username.value = savedUsername;
                this.elements.rememberMe.checked = true;
            }
        }
    };

    // Initialize login system
    try {
        loginSystem.init();
    } catch (error) {
        console.error('Login initialization error:', error);
    }
});