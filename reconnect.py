# reconnect.py

import sys
import socket
import json
import threading
import address_book
from typing import Final, Optional
from time import sleep


class ReConnect:

    def __init__(self, relay_port: int):
        self._ip_address = address_book.IP_ADDRESS
        self._relay_port: Final[int] = relay_port
        self._connection_queue_size: Final[int] = 10
        self._buffer_size: Final[int] = address_book.BUFFER_SIZE
        self._handover_key: Final[str] = address_book.RECONNECT_HANDOVER_KEY

        self.lock = threading.Lock()

        self._handover: bool = False
        self._connections: set[socket.socket] = set()

        self.counters = {
            "tx_message_count": 0,
            "rx_message_count": 0,
            "rx_monitor_count": 0,
            "rx_handover_count": 0
        }

    def monitor(self, limit: int = 0) -> int:
        """
        Monitor the status of existing communications network by connecting 10
        times per second.

        Parameters
        ----------
        limit: int
            Optional parameter that allows user to specify a maximum number of
            connections before quitting. Default value of 0 means that no limit
            will be imposed and monitor will continue to run indefinitely until
            the system being monitored stops accepting connections.

        Returns
        -------
        int
            Returns the number of successful connections before the system
            being monitored failed to accept a connection.
        """
        data = {
            "destination": address_book.RECONNECT_PORT,
            "monitor_packet": True
        }

        monitor_packet = json.dumps(data).encode('utf-8')

        connections = 0

        if limit:
            for i in range(limit):
                try:
                    with socket.socket(socket.AF_INET,
                                       socket.SOCK_STREAM) as s:
                        s.settimeout(0.1)
                        s.connect((self._ip_address,
                                   self._relay_port))
                        s.sendall(monitor_packet)
                        connections += 1
                except Exception:
                    break

                sleep(0.1)

        else:
            while True:
                try:
                    with socket.socket(socket.AF_INET,
                                       socket.SOCK_STREAM) as s:
                        s.settimeout(0.1)
                        s.connect((self._ip_address,
                                   self._relay_port))
                        s.sendall(monitor_packet)
                        connections += 1

                except Exception:
                    break

                sleep(0.1)

        return connections

    def _serialize(self, message_json: dict) -> bytes:
        """
        Convert a python dictionary representation of a JSON object into an
        array pf bytes ready to send over TCP.

        Parameters
        ----------
        message_json: dict
            The JSON message to be sent, as a JSON object represented by a
            Python dictionary.

        Returns
        -------
        bytes
            Returns the JSON object as bytes.
        """
        return json.dumps(message_json).encode("utf-8")

    def _deserialize(self, packet: bytes) -> dict:
        """
        Convert a received TCP packet from an array of bytes into a JSON object
        represented as a Python dictionary. If received packet is not valid
        JSON, return dictionary {"invalid": True}

        Parameters
        ----------
        message_json: dict
            The received packet as an array of bytes.

        Returns
        -------
        dict
            Returns a JSON object as represented by an Python dictionary.
        """
        try:
            return json.loads(packet.decode("utf-8"))

        except Exception:
            return {"invalid": True}

    def _determine_packet_type(self, message_json: dict) -> str:
        """
        Determine if a packet is a message to be delivered, a monitoring packet
        from another ReConnect node, or a handover request from a communication
        relay.

        Parameters
        ----------
        message_json: dict
            The received packet in JSON format as represented by a Python
            dictionary.

        Returns
        -------
        str
            Returns string "message" if packet is a message.
            Returns string "monitor" if packet is a monitoring packet.
            Returns string "handover" if packet is a handover request.
            Returns string "other" if packet type cannot be determined.
        """
        if "handover_key" in message_json:
            return "handover"

        if "monitor_packet" in message_json:
            return "monitor"

        if "destination" in message_json:
            return "message"

        # Transmitters and relay.py name the field "destination_port"
        if "destination_port" in message_json:
            return "message"

        return "other"

    def _get_destination_port(self, message_json: dict) -> int:
        """
        Parse a message packet to get the TCP port that it should be delivered
        to.

        Parameters
        ----------
        message_json: dict
            The contents of the received TCP packet, as a JSON object
            represented by a Python dictionary.

        Returns
        -------
        int
            Returns the port number that the message should be delivered to.
        """
        if "destination" in message_json:
            return int(message_json["destination"])
        return int(message_json["destination_port"])

    def _test_handover_key(self, message_json: dict) -> bool:
        """
        Check if the key provided in a handover request is the correct key.

        Parameters
        ----------
        message_json: dict
            The contents of the received TCP packet, as a JSON object
            represented by a Python dictionary.

        Returns
        -------
        bool
            Returns boolean True if handover request key is the correct key.
            Returns False otherwise.
        """
        return message_json["handover_key"] == self._handover_key

    def _deliver(self, packet: bytes, destination_port: int) -> bool:
        """
        Deliver a message to it's specified destination.

        Parameters
        ----------
        message_json: dict
            The contents of the received TCP packet, as a JSON object
            represented by a Python dictionary.

        destination_port: int
            The port to which the message is to be sent.

        Returns
        -------
        bool
            Returns boolean True if message is delivered successfully. Returns
            boolean False if any errors are encountered whiel trying to deliver
            message.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.settimeout(2)
                client.connect((address_book.IP_ADDRESS, destination_port))
                client.sendall(packet)
            return True

        except OSError:
            return False

    def _process_packet(self, packet: dict) -> Optional[dict]:
        """
        Act on one received packet and return the reply for its sender.

        Parameters
        ----------
        packet: dict
            The received packet, as a JSON object represented by a Python
            dictionary.

        Returns
        -------
        dict or None
            For a message: an ACK {"message_id", "status", "handled_by"}
            with status "accepted" if it was delivered, else "failed".
            For a handover request: {"status": "released"} or
            {"status": "refused"}. For anything else: None (no reply).
        """
        match self._determine_packet_type(packet):

            # If packet is a monitor packet
            case "monitor":
                with self.lock:
                    self.counters["rx_monitor_count"] += 1
                return None

            # If packet is a message packet
            case "message":
                with self.lock:
                    self.counters["rx_message_count"] += 1
                destination_port = self._get_destination_port(packet)
                message = self._serialize(packet)
                delivered = self._deliver(message, destination_port)
                if delivered:
                    with self.lock:
                        self.counters["tx_message_count"] += 1
                return {
                    "message_id": packet.get("message_id"),
                    "status": "accepted" if delivered else "failed",
                    "handled_by": "reconnect"
                }

            # If packet is a handover request
            case "handover":
                with self.lock:
                    self.counters["rx_handover_count"] += 1
                if self._test_handover_key(packet):
                    with self.lock:
                        self._handover = True
                    return {"status": "released"}
                return {"status": "refused"}

            # Ignore any other packet types
            case _:
                return None

    def _handle_received_packet(self, data: bytes) -> None:
        """
        Parse a received packet and determine what to do with it.

        Note that this method returns None since it is intended to run as a
        thread. Rather than returning a value, it uses a thread lock to safely
        update class attributes.

        Parameters
        ----------
        data: bytes
            The received TCP packet.
        """
        self._process_packet(self._deserialize(data))
        return

    @staticmethod
    def _split_packets(text: str) -> tuple[list[dict], str]:
        """
        Take every complete JSON object off the front of the received text.

        Returns
        -------
        tuple
            The complete packets (non-dict JSON is replaced by
            {"invalid": True}) and the text left over (an incomplete packet).
        """
        decoder = json.JSONDecoder()
        packets = []
        while True:
            text = text.lstrip()
            if not text:
                break
            try:
                obj, end = decoder.raw_decode(text)
            except json.JSONDecodeError:
                break
            packets.append(obj if isinstance(obj, dict) else {"invalid": True})
            text = text[end:]
        return packets, text

    def _send_reply(self, connection: socket.socket,
                    reply: Optional[dict]) -> bool:
        """Send a reply; return False if the sender has already gone."""
        if reply is None:
            return True
        try:
            connection.sendall(self._serialize(reply))
            return True
        except OSError:
            return False

    def _handle_connection(self, connection: socket.socket,
                           first_packets: list[dict], leftover: str) -> None:
        """
        Serve one sender's connection (run as a thread): answer the packets
        already read, then keep reading until the sender closes, so a sender
        may put several messages on one connection.
        """
        with self.lock:
            self._connections.add(connection)
        try:
            for packet in first_packets:
                if not self._send_reply(connection,
                                        self._process_packet(packet)):
                    return
            text = leftover
            while not self._handover:
                try:
                    data = connection.recv(self._buffer_size)
                except OSError:
                    return
                if not data:
                    return
                text += data.decode("utf-8", errors="replace")
                packets, text = self._split_packets(text)
                for packet in packets:
                    if not self._send_reply(connection,
                                            self._process_packet(packet)):
                        return
        finally:
            with self.lock:
                self._connections.discard(connection)
            connection.close()

    def export_counters(self, path: str) -> None:
        """
        Write self.counters to a JSON file.

        Parameters
        ----------
        path: str
            Path to where JSON file should be written.

        Raises
        ------
        FileNotFoundError
            If parameter 'path' points to a location that does not exist or
            a location that the user does not have permission to access.
        """
        with open(path, "w", encoding="utf-8") as outfile:
            json.dump(self.counters, outfile, indent=4)

    def relay(self) -> None:
        """
        Function as a substitute communications relay until a relay presents
        the correct handover key, then release self._relay_port.

        Every message is delivered to its destination port and answered with
        an ACK on the sender's connection. The first packet of each
        connection is read before the next connection is accepted, so a
        handover request takes effect before anything else is accepted.

        Raises
        ------
        OSError
            If it could not take control of self.relay_port
        """
        self._handover = False
        workers: list[threading.Thread] = []
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self._ip_address, self._relay_port))
            s.listen(self._connection_queue_size)
            s.settimeout(0.5)
            while not self._handover:
                try:
                    connection, address = s.accept()
                except socket.timeout:
                    continue
                connection.settimeout(2)
                try:
                    data = connection.recv(self._buffer_size)
                except OSError:
                    connection.close()
                    continue
                connection.settimeout(None)
                if not data:
                    connection.close()
                    continue
                text = data.decode("utf-8", errors="replace")
                packets, leftover = self._split_packets(text)
                if packets and \
                        self._determine_packet_type(packets[0]) == "handover":
                    reply = self._process_packet(packets[0])
                    self._send_reply(connection, reply)
                    connection.close()
                    continue
                t = threading.Thread(target=self._handle_connection,
                                     args=(connection, packets, leftover),
                                     daemon=True)
                t.start()
                workers.append(t)

        # Port released: drop senders still connected so that they reconnect
        # to the relay that now holds the port
        with self.lock:
            open_connections = list(self._connections)
        for connection in open_connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        # Let deliveries already under way finish before returning
        for t in workers:
            t.join(timeout=3)
        return None

    def wait_for_relay(self) -> None:
        """
        Block until something accepts connections on self._relay_port (the
        communications relay is up).
        """
        while True:
            try:
                with socket.create_connection((self._ip_address,
                                               self._relay_port),
                                              timeout=0.5):
                    return
            except OSError:
                sleep(0.2)


def demo() -> None:
    """
    Run ReConnect for a live demo: wait for the relay, monitor it, take over
    its port when it fails, hand the port back when it returns, repeat.
    """
    rc = ReConnect(address_book.RELAY_PORT)
    print(f"ReConnect: waiting for the relay on port "
          f"{address_book.RELAY_PORT}...", flush=True)
    try:
        while True:
            rc.wait_for_relay()
            print("ReConnect: monitoring the relay", flush=True)
            checks = rc.monitor()
            print(f"ReConnect: relay stopped answering after {checks} "
                  f"checks - taking over port {address_book.RELAY_PORT}",
                  flush=True)
            try:
                rc.relay()
            except OSError as error:
                print(f"ReConnect: could not take over the port: {error}",
                      flush=True)
                sleep(0.5)
                continue
            print(f"ReConnect: relay is back - port handed over "
                  f"(counters: {rc.counters})", flush=True)
            sleep(0.5)
    except KeyboardInterrupt:
        print("ReConnect stopped.")


if __name__ == "__main__":

    # No arguments: live demo mode
    if len(sys.argv) == 1:
        demo()
        sys.exit(0)

    # Integration test code (used by tests/test_system.py)
    relay_port: Final[int] = int(sys.argv[1])
    monitor_limit: Final[int] = int(sys.argv[2])
    output_file: Final[str] = sys.argv[3]

    rc = ReConnect(relay_port)
    rc.monitor(limit=monitor_limit)
    rc.relay()
    rc.export_counters(output_file)

    sys.exit(0)
