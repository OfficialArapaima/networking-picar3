import sys
import random
from PySide6.QtWidgets import QApplication, QPushButton, QDialog, QLineEdit, QVBoxLayout
from PySide6.QtCore import Slot

class Form(QDialog):
    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.setWindowTitle("My Form")

        self.edit = QLineEdit("Write here...")
        self.button = QPushButton("Submit")

        #create layout and add the widgets
        layout = QVBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)

        self.button.clicked.connect(self.greeting)

    # Greets the user
    def greeting(self):
        print(f'You submitted {self.edit.text()}')

if __name__ == '__main__':
    # Create the Qt Application
    app = QApplication(sys.argv)
    # Create and show the form
    form = Form()
    form.show()
    # Run the main Qt loop
    sys.exit(app.exec())