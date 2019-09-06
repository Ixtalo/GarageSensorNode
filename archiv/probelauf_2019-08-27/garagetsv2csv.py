#!/usr/bin/python3

import sys
import time
import datetime
import re

regex = re.compile('\*(?:L(\d+))+(?:H(\d\d\.\d\d))+(?:T(\d\d\.\d\d))+')

def print_error(s):
    print(s, file=sys.stderr)


with open("garage.tsv") as fin:
    for i, line in enumerate(fin):

        if i % 10 != 0:
            continue

        try:
            timestamp, ctime_str, data = line.strip().split('\t',3)
        except (ValueError, TypeError) as ex:
            print_error("Invalid line %d: %s" % (i, ex))
            continue

        m = regex.match(data)
        if not m:
            #print_error("Invalid data in line %d: %s" % (i, data))
            print_error("Invalid data in line %d" % i)
            continue

        assert len(m.groups()) == 3

        dt = datetime.datetime.fromtimestamp(float(timestamp))
        l = int(m.group(1))
        h = float(m.group(2))
        t = float(m.group(3))

        row = (dt, l, h, t)
        print(';'.join([str(s) for s in row]))

