# Defold Size Analyzer

A comprehensive tool for analyzing and comparing Defold component sizes across versions. The analyzer supports both native engine binaries and Java tooling (bob.jar) analysis with interactive visualizations and dashboard overview.

## Overview

The Defold Size Analyzer consists of three main components:
1. **Data Collection Pipeline** - Automated analysis and CSV generation
2. **Dashboard** - High-level overview with size evolution charts
3. **Size Analyzer** - Detailed comparison and analysis tools

---

## Data Collection Pipeline

### 1. Analysis Script (`analyze_builds.py`)

The Python script automates the download and analysis of Defold components across versions.

#### Supported Platforms:
- **Native Binaries**: `arm64-android` (libdmengine_release.so)
- **Java Tooling**: `bob.jar` (editor/build tools)

#### Data Sources:
- Downloads components from Defold's archive: `http://d.defold.com/archive/{sha1}/`
- Uses `releases.json` to determine available versions and SHA1 hashes
- Processes versions from 1.9.0 onwards

#### Analysis Methods:

**Native Binary Analysis (using Bloaty)**
```bash
bloaty -d compileunits --demangle=full -n 0 binary.so --csv
```
- **Tool**: [Google Bloaty](https://github.com/google/bloaty) - Binary size analysis tool
- **Documentation**: [Bloaty Usage Guide](https://github.com/google/bloaty/blob/main/doc/using.md)
- **Output**: `compileunits,vmsize,filesize`
- **vmsize**: Virtual memory size (loaded into memory)
- **filesize**: File size on disk
- **compileunits**: Source file/compilation unit names

**JAR Analysis (using Python zipfile)**
```python
with zipfile.ZipFile(jar_path, 'r') as zf:
    for info in zf.infolist():
        # Extract: filename, compressed_size, uncompressed_size
```
- **Output**: `filename,compressed,uncompressed`
- **compressed**: Size of entry in JAR (compressed)
- **uncompressed**: Original size of entry
- **filename**: Path within JAR file

#### Generated Files:
```
size-analyzer/
├── analysis_index.json     # Platform and version metadata
├── arm64-android/          # Native binary analysis
│   ├── 1.9.0.csv
│   ├── 1.9.1.csv
│   └── ...
└── bob.jar/               # Java tooling analysis
    ├── 1.9.0.csv
    ├── 1.9.1.csv
    └── ...
```

#### Running Analysis:
```bash
python3 analyze_builds.py
```

The script will:
1. Read `releases.json` for version information
2. Download and analyze each component for each version
3. Generate CSV files with size data
4. Update `analysis_index.json` with available platforms/versions
5. Clean up temporary downloaded files

---

## Dashboard

### 1. Overview Charts

The dashboard provides a high-level view of component size evolution across versions:

**Features:**
- **Bundle Size Chart**: Game bundle sizes across all supported platforms
- **Engine Size Chart**: Engine binary sizes across platforms  
- **Editor Size Chart**: Editor application sizes (desktop platforms)
- **Bob.jar Size Chart**: Build tool size evolution (macOS only)

**Interactive Elements:**
- **Version Dropdowns**: Select starting version for each chart
- **Legend Controls**: 
  - Click legend items to toggle platforms on/off
  - Alt+click legend items to isolate single platform
- **Chart Navigation**: Click any data point to open detailed analysis

### 2. Cross-Navigation

**Dashboard → Size Analyzer Integration:**
- Click any dot on dashboard charts to open size-analyzer
- Automatically selects the correct platform
- Pre-fills "from" version (previous) and "to" version (clicked)
- Opens in new tab for seamless workflow

**Supported Platforms:**
- `arm64-ios`, `arm64-android`, `armv7-android`
- `x86_64-macos`, `x86_64-linux`, `x86-win32`, `x86_64-win32`, `arm64-macos`
- `js-web`, `wasm-web`
- `bob.jar` (special handling for build tools)

**Files:**
- `index.html` - Dashboard interface
- `js/dashboard.js` - Chart rendering and interaction logic
- `css/dashboard.css` - Dashboard-specific styling

---

## Size Analyzer (Detailed View)

### 1. Architecture

The viewer is a client-side web application with no server dependencies:

**Technologies:**
- **Vanilla JavaScript** - No frameworks, pure ES6+
- **Plotly.js** - Interactive chart rendering
- **CSS3** - Modern responsive styling
- **Fetch API** - CSV data loading

**Files:**
- `index.html` - Main application interface
- `js/app.js` - Main application logic and state management
- `js/csv-parser.js` - CSV loading and data processing
- `js/plotly-histogram.js` - Chart rendering and interactions
- `css/style.css` - Visual styling and responsive design

### 2. Data-Driven Design

#### Dynamic Platform Detection:
The viewer automatically adapts to any CSV structure by reading headers:

**arm64-android format:**
```csv
compileunits,vmsize,filesize
src/dlib/array.cpp,2048,4096
```

**bob.jar format:**
```csv
filename,compressed,uncompressed
lib/android.jar,10299057,13989417
```

#### Tab Generation:
Tabs are automatically created based on available metrics:
- **Native Binary**: "File Size" and "VM Size" tabs
- **JAR Files**: "Compressed" and "Uncompressed" tabs
- **Future Formats**: Automatically supported by reading CSV headers

### 3. Core Features

#### Version Selection Logic:
- **Baseline Dropdown**: All versions except the latest (prevents impossible comparisons)
- **Compare Dropdown**: Only versions newer than selected baseline
- **Smart Defaults**: Automatically selects (latest-1) vs (latest) on load
- **Preservation**: Maintains selections when switching platforms if versions exist

#### Interactive Visualization:
- **Horizontal Bar Charts**: Files sorted by change magnitude
- **Color Coding**: Red (increased), Green (decreased)
- **Threshold Filtering**: Dynamic range based on actual data
- **Timeline Modal**: Click any bar to see version-by-version evolution

#### Data Processing Pipeline:
```javascript
1. CSV Loading → CSVParser.loadCSV()
2. Header Detection → getMetricsFromHeaders()
3. Tab Creation → createDynamicTabs()
4. Data Processing → processDataByMetric()
5. Visualization → PlotlyHistogramChart.render()
```

### 4. Advanced Features

#### Debug Section Filtering (Android):
- Automatically detects Android platforms
- Shows checkbox to hide debug-only sections
- Filters sections like `.debug_str`, `.symtab`, etc.
- Includes informational modal explaining debug sections

#### Platform-Specific Adaptations:
- **File Path Normalization**: Handles `../src/` vs `src/` inconsistencies
- **Dynamic Filename Columns**: `compileunits` vs `filename`
- **Metric-Specific Colors**: Different colors for different metrics
- **Timeline Data**: Adapts to platform-specific CSV formats

#### Performance Optimizations:
- **CSV Caching**: Prevents redundant network requests
- **Lazy Loading**: Only loads data when needed
- **Efficient Filtering**: Client-side processing with smart algorithms
- **Responsive UI**: Smooth interactions even with large datasets

### 5. User Interface

#### Main Interface:
1. **Platform Selection**: Choose between arm64-android, bob.jar, etc.
2. **Version Selection**: Smart dropdowns with validation
3. **Metric Tabs**: Dynamic tabs based on available data
4. **Threshold Control**: Filter by change magnitude
5. **Chart Visualization**: Interactive horizontal bar chart
6. **Data Table**: Detailed file list with filtering options

#### Timeline Modal:
- **Triggered**: Click any bar in the main chart
- **Content**: Line chart showing file evolution across all intermediate versions
- **Data**: Cumulative view from baseline to compare version
- **Interaction**: Hover for details, responsive design

#### URL Parameter Support:
- **Cross-navigation**: Supports platform, from, and to version parameters
- **Deep linking**: `size-analyzer/?platform=arm64-android&from=1.10.3&to=1.10.4`
- **Dashboard integration**: Automatically applied when navigating from dashboard

#### Responsive Design:
- **Desktop**: Full-featured interface with side-by-side layouts
- **Tablet**: Stacked layouts with touch-friendly controls
- **Mobile**: Simplified interface with collapsible sections

---

## Usage Examples

### Dashboard Workflow:
1. Open dashboard (`index.html`) for overview of all components
2. Use version dropdowns to focus on specific time ranges
3. Use legend controls to filter platforms:
   - Click to toggle platform visibility
   - Alt+click to show only one platform
4. Click any data point to dive into detailed analysis
5. Size analyzer opens with pre-selected comparison

### Comparing Engine Sizes:
1. Select "arm64-android" platform (or navigate from dashboard)
2. Choose baseline version (e.g., 1.10.3)
3. Choose compare version (e.g., 1.10.4)
4. Switch between "File Size" and "VM Size" tabs
5. Adjust threshold to focus on significant changes
6. Click bars to see detailed timeline evolution

### Analyzing JAR Components:
1. Select "bob.jar" platform  
2. Choose version range for comparison
3. Switch between "Compressed" and "Uncompressed" tabs
4. Identify which JAR entries contribute most to size changes
5. Use timeline view to understand growth patterns

### Debug Analysis (Android):
1. Select arm64-android platform
2. Check "Hide debug sections" to focus on runtime code
3. Click info button to understand debug section types
4. Compare with/without debug sections to understand overhead

---

## Technical Details

### CSV Format Requirements:
- **First column**: Must be filename/path (any name containing "filename" or "compileunits")
- **Other columns**: Numeric size metrics (any names)
- **Headers**: Used to generate tab names automatically
- **Encoding**: UTF-8 with proper CSV escaping

### Browser Compatibility:
- **Modern browsers**: Chrome 80+, Firefox 75+, Safari 13+, Edge 80+
- **Features used**: ES6 modules, Fetch API, CSS Grid, Flexbox
- **No IE support**: Uses modern JavaScript features

### Performance Characteristics:
- **Data loading**: ~100ms per CSV file (cached after first load)
- **Processing**: <50ms for datasets up to 10,000 files
- **Rendering**: <200ms for charts with 1,000+ bars
- **Memory usage**: ~5MB for typical datasets

### Extensibility:
The tool is designed to handle new platforms automatically:
1. Add CSV files in new platform directory
2. Update `analysis_index.json` with platform info
3. Add platform to dashboard CSV reports (bundle_report.csv, engine_report.csv, etc.)
4. Dashboard and size analyzer automatically detect and support new format
5. No code changes required for new metrics or platforms

### Cross-Navigation:
**URL Parameter Flow:**
```
Dashboard Click → Generate URL → Open Size Analyzer → Parse Parameters → Apply Selection
```

**Data Flow:**
```
CSV Reports → Dashboard Charts → User Click → URL Generation → Size Analyzer → Detailed Analysis
```

**Supported URL Parameters:**
- `platform`: Platform key (e.g., arm64-android, bob.jar)
- `from`: Baseline version for comparison
- `to`: Target version for comparison