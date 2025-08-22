#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import json
import shutil
import zipfile
import csv
from pathlib import Path
from collections import defaultdict

def parse_version(version_str):
    """Parse version string into tuple for comparison"""
    return tuple(map(int, version_str.split('.')))

def read_releases(path):
    """Read releases from JSON file"""
    with open(path, 'rb') as f:
        d = json.loads(f.read())
        return d
    return {}

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

def download_engine(sha1, platform, filename, output_path):
    """Download engine binary from Defold archive"""
    return download_file(sha1, f"engine/{platform}", filename, output_path)

def download_bob_jar(sha1, output_path):
    """Download bob.jar from Defold archive"""
    return download_file(sha1, "bob", "bob.jar", output_path)

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

def main():
    # Configuration
    platforms_config = {
        "arm64-android": "libdmengine_release.so",
        "armv7-android": "libdmengine_release.so",
        "arm64-ios": "dmengine_release",
        "x86_64-macos": "dmengine_release",
        "arm64-macos": "dmengine_release",
        "bob.jar": None  # Special platform for bob.jar analysis
    }
    min_version = "1.9.0"
    
    # Read releases
    releases = read_releases('releases.json')
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
    
    # Build version to SHA1 mapping from filtered releases
    version_to_sha1 = {release['version']: release['sha1'] for release in filtered_releases}
    
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
                    if not download_bob_jar(sha1, str(jar_path)):
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
                        if not download_engine(sha1, platform, filename, str(binary_path)):
                            print(f"Failed to download binary for {version}, skipping...")
                            continue
                        cleanup_paths.append(binary_path)
                        
                        # Download dSYM file
                        if not download_file(sha1, f"engine/{platform}", f"{filename}.dSYM.zip", str(dsym_zip_path)):
                            print(f"Failed to download dSYM for {version}, skipping...")
                            continue
                        cleanup_paths.append(dsym_zip_path)
                        
                        # Extract dSYM file
                        try:
                            import zipfile
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
                        if not download_engine(sha1, platform, filename, str(binary_path)):
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
        existing_csvs = list(platform_dir.glob("*.csv"))
        all_versions = []
        for csv_file in existing_csvs:
            version = csv_file.stem
            sha1 = version_to_sha1.get(version, "unknown")
            all_versions.append({"version": version, "sha1": sha1})
        all_platforms_versions[platform] = all_versions
        
        print(f"Finished processing {platform}: {len(all_versions)} versions")
    
    # Update analysis index with all platforms and versions
    analysis_index_path = size_data_dir / "analysis_index.json"
    
    # Read existing index or create new one
    if analysis_index_path.exists():
        with open(analysis_index_path, 'r') as f:
            index = json.load(f)
    else:
        index = {"platforms": {}}
    
    # Update all platforms
    for platform, version_data in all_platforms_versions.items():
        # Sort by version
        sorted_versions = sorted(version_data, key=lambda x: parse_version(x['version']))
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