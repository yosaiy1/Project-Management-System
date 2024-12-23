document.addEventListener('DOMContentLoaded', function () {
  // Theme Management
  const themeToggle = document.getElementById('themeToggle');
  const currentTheme = localStorage.getItem('theme') || 'light';
  document.body.classList.add(`theme-${currentTheme}`);

  if (themeToggle) {
      themeToggle.addEventListener('click', () => {
          const newTheme = document.body.classList.contains('theme-light') ? 'dark' : 'light';
          document.body.classList.replace(`theme-${currentTheme}`, `theme-${newTheme}`);
          localStorage.setItem('theme', newTheme);
      });
  }

  // Sidebar Management
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.querySelector('.main-content');
  
  if (sidebarToggle && sidebar) {
      sidebarToggle.addEventListener('click', () => {
          sidebar.classList.toggle('collapsed');
          mainContent.classList.toggle('expanded');
          localStorage.setItem('sidebarState', sidebar.classList.contains('collapsed'));
      });

      // Close sidebar on outside click (mobile)
      document.addEventListener('click', (e) => {
          if (window.innerWidth < 768 && 
              !sidebar.contains(e.target) && 
              !sidebarToggle.contains(e.target)) {
              sidebar.classList.remove('show');
          }
      });
  }

  // Kanban Board Drag-and-Drop
  const lists = ['todo', 'inprogress', 'done'].map(id => document.getElementById(id));
  
  lists.forEach(list => {
      if (list) {
          new Sortable(list, {
              group: 'kanban',
              animation: 150,
              ghostClass: 'sortable-ghost',
              dragClass: 'sortable-drag',
              onStart: (evt) => evt.item.classList.add('dragging'),
              onEnd: (evt) => {
                  evt.item.classList.remove('dragging');
                  const taskId = evt.item.getAttribute('data-id');
                  const newStatus = evt.to.id;
                  updateTaskStatus(taskId, newStatus);
              }
          });
      }
  });

  // Task Status Update
  async function updateTaskStatus(taskId, newStatus) {
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
      }
  }

  // Notification System
  function showNotification(message, type = 'info') {
      const notification = document.createElement('div');
      notification.className = `notification notification-${type} fade-in`;
      notification.textContent = message;
      
      document.body.appendChild(notification);
      
      setTimeout(() => {
          notification.classList.replace('fade-in', 'fade-out');
          setTimeout(() => notification.remove(), 300);
      }, 3000);
  }

  // Search Functionality
  const searchInput = document.querySelector('.search-input');
  if (searchInput) {
      let debounceTimer;
      searchInput.addEventListener('input', (e) => {
          clearTimeout(debounceTimer);
          debounceTimer = setTimeout(() => {
              const searchTerm = e.target.value.trim();
              if (searchTerm.length > 2) {
                  performSearch(searchTerm);
              }
          }, 300);
      });
  }

  async function performSearch(term) {
      try {
          const response = await fetch(`/api/search?q=${encodeURIComponent(term)}`);
          if (!response.ok) throw new Error('Search failed');
          
          const results = await response.json();
          updateSearchResults(results);
      } catch (error) {
          console.error('Search error:', error);
          showNotification('Search failed', 'error');
      }
  }

  // Utility Functions
  function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
          const cookies = document.cookie.split(';');
          for (let i = 0; i < cookies.length; i++) {
              const cookie = cookies[i].trim();
              if (cookie.substring(0, name.length + 1) === (name + '=')) {
                  cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                  break;
              }
          }
      }
      return cookieValue;
  }
});