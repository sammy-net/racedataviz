# Copyright 2016 Sam Creasey, sammy@sammy.net.  All rights reserved.
#
# TODO sammy find the right GPL3 preamble for this

import csv

class _Record(object):
    def __init__(self, interval, utc, value):
        self.interval = interval
        self.utc = utc
        self.value = value

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

        for fieldname in self.csv.fieldnames:
            field_params = fieldname.split('|')
            name = field_params[0]
            if name == 'Interval':
                self.interval_key = fieldname
                continue
            elif name == 'Utc':
                self.utc_key = fieldname
                continue
            new_field = _Field(*([fieldname] + field_params))
            self.records[new_field.name] = new_field

        for row in self.csv:
            interval = row[self.interval_key]
            utc = row[self.utc_key]
            for (key, value) in row.iteritems():
                name = key.split('|')[0]
                if (name == 'Interval' or name == 'Utc'):
                    continue
                self.records[name].add_record(interval, utc, value)
