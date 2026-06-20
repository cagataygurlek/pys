# ui/firma_secim_dialog.py

import os
import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QButtonGroup, QFileDialog, QFrame, QWidget, QScrollArea, QLineEdit, QApplication 
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QFont
from ui.utils import ModernMesaj, make_frameless
from database import get_db_folder, set_database, get_session, load_config
from sqlalchemy import create_engine
from models import Base
from ui.connection_dialog import ConnectionDialog
from ui.lisans_dialog import LisansDialog


class ModernInputDialog(QDialog):
    """Modern görünümlü tek girişli dialog (turuncu başlık, gri arka plan)"""
    def __init__(self, parent, baslik, mesaj, varsayilan="", parent_widget=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setFixedWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                border-radius: 12px;
                border: 1px solid #e67e22;
            }
            QLabel {
                color: #ecf0f1;
                background: transparent;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: 6px;
                color: white;
                font-size: 13px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #e67e22;
            }
        """)
        self.result_text = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header (turuncu)
        hdr = QFrame()
        hdr.setFixedHeight(60)
        hdr.setStyleSheet("background-color: #e67e22; border-top-left-radius: 12px; border-top-right-radius: 12px;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(20, 0, 20, 0)
        icon = QLabel("📝")
        icon.setStyleSheet("font-size: 20px; background: transparent; color: white;")
        title = QLabel(baslik)
        title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        hdr_lay.addWidget(icon)
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()
        lay.addWidget(hdr)

        # Body (gri)
        body = QFrame()
        body.setStyleSheet("background-color: #34495e;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(20, 20, 20, 10)
        body_lay.setSpacing(12)

        msg_lbl = QLabel(mesaj)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #ecf0f1;")
        body_lay.addWidget(msg_lbl)

        self.input_edit = QLineEdit()
        self.input_edit.setText(varsayilan)
        self.input_edit.selectAll()
        body_lay.addWidget(self.input_edit)

        # Butonlar
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background-color: #2c3e50; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; border-top: 1px solid #1a2a38;")
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setContentsMargins(20, 12, 20, 12)
        btn_lay.setSpacing(10)

        ok_btn = QPushButton("Tamam")
        ok_btn.setAutoFillBackground(True)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60 !important;
                color: white !important;
                font-weight: bold !important;
                border-radius: 6px !important;
                border: none !important;
                padding: 8px 20px !important;
                font-size: 12px !important;
            }
            QPushButton:hover {
                background-color: #2ecc71 !important;
            }
        """)
        ok_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("İptal")
        cancel_btn.setAutoFillBackground(True)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c !important;
                color: white !important;
                font-weight: bold !important;
                border-radius: 6px !important;
                border: none !important;
                padding: 8px 20px !important;
                font-size: 12px !important;
            }
            QPushButton:hover {
                background-color: #c0392b !important;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        btn_lay.addStretch()
        btn_lay.addWidget(ok_btn)
        btn_lay.addWidget(cancel_btn)

        body_lay.addWidget(btn_frame)
        lay.addWidget(body)
        make_frameless(self)

    def get_text(self):
        return self.input_edit.text().strip()


class FirmaKartBtn(QPushButton):
    def __init__(self, ikon, firma_adi, aciklama, db_path=None, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(160, 90)
        self.setCursor(Qt.PointingHandCursor)
        self.firma_adi = firma_adi
        self.aciklama = aciklama
        self.ikon = ikon
        self.db_path = db_path  # tam yol veya sadece dosya adı
        self._update_style(False)

    def _update_style(self, checked):
        if checked:
            self.setStyleSheet("QPushButton { background-color: #1a3a4a; border: 2px solid #3498db; border-radius: 12px; color: white; }")
        else:
            self.setStyleSheet("QPushButton { background-color: #34495e; border: 2px solid transparent; border-radius: 12px; color: white; } QPushButton:hover { background-color: #3d566e; border: 2px solid #4a6278; }")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setFont(QFont("Segoe UI", 16))
        painter.setPen(QColor("white"))
        painter.drawText(self.rect().adjusted(0, -20, 0, 0), Qt.AlignCenter, self.ikon)

        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(self.rect().adjusted(0, 30, 0, 0), Qt.AlignCenter, self.firma_adi)

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#bdc3c7"))
        painter.drawText(self.rect().adjusted(0, 60, 0, 0), Qt.AlignCenter, self.aciklama)


class FirmaSecimDialog(QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(700, 680)
        self.selected_db = None
        self.db_folder = get_db_folder()
        self.init_ui()

    def _ortala(self):
        if self.parent():
            pg = self.parent().frameGeometry()
            x = pg.x() + (pg.width() - self.width()) // 2
            y = pg.y() + (pg.height() - self.height()) // 2 - 90
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.x() + (screen.width() - self.width()) // 2
            y = screen.y() + (screen.height() - self.height()) // 2 - 90
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self._ortala)

    def _cikis(self):
        if self.parent():
            self.reject()
        else:
            import sys; sys.exit()

    def init_ui(self):
        self.bg_frame = QFrame(self)
        self.bg_frame.setGeometry(0, 0, 700, 680)
        self.bg_frame.setStyleSheet("""
            QFrame { 
                background-color: #2c3e50; 
                border-radius: 20px; 
                border: 2px solid #34495e; 
            }
        """)

        lay = QVBoxLayout(self.bg_frame)
        lay.setContentsMargins(30, 20, 30, 30)
        lay.setSpacing(10)

        # Kapatma butonu
        exit_top_lay = QHBoxLayout()
        exit_top_lay.addStretch()
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton { 
                background: transparent; color: #7f8c8d; font-size: 18px; border: none; 
            }
            QPushButton:hover { color: #e74c3c; }
        """)
        self.close_btn.clicked.connect(self.reject)
        exit_top_lay.addWidget(self.close_btn)
        lay.addLayout(exit_top_lay)
        # Pencereyi ekranın ortasına taşı (garantili yöntem)
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        # Logo ve Başlık
        self.logo_label = QLabel("🚀")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet("font-size: 50px; border: none; color: #3498db; background: transparent;")
        lay.addWidget(self.logo_label)

        title = QLabel("Personel Yönetim Sistemi")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white; border: none; background: transparent;")
        lay.addWidget(title)

        subtitle = QLabel("Lütfen çalışmak istediğiniz firmayı seçin")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 13px; color: #bdc3c7; border: none; background: transparent; margin-bottom: 10px;")
        lay.addWidget(subtitle)

        # Kaydırılabilir firma kartları alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setMinimumHeight(320)

        cards_widget = QWidget()
        cards_widget.setStyleSheet("background: transparent;")
        cards_layout = QGridLayout(cards_widget)
        cards_layout.setSpacing(20)
        cards_layout.setAlignment(Qt.AlignCenter)
        cards_layout.setContentsMargins(20, 20, 20, 20)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.btn_group.buttonToggled.connect(lambda btn, checked: btn._update_style(checked))

        # DATA klasöründeki tüm .db dosyalarını bul
        db_files = []
        if os.path.exists(self.db_folder):
            db_files = [f for f in os.listdir(self.db_folder) if f.endswith('.db') and os.path.isfile(os.path.join(self.db_folder, f))]
        cols = 2  # 2 sütunlu grid

        # Buton listesi
        all_buttons = []

        # Veritabanı butonları
        for db_file in db_files:
            firma_adi = os.path.splitext(db_file)[0].capitalize()
            aciklama = "Veritabanı"
            ikon = "🏢"
            btn = FirmaKartBtn(ikon, firma_adi, aciklama, db_path=db_file)  # sadece dosya adı
            self.btn_group.addButton(btn)
            all_buttons.append(btn)

        # Diğer butonu
        other_btn = FirmaKartBtn("📁", "Diğer...", "Dosya Seç", db_path=None)
        self.btn_group.addButton(other_btn)
        all_buttons.append(other_btn)

        # Yeni Veritabanı Oluştur butonu
        new_btn = FirmaKartBtn("➕", "Yeni", "Veritabanı Oluştur", db_path=None)
        new_btn.setCheckable(False)
        new_btn.clicked.connect(self.yeni_veritabani_olustur)
        all_buttons.append(new_btn)

        # PostgreSQL bağlantı yönetimi butonu
        pg_btn = FirmaKartBtn("🐘", "PG Bağlantı", "Ağ Veritabanı", db_path=None)
        pg_btn.setCheckable(False)
        pg_btn.clicked.connect(self._pg_baglanti_ac)
        all_buttons.append(pg_btn)

        # Butonları grid'e yerleştir
        for idx, btn in enumerate(all_buttons):
            row = idx // cols
            col = idx % cols
            cards_layout.addWidget(btn, row, col)

        scroll.setWidget(cards_widget)
        lay.addWidget(scroll)
        lay.addStretch()

        # Alt butonlar
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent; border: none;")
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setSpacing(15)

        cikis_btn = QPushButton("Sistemden Çık")
        cikis_btn.setFixedSize(140, 40)
        cikis_btn.setCursor(Qt.PointingHandCursor)
        cikis_btn.setStyleSheet("""
            QPushButton { 
                background-color: #34495e; color: #bdc3c7; border: 1px solid #7f8c8d; 
                border-radius: 8px; font-size: 13px; font-weight: bold; 
            } 
            QPushButton:hover { background-color: #c0392b; color: white; border: none; }
        """)
        cikis_btn.clicked.connect(self._cikis)

        ac_btn = QPushButton("Giriş Yap")
        ac_btn.setFixedSize(140, 40)
        ac_btn.setCursor(Qt.PointingHandCursor)
        ac_btn.setStyleSheet("""
            QPushButton { 
                background-color: #27ae60; color: white; border: none; 
                border-radius: 8px; font-size: 14px; font-weight: bold; 
            } 
            QPushButton:hover { background-color: #2ecc71; }
        """)
        ac_btn.clicked.connect(self._ac)

        btn_lay.addStretch()
        btn_lay.addWidget(cikis_btn)
        btn_lay.addWidget(ac_btn)
        btn_lay.addStretch()

        lay.addWidget(btn_frame)

        # Lisans butonu
        lisans_btn = QPushButton("🔑 Lisans Girişi")
        lisans_btn.setFixedSize(160, 36)
        lisans_btn.setCursor(Qt.PointingHandCursor)
        lisans_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a3c5e; color: #3498db; border: 1px solid #2980b9;
                border-radius: 8px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; color: white; }
        """)
        lisans_btn.clicked.connect(self._lisans_ac)
        lisans_lay = QHBoxLayout()
        lisans_lay.addStretch()
        lisans_lay.addWidget(lisans_btn)
        lisans_lay.addStretch()
        lay.addLayout(lisans_lay)

        # Uyarı mesajı: lisans butonunun altında
        if not db_files:
            warning = QLabel("⚠️ Hiç veritabanı dosyası bulunamadı!\n'Yeni' butonu ile oluşturun.")
            warning.setStyleSheet("color: #f39c12; font-size: 11px; background: transparent; padding: 4px;")
            warning.setAlignment(Qt.AlignCenter)
            warning.setWordWrap(True)
            lay.addWidget(warning)

    def yeni_veritabani_olustur(self):
        dialog = ModernInputDialog(self, "Yeni Veritabanı", "Veritabanı adını girin (uzantısız):", "yeni_firma")
        if dialog.exec_() == QDialog.Accepted:
            isim = dialog.get_text()
            if isim:
                db_ad = isim.replace(" ", "_") + ".db"
                db_path = os.path.join(self.db_folder, db_ad)
                if os.path.exists(db_path):
                    ModernMesaj.uyari(self, f"'{db_ad}' zaten mevcut. Lütfen farklı bir isim girin.")
                    return
                try:
                    # Veritabanını ve tabloları oluştur
                    engine = create_engine(f'sqlite:///{db_path}')
                    Base.metadata.create_all(engine)
                    engine.dispose()
                    ModernMesaj.basari(self, f"'{db_ad}' veritabanı başarıyla oluşturuldu.\nŞimdi bu firmayı seçebilirsiniz.")
                    self.refresh_dialog()
                except Exception as e:
                    ModernMesaj.hata(self, f"Veritabanı oluşturulamadı:\n{str(e)}")

    def refresh_dialog(self):
        self.close()
        new_dialog = FirmaSecimDialog(self.parent())
        new_dialog.exec_()
        if new_dialog.selected_db:
            self.selected_db = new_dialog.selected_db
            self.accept()
        else:
            self.reject()

    def _ac(self):
        checked = self.btn_group.checkedButton()
        if not checked:
            ModernMesaj.uyari(self, "Lütfen bir firma seçin.")
            return

        if checked.firma_adi == "Diğer...":
            path, _ = QFileDialog.getOpenFileName(self, "Veritabanı Seç", self.db_folder, "Veritabanı (*.db)")
            if path:
                self.selected_db = path
                self.accept()
            return
        elif checked.firma_adi == "Yeni":
            self.yeni_veritabani_olustur()
            return
        elif checked.firma_adi == "PG Bağlantı":
            self._pg_baglanti_ac()
            return
        else:
            # Normal veritabanı butonları - db_path sadece dosya adı
            db_full_path = os.path.join(self.db_folder, checked.db_path)
            if os.path.exists(db_full_path):
                self.selected_db = db_full_path
                self.accept()
            else:
                ModernMesaj.hata(self, f"Veritabanı dosyası bulunamadı:\n{db_full_path}")

    def _pg_baglanti_ac(self):
        dialog = ConnectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.selected_type == "postgresql" and dialog.selected_db:
                self.selected_db = dialog.selected_db
                self.accept()
            else:
                ModernMesaj.basari(self, "SQLite moduna geçildi. Lütfen bir firma seçin.")
                self.refresh_dialog()

    def _lisans_ac(self):
        dialog = LisansDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            ModernMesaj.basari(self, "Lisans başarıyla doğrulandı.")
            self.refresh_dialog()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'old_pos'):
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()