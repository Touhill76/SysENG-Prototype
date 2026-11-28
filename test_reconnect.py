# tests/test_reconnect.py

import sys
import subprocess
import address_book
import time
import json
import pytest
from pathlib import Path
from reconnect import ReConnect


def test_monitor() -> None:
    """
    Assert that ReConnect.monitor() can correctly determine when a port closes
    by opening a tcp server in a background thread that will close after
    accepting 5 connections, and then running the monitor method against it.

    ReConnect.monitor() returns the number of successful connections it
    acheived before the system beign monitored failed to accept a connection,
    so this can be compared agaisnt the number of connections that the dummy
    relay was told to accept to verify that the port was ever open to begin
    with.
    """

    expected_connections = 5

    # Spawn subprocess
    proc = subprocess.Popen(
        [sys.executable,
         "tests/dummy_server.py",
         str(address_book.RELAY_PORT),
         str(expected_connections)],
        stdout=subprocess.PIPE, text=True,
        stdin=subprocess.DEVNULL,  # set all three handles explicitly:
        stderr=subprocess.STDOUT,  # Windows + pytest can leave them invalid
    )

    # Explicit typecheck to satisfy static analysis
    assert proc.stdout is not None

    # Wait until dummy relay is ready to start accepting connections
    while True:
        time.sleep(0.01)
        if proc.stdout.readline().strip() == "ready":
            break

    try:

        rc = ReConnect(address_book.RELAY_PORT)

        actual_connections = rc.monitor()

        assert actual_connections == expected_connections

    # Cleanup spawned subprocess
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.parametrize("message", [
    {
        "destination": 5001,
    },

    {
        "destination": 5002,
        "monitor_packet": True
    },

    {
        "destination": 5003,
        "handover_key": "0123456789abcdef"
    }
])
def test_serialize(message: dict) -> None:
    """
    Assert ReConnect._serialize() returns a bytes array.
    """
    rc = ReConnect(address_book.RELAY_PORT)
    packet = rc._serialize(message)
    assert isinstance(packet, bytes)


@pytest.mark.parametrize("message", [
    {
        "destination": 5001,
        "data": "hello world"
    },

    {
        "monitor_packet": ""
    },

    {
        "handover_key": "0123456789abcdef"
    }
])
def test_deserialize(message: dict) -> None:
    """
    Assert ReConnect._deserialize() is the inverse operation of
    ReConnect._serialize() and returns a Python dictionary.
    """
    rc = ReConnect(address_book.RELAY_PORT)
    packet = rc._serialize(message)
    deserialized_packet = rc._deserialize(packet)
    assert deserialized_packet == message
    assert isinstance(deserialized_packet, dict)


@pytest.mark.parametrize("packet_type, packet", [
    ("message",
        {
            "destination": 5001
        }
     ),

    ("monitor",
        {
            "monitor_packet": ""
        }
     ),

    ("handover",
        {
            "handover_key": "0123456789abcdef"
        }
     ),

    ("other",
        {
            "data": "0123456789abcdef"
        }
     )
])
def test_determine_packet_type(packet_type: str, packet: dict) -> None:
    """
    Assert that ReConnect._determine_packet_type() can correctly differentiate
    between packet types.
    """
    rc = ReConnect(address_book.RELAY_PORT)
    detected_packet_type = rc._determine_packet_type(packet)
    assert detected_packet_type == packet_type


@pytest.mark.parametrize("expected_port, packet", [
    (5001,
        {
            "destination": 5001,
        }
     ),

    (5002,
        {
            "destination": 5002,
            "data": "hello world"
        }
     ),

    (5003,
        {
            "destination": 5003,
            "status": "ok"
        }
     )
])
def test_get_destination_port(expected_port: int, packet: dict) -> None:
    """
    Assert ReConnect._get_destination_port() can correctly read the destination
    port in supported packet types.
    """
    rc = ReConnect(address_book.RELAY_PORT)
    port = rc._get_destination_port(packet)
    assert port == expected_port
    assert isinstance(port, int)


