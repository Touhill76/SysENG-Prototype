# tests/test_system.py

import sys
import os
import signal
import socket
import json
from time import sleep, time
from subprocess import Popen, PIPE, DEVNULL, STDOUT
from tempfile import NamedTemporaryFile
from typing import Final
from reconnect import ReConnect
import address_book


def spawn_subprocess(script: str,
                     args: list[str] = [],
                     readiness_indicator: str = "") -> Popen:
    """
    Spawn a subprocess that runs a Python script. Optionally wait for a
    readiness indicator to be printed to stdout.

    Parameters
    ----------
    script: str
        A string naming the Python script to run. Note that as per the
        configurations in pyproject.toml, pytest runs from the project root
        directory, so all paths are relative to project root.

    args: list[str]
        An optional parameter consisting of a list of strings to pass to the
        Python script as arguments.

    readiness_indicator: str
        An optional parameter allowing the user to pass a string matching the
        readiness indicator that the Python script will print to stdout. If
        empty, no readiness check will be performed.

    Returns
    -------
    Popen
        Returns a subprocess.Popen object poiting to the running Python script.

    Raises
    ------
    FileNotFoundError
        if parameter 'scipt' points to a file that does not exist.
    """

    command = [sys.executable, script] + args

    # Spawn subprocess
    proc = Popen(command,
                 stdout=PIPE,
                 stdin=DEVNULL,  # set all three handles explicitly:
                 stderr=STDOUT,  # Windows + pytest can leave them invalid
                 text=True)

    # If user passed a readiness indicator
    if readiness_indicator:
        assert proc.stdout is not None

        # Block until readiness indicator is received
        while True:
            sleep(0.01)
            if proc.stdout.readline().strip() == readiness_indicator:
                break

    return proc


def wait_for_port(port: int, timeout: float = 10) -> None:
    """
    Block until something accepts TCP connections on 'port'.

    Raises
    ------
    TimeoutError
        If nothing accepts a connection within 'timeout' seconds.
    """
    deadline = time() + timeout
    while time() < deadline:
        try:
            with socket.create_connection(('localhost', port), timeout=0.5):
                return
        except OSError:
            sleep(0.05)
    raise TimeoutError(f"nothing accepted connections on port {port}")


def create_message(destination_port: int, message: str) -> bytes:
    """
    Convert a string to a sendable message.

    Parameters
    ----------
    destination: int
        Port that message should be sent to.

    message: str
        String to send as message.

    Returns
    -------
    bytes
        Returns message ready to send using TCP socket.
    """
    message_json = {
        "destination": destination_port,
        "message": message
    }
    rc = ReConnect(0)
    return rc._serialize(message_json)


# ReConnect integration test
def test_system() -> None:

    n_connections: Final[int] = 10
    pids: list[int] = []
    temp_file: str = ""
    with NamedTemporaryFile(mode='w+t',
                            suffix='.json',
                            delete=False) as tf:
        temp_file = tf.name

    try:
        # Spawn communications system
        relay = spawn_subprocess("tests/dummy_server.py",
                                 [str(address_book.RELAY_PORT),
                                  str(n_connections)],
                                 "ready")
        pids.append(relay.pid)

        # Spawn ReConnect
        reconnect = spawn_subprocess("reconnect.py",
                                     [str(address_book.RELAY_PORT),
                                      "20",
                                      temp_file])
        pids.append(reconnect.pid)

        # ReConnect will not enter monitor mode until dummy_server.py closes.
        # Block execution until dummy_server.py's PID is no longer active.
        while relay.poll() is None:
            sleep(0.1)

        # Spawn Receivers
        rx_1 = spawn_subprocess("tests/dummy_server.py",
                                [str(address_book.RX_1),
                                 str(n_connections)],
                                "ready")
        pids.append(rx_1.pid)
        rx_2 = spawn_subprocess("tests/dummy_server.py",
                                [str(address_book.RX_2),
                                 str(n_connections)],
                                "ready")
        pids.append(rx_2.pid)

        # ReConnect checks the relay every 0.1 s, so wait until it has
        # actually taken over the relay port before sending
        wait_for_port(address_book.RELAY_PORT)

        # Send messages to receivers via ReConnect
        destinations = [address_book.RX_1, address_book.RX_2]
        for i in range(n_connections):
            for destination in destinations:
                message = create_message(destination, str(i))
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('localhost', address_book.RELAY_PORT))
                    s.sendall(message)

        # Send handover request to ReConnect
        request = {"handover_key": address_book.RECONNECT_HANDOVER_KEY}
        rc = ReConnect(address_book.RELAY_PORT)
        packet = rc._serialize(request)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect(('localhost', address_book.RELAY_PORT))
            client.sendall(packet)

        # Block until ReConnect lets go of the port
        rc.monitor(limit=10)

        # Wait for ReConnect to finish writing counters file
        while reconnect.poll() is None:
            sleep(0.01)

        # Read counters file and confirm expected entries
        with open(temp_file, 'r') as file:
            counters = json.load(file)

            expected_counters = {
                "tx_message_count": 2 * n_connections,
                "rx_message_count": 2 * n_connections,
                "rx_monitor_count": 0,
                "rx_handover_count": 1
            }

            assert counters == expected_counters

    # Clean up temp file and kill any processes that are still running
    finally:
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)

            # Ignore processes that have already closed (Windows reports
            # these as PermissionError rather than ProcessLookupError)
            except (ProcessLookupError, PermissionError):
                pass

            # Ignore if test failed before file was created
            try:
                os.remove(temp_file)
            except FileNotFoundError:
                pass
