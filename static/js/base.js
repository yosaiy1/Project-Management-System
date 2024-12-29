document.addEventListener('DOMContentLoaded', function() {
    // Utility Functions
    const utils = {
        getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        },

        debounce(func, wait) {
            let timeout;
            return function(...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        },

        showNotification(message, type = 'info', duration = 3000) {
            const toast = document.createElement('div');
            toast.className = `toast align-items-center text-white bg-${type} border-0`;
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');

            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi bi-${this.getNotificationIcon(type)} me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            `;

            const container = document.querySelector('.toast-container') || this.createToastContainer();
            container.appendChild(toast);

            const bsToast = new bootstrap.Toast(toast, { delay: duration });
            bsToast.show();

            toast.addEventListener('hidden.bs.toast', () => toast.remove());
        },

        getNotificationIcon(type) {
            return {
                'success': 'check-circle',
                'error': 'x-circle',
                'warning': 'exclamation-triangle',
                'info': 'info-circle'
            }[type] || 'bell';
        },

        createToastContainer() {
            const container = document.createElement('div');
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1080';
            document.body.appendChild(container);
            return container;
        },

        animateValue(obj, start, end, duration) {
            if (!obj) return;

            const stepMs = 16;
            const steps = Math.floor(duration / stepMs);
            const increment = (end - start) / steps;
            
            let current = start;
            const timer = setInterval(() => {
                current += increment;
                
                if ((increment >= 0 && current >= end) || (increment < 0 && current <= end)) {
                    clearInterval(timer);
                    obj.textContent = end.toLocaleString();
                } else {
                    obj.textContent = Math.round(current).toLocaleString();
                }
            }, stepMs);
        }
    };

    // Theme System
    const themeSystem = {
        init() {
            this.themeToggle = document.getElementById('themeToggle');
            this.prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
            this.currentTheme = localStorage.getItem('theme') || 
                              (this.prefersDark.matches ? 'dark' : 'light');
            this.applyTheme(this.currentTheme);
            this.bindEvents();
        },

        applyTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            document.body.setAttribute('data-bs-theme', theme);
            localStorage.setItem('theme', theme);
            
            if (this.themeToggle) {
                const icon = this.themeToggle.querySelector('i');
                if (icon) {
                    icon.className = `bi bi-${theme === 'dark' ? 'moon-stars' : 'sun'} fs-5`;
                }
            }
        },

        bindEvents() {
            this.themeToggle?.addEventListener('click', () => {
                const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
                this.currentTheme = newTheme;
                this.applyTheme(newTheme);
            });

            this.prefersDark.addEventListener('change', (e) => {
                if (!localStorage.getItem('theme')) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    };

    // Sidebar System
    const sidebarSystem = {
        init() {
            this.sidebar = document.getElementById('sidebar');
            this.sidebarToggle = document.getElementById('sidebarToggle');
            this.sidebarOverlay = document.querySelector('.sidebar-overlay');
            this.bindEvents();
            this.handleResize();
        },

        bindEvents() {
            this.sidebarToggle?.addEventListener('click', () => this.toggleSidebar());
            this.sidebarOverlay?.addEventListener('click', () => this.closeSidebar());
        },

        handleResize() {
            window.addEventListener('resize', utils.debounce(() => {
                if (window.innerWidth > 768) {
                    document.body.classList.remove('sidebar-expanded');
                }
            }, 250));
        },

        toggleSidebar() {
            document.body.classList.toggle('sidebar-expanded');
        },

        closeSidebar() {
            document.body.classList.remove('sidebar-expanded');
        }
    };

    const searchSystem = {
        init() {
            this.searchInput = document.querySelector('.search-input');
            this.searchResults = document.querySelector('.search-results');
            this.searchSpinner = document.querySelector('.search-spinner');
            this.currentIndex = -1;
            this.results = [];
            if (this.searchInput && this.searchResults) {
                this.bindEvents();
            }
        },
    
        bindEvents() {
            // Debounced search handler
            const searchHandler = utils.debounce((e) => {
                const query = e.target.value.trim();
                if (query.length >= 2) {
                    this.performSearch(query);
                } else {
                    this.hideResults();
                }
            }, 300);
    
            // Click outside handler
            const clickOutsideHandler = (e) => {
                if (!this.searchResults.contains(e.target) && !this.searchInput.contains(e.target)) {
                    this.hideResults();
                }
            };
    
            // Keyboard navigation
            const keyHandler = (e) => {
                switch(e.key) {
                    case 'ArrowDown':
                        e.preventDefault();
                        this.navigateResults(1);
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        this.navigateResults(-1);
                        break;
                    case 'Enter':
                        if (this.currentIndex >= 0) {
                            e.preventDefault();
                            const selectedLink = this.searchResults.querySelector(`a:nth-child(${this.currentIndex + 1})`);
                            if (selectedLink) selectedLink.click();
                        }
                        break;
                    case 'Escape':
                        this.hideResults();
                        this.searchInput.blur();
                        break;
                }
            };
    
            // Bind events
            this.searchInput.addEventListener('input', searchHandler);
            this.searchInput.addEventListener('keydown', keyHandler);
            document.addEventListener('click', clickOutsideHandler);
            
            // Store cleanup function
            this.cleanup = () => {
                this.searchInput.removeEventListener('input', searchHandler);
                this.searchInput.removeEventListener('keydown', keyHandler);
                document.removeEventListener('click', clickOutsideHandler);
            };
        },
    
        navigateResults(direction) {
            const items = this.searchResults.querySelectorAll('a');
            if (!items.length) return;
    
            items[this.currentIndex]?.classList.remove('active');
            this.currentIndex = (this.currentIndex + direction + items.length) % items.length;
            items[this.currentIndex]?.classList.add('active');
            items[this.currentIndex]?.scrollIntoView({ block: 'nearest' });
        },
    
        hideResults() {
            this.searchResults.classList.add('d-none');
            this.currentIndex = -1;
            this.results = [];
        },
    
        async performSearch(query) {
            try {
                this.searchSpinner?.classList.remove('d-none');
                const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`, {
                    headers: {
                        'X-CSRFToken': utils.getCookie('csrftoken')
                    }
                });
                
                if (!response.ok) throw new Error('Search request failed');
                
                const data = await response.json();
                if (data.status === 'success') {
                    this.results = data.results;
                    this.displayResults(data.results);
                } else {
                    throw new Error(data.message || 'Search failed');
                }
            } catch (error) {
                console.error('Search error:', error);
                utils.showNotification(error.message, 'error');
                this.displayError();
            } finally {
                this.searchSpinner?.classList.add('d-none');
            }
        },
    
        displayResults(results) {
            if (!this.searchResults) return;
    
            try {
                if (!Array.isArray(results)) throw new Error('Invalid results format');
    
                this.searchResults.innerHTML = results.length ? 
                    results.map((result, index) => `
                        <a href="${result.url}" 
                           class="d-block p-2 text-decoration-none rounded hover-bg-light"
                           role="option"
                           aria-selected="${index === this.currentIndex}">
                            <i class="bi bi-${result.type === 'project' ? 'folder' : 'check-square'} me-2"></i>
                            <span>${result.title}</span>
                        </a>
                    `).join('') :
                    `<div class="p-3 text-center text-muted" role="status">
                        <i class="bi bi-search me-2"></i>
                        <span>No results found</span>
                    </div>`;
    
                this.searchResults.classList.remove('d-none');
                this.searchResults.setAttribute('role', 'listbox');
            } catch (error) {
                console.error('Display error:', error);
                this.displayError();
            }
        },
    
        displayError() {
            if (!this.searchResults) return;
            
            this.searchResults.innerHTML = `
                <div class="p-3 text-center text-danger" role="alert">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <span>Error displaying results</span>
                </div>
            `;
            this.searchResults.classList.remove('d-none');
        }
    };

    // Notification System
    const notificationSystem = {
        init() {
            this.setupNotificationListeners();
            this.autoHideNotifications();
        },

        setupNotificationListeners() {
            const notifications = document.querySelectorAll('.notification-item');
            if (!notifications.length) return;
        
            notifications.forEach(item => {
                if (!item.dataset.read) {
                    item.addEventListener('click', () => this.markAsRead(item));
                }
            });
        },

        autoHideNotifications() {
            document.querySelectorAll('.notification-toast').forEach(notification => {
                setTimeout(() => {
                    notification.classList.add('fade-out');
                    setTimeout(() => notification.remove(), 300);
                }, 5000);
            });
        },

        async markAsRead(notificationElement) {
            try {
                const id = notificationElement.dataset.id;
                const response = await fetch(`/notifications/mark-read/${id}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': utils.getCookie('csrftoken')
                    }
                });
                
                if (response.ok) {
                    notificationElement.classList.remove('unread');
                    this.updateUnreadCount();
                }
            } catch (error) {
                console.error('Error marking notification as read:', error);
                utils.showNotification('Failed to mark notification as read', 'error');
            }
        },

        updateUnreadCount() {
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                const currentCount = parseInt(badge.textContent) - 1;
                if (currentCount <= 0) {
                    badge.remove();
                } else {
                    badge.textContent = currentCount;
                }
            }
        }
    };

    // Progress System
    const progressSystem = {
        init() {
            this.progressBars = document.querySelectorAll('.progress-bar[data-value]');
            this.animateProgressBars();
        },

        animateProgressBars() {
            this.progressBars.forEach(bar => {
                const value = parseFloat(bar.dataset.value) || 0;
                bar.style.width = '0%';
                setTimeout(() => {
                    bar.style.transition = 'width 1s ease-in-out';
                    bar.style.width = `${value}%`;
                }, 100);
            });
        }
    };

    // Stats Animation System
    const statsSystem = {
        init() {
            this.stats = document.querySelectorAll('[data-stat-value]');
            this.animateStats();
        },

        animateStats() {
            this.stats.forEach(stat => {
                const endValue = parseInt(stat.dataset.statValue) || 0;
                utils.animateValue(stat, 0, endValue, 1000);
            });
        }
    };

    // Keyboard Shortcuts
    const keyboardShortcuts = {
        init() {
            document.addEventListener('keydown', (e) => {
                // Toggle sidebar with Ctrl + B
                if (e.ctrlKey && e.key === 'b') {
                    e.preventDefault();
                    sidebarSystem.toggleSidebar();
                }
                
                // Focus search with Ctrl + K
                if (e.ctrlKey && e.key === 'k') {
                    e.preventDefault();
                    searchSystem.searchInput?.focus();
                }
            });
        }
    };

    // Page Visibility Handler
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            progressSystem.animateProgressBars();
            statsSystem.animateStats();
        }
    });

    // Task Management System
const taskSystem = {
    init() {
        this.bindTaskEvents();
        this.setupTaskSorting();
    },

    bindTaskEvents() {
        document.addEventListener('click', e => {
            const taskStatusBtn = e.target.closest('[data-task-status]');
            if (taskStatusBtn) {
                const taskId = taskStatusBtn.dataset.taskId;
                const newStatus = taskStatusBtn.dataset.taskStatus;
                this.updateTaskStatus(taskId, newStatus);
            }
        });
    },

    async updateTaskStatus(taskId, status) {
        try {
            const response = await fetch(`/update_task_status/${taskId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': utils.getCookie('csrftoken')
                },
                body: JSON.stringify({ status })
            });
            if (response.ok) {
                utils.showNotification('Task updated successfully', 'success');
                // Refresh task lists if needed
                if (window.location.pathname.includes('/tasks/')) {
                    window.location.reload();
                }
            }
        } catch (error) {
            console.error('Task update error:', error);
            utils.showNotification('Failed to update task', 'error');
        }
    },

    setupTaskSorting() {
        const taskLists = document.querySelectorAll('.task-list');
        if (!taskLists.length) return;
    
        try {
            taskLists.forEach(list => {
                new Sortable(list, {
                    animation: 150,
                    ghostClass: 'task-ghost',
                    onEnd: this.handleTaskReorder.bind(this)
                });
            });
        } catch (error) {
            console.error('Task sorting setup error:', error);
            utils.showNotification('Failed to setup task sorting', 'error');
        }
    }
};

