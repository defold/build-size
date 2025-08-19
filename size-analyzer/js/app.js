// Main Application Logic

class DefoldSizeAnalyzer {
    constructor() {
        this.analysisIndex = null;
        this.currentComparison = null;
        this.chart = null;
        this.activeTab = null; // Will be set when tabs are created
        this.availableMetrics = []; // Will be populated from CSV headers
        this.currentSortField = 'difference'; // Default sort by change magnitude
        this.currentSortDirection = 'desc'; // Default descending (largest changes first)
        
        this.initializeElements();
        this.bindEvents();
        this.loadAnalysisIndex();
        this.handleUrlParameters();
    }
    
    initializeElements() {
        this.elements = {
            platformSelect: document.getElementById('platform-select'),
            version1Select: document.getElementById('version1-select'),
            version2Select: document.getElementById('version2-select'),
            // Checkboxes removed - replaced with tabs
            // hideUnchangedCheckbox removed - not needed for change-based histogram
            thresholdSlider: document.getElementById('threshold-slider'),
            thresholdValue: document.getElementById('threshold-value'),
            // maxFilesSlider removed - showing all changed files
            status: document.getElementById('status'),
            version1Label: document.getElementById('version1-label'),
            version2Label: document.getElementById('version2-label'),
            chartInfo: document.getElementById('chart-info'),
            legendDescription: document.getElementById('legend-description'),
            tabContainer: document.querySelector('.tab-buttons'), // Reference to container instead of buttons
            summary: document.getElementById('summary'),
            fileList: document.getElementById('file-list'),
            fileFilter: document.getElementById('file-filter'),
            changeTypeFilter: document.getElementById('change-type-filter'),
            minChangeFilter: document.getElementById('min-change-filter'),
            maxChangeFilter: document.getElementById('max-change-filter'),
            // Debug filter elements
            debugFilterGroup: document.getElementById('debug-filter-group'),
            hideDebugCheckbox: document.getElementById('hide-debug-sections'),
            debugInfoBtn: document.getElementById('debug-info-btn')
        };
    }
    
    bindEvents() {
        this.elements.platformSelect.addEventListener('change', () => this.onPlatformChange());
        this.elements.version1Select.addEventListener('change', () => this.onVersion1Change());
        this.elements.version2Select.addEventListener('change', () => this.onVersionChange());
        this.elements.thresholdSlider.addEventListener('input', () => this.onThresholdChange());
        
        // Tab switching will be handled dynamically when tabs are created
        
        // Table filters
        this.elements.fileFilter.addEventListener('input', () => this.onTableFilterChange());
        this.elements.changeTypeFilter.addEventListener('change', () => this.onTableFilterChange());
        this.elements.minChangeFilter.addEventListener('input', () => this.onTableFilterChange());
        this.elements.maxChangeFilter.addEventListener('input', () => this.onTableFilterChange());
        
        // Debug filter
        if (this.elements.hideDebugCheckbox) {
            this.elements.hideDebugCheckbox.addEventListener('change', () => this.onDebugFilterChange());
        }
        if (this.elements.debugInfoBtn) {
            this.elements.debugInfoBtn.addEventListener('click', () => this.showDebugInfo());
        }
    }
    
