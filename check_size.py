#!/usr/bin/env python
import urllib
import datetime
import itertools
import json
import shutil
import csv
import matplotlib
matplotlib.use('Agg')

from matplotlib import pyplot


def get_size(sha1, path):
    url = "http://d.defold.com/archive/" + sha1 + "/" + path
    d = urllib.urlopen(url)
    if d.getcode() == 200:
        return d.info()['Content-Length']
    return 0

def get_latest_version():
    url = "http://d.defold.com/stable/info.json"
    response = urllib.urlopen(url)
    if response.getcode() == 200:
        return json.loads(response.read())
    return {}

def read_releases(path):
    with open(path, 'rb') as f:
        d = json.loads(f.read())
        return d
    return {}

engines = [
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

def create_report(releases):
    print("Creating report.csv")
    report_rows = []
    with open('report.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            report_rows.append(row)

    with open("report.csv", 'w') as f:
        writer = csv.writer(f)
        header = []
        header.append("VERSION")
        for engine in engines:
            header.append(engine["platform"])
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
                print("Found new version {} - Getting size of engine binaries".format(version))
                row = []
                row.append(version)
                for engine in engines:
                    path = "engine/{}/stripped/{}".format(engine["platform"], engine["filename"])
                    size = get_size(release["sha1"], path)
                    if size == 0:
                        path = "engine/{}/{}".format(engine["platform"], engine["filename"])
                        size = get_size(release["sha1"], path)
                    row.append(size)

            writer.writerow(row)
    print("Creating report.csv - ok")

def parse_version(version_str):
    return map(int, version_str.split('.'))

def create_graph(out, from_version=None):
    print("Creating {}".format(out))
    with open('report.csv', 'r') as f:
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
                if version >= from_version:
                    new_data.append(line)
            data = new_data

        # get all versions, ignore column headers
        versions = [i[0] for i in data[1::]]
        xaxis_version = range(0, len(versions))

        fig, ax = pyplot.subplots(figsize=(20, 10))
        pyplot.xticks(xaxis_version, versions, rotation=270)
        max_ysize = 0
        markers = '.o8s+xD*pP<^'
        assert(len(markers) >= (len(data[0])-1)) # we need unique markers for each platform
        for engine, marker in zip(range(1, len(data[0])), markers):
            yaxis_size = [i[engine] for i in data[1::]]
            # convert from string to int
            yaxis_size = map(lambda x: int(x) if x > 0 else None, yaxis_size)
            # find the max y size
            max_ysize = max(max_ysize, max(yaxis_size))
            # replace zero values with nan to avoid plotting them
            yaxis_size = map(lambda x: x if x != 0 else float('nan'), yaxis_size)
            ax.plot(xaxis_version, yaxis_size, label=data[0][engine], marker=marker)

        # make sure the plot fills out the area (easier to see nuances)
        ax.set_ylim(bottom=0.)
        ax.set_xlim(left=0., right=xaxis_version[-1])

        mb = 1024 * 1024
        max_mb = (max_ysize+mb/2) // mb
        locs = [i * mb for i in range(0, max_mb + 1)]

        # create horizontal lines, to make it easier to track sizes
        for y in range(0, max_mb*mb, 2*mb):
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


latest_release = get_latest_version()
releases = read_releases('releases.json')

if check_for_updates(latest_release, releases):
    print("Found new release {}".format(latest_release))
    releases['releases'].append(latest_release)

    # update the releases on disc
    with open('releases_new.json', 'wb') as f:
        json.dump(releases, f, indent=4, separators=(',', ': '))
    # if everything went right, move the temp file
    shutil.move('releases_new.json', 'releases.json')


# update report (if releases are missing from report.csv)
create_report(releases['releases'])

create_graph(out='size.png')
create_graph(out='size_small.png', from_version='1.2.155') # from 1.2.155, we have stripped versions available for all platforms
