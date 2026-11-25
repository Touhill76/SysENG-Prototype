# reconnect.py

from typing import Final
import socket
import json
# import threading
import address_book
from time import sleep


class ReConnect:
    """

    """

    def __init__(self, relay_port: int):
        self.ip_address = address_book.IP_ADDRESS
        self.relay_port: Final[int] = relay_port

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
        monitor_packet = {
            "destination": address_book.RECONNECT_PORT,
            "monitor_packet": True
        }

        monitor_packet = json.dumps(monitor_packet).encode('utf-8')

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
            Returns boolean True if sent message returns an acknowledgement
            within TBD timeout. Returns False if message does not return an
            acknowledgement within TBD seconds.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((address_book.IP_ADDRESS, destination_port))
            client.sendall(packet)

    def relay(self) -> tuple[int, int, int]:
        """
        Function as a substitute communications relay.

        Returns
        -------
        tuple(int, int, int)
            The number of messages, monitoring packets, and handover requests
            that the ReConnect node received for the duration that it was
            acting as a communications relay.

        Raises
        ------
        OSError
            If it could not take control of self.relay_port
        """
        pass

    def release_communication_port(self, message_json) -> bool:
        """
        Release communication port back to the OS if and only if a handover
        request packet with the release key is presented.

        Parameters
        ----------
        message_json: dict
            The contents of the received TCP packet, as a JSON object
            represented by a Python dictionary.

        Returns
        -------
        bool
            Returns boolean True if release key was valid and
            self.communication_port was successfully released to the OS.
            Returns boolean False if release key was invalid.

        Raises
        ------
        OSError
            Raises OSError if self.communication port cannot be released to the
            OS.
        """
        pass
