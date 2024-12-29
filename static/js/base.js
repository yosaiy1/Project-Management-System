    // Utility Functions
    const utils = {
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
    
        showNotification(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `toast align-items-center text-white bg-${type} border-0`;
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                            data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            
            let container = document.querySelector('.toast-container');
            if (!container) {
                container = document.createElement('div');
                container.className = 'toast-container position-fixed top-0 end-0 p-3';
                document.body.appendChild(container);
            }
            
            container.appendChild(toast);
            const bsToast = new bootstrap.Toast(toast, {
                delay: 3000,
                animation: true
            });
            bsToast.show();
        },

        getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        }
    };

    // Theme System
    const themeSystem = {
        init() {
            // Initialize properties
            this.themeToggle = document.getElementById('themeToggle');
            this.prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
            this.currentTheme = localStorage.getItem('theme') || 'system';
            
            // Initial setup
            this.applyTheme(this.getEffectiveTheme());
            this.updateToggleButton();
            this.bindEvents();
        },
    
        getEffectiveTheme() {
            if (this.currentTheme === 'system') {
                return this.prefersDark.matches ? 'dark' : 'light';
            }
            return this.currentTheme;
        },
    
        applyTheme(theme) {
            // Remove existing theme classes
            document.body.classList.remove('theme-light', 'theme-dark');
            
            // Add new theme class
            document.body.classList.add(`theme-${theme}`);
            
            // Update data attributes
            document.documentElement.setAttribute('data-theme', theme);
            document.body.setAttribute('data-bs-theme', theme);
        },
    
        updateToggleButton() {
            if (!this.themeToggle) return;
    
            const theme = this.getEffectiveTheme();
            const icon = this.themeToggle.querySelector('i');
            
            if (icon) {
                icon.className = `bi bi-${theme === 'dark' ? 'moon-stars' : 'sun'} fs-5`;
            }
    
            this.themeToggle.setAttribute('title', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
            this.themeToggle.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
        },
    
        bindEvents() {
            // Theme toggle button click
            this.themeToggle?.addEventListener('click', () => {
                const newTheme = this.getEffectiveTheme() === 'light' ? 'dark' : 'light';
                this.currentTheme = newTheme;
                localStorage.setItem('theme', newTheme);
                this.applyTheme(newTheme);
                this.updateToggleButton();
                utils.showNotification(`Switched to ${newTheme} mode`, 'info');
            });
    
            // System preference change
            this.prefersDark.addEventListener('change', (e) => {
                if (this.currentTheme === 'system') {
                    const newTheme = e.matches ? 'dark' : 'light';
                    this.applyTheme(newTheme);
                    this.updateToggleButton();
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

// Search System
const searchSystem = {
    init() {
        this.searchInput = document.querySelector('.search-input');
        this.searchResults = document.querySelector('.search-results');
        this.searchSpinner = document.querySelector('.search-spinner');
        this.currentIndex = -1;
        
        if (this.searchInput && this.searchResults) {
            this.bindEvents();
            this.setupKeyboardShortcuts();
        }
    },

    bindEvents() {
        // Debounced search handler
        const searchHandler = utils.debounce(async (e) => {
            const query = e.target.value.trim();
            if (query.length >= 2) {
                await this.performSearch(query);
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
                    const activeItem = this.searchResults.querySelector('.active');
                    if (activeItem) {
                        e.preventDefault();
                        activeItem.click();
                    }
                    break;
                case 'Escape':
                    this.hideResults();
                    this.searchInput.blur();
                    break;
            }
        };

        this.searchInput.addEventListener('input', searchHandler);
        this.searchInput.addEventListener('keydown', keyHandler);
        document.addEventListener('click', clickOutsideHandler);
    },

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.searchInput.focus();
            }
        });
    },

    async performSearch(query) {
        try {
            this.searchSpinner?.classList.remove('d-none');
            this.searchResults.classList.add('d-none');

            const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'X-CSRFToken': utils.getCookie('csrftoken')
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `Search failed: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                this.displayResults(data.results);
            } else {
                throw new Error(data.message || 'Search failed');
            }
        } catch (error) {
            console.error('Search error:', error);
            this.displayError(error.message);
            utils.showNotification('Search failed: ' + error.message, 'error');
        } finally {
            this.searchSpinner?.classList.add('d-none');
        }
    },

    displayError(message = 'Error displaying results') {
        if (!this.searchResults) return;
        
        this.searchResults.innerHTML = `
            <div class="p-3 text-center text-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <span>${message}</span>
            </div>`;
        this.searchResults.classList.remove('d-none');
    },

    displayResults(results) {
        if (!this.searchResults) return;

        if (!results.length) {
            this.searchResults.innerHTML = `
                <div class="p-3 text-center text-muted">
                    <i class="bi bi-search me-2"></i>
                    <span>No results found</span>
                </div>`;
        } else {
            this.searchResults.innerHTML = results.map((result, index) => `
                <a href="${result.url}" 
                   class="d-flex align-items-center gap-2 p-2 text-decoration-none text-body rounded hover-bg-light ${index === 0 ? 'active' : ''}"
                   role="option">
                    <i class="bi bi-${result.type === 'project' ? 'folder' : 'check-square'} text-primary"></i>
                    <span>${result.title}</span>
                </a>
            `).join('');
        }

        this.searchResults.classList.remove('d-none');
        this.currentIndex = 0;
    },

    navigateResults(direction) {
        const items = this.searchResults.querySelectorAll('a');
        if (!items.length) return;

        items[this.currentIndex]?.classList.remove('active');
        this.currentIndex = (this.currentIndex + direction + items.length) % items.length;
        items[this.currentIndex]?.classList.add('active');
        items[this.currentIndex]?.scrollIntoView({ block: 'nearest' });
    },

    displayError() {
        if (!this.searchResults) return;
        
        this.searchResults.innerHTML = `
            <div class="p-3 text-center text-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <span>Error displaying results</span>
            </div>`;
        this.searchResults.classList.remove('d-none');
    },

    hideResults() {
        this.searchResults?.classList.add('d-none');
        this.currentIndex = -1;
    }
};

    // Notification System
    const notificationSystem = {
        selectors: {
            container: '.toast-container',
            badge: '.notification-badge',
            body: '.notification-body',
            item: '.notification-item',
            clearForm: 'form[action*="clear_notifications"]',
            dropdown: '#notificationDropdown'
        },

        state: {
            isLoading: false,
            notifications: [],
            unreadCount: 0
        },
    
        init() {
            // Initialize containers and state
            this.setupToastContainer();
            this.setupNotificationListeners();
            this.loadInitialNotifications();
            this.startPeriodicCheck();
        },
    
        setupToastContainer() {
            if (!document.querySelector(this.selectors.container)) {
                const container = document.createElement('div');
                container.className = 'toast-container position-fixed top-0 end-0 p-3';
                document.body.appendChild(container);
            }
        },
    
        setupNotificationListeners() {
            // Handle notification item clicks
            document.addEventListener('click', e => {
                const notification = e.target.closest(this.selectors.item);
                if (notification?.classList.contains('unread')) {
                    this.markAsRead(notification);
                }
            });
    
            // Handle clear all notifications
            const clearForm = document.querySelector(this.selectors.clearForm);
            if (clearForm) {
                clearForm.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    await this.clearAllNotifications(clearForm);
                });
            }
        },
    
        async loadInitialNotifications() {
            if (this.state.isLoading) return;
            this.state.isLoading = true;
        
            try {
                const response = await fetch('/notifications/?format=json', {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json'
                    }
                });
        
                if (!response.ok) throw new Error('Failed to fetch notifications');
        
                const data = await response.json();
                this.state.notifications = data.notifications;
                this.updateNotificationsList(data.notifications);
                this.updateUnreadCount(data.unread_count);
            } catch (error) {
                console.error('Failed to load notifications:', error);
                utils.showNotification('Failed to load notifications', 'error');
            } finally {
                this.state.isLoading = false;
            }
        },
    
        async markAsRead(notification) {
            try {
                const id = notification.dataset.id;
                const response = await fetch(`/notifications/mark-read/${id}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': utils.getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
    
                const data = await response.json();
                if (data.status === 'success') {
                    notification.classList.remove('unread');
                    this.updateUnreadCount(data.unread_count);
                    utils.showNotification('Notification marked as read', 'success');
                }
            } catch (error) {
                console.error('Failed to mark notification as read:', error);
                utils.showNotification('Failed to mark as read', 'error');
            }
        },
    
        async clearAllNotifications(form) {
            if (this.state.isLoading) return;  // Add loading state check
            this.state.isLoading = true;
        
            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': utils.getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
        
                const data = await response.json();
                if (data.status === 'success') {
                    this.updateNotificationsList([]);
                    this.updateUnreadCount(0);
                    utils.showNotification('All notifications cleared', 'success');
                }
            } catch (error) {
                console.error('Clear notifications error:', error);
                utils.showNotification('Failed to clear notifications', 'error');
            } finally {
                this.state.isLoading = false;
            }
        },
    
        updateNotificationsList(notifications) {
            const body = document.querySelector(this.selectors.body);
            if (!body) return;
    
            if (!notifications.length) {
                body.innerHTML = `
                    <div class="p-4 text-center text-muted">
                        <i class="bi bi-bell-slash fs-4 mb-2 d-block"></i>
                        <p class="mb-0 small">No notifications</p>
                    </div>`;
                return;
            }
    
            body.innerHTML = notifications.map(notification => `
                <div class="notification-item p-3 border-bottom ${notification.read ? '' : 'unread'}"
                     data-id="${notification.id}" role="listitem">
                    <div class="d-flex gap-3">
                        <div class="notification-icon rounded-circle bg-primary bg-opacity-10 p-2">
                            <i class="bi bi-bell text-primary"></i>
                        </div>
                        <div>
                            <p class="mb-1">${notification.message}</p>
                            <small class="text-muted">${notification.created_at}</small>
                        </div>
                    </div>
                </div>
            `).join('');
        },
    
        updateUnreadCount(count) {
            const badge = document.querySelector(this.selectors.badge);
            const container = document.querySelector(this.selectors.dropdown);
    
            if (count === 0) {
                badge?.remove();
            } else {
                if (badge) {
                    badge.textContent = count;
                } else if (container) {
                    const newBadge = document.createElement('span');
                    newBadge.className = 'notification-badge';
                    newBadge.setAttribute('aria-label', `${count} unread notifications`);
                    newBadge.textContent = count;
                    container.appendChild(newBadge);
                }
            }
        },
    
        startPeriodicCheck() {
            setInterval(async () => {
                await this.loadInitialNotifications();
            }, 30000); // Check every 30 seconds
        }
    };

// Progress System
const progressSystem = {
    init() {
        this.progressBars = document.querySelectorAll('.progress-bar[data-value]');
        if (this.progressBars?.length) {
            this.observeProgressBars();
        }
    },

    observeProgressBars() {
        if (!this.progressBars?.length) return;

        try {
            const observer = new IntersectionObserver(
                (entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            this.animateProgressBar(entry.target);
                            observer.unobserve(entry.target);
                        }
                    });
                },
                { threshold: 0.1 }
            );

            this.progressBars.forEach(bar => {
                if (bar) {
                    bar.setAttribute('aria-valuemin', '0');
                    bar.setAttribute('aria-valuemax', '100');
                    observer.observe(bar);
                }
            });

            return observer;
        } catch (error) {
            console.error('Progress bar observation error:', error);
            return null;
        }
    },

    animateProgressBar(bar) {
        if (!bar?.dataset?.value) return;

        try {
            const value = parseFloat(bar.dataset.value) || 0;
            const duration = 1000;
            const start = performance.now();
            bar.classList.add('animating');

            const animate = (currentTime) => {
                const elapsed = currentTime - start;
                const progress = Math.min(elapsed / duration, 1);
                
                const eased = this.easeOutCubic(progress);
                const current = eased * value;
                
                bar.style.width = `${current}%`;
                bar.style.backgroundColor = this.getColorForValue(current);
                bar.setAttribute('aria-valuenow', Math.round(current));

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    bar.classList.remove('animating');
                }
            };

            requestAnimationFrame(animate);
        } catch (error) {
            console.error('Progress bar animation error:', error);
            bar.classList.remove('animating');
        }
    },

    easeOutCubic(x) {
        return 1 - Math.pow(1 - x, 3);
    },

    getColorForValue(value) {
        if (value < 30) return '#dc3545';  // red
        if (value < 70) return '#ffc107';  // yellow
        return '#198754';  // green
    },

    updateProgress(progressId, newValue) {
        const bar = document.querySelector(`#${progressId}`);
        if (bar && !isNaN(newValue)) {
            bar.dataset.value = Math.min(Math.max(newValue, 0), 100);
            this.animateProgressBar(bar);
        }
    },

    resetProgress(progressId) {
        const bar = document.querySelector(`#${progressId}`);
        if (bar) {
            bar.classList.remove('animating');
            bar.style.width = '0%';
            bar.dataset.value = '0';
            bar.style.backgroundColor = this.getColorForValue(0);
            bar.setAttribute('aria-valuenow', 0);
        }
    }
};

