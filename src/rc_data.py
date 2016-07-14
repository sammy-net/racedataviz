# Copyright 2016 Sam Creasey, sammy@sammy.net.  All rights reserved.
#
# TODO sammy find the right GPL3 preamble for this

import copy
import csv
import math

from pyproj import Proj

INTERVAL_FIELD = 'Interval'
UTC_FIELD = 'Utc'
RELATIVE_TIME_FIELD = 'Relative time'
DISTANCE_FIELD = 'Distance'
RELATIVE_DISTANCE_FIELD = 'Relative distance'

class _Record(object):
    def __init__(self, interval, utc, value):
        self.interval = int(interval)
        self.utc = int(utc) / 1000.
        if isinstance(value, str) and not len(value):
            self.value = None
        else:
            self.value = float(value)

class _Field(object):
    def __init__(self, key, name, unit, minval, maxval, step):
        self.key = key
        self.name = name
        self.unit = unit
        self.minval = minval
        self.maxval = maxval
        self.step = step
        self.records = list()

    def add_record(self, interval, utc, value):
        self.records.append(_Record(interval, utc, value))

    def interpolate_records(self):
        present = list()
        for idx, records in enumerate(self.records):
            if records.value is None:
                continue
            present.append(idx)
        if len(present) == len(self.records):
            # Nothing to do, we're full!
            return

        # Fill out the start and end ranges with the first/last known value
        for idx in xrange(present[0]):
            self.records[idx].value = self.records[present[0]].value
            present.append(idx)
        for idx in xrange(present[-1], len(self.records)):
            self.records[idx].value = self.records[present[-1]].value
            present.append(idx)

        present.sort()
        # Fill in any gaps resursively.
        for idx in xrange(len(present) - 1):
            cur = present[idx]
            next_present = present[idx + 1]
            assert self.records[cur].value is not None
            assert self.records[next_present].value is not None
            if next_present == cur or next_present == cur + 1:
                continue
            middle = cur + ((next_present - cur) / 2)
            assert self.records[middle].value is None
            self.records[middle].value = (self.records[cur].value +
                                          self.records[next_present].value) / 2.
        self.interpolate_records()
        assert not None in [record.value for record in self.records]

class RcData(object):
    def __init__(self, filename):
        self.filename = filename
        self.csv = csv.DictReader(open(filename))
        self.records = dict()
        self.relative_start_time = None

        for fieldname in self.csv.fieldnames:
            field_params = fieldname.split('|')
            name = field_params[0]
            if name == INTERVAL_FIELD:
                self.interval_key = fieldname
            elif name == UTC_FIELD:
                self.utc_key = fieldname
            new_field = _Field(*([fieldname] + field_params))
            self.records[new_field.name] = new_field

        for row in self.csv:
            interval = row[self.interval_key]
            utc = row[self.utc_key]
            for (key, value) in row.iteritems():
                name = key.split('|')[0]
                self.records[name].add_record(interval, utc, value)

        for record in self.records.itervalues():
            record.interpolate_records()

        self.update_relative_time(self.records[UTC_FIELD].records[0].utc)

    def update_relative_time(self, relative_start):
        self.relative_start_time = relative_start
        self.records[RELATIVE_TIME_FIELD] = copy.deepcopy(
            self.records[UTC_FIELD])
        self.records[RELATIVE_TIME_FIELD].name = RELATIVE_TIME_FIELD
        min_time = 1e6
        min_time_idx = -1
        for idx, record in enumerate(self.records[RELATIVE_TIME_FIELD].records):
            record.value = record.utc - relative_start;
            if abs(record.value) < min_time:
                min_time = record.value
                min_time_idx = idx

        min_distance = self.records[DISTANCE_FIELD].records[min_time_idx].value
        self.records[RELATIVE_DISTANCE_FIELD] = copy.deepcopy(
            self.records[DISTANCE_FIELD])
        self.records[RELATIVE_DISTANCE_FIELD].name = RELATIVE_DISTANCE_FIELD
        for record in self.records[RELATIVE_DISTANCE_FIELD].records:
            record.value = record.value - min_distance

    def all(self, record):
        return [x.value for x in self.records[record].records]

    def times(self):
        return [x.utc for x in self.records[UTC_FIELD].records]

    def relative_times(self):
        return self.all(RELATIVE_TIME_FIELD)

    def value_at(self, record, index):
        return self.records[record].records[index].value

    def relative_index(self, relative_time):
        # Bisect through the relative times field and return the index
        # which corresponds to this element.
        array = self.relative_times()
        if len(array) == 0:
            return None
        if relative_time < array[0]:
            return None

        lower = 0
        upper = len(array)

        while abs(lower - upper) > 1:
            mid = (lower + upper) / 2
            value = array[mid]
            if relative_time < value:
                upper = mid
            else:
                lower = mid

        return lower

    def get_utm_data(self):
        """Return the position data for the logfile.  Returns a list of tuples
        of (relative_time, eastings, northings).
        """

        relative_times = self.relative_times()
        lats = self.all('Latitude')
        lons = self.all('Longitude')
        assert len(relative_times) == len(lats)
        assert len(relative_times) == len(lons)

        utm_zone = math.ceil((lons[0] + 180) / 6)
        p = Proj(proj='utm', zone=utm_zone, ellps='WGS84')

        utms = list()
        for i, time in enumerate(relative_times):
            x, y = p(lons[i], lats[i])
            utms.append((time, x, y))

        return utms
