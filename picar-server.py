import sys
from socket import *
from picarx import Picarx
from vilib import Vilib
serverPort = 12000

# bind the server to the socket
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(("", serverPort))
print("Server started on port: %s" % serverPort)
serverSocket.listen(1)
print('The server is now listening...\n')
connectionSocket, addr = serverSocket.accept()

# Face detect function
def face_detect(flag):
    print("Face Detect:" + str(flag))
    Vilib.face_detect_switch(flag)


    



px = Picarx()
while True:
    print('New connection from %s:%d' % (addr[0], addr[1]))
    data = connectionSocket.recv(1024).decode()
    if not data:
        break
    if 'w' in data:
        px.set_dir_servo_angle(0)
        px.forward(80)
    elif 's' == data:
        px.set_dir_servo_angle(0)
        px.backward(80)
    elif 'a' == data:
        px.set_dir_servo_angle(-35)
        px.forward(80)
    elif 'd' == data:
        px.set_dir_servo_angle(35)
        px.forward(80)
    elif 'f'== data:
        flag_face = not flag_face
        face_detect(flag_face)
    elif data == 'q':
        px.stop()
        sys.exit()
        connectionSocket.close()
    else:
       print(data)

    connectionSocket.send(data.encode())

connectionSocket.close()