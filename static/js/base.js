document.addEventListener('DOMContentLoaded', function () {
    // Utility Functions
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Theme System
    function initializeTheme() {
        const themeToggle = document.getElementById('themeToggle');
        const currentTheme = localStorage.getItem('theme') || 'light';
        const icon = themeToggle?.querySelector('i');

        function updateTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            document.body.classList.remove('theme-light', 'theme-dark');
            document.body.classList.add(`theme-${theme}`);
            localStorage.setItem('theme', theme);
            
            if (icon) {
                icon.classList.remove('bi-sun', 'bi-moon');
                icon.classList.add(theme === 'dark' ? 'bi-moon' : 'bi-sun');
            }
        }

        updateTheme(currentTheme);

        themeToggle?.addEventListener('click', () => {
            const newTheme = document.body.classList.contains('theme-light') ? 'dark' : 'light';
            updateTheme(newTheme);
        });
    }

    // Sidebar System
    function initializeSidebar() {
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('sidebar');
        const MOBILE_BREAKPOINT = 768;

        let isSidebarExpanded = localStorage.getItem('sidebarExpanded') === 'true';
        let isMobile = window.innerWidth < MOBILE_BREAKPOINT;

        function updateSidebarState(expanded) {
            isSidebarExpanded = expanded;
            document.body.classList.toggle('sidebar-expanded', expanded);
            sidebar?.classList.toggle('show', expanded);
            localStorage.setItem('sidebarExpanded', expanded);
        }

        updateSidebarState(isSidebarExpanded && !isMobile);

        sidebarToggle?.addEventListener('click', (e) => {
            e.preventDefault();
            updateSidebarState(!isSidebarExpanded);
        });

        document.addEventListener('click', (e) => {
            if (isMobile && isSidebarExpanded && 
                !sidebar?.contains(e.target) && 
                !sidebarToggle?.contains(e.target)) {
                updateSidebarState(false);
            }
        });

        window.addEventListener('resize', debounce(() => {
            const wasMobile = isMobile;
            isMobile = window.innerWidth < MOBILE_BREAKPOINT;
            if (wasMobile !== isMobile) {
                updateSidebarState(isMobile ? false : isSidebarExpanded);
            }
        }, 250));

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isSidebarExpanded) {
                updateSidebarState(false);
            }
        });
    }

    // Search System
    function initializeSearch() {
        const searchInput = document.querySelector('.search-wrapper input');
        const searchResults = document.querySelector('.search-results');
        const searchWrapper = document.querySelector('.search-wrapper');
        let currentSearchTerm = '';

        if (!searchInput || !searchResults) return;

        const performSearch = debounce(async (term) => {
            try {
                searchWrapper?.classList.add('is-searching');
                const response = await fetch(`/api/search?q=${encodeURIComponent(term)}`);
                if (!response.ok) throw new Error('Search failed');

                const results = await response.json();
                if (term === currentSearchTerm) {
                    updateSearchResults(results);
                }
            } catch (error) {
                console.error('Search error:', error);
                showNotification('Search failed', 'error');
            } finally {
                searchWrapper?.classList.remove('is-searching');
            }
        }, 300);

        function updateSearchResults(results) {
            searchResults.innerHTML = results.length ? 
                results.map(result => `
                    <a href="${result.url}" class="search-result-item">
                        <div class="search-result-title">${result.title}</div>
                        <div class="search-result-description">${result.description}</div>
                    </a>
                `).join('') :
                '<div class="search-no-results">No results found</div>';
        }

        searchInput.addEventListener('input', (e) => {
            currentSearchTerm = e.target.value.trim();
            
            searchWrapper.classList.toggle('is-searching', currentSearchTerm.length > 0);
            searchResults.style.display = currentSearchTerm.length > 0 ? 'block' : 'none';

            if (currentSearchTerm.length >= 2) {
                performSearch(currentSearchTerm);
            } else {
                searchResults.innerHTML = '';
            }
        });

        document.addEventListener('click', (e) => {
            if (!searchWrapper.contains(e.target)) {
                searchResults.style.display = 'none';
                searchWrapper.classList.remove('is-searching');
            }
        });

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                searchInput.value = '';
                searchResults.style.display = 'none';
                searchWrapper.classList.remove('is-searching');
            }
        });
    }

    // Notification System
    function showNotification(message, type = 'info') {
        const container = document.querySelector('.notification-container') || 
            (() => {
                const el = document.createElement('div');
                el.className = 'notification-container';
                document.body.appendChild(el);
                return el;
            })();

        const notification = document.createElement('div');
        notification.className = `notification notification-${type} fade-in`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="bi ${type === 'success' ? 'bi-check-circle' : 
                             type === 'error' ? 'bi-x-circle' : 
                             'bi-info-circle'}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close">×</button>
        `;

        container.appendChild(notification);

        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });

        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    // Kanban Board System
    function initializeKanban() {
        const lists = ['todo', 'inprogress', 'done'].map(id => document.getElementById(id));
        
        lists.forEach(list => {
            if (!list) return;

            new Sortable(list, {
                group: 'kanban',
                animation: 150,
                ghostClass: 'sortable-ghost',
                dragClass: 'sortable-drag',
                handle: '.task-drag-handle',
                filter: '.task-locked',
                onStart(evt) {
                    const item = evt.item;
                    item.classList.add('dragging');
                    item.dataset.originalStatus = evt.from.id;
                    document.body.classList.add('dragging-active');
                },
                onEnd(evt) {
                    const item = evt.item;
                    item.classList.remove('dragging');
                    document.body.classList.remove('dragging-active');

                    if (evt.from.id !== evt.to.id) {
                        const taskId = item.dataset.id;
                        const newStatus = evt.to.id;
                        updateTaskStatus(taskId, newStatus, evt.from.id);
                    }
                }
            });
        });
    }

    // Task Status Update
    async function updateTaskStatus(taskId, newStatus, originalStatus) {
        const taskElement = document.querySelector(`[data-id="${taskId}"]`);
        if (!taskElement) return;

        taskElement.classList.add('updating');

        try {
            const response = await fetch(`/update_task_status/${taskId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ status: newStatus, originalStatus })
            });

            const data = await response.json();
            
            if (!response.ok) throw new Error(data.message || 'Failed to update task status');

            showNotification('Task status updated successfully', 'success');
            taskElement.dataset.status = newStatus;

        } catch (error) {
            console.error('Error:', error);
            showNotification(error.message || 'Failed to update task status', 'error');
            const originalList = document.getElementById(originalStatus);
            if (originalList) originalList.appendChild(taskElement);
        } finally {
            taskElement.classList.remove('updating');
        }
    }

    // Initialize all components
    try {
        initializeTheme();
        initializeSidebar();
        initializeSearch();
        initializeKanban();
    } catch (error) {
        console.error('Initialization error:', error);
        showNotification('Failed to initialize application', 'error');
    }
});