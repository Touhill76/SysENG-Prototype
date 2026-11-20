import socket
import json



#1. Build Message
#2. Add Routing Info
#3. Transmit
#4. Wait for ACK
#5. Verify ACK
#6. Report Success/Failure

# Transmitter 
# Central node address
HOST = "127.0.0.1"
PORT = 5000

# Message to send
message = {
    "message_id": 1,
    "source_port": 5000,
    "destination_port": 5005,
    "payload": "hello from transmitter 5000"
}
counter = 0 
# Create TCP socket object
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to central node
client.connect((HOST, PORT))  # connect to this computer and this program

# Convert dict to JSON bytes
packet = json.dumps(message).encode("utf-8")

# Send message
while counter <6 :
    client.sendall(packet)
    counter=counter+1
    print("Message sent")

# Wait for acknowledgment
ack_data = client.recv(4096)

# Convert back to Python object
ack = json.loads(ack_data.decode("utf-8"))

print("ACK:", ack)

# Check acknowledgment
if ack["message_id"] == message["message_id"]:
    print("Message confirmed")

client.close()