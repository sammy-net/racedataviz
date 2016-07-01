# racedataviz

A collection of tools to visualize data from the RaceCapture/Pro.

It's very much a work in progress.  In fact, there's only one tool
present right now, which is located in src/tplot.py

To build on Ubuntu, the following packages are required:

scons python-pyside pyside-tools python-matplotlib python-pyproj

Fedora:

scons python-pyside pyside-tools python2-matplotlib python2-matplotlib-qt4 pyproj gdal-python

After installing the required packages, run scons in the top level
directory.  Once that's complete, run src/tplot.py.  Command line
arguments are available wth --help.
