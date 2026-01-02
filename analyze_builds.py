#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import shutil
import zipfile
import csv
import argparse
from pathlib import Path
from collections import defaultdict

def parse_version(version_str):
    """Parse version string into tuple for comparison"""
    base = version_str
    suffix = None
    if '-' in version_str:
        base, suffix = version_str.split('-', 1)
        suffix = suffix.lower()
    tokens = base.split('.')
    ints = list(map(int, tokens))
    stage_order = 2
    if suffix == 'alpha':
        stage_order = 0
    elif suffix == 'beta':
        stage_order = 1
    return (ints[0], ints[1], ints[2], stage_order)

def read_releases(path):
    """Read releases from JSON file"""
    with open(path, 'rb') as f:
        d = json.loads(f.read())
        return d
    return {}

def get_channel_from_version(version):
    if not version or '-' not in version:
        return None
    suffix = version.split('-', 1)[1].lower()
    if suffix in ("alpha", "beta"):
        return suffix
    return None

def build_bob_urls(sha1, channel):
    if channel in ("alpha", "beta"):
        return [
            f"http://d.defold.com/archive/{channel}/{sha1}/bob/bob.jar",
            f"http://d.defold.com/archive/{channel}/{sha1}/{channel}/bob/bob.jar",
            f"http://d.defold.com/archive/{sha1}/bob/bob.jar",
        ]
    return [
        f"http://d.defold.com/archive/stable/{sha1}/bob/bob.jar",
        f"http://d.defold.com/archive/{sha1}/bob/bob.jar",
    ]

def build_editor_urls(sha1, channel, filename):
    if channel in ("alpha", "beta"):
        return [
            f"http://d.defold.com/archive/{channel}/{sha1}/{channel}/editor2/{filename}",
            f"http://d.defold.com/archive/{channel}/{sha1}/editor2/{filename}",
            f"http://d.defold.com/archive/{sha1}/editor-alpha/editor2/{filename}",
        ]
    return [
        f"http://d.defold.com/archive/{sha1}/editor-alpha/editor2/{filename}",
    ]

def build_engine_urls(sha1, channel, platform, filename):
    bases = []
    if channel in ("alpha", "beta"):
        bases.append(f"http://d.defold.com/archive/{channel}/{sha1}")
    bases.append(f"http://d.defold.com/archive/{sha1}")
    urls = []
    for base in bases:
        urls.append(f"{base}/engine/{platform}/{filename}")
    return urls

def build_engine_dsym_urls(sha1, channel, platform, filename):
    bases = []
    if channel in ("alpha", "beta"):
        bases.append(f"http://d.defold.com/archive/{channel}/{sha1}")
    bases.append(f"http://d.defold.com/archive/{sha1}")
    urls = []
    for base in bases:
        urls.append(f"{base}/engine/{platform}/{filename}.dSYM.zip")
    return urls

def download_with_fallback(urls, output_path):
    for url in urls:
        print(f"Downloading from {url}")
        try:
            urllib.request.urlretrieve(url, output_path)
            print(f"Downloaded to {output_path}")
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"Error downloading {url}: {e.code} {e.reason}")
                continue
            print(f"Error downloading {url}: {e.code} {e.reason}")
            return False
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False
    return False

