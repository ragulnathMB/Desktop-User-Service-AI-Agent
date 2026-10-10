from PySide6.QtCore import QLockFile, qVersion
from PySide6.QtWidgets import QApplication, QLabel
import sys

app = QApplication(sys.argv)
label = QLabel(f"Qt {qVersion()} loaded successfully")
label.resize(320, 80)
label.show()
sys.exit(app.exec())
