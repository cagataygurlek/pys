# ui/connection_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QFrame, QWidget, QComboBox, QGroupBox,
    QButtonGroup, QRadioButton, QStackedWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from ui.utils import ModernMesaj, make_frameless
from connection_manager import (
    load_config, save_config, test_postgresql_connection,
    list_pg_schemas, create_pg_database, init_postgresql, init_sqlite, get_db_folder
)
from urllib.parse import urlparse
import os


class ConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(520, 560)
        self.selected_type = None
        self.selected_db = None
        self.init_ui()
        self._load_config()

    def _ortala(self):
        if self.parent():
            pg = self.parent().frameGeometry()
            x = pg.x() + (pg.width() - self.width()) // 2
            y = pg.y() + (pg.height() - self.height()) // 2 - 90
        else:
            screen = self.screen().availableGeometry()
            x = screen.x() + (screen.width() - self.width()) // 2
            y = screen.y() + (screen.height() - self.height()) // 2 - 90
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._ortala)

    def init_ui(self):
        bg = QFrame(self)
        bg.setGeometry(0, 0, 520, 520)
        bg.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 20px;
                border: 2px solid #34495e;
            }
        """)

        layout = QVBoxLayout(bg)
        layout.setContentsMargins(25, 15, 25, 20)
        layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("🔌 Veritabanı Bağlantısı")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; background: transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; color: #7f8c8d; font-size: 16px; border: none; border-radius: 14px; } QPushButton:hover { background: #e74c3c; color: white; }")
        close_btn.clicked.connect(self.reject)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        # Type selection
        type_group = QFrame()
        type_group.setStyleSheet("background: transparent; border: none;")
        type_lay = QHBoxLayout(type_group)
        type_lay.setContentsMargins(0, 0, 0, 0)

        self.type_radio_group = QButtonGroup(self)

        self.sqlite_radio = QRadioButton("💾 SQLite (Yerel)")
        self.sqlite_radio.setStyleSheet("QRadioButton { color: #ecf0f1; font-size: 13px; spacing: 8px; } QRadioButton::indicator { width: 18px; height: 18px; }")

        self.pg_radio = QRadioButton("🐘 PostgreSQL (Ağ)")
        self.pg_radio.setStyleSheet("QRadioButton { color: #ecf0f1; font-size: 13px; spacing: 8px; } QRadioButton::indicator { width: 18px; height: 18px; }")

        self.type_radio_group.addButton(self.sqlite_radio, 1)
        self.type_radio_group.addButton(self.pg_radio, 2)
        self.sqlite_radio.setChecked(True)

        type_lay.addWidget(self.sqlite_radio)
        type_lay.addSpacing(30)
        type_lay.addWidget(self.pg_radio)
        type_lay.addStretch()
        layout.addWidget(type_group)

        # Stack for settings
        self.stack = QStackedWidget()

        # SQLite page
        sqlite_widget = QWidget()
        sqlite_lay = QVBoxLayout(sqlite_widget)
        sqlite_lay.setContentsMargins(0, 5, 0, 0)

        sqlite_info = QLabel("SQLite veritabanı kullanılır.\nVeritabanı dosyaları DATA klasöründe saklanır.\nTek kullanıcı için uygundur.")
        sqlite_info.setStyleSheet("color: #bdc3c7; font-size: 12px; background: #34495e; padding: 12px; border-radius: 8px;")
        sqlite_lay.addWidget(sqlite_info)
        sqlite_lay.addStretch()
        self.stack.addWidget(sqlite_widget)

        # PostgreSQL page
        pg_widget = QWidget()
        pg_lay = QVBoxLayout(pg_widget)
        pg_lay.setContentsMargins(0, 5, 0, 0)
        pg_lay.setSpacing(8)

        form_style = """
            QLabel { color: #bdc3c7; font-size: 12px; background: transparent; }
            QLineEdit, QSpinBox, QComboBox {
                border: 1px solid #4a6278; border-radius: 6px;
                padding: 6px 10px; background: #34495e; color: white; font-size: 12px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #3498db;
            }
        """

        def _field(label):
            w = QWidget()
            w.setStyleSheet("background: transparent;")
            l = QHBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setFixedWidth(100)
            l.addWidget(lbl)
            return w, l

        w1, l1 = _field("Sunucu:")
        self.pg_host = QLineEdit("localhost")
        l1.addWidget(self.pg_host, 1)

        w2, l2 = _field("Port:")
        self.pg_port = QSpinBox()
        self.pg_port.setRange(1, 65535)
        self.pg_port.setValue(5432)
        self.pg_port.setFixedWidth(100)
        l2.addWidget(self.pg_port)
        l2.addStretch()

        w3, l3 = _field("Veritabanı:")
        self.pg_database = QLineEdit("pys")
        l3.addWidget(self.pg_database, 1)

        w4, l4 = _field("Kullanıcı:")
        self.pg_user = QLineEdit("postgres")
        l4.addWidget(self.pg_user, 1)

        w5, l5 = _field("Şifre:")
        self.pg_password = QLineEdit()
        self.pg_password.setEchoMode(QLineEdit.Password)
        l5.addWidget(self.pg_password, 1)

        w6, l6 = _field("Firma (Schema):")
        self.pg_schema = QComboBox()
        self.pg_schema.setEditable(True)
        self.pg_schema.setInsertPolicy(QComboBox.NoInsert)
        self.pg_schema.lineEdit().setPlaceholderText("Firma adı veya mevcut schema seçin")
        l6.addWidget(self.pg_schema, 1)

        for w in [w1, w2, w3, w4, w5, w6]:
            w.setStyleSheet("background: transparent;")
            pg_lay.addWidget(w)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        # URL paste field
        url_w = QWidget()
        url_w.setStyleSheet("background: transparent;")
        url_lay = QHBoxLayout(url_w)
        url_lay.setContentsMargins(0, 0, 0, 0)
        url_lbl = QLabel("Bağlantı URL:")
        url_lbl.setFixedWidth(100)
        self.pg_url = QLineEdit()
        self.pg_url.setPlaceholderText("postgresql://kullanici:sifre@host:5432/db?sslmode=require")
        self.pg_url.textChanged.connect(self._url_parse)
        url_lay.addWidget(url_lbl)
        url_lay.addWidget(self.pg_url, 1)
        pg_lay.addWidget(url_w)

        test_btn = QPushButton("🔄 Bağlantıyı Test Et")
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.setStyleSheet("QPushButton { background: #f39c12; color: white; font-weight: bold; border-radius: 6px; padding: 6px 12px; border: none; } QPushButton:hover { background: #e67e22; }")
        test_btn.clicked.connect(self._test_connection)

        list_btn = QPushButton("📋 Schemaları Listele")
        list_btn.setCursor(Qt.PointingHandCursor)
        list_btn.setStyleSheet("QPushButton { background: #3498db; color: white; font-weight: bold; border-radius: 6px; padding: 6px 12px; border: none; } QPushButton:hover { background: #2980b9; }")
        list_btn.clicked.connect(self._list_schemas)

        btn_row.addWidget(test_btn)
        btn_row.addWidget(list_btn)
        btn_row.addStretch()
        pg_lay.addLayout(btn_row)

        # Create database row
        create_row = QHBoxLayout()
        create_row.setSpacing(8)
        create_btn = QPushButton("🗄️ Yeni Veritabanı Oluştur")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet("QPushButton { background: #8e44ad; color: white; font-weight: bold; border-radius: 6px; padding: 6px 12px; border: none; } QPushButton:hover { background: #9b59b6; }")
        create_btn.clicked.connect(self._create_database)
        create_row.addWidget(create_btn)
        create_row.addStretch()
        pg_lay.addLayout(create_row)

        pg_lay.addStretch()

        self.stack.addWidget(pg_widget)
        layout.addWidget(self.stack, 1)

        # Bottom buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent; border: none;")
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setSpacing(10)

        iptal_btn = QPushButton("İptal")
        iptal_btn.setFixedSize(120, 38)
        iptal_btn.setCursor(Qt.PointingHandCursor)
        iptal_btn.setStyleSheet("QPushButton { background: #34495e; color: #bdc3c7; border: 1px solid #7f8c8d; border-radius: 8px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #c0392b; color: white; border: none; }")
        iptal_btn.clicked.connect(self.reject)

        kaydet_btn = QPushButton("Bağlan")
        kaydet_btn.setFixedSize(120, 38)
        kaydet_btn.setCursor(Qt.PointingHandCursor)
        kaydet_btn.setStyleSheet("QPushButton { background: #27ae60; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #2ecc71; }")
        kaydet_btn.clicked.connect(self._baglan)

        # Switch type button
        self.switch_sqlite_btn = QPushButton("💾 SQLite'a Geç")
        self.switch_sqlite_btn.setFixedSize(130, 38)
        self.switch_sqlite_btn.setCursor(Qt.PointingHandCursor)
        self.switch_sqlite_btn.setStyleSheet("QPushButton { background: #8e44ad; color: white; border: none; border-radius: 8px; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #9b59b6; }")
        self.switch_sqlite_btn.clicked.connect(self._sqlite_gec)

        btn_lay.addWidget(self.switch_sqlite_btn)
        btn_lay.addStretch()
        btn_lay.addWidget(iptal_btn)
        btn_lay.addWidget(kaydet_btn)
        layout.addWidget(btn_frame)

        apply_stylesheet = """
            QWidget { background: transparent; }
            QLabel { color: #bdc3c7; font-size: 12px; background: transparent; }
            QLineEdit, QSpinBox, QComboBox {
                border: 1px solid #4a6278; border-radius: 6px;
                padding: 6px 10px; background: #34495e; color: white; font-size: 12px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #34495e; color: white;
                selection-background-color: #3498db;
            }
            QComboBox::down-arrow { image: none; }
            QComboBox::down-arrow:on { top: 1px; }
        """
        pg_widget.setStyleSheet(apply_stylesheet)
        sqlite_widget.setStyleSheet("background: transparent;")
        make_frameless(self)

        self.type_radio_group.buttonToggled.connect(self._type_changed)
        self.stack.setCurrentIndex(0)

    def _type_changed(self, btn, checked):
        if checked:
            idx = 0 if btn == self.sqlite_radio else 1
            self.stack.setCurrentIndex(idx)

    def _load_config(self):
        config = load_config()
        if config.get("type") == "postgresql":
            self.pg_radio.setChecked(True)
            pg = config.get("postgresql", {})
            self.pg_host.setText(pg.get("host", "localhost"))
            self.pg_port.setValue(pg.get("port", 5432))
            self.pg_database.setText(pg.get("database", "pys"))
            self.pg_user.setText(pg.get("user", "postgres"))
            self.pg_password.setText(pg.get("password", ""))
            if pg.get("current_schema"):
                self.pg_schema.addItem(pg["current_schema"])
                self.pg_schema.setCurrentText(pg["current_schema"])
        else:
            self.sqlite_radio.setChecked(True)

    def _url_parse(self, url):
        url = url.strip()
        if not url.startswith("postgresql://"):
            return
        parsed = urlparse(url.replace("postgresql://", "postgresql+psycopg2://", 1))
        if parsed.hostname:
            self.pg_host.setText(parsed.hostname)
        if parsed.port:
            self.pg_port.setValue(parsed.port)
        if parsed.username:
            self.pg_user.setText(parsed.username)
        if parsed.password:
            self.pg_password.setText(parsed.password)
        path = parsed.path.lstrip("/")
        if path:
            parts = path.split("/")
            self.pg_database.setText(parts[0])
            if len(parts) > 1:
                self.pg_schema.setCurrentText(parts[1])

    def _test_connection(self):
        host = self.pg_host.text().strip()
        port = self.pg_port.value()
        database = self.pg_database.text().strip()
        user = self.pg_user.text().strip()
        password = self.pg_password.text()

        if not all([host, database, user]):
            ModernMesaj.uyari(self, "Lütfen sunucu, veritabanı ve kullanıcı alanlarını doldurun.")
            return

        ok, msg = test_postgresql_connection(host, port, database, user, password)
        if ok:
            ModernMesaj.basari(self, "✅ " + msg)
        else:
            ModernMesaj.hata(self, "❌ " + msg)

    def _list_schemas(self):
        host = self.pg_host.text().strip()
        port = self.pg_port.value()
        database = self.pg_database.text().strip()
        user = self.pg_user.text().strip()
        password = self.pg_password.text()

        if not all([host, database, user]):
            ModernMesaj.uyari(self, "Lütfen sunucu, veritabanı ve kullanıcı alanlarını doldurun.")
            return

        schemas = list_pg_schemas(host, port, database, user, password)
        self.pg_schema.clear()
        if schemas:
            self.pg_schema.addItems(schemas)
            ModernMesaj.basari(self, f"{len(schemas)} schema bulundu.")
        else:
            ModernMesaj.uyari(self, "Hiç schema bulunamadı. Firma adını manuel girin (otomatik oluşturulur).")

    def _create_database(self):
        host = self.pg_host.text().strip()
        port = self.pg_port.value()
        user = self.pg_user.text().strip()
        password = self.pg_password.text()
        new_db = self.pg_database.text().strip()

        if not all([host, user, new_db]):
            ModernMesaj.uyari(self, "Lütfen sunucu, kullanıcı ve veritabanı adını doldurun.")
            return

        ok, msg = create_pg_database(host, port, user, password, new_db)
        if ok:
            ModernMesaj.basari(self, msg)
        else:
            ModernMesaj.hata(self, msg)

    def _sqlite_gec(self):
        self.selected_type = "sqlite"
        self.selected_db = None
        self.accept()

    def _baglan(self):
        if self.sqlite_radio.isChecked():
            self.selected_type = "sqlite"
            self.selected_db = None
            self.accept()
            return

        url = self.pg_url.text().strip()
        if url:
            self.selected_type = "postgresql"
            self.selected_db = url
            self._saved_schema = "public"
            self.accept()
            return

        host = self.pg_host.text().strip()
        port = self.pg_port.value()
        database = self.pg_database.text().strip()
        user = self.pg_user.text().strip()
        password = self.pg_password.text()
        schema = self.pg_schema.currentText().strip()

        if not all([host, database, user, schema]):
            ModernMesaj.uyari(self, "Tüm alanları doldurun.")
            return

        ok, msg = test_postgresql_connection(host, port, database, user, password)
        if not ok:
            ModernMesaj.hata(self, f"Bağlantı başarısız:\n{msg}")
            return

        self.selected_type = "postgresql"
        self.selected_db = f"postgresql://{user}:{password}@{host}:{port}/{database}?schema={schema}&sslmode=require"
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'old_pos'):
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()
