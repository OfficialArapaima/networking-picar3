from socket import *
from time import sleep
import readchar

manual = '''
Press keys on keyboard to control PiCar-X!
    w: Forward
    a: Turn left
    s: Backward
    d: Turn right
    ctrl+c: Quit
Input key to call the funtion!
    f: Turn on/off face detection
'''

def show_info():
    print(manual)


def main():
    serverName = input('Input the PiCar\'s server address:')

    serverPort = 12000
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((serverName, serverPort))

    # Starts the camera 
    Vilib.camera_start(vflip=False,hflip=False)
    Vilib.display(local=True,web=True)

# make the car move when single key is pressed continuously


    while True:
        key = readchar.readkey()
        key = key.lower()
        if key == "exit":
            break
        if key in ('wsadf'):
            if 'w' in key:        
                clientSocket.send(key.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
            if 's' in key:        
                clientSocket.send(key.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
            if 'a' in key:        
                clientSocket.send(key.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
            if 'd' in key:        
                clientSocket.send(key.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
            if 'f' in key:
                clientSocket.send(key.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())

        

        elif key == readchar.key.CTRL_C:
                print("\n Quit")
                break


            
    clientSocket.close()

main()