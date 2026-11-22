import socket
import json
import threading as t
import address_book as a

HOST = a.IP_ADDRESS
LISTENING_PORT = a.RELAY_PORT
RELEASE_PORT = a.RECONNECT_RELEASE

message_log = []

def handle_new_transmitter(client, addr):
    buffer = b""
    while True:
        try:
            chunk = client.recv(a.BUFFER_SIZE)
        except ConnectionResetError:
            print(f"transmitter {addr} disconnected")
            break
        if not chunk: break

        buffer += chunk
        data = buffer.decode('utf-8')

        while True:
            try:
                json_data, end = json.JSONDecoder().raw_decode(data)
            except json.JSONDecodeError: break

            data = data[end:]
            buffer = data.encode('utf-8')

            dest = int(json_data['destination_port'])
            payload = json_data['payload']
            
            print(json_data)
            client.sendall(b'{"status":"accepted"}')
        
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as deliver:
                    deliver.bind((HOST, dest))
                    deliver.listen(1)
                    recipient, recipient_addr = deliver.accept()
            
                    json_payload = json.dumps(payload).encode('utf-8')
                    recipient.send(json_payload)
            except OSError as e:
                print(f"Relay {dest} has failed: {e}")

            message = [addr, dest, payload]
            message_log.append(message)


def requestRelease():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as release:
        release.connect((HOST, RELEASE_PORT))
        release.sendall(b'{"status":"alive"}')
        
        data = release.recv(a.BUFFER_SIZE)
        ack = json.loads(data.decode('utf-8'))
        print(f"ACK: {ack}")


relay = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

while True:
    try:
        relay.bind((HOST, LISTENING_PORT))
        break
    except OSError as e:
        if e.errno == 98 or e.errno == 48:
            requestRelease()

relay.listen(3)
while True:
    try:
        client, addr = relay.accept()
        thread = t.Thread(
            target=handle_new_transmitter,
            args=(client, addr),
            daemon=True
        )
        thread.start()
    except KeyboardInterrupt:
        print("Relay Shutting Down")
        break

relay.close()





