#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""garagenode_receiver_mqtt.py - GarageNode receiver to publish UART messages to MQTT.

Listen on UART serial for GarageNode sender messages and publish them to MQTT message broker.
Configuration is done via `.env`file or environment variables.

Usage:
  garagenode_receiver_mqtt.py [options]
  garagenode_receiver_mqtt.py -h | --help
  garagenode_receiver_mqtt.py --version

Arguments:
  None.

Options:
  -h --help       Show this screen.
  -q --quiet      Be more quiet, show only warnings and errors.
  --simulate      Do not use serial port but simulate using file TESTDATA_FILE.
  -v --verbose    Be more verbose.
  --version       Show version.
"""
##
## LICENSE:
##
## Copyright (C) 2019-2022 Alexander Streicher
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
import os
import re
import sys
from codecs import open
import logging
import paho.mqtt.publish
import serial
from docopt import docopt
from dotenv import load_dotenv

__version__ = "1.8.0"
__date__ = "2019-09-04"
__updated__ = "2022-05-21"
__author__ = "Ixtalo"
__license__ = "AGPL-3.0+"
__email__ = "ixtalo@gmail.com"
__status__ = "Production"

###############################################################################
###############################################################################
###############################################################################

## check for Python3
if sys.version_info < (3, 0):
    sys.stderr.write("Minimum required version is Python 3.x!\n")
    sys.exit(1)

TESTDATA_FILE = '../tools/serial2file.bin'
MQTT_TIME_PERIOD_SECONDS_DEFAULT = 600

DEBUG = bool(os.environ.get("DEBUG", "").lower() in ("1", "true", "yes"))
__script_dir = os.path.dirname(os.path.realpath(__file__))

## **L:140;H:29.90;T:27.60;S1:1$$
## **L:140;H:29.90;T:27.60;S1:1;S2:1$$
## **L:140;H:nan;T:nan;S1:0$$
regex = re.compile(r"(?P<L>(L:[^;]*);)?(?P<H>(H:[^;]*);)?(?P<T>(T:[^;]*);)?(?P<S1>(S1:.);?)?(?P<S2>(S2:.);?)?")


def send_mqtt(msgs):
    if DEBUG:
        logging.warning("DEBUG mode, not sending to MQTT")
        return

    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", 1883))
    mqtt_user = os.getenv("MQTT_USER")
    mqtt_pass = os.getenv("MQTT_PASS")
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


class MessageEnvelope(object):
    def __init__(self):
        self.msgs = {}

    def __len__(self):
        return len(self.msgs)

    def __repr__(self):
        return repr(self.msgs)

    def keys(self):
        return self.msgs.keys()

    def add(self, msg: Message):
        if not isinstance(msg, Message):
            raise TypeError("msg must be of type 'Message'!")
        self.msgs[msg.name] = msg
        return self

    def get(self, key):
        return self.msgs.get(key)


def datadict2msgs(envelope: MessageEnvelope):
    topic_base = os.getenv("MQTT_TOPIC_BASE")
    msgs = []
    for key in envelope.keys():
        d = envelope.get(key)
        assert type(d) is Message
        msgs.append({'topic': topic_base + d.name, 'payload': d.value, 'retain': d.retain})
    return msgs


def look_in_stream(stream):
    """
    Heuristic and parsing of data (file/serial line) stream.
    :param stream: data stream
    :return: DataEntries object or None if not parseable
    """
    ## look for 1st signature character
    ## example:
    ## **L:140;H:29.90;T:27.60;S1:1;S2:1$$
    x = stream.read(1)
    if DEBUG:
        print(".", end="", flush=True)
    if len(x) < 1:
        ## EOF
        raise IOError('EOF reached!')
    elif x == b'*':
        ## look for 2nd signature character (it is expected to be 2nd '*'!)
        x = stream.read(1)
        if x == b'*':
            logging.debug("signature '**' found - collecting ...")
            ## now collect everything till the next end-signature '$$'
            raw = b''
            y = ''
            while y != b'$' and y != b'*':
                y = stream.read(1)
                raw += y

            logging.debug("#%d bytes collected. Decoding...", len(raw))
            try:
                ## decode bytes as unicode
                ## error handler: replace with a suitable replacement marker
                data = raw.decode("utf8", errors="replace")
                logging.debug("decoded data: %s", data)
            except UnicodeDecodeError:
                logging.error("could not utf8-decode data (#%d bytes)!", len(raw))
                return None

            ## strip signature characters
            data = data.strip('*$')

            ## try regular expression pattern matching
            m = regex.search(data)
            if m:
                logging.debug("parsed. match: %s", m)
                g = m.groupdict()
                result = MessageEnvelope()

                keystring = "L"
                group = g[keystring]
                if group:
                    value = group.removeprefix(keystring + ":").strip(";")
                    try:
                        result.add(Message('light', int(value), retain=False))
                    except ValueError:
                        pass

                keystring = "H"
                group = g[keystring]
                if group:
                    value = group.removeprefix(keystring + ":").strip(";")
                    try:
                        result.add(Message('humidity', float(value), retain=False))
                    except ValueError:
                        pass

                keystring = "T"
                group = g[keystring]
                if group:
                    value = group.removeprefix(keystring + ":").strip(";")
                    try:
                        result.add(Message('temperature', float(value), retain=False))
                    except ValueError:
                        pass

                keystring = "S1"
                group = g[keystring]
                if group:
                    value = group.removeprefix(keystring + ":").strip(";")
                    try:
                        result.add(Message('switch1', int(value), retain=True))
                    except ValueError:
                        pass

                keystring = "S2"
                group = g[keystring]
                if group:
                    value = group.removeprefix(keystring + ":").strip(";")
                    try:
                        result.add(Message('switch2', int(value), retain=True))
                    except ValueError:
                        pass

                logging.debug("result: %s", result)
                return result
            else:
                logging.warning("Problem parsing data! (no match for '%s')", data)

    return None


def handle_stream(stream):
    """
    Handle GarageNode sender UART messages.
    :param stream:  input stream, i.e., serial UART stream
    """
    assert stream.readable()

    last_dt = datetime.datetime.min
    last_light = -1
    last_switch1 = -1
    last_switch2 = -1
    while True:
        ## parse stream, look for relevant data strings
        try:
            result = look_in_stream(stream)
        except IOError as ex:
            if str(ex) == "EOF reached!":
                ## EOF reached is not an error per se...
                logging.warning(ex)
            else:
                logging.error(ex)
            break
        except Exception as ex:
            logging.exception(ex)
            break

        if result is None:
            continue
        else:
            ## flag for MQTT sending
            do_send = False

            ## extra handling for light sensor
            if result.get('light'):
                if last_light != -1 and abs(last_light - result.get('light').value) > 50:  ## skip initial
                    logging.info('Significant light change detected!')
                    do_send = True
                last_light = result.get('light').value

            ## extra handling for switches
            if result.get('switch1'):
                value = result.get('switch1').value
                if last_switch1 != value:
                    logging.info('Switch1 change detected! (value=%d)', value)
                    ## force sending
                    do_send = True
                    last_switch1 = value
            if result.get('switch2'):
                value = result.get('switch2').value
                if last_switch2 != value:
                    logging.info('Switch2 change detected! (value=%d)', value)
                    ## force sending
                    do_send = True
                    last_switch2 = value

            ## periodic sending, make sure to send not too often
            now = datetime.datetime.now()
            tdiff_seconds = (now - last_dt).total_seconds()
            logging.debug("result: %s, tdiff_seconds: %d", result, tdiff_seconds)
            if tdiff_seconds > int(os.getenv("MQTT_TIME_PERIOD_SECONDS", MQTT_TIME_PERIOD_SECONDS_DEFAULT)):
                last_dt = now
                do_send = True

            ## only send if a condition from above is true
            if do_send:
                ## converting result array to MQTT messages
                msgs = datadict2msgs(result)
                ## send to MQTT
                send_mqtt(msgs)


def main():
    arguments = docopt(__doc__, version=f"garagenode_receiver_mqtt {__version__} ({__updated__})")
    arg_verbose = arguments["--verbose"]
    arg_simulate = arguments["--simulate"]
    arg_quiet = arguments["--quiet"]

    assert not (arg_verbose and arg_quiet), "CLI parameters verbose and quiet are mutually exclusive!"

    ## setup logging
    logging.basicConfig(level=logging.INFO,
                        stream=sys.stderr,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    if arg_verbose or DEBUG:
        logging.getLogger("").setLevel(logging.DEBUG)
    if arg_quiet:
        logging.getLogger("").setLevel(logging.WARNING)

    ## load configuration environment variables from .env file
    load_dotenv()
    assert os.getenv("MQTT_TOPIC_BASE")
    assert int(os.getenv("MQTT_TIME_PERIOD_SECONDS", MQTT_TIME_PERIOD_SECONDS_DEFAULT))

    logging.info("version: %s (%s)", __version__, __updated__)
    logging.info("SERIAL_PORT: %s", os.getenv("SERIAL_PORT"))
    logging.info("MQTT_TOPIC_BASE: %s", os.getenv("MQTT_TOPIC_BASE"))
    logging.info("MQTT_TIME_PERIOD_SECONDS: %s", os.getenv("MQTT_TIME_PERIOD_SECONDS"))

    ## setup input stream
    if arg_simulate:
        logging.warning("!!! DEBUG/SIMULATE MODE !!! TESTDATA_FILE: %s", os.path.realpath(TESTDATA_FILE))
        ## for debugging use a binary capture sample
        stream = open(TESTDATA_FILE, 'rb')
    else:
        assert os.getenv("SERIAL_PORT")
        ## setup real serial device
        stream = serial.Serial(
            port=os.getenv("SERIAL_PORT"),
            baudrate=int(os.getenv("SERIAL_BAUD", 9600)),
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )
    
    logging.info("input stream: %s", stream)

    ## handle stream, i.e., listen for incoming data
    handle_stream(stream)


if __name__ == '__main__':
    if DEBUG:
        # sys.argv.append('--verbose')
        pass
    if os.environ.get("PROFILE", "").lower() in ("true", "1", "yes"):
        import cProfile
        import pstats
        profile_filename = f"{__file__}.profile"
        cProfile.run('main()', profile_filename)
        with open(f'{profile_filename}.txt', 'w', encoding="utf8") as statsfp:
            profile_stats = pstats.Stats(profile_filename, stream=statsfp)
            stats = profile_stats.strip_dirs().sort_stats('cumulative')
            stats.print_stats()
        sys.exit(0)
    sys.exit(main())
