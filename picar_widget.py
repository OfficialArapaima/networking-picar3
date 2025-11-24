from socket import *
import sys
import random
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QGridLayout
from PySide6.QtCore import Slot, Qt, Signal

serverName = input('Input the PiCar\'s server address:')

serverPort = 12000
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName, serverPort))

class KeyboardControl(QWidget):
    # direction is one of: "forward", "left", "backward", "right"
    moveStarted = Signal(str)
    moveStopped = Signal(str)

    @Slot()
    def buttonPressed(self):
        key = self.sender().text()

        if key in ('WASD'):
            if 'W' in key:        
                clientSocket.send('start forward'.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
            if 'S' in key:        
                clientSocket.send('start backward'.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
            if 'A' in key:        
                clientSocket.send('start left'.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
            if 'D' in key:        
                clientSocket.send('start right'.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
        
            

    @Slot()
    def buttonReleased(self):
        key = self.sender().text()

        if key in ('WASD'):
            if 'W' in key:        
                clientSocket.send('stop forward'.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
            if 'S' in key:        
                clientSocket.send('stop backward'.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
            if 'A' in key:        
                clientSocket.send('stop left'.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())
            if 'D' in key:        
                clientSocket.send('stop right'.encode())
                modifiedSentence = clientSocket.recv(1024)
                print('From Server: ', modifiedSentence.decode())

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("WASD Controller")
        self.setFocusPolicy(Qt.StrongFocus)  # so we get key events

        # Base and active styles
        self.base_style = (
            "QPushButton {"
            "  font-size: 24px;"
            "  min-width: 60px;"
            "  min-height: 60px;"
            "}"
        )
        self.active_style = self.base_style + " QPushButton { background-color: #87cefa; }"

        # Create buttons
        self.btn_w = QPushButton("W")
        self.btn_a = QPushButton("A")
        self.btn_s = QPushButton("S")
        self.btn_d = QPushButton("D")

        self.key_to_button = {
            Qt.Key_W: self.btn_w,
            Qt.Key_S: self.btn_s,
            Qt.Key_A: self.btn_a,
            Qt.Key_D: self.btn_d,
        }

        for btn in (self.btn_w, self.btn_a, self.btn_s, self.btn_d):
            btn.setStyleSheet(self.base_style)
            btn.setFocusPolicy(Qt.NoFocus)  # keep focus on the main widget

        # Layout: W on top, A S D on bottom row
        layout = QGridLayout()
        layout.addWidget(self.btn_w, 0, 1)
        layout.addWidget(self.btn_a, 1, 0)
        layout.addWidget(self.btn_s, 1, 1)
        layout.addWidget(self.btn_d, 1, 2)
        self.setLayout(layout)

        # Track which directions are currently active
        self.active_dirs = set()

        # Mouse press/release on buttons should behave the same as keys
        self.btn_w.pressed.connect(self.buttonPressed)
        self.btn_a.pressed.connect(self.buttonPressed)
        self.btn_s.pressed.connect(self.buttonPressed)
        self.btn_d.pressed.connect(self.buttonPressed)

        self.btn_w.released.connect(self.buttonReleased)
        self.btn_a.released.connect(self.buttonReleased)
        self.btn_s.released.connect(self.buttonReleased)
        self.btn_d.released.connect(self.buttonReleased)

    # # ---------- keyboard handling ----------

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return

        btn = self.key_to_button.get(event.key())
        if btn is not None:
            btn.setDown(True)
            btn.setStyleSheet(self.active_style)
            btn.pressed.emit()



    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return

        btn = self.key_to_button.get(event.key())
        if btn is not None:
            btn.setDown(False)
            btn.setStyleSheet(self.base_style)
            btn.released.emit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = KeyboardControl()

    widget.show()
    sys.exit(app.exec())