// Stats Animation System
const statsSystem = {
    init() {
        this.stats = document.querySelectorAll('[data-stat-value]');
        if (this.stats?.length) {
            this.observeStats();
        }
    },

    observeStats() {
        if (!this.stats?.length) return;

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.animateStat(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.1 }
        );

        this.stats.forEach(stat => observer.observe(stat));
    },

    // Add missing animateStats method
    animateStats() {
        if (!this.stats?.length) return;
        this.stats.forEach(stat => this.animateStat(stat));
    },

    animateStat(element) {
        if (!element?.dataset?.statValue) return;

        try {
            const endValue = parseInt(element.dataset.statValue) || 0;
            const duration = 1000;
            const start = performance.now();
            const formatter = new Intl.NumberFormat();

            const animate = (currentTime) => {
                const elapsed = currentTime - start;
                const progress = Math.min(elapsed / duration, 1);
                
                const eased = this.easeOutCubic(progress);
                const current = Math.round(eased * endValue);
                
                element.textContent = formatter.format(current);

                if (progress < 1) {
                    requestAnimationFrame(animate);
                }
            };

            requestAnimationFrame(animate);
        } catch (error) {
            console.error('Stat animation error:', error);
        }
    },

    easeOutCubic(x) {
        return 1 - Math.pow(1 - x, 3);
    }
};

