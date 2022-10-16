#!pytest

import io
import os

import pytest

import garagenode_receiver_mqtt
from garagenode_receiver_mqtt import *
import unittest
from unittest.mock import MagicMock

garagenode_receiver_mqtt.DEBUG = 1
os.environ["MQTT_TOPIC_BASE"] = "/foobar/"


class MessageEnvelopeTests(unittest.TestCase):

    @staticmethod
    def test_add():
        ## prepare
        instance = MessageEnvelope()
        actual = instance.add(Message("name1", "foobar"))
        ## check
        assert isinstance(actual, MessageEnvelope)

    @staticmethod
    def test_add_invalid():
        ## prepare
        instance = MessageEnvelope()
        with pytest.raises(TypeError):
            instance.add([])
        with pytest.raises(TypeError):
            instance.add("")
        with pytest.raises(TypeError):
            instance.add(0)
        with pytest.raises(TypeError):
            instance.add(())
        with pytest.raises(TypeError):
            instance.add({})
        with pytest.raises(TypeError):
            instance.add(object)

    @staticmethod
    def test_get():
        ## prepare
        instance = MessageEnvelope()
        instance.add(Message("name1", "foobar"))
        ## action
        message = instance.get("name1")
        ## check
        assert message.name == "name1"
        assert message.value == "foobar"

    @staticmethod
    def test_repr():
        ## prepare
        instance = MessageEnvelope()
        instance.add(Message("name1", "foobar"))
        ## check
        assert repr(instance) == "{'name1': name1=foobar (retain: False)}"
        assert str(instance) == "{'name1': name1=foobar (retain: False)}"

    @staticmethod
    def test_keys():
        ## prepare
        instance = MessageEnvelope()
        instance.add(Message("name1", "foobar1"))
        instance.add(Message("name2", "foobar2"))
        ## action
        keys = instance.keys()
        ## check
        assert list(keys) == ["name1", "name2"]

    @staticmethod
    def test_len():
        ## prepare
        instance = MessageEnvelope()
        assert len(instance) == 0
        instance.add(Message("name1", "foobar1"))
        instance.add(Message("name2", "foobar2"))
        ## check
        assert len(instance) == 2

    @staticmethod
    def test_len_empty():
        instance = MessageEnvelope()
        assert len(instance) == 0


