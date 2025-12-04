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
    q: Quit (stops car)
    ctrl+c: Quit (stops car)
'''

# Create directory for received images
if not os.path.exists('received_faces'):
    os.makedirs('received_faces')
    print("Created 'received_faces' folder for captured images")

running = True  # Global flag to control threads

def show_info():
    print(manual)

def receive_data(clientSocket):
    """Background thread to receive all data (images and text responses) from server"""
    global running
    buffer = b""
    
    while running:
        try:
            clientSocket.settimeout(0.5)  # Short timeout to check running flag
            try:
                data = clientSocket.recv(4096)
            except timeout:
                continue
            
            if not data:
                print("\nConnection closed by server")
                break
            
            buffer += data
            
            # Process buffer - look for images or text messages
            while len(buffer) > 0:
                img_marker_pos = buffer.find(b"IMG")
                
                # Check if this is an image
                if img_marker_pos == 0 and len(buffer) >= 21:
                    # Extract header info
                    header_start = 3
                    try:
                        timestamp = buffer[header_start:header_start + 14].decode('utf-8')
                        img_size = struct.unpack('>I', buffer[header_start + 14:header_start + 18])[0]
                        
                        img_data_start = header_start + 18
                        img_data_end = img_data_start + img_size
                        
                        # Check if we have the full image
                        if len(buffer) >= img_data_end:
                            # Extract and save image
                            img_data = buffer[img_data_start:img_data_end]
                            filename = f"received_faces/face_{timestamp}.jpg"
                            with open(filename, 'wb') as f:
                                f.write(img_data)
                            
                            print(f"\n✓ Face image received and saved: {filename}")
                            
                            # Remove processed data
                            buffer = buffer[img_data_end:]
                        else:
                            # Wait for more data
                            break
                    except Exception as e:
                        # Not a valid image header, treat as text
                        buffer = buffer[1:]  # Skip one byte and try again
                        
                elif img_marker_pos > 0:
                    # There's text before the image marker - print it
                    text_data = buffer[:img_marker_pos]
                    try:
                        text = text_data.decode('utf-8').strip()
                        if text:
                            print(f"From Server: {text}")
                    except:
                        pass
                    buffer = buffer[img_marker_pos:]
                    
                elif img_marker_pos == -1:
                    # No image marker - this is text response
                    # Check if it looks like a complete message (no partial IMG)
                    if b"IMG" not in buffer:
                        try:
                            text = buffer.decode('utf-8').strip()
                            if text:
                                print(f"From Server: {text}")
                            buffer = b""
                        except:
                            # Might be partial binary data, keep it
                            if len(buffer) > 1000:  # Prevent buffer overflow
                                buffer = buffer[-100:]
                            break
                    else:
                        break
                else:
                    # img_marker_pos == 0 but not enough data for header
                    break
                    
        except Exception as e:
            if running:
                print(f"\nError receiving data: {e}")
            break


def main():
    global running
    
    serverName = input('Input the PiCar\'s server address: ')

    serverPort = 12000
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((serverName, serverPort))
    print(f"Connected to PiCar at {serverName}:{serverPort}\n")
    
    # Start background thread to receive all data (images + responses)
    recv_thread = threading.Thread(target=receive_data, args=(clientSocket,), daemon=True)
    recv_thread.start()

    show_info()
    
    try:
        while running:
            try:
                key = readchar.readkey()
                key = key.lower()
                
                if key == "exit":
                    break
                    
                if key in ('wsadfq'):
                    clientSocket.send(key.encode())
                    if key == 'q':
                        print("\nStopping car and quitting...")
                        sleep(0.5)  # Give server time to process
                        break
                        
                elif key == readchar.key.CTRL_C:
                    break
                    
            except KeyboardInterrupt:
                break
                
    except Exception as e:
        print(f"\nError: {e}")
    
    finally:
        # Always try to stop the car before quitting
        running = False
        try:
            clientSocket.send(b'q')  # Send quit command to stop car
            sleep(0.3)
        except:
            pass
        
        print("\nDisconnected. Car should be stopped.")
        clientSocket.close()

main()
