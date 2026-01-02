#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile
import urllib
import urllib.request
import datetime
import itertools
import json
import shutil
import csv
import zipfile
import matplotlib
matplotlib.use('Agg')

from matplotlib import pyplot
from collections import OrderedDict


# https://matplotlib.org/stable/api/markers_api.html
markers = '.o8s+xD*pP<<>'

# old list containing architectures we no longer use
# also a mix of engines and archives (apk vs engine binary)
legacy_engines = [
    {"platform": "arm64-darwin", "filename": "dmengine_release"},
    {"platform": "armv7-android", "filename": "dmengine_release.apk"}, # added in 1.2.153
    {"platform": "armv7-darwin", "filename": "dmengine_release"},
    {"platform": "darwin", "filename": "dmengine_release"},
    {"platform": "js-web", "filename": "dmengine_release.js"},
    {"platform": "wasm-web", "filename": "dmengine_release.wasm"}, # added in 1.2.141
    {"platform": "linux", "filename": "dmengine_release"},
    {"platform": "win32", "filename": "dmengine_release.exe"},
    {"platform": "x86_64-darwin", "filename": "dmengine_release"},
    {"platform": "x86_64-linux", "filename": "dmengine_release"},
    {"platform": "armv7-android", "filename": "dmengine.apk"},
    {"platform": "arm64-android", "filename": "dmengine.apk"},
]

engines = [
    {"platform": "arm64-ios",       "filename": "dmengine_release"},
    {"platform": "arm64-android",   "filename": "libdmengine_release.so"},
    {"platform": "armv7-android",   "filename": "libdmengine_release.so"},
    {"platform": "x86_64-macos",    "filename": "dmengine_release"},
    {"platform": "arm64-macos",     "filename": "dmengine_release"},
    {"platform": "js-web",          "filename": "dmengine_release.js"},
    {"platform": "wasm-web",        "filename": "dmengine_release.wasm"},
    {"platform": "x86_64-linux",    "filename": "dmengine_release"},
    {"platform": "x86-win32",       "filename": "dmengine_release.exe"},
    {"platform": "x86_64-win32",    "filename": "dmengine_release.exe"},
]

bundles = [
    {"platform": "arm64-ios",       "filename": "notused"},
    {"platform": "arm64-android",   "filename": "notused"},
    {"platform": "armv7-android",   "filename": "notused"},
    {"platform": "x86_64-macos",    "filename": "notused"},
    {"platform": "arm64-macos",     "filename": "notused"},
    {"platform": "js-web",          "filename": "notused"},
    {"platform": "wasm-web",        "filename": "notused"},
    {"platform": "x86_64-linux",    "filename": "notused"},
    {"platform": "x86-win32",       "filename": "notused"},
    {"platform": "x86_64-win32",    "filename": "notused"},
]

# each platform is the same size (it's the same bundle)
bob_files = [
    {"platform": "x86_64-macos",    "filename": "bob.jar"},
]

editor_files = [
    {"platform": "x86_64-macos",    "filename": "Defold-x86_64-macos.dmg"},
    {"platform": "arm64-macos",     "filename": "Defold-arm64-macos.dmg"},
    {"platform": "x86_64-win32",    "filename": "Defold-x86_64-win32.zip"},
    {"platform": "x86_64-linux",    "filename": "Defold-x86_64-linux.zip"},
]
#editor2/Defold-x86_64-macos.dmg

def get_host():
    if sys.platform == 'linux2':
        return 'linux'
    elif sys.platform == 'win32':
        return 'windows'
    elif sys.platform == 'darwin':
        return 'macos'
    raise "Unknown platform"

def download_bob(sha1):
    bob_path = 'bob_{}.jar'.format(sha1)
    if not os.path.exists(bob_path):
        print("Downloading bob version {} to {}".format(sha1, bob_path))
        url = "http://d.defold.com/archive/stable/" + sha1 + "/bob/bob.jar"
        urllib.request.urlretrieve(url, bob_path)
    return bob_path

