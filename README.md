[![Build Status](https://travis-ci.com/britzl/dmengine_size.svg?branch=master)](https://travis-ci.com/britzl/dmengine_size)

# Defold engine and application bundle size plot
This project will plot the size of the Defold engine (aka dmengine) as well as the size of a complete Defold game bundle for all supported platforms and versions.

## Bundle size
The bundle size is measured as:

* Android - Size of .apk file containing one CPU architecture
* iOS - Size of .ipa file
* macOS - Size of .app file
* Windows - Size of zip archive with engine, required library files and game archive
* Linux - Size of zip archive with engine, required library files and game archive
* HTML5 - Size of zip archive with either .wasm or .asm.js engine, required library files and game archive

![Bundle size per platform and version](https://github.com/britzl/dmengine_size/raw/master/bundle_size.png)


## Engine size
This is the size of a release version of the Defold engine executable/library:

![Engine size per platform and version](https://github.com/britzl/dmengine_size/raw/master/engine_size.png)


## Deprecated graphs
Graph of versions stripped of debug symbols:

![Size per platform and version](https://github.com/britzl/dmengine_size/raw/master/legacy_engine_size_stripped.png)

History of versions:

![History of size per platform and version](https://github.com/britzl/dmengine_size/raw/master/legacy_engine_size.png)

NOTE: In both of the deprecated graphs above the measurements show the size of the .apk file for Android and for all other platforms the size of the engine itself.

# Requirements
If you wish to run this script locally you need to have the following things installed:

* Python 2.7.10+
* Java 11.0.*
* [matlibplot](http://matplotlib.org/)

# Usage
Run [check_size.py](check_size.py):

    python check_size.py

It will generate these files:
* [releases.json](releases.json)
* [engine_report.csv](engine_report.csv)
* [bundle_report.csv](bundle_report.csv)
* [engine_size.png](engine_size.png)
* [bundle_size.png](bundle_size.png)


To include a new version of dmengine in the report you need to [add an entry in the releases list in releases.json](https://github.com/britzl/dmengine_size/blob/master/releases.json). The sha1 of the version you wish to add can be seen at [d.defold.com](d.defold.com).

The project will automatically generate new graphs and report files when a file in the project is changed. The automation is handled by [a Travis-CI job](https://travis-ci.org/britzl/dmengine_size).
