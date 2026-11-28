GROUP 5 PROTOTYPE

Current flow for a successful demo (one terminal each, in this order):
1. START RECEIVER NODES      python receiver.py      python Rx2.py
2. START RELAY               python relay.py
3. START RECONNECT           python reconnect.py     (no arguments = demo mode)
4. START TRANSMITTER NODES   python Transmitter.py   python transmitter_2.py

Failover demo:
5. While the transmitters run, stop the relay (Ctrl+C). ReConnect prints
   "taking over port 5001" and keeps delivering; the transmitters' ACKs say
   "handled_by": "reconnect".
6. Start the relay again (python relay.py). It asks ReConnect for the port,
   ReConnect prints "port handed over", and the relay carries traffic again.

How the pieces talk (all JSON over TCP, ports in address_book.py):
- Transmitter -> RELAY_PORT: {"message_id", "source_port", "destination_port", "payload"},
  one message per connection.
- Relay or ReConnect -> transmitter, after delivering: {"message_id", "status", "handled_by"},
  status "accepted" (delivered) or "failed" (with "reason").
- Relay or ReConnect -> receiver: connects to the receiver's port (RX_1 / RX_2) and sends
  the whole message. Receivers listen on their own port and ignore duplicates.
- ReConnect -> relay, 10 times a second: {"monitor_packet": true, ...}. The relay ignores it.
- Restarted relay -> RELAY_PORT (held by ReConnect): {"handover_key": RECONNECT_HANDOVER_KEY}.
  ReConnect answers {"status": "released"} and lets go of the port.

Tests: python -m pytest
  tests/test_integration.py runs the real programs through a relay crash,
  ReConnect takeover and handback.