    async loadAnalysisIndex() {
        try {
            this.setStatus('Loading analysis index...', 'info');
            
            const response = await fetch('analysis_index.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.analysisIndex = await response.json();
            this.populatePlatformSelect();
            this.setDefaultSelections();
            this.setStatus('Ready for comparison', 'info');
            
        } catch (error) {
            console.error('Error loading analysis index:', error);
            this.setStatus('Error loading analysis index. Please check that analysis_index.json exists.', 'error');
        }
    }
    
    populatePlatformSelect() {
        const platforms = Object.keys(this.analysisIndex.platforms);
        
        this.elements.platformSelect.innerHTML = '';
        
        platforms.forEach(platform => {
            const option = document.createElement('option');
            option.value = platform;
            option.textContent = platform;
            this.elements.platformSelect.appendChild(option);
        });
    }
    
    getVersionsForPlatform(platform) {
        /**
         * Helper method to handle both old and new analysis_index.json formats:
         * - Old format: {"platforms": {"platform": {"versions": ["1.9.0", "1.9.1", ...]}}}
         * - New format: {"platforms": {"platform": {"versions": [{"version": "1.9.0", "sha1": "..."}, ...]}}}
         */
        const platformData = this.analysisIndex.platforms[platform];
        if (!platformData || !platformData.versions) {
            return [];
        }
        
        const versions = platformData.versions;
        
        // Check if it's the new format (array of objects with version/sha1)
        if (versions.length > 0 && typeof versions[0] === 'object' && versions[0].version) {
            return versions.map(v => v.version);
        }
        
        // Old format (array of strings)
        return versions;
    }
    
    onPlatformChange() {
        const selectedPlatform = this.elements.platformSelect.value;
        
        if (selectedPlatform) {
            // Store current version selections
            const currentVersion1 = this.elements.version1Select.value;
            const currentVersion2 = this.elements.version2Select.value;
            
            this.populateVersionSelects(selectedPlatform);
            this.elements.version1Select.disabled = false;
            this.elements.version2Select.disabled = false;
            
            // Try to preserve version selections if they exist in new platform
            const newVersions = this.getVersionsForPlatform(selectedPlatform);
            
            if (currentVersion1 && newVersions.includes(currentVersion1)) {
                this.elements.version1Select.value = currentVersion1;
            }
            if (currentVersion2 && newVersions.includes(currentVersion2)) {
                this.elements.version2Select.value = currentVersion2;
            }
            
            // If no versions were preserved or selected, set defaults (last-1 to last)
            if (!this.elements.version1Select.value || !this.elements.version2Select.value) {
                this.setDefaultVersions(newVersions);
            }
            
            // Auto-trigger comparison if both versions are selected
            if (this.elements.version1Select.value && this.elements.version2Select.value) {
                this.compareVersions();
            }
            
            // Show debug filter for Android platforms
            if (this.elements.debugFilterGroup) {
                if (selectedPlatform.includes('android')) {
                    this.elements.debugFilterGroup.style.display = 'block';
                } else {
                    this.elements.debugFilterGroup.style.display = 'none';
                }
            }
        } else {
            this.elements.version1Select.disabled = true;
            this.elements.version2Select.disabled = true;
            this.clearVersionSelects();
            
            // Hide debug filter when no platform selected
            if (this.elements.debugFilterGroup) {
                this.elements.debugFilterGroup.style.display = 'none';
            }
        }
        
        this.clearResults();
    }
    
    populateVersionSelects(platform) {
        const versions = this.getVersionsForPlatform(platform);
        this.allVersions = versions; // Store for reference
        
        // Clear existing options
        this.clearVersionSelects();
        
        // Populate baseline (version1) - exclude the last version
        const baselineVersions = versions.slice(0, -1); // Remove last version
        baselineVersions.forEach(version => {
            const option1 = document.createElement('option');
            option1.value = version;
            option1.textContent = version;
            this.elements.version1Select.appendChild(option1);
        });
        
        // Populate compare (version2) - initially with all versions after first
        const compareVersions = versions.slice(1); // Remove first version
        compareVersions.forEach(version => {
            const option2 = document.createElement('option');
            option2.value = version;
            option2.textContent = version;
            this.elements.version2Select.appendChild(option2);
        });
    }
    
    clearVersionSelects() {
        this.elements.version1Select.innerHTML = '';
        this.elements.version2Select.innerHTML = '';
    }
    
    updateCompareVersions() {
        const selectedBaseline = this.elements.version1Select.value;
        if (!selectedBaseline || !this.allVersions) return;
        
        // Find the index of the selected baseline
        const baselineIndex = this.allVersions.indexOf(selectedBaseline);
        if (baselineIndex === -1) return;
        
        // Get currently selected compare version
        const currentCompareVersion = this.elements.version2Select.value;
        
        // Clear compare options
        this.elements.version2Select.innerHTML = '';
        
        // Populate compare box with only versions greater than baseline
        const availableCompareVersions = this.allVersions.slice(baselineIndex + 1);
        availableCompareVersions.forEach(version => {
            const option = document.createElement('option');
            option.value = version;
            option.textContent = version;
            this.elements.version2Select.appendChild(option);
        });
        
        // Try to preserve the current compare selection if it's still valid
        if (currentCompareVersion && availableCompareVersions.includes(currentCompareVersion)) {
            this.elements.version2Select.value = currentCompareVersion;
        } else if (availableCompareVersions.length > 0) {
            // Otherwise select the first available (next version after baseline)
            this.elements.version2Select.value = availableCompareVersions[0];
        }
    }
    
    setDefaultVersions(versions) {
        if (versions.length >= 2) {
            // Set second-to-last as baseline, last as compare
            const baselineVersion = versions[versions.length - 2];
            const compareVersion = versions[versions.length - 1];
            
            // Small delay to ensure options are populated
            setTimeout(() => {
                this.elements.version1Select.value = baselineVersion;
                
                // Update compare options based on selected baseline
                this.updateCompareVersions();
                
                // Set compare version if it's still available
                if (this.elements.version2Select.querySelector(`option[value="${compareVersion}"]`)) {
                    this.elements.version2Select.value = compareVersion;
                }
                
                // Trigger comparison after setting values
                if (this.elements.version1Select.value && this.elements.version2Select.value &&
                    this.elements.version1Select.value !== this.elements.version2Select.value) {
                    this.compareVersions();
                }
            }, 10);
        } else if (versions.length === 1) {
            // If only one version available, use it for both
            if (!this.elements.version1Select.value) {
                this.elements.version1Select.value = versions[0];
            }
            if (!this.elements.version2Select.value) {
                this.elements.version2Select.value = versions[0];
            }
        }
    }
    
    setDefaultSelections() {
        const platforms = Object.keys(this.analysisIndex.platforms);
        if (platforms.length > 0) {
            // Select first platform
            const firstPlatform = platforms[0];
            this.elements.platformSelect.value = firstPlatform;
            
            // Show debug filter for Android platforms
            if (this.elements.debugFilterGroup) {
                if (firstPlatform.includes('android')) {
                    this.elements.debugFilterGroup.style.display = 'block';
                } else {
                    this.elements.debugFilterGroup.style.display = 'none';
                }
            }
            
            // Populate versions and set defaults
            const versions = this.getVersionsForPlatform(firstPlatform);
            this.populateVersionSelects(firstPlatform);
            this.elements.version1Select.disabled = false;
            this.elements.version2Select.disabled = false;
            
            // Set default versions (will auto-trigger comparison)
            this.setDefaultVersions(versions);
        }
        
        // Apply URL parameters if they exist (for cross-navigation from dashboard)
        this.applyUrlParameters();
    }
    
    onVersion1Change() {
        // Update compare versions when baseline changes
        this.updateCompareVersions();
        
        // Then trigger version change logic
        this.onVersionChange();
    }
    
    onVersionChange() {
        const version1 = this.elements.version1Select.value;
        const version2 = this.elements.version2Select.value;
        
        if (version1 === version2 && version1) {
            this.setStatus('Please select different versions for comparison', 'error');
            this.clearResults();
        } else if (version1 && version2 && version1 !== version2) {
            this.compareVersions();
        } else {
            this.clearResults();
        }
    }
    
    onTabChange(tabName) {
        // Update active tab
        this.activeTab = tabName;
        
        // Update tab button states using the container
        const tabButtons = this.elements.tabContainer.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            if (button.dataset.tab === tabName) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });
        
