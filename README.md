# dmengine size plot
This project will plot the size of dmengine (Defold) for all supported platforms and versions. Note that this will show the size of the debug version of dmengine (ie including debug symbols). A release build of dmengine will be smaller.

Showing stripped versions:

![Size per platform and version](https://github.com/britzl/dmengine_size/raw/master/size_small.png)

History of versions:

![History of size per platform and version](https://github.com/britzl/dmengine_size/raw/master/size.png)

[![](https://travis-ci.org/britzl/dmengine_size.svg?branch=master)](https://travis-ci.org/britzl/dmengine_size/builds)

# Requirements
If you wish to run this script locally you need to have the following things installed:

* Python 2.7.10+
* [matlibplot](http://matplotlib.org/)

# Usage
Run [check_size.py](check_size.py):

    python check_size.py

It will generate these files:
* [releases.json](releases.json)
* [report.csv](report.csv)
* [size.png](size.png)
* [size_small.png](size_small.png)


To include a new version of dmengine in the report you need to [add an entry in the releases list in check_size.py](https://github.com/britzl/dmengine_size/blob/master/check_size.py#L28). The sha1 of the version you wish to add can be seen at [d.defold.com](d.defold.com).

The project will automatically generate a new graph and report file when a file in the project is changed. The automation is handled by [a Travis-CI job](https://travis-ci.org/britzl/dmengine_size).
