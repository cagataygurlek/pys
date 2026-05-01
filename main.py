# main.py

import sys
import os
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from ui.firma_secim_dialog import FirmaSecimDialog
from database import set_database
from ui.main_window import MainWindow


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))


def main():
    app = QApplication(sys.argv)

    # Uygulama genel iconunu ayarla (görev çubuğu için)
    icon = QIcon()
    base_dir = get_base_dir()
    for size in [256, 128, 64, 48, 32, 24, 16]:
        icon_path = os.path.join(base_dir, f"pys_icon_{size}x{size}.png")
        if os.path.exists(icon_path):
            icon.addFile(icon_path, QSize(size, size))
    if not icon.isNull():
        app.setWindowIcon(icon)

    # Takvim stilleri (yıl değiştirme okları için)
    app.setStyleSheet("""
        QCalendarWidget QToolButton {
            width: 30px;
            height: 24px;
            background-color: #34495e;
            color: white;
            border-radius: 4px;
        }
        QCalendarWidget QToolButton:hover {
            background-color: #3498db;
        }
        QCalendarWidget QMenu {
            background-color: #2c3e50;
            color: white;
        }
    """)

    firma_dialog = FirmaSecimDialog()
    if firma_dialog.exec_() == QDialog.Accepted:
        db_path = firma_dialog.selected_db
        set_database(db_path)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit()


if __name__ == "__main__":
    main()