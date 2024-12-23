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
});