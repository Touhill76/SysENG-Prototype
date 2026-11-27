# reconnect.py

import sys
import socket
import json
import threading
import address_book
from typing import Final
from time import sleep


class ReConnect:
    """

    """

    def __init__(self, relay_port: int):
        self._ip_address = address_book.IP_ADDRESS
        self._relay_port: Final[int] = relay_port
        self._connection_queue_size: Final[int] = 10
        self._buffer_size: Final[int] = address_book.BUFFER_SIZE
        self._handover_key: Final[str] = address_book.RECONNECT_HANDOVER_KEY

        self.lock = threading.Lock()

        self._handover: bool = False

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
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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
        return message_json["destination"]

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
                client.connect((address_book.IP_ADDRESS, destination_port))
                client.sendall(packet)
            return True

        except ConnectionRefusedError:
            return False

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
        packet = self._deserialize(data)

        match self._determine_packet_type(packet):

            # If packet is a monitor packet
            case "monitor":
                with self.lock:
                    self.counters["rx_monitor_count"] += 1

            # If packet is a message packet
            case "message":
                with self.lock:
                    self.counters["rx_message_count"] += 1
                destination_port = self._get_destination_port(packet)
                message = self._serialize(packet)
                if self._deliver(message, destination_port):
                    with self.lock:
                        self.counters["tx_message_count"] += 1

            # If packet is a handover request
            case "handover":
                with self.lock:
                    self.counters["rx_handover_count"] += 1
                if self._test_handover_key(packet):
                    with self.lock:
                        self._handover = True

            # Ignore any other packet types
            case _:
                pass
        return

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
        Function as a substitute communications relay.

        Raises
        ------
        OSError
            If it could not take control of self.relay_port
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self._ip_address, self._relay_port))
            s.listen()
            while not self._handover:
                connection, address = s.accept()
                packet = connection.recv(self._buffer_size)
                t = threading.Thread(target=self._handle_received_packet,
                                     args=(packet,),
                                     daemon=True)
                t.start()
        return None


# Integration test code
if __name__ == "__main__":

    relay_port: Final[int] = int(sys.argv[1])
    monitor_limit: Final[int] = int(sys.argv[2])
    output_file: Final[str] = sys.argv[3]

    rc = ReConnect(relay_port)
    rc.monitor(limit=monitor_limit)
    rc.relay()
    rc.export_counters(output_file)
    print("file written", flush=True)

    sys.exit(0)