class MyTestCase(unittest.TestCase):

    def setUp(self):
        garagenode_receiver_mqtt.send_mqtt = MagicMock(logging.warning("MOCKED send_mqtt!! Doing nothing."))

    @staticmethod
    def test_datadict2msgs():
        ## basic result type checking
        actual = datadict2msgs({})
        assert actual is not None
        assert type(actual) is list
        assert actual == []

        ## a single element
        actual = datadict2msgs(MessageEnvelope().add(Message('light', 11, False)))
        assert actual == [{'payload': 11, 'retain': False, 'topic': '/foobar/light'}]

        ## another single element
        actual = datadict2msgs(MessageEnvelope().add(Message('light', 11, True)))
        assert actual == [{'payload': 11, 'retain': True, 'topic': '/foobar/light'}]

        ## checking of unhandled names
        actual = datadict2msgs(MessageEnvelope().add(Message('AAA', 11, False)))
        assert actual == [{'payload': 11, 'retain': False, 'topic': '/foobar/AAA'}]

        ## checking of handled and undhandled
        actual = datadict2msgs(MessageEnvelope().add(Message('AAA', 11, False)).add(Message('light', 22, False)))
        assert actual == [
            {'payload': 11, 'retain': False, 'topic': '/foobar/AAA'},
            {'payload': 22, 'retain': False, 'topic': '/foobar/light'}
        ]

    @staticmethod
    def test_handle_stream_empty():
        ## check with empty stream
        garagenode_receiver_mqtt.handle_stream(io.BytesIO())

    @staticmethod
    def test_handle_stream_ok():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        stream.write(b'......**L:11;H:29.90;T:27.60;S1:1;S2:1$$.......')
        stream.write(b'...............')
        stream.write(b'**L:444;H:nan;T:nan;S1:1;S2:1$$')
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
        print(len(msgs), msgs)
        assert len(msgs) == 5
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/light', 'payload': 11, 'retain': False}, msgs[0]
        assert msgs[1] == {'topic': '/foobar/humidity', 'payload': 29.90, 'retain': False}, msgs[1]
        assert msgs[2] == {'topic': '/foobar/temperature', 'payload': 27.60, 'retain': False}, msgs[2]
        assert msgs[3] == {'topic': '/foobar/switch1', 'payload': 1, 'retain': True}, msgs[3]
        assert msgs[4] == {'topic': '/foobar/switch2', 'payload': 1, 'retain': True}, msgs[4]

    @staticmethod
    def test_handle_stream_ok_negativetemperature():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        stream.write(b'......**L:11;H:29.90;T:-1.60;S1:1;S2:1$$.......')
        stream.write(b'...............')
        stream.write(b'**L:444;H:nan;T:nan;S1:1;S2:1$$')
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
        print(len(msgs), msgs)
        assert len(msgs) == 5
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/light', 'payload': 11, 'retain': False}, msgs[0]
        assert msgs[1] == {'topic': '/foobar/humidity', 'payload': 29.90, 'retain': False}, msgs[1]
        assert msgs[2] == {'topic': '/foobar/temperature', 'payload': -1.6, 'retain': False}, msgs[2]
        assert msgs[3] == {'topic': '/foobar/switch1', 'payload': 1, 'retain': True}, msgs[3]
        assert msgs[4] == {'topic': '/foobar/switch2', 'payload': 1, 'retain': True}, msgs[4]

    @staticmethod
    def test_handle_stream_incompletesignature1():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## missing 2nd '*'!
        stream.write(b'......*L:11;H:29.90;T:27.60;S1:1;S2:1$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 0 == garagenode_receiver_mqtt.send_mqtt.call_count

    @staticmethod
    def test_handle_stream_incompletesignature2():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## missing 2nd '$'!
        ## (this does work though because only 1 '$' is acutally needed)
        stream.write(b'......**L:11;H:29.90;T:27.60;S1:1;S2:1$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 5
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/light', 'payload': 11, 'retain': False}, msgs[0]
        assert msgs[1] == {'topic': '/foobar/humidity', 'payload': 29.90, 'retain': False}, msgs[1]
        assert msgs[2] == {'topic': '/foobar/temperature', 'payload': 27.60, 'retain': False}, msgs[2]
        assert msgs[3] == {'topic': '/foobar/switch1', 'payload': 1, 'retain': True}, msgs[3]
        assert msgs[4] == {'topic': '/foobar/switch2', 'payload': 1, 'retain': True}, msgs[4]

    @staticmethod
    def test_handle_stream_wrongdata1():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## no number values but strings (which is wrong)
        stream.write(b'......**L:a;H:b;T:c;S1:d;S2:e$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 0
        assert type(msgs) is list

    @staticmethod
    def test_handle_stream_wrongdata2():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## only H: and R: are good
        stream.write(b'......**L:a;H:22;T:c;S1:0$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 2
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/humidity', 'payload': 22, 'retain': False}, msgs[0]
        assert msgs[1] == {'topic': '/foobar/switch1', 'payload': 0, 'retain': True}, msgs[1]

    @staticmethod
    def test_handle_stream_wrongdata3():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## no number values but strings (which is wrong)
        stream.write(b'......**L:a;H:b;T:c;S1:1$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 1
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/switch1', 'payload': 1, 'retain': True}, msgs[0]

    @staticmethod
    def test_handle_stream_missing1():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## L: is missing, T: is wrong
        stream.write(b'......**H:22;T:c;S1:0$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 2   ## only H: and R: are good
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/humidity', 'payload': 22, 'retain': False}, msgs[0]
        assert msgs[1] == {'topic': '/foobar/switch1', 'payload': 0, 'retain': True}, msgs[1]

    @staticmethod
    def test_handle_stream_missing2():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        stream.write(b'......**T:-99.99;$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 1
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/temperature', 'payload': -99.99, 'retain': False}, msgs[0]

    @staticmethod
    def test_handle_stream_missing3():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        stream.write(b'......**S1:1$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 1
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/switch1', 'payload': 1, 'retain': True}, msgs[0]

    @staticmethod
    def test_handle_stream_missing4():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        stream.write(b'......**x:y$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 0
        assert type(msgs) is list

    @staticmethod
    def test_handle_stream_invalidunicode():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## no number values but strings (which is wrong)
        stream.write(b'......**L:\xaf;H:22;T:33;S1:0$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 3
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/humidity', 'payload': 22, 'retain': False}, msgs[0]
        assert msgs[1] == {'topic': '/foobar/temperature', 'payload': 33, 'retain': False}, msgs[1]
        assert msgs[2] == {'topic': '/foobar/switch1', 'payload': 0, 'retain': True}, msgs[2]

    @staticmethod
    def test_handle_stream_switch1_0():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        stream.write(b'......**S1:0$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 1
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/switch1', 'payload': 0, 'retain': True}, msgs[0]

    @staticmethod
    def test_handle_stream_switch1_1():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        stream.write(b'......**S1:1$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 1
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/switch1', 'payload': 1, 'retain': True}, msgs[0]

    @staticmethod
    def test_handle_stream_switch2_0():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        stream.write(b'......**S2:0$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 1
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/switch2', 'payload': 0, 'retain': True}, msgs[0]

    @staticmethod
    def test_handle_stream_switch2_1():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        stream.write(b'......**S2:1$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 1
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/switch2', 'payload': 1, 'retain': True}, msgs[0]

    @staticmethod
    def test_handle_stream_semicolon1():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## S1/S2 do not really need semi-colons
        stream.write(b'......**L:11;H:29.90;T:27.60;S1:1S2:1$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 5
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/light', 'payload': 11, 'retain': False}, msgs[0]
        assert msgs[1] == {'topic': '/foobar/humidity', 'payload': 29.90, 'retain': False}, msgs[1]
        assert msgs[2] == {'topic': '/foobar/temperature', 'payload': 27.60, 'retain': False}, msgs[2]
        assert msgs[3] == {'topic': '/foobar/switch1', 'payload': 1, 'retain': True}, msgs[3]
        assert msgs[4] == {'topic': '/foobar/switch2', 'payload': 1, 'retain': True}, msgs[4]

    @staticmethod
    def test_handle_stream_semicolon1():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## additional (optional) semi-colon for S2
        stream.write(b'......**L:11;H:29.90;T:27.60;S1:1S2:1;$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 5
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/light', 'payload': 11, 'retain': False}, msgs[0]
        assert msgs[1] == {'topic': '/foobar/humidity', 'payload': 29.90, 'retain': False}, msgs[1]
        assert msgs[2] == {'topic': '/foobar/temperature', 'payload': 27.60, 'retain': False}, msgs[2]
        assert msgs[3] == {'topic': '/foobar/switch1', 'payload': 1, 'retain': True}, msgs[3]
        assert msgs[4] == {'topic': '/foobar/switch2', 'payload': 1, 'retain': True}, msgs[4]

    @staticmethod
    def test_handle_stream_corrupts1():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## value for S1 is missing
        stream.write(b'......**L:11;H:29.90;T:27.60;S1:;S2:1;$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 4
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/light', 'payload': 11, 'retain': False}, msgs[0]
        assert msgs[1] == {'topic': '/foobar/humidity', 'payload': 29.90, 'retain': False}, msgs[1]
        assert msgs[2] == {'topic': '/foobar/temperature', 'payload': 27.60, 'retain': False}, msgs[2]
        assert msgs[3] == {'topic': '/foobar/switch2', 'payload': 1, 'retain': True}, msgs[3]

    @staticmethod
    def test_handle_stream_corrupts1_missingsemicolon():
        ## check with 2 data elements in stream
        stream = io.BytesIO()
        ## value for S1 is missing *and* no dividing semi-colon!
        stream.write(b'......**L:11;H:29.90;T:27.60;S1:S2:1;$$.......')
        stream.seek(0)  ## needed!

        ## prepare mocking
        garagenode_receiver_mqtt.send_mqtt = MagicMock()

        ## run
        garagenode_receiver_mqtt.handle_stream(stream)

        ## checks
        assert 1 == garagenode_receiver_mqtt.send_mqtt.call_count
        call0 = garagenode_receiver_mqtt.send_mqtt.call_args_list[0]
        msgs = call0[0][0]
        print(len(msgs), msgs)
        assert len(msgs) == 3
        assert type(msgs) is list
        assert msgs[0] == {'topic': '/foobar/light', 'payload': 11, 'retain': False}, msgs[0]
        assert msgs[1] == {'topic': '/foobar/humidity', 'payload': 29.90, 'retain': False}, msgs[1]
        assert msgs[2] == {'topic': '/foobar/temperature', 'payload': 27.60, 'retain': False}, msgs[2]
