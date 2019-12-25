
import io
import garagenode_receiver_mqtt
from garagenode_receiver_mqtt import *
import unittest
from unittest.mock import MagicMock, patch


class MyTestCase(unittest.TestCase):

    def setUp(self):
        garagenode_receiver_mqtt.configuration = {
            'mqtt_host': 'localhost',
            'mqtt_port': 1883,
            'mqtt_user': 'foo',
            'mqtt_pass': 'bar',
            "mqtt_topic_base": "/foobar/"
        }
        garagenode_receiver_mqtt.send_mqtt = MagicMock(logging.warning("MOCKED send_mqtt!! Doing nothing."))

    def test_datadict2msgs(self):
        ## basic result type checking
        actual = datadict2msgs({})
        assert actual is not None
        assert type(actual) is list
        assert actual == []

        ## a single element
        actual = datadict2msgs(DataEntries().add(Message('light', 11, False)))
        assert actual == [{'payload': 11, 'retain': False, 'topic': '/foobar/light'}]

        ## another single element
        actual = datadict2msgs(DataEntries().add(Message('light', 11, True)))
        assert actual == [{'payload': 11, 'retain': True, 'topic': '/foobar/light'}]

        ## change topic base
        garagenode_receiver_mqtt.configuration['mqtt_topic_base'] = 'blubba/'
        actual = datadict2msgs(DataEntries().add(Message('light', 11, False)))
        assert actual == [{'payload': 11, 'retain': False, 'topic': 'blubba/light'}]

        ## checking of unhandled names
        actual = datadict2msgs(DataEntries().add(Message('AAA', 11, False)))
        assert actual == [{'payload': 11, 'retain': False, 'topic': 'blubba/AAA'}]

        ## checking of handled and undhandled
        actual = datadict2msgs(DataEntries().add(Message('AAA', 11, False)).add(Message('light', 22, False)))
        assert actual == [{'payload': 11, 'retain': False, 'topic': 'blubba/AAA'}, {'payload': 22, 'retain': False, 'topic': 'blubba/light'}]

    def test_handle_stream_empty(self):
        ## check with empty stream
        garagenode_receiver_mqtt.handle_stream(io.BytesIO())

    def test_handle_stream_example(self):
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        stream.write(b'......**L:11;H:29.90;T:27.60;R:0$$.......')
        stream.write(b'...............')
        stream.write(b'**L:444;H:nan;T:nan;R:1$$')
        stream.write(b'...............')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 2 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        assert len(msgs) == 4
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/light', 'payload': 11, 'retain': False}, msgs[0]