def get_size_from_url(sha1, path):
    url = "http://d.defold.com/archive/" + sha1 + "/" + path
    try:
        d = urllib.request.urlopen(url)
        if d.getcode() == 200:
            return d.info()['Content-Length']
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(e.code, "Url doesn't exist:", url)
    return 0

def get_engine_size_from_aws(sha1, platform, filename):
    if platform == "x86-win32":
        platform = "win32"
    path = "engine/{}/stripped/{}"
    print("Gettings size of {} for platform {} with sha1 {} from AWS".format(filename, platform, sha1))
    path = path.format(platform, filename)
    size = get_size_from_url(sha1, path)
    if size == 0:
        path = "engine/{}/{}"
        path = path.format(platform, filename)
        size = get_size_from_url(sha1, path)
    if size == 0:
        path = "engine/{}/{}".format(platform, filename)
        size = get_size_from_url(sha1, path)
    return size

def get_bob_size_from_aws(sha1, platform, filename):
    print("Gettings size of {} for platform {} with sha1 {} from AWS".format(filename, platform, sha1))
    path = "bob/{}".format(filename)
    size = get_size_from_url(sha1, path)
    return size

def get_editor_size_from_aws(sha1, platform, filename):
    print("Gettings size of {} for platform {} with sha1 {} from AWS".format(filename, platform, sha1))
    path = "editor-alpha/editor2/{}".format(filename)
    size = get_size_from_url(sha1, path)
    return size

def extract_from_bob(bob_path, filename):
    bob_zip = zipfile.ZipFile(bob_path)
    bob_info = bob_zip.getinfo(filename)
    return bob_zip.extract(bob_info)

def get_engine_size_from_bob(sha1, platform, filename):
    print("Gettings size of {} for platform {} with sha1 {} from Bob".format(filename, platform, sha1))
    try:
        bob_path = download_bob(sha1)
        engine_path = 'libexec/{}/{}'.format(platform, filename)
        extracted_engine = extract_from_bob(bob_path, engine_path)
        return os.path.getsize(extracted_engine)
    except Exception as e:
        print(e)
        return 0

def get_engine_size(sha1, platform, filename):
    # Try to get the engine size from Bob
    size = get_engine_size_from_bob(sha1, platform, filename)
    if size > 0:
        return size

    # Fall back to getting the engine size from AWS
    size = get_engine_size_from_aws(sha1, platform, filename)
    return size

def get_zipped_size(path):
    tmp = tempfile.NamedTemporaryFile("wb")
    z = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(path):
        for file in files:
            z.write(os.path.join(root, file))
            print("write " + os.path.join(root, file))
    z.close()
    return os.path.getsize(tmp.name)

def get_folder_size(path):
    size = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            size = size + os.path.getsize(os.path.join(root, file))
    return size

def get_bundle_size_from_bob(sha1, platform, _):
    print("Gettings size of bundle for platform {} with sha1 {} using Bob".format(platform, sha1))
    if os.path.exists("bundle_output"):
        shutil.rmtree("bundle_output")
    os.mkdir("bundle_output")

    try:
        bob_path = download_bob(sha1)
        bob_filename = os.path.basename(bob_path)
        shutil.copy(bob_path, os.path.join("empty_project", "bob.jar"))
        args = []
        args.append("java")
        args.append("-jar")
        args.append("bob.jar")
        args.append("--archive")
        if platform in ("armv7-android", "arm64-android"):
            args.append("--platform=armv7-android")
            args.append("--architectures=" + platform)
            args.append("--bundle-format="+"aab")
        elif platform in ("wasm-web", "js-web"):
            args.append("--platform=js-web")
            args.append("--architectures=" + platform)
        elif platform in ("x86_64-macos", "arm64-macos"):
            args.append("--platform=x86_64-macos")
            args.append("--architectures=" + platform)
        else:
            args.append("--platform=" + platform)
        args.append("--variant=release")
        args.append("--strip-executable")
        args.append("--bundle-output=../bundle_output")
        args.extend(["clean", "build", "bundle"])

        subprocess.call(args,cwd="empty_project")

        if platform in ("armv7-android", "arm64-android"):
            return os.path.getsize("bundle_output/unnamed/unnamed.aab")
        elif platform in ("arm64-ios","x86_64-ios","arm64-darwin"):
            return os.path.getsize("bundle_output/unnamed.ipa")
        elif platform in ("x86_64-macos", "x86_64-darwin", "arm64-macos"):
            return get_folder_size("bundle_output/unnamed.app")
        elif platform in ("x86_64-win32", "x86-win32"):
            return get_zipped_size("bundle_output")
        elif platform in ("x86_64-linux",):
            return get_zipped_size("bundle_output")
        elif platform in ("wasm-web", "js-web"):
            return get_zipped_size("bundle_output")
        else:
            raise Exception("Unknown platform {}". format(platform))
    except Exception as e:
        print(e)
        return 0


