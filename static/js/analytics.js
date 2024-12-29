if (!window.projectHub) {
    window.projectHub = {
        utils: {
            showNotification: (message, type) => console.log(`${type}: ${message}`)
        }
    };
}

// Analytics System
const analyticsSystem = {
    // Store chart instances for updating
    charts: {},
    
    // Chart configuration defaults
    chartDefaults: {
        responsive: true,
        maintainAspectRatio: true,
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
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleFont: {
                    family: "'Inter', sans-serif",
                    size: 13
                },
                bodyFont: {
                    family: "'Inter', sans-serif",
                    size: 12
                },
                padding: 12,
                cornerRadius: 8
            }
        },
        animation: {
            duration: 1000,
            easing: 'easeOutQuart'
        }
    },

    init() {
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded');
            return;
        }
        
        this.initializeCharts();
        this.setupEventListeners();
        this.startAutoRefresh();
    },

    initializeCharts() {
        // Check for analytics data
        if (!window.analyticsData) {
            console.error('Analytics data not loaded');
            return;
        }

        try {
            // Project Progress Timeline
            this.charts.projectProgress = this.createProgressChart();
            this.charts.taskDistribution = this.createDistributionChart();
            this.charts.teamPerformance = this.createPerformanceChart();
            this.charts.completionTrend = this.createTrendChart();
        } catch (error) {
            console.error('Chart initialization error:', error);
            window.projectHub.utils.showNotification('Failed to initialize charts', 'error');
        }
    },

    createProgressChart() {
        return new Chart(
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
                    ...this.chartDefaults,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                display: true,
                                drawBorder: false,
                                color: 'rgba(0, 0, 0, 0.05)'
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
    },

    createDistributionChart() {
        return new Chart(
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
                    ...this.chartDefaults,
                    cutout: '75%',
                    plugins: {
                        ...this.chartDefaults.plugins,
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            }
        );
    },

    createPerformanceChart() {
        return new Chart(
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
                    ...this.chartDefaults,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                drawBorder: false,
                                color: 'rgba(0, 0, 0, 0.05)'
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
    },

    createTrendChart() {
        return new Chart(
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
                    ...this.chartDefaults,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: value => `${value}%`
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
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
    },

    setupEventListeners() {
        // Time Range Selector
        const timeRange = document.getElementById('timeRange');
        timeRange?.addEventListener('change', (e) => this.updateChartData(e.target.value));

        // Export Button
        const exportBtn = document.querySelector('[data-export]');
        exportBtn?.addEventListener('click', () => this.exportAnalytics());

        // Handle visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.refreshCharts();
            }
        });
    },

    async updateChartData(timeRange) {
        const container = document.getElementById('analyticsCharts');
        try {
            container?.classList.add('loading');
            
            const response = await fetch(`/api/analytics/data/?range=${timeRange}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });
    
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Failed to fetch analytics data');
            }
    
            window.analyticsData = data;
            Object.keys(this.charts).forEach(chartKey => {
                this.updateChart(chartKey, data);
            });
    
            window.projectHub.utils.showNotification('Analytics updated successfully', 'success');
        } catch (error) {
            console.error('Chart update error:', error);
            window.projectHub.utils.showNotification(error.message, 'error');
        } finally {
            container?.classList.remove('loading');
        }
    },

    updateChart(chartKey, data) {
        try {
            const chart = this.charts[chartKey];
            if (!chart) return;

            switch (chartKey) {
                case 'projectProgress':
                    chart.data.labels = data.timelineLabels;
                    chart.data.datasets[0].data = data.completedTasksData;
                    break;
                case 'taskDistribution':
                    chart.data.datasets[0].data = data.taskDistribution;
                    break;
                case 'teamPerformance':
                    chart.data.labels = data.teamLabels;
                    chart.data.datasets[0].data = data.teamPerformance;
                    break;
                case 'completionTrend':
                    chart.data.labels = data.trendLabels;
                    chart.data.datasets[0].data = data.completionTrend;
                    break;
            }
            chart.update();
        } catch (error) {
            console.error(`Failed to update ${chartKey} chart:`, error);
            window.projectHub?.utils?.showNotification(`Failed to update ${chartKey} chart`, 'error');
        }
    },

    async refreshCharts() {
        const timeRange = document.getElementById('timeRange')?.value || '7';
        await this.updateChartData(timeRange);
    },

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => this.refreshCharts(), 300000);
    },

    destroy() {
        Object.values(this.charts).forEach(chart => chart.destroy());
        this.charts = {};
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    } 
}; 

// Initialize analytics system
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('analyticsCharts')) {
        try {
            analyticsSystem.init();
        } catch (error) {
            console.error('Analytics initialization error:', error);
            window.projectHub?.utils?.showNotification('Failed to initialize analytics', 'error');
        }
    }
});