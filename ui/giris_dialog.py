# ui/giris_dialog.py

import hashlib
import json
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QWidget, QApplication, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from models import Kullanici
from ui.utils import make_frameless, make_header


def _config_path():
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    d = os.path.join(appdata, "PYS")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "giris_hatirla.json")


def _kaydet_hatirla(username, sifre_hatirla):
    try:
        data = {}
        if username:
            data["username"] = username
        if sifre_hatirla:
            data["sifre_hatirla"] = True
        else:
            data.pop("sifre_hatirla", None)
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def _yukle_hatirla():
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class GirisDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.kullanici = None
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(380, 480)

        self._init_ui()
        self._hatirla_yukle()
        QTimer.singleShot(0, self._ortala)

    def _ortala(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; }
            QLineEdit { background:#1a2a38; border:1px solid #4a6278; border-radius:8px;
                        color:white; padding:10px 14px; font-size:13px; }
            QLineEdit:focus { border-color:#3498db; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        make_frameless(self, header_height=56)

        hdr, close_btn = make_header("🔐", "Kullanıcı Girişi", "#1a5276", "#2980b9", self)
        close_btn.clicked.connect(self.reject)
        outer_lay.addWidget(hdr)

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(32, 28, 32, 20)
        body_lay.setSpacing(16)

        ic = QLabel("👤")
        ic.setFixedSize(70, 70)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(52,152,219,0.15);border-radius:35px;font-size:32px;")
        body_lay.addWidget(ic, alignment=Qt.AlignCenter)

        body_lay.addSpacing(8)

        kullanici_lbl = QLabel("Kullanıcı Adı")
        kullanici_lbl.setStyleSheet("color:#bdc3c7;font-size:12px;font-weight:bold;")
        body_lay.addWidget(kullanici_lbl)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Kullanıcı adınızı girin...")
        self.username_input.setFixedHeight(42)
        self.username_input.returnPressed.connect(self._giris_yap)
        body_lay.addWidget(self.username_input)

        sifre_lbl = QLabel("Şifre")
        sifre_lbl.setStyleSheet("color:#bdc3c7;font-size:12px;font-weight:bold;")
        body_lay.addWidget(sifre_lbl)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Şifrenizi girin...")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(42)
        self.password_input.returnPressed.connect(self._giris_yap)
        body_lay.addWidget(self.password_input)

        hatirla_row = QHBoxLayout()
        self.kullanici_hatirla_cb = QCheckBox("Kullanıcı adını hatırla")
        self.kullanici_hatirla_cb.setStyleSheet("color:#bdc3c7;font-size:11px;background:transparent;")
        self.sifre_hatirla_cb = QCheckBox("Şifreyi hatırla")
        self.sifre_hatirla_cb.setStyleSheet("color:#bdc3c7;font-size:11px;background:transparent;")
        hatirla_row.addWidget(self.kullanici_hatirla_cb)
        hatirla_row.addWidget(self.sifre_hatirla_cb)
        hatirla_row.addStretch()
        body_lay.addLayout(hatirla_row)

        self.hata_lbl = QLabel("")
        self.hata_lbl.setStyleSheet("color:#e74c3c;font-size:11px;")
        self.hata_lbl.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(self.hata_lbl)

        body_lay.addSpacing(4)

        giris_btn = QPushButton("Giriş Yap")
        giris_btn.setFixedHeight(44)
        giris_btn.setCursor(Qt.PointingHandCursor)
        giris_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2980b9, stop:1 #3498db);
                color:white; font-weight:bold; font-size:14px;
                border:none; border-radius:8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2471a3, stop:1 #2e86c1);
            }
            QPushButton:pressed {
                background: #1a5276;
            }
        """)
        giris_btn.clicked.connect(self._giris_yap)
        body_lay.addWidget(giris_btn)

        body_lay.addStretch()
        outer_lay.addWidget(body, 1)

        self.username_input.setFocus()

    def _giris_yap(self):
        username = self.username_input.text().strip()
        sifre = self.password_input.text()

        if not username or not sifre:
            self.hata_lbl.setText("Kullanıcı adı ve şifre gereklidir.")
            return

        sifre_hash = hashlib.sha256(sifre.encode()).hexdigest()
        kullanici = self.session.query(Kullanici).filter(
            Kullanici.username == username,
            Kullanici.aktif == True
        ).first()

        if not kullanici or kullanici.password_hash != sifre_hash:
            self.hata_lbl.setText("Kullanıcı adı veya şifre hatalı.")
            self.password_input.clear()
            self.password_input.setFocus()
            return

        self.kullanici = kullanici
        _kaydet_hatirla(
            username if self.kullanici_hatirla_cb.isChecked() else "",
            self.sifre_hatirla_cb.isChecked()
        )
        self.accept()

    def _hatirla_yukle(self):
        data = _yukle_hatirla()
        if data.get("username"):
            self.username_input.setText(data["username"])
            self.kullanici_hatirla_cb.setChecked(True)
        if data.get("sifre_hatirla"):
            self.sifre_hatirla_cb.setChecked(True)
            self.password_input.setFocus()
        else:
            self.username_input.setFocus()
