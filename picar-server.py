import sys
from socket import *
serverPort = 12000

# bind the server to the socket
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(("", serverPort))
print("Server started on port: %s" % serverPort)
serverSocket.listen(1)
print('The server is now listening...\n')
connectionSocket, addr = serverSocket.accept()


while True:
    print('New connection from %s:%d' % (addr[0], addr[1]))
    data = connectionSocket.recv(1024).decode()
    if not data:
        break
    elif data == 'killsrv':
        connectionSocket.close()
        sys.exit()
    else:
       print(data)

    connectionSocket.send(data.encode())
    
connectionSocket.close()