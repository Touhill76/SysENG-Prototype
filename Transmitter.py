import socket
import json
import time
import address_book as a


#1. Build Message
#2. Add Routing Info
#3. Transmit
#4. Wait for ACK
#5. Verify ACK
#6. Report Success/Failure

# Transmitter 1
# Central node address (the relay, or ReConnect while the relay is down)
HOST = a.IP_ADDRESS
PORT = a.RELAY_PORT

MESSAGES = 6        # how many messages to send
ATTEMPTS = 5        # tries per message before reporting it failed
RETRY_DELAY = 1     # seconds between tries
GAP = 1             # seconds between messages

counter = 0
confirmed = 0

# Send messages
while counter < MESSAGES:
    counter = counter + 1

    #1. Build Message  #2. Add Routing Info
    message = {
        "message_id": counter,
        "source_port": a.TX_1,
        "destination_port": a.RX_1,
        "payload": f"hello from transmitter {a.TX_1}"
    }

    # Convert dict to JSON bytes
    packet = json.dumps(message).encode("utf-8")

    delivered = False
    for attempt in range(1, ATTEMPTS + 1):
        try:
            # Create TCP socket and connect to central node. A new connection per
            # message means each one goes to whoever holds the relay port now.
            with socket.create_connection((HOST, PORT), timeout=5) as client:

                #3. Transmit
                client.sendall(packet)
                print("Message", counter, "sent" + (f" (attempt {attempt})" if attempt > 1 else ""))

                #4. Wait for ACK
                ack_data = client.recv(a.BUFFER_SIZE)

        except OSError as error:   # relay unreachable, or no ACK within 5 s
            print("Message", counter, "attempt", attempt, "failed:", error)
            time.sleep(RETRY_DELAY)
            continue

        if not ack_data:
            print("Message", counter, "attempt", attempt, "failed: connection closed before ACK")
            time.sleep(RETRY_DELAY)
            continue

        # Convert back to Python object
        try:
            ack = json.loads(ack_data.decode("utf-8"))
        except ValueError:
            print("Message", counter, "attempt", attempt, "failed: ACK was not JSON:", ack_data)
            time.sleep(RETRY_DELAY)
            continue

        print("ACK:", ack)

        #5. Verify ACK
        if ack.get("message_id") == message["message_id"] and ack.get("status") == "accepted":
            delivered = True
            break
        print("Message", counter, "attempt", attempt, "not delivered:", ack.get("reason", ack))
        time.sleep(RETRY_DELAY)

    #6. Report Success/Failure
    if delivered:
        confirmed = confirmed + 1
        print("Message", counter, "confirmed by", ack.get("handled_by", "relay"))
    else:
        print("Message", counter, "FAILED after", ATTEMPTS, "attempts")

    time.sleep(GAP)

print(f"Transmitter 1 done: {confirmed} of {MESSAGES} messages confirmed")
