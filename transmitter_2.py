import socket
import json
import address_book as a


#1. Build Message
#2. Add Routing Info
#3. Transmit
#4. Wait for ACK
#5. Verify ACK
#6. Report Success/Failure

# Transmitter 2
# Central node address
HOST = a.IP_ADDRESS
PORT = a.RELAY_PORT

counter = 0
# Create TCP socket object
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.settimeout(5)  # stop waiting for an ACK after 5 seconds

# Connect to central node
client.connect((HOST, PORT))  # connect to this computer and this program

# Send messages
while counter < 6:
    counter = counter + 1

    #1. Build Message  #2. Add Routing Info
    message = {
        "message_id": counter,
        "source_port": a.TX_2,
        "destination_port": a.RX_2,
        "payload": f"hello from transmitter {a.TX_2}"
    }

    # Convert dict to JSON bytes
    packet = json.dumps(message).encode("utf-8")

    #3. Transmit
    client.sendall(packet)
    print("Message", counter, "sent")

    #4. Wait for ACK
    try:
        ack_data = client.recv(a.BUFFER_SIZE)
    except socket.timeout:
        print("Message", counter, "failed: no ACK")
        continue

    if not ack_data:
        print("Message", counter, "failed: relay closed the connection")
        break

    # Convert back to Python object
    ack = json.loads(ack_data.decode("utf-8"))

    print("ACK:", ack)

    #5. Verify ACK  #6. Report Success/Failure
    if ack["message_id"] == message["message_id"]:
        print("Message", counter, "confirmed")
    else:
        print("Message", counter, "failed: ACK was for message", ack["message_id"])

client.close()