def get_latest_release(channel):
    url = "http://d.defold.com/{}/info.json".format(channel)
    response = urllib.request.urlopen(url)
    if response.getcode() == 200:
        data = json.loads(response.read())
        data["channel"] = channel
        return data
    return {}

def read_releases(path):
    with open(path, 'rb') as f:
        d = json.loads(f.read())
        return d
    return {}

def print_report(report):

    """
    {
        'version' = ['1.3.3', '1.3.4', '1.3.5'],
        'arm64-ios' = {
            '1.3.4' = 123456,
            '1.3.5' = 123789,
        }
        'x86_64-macos' = {
            ...
        }
        ...
    }
    """
    print("report:")
    for key, data in report.items():
        if key == 'version':
            print("  version:")
            for version in data:
                print("    ", version)
            continue
        platform = key
        print("  platform:", platform)
        for version, size in data.items():
            print("    ", version, ":", size)

def read_report(path):
    #format:
    #VERSION,arm64-ios,arm64-android,armv7-android,x86_64-macos,js-web,wasm-web,x86_64-linux,x86-win32,x86_64-win32
    #1.2.38,0,0,0,0,0,0,0,0,0,0,0,0,0
    #1.2.39,0,0,0,0,0,0,0,0,0,0,0,0,0
    lines = []
    with open(path, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            lines.append(row)

    header = lines[0]
    platforms = header[1:]
    assert(header[0] == 'VERSION')

    report = OrderedDict()
    report['version'] = []
    for line in lines[1:]:
        version = line[0]
        report['version'].append(version)

        if len(line) != len(header):
            print("%s:" % path, "Mismatching number of cells in line", line)
            continue

        # loop over each platform
        for i, platform in enumerate(header):
            if i == 0:
                continue

            if not platform in report:
                report[platform] = OrderedDict()

            size = line[i]
            if size == '0':
                continue
            report[platform][version] = size

    return report

def sort_versions(versions):
    return sorted(versions, key=parse_version)

def write_report(path, report):
    #format:
    #VERSION,arm64-ios,arm64-android,armv7-android,x86_64-macos,js-web,wasm-web,x86_64-linux,x86-win32,x86_64-win32
    #1.2.38,0,0,0,0,0,0,0,0,0,0,0,0,0
    #1.2.39,0,0,0,0,0,0,0,0,0,0,0,0,0

    versions = sort_versions(report['version'])

    platforms = [x for x in report.keys() if x != 'version']

    lines = []
    lines.append(['VERSION']+platforms) # header

    for version in versions:
        row = [version]
        for platform in platforms:
            platform_data = report[platform]
            size = platform_data.get(version, 0) # the size (int) or n/a (0)
            row.append(size)

        lines.append(row)

    with open(path, 'w') as f:
        writer = csv.writer(f)
        for line in lines:
            writer.writerow(line)

    print("Wrote {}".format(path))


def create_report(report_filename, releases, report_platforms, fn, forced_versions=None):
    print("Creating {}".format(report_filename))

    report = read_report(report_filename)
    changed = False
    forced_versions = forced_versions or set()
    releases_versions = set(map(lambda x: x["version"], releases))

    # Remove versions that no longer exist in the releases list
    removed_versions = []
    for version in list(report['version']):
        if version not in releases_versions:
            report['version'].remove(version)
            removed_versions.append(version)
    if removed_versions:
        for platform, platform_data in report.items():
            if platform == 'version':
                continue
            for version in removed_versions:
                if version in platform_data:
                    del platform_data[version]
        changed = True

    # Remove old platforms
    supported_platforms = list(map(lambda x: x['platform'], report_platforms))
    delete_keys = []
    for key,_ in report.items():
        if key == 'version':
            continue
        if key not in supported_platforms:
            print("Removed old platform", key)
            delete_keys.append(key)
    for key in delete_keys:
        del report[key]
        changed = True

    # Add new platforms
    for platform in supported_platforms:
        if not platform in report:
            report[platform] = OrderedDict()
            changed = True


    # go through the releases one by one and either use existing size data
    # or download and get the size data
    for release in releases:
        version = release["version"]
        sha1 = release["sha1"]

        if version in report['version']:
            if version in forced_versions:
                print("  Version {} updated - Getting size".format(version))
                for report_platform in report_platforms:
                    platform = report_platform["platform"]
                    filename = report_platform["filename"]
                    print(f"  Making report for {platform}...")
                    size = fn(sha1, platform, filename)
                    print(f"  Resported size: {platform} {size}")
                    report[platform][version] = size
                changed = True
            else:
                print(f"  Version {version} already exists")
            continue # we already had the report for this version

        report['version'].append(version)
        print("Found new version {} - Getting size".format(version))
        changed = True

        for report_platform in report_platforms:
            platform = report_platform["platform"]
            filename = report_platform["filename"]
            print(f"  Making report for {platform}...")
            size = fn(sha1, platform, filename)
            print(f"  Resported size: {platform} {size}")
            report[platform][version] = size

    if changed:
        write_report(report_filename, report)
        print("Creating {} - ok".format(report_filename))
    else:
        print("No changes for {}".format(report_filename))
    return changed

def parse_version(version_str):
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

def create_graph(report_filename, out, from_version=None):
    print("Creating {}".format(out))
    with open(report_filename, 'r') as f:
        data = list(csv.reader(f))

        # only keep the versions starting with from_version and above
        if from_version is not None:
            from_version = parse_version(from_version)
            new_data = []
            for line in data:
                if 'VERSION' in line[0]:
                    new_data.append(line)
                    continue
                version = parse_version(line[0])
                #if new_version(version, from_version):
                if version >= from_version:
                    new_data.append(line)
            data = new_data

        # get all versions, ignore column headers
        versions = [i[0] for i in data[1::]]
        xaxis_version = range(0, len(versions))

        mb = 1024 * 1024

        fig, ax = pyplot.subplots(figsize=(20, 10))
        pyplot.xticks(xaxis_version, versions, rotation=270)
        max_ysize = 0
        min_ysize = 10000 * mb
        assert(len(markers) >= (len(data[0])-1)) # we need unique markers for each platform

        for engine, marker in zip(range(1, len(data[0])), markers):
            # convert from string to int
            # find the max y size
            yaxis_size = []
            for num in list([i[engine] for i in data[1::]]):
                num = int(num)
                max_ysize = max(max_ysize, num)
                min_ysize = min(min_ysize, num)
                yaxis_size.append(num)
            ax.plot(xaxis_version, yaxis_size, label=data[0][engine], marker=marker)

        # make sure the plot fills out the area (easier to see nuances)
        ax.set_ylim(bottom=min_ysize)
        ax.set_xlim(left=0., right=xaxis_version[-1])

        max_mb = int( (max_ysize+mb/2) // mb )
        min_mb = int( (min_ysize+mb/2) // mb )
        step = 1
        if max_mb - min_mb > 200:
            step = 10
        locs = [i * mb for i in range(min_mb, max_mb+1, step)]

        # create horizontal lines, to make it easier to track sizes
        for y in range(min_mb*mb, max_mb*mb, mb*step):
            ax.axhline(y, alpha=0.1)

        pyplot.yticks(locs, map(lambda x: "%d mb" % (x // mb), locs))
        pyplot.ylabel('SIZE')
        pyplot.xlabel('VERSION')
        # add timestamp to top-left corner of graph
        pyplot.annotate(str(datetime.datetime.now()), xy=(0.02, 0.95), xycoords='axes fraction')

        # create legend
        legend = ax.legend(loc='upper left', bbox_to_anchor=(0.02, 0.94))
        frame = legend.get_frame()
        frame.set_facecolor('0.90')

        fig.savefig(out, format='png', bbox_extra_artists=(legend,), bbox_inches='tight', pad_inches=1)
    print("Creating {} - ok".format(out))


def update_releases_with_channels(releases, latest_stable, latest_beta, latest_alpha):
    releases_list = releases['releases']
    changed = False
    forced_versions = set()

    filtered_releases = []
    for release in releases_list:
        version = release.get("version", "")
        if version.endswith("-alpha") or version.endswith("-beta"):
            changed = True
            continue
        filtered_releases.append(release)
    releases_list = filtered_releases

    def upsert_release(version, sha1):
        nonlocal changed
        existing = next((r for r in releases_list if r['version'] == version), None)
        if existing is None:
            releases_list.append({"version": version, "sha1": sha1})
            changed = True
            forced_versions.add(version)
            return
        if existing.get("sha1") != sha1:
            existing["sha1"] = sha1
            changed = True
            forced_versions.add(version)

    stable_version = None
    if latest_stable:
        stable_version = latest_stable.get("version")
        if stable_version and latest_stable.get("sha1"):
            upsert_release(stable_version, latest_stable["sha1"])

    if latest_beta and latest_beta.get("version") and latest_beta.get("sha1"):
        beta_version = latest_beta["version"]
        if beta_version != stable_version:
            upsert_release("{}-beta".format(beta_version), latest_beta["sha1"])

    if latest_alpha and latest_alpha.get("version") and latest_alpha.get("sha1"):
        alpha_version = latest_alpha["version"]
        upsert_release("{}-alpha".format(alpha_version), latest_alpha["sha1"])

    releases['releases'] = releases_list
    return changed, forced_versions


# latest_stable = { "version": "1.3.3", "sha1": "287c945fab310c324493e08b191ee1b1538ef973"}
latest_stable = get_latest_release("stable")
latest_beta = get_latest_release("beta")
latest_alpha = get_latest_release("alpha")

releases = read_releases('releases.json')

releases_changed, forced_versions = update_releases_with_channels(
    releases,
    latest_stable,
    latest_beta,
    latest_alpha,
)

if releases_changed:
    print("Found updated release info")

    # update the releases on disc
    with open('releases_new.json', 'w') as f:
        json.dump(releases, f, indent=4, separators=(',', ': '))
    # if everything went right, move the temp file
    shutil.move('releases_new.json', 'releases.json')


# update reports (if releases are missing from a report file)
print("Creating reports")
# create_report("legacy_engine_report.csv", releases['releases'], engines, get_engine_size_from_aws)
reports_changed = False
reports_changed |= create_report(
    "engine_report.csv",
    releases['releases'],
    engines,
    get_engine_size,
    forced_versions,
)
reports_changed |= create_report(
    "bundle_report.csv",
    releases['releases'],
    bundles,
    get_bundle_size_from_bob,
    forced_versions,
)
reports_changed |= create_report(
    "bob_report.csv",
    releases['releases'],
    bob_files,
    get_bob_size_from_aws,
    forced_versions,
)
reports_changed |= create_report(
    "editor_report.csv",
    releases['releases'],
    editor_files,
    get_editor_size_from_aws,
    forced_versions,
)


# create graphs based on the different reports
if reports_changed:
    print("Creating graphs")
    # create_graph("legacy_engine_report.csv", out='legacy_engine_size.png')
    # create_graph("legacy_engine_report.csv", out='legacy_engine_size_stripped.png', from_version='1.2.155') # from 1.2.155, we have stripped versions available for all platforms
    create_graph("engine_report.csv", out='engine_size.png', from_version='1.2.166')
    create_graph("bundle_report.csv", out='bundle_size.png', from_version='1.2.166')
    create_graph("bob_report.csv", out='bob_size.png', from_version='1.2.166')
    create_graph("editor_report.csv", out='editor_size.png', from_version='1.3.6')
else:
    print("Reports unchanged - skipping graph generation")
