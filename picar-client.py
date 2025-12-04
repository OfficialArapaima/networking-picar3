from socket import *
from time import sleep
import readchar
import threading
import os
import struct

manual = '''
Press keys on keyboard to control PiCar-X!
    w: Forward
    a: Turn left
    s: Backward
    d: Turn right
    f: Toggle face detection ON/OFF
    q: record/pause/continue
    e: stop
    ctrl+c: Quit
Input key to call the funtion!
    f: Turn on/off face detection
'''

# Create directory for received images
if not os.path.exists('received_faces'):
    os.makedirs('received_faces')
    print("Created 'received_faces' folder for captured images")

def show_info():
    print(manual)

def receive_images(clientSocket):
    """Background thread to continuously receive images from server"""
    buffer = b""
    
    while True:
        try:
            # Receive data in chunks
            data = clientSocket.recv(4096)
            if not data:
                print("\nConnection closed by server")
                break
            
            buffer += data
            
            # Look for image header (IMG marker + 14 byte timestamp + 4 byte size)
            while len(buffer) >= 21:  # Minimum header size: 3 (IMG) + 14 (timestamp) + 4 (size)
                img_marker_pos = buffer.find(b"IMG")
                
                if img_marker_pos == -1:
                    # No image marker found, might be a control message
                    # Keep last 20 bytes in case marker is split
                    if len(buffer) > 20:
                        buffer = buffer[-20:]
                    break
                
                # Check if we have full header
                if img_marker_pos + 21 > len(buffer):
                    break
                
                # Extract header info
                header_start = img_marker_pos + 3
                timestamp = buffer[header_start:header_start + 14].decode('utf-8')
                img_size = struct.unpack('>I', buffer[header_start + 14:header_start + 18])[0]
                
                img_data_start = header_start + 18
                img_data_end = img_data_start + img_size
                
                # Check if we have the full image
                if len(buffer) >= img_data_end:
                    # Extract image data
                    img_data = buffer[img_data_start:img_data_end]
                    
                    # Save image to file
                    filename = f"received_faces/face_{timestamp}.jpg"
                    with open(filename, 'wb') as f:
                        f.write(img_data)
                    
                    print(f"\n✓ Face image received and saved: {filename}")
                    
                    # Remove processed data from buffer
                    buffer = buffer[img_data_end:]
                else:
                    # Wait for more data
                    break
                    
        except Exception as e:
            print(f"\nError receiving image: {e}")
            break


def main():
    serverName = input('Input the PiCar\'s server address: ')

    serverPort = 12000
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((serverName, serverPort))
    print(f"Connected to PiCar at {serverName}:{serverPort}\n")
    
    # Start background thread to receive images
    img_thread = threading.Thread(target=receive_images, args=(clientSocket,), daemon=True)
    img_thread.start()

    # Starts the camera 
    Vilib.camera_start(vflip=False,hflip=False)
    Vilib.display(local=True,web=True)

# make the car move when single key is pressed continuously


    show_info()
    
    while True:
        try:
            key = readchar.readkey()
            key = key.lower()
            if key == "exit":
                break
            if key in ('wsadfqe'):
                clientSocket.send(key.encode())
                # Only wait for response on 'f' command (toggle face detection)
                if 'f' in key:
                    # Set timeout for receiving response
                    clientSocket.settimeout(1.0)
                    try:
                        response = clientSocket.recv(1024)
                        print('From Server: ', response.decode())
                    except timeout:
                        pass
                    finally:
                        clientSocket.settimeout(None)
            elif key == readchar.key.CTRL_C:
                    print("\n Quit")
                    break
        except KeyboardInterrupt:
            print("\n Quit")
            break


            
    clientSocket.close()

main()