// Modal System
const modalSystem = {
    init() {
        this.setupDynamicModals();
    },

    setupDynamicModals() {
        document.addEventListener('click', e => {
            const modalTrigger = e.target.closest('[data-modal]');
            if (modalTrigger) {
                const modalId = modalTrigger.dataset.modal;
                const modal = document.getElementById(modalId);
                if (modal) {
                    new bootstrap.Modal(modal).show();
                }
            }
        });
    }
};

// Analytics System
const analyticsSystem = {
    init() {
        this.setupCharts();
    },

    setupCharts() {
        const charts = document.querySelectorAll('[data-chart]');
        charts.forEach(chart => {
            const type = chart.dataset.chart;
            const data = JSON.parse(chart.dataset.chartData || '{}');
            this.createChart(chart, type, data);
        });
    },

    createChart(element, type, data) {
        if (!element || !type || !data) return;
        
        try {
            return new Chart(element, {
                type,
                data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        } catch (error) {
            console.error('Chart creation error:', error);
            utils.showNotification('Failed to create chart', 'error');
        }
    }
};

// Form System
const formSystem = {
    init() {
        this.setupFormValidation();
        this.setupFileUploads();
        this.setupFormSubmission();
    },

    setupFormValidation() {
        const forms = document.querySelectorAll('form[data-validate]');
        forms.forEach(form => {
            form.addEventListener('submit', this.validateForm.bind(this));
        });
    },

    setupFileUploads() {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.addEventListener('change', this.handleFileSelect.bind(this));
        });
    },

    setupFormSubmission() {
        const ajaxForms = document.querySelectorAll('form[data-ajax]');
        ajaxForms.forEach(form => {
            form.addEventListener('submit', this.handleAjaxSubmit.bind(this));
        });
    },

    validateForm(e) {
        const form = e.target;
        const isValid = form.checkValidity();
        
        if (!isValid) {
            e.preventDefault();
            e.stopPropagation();
            
            const invalidInputs = form.querySelectorAll(':invalid');
            invalidInputs.forEach(input => {
                utils.showNotification(input.validationMessage, 'error');
            });
        }
        
        form.classList.add('was-validated');
    },

    handleFileSelect(e) {
        const input = e.target;
        const files = Array.from(input.files);
        const maxSize = (input.dataset.maxSize || 5) * 1024 * 1024; // Default 5MB
        
        files.forEach(file => {
            if (file.size > maxSize) {
                utils.showNotification(`File ${file.name} is too large`, 'error');
                input.value = '';
            }
        });

        // Update file preview if exists
        const previewEl = document.querySelector(`[data-preview-for="${input.id}"]`);
        if (previewEl && files[0]) {
            const reader = new FileReader();
            reader.onload = e => previewEl.src = e.target.result;
            reader.readAsDataURL(files[0]);
        }
    },

    async handleAjaxSubmit(e) {
        e.preventDefault();
        const form = e.target;
        
        try {
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: form.method,
                headers: {
                    'X-CSRFToken': utils.getCookie('csrftoken')
                },
                body: formData
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                utils.showNotification(data.message || 'Success', 'success');
                if (data.redirect) window.location.href = data.redirect;
            } else {
                throw new Error(data.message || 'Submission failed');
            }
        } catch (error) {
            console.error('Form submission error:', error);
            utils.showNotification(error.message, 'error');
        }
    }
};

