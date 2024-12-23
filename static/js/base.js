document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const toggleButton = document.querySelector('.navbar-toggler');
    const mainContent = document.querySelector('main');
    const body = document.body;

    function toggleSidebar() {
        sidebar.classList.toggle('d-none');
        mainContent.classList.toggle('full-width');
        body.classList.toggle('sidebar-hidden');
    }

    toggleButton.addEventListener('click', function () {
        toggleSidebar();
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth >= 992) {
            sidebar.classList.remove('d-none');
            mainContent.classList.remove('full-width');
            body.classList.remove('sidebar-hidden');
        } else {
            sidebar.classList.add('d-none');
            mainContent.classList.add('full-width');
            body.classList.add('sidebar-hidden');
        }
    });

    // Initial check
    if (window.innerWidth < 992) {
        sidebar.classList.add('d-none');
        mainContent.classList.add('full-width');
        body.classList.add('sidebar-hidden');
    } else {
        sidebar.classList.remove('d-none');
        mainContent.classList.remove('full-width');
        body.classList.remove('sidebar-hidden');
    }

    console.log('Sidebar functionality initialized');

    // Kanban Board Drag-and-Drop
    const todoList = document.getElementById('todo');
    const inprogressList = document.getElementById('inprogress');
    const doneList = document.getElementById('done');

    new Sortable(todoList, {
        group: 'kanban',
        animation: 150,
        onEnd: function (evt) {
            // Handle task movement
            const taskId = evt.item.getAttribute('data-id');
            const newStatus = evt.to.id;
            updateTaskStatus(taskId, newStatus);
        }
    });

    new Sortable(inprogressList, {
        group: 'kanban',
        animation: 150,
        onEnd: function (evt) {
            const taskId = evt.item.getAttribute('data-id');
            const newStatus = evt.to.id;
            updateTaskStatus(taskId, newStatus);
        }
    });

    new Sortable(doneList, {
        group: 'kanban',
        animation: 150,
        onEnd: function (evt) {
            const taskId = evt.item.getAttribute('data-id');
            const newStatus = evt.to.id;
            updateTaskStatus(taskId, newStatus);
        }
    });

    function updateTaskStatus(taskId, newStatus) {
        console.log(`Updating task ${taskId} to status ${newStatus}`); // Add logging for debugging
        // Send an AJAX request to update the task status
        fetch(`/projects/update_task_status/${taskId}/`, {  // Note the /projects/ prefix
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ status: newStatus })
        }).then(response => {
            if (!response.ok) {
                console.error('Failed to update task status');
            } else {
                console.log('Task status updated successfully'); // Add logging for success
            }
        }).catch(error => {
            console.error('Error:', error);
        });
    }
    
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
    
    console.log('base.js loaded');
});