import socket
import time
from datetime import datetime

import address_book as a

HOST = a.IP_ADDRESS
PORT = a.RX_2
RETRY_TIME = 2
LOG_FILE = "rx2_messages.log"

try:
    print(f"RX2 waiting for messages on port {PORT}...")

    while True:
        try:
            # The relay opens this port when TX2 sends a message.
            with socket.create_connection((HOST, PORT), timeout=5) as receiver:
                message = receiver.recv(a.BUFFER_SIZE)
        except OSError as error:
            print(f"RX2 waiting for the relay: {error}")
            time.sleep(RETRY_TIME)
            continue

        if message:
            text = message.decode("utf-8")
            entry = f"{datetime.now().isoformat(timespec='seconds')} RX2: {text}"

            print(entry)
            with open(LOG_FILE, "a", encoding="utf-8") as log:
                log.write(entry + "\n")
        else:
            print("RX2 connected, but received no data.")

        time.sleep(RETRY_TIME)

except KeyboardInterrupt:
    print("\nRX2 stopped.")