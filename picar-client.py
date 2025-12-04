#!/usr/bin/env python3
"""
PiCar-X Client - Runs on Mac/PC
Sends keyboard commands to control the PiCar-X robot.
View camera at http://<pi-ip>:9000/mjpg in your browser.
"""

from socket import socket, AF_INET, SOCK_STREAM, timeout
from time import sleep
import readchar
import threading
import sys

MANUAL = '''
╔══════════════════════════════════════════════════════════════╗
║              PiCar-X Keyboard Control                        ║
╠══════════════════════════════════════════════════════════════╣
║  MOVEMENT              CAMERA HEAD                           ║
║    w : Forward           i : Tilt up                         ║
║    s : Backward          k : Tilt down                       ║
║    a : Turn left         j : Pan left                        ║
║    d : Turn right        l : Pan right                       ║
║    x : Stop                                                  ║
║                                                              ║
║  SPEED                 DETECTION MODES                       ║
║    + : Speed up          f : Toggle face detection           ║
║    - : Speed down        c : Cycle color detection           ║
║                          r : Toggle QR detection             ║
║                        0-6 : Color select (0=off, 1-6=color) ║
║                                                              ║
║  UTILITY                                                     ║
║    p : Take photo (saved on Pi)                              ║
║    n : Show detection info                                   ║
║    h : Help                                                  ║
║    q : Quit                                                  ║
║                                                              ║
║  Camera view: http://<pi-ip>:9000/mjpg                       ║
╚══════════════════════════════════════════════════════════════╝
'''

running = True


def receive_responses(client_socket):
    """Background thread to receive and display server responses"""
    global running
    
    while running:
        try:
            client_socket.settimeout(0.5)
            try:
                data = client_socket.recv(1024)
            except timeout:
                continue
            
            if not data:
                print("\n[Connection closed by server]")
                running = False
                break
            
            response = data.decode('utf-8').strip()
            if response:
                print(f"\r  → {response}")
                print("Command: ", end='', flush=True)
                
        except Exception as e:
            if running:
                print(f"\n[Error receiving: {e}]")
            break


def main():
    global running
    
    print("\n" + "="*60)
    print("       PiCar-X Remote Control Client")
    print("="*60 + "\n")
    
    # Get server address
    server_ip = input("Enter PiCar IP address: ").strip()
    if not server_ip:
        print("No IP provided. Exiting.")
        return
    
    server_port = 12000
    
    # Connect to server
    print(f"\nConnecting to {server_ip}:{server_port}...")
    
    try:
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((server_ip, server_port))
        print("Connected!\n")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
    
    # Start response receiver thread
    recv_thread = threading.Thread(target=receive_responses, args=(client_socket,), daemon=True)
    recv_thread.start()
    
    # Show controls
    print(MANUAL)
    
    print(f"\nCamera stream: http://{server_ip}:9000/mjpg")
    print("Open this URL in your browser to view the camera.\n")
    
    valid_commands = 'wasxdikjl+-=_fcr0123456pnhq'
    
    try:
        while running:
            print("Command: ", end='', flush=True)
            
            try:
                key = readchar.readkey()
            except KeyboardInterrupt:
                break
            
            # Handle special keys
            if key == readchar.key.CTRL_C:
                break
            
            key = key.lower()
            
            # Check if valid command
            if key in valid_commands:
                try:
                    client_socket.send(key.encode())
                except Exception as e:
                    print(f"\n[Send error: {e}]")
                    break
                
                if key == 'q':
                    print("\nQuitting...")
                    sleep(0.3)
                    break
            else:
                print(f"\r  [Invalid key: '{key}' - press 'h' for help]")
            
            sleep(0.05)
            
    except Exception as e:
        print(f"\nError: {e}")
    
    finally:
        running = False
        
        # Try to send quit command
        try:
            client_socket.send(b'q')
            sleep(0.2)
        except:
            pass
        
        client_socket.close()
        print("\nDisconnected from PiCar-X")


if __name__ == "__main__":
    main()
