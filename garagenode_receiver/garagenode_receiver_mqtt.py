#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""garagenode_receiver_mqtt.py - SHORT DESC

LONG DESC

Usage:
  garagenode_receiver_mqtt.py <serialport> <serialbaud> [--mqtt-host=IP] [--mqtt-port=N]
  garagenode_receiver_mqtt.py -h | --help
  garagenode_receiver_mqtt.py --version

Arguments:
  serialport      Serial port device, e.g. /dev/ttyACM0.
  serialbaud      Serial port baud speed, e.g. 9600.

Options:
  -h --help       Show this screen.
  --mqtt-host=IP  MQTT host address (IP or hostname) [default: localhost].
  --mqtt-port=N   MQTT port number [default: 1883].
  --version       Show version.
"""
##
## LICENSE:
##
## Copyright (C) 2019 Alexander Streicher
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU Affero General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##

import os
import re
import sys
import serial
import datetime
from codecs import open
import paho.mqtt.publish
from docopt import docopt

__version__ = "1.0"
__date__ = "2019-09-04"
__updated__ = "2019-09-05"
__author__ = "Ixtalo"
__license__ = "AGPL-3.0+"
__email__ = "ixtalo@gmail.com"
__status__ = "Production"

## Time in seconds between MQTT messages
MQTT_TIME_PERIOD = 600
## Base string for the MQTT topic
MQTT_TOPIC_BASE = '/garagenode/'

###############################################################################
###############################################################################
###############################################################################

DEBUG = os.environ.get('DEBUG')
TESTRUN = 0
PROFILE = 0
__script_dir = os.path.dirname(os.path.realpath(__file__))

## check for Python3
if sys.version_info < (3, 0):
    sys.stderr.write("Minimum required version is Python 3.x!\n")
    sys.exit(1)

## **L:140;H:29.90;T:27.60;R:0$$
## **L:140;H:nan;T:nan;R:0$$
regex = re.compile('(?:L:(\d+));(?:H:(\d+\.\d\d?|nan));(?:T:(\d+\.\d\d?|nan));(?:R:(\d))')


def send_mqtt(msgs, mqtt_host, mqtt_port):
    paho.mqtt.publish.multiple(msgs=msgs, hostname=mqtt_host, port=mqtt_port, client_id='garagenode')


## data "struct"
class Message(object):
    def __init__(self, name: str, value, retain: bool = False):
        self.name = name
        self.value = value
        self.retain = retain

    def __repr__(self):
        return "%s=%s (retain: %s)" % (self.name, self.value, self.retain)


class DataEntries(object):
    def __init__(self):
        self.entries = {}

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, item):
        return self.get(item)

    def __repr__(self):
        return repr(self.entries)

    def keys(self):
        return self.entries.keys()

    def add(self, entry:Message):
        assert type(entry) is Message
        self.entries[entry.name] = entry
        return self

    def get(self, key):
        return self.entries.get(key)


def datadict2msgs(dataentries: DataEntries):
    msgs = []
    for key in dataentries.keys():
        d = dataentries[key]
        assert type(d) is Message
        msgs.append({'topic': MQTT_TOPIC_BASE + d.name, 'payload': d.value, 'retain': d.retain})
    return msgs


def look_in_stream(stream):
    """
    Heuristic and parsing of data (file/serial line) stream.
    :param stream: data stream
    :return: DataEntries
    """
    ## look for 1st signature character
    ## example:
    ## **L:140;H:29.90;T:27.60;R:0$$
    x = stream.read(1)
    if len(x) < 1:
        ## EOF
        raise IOError('EOF reached!')
    elif x == b'*':
        ## look for 2nd signature character
        x = stream.read(1)
        if x == b'*':
            ## signature '**' found
            ## now, collect everything till the end-signature ('$$')
            raw = b''
            y = ''
            while y != b'$' and y != b'*':
                y = stream.read(1)
                raw += y

            ####print(raw, stream.tell())

            try:
                ## decode as unicode and strip signature characters
                data = raw.decode('utf8').strip('*$')
            except UnicodeDecodeError:
                ## TODO log exception
                data = 'ERROR'

            ## try regular expression pattern matching
            m = regex.search(data)
            if m:
                result = DataEntries()
                try:
                    result.add(Message('light', int(m.group(1)), False))
                except ValueError:
                    pass
                if not m.group(2) == 'nan':
                    try:
                        result.add(Message('humidity', float(m.group(2)), False))
                    except ValueError:
                        pass
                if not m.group(3) == 'nan':
                    try:
                        result.add(Message('temperature', float(m.group(3)), False))
                    except ValueError:
                        pass
                try:
                    result.add(Message('door_open', int(m.group(4)), True))
                except ValueError:
                    pass
                return result

    return None


def handle_stream(stream, mqtt_host, mqtt_port, mqtt_func=send_mqtt):
    assert stream.readable()

    last_dt = datetime.datetime.min
    last_light = -1
    last_door = -1
    while True:
        ## parse stream, look for relevant data strings
        try:
            result = look_in_stream(stream)
        except Exception as ex:
            print(ex)
            break

        if result is None:
            continue
        else:
            ## flag for MQTT sending
            do_send = False

            ## extra handling for light sensor
            if result.get('light'):
                if last_light != -1 and abs(last_light - result['light'].value) > 50:  ## skip initial
                    print('Significant light change detected!')
                    do_send = True
                last_light = result['light'].value

            ## extra handling for door state sensor (reed switch)
            if result.get('door_open'):
                if last_door != -1 and last_door != result['door_open'].value:
                    print('Door open state change detected!')
                    do_send = True
                last_door = result['door_open'].value

            ## periodic sending, make sure to send not too often
            now = datetime.datetime.now()
            tdiff_seconds = (now - last_dt).total_seconds()
            print(result, tdiff_seconds)
            if tdiff_seconds > MQTT_TIME_PERIOD:
                last_dt = now
                do_send = True

            ## only send if a condition from above is true
            if do_send and mqtt_func:
                msgs = datadict2msgs(result)
                #send_mqtt(msgs, mqtt_host, mqtt_port)
                mqtt_func(msgs, mqtt_host, mqtt_port)


def main():
    arguments = docopt(__doc__, version="serial2mqtt %s (%s)" % (__version__, __updated__))
    # print(arguments)

    serial_port = arguments['<serialport>']
    serial_baud = arguments['<serialbaud>']
    mqtt_host = arguments['--mqtt-host']
    mqtt_port = arguments['--mqtt-port']

    if DEBUG:
        stream = open('../tools/serial2file.bin', 'rb')
        print(stream.name)
    else:
        stream = serial.Serial(
            port=serial_port,
            baudrate=serial_baud,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )

    handle_stream(stream, mqtt_host, mqtt_port, mqtt_func=None if DEBUG else send_mqtt)


if __name__ == "__main__":
    if DEBUG:
        # sys.argv.append("-v")
        # sys.argv.append("--debug")
        # sys.argv.append("-h")
        pass
    if TESTRUN:
        import doctest

        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats

        profile_filename = __file__ + '.profile.bin'
        cProfile.run('main()', profile_filename)
        with open("%s.txt" % profile_filename, "wb") as statsfp:
            p = pstats.Stats(profile_filename, stream=statsfp)
            stats = p.strip_dirs().sort_stats('cumulative')
            stats.print_stats()
        sys.exit(0)
    sys.exit(main())