@pytest.mark.parametrize("message_json, expected_result", [
    ({"handover_key": address_book.RECONNECT_HANDOVER_KEY}, True),
    ({"handover_key": "1234567890"}, False),
    ({"handover_key": ""}, False)
])
def test_handover_key(message_json: dict, expected_result: bool) -> None:
    """
    Assert that ReConnect._test_handover_key can correctly indentify whether
    or not the correct key has been presented.
    """
    rc = ReConnect(address_book.RELAY_PORT)
    assert rc._test_handover_key(message_json) == expected_result


@pytest.mark.parametrize("destination_port, message_json", [
    (address_book.RX_1,
        {
            "destination": address_book.RX_1,
            "data": "hello_world"
        }
     ),
    (address_book.RX_2,
        {
            "destination": address_book.RX_2,
            "data": "hello_world"
        }
     )
])
def test_deliver(destination_port: int, message_json: dict) -> None:
    """
    Assert that ReConnect._deliver can successfully send a TCP message to the
    specfied destination port.
    """
    # Spawn subprocess
    proc = subprocess.Popen(
        [sys.executable,
         "tests/dummy_server.py",
         str(destination_port),
         "1"],
        stdout=subprocess.PIPE, text=True,
        stdin=subprocess.DEVNULL,  # set all three handles explicitly:
        stderr=subprocess.STDOUT,  # Windows + pytest can leave them invalid
    )

    # Explicit typecheck to satisfy static analysis
    assert proc.stdout is not None

    # Wait until dummy relay is ready to start accepting connections
    while True:
        time.sleep(0.01)
        if proc.stdout.readline().strip() == "ready":
            break

    try:
        rc = ReConnect(destination_port)
        packet = rc._serialize(message_json)
        result_1 = rc._deliver(packet, destination_port)

        # Wait until port is no longer open
        rc.monitor()

        result_2 = rc._deliver(packet, destination_port)

        assert result_1 is True
        assert result_2 is False

    # Cleanup spawned subprocess
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.parametrize("key, message_json", [
    ("rx_message_count",
        {
            "destination": 6001,
            "data": "hello world"
        }
     ),

    ("rx_monitor_count",
        {
            "monitor_packet": ""
        }
     ),

    ("rx_handover_count",
        {
            "handover_key": "0123456789abcdef"
        }
     )
])
def test_handle_received_packet(key: str, message_json: dict) -> None:
    """
    Assert that ReConnect._handle_received_packet() can correctly handle all
    supported packet types.
    """
    rc = ReConnect(0)
    packet = rc._serialize(message_json)
    rc._handle_received_packet(packet)

    keys_list = list(rc.counters)
    keys_list.remove(key)

    assert rc.counters[key] == 1

    for entry in keys_list:
        assert rc.counters[entry] == 0


@pytest.mark.parametrize("counters", [
    {
        "tx_message_count": 0,
        "rx_message_count": 0,
        "rx_monitor_count": 0,
        "rx_handover_count": 0
    },
    {
        "tx_message_count": 5,
        "rx_message_count": 7,
        "rx_monitor_count": 19,
        "rx_handover_count": 1
    },
    {
        "tx_message_count": 12345,
        "rx_message_count": 12345,
        "rx_monitor_count": 48917,
        "rx_handover_count": 13
    }
])
def test_export_counters(counters: dict, tmp_path: Path) -> None:
    """
    Assert that ReConnect.export_counters() exports the correct values as
    a valid JSON file.

    Uses pytest's tmp_path folder rather than an open NamedTemporaryFile,
    because Windows does not allow a second open of a file that is still
    open.
    """
    rc = ReConnect(0)
    rc.counters = counters
    path = tmp_path / "counters.json"
    rc.export_counters(str(path))
    with open(path, 'r') as file:
        saved_data = json.load(file)
        assert saved_data == rc.counters


def test_export_counters_raises() -> None:
    """
    Assert that ReConnect.export_counters() raises a FileNotFoundError
    exception if provided a path to a location that does not exist.
    """
    rc = ReConnect(0)
    with pytest.raises(FileNotFoundError):
        rc.export_counters("/this/location/does/not/exist")
