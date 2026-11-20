import socket
import time
import address_book as a

# Connection Settings - Might change in the future

HOST = a.IP_ADDRESS       # IP address of coms relay
PORT = a.RX_1             # port number used by coms relay

RECEIVER_ID = "RX1"     # how relay identifies each receiver
RETRY_TIME = 2          # number of seconds before trying to reconnect

# Main program

while True:
    try:
        print("Connecting to the relay...")

        # attempt to connect to relay
        receiver = socket.create_connection((HOST, PORT), timeout=5)

        # once connected, wait for messages without a time limit
        receiver.settimeout(None)

        print("Connected to the relay. Waiting for messages...")

        while True:
            # recieve up to 1024 bytes of data
            message = receiver.recv(a.BUFFER_SIZE)

            # if no data is received, the connection has closed
            if not message:
                print("Connection is lost.")
                break

            # convert the received bytes into the readable text
            message = message.decode("utf-8")

            # display the received message
            print ("Message received: ", message)

        # close the connection
        receiver.close()

    except OSError:

        #runs if the relay is unavailable or the connection is lost
        print("Relay unavailable.")

    except KeyboardInterrupt:

        # user stops program with Ctrl+C
        print("Program stopped by user.")
        break

    # wait before trying to reconnect
    print ("Retrying to connect...")
    time.sleep(RETRY_TIME)