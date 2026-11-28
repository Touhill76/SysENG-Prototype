import socket
import json
import time
from datetime import datetime

import address_book as a

HOST = a.IP_ADDRESS
PORT = a.RX_2
RETRY_TIME = 2
LOG_FILE = "rx2_messages.log"


def allow_quick_rebind(sock):
    # Let the port be reused right after a previous run stops
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


def read_messages(text):
    # Take every complete JSON message out of the received text
    decoder = json.JSONDecoder()
    messages = []
    text = text.strip()
    while text:
        try:
            message, end = decoder.raw_decode(text)
        except json.JSONDecodeError:
            messages.append(text)      # not JSON: keep it as plain text
            break
        messages.append(message)
        text = text[end:].strip()
    return messages


seen = set()   # (source_port, message_id) already received, to ignore resends

# Open RX2's port; the relay (or ReConnect) connects here to deliver each message
while True:
    receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    allow_quick_rebind(receiver)
    try:
        receiver.bind((HOST, PORT))
        break
    except OSError as error:
        receiver.close()
        print(f"RX2 port {PORT} is busy: {error}")
        time.sleep(RETRY_TIME)

receiver.listen(5)
receiver.settimeout(1.0)   # wake up every second so Ctrl+C works on Windows

try:
    print(f"RX2 waiting for messages on port {PORT}...", flush=True)

    while True:
        try:
            connection, address = receiver.accept()
        except socket.timeout:
            continue

        # The relay sends one message and closes the connection
        with connection:
            connection.settimeout(5)
            data = b""
            try:
                while True:
                    chunk = connection.recv(a.BUFFER_SIZE)
                    if not chunk:
                        break
                    data += chunk
            except OSError:
                pass

        if not data:
            print("RX2 connected, but received no data.")
            continue

        for message in read_messages(data.decode("utf-8", errors="replace")):
            if isinstance(message, dict):
                key = (message.get("source_port"), message.get("message_id"))
                if key in seen and key != (None, None):
                    print(f"RX2: duplicate ignored {key}", flush=True)
                    continue
                seen.add(key)
                text = (f"message {message.get('message_id')} from "
                        f"{message.get('source_port')}: "
                        f"{message.get('payload', message)}")
            else:
                text = str(message)

            entry = f"{datetime.now().isoformat(timespec='seconds')} RX2: {text}"

            print(entry, flush=True)
            with open(LOG_FILE, "a", encoding="utf-8") as log:
                log.write(entry + "\n")

except KeyboardInterrupt:
    print("\nRX2 stopped.")

receiver.close()
