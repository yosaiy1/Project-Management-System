document.addEventListener('DOMContentLoaded', function () {
    const body = document.body;

    console.log('base.js loaded');

    // Kanban Board Drag-and-Drop
    const todoList = document.getElementById('todo');
    const inprogressList = document.getElementById('inprogress');
    const doneList = document.getElementById('done');

    if (todoList) {
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
    }

    if (inprogressList) {
        new Sortable(inprogressList, {
            group: 'kanban',
            animation: 150,
            onEnd: function (evt) {
                const taskId = evt.item.getAttribute('data-id');
                const newStatus = evt.to.id;
                updateTaskStatus(taskId, newStatus);
            }
        });
    }

    if (doneList) {
        new Sortable(doneList, {
            group: 'kanban',
            animation: 150,
            onEnd: function (evt) {
                const taskId = evt.item.getAttribute('data-id');
                const newStatus = evt.to.id;
                updateTaskStatus(taskId, newStatus);
            }
        });
    }

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
});