// Update visibility handler
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        progressSystem?.observeProgressBars?.();
        statsSystem?.animateStats?.();
    }
});

// Keyboard Shortcuts
const keyboardShortcuts = {
    init() {
        this.shortcuts = new Map([
            ['b', { key: 'b', ctrl: true, action: () => sidebarSystem.toggleSidebar() }],
            ['k', { key: 'k', ctrl: true, action: () => searchSystem.searchInput?.focus() }],
            ['h', { key: 'h', ctrl: true, action: () => this.showShortcutsHelp() }],
            ['/', { key: '/', action: () => searchSystem.searchInput?.focus() }]
        ]);

        this.bindShortcuts();
    },

    bindShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger in input fields
            if (e.target.matches('input, textarea')) return;

            for (const [key, shortcut] of this.shortcuts) {
                if (this.matchesShortcut(e, shortcut)) {
                    e.preventDefault();
                    shortcut.action();
                    break;
                }
            }
        });
    },

    matchesShortcut(event, shortcut) {
        return event.key === shortcut.key && 
               (!shortcut.ctrl || event.ctrlKey) &&
               (!shortcut.shift || event.shiftKey) &&
               (!shortcut.alt || event.altKey);
    },

    showShortcutsHelp() {
        const shortcuts = Array.from(this.shortcuts.entries())
            .map(([key, shortcut]) => {
                const keys = [];
                if (shortcut.ctrl) keys.push('Ctrl');
                if (shortcut.shift) keys.push('Shift');
                if (shortcut.alt) keys.push('Alt');
                keys.push(shortcut.key.toUpperCase());
                
                return `<div class="shortcut-item">
                    <kbd>${keys.join('+')}</kbd>
                    <span>${key}</span>
                </div>`;
            })
            .join('');

        utils.showNotification(`
            <div class="shortcuts-help">
                <h5>Keyboard Shortcuts</h5>
                ${shortcuts}
            </div>
        `, 'info');
    }
};

