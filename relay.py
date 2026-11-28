import socket
import json
import time
import threading as t
import address_book as a

HOST = a.IP_ADDRESS
LISTENING_PORT = a.RELAY_PORT

message_log = []


def allow_quick_rebind(sock):
    # Let a port be reused right after the program that held it stops.
    # Windows: exclusive use, so the relay can't bind while ReConnect holds the port.
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


def deliver(message, dest):
    # Receivers listen on their own port; connect, send the whole message, close.
    try:
        with socket.create_connection((HOST, dest), timeout=2) as recipient:
            recipient.sendall(json.dumps(message).encode('utf-8'))
        return True, ""
    except OSError as e:
        return False, str(e)


def handle_new_transmitter(client, addr):
    decoder = json.JSONDecoder()
    buffer = ""
    with client:
        while True:
            try:
                chunk = client.recv(a.BUFFER_SIZE)
            except OSError:
                print(f"transmitter {addr} disconnected")
                break
            if not chunk: break

            buffer += chunk.decode('utf-8', errors='replace')

            while True:
                buffer = buffer.lstrip()
                try:
                    json_data, end = decoder.raw_decode(buffer)
                except json.JSONDecodeError: break
                buffer = buffer[end:]

                # ReConnect's health checks (and stray handover requests) need no answer
                if not isinstance(json_data, dict) or "monitor_packet" in json_data \
                        or "handover_key" in json_data:
                    continue

                message_id = json_data.get('message_id')
                dest = json_data.get('destination_port', json_data.get('destination'))
                print(json_data)

                if dest is None:
                    ok, error = False, "no destination_port"
                else:
                    ok, error = deliver(json_data, int(dest))
                if not ok:
                    print(f"Delivery to {dest} failed: {error}")

                message_log.append([addr, dest, json_data.get('payload')])

                # ACK after delivery, so "accepted" means the receiver got it
                ack = {"message_id": message_id,
                       "status": "accepted" if ok else "failed",
                       "handled_by": "relay"}
                if not ok:
                    ack["reason"] = error
                try:
                    client.sendall(json.dumps(ack).encode('utf-8'))
                except OSError:
                    return


def requestRelease():
    # ReConnect holds RELAY_PORT while the relay is down; present the handover key there.
    try:
        with socket.create_connection((HOST, LISTENING_PORT), timeout=2) as release:
            request = {"handover_key": a.RECONNECT_HANDOVER_KEY}
            release.sendall(json.dumps(request).encode('utf-8'))
            data = release.recv(a.BUFFER_SIZE)
        ack = json.loads(data.decode('utf-8')) if data else None
        print(f"ACK: {ack}")
    except (OSError, ValueError) as e:
        print(f"Handover request failed: {e}")


relay = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
allow_quick_rebind(relay)

while True:
    try:
        relay.bind((HOST, LISTENING_PORT))
        break
    except OSError:
        print(f"Port {LISTENING_PORT} is in use - asking ReConnect to hand it back")
        requestRelease()
        time.sleep(0.5)

relay.listen(5)
relay.settimeout(1.0)  # wake up every second so Ctrl+C works on Windows
print(f"Relay listening on port {LISTENING_PORT}", flush=True)

try:
    while True:
        try:
            client, addr = relay.accept()
        except socket.timeout:
            continue
        client.settimeout(None)
        thread = t.Thread(
            target=handle_new_transmitter,
            args=(client, addr),
            daemon=True
        )
        thread.start()
except KeyboardInterrupt:
    print("Relay Shutting Down")

relay.close()
