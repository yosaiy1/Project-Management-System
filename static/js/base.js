document.addEventListener('DOMContentLoaded', function () {
    // Theme Management
    function initializeTheme() {
        const themeToggle = document.getElementById('themeToggle');
        const currentTheme = localStorage.getItem('theme') || 'light';
        document.body.classList.add(`theme-${currentTheme}`);

        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const newTheme = document.body.classList.contains('theme-light') ? 'dark' : 'light';
                document.body.classList.replace(`theme-${currentTheme}`, `theme-${newTheme}`);
                localStorage.setItem('theme', newTheme);

                // Update theme toggle icon
                const icon = themeToggle.querySelector('i');
                if (icon) {
                    icon.classList.replace(
                        newTheme === 'dark' ? 'bi-sun' : 'bi-moon',
                        newTheme === 'dark' ? 'bi-moon' : 'bi-sun'
                    );
                }
            });
        }
    }

    // Sidebar Management
    function initializeSidebar() {
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('sidebar');
        const MOBILE_BREAKPOINT = 768;

        let isSidebarExpanded = localStorage.getItem('sidebarExpanded') === 'true';
        let isMobile = window.innerWidth < MOBILE_BREAKPOINT;

        // Update sidebar state
        const updateSidebarState = (expanded) => {
            isSidebarExpanded = expanded;
            document.body.classList.toggle('sidebar-expanded', expanded);
            sidebar?.classList.toggle('show', expanded);
            localStorage.setItem('sidebarExpanded', expanded);

            requestAnimationFrame(() => {
                sidebar?.classList.add('sidebar-transition');
            });
        };

        // Adjust sidebar state on screen resize
        const handleResize = () => {
            const wasMobile = isMobile;
            isMobile = window.innerWidth < MOBILE_BREAKPOINT;

            if (wasMobile !== isMobile) {
                updateSidebarState(isMobile ? false : isSidebarExpanded);
            }
        };

        const handleSidebarToggle = (e) => {
            e?.preventDefault();
            e?.stopPropagation();
            updateSidebarState(!isSidebarExpanded);
        };

        const handleOutsideClick = (e) => {
            if (isMobile && isSidebarExpanded && !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                updateSidebarState(false);
            }
        };

        const initializeEventListeners = () => {
            if (sidebarToggle && sidebar) {
                sidebarToggle.addEventListener('click', handleSidebarToggle);
                document.addEventListener('click', handleOutsideClick);

                let resizeTimer;
                window.addEventListener('resize', () => {
                    clearTimeout(resizeTimer);
                    resizeTimer = setTimeout(handleResize, 250);
                });

                document.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape' && isMobile && isSidebarExpanded) {
                        updateSidebarState(false); // Close sidebar on Escape
                    }
                });
            }
        };

        initializeEventListeners();
        handleResize();
    }

    // Kanban Board Drag-and-Drop
    function initializeKanban() {
        const lists = ['todo', 'inprogress', 'done'].map(id => document.getElementById(id));

        lists.forEach(list => {
            if (list) {
                new Sortable(list, {
                    group: 'kanban',
                    animation: 150,
                    ghostClass: 'sortable-ghost',
                    dragClass: 'sortable-drag',
                    onStart(evt) {
                        evt.item.classList.add('dragging');
                        document.body.classList.add('dragging-active');
                    },
                    onEnd(evt) {
                        evt.item.classList.remove('dragging');
                        document.body.classList.remove('dragging-active');
                        const taskId = evt.item.getAttribute('data-id');
                        const newStatus = evt.to.id;
                        updateTaskStatus(taskId, newStatus);
                    }
                });
            }
        });
    }

    // Task Status Update
    async function updateTaskStatus(taskId, newStatus) {
        const taskElement = document.querySelector(`[data-id="${taskId}"]`);
        if (!taskElement) return;

        taskElement.classList.add('updating');
        try {
            const response = await fetch(`/projects/update_task_status/${taskId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ status: newStatus })
            });

            if (!response.ok) throw new Error('Failed to update task status');
            showNotification('Task status updated successfully', 'success');
        } catch (error) {
            console.error('Error:', error);
            showNotification('Failed to update task status', 'error');
            revertTaskPosition(taskElement); // Revert task to original position on error
        } finally {
            taskElement.classList.remove('updating');
        }
    }

    // Revert Task Position
    function revertTaskPosition(taskElement) {
        const originalList = document.getElementById(taskElement.dataset.originalStatus);
        if (originalList) {
            originalList.appendChild(taskElement);
        }
    }

    // Notification Badge Management
    function showNotification(message, type = 'info') {
        let container = document.querySelector('.alert-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'alert-container';
            document.body.appendChild(container);
        }

        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show glass-card`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        container.appendChild(notification);

        const bsAlert = new bootstrap.Alert(notification);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                bsAlert.dispose();
                notification.remove();
            }, 150);
        }, 3000);
    }

    function updateNotificationCount(count) {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            if (count > 0) {
                badge.classList.add('pulse');
                badge.style.display = 'block';
                badge.textContent = count;
            } else {
                badge.classList.remove('pulse');
                badge.style.display = 'none';
            }
        }
    }

    async function fetchNotifications() {
        try {
            const response = await fetch('/notifications/get_notifications');
            if (!response.ok) throw new Error('Failed to fetch notifications');

            const data = await response.json();
            updateNotificationCount(data.unread_count);

            data.notifications.forEach(notification => {
                if (!notification.read) {
                    showNotification(notification.message, 'info');
                }
            });
        } catch (error) {
            console.error('Notification fetch error:', error);
        }
    }

    async function clearNotifications() {
        try {
            const response = await fetch('/projects/notifications/clear_all/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });

            if (!response.ok) throw new Error('Failed to clear notifications');
            updateNotificationCount(0);
            document.querySelector('.notification-body').innerHTML = `
                <div class="p-4 text-center text-muted">
                    <i class="bi bi-bell-slash fs-4 mb-2 d-block"></i>
                    <p class="mb-0 small">No notifications</p>
                </div>
            `;
        } catch (error) {
            console.error('Clear notifications error:', error);
            showNotification('Failed to clear notifications', 'error');
        }
    }

    async function markAsRead(notificationId) {
        try {
            const response = await fetch(`/notifications/mark_as_read/${notificationId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            if (!response.ok) throw new Error('Failed to mark notification as read');

            const notificationElement = document.querySelector(`.notification-item[data-id="${notificationId}"]`);
            if (notificationElement) {
                notificationElement.classList.remove('unread');
            }
        } catch (error) {
            console.error('Mark as read error:', error);
            showNotification('Failed to mark notification as read', 'error');
        }
    }

    // CSRF Token Utility
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    // Enhanced Search Functionality
    function initializeSearch() {
        const searchInput = document.querySelector('.search-wrapper input');
        const searchWrapper = document.querySelector('.search-wrapper');

        if (searchInput) {
            let debounceTimer;

            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                const searchTerm = e.target.value.trim();

                searchWrapper.classList.toggle('is-searching', searchTerm.length > 0);

                if (searchTerm.length > 2) {
                    debounceTimer = setTimeout(() => performSearch(searchTerm), 300);
                }
            });

            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    searchInput.value = '';
                    searchWrapper.classList.remove('is-searching');
                }
            });
        }
    }

    async function performSearch(term) {
        const searchWrapper = document.querySelector('.search-wrapper');
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(term)}`);
            if (!response.ok) throw new Error('Search failed');

            const results = await response.json();
            updateSearchResults(results);
        } catch (error) {
            console.error('Search error:', error);
            showNotification('Search failed', 'error');
        } finally {
            searchWrapper?.classList.remove('is-searching');
        }
    }

    // Initialize all components
    initializeTheme();
    initializeSidebar();
    initializeKanban();
    initializeSearch();

    // Fetch and update notifications
    fetchNotifications();
});