        // Update chart info text
        this.elements.chartInfo.textContent = `Cumulative ${this.formatMetricName(tabName)} Changes - Click bars for timeline, hover for details`;
        
        // Re-render if we have data
        if (this.currentComparison && this.currentComparison.metricComparisons) {
            // Recalculate threshold range for the new metric
            const activeComparisons = this.currentComparison.metricComparisons[tabName];
            
            if (activeComparisons) {
                const thresholdRange = this.calculateThresholdRange(activeComparisons);
                this.updateThresholdSlider(thresholdRange);
            }
            
            this.displayResults();
        }
    }
    
    // onFilterChange removed - not needed for change-based histogram
    
    onThresholdChange() {
        const threshold = parseInt(this.elements.thresholdSlider.value);
        // Update the threshold value span (re-find it in case DOM was updated)
        const thresholdValueSpan = document.getElementById('threshold-value');
        if (thresholdValueSpan) {
            thresholdValueSpan.textContent = DataProcessor.formatBytes(threshold);
        }
        
        if (this.currentComparison && this.currentComparison.data1 && this.currentComparison.data2) {
            // Reprocess data with new threshold for all metrics
            this.availableMetrics.forEach(metric => {
                this.currentComparison.metricComparisons[metric] = DataProcessor.processDataByMetric(
                    this.currentComparison.data1, 
                    this.currentComparison.data2, 
                    metric, 
                    threshold,
                    this.filenameColumn
                );
            });
            
            // Update general comparisons reference
            this.currentComparison.comparisons = this.currentComparison.metricComparisons[this.availableMetrics[0]] || [];
            
            this.displayResults();
        }
    }
    
    // onMaxFilesChange removed - showing all changed files
    
    onTableFilterChange() {
        if (this.currentComparison && this.currentComparison.metricComparisons) {
            this.displayFileList(this.getFilteredComparisons());
        }
    }
    
    getFilteredComparisons() {
        if (!this.currentComparison || !this.currentComparison.metricComparisons) {
            return [];
        }
        
        // Use the currently active metric for filtering
        const activeComparisons = this.currentComparison.metricComparisons[this.activeTab] || [];
        let filtered = [...activeComparisons];
        
        // Apply debug filtering first if enabled and platform is Android
        const hideDebug = this.elements.hideDebugCheckbox && this.elements.hideDebugCheckbox.checked;
        const isAndroid = this.elements.platformSelect.value.includes('android');
        
        if (hideDebug && isAndroid) {
            filtered = filtered.filter(comp => !this.isDebugSection(comp.compileUnit));
        }
        
        // Filter by file name
        const fileFilter = this.elements.fileFilter.value.toLowerCase();
        if (fileFilter) {
            filtered = filtered.filter(comp => 
                comp.compileUnit.toLowerCase().includes(fileFilter)
            );
        }
        
        // Filter by change type
        const changeTypeFilter = this.elements.changeTypeFilter.value;
        if (changeTypeFilter) {
            filtered = filtered.filter(comp => comp.changeType === changeTypeFilter);
        }
        
        // Filter by min change
        const minChange = parseFloat(this.elements.minChangeFilter.value);
        if (!isNaN(minChange)) {
            filtered = filtered.filter(comp => Math.abs(comp.difference) >= minChange);
        }
        
        // Filter by max change
        const maxChange = parseFloat(this.elements.maxChangeFilter.value);
        if (!isNaN(maxChange)) {
            filtered = filtered.filter(comp => Math.abs(comp.difference) <= maxChange);
        }
        
        return filtered;
    }
    
    async compareVersions() {
        const platform = this.elements.platformSelect.value;
        const version1 = this.elements.version1Select.value;
        const version2 = this.elements.version2Select.value;
        
        if (!platform || !version1 || !version2) {
            this.setStatus('Please select platform and both versions', 'error');
            return;
        }
        
        try {
            this.setStatus('Loading comparison data...', 'info');
            
            // Load CSV data for both versions
            const [data1, data2] = await Promise.all([
                CSVParser.loadCSV(`${platform}/${version1}.csv`),
                CSVParser.loadCSV(`${platform}/${version2}.csv`)
            ]);
            
            this.setStatus('Processing comparison...', 'info');
            
            // Detect available metrics from CSV headers
            if (data1.length > 0) {
                const headers = Object.keys(data1[0]);
                this.availableMetrics = CSVParser.getMetricsFromHeaders(headers);
                this.filenameColumn = CSVParser.getFilenameColumn(headers);
                
                
                // Create dynamic tabs
                this.createDynamicTabs();
                
                // Reset and set active tab for new platform
                this.activeTab = this.availableMetrics.length > 0 ? this.availableMetrics[0] : null;
            }
            
            // Store raw data for reprocessing when metrics change
            this.currentComparison = { data1, data2, platform, version1, version2 };
            
            this.processAndDisplayComparison();
            
        } catch (error) {
            console.error('Error during comparison:', error);
            this.setStatus(`Error loading data: ${error.message}`, 'error');
        } finally {
            // No button to re-enable since we removed it
        }
    }
    
    createDynamicTabs() {
        const tabContainer = this.elements.tabContainer;
        if (!tabContainer) return;
        
        // Clear existing tabs
        tabContainer.innerHTML = '';
        
        // Create tabs for each available metric
        this.availableMetrics.forEach((metric, index) => {
            const button = document.createElement('button');
            button.className = 'tab-button';
            button.dataset.tab = metric;
            button.textContent = this.formatMetricName(metric);
            
            // Set first tab as active if no active tab is set
            if (index === 0 && !this.activeTab) {
                button.classList.add('active');
                this.activeTab = metric;
            } else if (metric === this.activeTab) {
                button.classList.add('active');
            }
            
            // Add click event listener
            button.addEventListener('click', () => this.onTabChange(metric));
            
            tabContainer.appendChild(button);
        });
    }
    
    formatMetricName(metric) {
        // Convert metric names to human-readable format
        const formatMap = {
            'filesize': 'File Size',
            'vmsize': 'VM Size',
            'compressed': 'Compressed',
            'uncompressed': 'Uncompressed'
        };
        
        return formatMap[metric.toLowerCase()] || 
               metric.charAt(0).toUpperCase() + metric.slice(1);
    }
    
    processAndDisplayComparison() {
        const { data1, data2, version1, version2 } = this.currentComparison;
        
        // Process all available metrics
        this.currentComparison.metricComparisons = {};
        
        // First, calculate threshold without any filtering to get data range
        this.availableMetrics.forEach(metric => {
            this.currentComparison.metricComparisons[metric] = DataProcessor.processDataByMetric(
                data1, data2, metric, 0, this.filenameColumn
            );
        });
        
        // Calculate dynamic threshold range for the active metric
        const activeComparisons = this.currentComparison.metricComparisons[this.activeTab] || [];
        const thresholdRange = this.calculateThresholdRange(activeComparisons);
        
        // Update threshold slider with dynamic range
        this.updateThresholdSlider(thresholdRange);
        
        // Get current threshold value
        const threshold = parseInt(this.elements.thresholdSlider.value);
        
        // Reprocess all metrics with actual threshold
        this.availableMetrics.forEach(metric => {
            this.currentComparison.metricComparisons[metric] = DataProcessor.processDataByMetric(
                data1, data2, metric, threshold, this.filenameColumn
            );
        });
        
        // Use first metric comparisons for general summary (backward compatibility)
        this.currentComparison.comparisons = this.currentComparison.metricComparisons[this.availableMetrics[0]] || [];
        
        // Update labels
        this.elements.version1Label.textContent = `Version ${version1}`;
        this.elements.version2Label.textContent = `Version ${version2}`;
        
        // Update legend description with actual version numbers
        this.elements.legendDescription.innerHTML = `
            Shows cumulative change from version <strong>${version1}</strong> to version <strong>${version2}</strong>.<br>
            Use tabs above to switch between File Size and VM Size metrics.<br>
            <strong>Click any file bar</strong> to see its detailed evolution timeline across all intermediate versions.
        `;
        
        this.displayResults();
        this.setStatus(`Comparison complete: ${this.currentComparison.comparisons.length} files analyzed`, 'success');
    }
    
    displayResults() {
        const threshold = parseInt(this.elements.thresholdSlider.value);
        
        // Initialize chart if needed
        if (!this.chart) {
            this.chart = new PlotlyHistogramChart('metric-chart');
        }
        
        // Get the metric-specific data for the active tab
        const metricData = this.filterByMetric(null, this.activeTab);
        
        
        // Prepare data for visualization
        const vizData = DataProcessor.prepareForVisualization(metricData, false);
        this.chart.render(vizData.all, threshold, this.activeTab);
        
        // Display summary using first available metric data
        const summaryData = this.currentComparison.metricComparisons?.[this.availableMetrics[0]] || [];
        this.displaySummary(summaryData);
        
        // Display file list with filters applied  
        this.displayFileList(this.getFilteredComparisons());
    }
    
    displaySummary(comparisons) {
        const summary = DataProcessor.generateSummary(comparisons);
        
        const summaryHtml = `
            <div class="summary-item">
                <span>Total files:</span>
                <span>${DataProcessor.formatNumber(summary.totalFiles)}</span>
            </div>
            <div class="summary-item">
                <span>Unchanged:</span>
                <span>${DataProcessor.formatNumber(summary.unchanged)}</span>
            </div>
            <div class="summary-item">
                <span>Increased size:</span>
                <span>${DataProcessor.formatNumber(summary.increased)}</span>
            </div>
            <div class="summary-item">
                <span>Decreased size:</span>
                <span>${DataProcessor.formatNumber(summary.decreased)}</span>
            </div>
            <div class="summary-item">
                <span>Total size change:</span>
                <span class="${summary.totalSizeChange >= 0 ? 'positive' : 'negative'}">
                    ${DataProcessor.formatBytes(summary.totalSizeChange)}
                </span>
            </div>
            ${summary.largestIncrease ? `
                <div class="summary-item">
                    <span>Largest increase:</span>
                    <span class="positive">${DataProcessor.formatBytes(summary.largestIncrease.difference)}</span>
                </div>
            ` : ''}
            ${summary.largestDecrease ? `
                <div class="summary-item">
                    <span>Largest decrease:</span>
                    <span class="negative">${DataProcessor.formatBytes(summary.largestDecrease.difference)}</span>
                </div>
            ` : ''}
        `;
        
        this.elements.summary.innerHTML = summaryHtml;
    }
    
    displayFileList(comparisons) {
        const maxItems = 100; // Limit for performance
        
        // Sort comparisons based on current sort settings
        const sortedComparisons = this.sortComparisons([...comparisons]);
        const displayItems = sortedComparisons.slice(0, maxItems);
        
        // Get current metric name for header
        const currentMetric = this.formatMetricName(this.activeTab);
        const version1 = this.currentComparison?.version1 || 'Version 1';
        const version2 = this.currentComparison?.version2 || 'Version 2';
        
        // Generate sortable headers with sort indicators
        const getSortIcon = (field) => {
            if (this.currentSortField === field) {
                return this.currentSortDirection === 'asc' ? ' ↑' : ' ↓';
            }
            return '';
        };
        
        let html = `
            <div class="file-list-header">
                <div class="file-name-header sortable-header" data-sort="filename">
                    File Name${getSortIcon('filename')}
                </div>
                <div class="file-sizes-header">
                    <div class="size-value-header sortable-header" data-sort="size1">
                        ${currentMetric} (${version1})${getSortIcon('size1')}
                    </div>
                    <div class="size-value-header sortable-header" data-sort="size2">
                        ${currentMetric} (${version2})${getSortIcon('size2')}
                    </div>
                    <div class="size-change-header sortable-header" data-sort="difference">
                        Change (bytes)${getSortIcon('difference')}
                    </div>
                </div>
            </div>
        `;
        
        if (comparisons.length > maxItems) {
            const sortDescription = this.getSortDescription();
            html += `<p><em>Showing top ${maxItems} of ${comparisons.length} files (sorted by ${sortDescription})</em></p>`;
        }
        
        displayItems.forEach(comp => {
            const changeClass = comp.difference > 0 ? 'positive' : 
                               comp.difference < 0 ? 'negative' : 'neutral';
            
            // Add move indicator to display name if applicable
            let displayName = comp.compileUnit;
            let moveIndicator = '';
            if (comp.isMoved) {
                moveIndicator = ' 📁';
                displayName = comp.displayName || comp.compileUnit;
            }
            
            html += `
                <div class="file-item">
                    <div class="file-name" title="${comp.compileUnit}${comp.isMoved ? ' (File was moved)' : ''}">${displayName}${moveIndicator}</div>
                    <div class="file-sizes">
                        <div class="size-value">${DataProcessor.formatBytes(comp.size1)}</div>
                        <div class="size-value">${DataProcessor.formatBytes(comp.size2)}</div>
                        <div class="size-change ${changeClass}">
                            ${comp.difference === 0 ? '0' : DataProcessor.formatBytes(comp.difference)}
                        </div>
                    </div>
                </div>
            `;
        });
        
        this.elements.fileList.innerHTML = html;
        
        // Add click event listeners to sortable headers
        this.elements.fileList.querySelectorAll('.sortable-header').forEach(header => {
            header.addEventListener('click', () => {
                const sortField = header.dataset.sort;
                this.onColumnHeaderClick(sortField);
            });
        });
    }
    
    onColumnHeaderClick(sortField) {
        // Toggle sort direction if clicking the same field
        if (this.currentSortField === sortField) {
            this.currentSortDirection = this.currentSortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            // New field - set default direction based on field type
            this.currentSortField = sortField;
            if (sortField === 'filename') {
                this.currentSortDirection = 'asc'; // Alphabetical ascending
            } else {
                this.currentSortDirection = 'desc'; // Numerical descending (largest first)
            }
        }
        
        // Re-render the file list with new sorting
        this.displayFileList(this.getFilteredComparisons());
    }
    
    sortComparisons(comparisons) {
        return comparisons.sort((a, b) => {
            let valueA, valueB;
            
            switch (this.currentSortField) {
                case 'filename':
                    valueA = a.compileUnit.toLowerCase();
                    valueB = b.compileUnit.toLowerCase();
                    break;
                case 'size1':
                    valueA = a.size1;
                    valueB = b.size1;
                    break;
                case 'size2':
                    valueA = a.size2;
                    valueB = b.size2;
                    break;
                case 'difference':
                    valueA = Math.abs(a.difference); // Sort by absolute change magnitude
                    valueB = Math.abs(b.difference);
                    break;
                default:
                    // Default sort by absolute difference (change magnitude)
                    valueA = Math.abs(a.difference);
                    valueB = Math.abs(b.difference);
            }
            
            // Handle string vs number comparison
            let comparison;
            if (typeof valueA === 'string' && typeof valueB === 'string') {
                comparison = valueA.localeCompare(valueB);
            } else {
                comparison = valueA - valueB;
            }
            
            // Apply sort direction
            return this.currentSortDirection === 'asc' ? comparison : -comparison;
        });
    }
    
    getSortDescription() {
        const fieldNames = {
            'filename': 'file name',
            'size1': 'baseline size',
            'size2': 'compare size', 
            'difference': 'change magnitude'
        };
        
        const fieldName = fieldNames[this.currentSortField] || 'change magnitude';
        const direction = this.currentSortDirection === 'asc' ? 'ascending' : 'descending';
        return `${fieldName}, ${direction}`;
    }
    
    calculateThresholdRange(comparisons) {
        // Get all non-zero absolute differences
        const nonZeroDiffs = comparisons
            .map(comp => Math.abs(comp.difference))
            .filter(diff => diff > 0)
            .sort((a, b) => a - b);
        
        if (nonZeroDiffs.length === 0) {
            return { min: 1, max: 1000, median: 50 };
        }
        
        const min = nonZeroDiffs[0];
        
        // Remove top 30 files for max calculation to avoid extreme outliers
        const trimmedDiffs = nonZeroDiffs.length > 30 ? 
            nonZeroDiffs.slice(0, -30) : 
            nonZeroDiffs;
        
        const max = trimmedDiffs.length > 0 ? 
            trimmedDiffs[trimmedDiffs.length - 1] : 
            nonZeroDiffs[nonZeroDiffs.length - 1];
        
        const median = nonZeroDiffs[Math.floor(nonZeroDiffs.length / 2)];
        
        return { min, max, median };
    }
    
    updateThresholdSlider(thresholdRange) {
        const slider = this.elements.thresholdSlider;
        const valueDisplay = this.elements.thresholdValue;
        
        // Update slider range
        slider.min = thresholdRange.min;
        slider.max = thresholdRange.max;
        slider.value = thresholdRange.median;
        
        // Update display
        valueDisplay.textContent = DataProcessor.formatBytes(thresholdRange.median);
        
        // Update label
        const label = slider.parentElement.querySelector('label');
        label.innerHTML = `Change threshold: <span id="threshold-value">${DataProcessor.formatBytes(thresholdRange.median)}</span>`;
    }

    filterByMetric(data, metricType) {
        // Return the appropriate metric data from the current comparison
        let comparisons = this.currentComparison.metricComparisons?.[metricType] || [];
        
        // Apply debug filtering if enabled and platform is Android
        const hideDebug = this.elements.hideDebugCheckbox && this.elements.hideDebugCheckbox.checked;
        const isAndroid = this.elements.platformSelect.value.includes('android');
        
        if (hideDebug && isAndroid) {
            comparisons = comparisons.filter(comp => !this.isDebugSection(comp.compileUnit));
        }
        
        return comparisons;
    }
    
    clearResults() {
        this.currentComparison = null;
        this.availableMetrics = [];
        this.activeTab = null;
        this.filenameColumn = 'compileunits'; // default fallback
        this.elements.summary.innerHTML = '';
        this.elements.fileList.innerHTML = '';
        this.elements.version1Label.textContent = 'Version 1';
        this.elements.version2Label.textContent = 'Version 2';
        
        // Reset legend description
        this.elements.legendDescription.innerHTML = `
            Shows cumulative change from the selected baseline version to the compare version.<br>
            Use tabs above to switch between File Size and VM Size metrics.<br>
            <strong>Click any file bar</strong> to see its detailed evolution timeline across all intermediate versions.
        `;
        
        // Clear tabs
        if (this.elements.tabContainer) {
            this.elements.tabContainer.innerHTML = '';
        }
        
        if (this.chart) {
            this.chart.showMessage('Select versions to compare');
        }
    }
    
    onDebugFilterChange() {
        if (this.currentComparison && this.currentComparison.metricComparisons) {
            this.displayResults();
            // Also update the file list table with the new filtering
            this.displayFileList(this.getFilteredComparisons());
        }
    }

    showDebugInfo() {
        const modal = document.createElement('div');
        modal.className = 'timeline-modal-backdrop';
        modal.onclick = () => modal.remove();
        
        modal.innerHTML = `
            <div class="timeline-modal" onclick="event.stopPropagation()">
                <div class="timeline-modal-header">
                    <h3>Debug Sections Information</h3>
                    <button class="timeline-modal-close" onclick="this.closest('.timeline-modal-backdrop').remove()">×</button>
                </div>
                <div class="timeline-modal-body" style="max-height: 70vh; overflow-y: auto;">
                    <p><strong>Debug sections</strong> are used during development and debugging but are not needed in runtime builds. They typically have <code>vmsize=0</code> (not loaded into memory).</p>
                    
                    <h4>Debug/Debug-only sections:</h4>
                    <ul style="line-height: 1.6; margin: 10px 0;">
                        <li><strong>[section .debug_loc]</strong> — DWARF location lists (where variables live over code ranges). vmsize=0, debug-only.</li>
                        <li><strong>[section .debug_ranges]</strong> — DWARF range lists (code address ranges). vmsize=0, debug-only.</li>
                        <li><strong>[section .debug_str]</strong> — DWARF string pool. vmsize=0, debug-only.</li>
                        <li><strong>[section .debug_frame]</strong> — DWARF call frame info (CFI) for unwinding in debuggers. vmsize=0, debug-only (distinct from .eh_frame).</li>
                        <li><strong>[section .debug_abbrev]</strong> — DWARF abbreviation table used by .debug_info. vmsize=0, debug-only.</li>
                        <li><strong>[section .symtab]</strong> — Full ELF symbol table (used by linkers/debuggers; stripped in release). vmsize=0, debug/metadata.</li>
                        <li><strong>[section .strtab]</strong> — String table for .symtab. vmsize=0, debug/metadata.</li>
                        <li><strong>[section .shstrtab]</strong> — Section-name strings (tooling metadata). vmsize=0, safe to strip from shipped builds.</li>
                        <li><strong>[section .comment]</strong> — Compiler/toolchain notes. vmsize=0, not needed at runtime.</li>
                    </ul>
                    
                    <p><em>Note: This filtering option is only available for Android platforms where debug sections are commonly present.</em></p>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    isDebugSection(filename) {
        const debugSections = [
            '[section .debug_loc]',
            '[section .debug_ranges]', 
            '[section .debug_str]',
            '[section .debug_frame]',
            '[section .debug_abbrev]',
            '[section .symtab]',
            '[section .strtab]',
            '[section .shstrtab]',
            '[section .comment]'
        ];
        
        return debugSections.some(section => filename.includes(section));
    }
    
    handleUrlParameters() {
        const urlParams = new URLSearchParams(window.location.search);
        const platform = urlParams.get('platform');
        const fromVersion = urlParams.get('from');
        const toVersion = urlParams.get('to');
        
        if (platform && fromVersion && toVersion) {
            // Store these for later use when analysis index is loaded
            this.urlParams = { platform, fromVersion, toVersion };
        }
    }
    
    applyUrlParameters() {
        if (!this.urlParams || !this.analysisIndex) return;
        
        const { platform, fromVersion, toVersion } = this.urlParams;
        
        // Check if the platform exists in the analysis index
        if (this.analysisIndex.platforms[platform]) {
            // Set platform
            this.elements.platformSelect.value = platform;
            this.onPlatformChange();
            
            // Wait a bit for platform change to populate versions, then set versions
            setTimeout(() => {
                if (this.elements.version1Select.querySelector(`option[value="${fromVersion}"]`)) {
                    this.elements.version1Select.value = fromVersion;
                    this.onVersion1Change();
                }
                
                setTimeout(() => {
                    if (this.elements.version2Select.querySelector(`option[value="${toVersion}"]`)) {
                        this.elements.version2Select.value = toVersion;
                        this.onVersionChange();
                    }
                }, 100);
            }, 100);
            
            // Clear URL params after applying
            this.urlParams = null;
        }
    }

    setStatus(message, type = 'info') {
        this.elements.status.innerHTML = `<p>${message}</p>`;
        this.elements.status.className = `status ${type}`;
    }
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.defoldApp = new DefoldSizeAnalyzer();
});