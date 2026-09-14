// Accountability Platform Frontend JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if needed
    // Initialize any page-specific functionality
    
    // Global AJAX setup
    const apiBase = '/api';
    
    // Chart.js configuration
    Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
    Chart.defaults.color = '#64748b';
    
    // Utility functions
    const utils = {
        showLoading: (element) => {
            element.innerHTML = '<div class="loading-skeleton" style="height: 100%; width: 100%;"></div>';
        },
        
        showError: (element, message) => {
            element.innerHTML = `<div class="alert alert-error">${message}</div>`;
        },
        
        formatNumber: (num) => {
            if (num >= 1000000) {
                return (num / 1000000).toFixed(1) + 'M';
            } else if (num >= 1000) {
                return (num / 1000).toFixed(1) + 'K';
            }
            return num;
        }
    };
    
    // AI Data Fetching and Rendering
    const aiService = {
        // Fetch AI data and render both text panel and chart
        fetchAndRender: async (endpoint, textPanelSelector, chartSelector, chartType, chartDataFn) => {
            const textPanel = document.querySelector(textPanelSelector);
            const chartContainer = document.querySelector(chartSelector);
            
            if (!textPanel || !chartContainer) return;
            
            // Show loading states
            textPanel.innerHTML = '<div class="loading-skeleton" style="height: 60px;"></div>';
            utils.showLoading(chartContainer);
            
            try {
                const response = await fetch(`${apiBase}${endpoint}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                
                if (!data.success) {
                    throw new Error('API returned unsuccessful response');
                }
                
                // Render text panel
                textPanel.innerHTML = aiService.renderTextPanel(data.data);
                
                // Render chart
                const chartData = chartDataFn(data.data);
                if (chartData) {
                    aiService.renderChart(chartContainer, chartType, chartData);
                } else {
                    chartContainer.innerHTML = '<p>No chart data available</p>';
                }
                
            } catch (error) {
                console.error('Error fetching AI data:', error);
                textPanel.innerHTML = '<p>Error loading analysis. Please try again later.</p>';
                chartContainer.innerHTML = '<p>Error loading chart. Please try again later.</p>';
            }
        },
        
        renderTextPanel: (data) => {
            // This should be overridden by specific implementations
            // For now, just show JSON as fallback
            return `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        },
        
        renderChart: (container, type, data) => {
            // Clear container
            container.innerHTML = '<canvas></canvas>';
            const ctx = container.querySelector('canvas').getContext('2d');
            
            // Destroy existing chart if any
            if container.chart instanceof Chart {
                container.chart.destroy();
            }
            
            // Create new chart
            container.chart = new Chart(ctx, {
                type: type,
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                        }
                    }
                }
            });
        }
    };
    
    // Make utils and aiService available globally
    window.utils = utils;
    window.aiService = aiService;
    
    // Initialize any page-specific scripts
    if (typeof initPage === 'function') {
        initPage();
    }
});

// Chart type specific rendering functions
function renderGaugeChart(data, options = {}) {
    return {
        labels: ['Value'],
        datasets: [{
            data: [data.value, 100 - data.value],
            backgroundColor: [
                data.color || '#10b981',
                '#e2e8f0'
            ],
            borderWidth: 0
        }]
    };
}

function renderBarChart(data, options = {}) {
    return {
        labels: data.labels || [],
        datasets: [{
            label: data.label || '',
            data: data.values || [],
            backgroundColor: data.color || '#6366f1',
            borderColor: data.color || '#6366f1',
            borderWidth: 1
        }]
    };
}

function renderHorizontalBarChart(data, options = {}) {
    return {
        labels: data.labels || [],
        datasets: [{
            label: data.label || '',
            data: data.values || [],
            backgroundColor: data.backgroundColor || '#6366f1',
            borderColor: data.borderColor || '#6366f1',
            borderWidth: 1
        }]
    };
}

function renderLineChart(data, options = {}) {
    return {
        labels: data.labels || [],
        datasets: [{
            label: data.label || '',
            data: data.values || [],
            fill: false,
            borderColor: data.color || '#6366f1',
            tension: 0.1
        }]
    };
}

function renderStackedBarChart(data, options = {}) {
    return {
        labels: data.labels || [],
        datasets: data.datasets || []
    };
}

function renderRadarChart(data, options = {}) {
    return {
        labels: data.labels || [],
        datasets: [{
            label: data.label || '',
            data: data.values || [],
            fill: true,
            backgroundColor: data.backgroundColor || 'rgba(99, 102, 241, 0.2)',
            borderColor: data.borderColor || '#6366f1',
            pointBackgroundColor: data.borderColor || '#6366f1',
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: data.borderColor || '#6366f1'
        }]
    };
}

function renderDoughnutChart(data, options = {}) {
    return {
        labels: data.labels || [],
        datasets: [{
            data: data.values || [],
            backgroundColor: data.backgroundColor || ['#10b981', '#f59e0b', '#ef4444'],
            hoverOffset: 4
        }]
    };
}

// Page-specific initialization functions will be defined in each page's script
