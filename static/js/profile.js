document.addEventListener('DOMContentLoaded', function() {
    const profileSystem = {
        init() {
            this.avatarWrapper = document.getElementById('avatarWrapper');
            this.uploadBtn = document.getElementById('uploadAvatarBtn');
            this.avatarModal = document.getElementById('uploadAvatarModal');
            this.avatarForm = document.getElementById('avatarForm');
            this.avatarInput = document.getElementById('avatarInput');
            this.avatarPreview = document.getElementById('avatarPreview');
            this.previewArea = document.querySelector('.preview-area');

            this.bindEvents();
        },

        bindEvents() {
            // Upload button click
            this.uploadBtn?.addEventListener('click', () => {
                const modal = new bootstrap.Modal(this.avatarModal);
                modal.show();
            });

            // File input change
            this.avatarInput?.addEventListener('change', (e) => {
                this.handleFilePreview(e);
            });

            // Form submission
            this.avatarForm?.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleAvatarUpload();
            });
        },

        handleFilePreview(e) {
            const file = e.target.files[0];
            if (!file) return;

            // Validate file type and size
            if (!file.type.startsWith('image/')) {
                window.projectHub.utils.showNotification('Please select an image file', 'error');
                this.avatarInput.value = '';
                return;
            }

            if (file.size > 5 * 1024 * 1024) { // 5MB limit
                window.projectHub.utils.showNotification('Image size should be less than 5MB', 'error');
                this.avatarInput.value = '';
                return;
            }

            // Show preview
            const reader = new FileReader();
            reader.onload = (e) => {
                this.avatarPreview.src = e.target.result;
                this.previewArea.classList.remove('d-none');
            };
            reader.readAsDataURL(file);
        },

        async handleAvatarUpload() {
            try {
                const formData = new FormData(this.avatarForm);
                
                const response = await fetch('/profile/update-avatar/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': window.projectHub.utils.getCookie('csrftoken')
                    },
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    // Update avatar in UI
                    const avatarImg = this.avatarWrapper.querySelector('img');
                    if (avatarImg) {
                        avatarImg.src = data.avatar_url;
                    } else {
                        // Replace placeholder with new image
                        this.avatarWrapper.innerHTML = `
                            <img src="${data.avatar_url}" alt="Profile" class="profile-avatar">
                        `;
                    }

                    // Close modal
                    bootstrap.Modal.getInstance(this.avatarModal).hide();
                    
                    // Show success message
                    window.projectHub.utils.showNotification('Profile picture updated successfully', 'success');
                } else {
                    throw new Error(data.message || 'Upload failed');
                }
            } catch (error) {
                console.error('Avatar upload error:', error);
                window.projectHub.utils.showNotification(
                    error.message || 'Failed to update profile picture', 
                    'error'
                );
            }
        },

        // Stats animation
        animateStats() {
            const stats = document.querySelectorAll('.stat-value');
            stats.forEach(stat => {
                const value = parseInt(stat.dataset.value) || 0;
                window.projectHub.utils.animateValue(stat, 0, value, 1000);
            });
        }
    };

    // Initialize profile system
    try {
        profileSystem.init();
        profileSystem.animateStats();
    } catch (error) {
        console.error('Profile initialization error:', error);
        window.projectHub.utils.showNotification('Failed to initialize profile', 'error');
    }
});