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
            
            // Get saved theme or use system preference
            this.currentTheme = localStorage.getItem('theme') || 
                              (this.prefersDark.matches ? 'dark' : 'light');
            
            this.applyTheme(this.currentTheme);
            this.bindEvents();
        },

        applyTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            document.body.className = `theme-${theme}`;
            localStorage.setItem('theme', theme);
            
            // Update toggle button icon
            if (this.themeToggle) {
                const icon = this.themeToggle.querySelector('i');
                if (icon) {
                    icon.className = `bi bi-${theme === 'dark' ? 'moon-stars' : 'sun'} fs-5`;
                }
            }
        },

        bindEvents() {
            // Theme toggle click
            this.themeToggle?.addEventListener('click', () => {
                const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
                this.currentTheme = newTheme;
                this.applyTheme(newTheme);
            });

            // System theme change
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
            this.toggle = document.getElementById('sidebarToggle');
            this.overlay = document.querySelector('.sidebar-overlay');
            this.mainContent = document.getElementById('main-content');
            this.mobileBreakpoint = 768;
            
            this.state = {
                expanded: localStorage.getItem('sidebarExpanded') === 'true',
                isMobile: window.innerWidth < this.mobileBreakpoint
            };

            this.setupSidebar();
            this.bindEvents();
        },

        setupSidebar() {
            this.updateSidebarState(this.state.expanded && !this.state.isMobile);
            
            // Touch support for mobile
            if (this.sidebar) {
                let touchStartX = 0;
                let touchEndX = 0;

                this.sidebar.addEventListener('touchstart', e => {
                    touchStartX = e.changedTouches[0].screenX;
                }, { passive: true });

                this.sidebar.addEventListener('touchend', e => {
                    touchEndX = e.changedTouches[0].screenX;
                    if (touchStartX - touchEndX > 50) {
                        this.updateSidebarState(false);
                    }
                }, { passive: true });
            }
        },

        updateSidebarState(expanded) {
            this.state.expanded = expanded;
            document.body.classList.toggle('sidebar-expanded', expanded);
            this.sidebar?.classList.toggle('show', expanded);
            this.overlay?.classList.toggle('show', expanded && this.state.isMobile);
            localStorage.setItem('sidebarExpanded', expanded);

            if (this.toggle) {
                this.toggle.setAttribute('aria-expanded', expanded.toString());
            }
        },

        bindEvents() {
            // Toggle click
            this.toggle?.addEventListener('click', () => {
                this.updateSidebarState(!this.state.expanded);
            });

            // Overlay click
            this.overlay?.addEventListener('click', () => {
                this.updateSidebarState(false);
            });

            // Window resize
            window.addEventListener('resize', utils.debounce(() => {
                const wasMobile = this.state.isMobile;
                this.state.isMobile = window.innerWidth < this.mobileBreakpoint;
                
                if (wasMobile !== this.state.isMobile) {
                    this.updateSidebarState(this.state.isMobile ? false : this.state.expanded);
                }
            }, 250));

            // Escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.state.expanded) {
                    this.updateSidebarState(false);
                }
            });
        }
    };

    // Search System
    const searchSystem = {
        init() {
            this.wrapper = document.querySelector('.search-wrapper');
            this.input = this.wrapper?.querySelector('input[type="search"]');
            this.results = this.wrapper?.querySelector('.search-results');
            this.spinner = this.wrapper?.querySelector('.search-spinner');

            if (!this.wrapper || !this.input) return;

            this.state = {
                currentTerm: '',
                isSearching: false,
                selectedIndex: -1
            };

            this.bindEvents();
        },

        async performSearch(term) {
            if (!term || term.length < 2) {
                this.hideResults();
                return;
            }

            try {
                this.setState({ isSearching: true });
                const response = await fetch(`/api/search?q=${encodeURIComponent(term)}`);
                
                if (!response.ok) throw new Error('Search failed');
                
                const results = await response.json();
                
                if (term === this.state.currentTerm) {
                    this.showResults(results);
                }
            } catch (error) {
                console.error('Search error:', error);
                utils.showNotification('Search failed. Please try again.', 'error');
            } finally {
                this.setState({ isSearching: false });
            }
        },

        setState(newState) {
            this.state = { ...this.state, ...newState };
            this.spinner?.classList.toggle('d-none', !this.state.isSearching);
            this.wrapper?.classList.toggle('is-searching', this.state.isSearching);
        },

        showResults(results) {
            if (!this.results) return;

            if (!results.length) {
                this.results.innerHTML = `
                    <div class="search-empty p-3 text-center">
                        <i class="bi bi-search fs-4 mb-2"></i>
                        <p class="mb-0">No results found</p>
                    </div>
                `;
            } else {
                this.results.innerHTML = results.map((item, index) => `
                    <a href="${item.url}" 
                       class="search-result-item ${index === this.state.selectedIndex ? 'active' : ''}"
                       role="option"
                       aria-selected="${index === this.state.selectedIndex}">
                        <i class="bi bi-${this.getItemIcon(item.type)}"></i>
                        <div class="result-content">
                            <div class="result-title">${item.title}</div>
                            <div class="result-meta">${item.description}</div>
                        </div>
                    </a>
                `).join('');
            }

            this.results.classList.add('show');
        },

        hideResults() {
            this.results?.classList.remove('show');
        },

        getItemIcon(type) {
            return {
                'project': 'folder',
                'task': 'check-square',
                'user': 'person'
            }[type] || 'file-text';
        },

        bindEvents() {
            // Search input
            this.input?.addEventListener('input', utils.debounce((e) => {
                const term = e.target.value.trim();
                this.state.currentTerm = term;
                this.performSearch(term);
            }, 300));

            // Keyboard navigation
            this.input?.addEventListener('keydown', (e) => {
                const results = this.results?.querySelectorAll('.search-result-item') || [];
                
                switch(e.key) {
                    case 'ArrowDown':
                    case 'ArrowUp':
                        e.preventDefault();
                        this.navigateResults(e.key === 'ArrowUp' ? -1 : 1, results.length);
                        break;
                    case 'Enter':
                        if (this.state.selectedIndex >= 0) {
                            e.preventDefault();
                            results[this.state.selectedIndex]?.click();
                        }
                        break;
                    case 'Escape':
                        this.hideResults();
                        this.input.blur();
                        break;
                }
            });
                        // Click outside to close results
                        document.addEventListener('click', (e) => {
                            if (!this.wrapper?.contains(e.target)) {
                                this.hideResults();
                            }
                        });
                    },
            
                    navigateResults(direction, totalResults) {
                        if (totalResults === 0) return;
            
                        this.state.selectedIndex = ((this.state.selectedIndex + direction) + totalResults) % totalResults;
                        
                        const results = this.results?.querySelectorAll('.search-result-item');
                        results?.forEach((result, index) => {
                            result.classList.toggle('active', index === this.state.selectedIndex);
                            result.setAttribute('aria-selected', index === this.state.selectedIndex);
                            
                            if (index === this.state.selectedIndex) {
                                result.scrollIntoView({ block: 'nearest' });
                            }
                        });
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
            
                // Initialize all systems
                try {
                    themeSystem.init();
                    sidebarSystem.init();
                    searchSystem.init();
                    progressSystem.init();
                    statsSystem.init();
                } catch (error) {
                    console.error('Initialization error:', error);
                    utils.showNotification('Failed to initialize application', 'error');
                }
            
                // Handle page visibility changes
                document.addEventListener('visibilitychange', () => {
                    if (document.visibilityState === 'visible') {
                        progressSystem.animateProgressBars();
                        statsSystem.animateStats();
                    }
                });
            
                // Export systems for potential external use
                window.projectHub = {
                    utils,
                    themeSystem,
                    sidebarSystem,
                    searchSystem,
                    progressSystem,
                    statsSystem
                };
            });