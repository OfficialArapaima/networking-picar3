import threading
import time
from socket import *
from picarx import Picarx
serverPort = 12000

# bind the server to the socket
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(("", serverPort))
print("Server started on port: %s" % serverPort)
serverSocket.listen(1)
print('The server is now listening...\n')
connectionSocket, addr = serverSocket.accept()

px = Picarx()

# set up global variables needed
current_angle = 0;
target_angle = 0;
running = True;

def steering_loop():
    global current_angle, target_angle, running, px
    while running:
        if current_angle < target_angle:
            current_angle += 1
        elif current_angle > target_angle:
            current_angle -= 1

        px.set_dir_servo_angle(current_angle)
        time.sleep(0.005)

def server_loop():
    global target_angle, running, px
    while running:
        data = connectionSocket.recv(1024).decode()
        match data:
            case 'start forward':
                px.forward(80)
            case 'start backward':
                px.backward(80)
            case 'start left':
                target_angle = -35
            case 'start right':
                target_angle = 35
            case 'stop forward':
                px.forward(0)
            case 'stop backward':
                px.forward(0)
            case 'stop left' | 'stop right':
                target_angle = 0
            
        connectionSocket.send(data.encode())

def main():
    steer_thread = threading.Thread(target=steering_loop, daemon=True)
    steer_thread.start()
    server_thread = threading.Thread(target=server_loop())
    server_thread.start()

main()  
# connectionSocket.close()