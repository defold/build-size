// Defold Component Size Dashboard

class DefoldDashboard {
    constructor() {
        this.csvCache = new Map();
        this.charts = new Map();
        this.chartConfigs = new Map(); // Store chart configurations
        this.platformColors = {
            'arm64-ios': '#e74c3c',
            'arm64-android': '#3498db',
            'armv7-android': '#9b59b6',
            'x86_64-macos': '#2ecc71',
            'js-web': '#f39c12',
            'wasm-web': '#e67e22',
            'x86_64-linux': '#34495e',
            'x86-win32': '#16a085',
            'x86_64-win32': '#27ae60',
            'arm64-macos': '#8e44ad'
        };
        
        this.init();
        
        // Add window resize listener to handle responsive layout changes
        window.addEventListener('resize', () => {
            this.handleResize();
        });
    }
    
    async init() {
        try {
            // Load all CSV files
            await this.loadAllData();
            
            // Create all charts
            this.createBundleChart();
            this.createEngineChart();
            this.createEditorChart();
            this.createBobChart();
            
            // Setup version dropdowns and event listeners
            this.setupVersionDropdowns();
            
            console.log('Dashboard loaded successfully');
            
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            this.showError('Failed to load dashboard data');
        }
    }
    
    async loadAllData() {
        const files = ['bundle_report.csv', 'engine_report.csv', 'editor_report.csv', 'bob_report.csv'];
        
        for (const file of files) {
            await this.loadCSV(file);
        }
    }
    
    async loadCSV(filename) {
        if (this.csvCache.has(filename)) {
            return this.csvCache.get(filename);
        }
        
        try {
            const response = await fetch(filename);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const text = await response.text();
            const data = this.parseCSV(text);
            
            // Filter out rows with all zeros
            const filteredData = data.filter(row => {
                const values = Object.values(row);
                return values.some(value => value !== 'VERSION' && parseFloat(value) > 0);
            });
            
            this.csvCache.set(filename, filteredData);
            return filteredData;
            
        } catch (error) {
            console.error(`Error loading ${filename}:`, error);
            throw error;
        }
    }
    
