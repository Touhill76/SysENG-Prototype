# address_book.py
#
# This file keeps track of all TCP ports in use.

IP_ADDRESS = '127.0.0.1'
BUFFER_SIZE = 1000

# Transmitters send data to here
RELAY_PORT = 5000

# Relay sends data here to request communications handover from ReConnect
RECONNECT_RELEASE = 5025

# Transmitters
TX_1 = 5005
TX_2 = 5010

# Receivers
RX_1 = 5015
RX_2 = 5020