// Task Management System
const taskSystem = {
    init() {
        if (document.querySelector('.task-list')) {
            this.setupKanban();
        }
    },

    setupKanban() {
        const taskLists = document.querySelectorAll('.task-list');
        if (!taskLists.length) return;

        taskLists.forEach(list => {
            new Sortable(list, {
                group: 'shared-tasks',
                animation: 150,
                ghostClass: 'task-ghost',
                dragClass: 'task-drag',
                handle: '.task-drag-handle',
                onEnd: this.handleTaskMove.bind(this)
            });
        });
    },

    async handleTaskMove(evt) {
        const taskId = evt.item.dataset.id;
        const newStatus = evt.to.dataset.status;
        const oldStatus = evt.from.dataset.status;

        // Don't make API call if status hasn't changed
        if (newStatus === oldStatus) return;
        
        try {
            // Use the correct URL from urls.py
            const response = await fetch(`/tasks/status/${taskId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': utils.getCookie('csrftoken')
                },
                body: JSON.stringify({ status: newStatus })
            });

            if (!response.ok) {
                throw new Error('Failed to update task status');
            }

            const data = await response.json();
            if (data.status === 'success') {
                utils.showNotification(`Task moved to ${newStatus}`, 'success');
                this.updateTaskCounts();
            } else {
                throw new Error(data.message || 'Update failed');
            }
        } catch (error) {
            console.error('Task move error:', error);
            utils.showNotification(error.message, 'error');
            this.revertTaskPosition(evt);
        }
    },

    revertTaskPosition(evt) {
        if (!evt.item || evt.oldIndex === undefined) return;
        const list = evt.from; // Use from instead of parentNode
        const referenceNode = evt.oldIndex < evt.newIndex 
            ? list.children[evt.oldIndex] 
            : list.children[evt.oldIndex + 1];
        list.insertBefore(evt.item, referenceNode);
    },

    updateTaskCounts() {
        document.querySelectorAll('.task-list').forEach(list => {
            const count = list.children.length;
            const badge = list.closest('.kanban-column')
                             .querySelector('.badge');
            if (badge) {
                badge.textContent = count;
            }
        });
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
                    const bsModal = new bootstrap.Modal(modal);
                    bsModal.show();
                    
                    // Handle form submission in modal if exists
                    const form = modal.querySelector('form');
                    if (form) {
                        form.addEventListener('submit', this.handleModalFormSubmit);
                    }
                }
            }
        });
    },

    handleModalFormSubmit(e) {
        e.preventDefault();
        // Add form submission logic here
    }
};

const formSystem = {
    selectors: {
        ajaxForm: 'form[data-ajax]',
        validateForm: 'form[data-validate]',
        fileInput: 'input[type="file"]',
        preview: '[data-preview-for]'
    },

    state: {
        forms: new Map(),
        fileTypes: {
            image: ['image/jpeg', 'image/png', 'image/gif'],
            document: ['.pdf', '.doc', '.docx', '.txt']
        }
    },

    init() {
        this.setupFormValidation();
        this.setupFileUploads();
        this.setupAjaxForms();
        this.setupFormResets();
    },

    setupAjaxForms() {
        document.querySelectorAll(this.selectors.ajaxForm).forEach(form => {
            // Initialize form state
            if (!form.id) form.id = `form-${Date.now()}`;
            this.state.forms.set(form.id, { isSubmitting: false });
            
            form.addEventListener('submit', this.handleAjaxSubmit.bind(this));
        });
    },

    setupFormValidation() {
        document.querySelectorAll(this.selectors.validateForm).forEach(form => {
            if (!form.id) form.id = `form-${Date.now()}`;
            this.state.forms.set(form.id, { isSubmitting: false });
            
            this.setupFieldValidation(form);
            form.addEventListener('submit', this.validateForm.bind(this));
        });
    },

    setupFieldValidation(form) {
        form.querySelectorAll('input, select, textarea').forEach(field => {
            ['input', 'blur'].forEach(event => {
                field.addEventListener(event, () => this.validateField(field));
            });
        });
    },

    validateField(field) {
        const isValid = field.checkValidity();
        field.classList.toggle('is-invalid', !isValid);
        field.classList.toggle('is-valid', isValid);
        
        const feedback = field.nextElementSibling;
        if (feedback?.classList.contains('invalid-feedback')) {
            feedback.textContent = field.validationMessage;
        }

        return isValid;
    },

    validateForm(e) {
        const form = e.target;
        let isValid = true;

        form.querySelectorAll('input, select, textarea').forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        if (!isValid) {
            e.preventDefault();
            e.stopPropagation();
        }

        form.classList.add('was-validated');
        return isValid;
    },

    setupFileUploads() {
        document.querySelectorAll(this.selectors.fileInput).forEach(input => {
            input.addEventListener('change', this.handleFileSelect.bind(this));
        });
    },

    handleFileSelect(e) {
        const input = e.target;
        const files = Array.from(input.files);
        const maxSize = (input.dataset.maxSize || 5) * 1024 * 1024;
        const allowedTypes = input.accept?.split(',') || [];

        for (const file of files) {
            if (!this.validateFile(file, maxSize, allowedTypes)) {
                input.value = '';
                return;
            }
        }

        this.updateFilePreview(input, files[0]);
    },

    validateFile(file, maxSize, allowedTypes) {
        if (file.size > maxSize) {
            utils.showNotification(
                `File ${file.name} exceeds ${maxSize/1024/1024}MB limit`, 
                'error'
            );
            return false;
        }

        if (allowedTypes.length && !this.isFileTypeAllowed(file, allowedTypes)) {
            utils.showNotification(`File type ${file.type} not allowed`, 'error');
            return false;
        }

        return true;
    },

    isFileTypeAllowed(file, allowedTypes) {
        return allowedTypes.some(type => {
            const cleanType = type.trim();
            return cleanType === file.type || 
                   cleanType === `.${file.name.split('.').pop()}` ||
                   cleanType.includes('*');
        });
    },

    updateFilePreview(input, file) {
        const previewEl = document.querySelector(`[data-preview-for="${input.id}"]`);
        if (!previewEl || !file) return;

        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = e => {
                previewEl.src = e.target.result;
                previewEl.classList.remove('d-none');
            };
            reader.readAsDataURL(file);
        } else {
            previewEl.src = '/static/images/file-icon.png';
            previewEl.classList.remove('d-none');
        }
    },

    resetForm(form) {
        if (!form) return;
        
        // Reset form fields
        form.reset();
        
        // Remove validation classes
        form.classList.remove('was-validated');
        form.querySelectorAll('.is-invalid, .is-valid').forEach(field => {
            field.classList.remove('is-invalid', 'is-valid');
        });
        
        // Clear error messages
        form.querySelectorAll('.invalid-feedback').forEach(feedback => {
            feedback.textContent = '';
        });
        
        // Reset file previews
        form.querySelectorAll('[data-preview-for]').forEach(preview => {
            preview.classList.add('d-none');
            preview.src = '';
        });

        // Reset submit button
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = submitButton.dataset.originalText || 'Save';
        }
    },

    async handleAjaxSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const formState = this.state.forms.get(form.id);
        
        if (formState?.isSubmitting) return;
        
        const submitButton = form.querySelector('button[type="submit"]');
        if (!submitButton?.dataset.originalText) {
            submitButton.dataset.originalText = submitButton.innerHTML;
        }
        
        try {
            if (!this.validateForm({ target: form })) {
                throw new Error('Please fix the validation errors');
            }
    
            formState.isSubmitting = true;
            form.classList.add('is-submitting');
            
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
            }
    
            const formData = new FormData(form);
            
            const response = await fetch(form.action, {
                method: form.method || 'POST',
                headers: {
                    'X-CSRFToken': utils.getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });
    
            // Special handling for notification clearing
            if (form.action.includes('clear_notifications')) {
                const data = await response.json();
                if (data.status === 'success') {
                    window.projectHub?.notificationSystem?.updateNotificationsList?.([]);
                    window.projectHub?.notificationSystem?.updateUnreadCount?.(0);
                    utils.showNotification(data.message || 'Notifications cleared', 'success');
                    return;
                }
                throw new Error(data.message || 'Failed to clear notifications');
            }
    
            // Handle project/task deletion
            if (form.action.includes('delete')) {
                const data = await response.json();
                if (data.success) {
                    utils.showNotification(data.message || 'Deleted successfully', 'success');
                    if (data.redirect_url) {
                        setTimeout(() => window.location.href = data.redirect_url, 1000);
                    } else {
                        window.location.href = response.url || '/';
                    }
                    return;
                }
                throw new Error(data.message || 'Deletion failed');
            }
    
            // Handle other responses
            const contentType = response.headers.get('content-type');
            if (contentType?.includes('application/json')) {
                const data = await response.json();
                
                if (data.success || data.status === 'success') {
                    utils.showNotification(data.message || 'Success', 'success');
                    if (data.redirect_url) {
                        setTimeout(() => window.location.href = data.redirect_url, 1000);
                    } else {
                        this.resetForm(form);
                    }
                } else {
                    if (data.errors) {
                        this.handleValidationErrors(form, data.errors);
                    }
                    throw new Error(data.message || 'Form submission failed');
                }
            } else {
                // Handle non-JSON responses
                const text = await response.text();
                
                if (response.ok) {
                    if (response.redirected || response.url !== window.location.href) {
                        window.location.href = response.url;
                        return;
                    }
                    utils.showNotification('Success', 'success');
                    this.resetForm(form);
                } else {
                    // Try to extract form with errors
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(text, 'text/html');
                    const newForm = doc.querySelector('form');
                    if (newForm) {
                        form.innerHTML = newForm.innerHTML;
                    }
                    throw new Error('Form submission failed');
                }
            }
        } catch (error) {
            console.error('Form submission error:', error);
            utils.showNotification(error.message, 'error');
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = submitButton.dataset.originalText;
            }
            form.classList.remove('is-submitting');
            formState.isSubmitting = false;
        }
    },

    handleValidationErrors(form, errors) {
        if (!errors) return;
        
        Object.entries(errors).forEach(([field, messages]) => {
            const input = form.querySelector(`[name="${field}"]`);
            if (input) {
                input.classList.add('is-invalid');
                const feedback = input.nextElementSibling;
                if (feedback?.classList.contains('invalid-feedback')) {
                    feedback.textContent = Array.isArray(messages) ? messages.join(', ') : messages;
                }
            }
        });
    },

    setupFormResets() {
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('reset', () => this.resetForm(form));
        });
    }
};

taskSystem.handleTaskReorder = async function(evt) {
    if (!evt?.item?.dataset?.taskId || evt.newIndex === undefined) {
        console.error('Invalid task reorder event:', evt);
        return;
    }

    const taskId = evt.item.dataset.taskId;
    const newIndex = evt.newIndex;
    const listId = evt.to.dataset.listId;
    const originalPosition = evt.oldIndex;

    try {
        const response = await fetch(`/api/tasks/${taskId}/reorder/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': utils.getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ 
                position: newIndex,
                list_id: listId,
                original_position: originalPosition
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Reorder failed');
        }

        if (data.positions) {
            this.updateTaskPositions(data.positions);
        }
        
        utils.showNotification('Task order updated', 'success');

    } catch (error) {
        console.error('Task reorder error:', error);
        utils.showNotification(error.message, 'error');
        this.revertTaskPosition(evt);
    }
};

taskSystem.revertTaskPosition = function(evt) {
    if (!evt.item || evt.oldIndex === undefined) return;
    
    const list = evt.item.parentNode;
    const referenceNode = evt.oldIndex < evt.newIndex 
        ? list.children[evt.oldIndex] 
        : list.children[evt.oldIndex + 1];
        
    list.insertBefore(evt.item, referenceNode);
};

// Loading System
const loadingSystem = {
    selectors: {
        loader: '#pageLoader'
    },

    init() {
        this.loader = document.querySelector(this.selectors.loader);
    },

    show() {
        this.loader?.classList.remove('d-none');
    },

    hide() {
        this.loader?.classList.add('d-none');
    }
};

document.addEventListener('DOMContentLoaded', function() {
    // Initialize core utilities
    window.projectHub = { utils };

    try {
        // Core systems
        loadingSystem.init();
        themeSystem.init();
        sidebarSystem.init();
        notificationSystem.init();
        formSystem.init();
        
        // UI systems with checks
        if (document.querySelector('.search-input')) {
            searchSystem.init();
        }
        if (document.querySelector('.notification-badge') || document.querySelector('.notification-container')) {
            notificationSystem.init();
        }
        if (document.querySelectorAll('.progress-bar[data-value]').length) {
            progressSystem.init();
        }
        if (document.querySelectorAll('[data-stat-value]').length) {
            statsSystem.init();
        }
        if (document.querySelector('.task-list')) {
            taskSystem.init();
        }

        // Core functionality systems
        keyboardShortcuts.init();
        modalSystem.init();
        
        if (document.querySelector('form')) {
            formSystem.init();
        }

        // Export systems
        Object.assign(window.projectHub, {
            themeSystem,
            progressSystem,
            statsSystem,
            sidebarSystem,
            searchSystem,
            notificationSystem,
            keyboardShortcuts,
            taskSystem,
            modalSystem,
            formSystem,
            loadingSystem
        });

    } catch (error) {
        console.error('Initialization error:', error);
        window.projectHub.utils?.showNotification('Failed to initialize application', 'error');
    }
});

// Add visibility handler
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        window.projectHub?.progressSystem?.observeProgressBars?.();
        window.projectHub?.statsSystem?.animateStats?.();
    }
});