taskSystem.handleTaskReorder = async function(evt) {
    if (!evt?.item?.dataset?.taskId || evt.newIndex === undefined) {
        console.error('Invalid task reorder event:', evt);
        return;
    }

    try {
        const taskId = evt.item.dataset.taskId;
        const newIndex = evt.newIndex;
        const listId = evt.to.dataset.listId;

        const response = await fetch(`/tasks/${taskId}/reorder/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': utils.getCookie('csrftoken')
            },
            body: JSON.stringify({ 
                position: newIndex,
                list_id: listId
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Reorder failed');
        }

        utils.showNotification('Task reordered successfully', 'success');
        
        // Update task positions if needed
        if (data.positions) {
            this.updateTaskPositions(data.positions);
        }

    } catch (error) {
        console.error('Task reorder error:', error);
        utils.showNotification(error.message || 'Failed to reorder task', 'error');
        
        // Revert the change in UI
        evt.item.parentNode.insertBefore(evt.item, evt.oldIndex < evt.newIndex 
            ? evt.item.parentNode.children[evt.oldIndex]
            : evt.item.parentNode.children[evt.oldIndex + 1]
        );
    }
};

  // Update initialization
try {
    themeSystem.init();
    progressSystem.init();
    statsSystem.init();
    sidebarSystem.init();
    searchSystem.init();
    notificationSystem.init();
    keyboardShortcuts.init();
    taskSystem.init();
    modalSystem.init();
    analyticsSystem.init();
    formSystem.init();
} catch (error) {
    console.error('Initialization error:', error);
    utils.showNotification('Failed to initialize application', 'error');
}

// Update exports
window.projectHub = {
    utils,
    themeSystem,
    progressSystem,
    statsSystem,
    sidebarSystem,
    searchSystem,
    notificationSystem,
    keyboardShortcuts,
    taskSystem,
    modalSystem,
    analyticsSystem,
    formSystem
    }
});