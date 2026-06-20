# ui/lisans_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QWidget, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from ui.utils import make_frameless, make_header
from license_checker import check_license, set_license_key, get_saved_key


class LisansDialog(QDialog):
    def __init__(self, parent=None, hata_mesaji=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(480, 620)
        self.lisans_ok = False
        self.bitis_tarihi = None
        self._hata_mesaji = hata_mesaji
        self._kontrol_ediliyor = False

        self._init_ui()
        QTimer.singleShot(0, self._ortala)
        if not hata_mesaji:
            QTimer.singleShot(100, self._otomatik_kontrol)

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

        if self._hata_mesaji:
            hdr, close_btn = make_header("⚠️", "Lisans Süresi Doldu", "#7b241c", "#c0392b", self)
        else:
            hdr, close_btn = make_header("🔑", "Lisans Doğrulama", "#1a3c5e", "#2980b9", self)
        close_btn.clicked.connect(self.reject)
        outer_lay.addWidget(hdr)

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(32, 20, 32, 20)
        body_lay.setSpacing(10)

        if self._hata_mesaji:
            self._expired_ui(body_lay)
        else:
            self._normal_ui(body_lay)

        body_lay.addStretch()
        outer_lay.addWidget(body, 1)

        saved = get_saved_key()
        if saved and not self._hata_mesaji:
            self.key_input.setText(saved)

    def _expired_ui(self, body_lay):
        ic = QLabel("⚠️")
        ic.setFixedSize(72, 72)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(231,76,60,0.15);border-radius:36px;font-size:32px;")
        body_lay.addWidget(ic, alignment=Qt.AlignCenter)

        body_lay.addSpacing(4)

        baslik = QLabel("Lisansınızın Süresi Dolmuştur")
        baslik.setStyleSheet("color:#e74c3c;font-size:16px;font-weight:bold;")
        baslik.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(baslik)

        hata_box = QLabel(self._hata_mesaji)
        hata_box.setWordWrap(True)
        hata_box.setStyleSheet(
            "color:#e74c3c;font-size:12px;background:rgba(231,76,60,0.10);"
            "border:1px solid rgba(231,76,60,0.3);border-radius:8px;padding:10px 14px;"
        )
        hata_box.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(hata_box)

        body_lay.addSpacing(8)

        info_text = (
            "Lisansınızı yenilemek için yeni bir lisans anahtarı girin\n"
            "veya yöneticinizle iletişime geçin."
        )
        info = QLabel(info_text)
        info.setWordWrap(True)
        info.setStyleSheet("color:#bdc3c7;font-size:12px;")
        info.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(info)

        body_lay.addSpacing(12)

        key_lbl = QLabel("Yeni Lisans Anahtarı")
        key_lbl.setStyleSheet("color:#bdc3c7;font-size:12px;font-weight:bold;")
        body_lay.addWidget(key_lbl)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_input.setFixedHeight(42)
        self.key_input.returnPressed.connect(self._kontrol_et)
        body_lay.addWidget(self.key_input)

        body_lay.addSpacing(4)

        self.durum_lbl = QLabel("")
        self.durum_lbl.setWordWrap(True)
        self.durum_lbl.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(self.durum_lbl)

        body_lay.addSpacing(6)

        btn_row = QHBoxLayout()
        self.kontrol_btn = QPushButton("Yenile ve Doğrula")
        self.kontrol_btn.setFixedHeight(44)
        self.kontrol_btn.setCursor(Qt.PointingHandCursor)
        self.kontrol_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #c0392b, stop:1 #e74c3c);
                color:white; font-weight:bold; font-size:14px;
                border:none; border-radius:8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #a93226, stop:1 #c0392b);
            }
            QPushButton:pressed { background: #7b241c; }
        """)
        self.kontrol_btn.clicked.connect(self._kontrol_et)
        btn_row.addWidget(self.kontrol_btn)

        self.atla_btn = QPushButton("Çıkış")
        self.atla_btn.setFixedHeight(44)
        self.atla_btn.setCursor(Qt.PointingHandCursor)
        self.atla_btn.setStyleSheet("""
            QPushButton {
                background: #34495e; color:#bdc3c7; font-size:13px;
                border:1px solid #4a6278; border-radius:8px;
            }
            QPushButton:hover { background:#3d566e; color:white; }
        """)
        self.atla_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.atla_btn)

        body_lay.addLayout(btn_row)

        body_lay.addSpacing(12)

        iletisim = QLabel("📞 Yönetici ile iletişime geçin: cagataygurlek@gmail.com")
        iletisim.setWordWrap(True)
        iletisim.setStyleSheet("color:#7f8c8d;font-size:10px;")
        iletisim.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(iletisim)

    def _normal_ui(self, body_lay):
        ic = QLabel("🔑")
        ic.setFixedSize(64, 64)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(52,152,219,0.15);border-radius:32px;font-size:28px;")
        body_lay.addWidget(ic, alignment=Qt.AlignCenter)

        aciklama = QLabel("Lisans anahtarınızı girin")
        aciklama.setStyleSheet("color:#bdc3c7;font-size:12px;")
        aciklama.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(aciklama)

        body_lay.addSpacing(4)

        key_lbl = QLabel("Lisans Anahtarı")
        key_lbl.setStyleSheet("color:#bdc3c7;font-size:12px;font-weight:bold;")
        body_lay.addWidget(key_lbl)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_input.setFixedHeight(42)
        self.key_input.returnPressed.connect(self._kontrol_et)
        body_lay.addWidget(self.key_input)

        body_lay.addSpacing(4)

        self.durum_lbl = QLabel("")
        self.durum_lbl.setWordWrap(True)
        self.durum_lbl.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(self.durum_lbl)

        body_lay.addSpacing(4)

        btn_row = QHBoxLayout()
        self.kontrol_btn = QPushButton("Doğrula")
        self.kontrol_btn.setFixedHeight(44)
        self.kontrol_btn.setCursor(Qt.PointingHandCursor)
        self.kontrol_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2980b9, stop:1 #3498db);
                color:white; font-weight:bold; font-size:14px;
                border:none; border-radius:8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2471a3, stop:1 #2e86c1);
            }
            QPushButton:pressed { background: #1a5276; }
        """)
        self.kontrol_btn.clicked.connect(self._kontrol_et)
        btn_row.addWidget(self.kontrol_btn)

        self.atla_btn = QPushButton("Vazgeç")
        self.atla_btn.setFixedHeight(44)
        self.atla_btn.setCursor(Qt.PointingHandCursor)
        self.atla_btn.setStyleSheet("""
            QPushButton {
                background: #34495e; color:#bdc3c7; font-size:13px;
                border:1px solid #4a6278; border-radius:8px;
            }
            QPushButton:hover { background:#3d566e; color:white; }
        """)
        self.atla_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.atla_btn)

        body_lay.addLayout(btn_row)

        body_lay.addSpacing(8)

        self.info_lbl = QLabel("")
        self.info_lbl.setWordWrap(True)
        self.info_lbl.setStyleSheet("color:#7f8c8d;font-size:10px;")
        self.info_lbl.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(self.info_lbl)

    def _otomatik_kontrol(self):
        if self._kontrol_ediliyor:
            return
        key = self.key_input.text().strip()
        if key:
            self._kontrol_et()

    def _kontrol_et(self):
        if self._kontrol_ediliyor:
            return

        key = self.key_input.text().strip()
        if not key:
            self._set_durum("Lisans anahtarı boş olamaz.", False)
            return

        self._kontrol_ediliyor = True
        self.kontrol_btn.setEnabled(False)
        self.kontrol_btn.setText("Kontrol ediliyor...")
        self.durum_lbl.setText("⏳ Bağlanılıyor...")
        self.durum_lbl.setStyleSheet(
            "color:#f39c12;font-size:12px;background:rgba(243,156,18,0.12);"
            "border-radius:8px;padding:8px 12px;"
        )

        try:
            gecerli, mesaj, bitis = check_license(key)
        except Exception as e:
            gecerli, mesaj, bitis = False, f"Hata: {e}", None

        self.kontrol_btn.setEnabled(True)
        self.kontrol_btn.setText("Yenile ve Doğrula" if self._hata_mesaji else "Doğrula")
        self._kontrol_ediliyor = False

        if gecerli:
            self.lisans_ok = True
            self.bitis_tarihi = bitis
            self._set_durum(mesaj, True)
            QTimer.singleShot(1200, self.accept)
        else:
            self._set_durum(mesaj, False)

    def _set_durum(self, text, basarili):
        if basarili:
            renk = "#2ecc71"
            bg = "rgba(46,204,113,0.12)"
            icon = "✓ "
        else:
            renk = "#e74c3c"
            bg = "rgba(231,76,60,0.12)"
            icon = "✕ "
        self.durum_lbl.setText(icon + text)
        self.durum_lbl.setStyleSheet(
            f"color:{renk};font-size:12px;background:{bg};"
            f"border-radius:8px;padding:8px 12px;"
        )
