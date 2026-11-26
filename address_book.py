# address_book.py
#
# This file keeps track of all project-wide ports, addresses, and constants.

from typing import Final

IP_ADDRESS: Final[str] = 'localhost'
BUFFER_SIZE: Final[int] = 1000

# Transmitters send data to here
RELAY_PORT: Final[int] = 5001

# Relay sends data here to request communications handover from ReConnect
RECONNECT_PORT: Final[int] = 5025

# Key that relay node must present to ReConnect when requesting ReConnect to
# handover RELAY_PORT
RECONNECT_HANDOVER_KEY: Final[str] = "0123456789abcdef"

# Transmitters
TX_1: Final[int] = 5005
TX_2: Final[int] = 5010

# Receivers
RX_1: Final[int] = 5015
RX_2: Final[int] = 5020