    parseCSV(text) {
        const lines = text.trim().split('\n');
        const headers = lines[0].split(',').map(h => h.trim());
        const data = [];
        
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim());
            if (values.length === headers.length) {
                const row = {};
                headers.forEach((header, index) => {
                    row[header] = values[index];
                });
                data.push(row);
            }
        }
        
        return data;
    }
    
    compareVersions(v1, v2) {
        const a = v1.split('.').map(Number);
        const b = v2.split('.').map(Number);
        
        for (let i = 0; i < Math.max(a.length, b.length); i++) {
            const numA = a[i] || 0;
            const numB = b[i] || 0;
            if (numA !== numB) {
                return numA - numB;
            }
        }
        return 0;
    }
    
    filterDataFromVersion(data, startVersion) {
        return data.filter(row => {
            const version = row.VERSION;
            return this.compareVersions(version, startVersion) >= 0;
        });
    }
    
    calculateDefaultVersion(csvFile, minimumVersion) {
        const rawData = this.csvCache.get(csvFile);
        if (!rawData) return minimumVersion;
        
        // Get all versions with data (non-zero values)
        const versions = rawData
            .filter(row => {
                const values = Object.values(row);
                return values.some(value => value !== 'VERSION' && parseFloat(value) > 0);
            })
            .map(row => row.VERSION);
        
        // Sort versions
        versions.sort(this.compareVersions.bind(this));
        
        // Filter to only include versions >= minimum allowed
        const validVersions = versions.filter(version => 
            this.compareVersions(version, minimumVersion) >= 0
        );
        
        // If we have more than 20 versions, start from the 20th from the end
        if (validVersions.length > 20) {
            const startIndex = validVersions.length - 20;
            return validVersions[startIndex];
        }
        
        // If we have 20 or fewer versions, start from the minimum
        return minimumVersion;
    }
    
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
        
        return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
    }
    
    createBundleChart() {
        const rawData = this.csvCache.get('bundle_report.csv');
        const platforms = ['arm64-ios', 'arm64-android', 'armv7-android', 'x86_64-macos', 'js-web', 'wasm-web', 'x86_64-linux', 'x86-win32', 'x86_64-win32', 'arm64-macos'];
        
        // Calculate default version (last 20 versions)
        const defaultVersion = this.calculateDefaultVersion('bundle_report.csv', '1.2.166');
        
        // Store chart config
        this.chartConfigs.set('bundle-chart', {
            csvFile: 'bundle_report.csv',
            platforms: platforms,
            title: 'Bundle Size Evolution',
            defaultVersion: defaultVersion,
            selectId: 'bundle-version-select'
        });
        
        const data = this.filterDataFromVersion(rawData, defaultVersion);
        this.createChart('bundle-chart', data, platforms, 'Bundle Size Evolution');
    }
    
    createEngineChart() {
        const rawData = this.csvCache.get('engine_report.csv');
        const platforms = ['arm64-ios', 'arm64-android', 'armv7-android', 'x86_64-macos', 'js-web', 'wasm-web', 'x86_64-linux', 'x86-win32', 'x86_64-win32', 'arm64-macos'];
        
        // Calculate default version (last 20 versions)
        const defaultVersion = this.calculateDefaultVersion('engine_report.csv', '1.2.166');
        
        // Store chart config
        this.chartConfigs.set('engine-chart', {
            csvFile: 'engine_report.csv',
            platforms: platforms,
            title: 'Engine Size Evolution',
            defaultVersion: defaultVersion,
            selectId: 'engine-version-select'
        });
        
        const data = this.filterDataFromVersion(rawData, defaultVersion);
        this.createChart('engine-chart', data, platforms, 'Engine Size Evolution');
    }
    
    createEditorChart() {
        const rawData = this.csvCache.get('editor_report.csv');
        const platforms = ['x86_64-macos', 'x86_64-win32', 'x86_64-linux', 'arm64-macos'];
        
        // Calculate default version (last 20 versions)
        const defaultVersion = this.calculateDefaultVersion('editor_report.csv', '1.3.6');
        
        // Store chart config
        this.chartConfigs.set('editor-chart', {
            csvFile: 'editor_report.csv',
            platforms: platforms,
            title: 'Editor Size Evolution',
            defaultVersion: defaultVersion,
            selectId: 'editor-version-select'
        });
        
        const data = this.filterDataFromVersion(rawData, defaultVersion);
        this.createChart('editor-chart', data, platforms, 'Editor Size Evolution');
    }
    
    createBobChart() {
        const rawData = this.csvCache.get('bob_report.csv');
        const platforms = ['x86_64-macos'];
        
        // Calculate default version (last 20 versions)
        const defaultVersion = this.calculateDefaultVersion('bob_report.csv', '1.2.166');
        
        // Store chart config
        this.chartConfigs.set('bob-chart', {
            csvFile: 'bob_report.csv',
            platforms: platforms,
            title: 'Bob.jar Size Evolution',
            defaultVersion: defaultVersion,
            selectId: 'bob-version-select'
        });
        
        const data = this.filterDataFromVersion(rawData, defaultVersion);
        this.createChart('bob-chart', data, platforms, 'Bob.jar Size Evolution', false); // No legend for Bob chart
    }
    
    createChart(containerId, data, platforms, title, showLegend = true) {
        const container = document.getElementById(containerId);
        
        if (!data || data.length === 0) {
            container.innerHTML = '<div class="error">No data available</div>';
            return;
        }
        
        // Show loading state
        container.innerHTML = '<div class="loading">Loading chart...</div>';
        
        const traces = [];
        const versions = data.map(row => row.VERSION);
        
        platforms.forEach(platform => {
            const sizes = data.map(row => {
                const size = parseFloat(row[platform]) || 0;
                return size;
            });
            
            // Only include platforms that have some data
            const hasData = sizes.some(size => size > 0);
            if (!hasData) return;
            
            traces.push({
                x: versions,
                y: sizes,
                type: 'scatter',
                mode: 'lines+markers',
                name: this.formatPlatformName(platform),
                line: {
                    color: this.platformColors[platform] || '#666',
                    width: 2
                },
                marker: {
                    size: 4,
                    color: this.platformColors[platform] || '#666'
                },
                hovertemplate: `<b>%{fullData.name}</b><br>Version: %{x}<br>Size: %{text}<br>Bytes: %{y:,.0f}<extra></extra>`,
                text: sizes.map(size => this.formatBytes(size)),
                hoverlabel: {
                    bgcolor: '#FFFFDD',
                    bordercolor: '#333',
                    font: { color: '#000', size: 12 }
                }
            });
        });
        
        // Check if we're on mobile/tablet (768px or less)
        const isMobile = window.innerWidth <= 768;
        
        const layout = {
            title: {
                text: title,
                font: { size: 16, color: '#2c3e50' },
                y: isMobile ? 0.92 : 0.95,
                yanchor: 'top'
            },
            xaxis: {
                title: 'Version',
                tickangle: -45,
                gridcolor: '#f0f0f0'
            },
            yaxis: {
                title: 'Size',
                tickformat: '.2s',
                gridcolor: '#f0f0f0'
            },
            margin: { 
                l: 80, 
                r: 50, 
                t: isMobile ? 100 : 60, 
                b: showLegend ? 100 : 60 
            },
            paper_bgcolor: 'white',
            plot_bgcolor: 'white',
            showlegend: showLegend,
            legend: showLegend ? {
                orientation: 'h',
                x: 0,
                y: -0.25,
                xanchor: 'left',
                bgcolor: 'rgba(255,255,255,0.8)',
                bordercolor: '#ddd',
                borderwidth: 1,
                font: { size: 12 }
            } : {},
            hovermode: 'closest'
        };
        
        const config = {
            displayModeBar: true,
            modeBarButtonsToRemove: ['select2d', 'lasso2d'],
            displaylogo: false,
            responsive: true
        };
        
        // Clear loading spinner before creating chart
        container.innerHTML = '';
        
        Plotly.newPlot(containerId, traces, layout, config);
        this.charts.set(containerId, { traces, layout, config, platforms });
        
        // Add click handler to open size-analyzer with selected version
        document.getElementById(containerId).on('plotly_click', (data) => {
            this.handleChartClick(data, platforms, containerId);
        });
        
        // Add legend click handler for Alt+click to show only selected platform
        if (showLegend) {
            document.getElementById(containerId).on('plotly_legendclick', (data) => {
                return this.handleLegendClick(data, containerId);
            });
            
            // Add legend usage info
            this.addLegendInfo(containerId);
        }
    }
    
    addLegendInfo(containerId) {
        const container = document.getElementById(containerId);
        const chartContainer = container.closest('.chart-section');
        
        if (chartContainer) {
            // Check if info already exists
            const existingInfo = chartContainer.querySelector('.legend-info');
            if (!existingInfo) {
                const infoDiv = document.createElement('div');
                infoDiv.className = 'legend-info';
                infoDiv.style.cssText = `
                    font-style: italic; 
                    font-size: 9px; 
                    color: #999; 
                    text-align: right;
                    margin-top: 2px;
                    line-height: 1;
                `;
                infoDiv.textContent = 'Legend: click to toggle, Alt+click to isolate';
                
                // Add after the chart container
                const chartDiv = chartContainer.querySelector('.chart-container');
                if (chartDiv) {
                    chartDiv.insertAdjacentElement('afterend', infoDiv);
                } else {
                    container.insertAdjacentElement('afterend', infoDiv);
                }
            }
        }
    }
    
    handleChartClick(data, platforms, containerId) {
        if (data.points && data.points.length > 0) {
            const point = data.points[0];
            const clickedVersion = point.x; // Version from X-axis
            const platformName = point.fullData.name; // Platform name from trace
            
            // Find the actual platform key from the formatted name
            let platformKey = this.findPlatformKey(platformName, platforms);
            
            // Special case: if this is the Bob chart, use 'bob.jar' as platform
            if (containerId === 'bob-chart') {
                platformKey = 'bob.jar';
            }
            
            // Special case: if this is the Editor chart, map to editor platform names
            if (containerId === 'editor-chart') {
                const editorPlatformMap = {
                    'x86_64-win32': 'editor-win32',
                    'x86_64-linux': 'editor-x86_64-linux',
                    'x86_64-macos': 'editor-x86_64-macos',
                    'arm64-macos': 'editor-arm64-macos'
                };
                platformKey = editorPlatformMap[platformKey] || platformKey;
            }
            
            if (platformKey && clickedVersion) {
                // Get all available versions for this platform to find the previous version
                const allVersions = this.getAllVersionsForPlatform(platformKey, containerId);
                const versionIndex = allVersions.indexOf(clickedVersion);
                
                if (versionIndex > 0) {
                    const fromVersion = allVersions[versionIndex - 1];
                    const toVersion = clickedVersion;
                    
                    // Open size-analyzer with URL parameters
                    const url = `size-analyzer/?platform=${platformKey}&from=${fromVersion}&to=${toVersion}`;
                    window.open(url, '_blank');
                } else {
                    alert('Cannot compare: This is the first version in the dataset.');
                }
            }
        }
    }
    
    handleLegendClick(data, containerId) {
        // Check if Alt key is pressed
        if (data.event && data.event.altKey) {
            // Alt+click: show only the clicked trace, hide all others
            const clickedTraceIndex = data.curveNumber;
            const currentChart = this.charts.get(containerId);
            
            if (currentChart) {
                const update = {
                    visible: currentChart.traces.map((trace, index) => 
                        index === clickedTraceIndex ? true : 'legendonly'
                    )
                };
                
                Plotly.restyle(containerId, update);
            }
            
            // Return false to prevent default legend click behavior
            return false;
        }
        
        // Return true to allow default legend click behavior (normal toggle)
        return true;
    }
    
    findPlatformKey(platformName, platforms) {
        // Convert formatted platform name back to platform key
        const reverseNameMap = {
            'ARM64 iOS': 'arm64-ios',
            'ARM64 Android': 'arm64-android',
            'ARMv7 Android': 'armv7-android',
            'x86_64 macOS': 'x86_64-macos',
            'JS Web': 'js-web',
            'WASM Web': 'wasm-web',
            'x86_64 Linux': 'x86_64-linux',
            'x86 Win32': 'x86-win32',
            'x86_64 Win32': 'x86_64-win32',
            'ARM64 macOS': 'arm64-macos'
        };
        
        return reverseNameMap[platformName] || platforms.find(p => 
            this.formatPlatformName(p) === platformName
        );
    }
    
    getAllVersionsForPlatform(platformKey, containerId = null) {
        // Get all available versions from the raw CSV data
        let csvFile;
        
        // Special case: if this is the Bob chart or platform is bob.jar, use bob_report.csv
        if (containerId === 'bob-chart' || platformKey === 'bob.jar') {
            csvFile = 'bob_report.csv';
        } else {
            csvFile = this.getCsvFileForPlatform(platformKey);
        }
        
        const rawData = this.csvCache.get(csvFile);
        
        if (rawData) {
            return rawData.map(row => row.VERSION).filter(v => v);
        }
        
        return [];
    }
    
    getCsvFileForPlatform(platformKey) {
        // Map platform to CSV file based on chart context
        // For desktop platforms, prefer editor_report.csv, except for bob chart
        if (['x86_64-macos', 'x86_64-win32', 'x86_64-linux', 'arm64-macos'].includes(platformKey)) {
            return 'editor_report.csv';
        } else {
            // For mobile/web platforms, use bundle_report.csv (or engine_report.csv as fallback)
            return this.csvCache.has('bundle_report.csv') ? 'bundle_report.csv' : 'engine_report.csv';
        }
    }
    
    formatPlatformName(platform) {
        const names = {
            'arm64-ios': 'ARM64 iOS',
            'arm64-android': 'ARM64 Android',
            'armv7-android': 'ARMv7 Android',
            'x86_64-macos': 'x86_64 macOS',
            'js-web': 'JS Web',
            'wasm-web': 'WASM Web',
            'x86_64-linux': 'x86_64 Linux',
            'x86-win32': 'x86 Win32',
            'x86_64-win32': 'x86_64 Win32',
            'arm64-macos': 'ARM64 macOS'
        };
        return names[platform] || platform;
    }
    
    setupVersionDropdowns() {
        // Setup dropdowns for each chart
        this.chartConfigs.forEach((config, chartId) => {
            this.populateVersionDropdown(config.selectId, config.csvFile, config.defaultVersion);
            
            // Add event listener for version changes
            const select = document.getElementById(config.selectId);
            select.addEventListener('change', () => {
                this.onVersionChange(chartId, select.value);
            });
        });
    }
    
    populateVersionDropdown(selectId, csvFile, defaultVersion) {
        const select = document.getElementById(selectId);
        const rawData = this.csvCache.get(csvFile);
        
        if (!rawData) return;
        
        // Define minimum allowed versions for each chart type
        const minimumVersions = {
            'bundle_report.csv': '1.2.166',
            'engine_report.csv': '1.2.166',
            'editor_report.csv': '1.3.6',
            'bob_report.csv': '1.2.166'
        };
        
        const minimumVersion = minimumVersions[csvFile];
        
        // Get all versions with data (non-zero values)
        const versions = rawData
            .filter(row => {
                const values = Object.values(row);
                return values.some(value => value !== 'VERSION' && parseFloat(value) > 0);
            })
            .map(row => row.VERSION);
        
        // Sort versions
        versions.sort(this.compareVersions.bind(this));
        
        // Filter versions to only include those >= minimum allowed version
        const validVersions = versions.filter(version => 
            this.compareVersions(version, minimumVersion) >= 0
        );
        
        // Get maximum versions for selection range (last available - 3)
        const maxVersionIndex = Math.max(0, validVersions.length - 4);
        const selectableVersions = validVersions.slice(0, maxVersionIndex + 1);
        
        // Clear and populate dropdown
        select.innerHTML = '';
        
        selectableVersions.forEach(version => {
            const option = document.createElement('option');
            option.value = version;
            option.textContent = version;
            if (version === defaultVersion) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }
    
    onVersionChange(chartId, selectedVersion) {
        if (!selectedVersion) return;
        
        const config = this.chartConfigs.get(chartId);
        if (!config) return;
        
        const rawData = this.csvCache.get(config.csvFile);
        const filteredData = this.filterDataFromVersion(rawData, selectedVersion);
        
        // Update the chart
        this.updateChartWithData(chartId, filteredData, config.platforms, config.title);
    }
    
    updateChartWithData(chartId, data, platforms, title) {
        const container = document.getElementById(chartId);
        const chartData = this.charts.get(chartId);
        
        if (!data || !chartData) return;
        
        const traces = [];
        const versions = data.map(row => row.VERSION);
        
        platforms.forEach(platform => {
            const sizes = data.map(row => {
                const size = parseFloat(row[platform]) || 0;
                return size;
            });
            
            // Only include platforms that have some data
            const hasData = sizes.some(size => size > 0);
            if (!hasData) return;
            
            traces.push({
                x: versions,
                y: sizes,
                type: 'scatter',
                mode: 'lines+markers',
                name: this.formatPlatformName(platform),
                line: {
                    color: this.platformColors[platform] || '#666',
                    width: 2
                },
                marker: {
                    size: 4,
                    color: this.platformColors[platform] || '#666'
                },
                hovertemplate: `<b>%{fullData.name}</b><br>Version: %{x}<br>Size: %{text}<br>Bytes: %{y:,.0f}<extra></extra>`,
                text: sizes.map(size => this.formatBytes(size)),
                hoverlabel: {
                    bgcolor: '#FFFFDD',
                    bordercolor: '#333',
                    font: { color: '#000', size: 12 }
                }
            });
        });
        
        Plotly.react(chartId, traces, chartData.layout, chartData.config);
    }
    
    handleResize() {
        // Debounce resize events
        clearTimeout(this.resizeTimeout);
        this.resizeTimeout = setTimeout(() => {
            // Update all charts with responsive layout
            this.chartConfigs.forEach((config, chartId) => {
                const chartData = this.charts.get(chartId);
                if (chartData) {
                    const isMobile = window.innerWidth <= 768;
                    const updatedLayout = {
                        ...chartData.layout,
                        title: {
                            ...chartData.layout.title,
                            y: isMobile ? 0.92 : 0.95
                        },
                        margin: {
                            ...chartData.layout.margin,
                            t: isMobile ? 100 : 60
                        }
                    };
                    
                    Plotly.relayout(chartId, updatedLayout);
                    this.charts.set(chartId, { ...chartData, layout: updatedLayout });
                }
            });
        }, 250); // 250ms debounce
    }
    
    showError(message) {
        const sections = document.querySelectorAll('.chart-section .chart-container');
        sections.forEach(section => {
            section.innerHTML = `<div class="error">${message}</div>`;
        });
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.defoldDashboard = new DefoldDashboard();
});