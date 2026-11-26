# reconnect.py

from typing import Final
import socket
import json
import threading
import address_book
from time import sleep


class ReConnect:
    """

    """

    def __init__(self, relay_port: int):
        self.ip_address = address_book.IP_ADDRESS
        self.relay_port: Final[int] = relay_port
        self.connection_queue_size: Final[int] = 10
        self.buffer_size: Final[int] = address_book.BUFFER_SIZE

        self.lock = threading.Lock()

        self._handover: bool = False

        self.counters = {
            "tx_message_count": 0,
            "rx_message_count": 0,
            "rx_monitor_count": 0,
            "rx_handover_count": 0
        }

    def monitor(self) -> int:
        """
        Monitor the status of existing communications network by connecting 10
        times per second.

        This method blocks indefinitely for as long as the communications
        system being monitored continues to accept connections.

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

        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.1)
                    s.connect((self.ip_address,
                               self.relay_port))
                    s.sendall(monitor_packet)
                    connections += 1

            except Exception:
                break

            sleep(0.1)

        return connections

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

        if "destination" not in message_json:
            return "other"

        if "handover_key" in message_json:
            return "handover"

        if "monitor_packet" in message_json:
            return "monitor"

        return "message"

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

    def _receive_message(self, connection: socket.socket) -> None:
        """

        """
        with connection:

            data = connection.recv(self.buffer_size)
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
                        self._handover = True

                # Ignore any other packet types
                case _:
                        pass
        return

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
            s.bind((self.ip_address, self.relay_port))
            s.listen()
            while not self._handover:
                connection, address = s.accept()
                t = threading.Thread(target=self._receive_message,
                                     args=(connection,),
                                     daemon=True)
                t.start()
        return None
