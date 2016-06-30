Acquiring GDAL data:

GDAL data consists of two parts, ortho imagery and elevation.

To figure out what GDAL data to download, use Google Maps to find a
rough center lon/lat, and then figure out the extents.  To find the
extents, it can be useful to use The National Map from the USGS, found at
http://viewer.nationalmap.gov/basic

Select "Coordinates", and create a box slightly bigger than the center
point by adding/subtracting a small offset from the center point
located with Google Maps.  Once the relevant area is visible, select
"Box/Point", and draw a box around the area of interest.  Mousing over
the extents of this box is one way to find the lon/lat range which is
interesting.

Data can be downloaded from https://gdg.sc.egov.usda.gov/GDGOrder.aspx?order=MBROrder

Enter the bounding rectangle using the coordinates above.  After
checking and submitting the coordinates, pick the best elevation (the
3 meter dataset is a safe bet, but higher resolution is fine) and
ortho imagery (a recent ortho image set from the NAIP is usually a
good bet).

On the next screen, select "Extract" as the inclusion type and
"Download" as the delivery method.

Unzip the resulting files, and copy the .jp2 file into this directory,
and the .tif for elevation into the same directory with "_elev.tif" as
the end of the file name.  The GDAL data should be automatically
loaded for any course map which includes the resulting coordinates.
