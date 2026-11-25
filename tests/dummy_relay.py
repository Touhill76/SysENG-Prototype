# tests/dummy_relay.py

import sys
import socket


# Port to listen on
port = int(sys.argv[1])

# Number of connections to accept before quitting
n_packets = int(sys.argv[2])

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

srv.bind(('localhost', port))
srv.listen(8)

# Print status so that test knows that it can start
print("ready", flush=True)

for i in range(n_packets):
    conn, _ = srv.accept()
    conn.recv(1024)
    conn.close()
