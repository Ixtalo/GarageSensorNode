
import io
import garagenode_receiver_mqtt
from garagenode_receiver_mqtt import *


def test_datadict2msgs():
    ## basic result type checking
    actual = datadict2msgs({})
    assert actual is not None
    assert type(actual) is list
    assert actual == []

    ## a single element
    actual = datadict2msgs(DataEntries().add(Message('light', 11, False)))
    assert actual == [{'payload': 11, 'retain': False, 'topic': '/garagenode/light'}]

    ## another single element
    actual = datadict2msgs(DataEntries().add(Message('light', 11, True)))
    assert actual == [{'payload': 11, 'retain': True, 'topic': '/garagenode/light'}]

    ## change topic base
    garagenode_receiver_mqtt.MQTT_TOPIC_BASE = 'foobar/'
    actual = datadict2msgs(DataEntries().add(Message('light', 11, False)))
    assert actual == [{'payload': 11, 'retain': False, 'topic': 'foobar/light'}]

    ## checking of unhandled names
    actual = datadict2msgs(DataEntries().add(Message('AAA', 11, False)))
    assert actual == [{'payload': 11, 'retain': False, 'topic': 'foobar/AAA'}]

    ## checking of handled and undhandled
    actual = datadict2msgs(DataEntries().add(Message('AAA', 11, False)).add(Message('light', 22, False)))
    assert actual == [{'payload': 11, 'retain': False, 'topic': 'foobar/AAA'}, {'payload': 22, 'retain': False, 'topic': 'foobar/light'}]


def test_handle_stream():
    ## check with empty stream
    garagenode_receiver_mqtt.handle_stream(io.BytesIO(), None, None)

    ## check with 2 data elements in stream
    stream = io.BytesIO()
    stream.write(b'......**L:11;H:29.90;T:27.60;R:0$$.......')
    stream.write(b'...............')
    stream.write(b'**L:444;H:nan;T:nan;R:1$$')
    stream.write(b'...............')
    stream.seek(0)  ## needed!
    ## own callback
    def my_send_mqtt(msgs, mqtt_host, mqtt_port):
        ##print(msgs)
        assert len(msgs) in (2, 4)
        assert type(msgs) is list
        assert msgs[0] in ({'topic': 'foobar/light', 'payload': 11, 'retain': False}, {'topic': 'foobar/light', 'payload': 444, 'retain': False})
    garagenode_receiver_mqtt.handle_stream(stream, None, None, my_send_mqtt)

