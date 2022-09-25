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
    {"platform": "js-web",          "filename": "notused"},
    {"platform": "wasm-web",        "filename": "notused"},
    {"platform": "x86_64-linux",    "filename": "notused"},
    {"platform": "x86-win32",       "filename": "notused"},
    {"platform": "x86_64-win32",    "filename": "notused"},
]

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
    d = urllib.request.urlopen(url)
    if d.getcode() == 200:
        return d.info()['Content-Length']
    return 0

def get_engine_size_from_aws(sha1, platform, filename):
    print("Gettings size of {} for platform {} with sha1 {} from AWS".format(filename, platform, sha1))
    path = "engine/{}/stripped/{}".format(platform, filename)
    size = get_size_from_url(sha1, path)
    if size == 0:
        path = "engine/{}/{}".format(platform, filename)
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
        elif platform in ("wasm-web", "js-web"):
            args.append("--platform=js-web")
            args.append("--architectures=" + platform)
        else:
            args.append("--platform=" + platform)
        args.append("--variant=release")
        args.append("--bundle-output=../bundle_output")
        args.extend(["clean", "build", "bundle"])

        subprocess.call(args,cwd="empty_project")

        if platform in ("armv7-android", "arm64-android"):
            return os.path.getsize("bundle_output/unnamed/unnamed.apk")
        elif platform in ("arm64-ios","x86_64-ios","arm64-darwin"):
            return os.path.getsize("bundle_output/unnamed.ipa")
        elif platform in ("x86_64-macos", "x86_64-darwin"):
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


def get_latest_version():
    url = "http://d.defold.com/stable/info.json"
    response = urllib.request.urlopen(url)
    if response.getcode() == 200:
        return json.loads(response.read())
    return {}

def read_releases(path):
    with open(path, 'rb') as f:
        d = json.loads(f.read())
        return d
    return {}


def create_report(report_filename, releases, report_platforms, fn):
    print("Creating {}".format(report_filename))
    report_rows = []
    with open(report_filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            report_rows.append(row)

    with open(report_filename, 'w') as f:
        writer = csv.writer(f)
        header = []
        header.append("VERSION")
        for report_platform in report_platforms:
            header.append(report_platform["platform"])
        writer.writerow(header)

        # go through the releases one by one and either use existing size data
        # or download and get the size data
        for release in releases:
            version = release["version"]
            sha1 = release["sha1"]

            row = None
            for report_row in report_rows:
                if report_row[0] == version:
                    row = report_row
                    break

            if row is None:
                print("Found new version {} - Getting size".format(version))
                row = []
                row.append(version)
                for report_platform in report_platforms:
                    platform = report_platform["platform"]
                    filename = report_platform["filename"]
                    size = fn(sha1, platform, filename)
                    row.append(size)

            writer.writerow(row)
    print("Creating {} - ok".format(report_filename))

def parse_version(version_str):
    v = version_str.split('.')
    v[0] = int(v[0])
    v[1] = int(v[1])
    v[2] = int(v[2])
    return v

def new_version(v1, v2):
    if v1[0] < v2[0]:
        return False
    if v1[0] == v2[0] and v1[1] < v2[1]:
        return False
    if v1[0] == v2[0] and v1[1] == v2[1] and v1[2] < v2[2]:
        return False
    return True

def create_graph(report_filename, out, from_version=None):
    print("Creating {}".format(out))
    with open(report_filename, 'r') as f:
        data = list(csv.reader(f))

        # only keep the versions starting with from_version and above
        if from_version is not None:
            from_version = parse_version(from_version)
            new_data = []
            for line in data:
                if not line[0].startswith('1.2.'):
                    new_data.append(line)
                    continue
                version = parse_version(line[0])
                if new_version(version, from_version):
                    new_data.append(line)
            data = new_data

        # get all versions, ignore column headers
        versions = [i[0] for i in data[1::]]
        xaxis_version = range(0, len(versions))

        fig, ax = pyplot.subplots(figsize=(20, 10))
        pyplot.xticks(xaxis_version, versions, rotation=270)
        max_ysize = 0
        assert(len(markers) >= (len(data[0])-1)) # we need unique markers for each platform
        for engine, marker in zip(range(1, len(data[0])), markers):
            # convert from string to int
            # find the max y size
            yaxis_size = []
            for num in list([i[engine] for i in data[1::]]):
                num = int(num)
                max_ysize = max(max_ysize, num)
                yaxis_size.append(num)
            ax.plot(xaxis_version, yaxis_size, label=data[0][engine], marker=marker)

        # make sure the plot fills out the area (easier to see nuances)
        ax.set_ylim(bottom=0.)
        ax.set_xlim(left=0., right=xaxis_version[-1])

        mb = 1024 * 1024
        max_mb = (max_ysize+mb/2) // mb
        locs = [i * mb for i in range(0, int(max_mb + 1))]

        # create horizontal lines, to make it easier to track sizes
        for y in range(0, int(max_mb*mb), 2*mb):
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


def check_for_updates(latest_release, releases):
    # Is the release already present?
    for release in releases['releases']:
        if latest_release['version'] == release['version']:
            return False
    return True


# latest_release = { "version": "1.3.3", "sha1": "287c945fab310c324493e08b191ee1b1538ef973"}
latest_release = get_latest_version()

releases = read_releases('releases.json')

if check_for_updates(latest_release, releases):
    print("Found new release {}".format(latest_release))
    releases['releases'].append(latest_release)

    # update the releases on disc
    with open('releases_new.json', 'w') as f:
        json.dump(releases, f, indent=4, separators=(',', ': '))
    # if everything went right, move the temp file
    shutil.move('releases_new.json', 'releases.json')


# update reports (if releases are missing from a report file)
print("Creating reports")
# create_report("legacy_engine_report.csv", releases['releases'], engines, get_engine_size_from_aws)
create_report("engine_report.csv", releases['releases'], engines, get_engine_size_from_bob)
create_report("bundle_report.csv", releases['releases'], bundles, get_bundle_size_from_bob)


# create graphs based on the different reports
print("Creating graphs")
# create_graph("legacy_engine_report.csv", out='legacy_engine_size.png')
# create_graph("legacy_engine_report.csv", out='legacy_engine_size_stripped.png', from_version='1.2.155') # from 1.2.155, we have stripped versions available for all platforms
create_graph("engine_report.csv", out='engine_size.png', from_version='1.2.166')
create_graph("bundle_report.csv", out='bundle_size.png', from_version='1.2.166')
