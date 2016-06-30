# Copyright 2016 Sam Creasey, sammy@sammy.net.  All rights reserved.
#
# TODO sammy find the right GPL3 preamble for this

import glob
import os
import sys

import numpy

from osgeo import gdal


_default_gdal_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "gdal")


class CourseGdal(object):
    """Class for loading course maps from GDAL data."""
    def __init__(self, image_filename):
        self._dataset = gdal.Open(image_filename, gdal.GA_ReadOnly)
        geo_transform = self._dataset.GetGeoTransform()
        if geo_transform[2] != 0.0 or geo_transform[4] != 0.0:
            raise RuntimeError("Unable to process gdal data for " + image_filename)
        self._origin = (geo_transform[0], geo_transform[3])
        self._pixel_size = (geo_transform[1], geo_transform[5])
        self._bounds = (self.pixel_to_coord(0, self._dataset.RasterYSize),
                        self.pixel_to_coord(self._dataset.RasterXSize, 0))
        self._array = self._dataset.ReadAsArray()

    @property
    def origin(self):
        return self._origin

    @property
    def bounds(self):
        return self._bounds

    @property
    def extent(self):
        return (self.bounds[0][0], self.bounds[1][0],
                self.bounds[0][1], self.bounds[1][1])

    @property
    def array(self):
        return self._array

    @property
    def image(self):
        rows = []
        for row in xrange(0, self._dataset.RasterYSize):
            cols = []
            for col in xrange(0, self._dataset.RasterXSize):
                cols.append((self._array[0][row][col],
                             self._array[1][row][col],
                             self._array[2][row][col]))

            rows.append(cols)
        return numpy.array(rows)

    def pixel_to_coord(self, x, y):
        coord_x = self._origin[0] + self._pixel_size[0] * x
        coord_y = self._origin[1] + self._pixel_size[1] * y
        return (coord_x, coord_y)


class GdalSource(object):
    """Provides GDAL data for various known locations."""
    def __init__(self, pathname=_default_gdal_path):
        jp2_files = glob.glob(os.path.join(pathname, "*.jp2"))
        # TODO sammy support elevation.
        self._gdal = list()
        for filename in jp2_files:
            self._gdal.append(CourseGdal(filename))

    def get_gdal(self, x, y):
        for gdal in self._gdal:
            bounds = gdal.bounds
            if ((x >= bounds[0][0] and x <= bounds[1][0]) and
                (y >= bounds[0][1] and y <= bounds[1][1])):
                return gdal
        return None


if __name__ == "__main__":
    gdal_obj = CourseGdal(sys.argv[1])
    print "Origin:", gdal_obj.origin
    print "Bounds: ", gdal_obj.bounds
