# tests/test_reconnect.py

import sys
import subprocess
import address_book
import time
import pytest
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


@pytest.mark.parametrize("packet_type, packet", [
    ("message",
        {
            "destination": address_book.RECONNECT_PORT,
        }
     ),

    ("monitor",
        {
            "destination": address_book.RECONNECT_PORT,
            "monitor_packet": True
        }
     ),

    ("handover",
        {
            "destination": address_book.RECONNECT_PORT,
            "handover_key": "0123456789abcdef"
        }
     ),

    ("other",
        {
            "handover_key": "0123456789abcdef"
        }
     )
])
def test_determine_packet_type(packet_type: str, packet: dict) -> None:
    """
    Assert that ReConnect.determine_packet_type() can correctly differentiate
    between packet types.
    """
    rc = ReConnect(address_book.RELAY_PORT)
    detected_packet_type = rc.determine_packet_type(packet)
    assert detected_packet_type == packet_type
