from socket import *
import sys
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QWidget,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import Slot, Qt

serverName = input("Input the PiCar's server address: ")

serverPort = 12000
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName, serverPort))

recv_buffer = b""  # global above

def recv_line(sock):
    """
    Read a single newline-terminated line from the server.
    Returns:
        - str (possibly empty) when a line is received
        - None only when the socket is actually closed
    """
    global recv_buffer

    while True:
        if b"\n" in recv_buffer:
            line, recv_buffer = recv_buffer.split(b"\n", 1)
            return line.decode(errors="ignore").rstrip("\r")

        chunk = sock.recv(1024)
        if not chunk:
            # Real connection close
            return None
        recv_buffer += chunk

def recv_multiline(sock):
    lines = []
    while True:
        line = recv_line(sock)
        if line is None:
            return None
        if line == "<END>":
            break
        lines.append(line)
    return "\n".join(lines)


welcome = recv_line(clientSocket)
if welcome:
    print("From Server:", welcome)


# Keys physically available on the UI / keyboard
available_keys = "wasxdikjl+-=_rpnhq"

# Commands (use UPPERCASE for letter keys as the canonical form)
key_to_command = {
    "W": "forward",
    "A": "left",
    "S": "backward",
    "D": "right",
    "I": "cam_up",
    "K": "cam_down",
    "J": "cam_left",
    "L": "cam_right",
    "=": "speed_increase",
    "-": "speed_decrease",
    "P": "take_photo",
    "N": "show_detect",
    "H": "help",
}

# Human-friendly labels for buttons
button_labels = {
    "W": "Forward",
    "A": "Left",
    "S": "Backward",
    "D": "Right",
    "I": "Camera Up",
    "K": "Camera Down",
    "J": "Camera Left",
    "L": "Camera Right",
    "=": "Increase Speed",
    "-": "Decrease Speed",
    "P": "Take Photo",
    "N": "Show Detection",
    "H": "Help",
}

# Keys that are continuous (start on press, stop on release)
CONTINUOUS_KEYS = {"W", "A", "S", "D", "I", "J", "K", "L", "=", "-"}

# Keys that are toggles / one-shot (activate on release only)
TOGGLE_KEYS = {"P", "N", "H"}

# Map logical key -> Qt key (for keyboard handling)
KEY_TO_QT = {
    "W": Qt.Key_W,
    "A": Qt.Key_A,
    "S": Qt.Key_S,
    "D": Qt.Key_D,
    "I": Qt.Key_I,
    "J": Qt.Key_J,
    "K": Qt.Key_K,
    "L": Qt.Key_L,
    "=": Qt.Key_Equal,
    "-": Qt.Key_Minus,
    "P": Qt.Key_P,
    "N": Qt.Key_N,
    "H": Qt.Key_H,
}


