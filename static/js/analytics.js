document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    setupEventListeners();
});

function initializeCharts() {
    // Check if data exists first
    if (!window.analyticsData) {
        console.error('Analytics data not loaded');
        return;
    }

    // Chart Configuration
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    padding: 20,
                    font: {
                        family: "'Inter', sans-serif",
                        size: 12
                    }
                }
            }
        }
    };

    // Project Progress Timeline
    const projectProgress = new Chart(
        document.getElementById('projectProgress').getContext('2d'),
        {
            type: 'line',
            data: {
                labels: window.analyticsData.timelineLabels,
                datasets: [{
                    label: 'Completed Tasks',
                    data: window.analyticsData.completedTasksData,
                    borderColor: '#4f46e5',
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                ...chartOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            display: true,
                            drawBorder: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        }
    );

    // Task Distribution
    const taskDistribution = new Chart(
        document.getElementById('taskDistribution').getContext('2d'),
        {
            type: 'doughnut',
            data: {
                labels: ['To Do', 'In Progress', 'Completed'],
                datasets: [{
                    data: window.analyticsData.taskDistribution,
                    backgroundColor: [
                        '#ef4444',
                        '#6366f1',
                        '#34d399'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                ...chartOptions,
                cutout: '75%'
            }
        }
    );

    // Team Performance
    const teamPerformance = new Chart(
        document.getElementById('teamPerformance').getContext('2d'),
        {
            type: 'bar',
            data: {
                labels: window.analyticsData.teamLabels,
                datasets: [{
                    label: 'Tasks Completed',
                    data: window.analyticsData.teamPerformance,
                    backgroundColor: '#818cf8',
                    borderRadius: 8
                }]
            },
            options: {
                ...chartOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            drawBorder: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        }
    );

    // Completion Trend
    const completionTrend = new Chart(
        document.getElementById('completionTrend').getContext('2d'),
        {
            type: 'line',
            data: {
                labels: window.analyticsData.trendLabels,
                datasets: [{
                    label: 'Completion Rate',
                    data: window.analyticsData.completionTrend,
                    borderColor: '#c084fc',
                    backgroundColor: 'rgba(192, 132, 252, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                ...chartOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        }
    );
}

function setupEventListeners() {
    // Time Range Selector
    document.getElementById('timeRange').addEventListener('change', function(e) {
        updateChartData(e.target.value);
    });
}

function updateChartData(timeRange) {
    fetch(`/api/analytics/data?range=${timeRange}`)
        .then(response => response.json())
        .then(data => {
            // Update charts with new data
            window.analyticsData = data;
            initializeCharts();
        })
        .catch(error => {
            console.error('Error fetching analytics data:', error);
        });
}

function exportAnalytics() {
    const timeRange = document.getElementById('timeRange').value;
    window.location.href = `/export-report/?range=${timeRange}`;
}