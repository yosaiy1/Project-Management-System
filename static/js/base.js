// Layout Manager
class LayoutManager {
    constructor() {
      this.init();
      this.bindEvents();
    }
  
    init() {
      this.header = document.querySelector('.header');
      this.sidebar = document.querySelector('.sidebar');
      this.mainContent = document.querySelector('.main-content');
      this.sidebarToggle = document.querySelector('.sidebar-toggle');
      this.lastScrollPosition = 0;
      this.createOverlay();
    }
  
    createOverlay() {
      this.overlay = document.createElement('div');
      this.overlay.className = 'overlay';
      document.body.appendChild(this.overlay);
    }
  
    bindEvents() {
      // Sidebar toggle
      this.sidebarToggle?.addEventListener('click', () => this.toggleSidebar());
      this.overlay?.addEventListener('click', () => this.closeSidebar());
  
      // Scroll handling
      window.addEventListener('scroll', () => this.handleScroll());
      
      // Responsive handling
      window.addEventListener('resize', () => this.handleResize());
      
      // Initialize state
      this.handleResize();
    }
  
    toggleSidebar() {
      this.sidebar?.classList.toggle('show');
      this.overlay?.classList.toggle('active');
      document.body.style.overflow = this.sidebar?.classList.contains('show') ? 'hidden' : '';
    }
  
    closeSidebar() {
      this.sidebar?.classList.remove('show');
      this.overlay?.classList.remove('active');
      document.body.style.overflow = '';
    }
  
    handleScroll() {
      if (!this.header) return;
      
      const currentScroll = window.pageYOffset;
      
      if (currentScroll > this.lastScrollPosition && currentScroll > 100) {
        this.header.style.transform = 'translateY(-100%)';
      } else {
        this.header.style.transform = 'translateY(0)';
      }
      
      this.lastScrollPosition = currentScroll;
    }
  
    handleResize() {
      if (window.innerWidth > 1024) {
        this.closeSidebar();
      }
    }
  }
  
  // Initialize layout
  document.addEventListener('DOMContentLoaded', () => {
    new LayoutManager();
  });
  
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
  
    addClass(el, className) {
      if (el.classList) el.classList.add(className);
      else el.className += ' ' + className;
    },
  
    removeClass(el, className) {
      if (el.classList) el.classList.remove(className);
      else el.className = el.className.replace(new RegExp('(^|\\b)' + className.split(' ').join('|') + '(\\b|$)', 'gi'), ' ');
    }
  };