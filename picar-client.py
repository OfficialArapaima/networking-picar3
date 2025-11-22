from socket import *


manual = '''
Press keys on keyboard to control PiCar-X!
    w: Forward
    a: Turn left
    s: Backward
    d: Turn right
    ctrl+c: Quit
'''

def show_info():
    print(manual)


def main():
    serverName = input('Input the PiCar\'s server address:')

    serverPort = 12000
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((serverName, serverPort))


    while True:
        key = input('Input lowercase sentence:')
        if key == "exit":
               break
        if key in ('wsad'):
            clientSocket.send(key.encode())
            modifiedSentence = clientSocket.recv(1024)
            print('From Server: ', modifiedSentence.decode())
            
    clientSocket.close()

main()