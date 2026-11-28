import socket
import json
import time
import address_book as a

# Connection Settings

HOST = a.IP_ADDRESS       # IP address of this receiver
PORT = a.RX_1             # port the relay (or ReConnect) delivers to

RECEIVER_ID = "RX1"     # how relay identifies each receiver
RETRY_TIME = 2          # number of seconds before trying to open the port again


def allow_quick_rebind(sock):
    # Let the port be reused right after a previous run stops
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


def read_messages(text):
    # take every complete JSON message out of the received text
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


# Main program

seen = set()   # (source_port, message_id) already received, to ignore resends

# open this receiver's port; the relay connects here to deliver each message
while True:
    receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    allow_quick_rebind(receiver)
    try:
        receiver.bind((HOST, PORT))
        break
    except OSError:
        receiver.close()
        print(f"Port {PORT} is busy. Retrying...")
        time.sleep(RETRY_TIME)

receiver.listen(5)
receiver.settimeout(1.0)   # wake up every second so Ctrl+C works on Windows
print(f"{RECEIVER_ID} listening on port {PORT}. Waiting for messages...", flush=True)

try:
    while True:
        try:
            connection, address = receiver.accept()
        except socket.timeout:
            continue

        # the relay sends one message and closes the connection
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

        for message in read_messages(data.decode("utf-8", errors="replace")):
            if isinstance(message, dict):
                key = (message.get("source_port"), message.get("message_id"))
                if key in seen and key != (None, None):
                    print("Duplicate ignored:", key, flush=True)
                    continue
                seen.add(key)
                print("Message received: ", message.get("payload", message),
                      f"(message {message.get('message_id')} from {message.get('source_port')})",
                      flush=True)
            else:
                print("Message received: ", message, flush=True)

except KeyboardInterrupt:
    # user stops program with Ctrl+C
    print("Program stopped by user.")

receiver.close()
