# main.py

import os
import PyQt5
dirname = os.path.dirname(PyQt5.__file__)
plugin_path = os.path.join(dirname, 'Qt5', 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
import sys

from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtCore import QSize, QTimer
from ui.firma_secim_dialog import FirmaSecimDialog
from ui.giris_dialog import GirisDialog
from ui.lisans_dialog import LisansDialog
from database import set_database, get_session, get_db_type
from connection_manager import keepalive
from ui.main_window import MainWindow
from license_checker import check_license, get_saved_key
from migrate_db import add_columns


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))


def main():
    app = QApplication(sys.argv)

    # Uygulama genel arka plan rengini koyu yap
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor("#2c3e50"))
    palette.setColor(QPalette.WindowText, QColor("#ecf0f1"))
    app.setPalette(palette)

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

    # 0. Lisans Kontrolü
    try:
        saved_key = get_saved_key()
        if saved_key:
            gecerli, mesaj, _ = check_license(saved_key)
            if not gecerli:
                lisans_dlg = LisansDialog(hata_mesaji=mesaj)
                if lisans_dlg.exec_() != QDialog.Accepted:
                    sys.exit()
        else:
            lisans_dlg = LisansDialog()
            if lisans_dlg.exec_() != QDialog.Accepted:
                sys.exit()
    except Exception:
        from ui.utils import ModernMesaj
        msg = ModernMesaj(None, ModernMesaj.HATA,
            "Lisans Hatası",
            "Lisans kontrolü sırasında bir hata oluştu.\n"
            "İnternet bağlantınızı kontrol edin.")
        msg.exec_()
        sys.exit()

    # 1. Firma Seçimi
    firma_dialog = FirmaSecimDialog()
    if firma_dialog.exec_() != QDialog.Accepted:
        sys.exit()

    db_path = firma_dialog.selected_db
    set_database(db_path)
    add_columns()

    # 2. Kullanıcı Girişi
    session = get_session()
    giris_dialog = GirisDialog(session=session)
    if giris_dialog.exec_() != QDialog.Accepted:
        session.close()
        sys.exit()

    giris_yapan = giris_dialog.kullanici
    _ = giris_yapan.yetkileri
    _ = giris_yapan.subeleri
    session.close()

    # 3. Ana Pencere
    window = MainWindow(kullanici=giris_yapan)
    window.show()

    # 4. Neon cold start engelleme (yalnızca PostgreSQL'de)
    if get_db_type() == "postgresql":
        _keepalive_timer = QTimer()
        _keepalive_timer.timeout.connect(keepalive)
        _keepalive_timer.start(60000)  # her 60 sn'de bir ping
        window._keepalive_timer = _keepalive_timer  # referansı canlı tut

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
