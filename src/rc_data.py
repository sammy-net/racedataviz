# Copyright 2016 Sam Creasey, sammy@sammy.net.  All rights reserved.
#
# TODO sammy find the right GPL3 preamble for this

import copy
import csv

INTERVAL_FIELD = 'Interval'
UTC_FIELD = 'Utc'
RELATIVE_TIME_FIELD = 'Relative time'

class _Record(object):
    def __init__(self, interval, utc, value):
        self.interval = int(interval)
        self.utc = int(utc) / 1000.
        if not value:
            self.value = 0.
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

class RcData(object):
    def __init__(self, filename):
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

        self.update_relative_time(self.records[UTC_FIELD].records[0].utc)

    def update_relative_time(self, relative_start):
        self.relative_start_time = relative_start
        self.records[RELATIVE_TIME_FIELD] = copy.deepcopy(
            self.records[UTC_FIELD])
        self.records[RELATIVE_TIME_FIELD].name = RELATIVE_TIME_FIELD
        for record in self.records[RELATIVE_TIME_FIELD].records:
            record.value = record.utc - relative_start;

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