def download_file(sha1, path, filename, output_path):
    """Download file from Defold archive (engine binary or bob.jar)"""
    url = f"http://d.defold.com/archive/{sha1}/{path}/{filename}"
    print(f"Downloading {filename} from {url}")
    
    try:
        urllib.request.urlretrieve(url, output_path)
        print(f"Downloaded to {output_path}")
        return True
    except urllib.error.HTTPError as e:
        print(f"Error downloading {url}: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def download_engine(sha1, version, platform, filename, output_path):
    """Download engine binary from Defold archive"""
    channel = get_channel_from_version(version)
    urls = build_engine_urls(sha1, channel, platform, filename)
    return download_with_fallback(urls, output_path)

def download_engine_dsym(sha1, version, platform, filename, output_path):
    """Download engine dSYM from Defold archive"""
    channel = get_channel_from_version(version)
    urls = build_engine_dsym_urls(sha1, channel, platform, filename)
    return download_with_fallback(urls, output_path)

def download_bob_jar(sha1, version, output_path):
    """Download bob.jar from Defold archive"""
    channel = get_channel_from_version(version)
    urls = build_bob_urls(sha1, channel)
    return download_with_fallback(urls, output_path)

def download_editor(sha1, version, platform, filename, output_path):
    """Download editor from Defold archive"""
    channel = get_channel_from_version(version)
    urls = build_editor_urls(sha1, channel, filename)
    return download_with_fallback(urls, output_path)

def apply_symbol_grouping(symbol_name):
    """
    Apply symbol grouping rules to compress similar symbols.
    Returns tuple: (group_name, is_grouped)
    """
    
    # Rule 1: C++ namespace - group by string before "::"
    if '::' in symbol_name:
        namespace = symbol_name.split('::')[0]
        return namespace, True
    
    # Rule 2: String between underscores (at least two underscores, not consecutive)
    # Find the first pair of non-consecutive underscores with content between them
    underscores = [i for i, char in enumerate(symbol_name) if char == '_']
    
    if len(underscores) >= 2:
        # Look for the first pair of underscores with content between them
        for i in range(len(underscores) - 1):
            first_underscore = underscores[i]
            second_underscore = underscores[i + 1]
            
            # Check if there's content between these underscores
            if second_underscore - first_underscore > 1:
                middle_part = symbol_name[first_underscore + 1:second_underscore]
                if middle_part:  # Not empty
                    return f"_{middle_part}_* (library)", True
    
    # Rule 3: Not grouped - keep individual
    return symbol_name, False

def compress_symbols_data(input_csv_path, output_csv_path):
    """
    Apply symbol compression to bloaty shortsymbols output.
    """
    
    groups = defaultdict(lambda: {'vmsize': 0, 'filesize': 0, 'count': 0})
    
    with open(input_csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            symbol_name = row['shortsymbols']
            vmsize = int(row['vmsize']) if row['vmsize'].isdigit() else 0
            filesize = int(row['filesize']) if row['filesize'].isdigit() else 0
            
            group_name, is_grouped = apply_symbol_grouping(symbol_name)
            
            groups[group_name]['vmsize'] += vmsize
            groups[group_name]['filesize'] += filesize
            groups[group_name]['count'] += 1
    
    # Sort by size
    sorted_groups = sorted(groups.items(), key=lambda x: x[1]['vmsize'], reverse=True)
    
    # Write output
    with open(output_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['symbol_group_name', 'vmsize', 'filesize'])
        
        for group_name, data in sorted_groups:
            writer.writerow([
                group_name,
                data['vmsize'],
                data['filesize']
            ])
    
    # Count grouped vs ungrouped for logging
    grouped_count = sum(1 for group_name, data in sorted_groups if data['count'] > 1)
    ungrouped_count = sum(1 for group_name, data in sorted_groups if data['count'] == 1)
    
    print(f"Symbol compression results: {len(sorted_groups)} total groups ({grouped_count} grouped, {ungrouped_count} individual)")
    return True

def run_bloaty_analysis(binary_path, output_csv_path, platform, debug_file_path=None):
    """Run bloaty analysis on the binary using shortsymbols mode with compression"""
    print(f"Running bloaty analysis on {binary_path}")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    
    try:
        # Use shortsymbols mode for all platforms to get symbol-level data
        analysis_mode = "shortsymbols"
        
        # Create temporary file for raw bloaty output
        temp_csv_path = output_csv_path + ".temp"
        
        # Run bloaty with the specified parameters
        cmd = [
            "bloaty", 
            "-d", analysis_mode, 
            "--demangle=full", 
            "-n", "0"
        ]
        
        # Add debug file for Apple platforms (dSYM)
        if debug_file_path:
            cmd.extend(["--debug-file", debug_file_path])
            print(f"Using debug file: {debug_file_path}")
        
        cmd.extend([binary_path, "--csv"])
        
        print(f"Using analysis mode: {analysis_mode}")
        
        # Run bloaty and save raw output to temp file
        with open(temp_csv_path, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            print(f"Raw bloaty analysis completed, applying symbol compression...")
            
            # Apply symbol compression to the raw output
            success = compress_symbols_data(temp_csv_path, output_csv_path)
            
            if success:
                # Clean up temp file
                os.remove(temp_csv_path)
                print(f"Compressed analysis saved to {output_csv_path}")
                return True
            else:
                print(f"Symbol compression failed")
                return False
        else:
            print(f"Bloaty analysis failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("Error: bloaty not found. Please install bloaty first.")
        return False
    except Exception as e:
        print(f"Error running bloaty: {e}")
        return False

def analyze_bob_jar(jar_path, output_csv_path):
    """Analyze bob.jar file and extract ZIP entry information"""
    print(f"Analyzing bob.jar: {jar_path}")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    
    try:
        entries = []
        
        with zipfile.ZipFile(jar_path, 'r') as zf:
            for info in zf.infolist():
                # Skip directories
                if info.is_dir():
                    continue
                
                entries.append({
                    'filename': info.filename,
                    'uncompressed': info.file_size,  # Uncompressed size
                    'compressed': info.compress_size  # Compressed size
                })
        
        # Sort by uncompressed size (descending)
        entries.sort(key=lambda x: x['uncompressed'], reverse=True)
        
        # Write to CSV
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            if entries:
                fieldnames = ['filename', 'compressed', 'uncompressed']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(entries)
                
                print(f"Bob.jar analysis saved to {output_csv_path} ({len(entries)} entries)")
                return True
            else:
                print(f"No entries found in {jar_path}")
                return False
                
    except zipfile.BadZipFile:
        print(f"Error: {jar_path} is not a valid ZIP file")
        return False
    except Exception as e:
        print(f"Error analyzing bob.jar: {e}")
        return False

def analyze_combined_editor(directory_path, output_csv_path):
    """Analyze editor combining jar contents, individual files (excluding jars), and JDK as single entity"""
    print(f"Analyzing combined editor contents in: {directory_path}")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    
    try:
        entries = {}  # Use dict to aggregate entries by filename
        jdk_total_size = 0
        directory = Path(directory_path)
        
        # Find jar files first
        jar_files = list(directory.rglob('*.jar'))
        main_jar = None
        if jar_files:
            # Use the largest jar file (likely the main editor jar)
            main_jar = max(jar_files, key=lambda x: x.stat().st_size)
        
        # Analyze jar contents if found
        if main_jar:
            try:
                with zipfile.ZipFile(str(main_jar), 'r') as zf:
                    for info in zf.infolist():
                        # Skip directories
                        if info.is_dir():
                            continue
                        
                        # Group class files and other library files
                        filename = info.filename
                        # Check for grouping patterns (not just .class files, but all files in these packages)
                        if filename.startswith('editor/') and filename.endswith('.class'):
                            # Group editor class files by string before first $
                            class_path = filename[7:]  # Remove 'editor/' prefix
                            if '$' in class_path:
                                group_name = 'editor/' + class_path.split('$')[0]
                            else:
                                # Remove .class extension for grouping
                                group_name = 'editor/' + class_path[:-6] if class_path.endswith('.class') else 'editor/' + class_path
                            filename = group_name
                        elif filename.startswith('clojure/'):
                            # All clojure classes go to "clojure/"
                            filename = 'clojure/*.*'
                        elif filename.startswith('com/ibm/'):
                            filename = 'com/ibm/*.*'
                        elif filename.startswith('com/sun/'):
                            filename = 'com/sun/*.*'
                        elif filename.startswith('com/jogamp/'):
                            filename = 'com/jogamp/*.*'
                        elif filename.startswith('com/google/protobuf/'):
                            filename = 'com/google/protobuf/*.*'
                        elif filename.startswith('com/dynamo/'):
                            filename = 'com/dynamo/*.*'
                        elif filename.startswith('com/amazonaws/'):
                            filename = 'com/amazonaws/*.*'
                        elif filename.startswith('com/fasterxml/jackson/'):
                            filename = 'com/fasterxml/jackson/*.*'
                        elif filename.startswith('com/github/benmanes/caffeine/'):
                            filename = 'com/github/benmanes/caffeine/*.*'
                        elif filename.startswith('com/defold/'):
                            filename = 'com/defold/*.*'
                        elif filename.startswith('com/jcraft/'):
                            filename = 'com/jcraft/*.*'
                        elif filename.startswith('ch/qos/'):
                            filename = 'ch/qos/*.*'
                        elif filename.startswith('org/apache/commons/'):
                            filename = 'org/apache/commons/*.*'
                        elif filename.startswith('org/apache/http/'):
                            filename = 'org/apache/http/*.*'
                        elif filename.startswith('org/antlr/'):
                            filename = 'org/antlr/*.*'
                        elif filename.startswith('org/eclipse/jgit/'):
                            filename = 'org/eclipse/jgit/*.*'
                        elif filename.startswith('org/eclipse/jetty/'):
                            filename = 'org/eclipse/jetty/*.*'
                        elif filename.startswith('org/codehaus/jackson/'):
                            filename = 'org/codehaus/jackson/*.*'
                        elif filename.startswith('org/joda/'):
                            filename = 'org/joda/*.*'
                        elif filename.startswith('org/luaj/'):
                            filename = 'org/luaj/*.*'
                        elif filename.startswith('org/checkerframework/'):
                            filename = 'org/checkerframework/*.*'
                        elif filename.startswith('org/yaml/snakeyaml/'):
                            filename = 'org/yaml/snakeyaml/*.*'
                        elif filename.startswith('org/snakeyaml/engine/'):
                            filename = 'org/snakeyaml/engine/*.*'
                        elif filename.startswith('org/stringtemplate/'):
                            filename = 'org/stringtemplate/*.*'
                        elif filename.startswith('org/jsoup/'):
                            filename = 'org/jsoup/*.*'
                        elif filename.startswith('org/commonmark/'):
                            filename = 'org/commonmark/*.*'
                        elif filename.startswith('org/msgpack/'):
                            filename = 'org/msgpack/*.*'
                        elif filename.startswith('org/openmali/'):
                            filename = 'org/openmali/*.*'
                        elif filename.startswith('org/jdom2/'):
                            filename = 'org/jdom2/*.*'
                        elif filename.startswith('javafx/'):
                            filename = 'javafx/*.*'
                        elif filename.startswith('cljfx/'):
                            filename = 'cljfx/*.*'
                        elif filename.startswith('jogamp/'):
                            filename = 'jogamp/*.*'
                        elif filename.startswith('javassist/'):
                            filename = 'javassist/*.*'
                        elif filename.startswith('schema/'):
                            filename = 'schema/*.*'
                        elif filename.startswith('reitit/'):
                            filename = 'reitit/*.*'
                        elif filename.startswith('cognitect/'):
                            filename = 'cognitect/*.*'
                        elif filename.startswith('META-INF/'):
                            filename = 'META-INF/*.*'
                        elif filename.startswith('internal/graph/'):
                            filename = 'internal/graph/*.*'
                        elif filename.startswith('welcome/'):
                            filename = 'welcome/*.*'
                        
                        # Aggregate entries by filename
                        if filename in entries:
                            entries[filename]['compressed'] += info.compress_size
                            entries[filename]['uncompressed'] += info.file_size
                        else:
                            entries[filename] = {
                                'filename': filename,
                                'compressed': info.compress_size,
                                'uncompressed': info.file_size
                            }
            except Exception as e:
                print(f"Warning: Could not analyze jar file {main_jar}: {e}")
        
        # Walk through all files in the directory recursively (excluding jar files)
        for file_path in directory.rglob('*'):
            # Skip directories and jar files
            if file_path.is_dir() or file_path.suffix == '.jar':
                continue
            
            try:
                file_size = file_path.stat().st_size
                relative_path = file_path.relative_to(directory)
                relative_path_str = str(relative_path)
                
                # Check if this is a JDK file (in packages/jdk-* folder)
                if '/packages/jdk-' in relative_path_str or '\\packages\\jdk-' in relative_path_str:
                    jdk_total_size += file_size
                else:
                    # Aggregate entries by filename
                    if relative_path_str in entries:
                        entries[relative_path_str]['compressed'] += file_size
                        entries[relative_path_str]['uncompressed'] += file_size
                    else:
                        entries[relative_path_str] = {
                            'filename': relative_path_str,
                            'compressed': file_size,
                            'uncompressed': file_size  # For non-jar files, compressed == uncompressed
                        }
            except (OSError, ValueError) as e:
                print(f"Warning: Could not analyze file {file_path}: {e}")
                continue
        
        # Add JDK as a single entity if there were JDK files
        if jdk_total_size > 0:
            entries['JDK'] = {
                'filename': 'JDK',
                'compressed': jdk_total_size,
                'uncompressed': jdk_total_size  # For JDK, compressed == uncompressed
            }
        
        # Convert dict to list and sort by uncompressed size (descending)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda x: x['uncompressed'], reverse=True)
        
        # Write to CSV
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            if entries_list:
                fieldnames = ['filename', 'compressed', 'uncompressed']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(entries_list)
                
                jdk_info = f" (JDK grouped: {jdk_total_size} bytes)" if jdk_total_size > 0 else ""
                jar_info = f" (JAR analyzed: {main_jar.name})" if main_jar else ""
                print(f"Combined editor analysis saved to {output_csv_path} ({len(entries_list)} entries{jdk_info}{jar_info})")
                return True
            else:
                print(f"No files found in {directory_path}")
                return False
                
    except Exception as e:
        print(f"Error analyzing combined editor: {e}")
        return False

def update_analysis_index(analysis_index_path, platform, version_data):
    """Update the analysis index JSON file with platform and available versions with SHA1"""
    # Read existing index or create new one
    if analysis_index_path.exists():
        with open(analysis_index_path, 'r') as f:
            index = json.load(f)
    else:
        index = {"platforms": {}}
    
    # Update platform data - version_data should be list of {"version": "x.y.z", "sha1": "..."}
    sorted_versions = sorted(version_data, key=lambda x: parse_version(x['version']))
    index["platforms"][platform] = {
        "versions": sorted_versions
    }
    
    # Write updated index
    with open(analysis_index_path, 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"Updated analysis index: {analysis_index_path}")

def run_test_mode(test_platform, releases):
    """Run test mode for a specific platform with latest version"""
    print(f"=== Test Mode: {test_platform} ===")
    
    # Get latest release by version number (find highest version)
    if not releases or 'releases' not in releases or not releases['releases']:
        print("No releases found")
        return
    
    # Find the release with the highest version number
    latest_release = None
    latest_version_tuple = (0, 0, 0)
    
    for release in releases['releases']:
        try:
            version_tuple = parse_version(release['version'])
            if version_tuple > latest_version_tuple:
                latest_version_tuple = version_tuple
                latest_release = release
        except ValueError:
            continue  # Skip invalid version formats
    
    if not latest_release:
        print("No valid releases found")
        return
    version = latest_release['version']
    sha1 = latest_release['sha1']
    
    print(f"Testing with latest version: {version} (sha1: {sha1})")
    
    size_data_dir = Path("size-analyzer")
    
    if test_platform == "ios":
        # Test arm64-ios platform
        platform = "arm64-ios"
        filename = "dmengine_release"
        platform_dir = size_data_dir / platform
        platform_dir.mkdir(parents=True, exist_ok=True)
        
        csv_path = platform_dir / f"{version}.csv"
        binary_filename = f"dmengine_release_{version}"
        dsym_filename = f"dmengine_release_{version}.dSYM.zip"
        binary_path = platform_dir / binary_filename
        dsym_zip_path = platform_dir / dsym_filename
        dsym_extract_dir = platform_dir / f"dsym_{version}"
        
        cleanup_paths = []
        
        try:
            # Download binary
            if not download_engine(sha1, version, platform, filename, str(binary_path)):
                print(f"Failed to download binary for {version}")
                return
            cleanup_paths.append(binary_path)
            
            # Download dSYM
            if not download_engine_dsym(sha1, version, platform, filename, str(dsym_zip_path)):
                print(f"Failed to download dSYM for {version}")
                return
            cleanup_paths.append(dsym_zip_path)
            
            # Extract dSYM
            with zipfile.ZipFile(str(dsym_zip_path), 'r') as zf:
                zf.extractall(str(dsym_extract_dir))
            cleanup_paths.append(dsym_extract_dir)
            
            # Find DWARF file
            dwarf_file = dsym_extract_dir / "src" / f"{filename}.dSYM" / "Contents" / "Resources" / "DWARF" / filename
            
            if not dwarf_file.exists():
                print(f"DWARF file not found in dSYM")
                return
            
            # Run analysis
            if run_bloaty_analysis(str(binary_path), str(csv_path), platform, str(dwarf_file)):
                print(f"✅ iOS test completed successfully: {csv_path}")
            else:
                print("❌ iOS test failed")
                
        finally:
            # Clean up
            for path in cleanup_paths:
                if path.exists():
                    try:
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink()
                        print(f"Cleaned up: {path}")
                    except Exception as e:
                        print(f"Warning: Failed to clean up {path}: {e}")
                        
    elif test_platform == "android":
        # Test arm64-android platform
        platform = "arm64-android"
        filename = "libdmengine_release.so"
        platform_dir = size_data_dir / platform
        platform_dir.mkdir(parents=True, exist_ok=True)
        
        csv_path = platform_dir / f"{version}.csv"
        binary_filename = f"dmengine_release_{version}.so"
        binary_path = platform_dir / binary_filename
        
        cleanup_paths = []
        
        try:
            # Download binary
            if not download_engine(sha1, version, platform, filename, str(binary_path)):
                print(f"Failed to download binary for {version}")
                return
            cleanup_paths.append(binary_path)
            
            # Run analysis
            if run_bloaty_analysis(str(binary_path), str(csv_path), platform):
                print(f"✅ Android test completed successfully: {csv_path}")
            else:
                print("❌ Android test failed")
                
        finally:
            # Clean up
            for path in cleanup_paths:
                if path.exists():
                    try:
                        path.unlink()
                        print(f"Cleaned up: {path}")
                    except Exception as e:
                        print(f"Warning: Failed to clean up {path}: {e}")
                        
    elif test_platform == "bob":
        # Test bob.jar platform
        platform = "bob.jar"
        platform_dir = size_data_dir / platform
        platform_dir.mkdir(parents=True, exist_ok=True)
        
        csv_path = platform_dir / f"{version}.csv"
        jar_filename = f"bob_{version}.jar"
        jar_path = platform_dir / jar_filename
        
        cleanup_paths = []
        
        try:
            # Download bob.jar
            if not download_bob_jar(sha1, version, str(jar_path)):
                print(f"Failed to download bob.jar for {version}")
                return
            cleanup_paths.append(jar_path)
            
            # Run analysis
            if analyze_bob_jar(str(jar_path), str(csv_path)):
                print(f"✅ Bob test completed successfully: {csv_path}")
            else:
                print("❌ Bob test failed")
                
        finally:
            # Clean up
            for path in cleanup_paths:
                if path.exists():
                    try:
                        path.unlink()
                        print(f"Cleaned up: {path}")
                    except Exception as e:
                        print(f"Warning: Failed to clean up {path}: {e}")
                        
    elif test_platform == "editor":
        # Test editor win32 platform
        editor_platform = "win32"
        filename = "Defold-x86_64-win32.zip"
        editor_platform_dir = size_data_dir / f"editor-{editor_platform}"
        editor_platform_dir.mkdir(parents=True, exist_ok=True)
        
        csv_path = editor_platform_dir / f"{version}.csv"
        editor_filename = f"editor_{version}_{editor_platform}.zip"
        editor_path = editor_platform_dir / editor_filename
        extract_dir = editor_platform_dir / f"extracted_{version}"
        
        cleanup_paths = []
        
        try:
            # Download editor
            if not download_editor(sha1, version, editor_platform, filename, str(editor_path)):
                print(f"Failed to download editor for {version}")
                return
            cleanup_paths.append(editor_path)
            
            # Extract editor
            with zipfile.ZipFile(str(editor_path), 'r') as zf:
                zf.extractall(str(extract_dir))
            cleanup_paths.append(extract_dir)
            
            # Run combined analysis
            if analyze_combined_editor(str(extract_dir), str(csv_path)):
                print(f"✅ Editor test completed successfully: {csv_path}")
            else:
                print("❌ Editor test failed")
                
        finally:
            # Clean up
            for path in cleanup_paths:
                if path.exists():
                    try:
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink()
                        print(f"Cleaned up: {path}")
                    except Exception as e:
                        print(f"Warning: Failed to clean up {path}: {e}")
                        
    elif test_platform == "macos":
        # Test arm64-macos platform
        platform = "arm64-macos"
        filename = "dmengine_release"
        platform_dir = size_data_dir / platform
        platform_dir.mkdir(parents=True, exist_ok=True)
        
        csv_path = platform_dir / f"{version}.csv"
        binary_filename = f"dmengine_release_{version}"
        dsym_filename = f"dmengine_release_{version}.dSYM.zip"
        binary_path = platform_dir / binary_filename
        dsym_zip_path = platform_dir / dsym_filename
        dsym_extract_dir = platform_dir / f"dsym_{version}"
        
        cleanup_paths = []
        
        try:
            # Download binary
            if not download_engine(sha1, version, platform, filename, str(binary_path)):
                print(f"Failed to download binary for {version}")
                return
            cleanup_paths.append(binary_path)
            
            # Download dSYM
            if not download_file(sha1, f"engine/{platform}", f"{filename}.dSYM.zip", str(dsym_zip_path)):
                print(f"Failed to download dSYM for {version}")
                return
            cleanup_paths.append(dsym_zip_path)
            
            # Extract dSYM
            with zipfile.ZipFile(str(dsym_zip_path), 'r') as zf:
                zf.extractall(str(dsym_extract_dir))
            cleanup_paths.append(dsym_extract_dir)
            
            # Find DWARF file
            dwarf_file = dsym_extract_dir / "src" / f"{filename}.dSYM" / "Contents" / "Resources" / "DWARF" / filename
            
            if not dwarf_file.exists():
                print(f"DWARF file not found in dSYM")
                return
            
            # Run analysis
            if run_bloaty_analysis(str(binary_path), str(csv_path), platform, str(dwarf_file)):
                print(f"✅ macOS test completed successfully: {csv_path}")
            else:
                print("❌ macOS test failed")
                
        finally:
            # Clean up
            for path in cleanup_paths:
                if path.exists():
                    try:
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink()
                        print(f"Cleaned up: {path}")
                    except Exception as e:
                        print(f"Warning: Failed to clean up {path}: {e}")
    else:
        print(f"Unknown test platform: {test_platform}")
        print("Available platforms: ios, android, bob, editor, macos")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Analyze Defold build sizes')
    parser.add_argument('--test', choices=['ios', 'android', 'bob', 'editor', 'macos'], 
                       help='Test mode: download and analyze latest version of specified platform')
    args = parser.parse_args()
    
    # Read releases first
    releases = read_releases('releases.json')

    # Read existing analysis index to detect SHA1 changes
    size_data_dir = Path("size-analyzer")
    analysis_index_path = size_data_dir / "analysis_index.json"
    existing_index = {}
    if analysis_index_path.exists():
        with open(analysis_index_path, 'r') as f:
            existing_index = json.load(f)
    
    # If test mode, run test and exit
    if args.test:
        run_test_mode(args.test, releases)
        return
    
    # Configuration
    platforms_config = {
        "arm64-android": "libdmengine_release.so",
        "armv7-android": "libdmengine_release.so",
        "arm64-ios": "dmengine_release",
        "x86_64-macos": "dmengine_release",
        "arm64-macos": "dmengine_release",
        "bob.jar": None  # Special platform for bob.jar analysis
    }
    
    # Editor platforms configuration
    editor_platforms_config = {
        "win32": "Defold-x86_64-win32.zip",
        "x86_64-linux": "Defold-x86_64-linux.zip", 
        "x86_64-macos": "Defold-x86_64-macos.zip",
        "arm64-macos": "Defold-arm64-macos.zip"
    }
    min_version = "1.9.0"
    min_version_tuple = parse_version(min_version)
    
    # Create size-analyzer directory structure
    size_data_dir = Path("size-analyzer")
    
    # Track processed versions with SHA1 for index update
    all_platforms_versions = {}
    
    # Filter releases starting from 1.9.0
    filtered_releases = []
    for release in releases['releases']:
        version = release['version']
        try:
            version_tuple = parse_version(version)
            if version_tuple >= min_version_tuple:
                filtered_releases.append(release)
        except ValueError:
            print(f"Skipping invalid version format: {version}")
            continue
    
    print(f"Found {len(filtered_releases)} releases starting from {min_version}")
    
    # Build version to SHA1 mapping from all releases (not just filtered ones)
    version_to_sha1 = {release['version']: release['sha1'] for release in releases['releases']}
    releases_version_set = set(version_to_sha1.keys())

    def get_existing_sha1(platform, version):
        platform_data = existing_index.get("platforms", {}).get(platform, {})
        for version_info in platform_data.get("versions", []):
            if version_info.get("version") == version:
                return version_info.get("sha1")
        return None

    def cleanup_stale_csvs(directory, allowed_versions):
        for csv_file in directory.glob("*.csv"):
            version = csv_file.stem
            if version not in allowed_versions:
                try:
                    csv_file.unlink()
                    print(f"Removed stale analysis: {csv_file}")
                except Exception as e:
                    print(f"Warning: Failed to remove stale analysis {csv_file}: {e}")
    
    # Process each platform
    for platform, filename in platforms_config.items():
        print(f"\n=== Processing platform: {platform} ===")
        
        # Create platform directory
        platform_dir = size_data_dir / platform
        platform_dir.mkdir(parents=True, exist_ok=True)
        
        processed_versions = []
        
        # Process each release for this platform
        for release in filtered_releases:
            version = release['version']
            sha1 = release['sha1']
            
            print(f"\nProcessing version {version} (sha1: {sha1}) for {platform}")
            
            # Check if analysis already exists
            csv_filename = f"{version}.csv"
            csv_path = platform_dir / csv_filename
            
            if csv_path.exists():
                existing_sha1 = get_existing_sha1(platform, version)
                if existing_sha1 and existing_sha1 != sha1:
                    print(f"Analysis exists but SHA1 changed ({existing_sha1} -> {sha1}), reprocessing...")
                else:
                    print(f"Analysis already exists: {csv_path}")
                    processed_versions.append(version)
                    continue
            
            if platform == "bob.jar":
                # Handle bob.jar analysis
                jar_filename = f"bob_{version}.jar"
                jar_path = platform_dir / jar_filename
                
                # Keep track of files to clean up
                cleanup_paths = []
                
                try:
                    # Download bob.jar
                    if not download_bob_jar(sha1, version, str(jar_path)):
                        print(f"Failed to download bob.jar for {version}, skipping...")
                        continue
                    cleanup_paths.append(jar_path)
                    
                    # Analyze bob.jar
                    if not analyze_bob_jar(str(jar_path), str(csv_path)):
                        print(f"Failed to analyze bob.jar for {version}, skipping...")
                        continue
                    
                    print(f"Successfully analyzed {version} for {platform}")
                    
                finally:
                    # Always clean up downloaded files
                    for path in cleanup_paths:
                        if path.exists():
                            try:
                                path.unlink()
                                print(f"Cleaned up file: {path}")
                            except Exception as e:
                                print(f"Warning: Failed to clean up {path}: {e}")
            
            else:
                # Handle native binary analysis
                if platform in ["arm64-ios", "x86_64-macos", "arm64-macos"]:
                    # Apple platforms - need binary and dSYM file
                    binary_filename = f"dmengine_release_{version}"
                    dsym_filename = f"dmengine_release_{version}.dSYM.zip"
                    binary_path = platform_dir / binary_filename
                    dsym_zip_path = platform_dir / dsym_filename
                    dsym_extract_dir = platform_dir / f"dsym_{version}"
                    
                    # Keep track of all files/directories to clean up
                    cleanup_paths = []
                    
                    try:
                        # Download main binary
                        if not download_engine(sha1, version, platform, filename, str(binary_path)):
                            print(f"Failed to download binary for {version}, skipping...")
                            continue
                        cleanup_paths.append(binary_path)
                        
                        # Download dSYM file
                        if not download_engine_dsym(sha1, version, platform, filename, str(dsym_zip_path)):
                            print(f"Failed to download dSYM for {version}, skipping...")
                            continue
                        cleanup_paths.append(dsym_zip_path)
                        
                        # Extract dSYM file
                        try:
                            with zipfile.ZipFile(str(dsym_zip_path), 'r') as zf:
                                zf.extractall(str(dsym_extract_dir))
                            cleanup_paths.append(dsym_extract_dir)
                            
                            # Find the DWARF file inside the dSYM bundle
                            dwarf_file = dsym_extract_dir / "src" / f"{filename}.dSYM" / "Contents" / "Resources" / "DWARF" / filename
                            
                            if not dwarf_file.exists():
                                print(f"DWARF file not found in dSYM for {version}, skipping...")
                                continue
                            
                            # Run bloaty analysis with dSYM debug file
                            if not run_bloaty_analysis(str(binary_path), str(csv_path), platform, str(dwarf_file)):
                                print(f"Failed to analyze {version}, skipping...")
                                continue
                            
                            print(f"Successfully analyzed {version} for {platform}")
                            
                        except zipfile.BadZipFile:
                            print(f"Invalid ZIP file for dSYM {version}, skipping...")
                            continue
                        except Exception as e:
                            print(f"Failed to extract dSYM for {version}: {e}")
                            continue
                            
                    finally:
                        # Always clean up all downloaded/extracted files
                        for path in cleanup_paths:
                            if path.exists():
                                try:
                                    if path.is_dir():
                                        shutil.rmtree(path)
                                        print(f"Cleaned up directory: {path}")
                                    else:
                                        path.unlink()
                                        print(f"Cleaned up file: {path}")
                                except Exception as e:
                                    print(f"Warning: Failed to clean up {path}: {e}")
                else:
                    # Handle other platforms (Android, etc.)
                    binary_filename = f"dmengine_release_{version}.so"
                    binary_path = platform_dir / binary_filename
                    
                    # Keep track of files to clean up
                    cleanup_paths = []
                    
                    try:
                        # Download binary
                        if not download_engine(sha1, version, platform, filename, str(binary_path)):
                            print(f"Failed to download {version}, skipping...")
                            continue
                        cleanup_paths.append(binary_path)
                        
                        # Run bloaty analysis with compileunits mode (no debug file needed)
                        if not run_bloaty_analysis(str(binary_path), str(csv_path), platform):
                            print(f"Failed to analyze {version}, skipping...")
                            continue
                        
                        print(f"Successfully analyzed {version} for {platform}")
                        
                    finally:
                        # Always clean up downloaded files
                        for path in cleanup_paths:
                            if path.exists():
                                try:
                                    path.unlink()
                                    print(f"Cleaned up file: {path}")
                                except Exception as e:
                                    print(f"Warning: Failed to clean up {path}: {e}")
            
            # Add to processed versions list
            processed_versions.append(version)
            print(f"Completed processing {version} for {platform}")
        
        # Get all existing CSV files for this platform to include in index
        cleanup_stale_csvs(platform_dir, releases_version_set)
        existing_csvs = list(platform_dir.glob("*.csv"))
        all_versions = []
        for csv_file in existing_csvs:
            version = csv_file.stem
            if version not in releases_version_set:
                continue
            sha1 = version_to_sha1.get(version, "unknown")
            all_versions.append({"version": version, "sha1": sha1})
        all_platforms_versions[platform] = all_versions
        
        print(f"Finished processing {platform}: {len(all_versions)} versions")
    
    # Process editor platforms
    for editor_platform, filename in editor_platforms_config.items():
        print(f"\\n=== Processing editor platform: {editor_platform} ===")
        
        # Create editor platform directory with "editor-" prefix
        editor_platform_dir = size_data_dir / f"editor-{editor_platform}"
        editor_platform_dir.mkdir(parents=True, exist_ok=True)
        
        processed_versions = []
        
        # Process each release for this editor platform
        for release in filtered_releases:
            version = release['version']
            sha1 = release['sha1']
            
            print(f"\\nProcessing editor version {version} (sha1: {sha1}) for {editor_platform}")
            
            # Check if analysis already exists
            csv_filename = f"{version}.csv"
            csv_path = editor_platform_dir / csv_filename
            
            if csv_path.exists():
                existing_sha1 = get_existing_sha1(f"editor-{editor_platform}", version)
                if existing_sha1 and existing_sha1 != sha1:
                    print(f"Editor analysis exists but SHA1 changed ({existing_sha1} -> {sha1}), reprocessing...")
                else:
                    print(f"Editor analysis already exists for {version}")
                    processed_versions.append(version)
                    continue
            
            # Download and extract editor
            editor_filename = f"editor_{version}_{editor_platform}.zip"
            
            editor_path = editor_platform_dir / editor_filename
            extract_dir = editor_platform_dir / f"extracted_{version}"
            
            # Keep track of files to clean up
            cleanup_paths = []
            
            try:
                # Download editor
                if not download_editor(sha1, version, editor_platform, filename, str(editor_path)):
                    print(f"Failed to download editor for {version}, skipping...")
                    continue
                cleanup_paths.append(editor_path)
                
                # Extract editor archive (all are zip files)
                try:
                    with zipfile.ZipFile(str(editor_path), 'r') as zf:
                        zf.extractall(str(extract_dir))
                    
                    cleanup_paths.append(extract_dir)
                    
                    # Analyze editor with combined approach
                    if analyze_combined_editor(str(extract_dir), str(csv_path)):
                        print(f"Successfully analyzed editor {version} for {editor_platform}")
                        processed_versions.append(version)
                    else:
                        print(f"Failed to analyze editor {version}")
                        
                except zipfile.BadZipFile:
                    print(f"Invalid ZIP file for editor {version}, skipping...")
                    continue
                except Exception as e:
                    print(f"Failed to extract editor for {version}: {e}")
                    continue
                    
            finally:
                # Always clean up all downloaded/extracted files
                for path in cleanup_paths:
                    if path.exists():
                        try:
                            if path.is_dir():
                                shutil.rmtree(path)
                                print(f"Cleaned up directory: {path}")
                            else:
                                path.unlink()
                                print(f"Cleaned up file: {path}")
                        except Exception as e:
                            print(f"Warning: Failed to clean up {path}: {e}")
        
        # Get all existing CSV files for this editor platform to include in index
        cleanup_stale_csvs(editor_platform_dir, releases_version_set)
        existing_csvs = list(editor_platform_dir.glob("*.csv"))
        editor_versions = []
        for csv_file in existing_csvs:
            version = csv_file.stem
            if version not in releases_version_set:
                continue
            sha1 = version_to_sha1.get(version, "unknown")
            editor_versions.append({"version": version, "sha1": sha1})
        all_platforms_versions[f"editor-{editor_platform}"] = editor_versions
        
        print(f"Finished processing editor-{editor_platform}: {len(editor_versions)} versions")
    
    # Update analysis index with all platforms and versions
    analysis_index_path = size_data_dir / "analysis_index.json"
    
    index = {"platforms": {}}
    
    # Update all platforms while preserving existing SHA1 values
    for platform, version_data in all_platforms_versions.items():
        # Get existing SHA1s for this platform if they exist
        existing_sha1_map = {}
        if "platforms" in existing_index and platform in existing_index["platforms"]:
            for version_info in existing_index["platforms"][platform].get("versions", []):
                existing_sha1_map[version_info["version"]] = version_info["sha1"]
        
        # Update version data with existing SHA1s where available
        updated_versions = []
        for version_info in version_data:
            version = version_info["version"]
            # Prefer current release SHA1, then existing, then current value
            sha1 = version_to_sha1.get(version, existing_sha1_map.get(version, version_info["sha1"]))
            updated_versions.append({"version": version, "sha1": sha1})
        
        # Sort by version
        sorted_versions = sorted(updated_versions, key=lambda x: parse_version(x['version']))
        index["platforms"][platform] = {
            "versions": sorted_versions
        }
    
    # Write updated index
    with open(analysis_index_path, 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"\nFinished processing all platforms and releases.")
    print(f"Analysis index updated with platforms: {list(all_platforms_versions.keys())}")
    for platform, versions in all_platforms_versions.items():
        print(f"  {platform}: {len(versions)} versions")

if __name__ == "__main__":
    main()
