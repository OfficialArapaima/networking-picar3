from socket import *
import sys
import random
from PySide6.QtWidgets import QApplication, QPushButton, QDialog, QLineEdit, QVBoxLayout, QWidget, QGridLayout
from PySide6.QtCore import Slot, Qt, Signal

class KeyboardControl(QWidget):
    # direction is one of: "forward", "left", "backward", "right"
    moveStarted = Signal(str)
    moveStopped = Signal(str)

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
        self.btn_w.pressed.connect()
        self.btn_a.pressed.connect()
        self.btn_s.pressed.connect()
        self.btn_d.pressed.connect()

        self.btn_w.released.connect()
        self.btn_a.released.connect()
        self.btn_s.released.connect()
        self.btn_d.released.connect()

    def buttonPressed():
        print("Hello")

    # # ---------- keyboard handling ----------

    # def keyPressEvent(self, event):
    #     if event.isAutoRepeat():
    #         return

    #     info = self.key_map.get(event.key())
    #     if info is None:
    #         super().keyPressEvent(event)
    #         return

    #     direction, button = info
    #     self._on_direction_press(direction, button)

    # def keyReleaseEvent(self, event):
    #     if event.isAutoRepeat():
    #         return

    #     info = self.key_map.get(event.key())
    #     if info is None:
    #         super().keyReleaseEvent(event)
    #         return

    #     direction, button = info
    #     self._on_direction_release(direction, button)

    # def _on_direction_press(self, direction: str, button: QPushButton):
    #     if direction in self.active_dirs:
    #         return
    #     self.active_dirs.add(direction)
    #     button.setStyleSheet(self.active_style)
    #     self.moveStarted.emit(direction)

    # def _on_direction_release(self, direction: str, button: QPushButton):
    #     if direction not in self.active_dirs:
    #         return
    #     self.active_dirs.remove(direction)
    #     button.setStyleSheet(self.base_style)
    #     self.moveStopped.emit(direction)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = KeyboardControl()

    widget.show()
    sys.exit(app.exec())