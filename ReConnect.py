# ReConnect.py

from typing import Final
# import socket
# import json
# import threading
# import address_book


class ReConnect:
    """

    """

    def __init__(self, tx_port: int, communications_port: int):
        self.tx_port: Final[int] = tx_port
        self.communications_port: Final[int] = communications_port

    def monitor(self) -> None:
        """
        Monitor the status of existing communications network by sending a
        packet to itself 10 times per second via the communications system
        being monitored, each with a timeout of 0.1 seconds.

        This method blocks indefinitely for as long as the communications
        system being monitored continues to acknowledge the sent packets.

        Returns
        -------
        None
            Returns None if 3 consecutive packets fail to return an
            acknowledgement within 0.1 seconds.

        Raises
        ------
        OSError
            Raises an OSError if self.tx_port becomes unusable.
        """
        pass

    def receive_message(self) -> dict:
        """
        Listen for incoming TCP messages on port self.communications_port.

        Returns
        -------
        dict
            Returns received json object as a dictionary.

        Raises
        ------
        OSError
            Raises an OSError if self.communications_port becomes unavailable.
        """
        pass

    def determine_packet_type(self, message_json: dict) -> str:
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
        pass

    def get_destination_port(self, message_json: dict) -> int:
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
            Returns the port number that the message should be delivered to if
            the message packet's 'destination_port' field specifies a valid
            TCP port. Else, returns -1.
        """
        pass

    def deliver(self, message_json: dict, destination_port: int) -> bool:
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

        Raises
        ------
        OSError
            Raises an OSError if self.tx_port cannot be used.
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
