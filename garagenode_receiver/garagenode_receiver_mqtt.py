#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""garagenode_receiver_mqtt.py - GarageNode receiver to publish UART messages to MQTT.

Listen on UART serial for GarageNode sender messages and publish them to MQTT message broker.
The MQTT configuration is done via garagenode_receiver_mqtt.json.

Usage:
  garagenode_receiver_mqtt.py <config.json>
  garagenode_receiver_mqtt.py -h | --help
  garagenode_receiver_mqtt.py --version

Arguments:
  config.json     Configuration file in JSON format.

Options:
  -h --help       Show this screen.
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

import datetime
import json
import os
import re
import sys
from codecs import open
import logging
import paho.mqtt.publish
import serial
from docopt import docopt

__version__ = "1.2"
__date__ = "2019-09-04"
__updated__ = "2019-12-25"
__author__ = "Ixtalo"
__license__ = "AGPL-3.0+"
__email__ = "ixtalo@gmail.com"
__status__ = "Production"

## Time in seconds between MQTT messages
MQTT_TIME_PERIOD = 600

###############################################################################
###############################################################################
###############################################################################

## check for Python3
if sys.version_info < (3, 0):
    sys.stderr.write("Minimum required version is Python 3.x!\n")
    sys.exit(1)

DEBUG = os.environ.get('DEBUG')
TESTRUN = 0
PROFILE = 0
__script_dir = os.path.dirname(os.path.realpath(__file__))

## **L:140;H:29.90;T:27.60;R:0$$
## **L:140;H:nan;T:nan;R:0$$
regex = re.compile("(?:L:(\d+));(?:H:(\d+\.\d\d?|nan));(?:T:(\d+\.\d\d?|nan));(?:R:(\d))")

## configuration, e.g., from JSON file
configuration = {}


def send_mqtt(msgs):
    if DEBUG:
        logging.warning("DEBUG mode, not sending to MQTT")
        return

    global configuration
    mqtt_host = configuration.get('mqtt_host')
    mqtt_port = configuration.get('mqtt_port')
    mqtt_user = configuration.get('mqtt_user', None)
    mqtt_pass = configuration.get('mqtt_pass', None)
    assert mqtt_host, 'Configuration mqtt_host is mandatory!'
    assert mqtt_port, 'Configuration mqtt_port is mandatory!'
    logging.debug("Sending to MQTT... (%s:%d)", mqtt_host, mqtt_port)
    paho.mqtt.publish.multiple(msgs=msgs,
                               hostname=mqtt_host,
                               port=mqtt_port,
                               client_id='garagenode',
                               ## password could be None
                               auth={'username': mqtt_user, 'password': mqtt_pass} if mqtt_user else None
                               )


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

    def add(self, entry: Message):
        assert type(entry) is Message
        self.entries[entry.name] = entry
        return self

    def get(self, key):
        return self.entries.get(key)


def datadict2msgs(dataentries: DataEntries):
    global configuration
    topic_base = configuration['mqtt_topic_base']

    msgs = []
    for key in dataentries.keys():
        d = dataentries[key]
        assert type(d) is Message
        msgs.append({'topic': topic_base + d.name, 'payload': d.value, 'retain': d.retain})
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


def handle_stream(stream):
    """
    Handle GarageNode sender UART messages.
    :param stream:  input stream, i.e., serial UART stream
    """
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
            logging.debug(result, tdiff_seconds)
            if tdiff_seconds > MQTT_TIME_PERIOD:
                last_dt = now
                do_send = True

            ## only send if a condition from above is true
            if do_send:
                ## converting result array to MQTT messages
                msgs = datadict2msgs(result)
                ## send to MQTT
                send_mqtt(msgs)


def load_config(filename):
    """
    Load configuration from file
    :param filename:
    """
    global configuration
    config_filepath = os.path.join(__script_dir, filename)
    if not os.path.exists(config_filepath):
        raise RuntimeError("No config file! Expected:%s" % os.path.abspath(config_filepath))
    with open(config_filepath) as fin:
        logging.debug('Loading config JSON ... (%s)', config_filepath)
        configuration = json.load(fin)


def main():
    arguments = docopt(__doc__, version="serial2mqtt %s (%s)" % (__version__, __updated__))
    # print(arguments)

    ## setup logging
    logging.basicConfig(level=logging.DEBUG if DEBUG else logging.WARN)

    ## load configuration from JSON file
    load_config(arguments['<config.json>'])

    ## setup input stream
    serial_port = configuration['serial_port']
    serial_baud = configuration['serial_baud']
    if DEBUG:
        ## for debugging use a binary capture sample
        stream = open('../tools/serial2file.bin', 'rb')
        print(stream.name)
    else:
        ## setup real serial device
        stream = serial.Serial(
            port=serial_port,
            baudrate=serial_baud,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )

    ## handle stream, i.e., listen for incoming data
    handle_stream(stream)


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
