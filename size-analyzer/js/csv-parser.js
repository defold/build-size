// CSV Parser and Data Processing Module

class CSVParser {
    // Cache for loaded CSV data to avoid repeated requests
    static csvCache = new Map();
    
    static async parseCSV(text) {
        const lines = text.trim().split('\n');
        const headers = lines[0].split(',');
        const data = [];
        
        for (let i = 1; i < lines.length; i++) {
            const values = this.parseCSVLine(lines[i]);
            if (values.length === headers.length) {
                const row = {};
                headers.forEach((header, index) => {
                    row[header.trim()] = values[index].trim();
                });
                data.push(row);
            }
        }
        
        return data;
    }
    
    static getMetricsFromHeaders(headers) {
        // Get metrics from CSV headers, excluding the filename column
        const filenameColumns = ['compileunits', 'filename'];
        return headers
            .map(h => h.trim())
            .filter(header => !filenameColumns.includes(header.toLowerCase()));
    }
    
    static getFilenameColumn(headers) {
        // Find the filename column
        const filenameColumns = ['compileunits', 'filename'];
        return headers
            .map(h => h.trim())
            .find(header => filenameColumns.includes(header.toLowerCase())) || headers[0];
    }
    
    static parseCSVLine(line) {
        const result = [];
        let current = '';
        let inQuotes = false;
        
        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            
            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                result.push(current);
                current = '';
            } else {
                current += char;
            }
        }
        
        result.push(current);
        return result;
    }
    
    static async loadCSV(url) {
        // Check cache first
        if (this.csvCache.has(url)) {
            return this.csvCache.get(url);
        }
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const text = await response.text();
            const data = await this.parseCSV(text);
            
            // Cache the parsed data
            this.csvCache.set(url, data);
            return data;
        } catch (error) {
            console.error('Error loading CSV:', url, error);
            throw error;
        }
    }
    
    static clearCache() {
        this.csvCache.clear();
    }
}