class KeyboardControl(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("PiCar Controller")
        self.setFocusPolicy(Qt.StrongFocus)  # so we get key events

        # Base and active styles
        self.base_style = (
            "QPushButton {"
            "  font-size: 18px;"
            "  min-width: 140px;"
            "  min-height: 40px;"
            "}"
        )
        self.active_style = (
            "QPushButton {"
            "  font-size: 18px;"
            "  min-width: 140px;"
            "  min-height: 40px;"
            "  background-color: #87cefa;"
            "}"
        )

        # Create all buttons once, keyed by logical key (e.g. "W", "F", "=")
        self.buttons = {}
        self.button_to_key = {}  # QPushButton -> logical key

        for ch in available_keys:
            # Canonical logical key: letters uppercase, symbols as-is
            key = ch.upper() if ch.isalpha() else ch

            # Only build buttons for keys we actually have commands for
            if key not in key_to_command:
                continue

            label_text = button_labels.get(key, f"Key {key}")
            btn = QPushButton(f"{label_text} ({key})")
            btn.setStyleSheet(self.base_style)
            btn.setFocusPolicy(Qt.NoFocus)

            self.buttons[key] = btn
            self.button_to_key[btn] = key

        # Layouts
        main_layout = QGridLayout()
        main_layout.setHorizontalSpacing(40)

        # --- Car controls (WASD + speed) ---
        car_label = QLabel("Car Controls")
        car_label.setAlignment(Qt.AlignHCenter)

        car_grid = QGridLayout()
        # WASD positions
        car_positions = {
            "W": (0, 1),
            "A": (1, 0),
            "S": (1, 1),
            "D": (1, 2),
        }
        for key, (r, c) in car_positions.items():
            if key in self.buttons:
                car_grid.addWidget(self.buttons[key], r, c)

        # Speed controls row
        speed_layout = QHBoxLayout()
        for key in ["-", "="]:
            if key in self.buttons:
                speed_layout.addWidget(self.buttons[key])

        car_column = QVBoxLayout()
        car_column.addWidget(car_label)
        car_column.addLayout(car_grid)
        car_column.addLayout(speed_layout)

        # --- Camera controls (IJKL) ---
        cam_label = QLabel("Camera Controls")
        cam_label.setAlignment(Qt.AlignHCenter)

        cam_grid = QGridLayout()
        cam_positions = {
            "I": (0, 1),
            "J": (1, 0),
            "K": (1, 1),
            "L": (1, 2),
        }
        for key, (r, c) in cam_positions.items():
            if key in self.buttons:
                cam_grid.addWidget(self.buttons[key], r, c)

        cam_column = QVBoxLayout()
        cam_column.addWidget(cam_label)
        cam_column.addLayout(cam_grid)

        # --- Other controls (toggles) ---
        other_label = QLabel("Other Controls")
        other_label.setAlignment(Qt.AlignHCenter)

        other_column = QVBoxLayout()
        other_column.addWidget(other_label)
        for key in ["P", "N", "H"]:
            if key in self.buttons:
                other_column.addWidget(self.buttons[key])

        # Add the three columns to the main layout
        main_layout.addLayout(car_column, 0, 0)
        main_layout.addLayout(cam_column, 0, 1)
        main_layout.addLayout(other_column, 0, 2)

        self.setLayout(main_layout)

        # Map Qt keys to buttons for keyboard handling
        self.key_to_button = {}
        for key, btn in self.buttons.items():
            qt_key = KEY_TO_QT.get(key)
            if qt_key is not None:
                self.key_to_button[qt_key] = btn

        # Connect all buttons that have commands
        for btn in self.button_to_key.keys():
            btn.pressed.connect(self.buttonPressed)
            btn.released.connect(self.buttonReleased)

    # ---------- networking helper ----------

    def _send_command(self, action: str, key_char: str):
        command = key_to_command.get(key_char)
        if not command:
            return

        # Send newline-terminated command
        msg = f"{action} {command}\n"
        clientSocket.sendall(msg.encode())

        # Read multiline response block (<END> terminated)
        response = recv_multiline(clientSocket)

        if response is None:
            print("From Server: <connection closed>")
            return

        # Print the full block only if it's not empty
        if response.strip():
            print("From Server:")
            print(response)



    # ---------- button slots ----------

    @Slot()
    def buttonPressed(self):
        sender = self.sender()
        key_char = self.button_to_key.get(sender)
        if not key_char:
            return

        # Continuous controls: start on press
        if key_char in CONTINUOUS_KEYS:
            self._send_command("start", key_char)
        # Toggle controls: do nothing on press (only on release)

    @Slot()
    def buttonReleased(self):
        sender = self.sender()
        key_char = self.button_to_key.get(sender)
        if not key_char:
            return

        # Continuous controls: stop on release
        if key_char in CONTINUOUS_KEYS:
            self._send_command("stop", key_char)

        # Toggle controls: activate on release
        elif key_char in TOGGLE_KEYS:
            self._send_command("start", key_char)

    # ---------- keyboard handling ----------

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
