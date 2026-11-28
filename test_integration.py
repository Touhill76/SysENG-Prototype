# tests/test_integration.py
#
# Runs the real programs together: relay.py, reconnect.py (demo mode),
# receiver.py, Rx2.py, Transmitter.py and transmitter_2.py.
#
# Scenario:
#   1. Both transmitters start sending through the relay.
#   2. The relay is killed part-way through (simulated failure).
#   3. ReConnect takes over the relay port and keeps delivering.
#   4. The relay is restarted, asks for its port back, and ReConnect hands
#      it over.
#   5. Every message must be confirmed by its transmitter and arrive exactly
#      once at its receiver.

import re
import sys
import time
from pathlib import Path
from subprocess import Popen, STDOUT, DEVNULL
from typing import IO

import pytest


class Program:
    """A running Python script whose output is written to a file."""

    def __init__(self, script: str, log_dir: Path, name: str) -> None:
        self.path = log_dir / f"{name}.out"
        self._file: IO[str] = open(self.path, "w")
        self.proc = Popen([sys.executable, "-u", script],
                          stdout=self._file, stderr=STDOUT, text=True,
                          stdin=DEVNULL)  # needed on Windows under pytest

    def output(self) -> str:
        return self.path.read_text(errors="replace")

    def wait_for(self, text: str, timeout: float = 15) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if text in self.output():
                return
            if self.proc.poll() is not None:
                break
            time.sleep(0.05)
        pytest.fail(f"{self.path.name}: never printed {text!r}\n"
                    f"{self.output()[-2000:]}")

    def stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=5)
        self._file.close()


def test_failover_and_handover(tmp_path: Path) -> None:
    running: list[Program] = []

    def start(script: str, name: str, ready: str = "") -> Program:
        program = Program(script, tmp_path, name)
        running.append(program)
        if ready:
            program.wait_for(ready)
        return program

    try:
        rx1 = start("receiver.py", "rx1", "listening on port")
        rx2 = start("Rx2.py", "rx2", "waiting for messages")
        relay = start("relay.py", "relay", "Relay listening")
        reconnect = start("reconnect.py", "reconnect",
                          "monitoring the relay")

        tx1 = start("Transmitter.py", "tx1")
        tx2 = start("transmitter_2.py", "tx2")

        # Let a couple of messages go through the relay, then kill it
        tx2.wait_for("Message 2 confirmed")
        relay.proc.kill()
        reconnect.wait_for("taking over port")

        # Let ReConnect carry at least one message, then restart the relay
        tx2.wait_for("confirmed by reconnect")
        relay_2 = start("relay.py", "relay_2", "Relay listening")
        reconnect.wait_for("port handed over")

        for tx in (tx1, tx2):
            tx.proc.wait(timeout=90)

        out_tx1, out_tx2 = tx1.output(), tx2.output()
        assert "6 of 6 messages confirmed" in out_tx1, out_tx1
        assert "6 of 6 messages confirmed" in out_tx2, out_tx2

        both = out_tx1 + out_tx2
        assert "confirmed by reconnect" in both
        assert relay_2.output().count("'message_id'") >= 1, \
            "restarted relay carried no messages"
        assert "asking ReConnect to hand it back" in relay_2.output()

        time.sleep(1)  # let the receivers print the last message
        got_1 = set(re.findall(r"\(message (\d+) from 5005\)",
                               rx1.output()))
        got_2 = set(re.findall(r"message (\d+) from 5010:", rx2.output()))
        assert got_1 == {str(i) for i in range(1, 7)}, rx1.output()
        assert got_2 == {str(i) for i in range(1, 7)}, rx2.output()

    finally:
        for program in running:
            program.stop()
        Path("rx2_messages.log").unlink(missing_ok=True)
