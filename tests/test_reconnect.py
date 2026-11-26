# tests/test_reconnect.py

import sys
import subprocess
import address_book
import time
import pytest
import threading
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
         "tests/dummy_relay.py",
         str(address_book.RELAY_PORT),
         str(expected_connections)],
        stdout=subprocess.PIPE, text=True,
    )

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
            "monitor_packet": True
        }
     ),

    (5003,
        {
            "destination": 5003,
            "handover_key": "0123456789abcdef"
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


def test_deliver() -> None:
    pass


def test_receive_message() -> None:
    pass


@pytest.mark.parametrize("key, destination_port, expected_tx, message_json", [
    ("rx_message_count", 6001, 1,
        {
            "destination": 6001
        }
     ),

    ("rx_monitor_count", 6002, 0,
        {
            "destination": 6002,
            "monitor_packet": True
        }
     ),

    ("rx_handover_count", 6003, 0,
        {
            "destination": 6003,
            "handover_key": "0123456789abcdef"
        }
     )
])
@pytest.mark.skip
def test_relay(key, destination_port, expected_tx, message_json) -> None:
    """

    """
    time.sleep(1)
    rc = ReConnect(0)

    relay_thread = threading.Thread(target=rc.relay, daemon=True)
    relay_thread.start()

    packet = rc._serialize(message_json)
    rc._deliver(packet, rc.relay_port)

    time.sleep(1)
    rc._handover = True
    time.sleep(1)

    keys_list = list(rc.counters)
    keys_list.remove(key)

    print(f"keys_list={keys_list}")
    print(f"key={key}")
    print(f"rc.counters={rc.counters}")

    assert rc.counters[key] == 1

    for entry in keys_list:
        assert rc.counters[entry] == 0

    if expected_tx > 0:
        assert rc.counters["tx_message_count"] == expected_tx
