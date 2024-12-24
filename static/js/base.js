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
        const mainContent = document.querySelector('.main-content');
        const MOBILE_BREAKPOINT = 768;
        
        // State management
        let isSidebarExpanded = localStorage.getItem('sidebarExpanded') === 'true';
        let isMobile = window.innerWidth < MOBILE_BREAKPOINT;
        
        // Initialize sidebar state
        function updateSidebarState(expanded) {
            isSidebarExpanded = expanded;
            document.body.classList.toggle('sidebar-expanded', expanded);
            sidebar?.classList.toggle('show', expanded);
            localStorage.setItem('sidebarExpanded', expanded);
            
            // Add transition class after initial load
            requestAnimationFrame(() => {
                sidebar?.classList.add('sidebar-transition');
            });
        }
        
        // Set initial state based on screen size
        function initializeBasedOnScreenSize() {
            isMobile = window.innerWidth < MOBILE_BREAKPOINT;
            if (isMobile) {
                updateSidebarState(false);
            } else {
                updateSidebarState(isSidebarExpanded);
            }
        }
        
        // Handle sidebar toggle click
        function handleSidebarToggle(e) {
            e?.preventDefault();
            e?.stopPropagation();
            updateSidebarState(!isSidebarExpanded);
        }
        
        // Handle clicks outside sidebar on mobile
        function handleOutsideClick(e) {
            if (isMobile && 
                isSidebarExpanded && 
                sidebar && 
                !sidebar.contains(e.target) && 
                !sidebarToggle?.contains(e.target)) {
                updateSidebarState(false);
            }
        }
        
        // Handle window resize
        function handleResize() {
            const wasMobile = isMobile;
            isMobile = window.innerWidth < MOBILE_BREAKPOINT;
            
            // If changing between mobile and desktop
            if (wasMobile !== isMobile) {
                if (isMobile) {
                    updateSidebarState(false);
                } else {
                    // On desktop, restore previous state or default to expanded
                    updateSidebarState(localStorage.getItem('sidebarExpanded') !== 'false');
                }
            }
        }
        
        // Initialize event listeners
        function initializeEventListeners() {
            if (sidebarToggle && sidebar) {
                sidebarToggle.addEventListener('click', handleSidebarToggle);
                document.addEventListener('click', handleOutsideClick);
                
                // Debounced resize handler
                let resizeTimer;
                window.addEventListener('resize', () => {
                    clearTimeout(resizeTimer);
                    resizeTimer = setTimeout(handleResize, 250);
                });
                
                // Handle escape key to close sidebar on mobile
                document.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape' && isMobile && isSidebarExpanded) {
                        updateSidebarState(false);
                    }
                });
            }
        }
        
        // Initialize
        initializeBasedOnScreenSize();
        initializeEventListeners();
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
                    onStart: (evt) => {
                        evt.item.classList.add('dragging');
                        document.body.classList.add('dragging-active');
                    },
                    onEnd: (evt) => {
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
            // Revert the task to its original position
            const originalList = document.getElementById(taskElement.dataset.originalStatus);
            if (originalList) {
                originalList.appendChild(taskElement);
            }
        } finally {
            taskElement.classList.remove('updating');
        }
    }

    // Enhanced Notification System
    function showNotification(message, type = 'info') {
        // Create container if it doesn't exist
        let container = document.querySelector('.alert-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'alert-container';
            document.body.appendChild(container);
        }

        // Create notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show glass-card`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Add to container
        container.appendChild(notification);

        // Initialize Bootstrap alert
        const bsAlert = new bootstrap.Alert(notification);

        // Remove after delay
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                bsAlert.dispose();
                notification.remove();
            }, 150);
        }, 3000);
    }

    // Notification Badge Management
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

    // Enhanced Search Functionality
    function initializeSearch() {
        const searchInput = document.querySelector('.search-wrapper input');
        const searchWrapper = document.querySelector('.search-wrapper');
        
        if (searchInput) {
            let debounceTimer;
            
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                const searchTerm = e.target.value.trim();
                
                if (searchTerm.length > 0) {
                    searchWrapper.classList.add('is-searching');
                } else {
                    searchWrapper.classList.remove('is-searching');
                }
                
                if (searchTerm.length > 2) {
                    debounceTimer = setTimeout(() => performSearch(searchTerm), 300);
                }
            });

            // Clear search on escape
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    searchInput.value = '';
                    searchWrapper.classList.remove('is-searching');
                }
            });
        }
    }

    // Perform Search
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

    // CSRF Token Utility
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    // Initialize all components
    initializeTheme();
    initializeSidebar();
    initializeKanban();
    initializeSearch();
});