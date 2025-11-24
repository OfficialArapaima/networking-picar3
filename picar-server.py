import sys
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

while True:
    data = connectionSocket.recv(1024).decode()
    match data:
        case 'start forward':
            px.forward(80)
        case 'start backward':
            px.backward(80)
        case 'start left':
            for i in range(7):
                px.set_dir_servo_angle(-i * 5 - 5)
        case 'start right':
            for i in range(7):
                px.set_dir_servo_angle(i * 5 + 5)
        case 'stop forward':
            px.forward(0)
        case 'stop backward':
            px.forward(0)
        case 'stop left':
            for i in range(7):
                px.set_dir_servo_angle(-i * 5 - 5)
        case 'stop right':
            for i in range(7):
                px.set_dir_servo_angle(i * 5 + 5)
        
    connectionSocket.send(data.encode())

# while True:
#     print('New connection from %s:%d' % (addr[0], addr[1]))
#     data = connectionSocket.recv(1024).decode()
#     if not data:
#         break
#     if 'w' in data:
#         px.set_dir_servo_angle(0)
#         px.forward(80)
#     elif 's' == data:
#         px.set_dir_servo_angle(0)
#         px.backward(80)
#     elif 'a' == data:
#         px.set_dir_servo_angle(-35)
#         px.forward(80)
#     elif 'd' == data:
#         px.set_dir_servo_angle(35)
#         px.forward(80)
#     elif data == 'q':
#         px.stop()
#         sys.exit()
#         connectionSocket.close()
#     else:
#        print(data)

    
connectionSocket.close()