class DataProcessor {
    static normalizeFilePath(filePath) {
        if (!filePath) return filePath;
        
        // Remove leading ../ and ./ prefixes
        let normalized = filePath.replace(/^(\.\.\/)+/, '').replace(/^\.\//, '');
        
        // Handle cases where the path might start with different variations
        // Also remove any leading / if present
        normalized = normalized.replace(/^\/+/, '');
        
        return normalized;
    }

    static parseVersion(version) {
        return version.split('.').map(Number);
    }

    static compareVersions(v1, v2) {
        const a = this.parseVersion(v1);
        const b = this.parseVersion(v2);
        
        for (let i = 0; i < Math.max(a.length, b.length); i++) {
            const numA = a[i] || 0;
            const numB = b[i] || 0;
            if (numA !== numB) {
                return numA - numB;
            }
        }
        return 0;
    }

    static getVersionsInRange(allVersions, startVersion, endVersion) {
        return allVersions
            .filter(version => {
                return this.compareVersions(version, startVersion) >= 0 && 
                       this.compareVersions(version, endVersion) <= 0;
            })
            .sort(this.compareVersions.bind(this));
    }

    static async getFileTimeline(fileName, platform, startVersion, endVersion, metricType) {
        // Get analysis index to determine available versions
        const analysisResponse = await fetch('analysis_index.json');
        const analysisIndex = await analysisResponse.json();
        const allVersions = analysisIndex.platforms[platform].versions;
        
        // Get versions in range
        const versionsInRange = this.getVersionsInRange(allVersions, startVersion, endVersion);
        
        const timeline = [];
        let filenameColumn = 'compileunits'; // default
        
        // Load data for each version
        for (const version of versionsInRange) {
            try {
                const csvData = await CSVParser.loadCSV(`${platform}/${version}.csv`);
                
                // Detect filename column from first version's data
                if (csvData.length > 0 && filenameColumn === 'compileunits') {
                    const headers = Object.keys(csvData[0]);
                    filenameColumn = CSVParser.getFilenameColumn(headers);
                }
                
                // Find the file in this version's data
                const normalizedFileName = DataProcessor.normalizeFilePath(fileName);
                const fileRow = csvData.find(row => 
                    DataProcessor.normalizeFilePath(row[filenameColumn]) === normalizedFileName
                );
                
                const size = fileRow ? (parseInt(fileRow[metricType]) || 0) : 0;
                
                timeline.push({
                    version: version,
                    size: size,
                    exists: !!fileRow
                });
                
            } catch (error) {
                console.warn(`Failed to load data for version ${version}:`, error);
                // Add zero size for missing versions
                timeline.push({
                    version: version,
                    size: 0,
                    exists: false
                });
            }
        }
        
        return timeline;
    }

    static processDataByMetric(data1, data2, metricType, changeThreshold = 50, filenameColumn = 'compileunits') {
        // Process data for a specific metric (dynamic based on CSV headers)
        
        const data1Map = new Map();
        const data2Map = new Map();
        
        // Process first dataset
        data1.forEach((row, index) => {
            const compileUnit = this.normalizeFilePath(row[filenameColumn]);
            const metricValue = parseInt(row[metricType]) || 0;
            
            data1Map.set(compileUnit, {
                size: metricValue,
                compileUnit,
                originalPath: row[filenameColumn]
            });
        });
        
        // Process second dataset
        data2.forEach(row => {
            const compileUnit = this.normalizeFilePath(row[filenameColumn]);
            const metricValue = parseInt(row[metricType]) || 0;
            
            data2Map.set(compileUnit, {
                size: metricValue,
                compileUnit,
                originalPath: row[filenameColumn]
            });
        });
        
        // Detect file moves before processing comparisons
        const moveDetection = this.detectFileMoves(data1Map, data2Map);
        const { mergedData1, mergedData2 } = moveDetection;
        
        // Compare and create comparison data using merged data (after move detection)
        const comparisons = [];
        const allKeys = new Set([...mergedData1.keys(), ...mergedData2.keys()]);
        
        allKeys.forEach(compileUnit => {
            const item1 = mergedData1.get(compileUnit);
            const item2 = mergedData2.get(compileUnit);
            
            const size1 = item1 ? item1.size : 0;
            const size2 = item2 ? item2.size : 0;
            const difference = size2 - size1;
            const percentChange = size1 > 0 ? ((difference / size1) * 100) : (size2 > 0 ? 100 : 0);
            
            let changeType = 'unchanged';
            if (Math.abs(difference) > changeThreshold) {
                changeType = difference > 0 ? 'increased' : 'decreased';
            }
            
            // Add move detection info if applicable
            const moveInfo = item1?.moveInfo || item2?.moveInfo;
            
            comparisons.push({
                compileUnit,
                size1,
                size2,
                difference,
                percentChange,
                changeType,
                metricType,
                ...(moveInfo && { 
                    isMoved: true, 
                    moveInfo: moveInfo,
                    displayName: moveInfo.displayName 
                })
            });
        });
        
        // Sort by absolute difference (largest changes first)
        comparisons.sort((a, b) => Math.abs(b.difference) - Math.abs(a.difference));
        
        
        return comparisons;
    }

    static detectFileMoves(data1Map, data2Map) {
        // Algorithm to detect file moves by comparing basenames and sizes
        // Returns merged data maps where moves are consolidated as single entities
        
        const mergedData1 = new Map(data1Map);
        const mergedData2 = new Map(data2Map);
        const moveInfo = new Map();
        
        // Get files that are only in data1 (potentially moved out)
        const onlyInData1 = [];
        for (const [key, value] of data1Map) {
            if (!data2Map.has(key)) {
                onlyInData1.push({ key, value });
            }
        }
        
        // Get files that are only in data2 (potentially moved in)
        const onlyInData2 = [];
        for (const [key, value] of data2Map) {
            if (!data1Map.has(key)) {
                onlyInData2.push({ key, value });
            }
        }
        
        // Try to match files by basename and similar size
        const matchedMoves = [];
        
        for (const item1 of onlyInData1) {
            const basename1 = this.getBasename(item1.key);
            const size1 = item1.value.size;
            
            for (const item2 of onlyInData2) {
                const basename2 = this.getBasename(item2.key);
                const size2 = item2.value.size;
                
                // Check if basenames match and sizes are similar (within 10% tolerance)
                if (basename1 === basename2 && this.sizesAreSimilar(size1, size2)) {
                    matchedMoves.push({
                        oldKey: item1.key,
                        newKey: item2.key,
                        oldValue: item1.value,
                        newValue: item2.value,
                        basename: basename1
                    });
                    break; // Move to next item1 after finding a match
                }
            }
        }
        
        // Process matched moves
        for (const move of matchedMoves) {
            // Use the new path as the canonical key
            const canonicalKey = move.newKey;
            
            // Create move info
            const moveDetails = {
                oldPath: move.oldValue.originalPath,
                newPath: move.newValue.originalPath,
                displayName: `${move.basename} (moved from ${this.getDirectoryPath(move.oldKey)} to ${this.getDirectoryPath(move.newKey)})`
            };
            
            // Remove the individual entries
            mergedData1.delete(move.oldKey);
            mergedData2.delete(move.newKey);
            
            // Add the moved file with combined info
            mergedData1.set(canonicalKey, {
                ...move.oldValue,
                moveInfo: moveDetails
            });
            
            mergedData2.set(canonicalKey, {
                ...move.newValue,
                moveInfo: moveDetails
            });
        }
        
        return { mergedData1, mergedData2, moveInfo: matchedMoves };
    }
    
    static getBasename(filePath) {
        // Extract the basename (filename without directory path)
        const parts = filePath.split('/');
        return parts[parts.length - 1];
    }
    
    static getDirectoryPath(filePath) {
        // Extract the directory path (everything except the basename)
        const parts = filePath.split('/');
        return parts.slice(0, -1).join('/') || '/';
    }
    
    static sizesAreSimilar(size1, size2, tolerance = 0.1) {
        // Check if sizes are similar within tolerance percentage
        if (size1 === 0 && size2 === 0) return true;
        if (size1 === 0 || size2 === 0) return false;
        
        const diff = Math.abs(size1 - size2);
        const average = (size1 + size2) / 2;
        return (diff / average) <= tolerance;
    }

    static processData(data1, data2, includeVMSize = true, includeFileSize = true, changeThreshold = 50) {
        // Create maps for fast lookup
        const data1Map = new Map();
        const data2Map = new Map();
        
        // Process first dataset
        data1.forEach(row => {
            const compileUnit = this.normalizeFilePath(row.compileunits);
            const vmsize = parseInt(row.vmsize) || 0;
            const filesize = parseInt(row.filesize) || 0;
            
            let totalSize = 0;
            if (includeVMSize) totalSize += vmsize;
            if (includeFileSize) totalSize += filesize;
            
            data1Map.set(compileUnit, {
                vmsize,
                filesize,
                totalSize,
                compileUnit
            });
        });
        
        // Process second dataset
        data2.forEach(row => {
            const compileUnit = this.normalizeFilePath(row.compileunits);
            const vmsize = parseInt(row.vmsize) || 0;
            const filesize = parseInt(row.filesize) || 0;
            
            let totalSize = 0;
            if (includeVMSize) totalSize += vmsize;
            if (includeFileSize) totalSize += filesize;
            
            data2Map.set(compileUnit, {
                vmsize,
                filesize,
                totalSize,
                compileUnit
            });
        });
        
        // Compare and create comparison data
        const comparisons = [];
        const allKeys = new Set([...data1Map.keys(), ...data2Map.keys()]);
        
        allKeys.forEach(compileUnit => {
            const item1 = data1Map.get(compileUnit);
            const item2 = data2Map.get(compileUnit);
            
            const size1 = item1 ? item1.totalSize : 0;
            const size2 = item2 ? item2.totalSize : 0;
            const difference = size2 - size1;
            const percentChange = size1 > 0 ? ((difference / size1) * 100) : (size2 > 0 ? 100 : 0);
            
            let changeType = 'unchanged';
            if (Math.abs(difference) > changeThreshold) {
                changeType = difference > 0 ? 'increased' : 'decreased';
            }
            
            comparisons.push({
                compileUnit,
                size1,
                size2,
                difference,
                percentChange,
                changeType,
                vmsize1: item1 ? item1.vmsize : 0,
                filesize1: item1 ? item1.filesize : 0,
                vmsize2: item2 ? item2.vmsize : 0,
                filesize2: item2 ? item2.filesize : 0
            });
        });
        
        // Sort by absolute difference (largest changes first)
        comparisons.sort((a, b) => Math.abs(b.difference) - Math.abs(a.difference));
        
        return comparisons;
    }
    
    static generateSummary(comparisons) {
        const summary = {
            totalFiles: comparisons.length,
            unchanged: 0,
            increased: 0,
            decreased: 0,
            totalSizeChange: 0,
            largestIncrease: null,
            largestDecrease: null
        };
        
        comparisons.forEach(comp => {
            summary.totalSizeChange += comp.difference;
            
            switch (comp.changeType) {
                case 'unchanged':
                    summary.unchanged++;
                    break;
                case 'increased':
                    summary.increased++;
                    if (!summary.largestIncrease || comp.difference > summary.largestIncrease.difference) {
                        summary.largestIncrease = comp;
                    }
                    break;
                case 'decreased':
                    summary.decreased++;
                    if (!summary.largestDecrease || comp.difference < summary.largestDecrease.difference) {
                        summary.largestDecrease = comp;
                    }
                    break;
            }
        });
        
        return summary;
    }
    
    static formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
        
        return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
    }
    
    static formatNumber(num) {
        return num.toLocaleString();
    }
    
    static formatPercentage(percent) {
        return (percent >= 0 ? '+' : '') + percent.toFixed(1) + '%';
    }
    
    static prepareForVisualization(comparisons, hideUnchanged = false) {
        let filteredComparisons = comparisons;
        
        if (hideUnchanged) {
            filteredComparisons = comparisons.filter(comp => comp.changeType !== 'unchanged');
        }
        
        // Group by change type for better visualization
        const groups = {
            unchanged: filteredComparisons.filter(comp => comp.changeType === 'unchanged'),
            decreased: filteredComparisons.filter(comp => comp.changeType === 'decreased'),
            increased: filteredComparisons.filter(comp => comp.changeType === 'increased')
        };
        
        return {
            all: filteredComparisons,
            groups: groups,
            maxSize: Math.max(...filteredComparisons.map(comp => Math.max(comp.size1, comp.size2)))
        };
    }
}