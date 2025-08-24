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
- **Native Binaries**: `arm64-android`, `armv7-android`, `arm64-ios`, `x86_64-macos`, `arm64-macos` (libdmengine_release.so)
- **Java Tooling**: `bob.jar` (editor/build tools)
- **Editor Applications**: `editor-win32`, `editor-x86_64-linux`, `editor-x86_64-macos`, `editor-arm64-macos` (complete editor packages)

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

**Editor Analysis (Combined Approach)**
```python
# Combines JAR analysis, JDK grouping, and file analysis
# - JAR contents analyzed individually with compression ratios
# - JDK folder grouped as single "JDK" entity
# - Other files analyzed individually (compressed == uncompressed)
# - Library grouping applied to reduce complexity
```
- **Output**: `filename,compressed,uncompressed`
- **compressed**: Compressed size (for JARs) or file size (for other files)
- **uncompressed**: Uncompressed size (for JARs) or file size (for other files)
- **filename**: File path or grouped library name (e.g., `com/ibm/*.*`, `JDK`)

#### Generated Files:
```
size-analyzer/
├── analysis_index.json     # Platform and version metadata
├── arm64-android/          # Native binary analysis
│   ├── 1.9.0.csv
│   ├── 1.9.1.csv
│   └── ...
├── bob.jar/               # Java tooling analysis
│   ├── 1.9.0.csv
│   ├── 1.9.1.csv
│   └── ...
└── editor-*/              # Editor analysis (all platforms)
    ├── 1.10.3.csv
    ├── 1.10.4.csv
    └── ...
```

#### Running Analysis:
```bash
# Full analysis (all platforms, all versions)
python3 analyze_builds.py

# Test mode (single platform, latest version only)
python3 analyze_builds.py --test editor  # Test editor analysis
python3 analyze_builds.py --test bob     # Test bob.jar analysis
python3 analyze_builds.py --test ios     # Test iOS engine analysis
```

The script will:
1. Read `releases.json` for version information
2. Download and analyze each component for each version
3. Generate CSV files with size data
4. Apply library grouping for editor analysis (reduces ~76,000 entries to ~5,500)
5. Update `analysis_index.json` with available platforms/versions
6. Clean up temporary downloaded files

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
- `editor-*` platforms (automatic mapping from dashboard to size-analyzer)

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

**editor format (with library grouping):**
```csv
filename,compressed,uncompressed
jfxwebkit.dll,31852784,83512832
JDK,58083658,58083658
com/ibm/*.*,11528031,27028277
com/sun/*.*,8886096,21765809
clojure/*.*,6990823,15500531
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
- **Color Coding**: Red (increased), Green (decreased) with metric-specific colors
- **Threshold Filtering**: Dynamic range based on actual data
- **Timeline Modal**: Click any bar to see version-by-version evolution
- **Pan Navigation**: Charts support panning but prevent zoom in/out for consistent scale
- **External Titles**: Chart titles displayed outside Plotly area for better mobile experience
- **Enhanced Hover Areas**: Full-row hover detection with subtle gray overlays for easier interaction
- **Cursor-Following Tooltips**: Tooltips positioned near cursor with Plotly-style yellow background
- **File Name Tooltips**: Hover over long file names (chart y-axis or table) to see full paths

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
- **Chart Optimization**: Fixed axis ranges prevent expensive zoom calculations
- **Mobile Performance**: Reduced chart complexity and disabled zoom for better touch performance

### 5. User Interface

#### Main Interface:
1. **Platform Selection**: Choose between arm64-android, bob.jar, etc.
2. **Version Selection**: Smart dropdowns with validation
3. **Metric Tabs**: Dynamic tabs based on available data
4. **Threshold Control**: Filter by change magnitude
5. **Chart Info**: Dynamic title showing comparison details above chart
6. **Chart Visualization**: Interactive horizontal bar chart with pan-only navigation
7. **Data Table**: Detailed file list with filtering options

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
- **Desktop**: Full-featured interface with side-by-side layouts and standard chart margins
- **Tablet**: Stacked layouts with touch-friendly controls and adjusted chart spacing
- **Mobile**: Simplified interface with collapsible sections and mobile-optimized chart layouts
- **Dynamic Layout**: Charts automatically adjust margins and title positioning based on screen width
- **Touch-Friendly**: Disabled zoom gestures to prevent accidental UI disruption on mobile devices

---

## Recent Improvements

### Editor Analysis Integration (v20):
- **Complete Editor Analysis**: Added support for analyzing Defold editor packages across all platforms
- **Combined Analysis Approach**: JAR contents + individual files + JDK grouping in unified CSV format
- **Intelligent Library Grouping**: Reduced editor analysis from ~76,000 entries to ~5,500 (92% reduction)
- **Test Mode**: Added `--test` flag for quick single-platform validation during development
- **Dashboard Integration**: Automatic platform name mapping from dashboard to size-analyzer URLs

### Enhanced User Experience (v20):
- **Full-Row Hover Detection**: Click/hover anywhere across chart rows, not just thin bars
- **Cursor-Following Tooltips**: Tooltips now position near cursor instead of fixed right-side placement
- **File Name Tooltips**: Hover over truncated file names (y-axis labels and table) to see complete paths
- **Smart Tooltip Styling**: Maintained Plotly-style yellow background with dynamic width adaptation
- **Subtle Visual Cues**: Light gray overlay bars indicate hoverable areas without interfering with data

### Mobile & Touch Optimization (v19):
- **Responsive Chart Titles**: Moved chart titles outside Plotly area to prevent mobile overlap with modebar
- **Zoom Restrictions**: Disabled zoom in/out to maintain consistent scale and prevent accidental gestures
- **Touch Navigation**: Enabled pan-only interaction for better mobile experience
- **Dynamic Margins**: Charts automatically adjust spacing based on screen width (≤768px detection)
- **Simplified Controls**: Streamlined arrow labels ("← smaller" / "bigger →") for mobile readability

### Error Handling & Stability:
- **Version Parsing**: Fixed `version.split is not a function` error in timeline modal
- **Type Safety**: Added string conversion safeguards for version processing
- **Data Validation**: Improved handling of analysis_index.json structure changes
- **Cross-Platform URL Mapping**: Automatic conversion between dashboard platform keys and size-analyzer directories

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

### Analyzing Editor Components:
1. Select any "editor-*" platform (win32, linux, macos)
2. Choose version range for comparison (editor analysis starts from 1.10.3)
3. Switch between "Compressed" and "Uncompressed" tabs
4. Analyze grouped libraries (com/ibm/*.*, com/sun/*.*, etc.) and individual components
5. Compare JDK overhead vs application code vs bundled libraries
6. Use hover tooltips to see full component names for grouped entries

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
- **Features used**: ES6 modules, Fetch API, CSS Grid, Flexbox, window.innerWidth detection
- **Mobile browsers**: iOS Safari 13+, Android Chrome 80+, mobile-optimized interactions
- **No IE support**: Uses modern JavaScript features and responsive design

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