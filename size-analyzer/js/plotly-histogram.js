// Plotly-based Horizontal Bar Histogram Implementation

class PlotlyHistogramChart {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        
        // Color scheme
        this.colors = {
            version1: '#2E86AB',      // Blue for Version 1
            version2: '#F24236',      // Red/Orange for Version 2
            unchanged: '#95a5a6',
            decreasedFilesize: '#27ae60',    // Dark green for filesize decreased
            decreasedVmsize: '#52c281',      // Light green for vmsize decreased
            increasedFilesize: '#e74c3c',    // Dark red for filesize increased
            increasedVmsize: '#ff6b6b'       // Light red for vmsize increased
        };
        
        this.init();
    }
    
    init() {
        // Clear any existing content
        this.container.innerHTML = '';
        
        // Set up container dimensions
        this.updateDimensions();
        
        // Set up resize handler
        window.addEventListener('resize', () => this.handleResize());
    }
    
    updateDimensions() {
        const container = this.container.parentElement;
        this.width = container.clientWidth;
        this.height = 600;
    }
    
    handleResize() {
        this.updateDimensions();
        
        // Handle responsive layout updates
        if (this.currentData && document.getElementById(this.containerId).data) {
            const isMobile = window.innerWidth <= 768;
            const updatedLayout = {
                width: this.width,
                margin: {
                    l: 240,
                    r: 50,
                    t: 30,
                    b: 50
                }
            };
            
            Plotly.relayout(this.containerId, updatedLayout);
        } else if (this.currentData) {
            // Full re-render if no existing chart
            this.render(this.currentData, this.threshold, this.metricType);
        }
    }
    
    render(data, threshold = 50, metricType = 'filesize') {
        this.currentData = data;
        this.threshold = threshold;
        this.metricType = metricType;
        
        if (!data || data.length === 0) {
            this.showMessage(`No data to display for ${metricType}`);
            return;
        }
        
        // Prepare data for Plotly horizontal bar chart
        const chartData = this.prepareHistogramData(data, threshold, metricType);
        
        // Store chart data for hover functionality
        this.chartData = chartData;
        
        // Create Plotly horizontal bar chart
        this.createPlotlyHistogram(chartData, threshold, metricType);
    }
    
    prepareHistogramData(comparisons, threshold = 50, metricType = 'filesize') {
        // Simple processing - filter by threshold and sort by change magnitude
        const processedComparisons = comparisons
            .filter(comp => {
                const size1 = comp.size1 || 0;
                const size2 = comp.size2 || 0;
                const change = Math.abs(size2 - size1);
                return change >= threshold;
            })
            .map(comp => {
                const size1 = comp.size1 || 0;
                const size2 = comp.size2 || 0;
                const change = size2 - size1;
                
                return {
                    ...comp,
                    change: change,
                    metricType: metricType
                };
            })
            .sort((a, b) => {
                // Sort by absolute value of change (largest changes first)
                return Math.abs(b.change) - Math.abs(a.change);
            });
        
        // Prepare data for the chart
        const fileNames = [];
        const fullFileNames = []; // Store full filenames for timeline lookup
        const barValues = [];
        const hoverTexts = [];
        const barColors = [];
        let increasedCount = 0;
        let decreasedCount = 0;
        
        // Process all changed files in sorted order
        processedComparisons.forEach(comp => {
            const fullFileName = comp.compileUnit;
            let fileName = this.truncateFileName(fullFileName);
            
            // Add move indicator to displayed file name if applicable
            if (comp.isMoved) {
                fileName = '📁 ' + fileName;
            }
            
            const size1 = comp.size1 || 0;
            const size2 = comp.size2 || 0;
            const change = comp.change;
            const percentChange = size1 > 0 ? ((change / size1) * 100) : 0;
            
            fileNames.push(fileName);
            fullFileNames.push(fullFileName); // Store full filename
            barValues.push(change);
            
            // Use simple color scheme based on direction
            // Create hover text with move information if applicable
            let hoverText = `${fullFileName}<br>Metric: ${metricType.toUpperCase()}<br>`;
            
            if (comp.isMoved) {
                hoverText += `📁 MOVED: ${comp.moveInfo.oldPath} → ${comp.moveInfo.newPath}<br>`;
            }
            
            if (change > 0) {
                hoverText += `Became larger: ${this.formatBytes(change)}<br>From: ${this.formatBytes(size1)} → ${this.formatBytes(size2)}<br>Change: +${this.formatBytes(change)} (+${percentChange.toFixed(1)}%)`;
                hoverTexts.push(hoverText);
                barColors.push(this.getIncreaseColor(metricType));
                increasedCount++;
            } else {
                hoverText += `Became smaller: ${this.formatBytes(Math.abs(change))}<br>From: ${this.formatBytes(size1)} → ${this.formatBytes(size2)}<br>Change: ${this.formatBytes(change)} (${percentChange.toFixed(1)}%)`;
                hoverTexts.push(hoverText);
                barColors.push(this.getDecreaseColor(metricType));
                decreasedCount++;
            }
        });
        
        return {
            fileNames,
            fullFileNames, // Include full filenames in return data
            barValues,
            hoverTexts,
            barColors,
            decreasedCount: decreasedCount,
            increasedCount: increasedCount
        };
    }
    
    createPlotlyHistogram(chartData, threshold = 50, metricType = 'filesize') {
        // Calculate the range for overlay bars to span full chart width
        const maxAbsValue = Math.max(...chartData.barValues.map(v => Math.abs(v)));
        const fullWidth = maxAbsValue * 2.2; // Full width from left to right edge
        
        const data = [
            {
                y: chartData.fileNames,
                x: chartData.barValues,
                type: 'bar',
                orientation: 'h',
                name: 'File Size Changes',
                marker: {
                    color: chartData.barColors,
                    line: {
                        color: 'rgba(0, 0, 0, 0.3)',
                        width: 1
                    }
                },
                hoverinfo: 'skip', // Skip hover for main bars
                hoverlabel: {
                    bgcolor: '#FFFFDD',
                    bordercolor: '#333',
                    font: { color: '#000', size: 12 }
                },
                showlegend: false
            },
            // Invisible overlay bars for easier hovering - spans full row width
            {
                y: chartData.fileNames,
                x: chartData.fileNames.map(() => fullWidth), // Full width bars
                type: 'bar',
                orientation: 'h',
                name: 'Hover Area',
                marker: {
                    color: 'rgba(240, 240, 240, 0.15)', // Very light gray with low opacity
                    line: { 
                        color: 'rgba(220, 220, 220, 0.2)', // Slightly darker gray border
                        width: 0.5 
                    }
                },
                hoverinfo: 'text', // Enable hover events for custom tooltip
                customdata: chartData.hoverTexts.map((text, index) => ({
                    hoverText: text,
                    fullFileName: chartData.fullFileNames[index]
                })),
                hoverlabel: {
                    bgcolor: '#FFFFDD',
                    bordercolor: '#333',
                    font: { color: '#000', size: 12 }
                },
                showlegend: false,
                base: -maxAbsValue * 1.1, // Start from left edge
                visible: true,
                hoverinfo: 'text',
                width: 0.8 // Match the main bar width to align properly
            }
        ];
        
        // Calculate axis range using the already calculated maxAbsValue
        const axisRange = [-maxAbsValue * 1.1, maxAbsValue * 1.1];
        
        // Check if we're on mobile/tablet (768px or less)
        const isMobile = window.innerWidth <= 768;
        
        // Update external title block instead of using Plotly title
        this.updateExternalTitle(metricType, threshold, chartData.decreasedCount, chartData.increasedCount);
        
        const layout = {
            width: this.width,
            height: Math.max(600, chartData.fileNames.length * 25 + 100), // Dynamic height based on data
            margin: { 
                l: 240, 
                r: 50, 
                t: 30, 
                b: 50 
            }, // 20% more left margin for file names (200 * 1.2 = 240), reduced top margin since title is external
            font: { size: 11, family: 'Arial, sans-serif' },
            paper_bgcolor: 'white',
            plot_bgcolor: 'white',
            dragmode: 'pan', // Set pan as default in layout
            bargap: 0.1, // Control spacing between bars (smaller = closer together)
            barmode: 'overlay', // Overlay mode for the invisible bars
            hovermode: 'closest', // Position hover tooltip near cursor
            xaxis: {
                title: 'Size Change (bytes)',
                range: axisRange,
                zeroline: true,
                zerolinecolor: '#333',
                zerolinewidth: 2,
                gridcolor: '#f0f0f0',
                tickformat: '.2s',
                fixedrange: true
            },
            yaxis: {
                title: 'Files',
                tickmode: 'array',
                tickvals: Array.from({length: chartData.fileNames.length}, (_, i) => i),
                ticktext: chartData.fileNames,
                autorange: 'reversed', // Show first file at top
                gridcolor: '#f0f0f0',
                fixedrange: true
            },
            annotations: [
                {
                    text: "← smaller",
                    showarrow: false,
                    x: -maxAbsValue * 0.5,
                    y: -1,
                    xref: 'x',
                    yref: 'y',
                    font: { size: 12, color: this.colors.decreasedFilesize }
                },
                {
                    text: "bigger →",
                    showarrow: false,
                    x: maxAbsValue * 0.5,
                    y: -1,
                    xref: 'x',
                    yref: 'y',
                    font: { size: 12, color: this.colors.increasedFilesize }
                }
            ]
        };
        
        const config = {
            displayModeBar: true,
            modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d', 'zoomIn2d', 'zoomOut2d', 'zoom2d', 'resetScale2d'],
            displaylogo: false,
            responsive: true,
            scrollZoom: false,
            doubleClick: false,
            dragMode: 'pan', // Set pan as default interaction mode
            toImageButtonOptions: {
                format: 'png',
                filename: 'defold_size_histogram',
                height: layout.height,
                width: this.width,
                scale: 1
            }
        };
        
        Plotly.newPlot(this.containerId, data, layout, config);
        
        // Add click event listeners for additional interactivity
        this.addInteractivity();
    }
    
    showMessage(message) {
        this.container.innerHTML = `
            <div style="
                display: flex;
                align-items: center;
                justify-content: center;
                height: 400px;
                font-size: 18px;
                color: #666;
            ">${message}</div>
        `;
    }
    
    truncateFileName(filename) {
        return filename.length > 40 
            ? '...' + filename.slice(-37)
            : filename;
    }
    
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
        
        return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
    }
    
    getIncreaseColor(metricType) {
        // Map metric types to appropriate increase colors
        const colorMap = {
            'vmsize': this.colors.increasedVmsize,
            'filesize': this.colors.increasedFilesize,
            'compressed': this.colors.increasedFilesize,
            'uncompressed': this.colors.increasedVmsize
        };
        return colorMap[metricType.toLowerCase()] || this.colors.increasedFilesize;
    }
    
    getDecreaseColor(metricType) {
        // Map metric types to appropriate decrease colors
        const colorMap = {
            'vmsize': this.colors.decreasedVmsize,
            'filesize': this.colors.decreasedFilesize,
            'compressed': this.colors.decreasedFilesize,
            'uncompressed': this.colors.decreasedVmsize
        };
        return colorMap[metricType.toLowerCase()] || this.colors.decreasedFilesize;
    }
    
    formatMetricTitle(metricType) {
        // Convert metric types to display titles
        const titleMap = {
            'vmsize': 'VM Size',
            'filesize': 'File Size',
            'compressed': 'Compressed Size',
            'uncompressed': 'Uncompressed Size'
        };
        return titleMap[metricType.toLowerCase()] || 
               metricType.charAt(0).toUpperCase() + metricType.slice(1);
    }
    
    updateExternalTitle(metricType, threshold, decreasedCount, increasedCount) {
        // Update the chart info element with title information
        const chartInfo = document.getElementById('chart-info');
        if (chartInfo) {
            chartInfo.textContent = `${this.formatMetricTitle(metricType)} Changes (≥${this.formatBytes(threshold)}): ${decreasedCount} decreased, ${increasedCount} increased - Click bars for timeline, hover for details`;
        }
    }
    
    addInteractivity() {
        const plotElement = document.getElementById(this.containerId);
        
        // Add click events
        plotElement.on('plotly_click', (data) => {
            this.handleElementClick(data);
        });
        
        // Add custom cursor-based hover functionality
        this.addCustomHover(plotElement);
        
        // Add hover functionality for y-axis labels
        this.addYAxisHover(plotElement);
        
        // Double-click disabled to prevent zoom reset
    }
    
    addCustomHover(plotElement) {
        const tooltip = document.getElementById('tooltip');
        if (!tooltip) return;
        
        // Add mouse events to the plot element
        plotElement.on('plotly_hover', (data) => {
            if (data.points && data.points.length > 0) {
                const point = data.points[0];
                const hoverText = point.customdata ? point.customdata.hoverText : '';
                
                if (hoverText) {
                    tooltip.innerHTML = hoverText.replace(/\n/g, '<br>');
                    // Apply Plotly-style yellow background
                    tooltip.style.backgroundColor = '#FFFFDD';
                    tooltip.style.color = '#000';
                    tooltip.style.border = '1px solid #333';
                    // Reset width and let content determine size
                    tooltip.style.width = 'auto';
                    tooltip.style.maxWidth = '400px'; // Reasonable max width
                    tooltip.style.minWidth = '150px'; // Minimum width
                    tooltip.style.wordWrap = 'break-word';
                    tooltip.style.whiteSpace = 'normal';
                    tooltip.classList.add('visible');
                }
            }
        });
        
        plotElement.on('plotly_unhover', () => {
            tooltip.classList.remove('visible');
        });
        
        // Add mousemove event to position tooltip near cursor
        plotElement.addEventListener('mousemove', (e) => {
            if (tooltip.classList.contains('visible')) {
                tooltip.style.left = (e.pageX + 15) + 'px';
                tooltip.style.top = (e.pageY - 10) + 'px';
                
                // Adjust position if tooltip goes off screen
                const tooltipRect = tooltip.getBoundingClientRect();
                if (tooltipRect.right > window.innerWidth) {
                    tooltip.style.left = (e.pageX - tooltipRect.width - 15) + 'px';
                }
                if (tooltipRect.bottom > window.innerHeight) {
                    tooltip.style.top = (e.pageY - tooltipRect.height - 10) + 'px';
                }
            }
        });
    }
    
    addYAxisHover(plotElement) {
        // Wait for plot to be fully rendered before adding hover listeners
        setTimeout(() => {
            const yAxisLabels = plotElement.querySelectorAll('.ytick text');
            const tooltip = document.getElementById('tooltip');
            
            if (!tooltip) return;
            
            yAxisLabels.forEach((label, index) => {
                const truncatedText = label.textContent.trim();
                
                // Find the corresponding full filename
                let fullFileName = '';
                if (this.chartData && this.chartData.fullFileNames && this.chartData.fullFileNames[index]) {
                    fullFileName = this.chartData.fullFileNames[index];
                } else {
                    // Fallback: remove emoji and try to find matching full name
                    const cleanText = truncatedText.replace(/📁\s*/, '');
                    if (this.chartData && this.chartData.fullFileNames) {
                        const match = this.chartData.fullFileNames.find(name => 
                            this.truncateFileName(name) === cleanText
                        );
                        fullFileName = match || truncatedText;
                    }
                }
                
                // Only show tooltip if filename is truncated
                if (fullFileName && fullFileName !== truncatedText.replace(/📁\s*/, '')) {
                    label.addEventListener('mouseenter', (e) => {
                        const rect = e.target.getBoundingClientRect();
                        
                        tooltip.textContent = fullFileName;
                        tooltip.style.left = (rect.right + window.scrollX + 10) + 'px';
                        tooltip.style.top = (rect.top + window.scrollY) + 'px';
                        tooltip.classList.add('visible');
                        
                        // Adjust position if tooltip goes off screen
                        setTimeout(() => {
                            const tooltipRect = tooltip.getBoundingClientRect();
                            if (tooltipRect.right > window.innerWidth) {
                                tooltip.style.left = (rect.left + window.scrollX - tooltipRect.width - 10) + 'px';
                            }
                        }, 0);
                    });
                    
                    label.addEventListener('mouseleave', () => {
                        tooltip.classList.remove('visible');
                    });
                    
                    // Add cursor style to indicate hoverable
                    label.style.cursor = 'help';
                }
            });
        }, 100);
    }
    
    handleElementClick(data) {
        if (data.points && data.points.length > 0) {
            const point = data.points[0];
            this.showTimelineModal(point);
        }
    }
    
    async showTimelineModal(point) {
        const fileName = (point.customdata && point.customdata.fullFileName) || point.y || 'N/A';
        const totalChange = point.x || 0;
        
        // Get version information from the current comparison
        const app = window.defoldApp;
        if (!app || !app.currentComparison) {
            alert('Timeline feature requires version comparison data. Please select and compare two versions first.');
            return;
        }
        
        const { platform, version1, version2 } = app.currentComparison;
        
        // Create modal backdrop
        const modalBackdrop = document.createElement('div');
        modalBackdrop.className = 'timeline-modal-backdrop';
        modalBackdrop.onclick = () => modalBackdrop.remove();
        
        // Add inline styles as fallback to ensure modal appears
        modalBackdrop.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        // Create modal content
        const modal = document.createElement('div');
        modal.className = 'timeline-modal';
        modal.onclick = (e) => e.stopPropagation(); // Prevent closing when clicking inside modal
        
        // Add inline styles as fallback to ensure modal appears properly
        modal.style.cssText = `
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            width: 90%;
            max-width: 900px;
            max-height: 90vh;
            overflow: hidden;
        `;
        
        // Create modal header
        const isDecrease = totalChange < 0;
        const changeColor = isDecrease ? '#27ae60' : '#e74c3c';
        
        modal.innerHTML = `
            <div class="timeline-modal-header">
                <h3>${fileName}</h3>
                <div class="timeline-modal-summary">
                    <span>Total change (${version1} → ${version2}): </span>
                    <span style="color: ${changeColor}; font-weight: bold;">
                        ${isDecrease ? '' : '+'}${this.formatBytes(totalChange)}
                    </span>
                </div>
                <button class="timeline-modal-close" onclick="this.closest('.timeline-modal-backdrop').remove()">×</button>
            </div>
            <div class="timeline-modal-body">
                <div class="timeline-loading">
                    <div class="loading-spinner"></div>
                    <p>Loading timeline data...</p>
                </div>
                <div id="timeline-chart" style="width: 100%; height: 400px; display: none;"></div>
            </div>
        `;
        
        modalBackdrop.appendChild(modal);
        document.body.appendChild(modalBackdrop);
        
        // Load timeline data
        try {
            const timeline = await DataProcessor.getFileTimeline(
                fileName, 
                platform, 
                version1, 
                version2, 
                this.metricType
            );
            
            // Calculate actual total change from timeline data
            if (timeline && timeline.length > 1) {
                const firstSize = timeline[0].size;
                const lastSize = timeline[timeline.length - 1].size;
                const actualTotalChange = lastSize - firstSize;
                
                // Update the summary with actual change
                const summaryDiv = modal.querySelector('.timeline-modal-summary');
                const isDecrease = actualTotalChange < 0;
                const changeColor = isDecrease ? '#27ae60' : '#e74c3c'; // Green for decrease, red for increase
                
                summaryDiv.innerHTML = `
                    <span>Total change (${version1} → ${version2}): </span>
                    <span style="color: ${changeColor}; font-weight: bold;">
                        ${isDecrease ? '' : '+'}${this.formatBytes(actualTotalChange)}
                    </span>
                `;
            }
            
            // Hide loading and show chart
            modal.querySelector('.timeline-loading').style.display = 'none';
            modal.querySelector('#timeline-chart').style.display = 'block';
            
            // Create timeline chart
            this.createTimelineChart(timeline, fileName);
            
        } catch (error) {
            console.error('Error loading timeline data:', error);
            modal.querySelector('.timeline-loading').innerHTML = `
                <p style="color: #e74c3c;">Error loading timeline data: ${error.message}</p>
            `;
        }
    }
    
    createTimelineChart(timeline, fileName) {
        const versions = timeline.map(t => t.version);
        const sizes = timeline.map(t => t.size);
        const exists = timeline.map(t => t.exists);
        
        // Calculate better Y-axis range, handling file existence properly
        const existingSizes = sizes.filter((size, index) => exists[index] && size > 0);
        
        if (existingSizes.length === 0) {
            // File doesn't exist in any version with valid data
            var yAxisMin = -1000;
            var yAxisMax = 1000;
        } else if (existingSizes.length === 1) {
            // File exists in only one version
            const singleValue = existingSizes[0];
            var yAxisMin = 0;
            var yAxisMax = singleValue * 1.2;
        } else {
            // File exists in multiple versions - use actual size range
            const minExistingSize = Math.min(...existingSizes);
            const maxExistingSize = Math.max(...existingSizes);
            const sizeRange = maxExistingSize - minExistingSize;
            
            
            if (sizeRange === 0) {
                // Same size in all versions where it exists
                const baseValue = minExistingSize;
                var yAxisMin = Math.max(0, baseValue * 0.9);
                var yAxisMax = baseValue * 1.1;
            } else {
                // Different sizes - show the actual range
                const padding = sizeRange * 0.1;
                var yAxisMin = Math.max(0, minExistingSize - padding);
                var yAxisMax = maxExistingSize + padding;
            }
        }
        
        // Prepare hover text
        const hoverText = timeline.map(t => 
            `Version: ${t.version}<br>Size: ${this.formatBytes(t.size)}<br>Status: ${t.exists ? 'Exists' : 'Not found'}`
        );
        
        const data = [{
            x: versions,
            y: sizes,
            type: 'scatter',
            mode: 'lines+markers',
            name: `${this.metricType} Size`,
            line: {
                color: '#3498db',
                width: 3
            },
            marker: {
                size: 8,
                color: exists.map(e => e ? '#3498db' : '#95a5a6'),
                line: {
                    color: '#2c3e50',
                    width: 1
                }
            },
            hovertemplate: '%{customdata}<extra></extra>',
            customdata: hoverText,
            hoverlabel: {
                bgcolor: '#FFFFDD',
                bordercolor: '#333',
                font: { color: '#000', size: 12 }
            }
        }];
        
        // Check if we're on mobile for timeline modal
        const isMobile = window.innerWidth <= 768;
        
        const layout = {
            xaxis: {
                title: 'Version',
                tickangle: -45,
                side: 'bottom'
            },
            yaxis: {
                title: `Size (${this.metricType})`,
                tickformat: '',
                automargin: true,
                range: [yAxisMin, yAxisMax],
                fixedrange: false,
                autorange: false
            },
            margin: { 
                l: 80, 
                r: 40, 
                t: isMobile ? 80 : 60, 
                b: 80 
            },
            showlegend: false,
            hovermode: 'closest'
        };
        
        const config = {
            displayModeBar: true,
            modeBarButtonsToRemove: ['select2d', 'lasso2d'],
            displaylogo: false,
            responsive: true
        };
        
        Plotly.newPlot('timeline-chart', data, layout, config);
    }
    
}