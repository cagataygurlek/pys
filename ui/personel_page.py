# ui/personel_page.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QComboBox, QLabel, QPushButton, QFrame,
    QHeaderView, QMessageBox, QLineEdit, QDialog, QFormLayout,
    QDateEdit, QGroupBox, QFileDialog, QTextEdit, QCalendarWidget,
    QDialogButtonBox, QApplication, QGridLayout, QScrollArea, QCheckBox,
    QScrollArea as QSA, QMenu
)
from PyQt5.QtCore import Qt, QDate, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPalette, QLinearGradient, QBrush

import pandas as pd
import datetime
import os
import re
import json
from database import get_session
from models import Personel, Sube, Gorev, Haciz, YillikIzin, Izin, Bordro, MaasOdeme, HacizOdeme, KullaniciSube
from sqlalchemy import func
from ui.utils import ModernMesaj, TarihAlani, ModernTarihSecici, get_config_path, make_frameless, ButtonDelegate
from ui.ozluk_evraklari_dialog import OzlukEvraklariDialog
from ui.personel_detay_islemleri import (
    AvansKasaSigaraDialog, SenelikIzinDialog,
    MaasOdemeDialog, HacizOdemeDialog, BordroHesaplaDialog
)
from .izin_gecmisi_dialog import IzinGecmisiDialog   # YENİ

# ==================== EXCEL TARZI ÇOKTAN SEÇMELİ FİLTRE ====================
class MultiSelectFilter(QPushButton):
    """Excel tarzı çoktan seçmeli filtre butonu"""
    selectionChanged = pyqtSignal()

    def __init__(self, placeholder, parent=None):
        super().__init__(parent)
        self.placeholder = placeholder
        self._selected = set()
        self._options = []
        self._popup = None
        self._checkboxes = []
        self._all_chk = None
        self._update_text()
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: 5px;
                color: #bdc3c7;
                padding: 4px 8px;
                font-size: 12px;
                text-align: left;
            }
            QPushButton:hover { border-color: #3498db; color: white; }
            QPushButton[active="true"] { border-color: #3498db; color: #3498db; }
        """)
        self.clicked.connect(self._show_popup)

    def _update_text(self):
        has_filter = bool(self._selected)
        self.setProperty("active", "true" if has_filter else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if not self._selected:
            self.setText(f"▾  {self.placeholder}")
        elif len(self._selected) == 1:
            val = next(iter(self._selected))
            short = val if len(val) <= 12 else val[:12] + "…"
            self.setText(f"▾  {short}")
        else:
            self.setText(f"▾  {len(self._selected)} seçili")

    def set_options(self, options):
        self._options = sorted(set(str(o) for o in options if o and str(o).strip()))

    def set_selected(self, items):
        self._selected = set(str(i) for i in items if str(i) in self._options)
        self._update_text()
        self.selectionChanged.emit()

    def clear_selection(self):
        self._selected = set()
        self._update_text()
        self.selectionChanged.emit()

    def get_selected(self):
        return self._selected

    def _show_popup(self):
        if self._popup and self._popup.isVisible():
            self._popup.close()
            self._popup = None
            return

        self._popup = QFrame(self.window(), Qt.Popup | Qt.FramelessWindowHint)
        self._popup.setStyleSheet("""
            QFrame {
                background: #2c3e50;
                border: 1px solid #3498db;
                border-radius: 8px;
            }
            QCheckBox {
                color: #ecf0f1;
                padding: 3px 6px;
                font-size: 12px;
                background: transparent;
                spacing: 8px;
            }
            QCheckBox:hover { color: #3498db; }
            QCheckBox::indicator {
                width: 15px; height: 15px;
                border: 2px solid #4a6278;
                border-radius: 3px;
                background: #34495e;
            }
            QCheckBox::indicator:checked {
                background: #3498db;
                border-color: #3498db;
            }
            QPushButton#applyBtn {
                background: #3498db; color: white;
                border: none; border-radius: 5px;
                padding: 5px 12px; font-size: 11px; font-weight: bold;
            }
            QPushButton#applyBtn:hover { background: #2980b9; }
            QPushButton#clearBtn {
                background: transparent; color: #7f8c8d;
                border: 1px solid #4a6278; border-radius: 5px;
                padding: 5px 12px; font-size: 11px;
            }
            QPushButton#clearBtn:hover { color: white; border-color: #e74c3c; }
        """)

        outer = QVBoxLayout(self._popup)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(4)

        self._all_chk = QCheckBox("(Tümünü Seç)")
        self._all_chk.setChecked(len(self._selected) == len(self._options))
        outer.addWidget(self._all_chk)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #4a6278; margin: 2px 0;")
        sep.setFixedHeight(1)
        outer.addWidget(sep)

        scroll = QSA()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QSA.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setMaximumHeight(200)

        inner_w = QWidget()
        inner_w.setStyleSheet("background: transparent;")
        inner_lay = QVBoxLayout(inner_w)
        inner_lay.setContentsMargins(0, 0, 0, 0)
        inner_lay.setSpacing(2)

        self._checkboxes = []
        for opt in self._options:
            chk = QCheckBox(opt)
            chk.setChecked(opt in self._selected)
            inner_lay.addWidget(chk)
            self._checkboxes.append((opt, chk))
            chk.stateChanged.connect(self._on_item_changed)

        scroll.setWidget(inner_w)
        outer.addWidget(scroll)

        self._all_chk.stateChanged.connect(self._on_all_changed)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        clear_btn = QPushButton("Temizle")
        clear_btn.setObjectName("clearBtn")
        clear_btn.clicked.connect(self._clear)
        apply_btn = QPushButton("Uygula")
        apply_btn.setObjectName("applyBtn")
        apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(apply_btn)
        outer.addLayout(btn_row)

        pos = self.mapToGlobal(self.rect().bottomLeft())
        self._popup.adjustSize()
        self._popup.move(pos)
        min_w = max(self.width(), 180)
        self._popup.setMinimumWidth(min_w)
        self._popup.show()

    def _on_all_changed(self, state):
        for _, chk in self._checkboxes:
            chk.blockSignals(True)
            chk.setChecked(state == Qt.Checked)
            chk.blockSignals(False)

    def _on_item_changed(self):
        all_checked = all(chk.isChecked() for _, chk in self._checkboxes)
        if self._all_chk:
            self._all_chk.blockSignals(True)
            self._all_chk.setChecked(all_checked)
            self._all_chk.blockSignals(False)

    def _clear(self):
        for _, chk in self._checkboxes:
            chk.blockSignals(True)
            chk.setChecked(False)
            chk.blockSignals(False)
        if self._all_chk:
            self._all_chk.blockSignals(True)
            self._all_chk.setChecked(False)
            self._all_chk.blockSignals(False)
        self._apply()

    def _apply(self):
        self._selected = {opt for opt, chk in self._checkboxes if chk.isChecked()}
        self._update_text()
        if self._popup:
            self._popup.close()
            self._popup = None
        self.selectionChanged.emit()


# ==================== PERSONEL DÜZENLEME DIALOGU ====================
class PersonelDialog(QDialog):
    def __init__(self, session, personel=None, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.personel = personel
        self.selected_personel_id = None
        eylem = "Yeni Personel" if not personel else f"Düzenle — {personel.ad_soyad}"
        self.setWindowTitle(eylem)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(720)
        self.setStyleSheet("""
            QFrame#card {
                background-color: #34495e;
                border: 1px solid #4a6278;
                border-radius: 12px;
            }
            QLabel#card_title {
                font-size: 13px;
                font-weight: bold;
                color: #ecf0f1;
                background: transparent;
                padding: 0 8px;
            }
            QLineEdit, QComboBox, QTextEdit {
                border: 1px solid #3498db;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #2c3e50;
                color: #ffffff;
                font-size: 13px;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border-color: #e74c3c;
                background-color: #1a2a38;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #ecf0f1;
                color: #ecf0f1;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QLabel { color: #bdc3c7; background: transparent; font-size: 11px; }
            QPushButton#tarihButonu {
                background: #34495e; border: 1px solid #4a6278;
                color: #ecf0f1; border-radius: 6px; padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton#tarihButonu:hover { background: #3d566e; }
        """)
        self._drag_pos = None
        self.init_ui()
        make_frameless(self, header_height=70)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.pos().y() <= 70:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; }
            QLineEdit, QComboBox, QTextEdit {
                border: 1px solid #3498db;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #2c3e50;
                color: #ffffff;
                font-size: 13px;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border-color: #e74c3c;
                background-color: #1a2a38;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #34495e;
                color: #ecf0f1;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QPushButton#tarihButonu {
                background: #34495e; border: 1px solid #4a6278;
                color: #ecf0f1; border-radius: 6px; padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton#tarihButonu:hover { background: #3d566e; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(70)
        hdr.setStyleSheet("QFrame { background-color: #1a3a4a; border-top-left-radius: 16px; border-top-right-radius: 16px; }")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(20, 0, 20, 0)
        hdr_lay.setSpacing(12)
        ic = QLabel("👤")
        ic.setFixedSize(44, 44)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background-color: #2980b9; border-radius: 22px; font-size: 20px;")
        hdr_lay.addWidget(ic)
        tl = QLabel("Yeni Personel" if not self.personel else f"Düzenle — {self.personel.ad_soyad}")
        tl.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        hdr_lay.addWidget(tl)
        hdr_lay.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.08);color:#ecf0f1;font-size:16px;font-weight:bold;border:none;border-radius:13px;} QPushButton:hover{background:rgba(231,76,60,0.7);color:white;}")
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 14, 16, 10)
        outer_lay.addLayout(layout)

        # Kişisel Bilgiler Kartı
        kisi_card = QFrame()
        kisi_card.setObjectName("card")
        kisi_layout = QVBoxLayout(kisi_card)
        kisi_layout.setContentsMargins(16, 12, 16, 16)
        kisi_layout.setSpacing(10)

        kisi_title_layout = QHBoxLayout()
        kisi_title_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("👤")
        icon_lbl.setStyleSheet("font-size: 16px; color: #3498db; background: transparent;")
        kisi_title_layout.addWidget(icon_lbl)
        title_lbl = QLabel("Kişisel Bilgiler")
        title_lbl.setObjectName("card_title")
        kisi_title_layout.addWidget(title_lbl)
        kisi_title_layout.addStretch()
        kisi_layout.addLayout(kisi_title_layout)

        kisi_content = QWidget()
        kisi_content.setStyleSheet("background: transparent;")
        kisi_grid = QGridLayout(kisi_content)
        kisi_grid.setSpacing(10)
        kisi_grid.setContentsMargins(0, 0, 0, 0)

        kisi_grid.addWidget(QLabel("Ad Soyad:"), 0, 0)
        self.ad_input = QLineEdit()
        self.ad_input.setPlaceholderText("Ad Soyad")
        kisi_grid.addWidget(self.ad_input, 0, 1, 1, 2)

        kisi_grid.addWidget(QLabel("TC No:"), 0, 3)
        self.tc_input = QLineEdit()
        self.tc_input.setPlaceholderText("11 Haneli TC No")
        self.tc_input.setMaxLength(11)
        kisi_grid.addWidget(self.tc_input, 0, 4)

        kisi_grid.addWidget(QLabel("Baba Adı:"), 1, 0)
        self.baba_adi_input = QLineEdit()
        self.baba_adi_input.setPlaceholderText("Baba Adı")
        kisi_grid.addWidget(self.baba_adi_input, 1, 1)

        kisi_grid.addWidget(QLabel("Doğum Yeri:"), 1, 2)
        self.dogum_yeri_input = QLineEdit()
        self.dogum_yeri_input.setPlaceholderText("Doğum Yeri")
        kisi_grid.addWidget(self.dogum_yeri_input, 1, 3)

        kisi_grid.addWidget(QLabel("Doğum Tarihi:"), 1, 4)
        self.dogum_tarihi = TarihAlani()
        kisi_grid.addWidget(self.dogum_tarihi, 1, 5)

        kisi_grid.addWidget(QLabel("Telefon:"), 2, 0)
        self.telefon_input = QLineEdit()
        self.telefon_input.setPlaceholderText("Telefon")
        kisi_grid.addWidget(self.telefon_input, 2, 1)

        kisi_grid.addWidget(QLabel("IBAN:"), 2, 2)
        self.iban_input = QLineEdit()
        self.iban_input.setPlaceholderText("TR________")
        kisi_grid.addWidget(self.iban_input, 2, 3, 1, 3)

        kisi_layout.addWidget(kisi_content)
        layout.addWidget(kisi_card)

        # Çalışma Bilgileri Kartı
        calisma_card = QFrame()
        calisma_card.setObjectName("card")
        calisma_layout = QVBoxLayout(calisma_card)
        calisma_layout.setContentsMargins(16, 12, 16, 16)
        calisma_layout.setSpacing(10)

        calisma_title_layout = QHBoxLayout()
        calisma_title_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl2 = QLabel("💼")
        icon_lbl2.setStyleSheet("font-size: 16px; color: #e67e22; background: transparent;")
        calisma_title_layout.addWidget(icon_lbl2)
        title_lbl2 = QLabel("Çalışma Bilgileri")
        title_lbl2.setObjectName("card_title")
        calisma_title_layout.addWidget(title_lbl2)
        calisma_title_layout.addStretch()
        calisma_layout.addLayout(calisma_title_layout)

        calisma_content = QWidget()
        calisma_content.setStyleSheet("background: transparent;")
        calisma_grid = QGridLayout(calisma_content)
        calisma_grid.setSpacing(10)
        calisma_grid.setContentsMargins(0, 0, 0, 0)

        calisma_grid.addWidget(QLabel("Sicil No:"), 0, 0)
        self.sicil_input = QLineEdit()
        self.sicil_input.setPlaceholderText("Sicil No")
        calisma_grid.addWidget(self.sicil_input, 0, 1)
        calisma_grid.addWidget(QLabel("Maaş:"), 0, 2)
        self.maas_input = QLineEdit()
        self.maas_input.setPlaceholderText("Ör: 28075,50")
        calisma_grid.addWidget(self.maas_input, 0, 3)

        calisma_grid.addWidget(QLabel("Şube:"), 1, 0)
        self.sube_cb = QComboBox()
        for s in self.session.query(Sube).all():
            self.sube_cb.addItem(s.ad, s.id)
        calisma_grid.addWidget(self.sube_cb, 1, 1)
        calisma_grid.addWidget(QLabel("Görev:"), 1, 2)
        self.gorev_cb = QComboBox()
        for g in self.session.query(Gorev).all():
            self.gorev_cb.addItem(g.ad, g.id)
        calisma_grid.addWidget(self.gorev_cb, 1, 3)

        calisma_grid.addWidget(QLabel("Giriş Tarihi:"), 2, 0)
        giris_layout = QHBoxLayout()
        self.giris_label = QLabel()
        self.giris_label.setFixedHeight(36)
        self.giris_label.setStyleSheet("border: 1px solid #4a6278; border-radius: 8px; padding: 8px 12px; color: white; background: #2c3e50; font-size: 13px;")
        self.giris_btn = QPushButton("📅 Seç")
        self.giris_btn.setObjectName("tarihButonu")
        self.giris_btn.setFixedSize(70, 36)
        self.giris_btn.setCursor(Qt.PointingHandCursor)
        self.giris_btn.clicked.connect(self.giris_sec)
        giris_layout.addWidget(self.giris_label)
        giris_layout.addWidget(self.giris_btn)
        calisma_grid.addLayout(giris_layout, 2, 1, 1, 3)

        calisma_grid.addWidget(QLabel("Ayrılma Tarihi:"), 3, 0)
        ayrilma_layout = QHBoxLayout()
        self.ayrilma_label = QLabel()
        self.ayrilma_label.setFixedHeight(36)
        self.ayrilma_label.setStyleSheet("border: 1px solid #4a6278; border-radius: 8px; padding: 8px 12px; color: white; background: #2c3e50; font-size: 13px;")
        self.ayrilma_btn = QPushButton("📅 Seç")
        self.ayrilma_btn.setObjectName("tarihButonu")
        self.ayrilma_btn.setFixedSize(70, 36)
        self.ayrilma_btn.setCursor(Qt.PointingHandCursor)
        self.ayrilma_btn.clicked.connect(self.ayrilma_sec)
        ayrilma_layout.addWidget(self.ayrilma_label)
        ayrilma_layout.addWidget(self.ayrilma_btn)
        calisma_grid.addLayout(ayrilma_layout, 3, 1, 1, 3)

        calisma_grid.addWidget(QLabel("Durum:"), 4, 0)
        self.durum_cb = QComboBox()
        self.durum_cb.addItems(["Aktif", "Pasif", "Ayrıldı"])
        self.durum_cb.currentTextChanged.connect(self.durum_degisti)
        calisma_grid.addWidget(self.durum_cb, 4, 1)
        calisma_grid.addWidget(QLabel("Açıklama:"), 4, 2)
        self.aciklama_input = QLineEdit()
        self.aciklama_input.setPlaceholderText("Engelli, Emekli vb.")
        calisma_grid.addWidget(self.aciklama_input, 4, 3)

        calisma_layout.addWidget(calisma_content)
        layout.addWidget(calisma_card)

        # Butonlar
        btn_frame = QFrame()
        btn_frame.setStyleSheet("QFrame { background-color: #243342; border-top: 1px solid #1a2a38; border-bottom-left-radius: 16px; border-bottom-right-radius: 16px; }")
        btn_frame.setFixedHeight(60)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(20, 10, 20, 10)
        btn_layout.setSpacing(10)

        # Personel Kaydını Sil butonu - yalnızca düzenleme modunda göster
        if self.personel:
            self.sil_btn = QPushButton("🗑️ Personel Kaydını Sil")
            self.sil_btn.setFixedHeight(40)
            self.sil_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #e74c3c;
                    border: 1.5px solid #e74c3c;
                    border-radius: 8px;
                    padding: 0 16px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e74c3c;
                    color: white;
                }
            """)
            self.sil_btn.setCursor(Qt.PointingHandCursor)
            self.sil_btn.clicked.connect(self._personel_sil)
            btn_layout.addWidget(self.sil_btn)

        btn_layout.addStretch()

        self.kaydet_btn = QPushButton("  Kaydet")
        self.kaydet_btn.setFixedHeight(40)
        self.kaydet_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; border-radius: 8px; border: none; padding: 0 28px; font-size: 13px; } QPushButton:hover { background-color: #2ecc71; }")
        self.kaydet_btn.setCursor(Qt.PointingHandCursor)
        self.kaydet_btn.clicked.connect(self._kaydet_kontrol)

        self.iptal_btn = QPushButton("İptal")
        self.iptal_btn.setFixedHeight(40)
        self.iptal_btn.setStyleSheet("QPushButton { background-color: transparent; color: #7f8c8d; border: 1px solid #4a6278; border-radius: 8px; padding: 0 20px; font-size: 13px; } QPushButton:hover { background-color: #34495e; color: white; }")
        self.iptal_btn.setCursor(Qt.PointingHandCursor)
        self.iptal_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.kaydet_btn)
        btn_layout.addWidget(self.iptal_btn)

        outer_lay.addWidget(btn_frame)

        if self.personel:
            self.load_personel()

    def giris_sec(self):
        self._tarih_sec(self.giris_label)

    def ayrilma_sec(self):
        self._tarih_sec(self.ayrilma_label)

    def _tarih_sec(self, label):
        mevcut = label.property("tarih")
        if mevcut and isinstance(mevcut, datetime.date):
            qdate = QDate(mevcut.year, mevcut.month, mevcut.day)
        else:
            qdate = QDate.currentDate()
        dialog = ModernTarihSecici(self, qdate)
        if dialog.exec_():
            secilen = dialog.secilen_tarih()
            label.setText(secilen.toString("dd.MM.yyyy"))
            label.setProperty("tarih", secilen.toPyDate())

    def durum_degisti(self, text):
        self.ayrilma_btn.setEnabled(text == "Ayrıldı")
        if text != "Ayrıldı":
            self.ayrilma_label.setText("")
            self.ayrilma_label.setProperty("tarih", None)

    def load_personel(self):
        p = self.personel
        self.ad_input.setText(p.ad_soyad)
        self.tc_input.setText(p.tc_no or "")
        self.baba_adi_input.setText(p.baba_adi or "")
        self.dogum_yeri_input.setText(p.dogum_yeri or "")
        if p.dogum_tarihi:
            self.dogum_tarihi.set_pydate(p.dogum_tarihi)
        self.iban_input.setText(p.iban or "")
        self.telefon_input.setText(p.telefon or "")
        self.sicil_input.setText(p.sicil_no or "")
        self.maas_input.setText(f"{p.maas:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".") if p.maas else "0")
        if p.ise_baslama:
            self.giris_label.setText(p.ise_baslama.strftime("%d.%m.%Y"))
            self.giris_label.setProperty("tarih", p.ise_baslama)
        if p.isten_ayrilma:
            self.ayrilma_label.setText(p.isten_ayrilma.strftime("%d.%m.%Y"))
            self.ayrilma_label.setProperty("tarih", p.isten_ayrilma)
        self.durum_cb.setCurrentText(p.durum)
        self.aciklama_input.setText(p.aciklama or "")
        idx = self.sube_cb.findData(p.sube_id)
        if idx >= 0:
            self.sube_cb.setCurrentIndex(idx)
        idx = self.gorev_cb.findData(p.gorev_id)
        if idx >= 0:
            self.gorev_cb.setCurrentIndex(idx)

    def _kaydet_kontrol(self):
        """Ad Soyad zorunlu alan kontrolü yapıp kaydet."""
        ad = self.ad_input.text().strip()
        if not ad:
            self.ad_input.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #e74c3c;
                    border-radius: 8px;
                    padding: 8px 12px;
                    background-color: #2c1810;
                    color: #ffffff;
                    font-size: 13px;
                    min-height: 20px;
                }
            """)
            self.ad_input.setPlaceholderText("⚠️ Ad Soyad zorunludur!")
            self.ad_input.setFocus()
            from ui.utils import ModernMesaj
            ModernMesaj.uyari(self, "Ad Soyad alanı boş bırakılamaz.")
            return
        self.ad_input.setStyleSheet("")
        self.accept()

    def _personel_sil(self):
        """Düzenleme modunda personeli doğrudan sil."""
        from ui.utils import ModernMesaj
        cevap = ModernMesaj.soru(
            self,
            f"⚠️ '{self.personel.ad_soyad}' adlı personelin kaydı kalıcı olarak silinecek.\n\n"
            f"İlişkili tüm puantaj, bordro, izin ve haciz kayıtları da silinir.\n\n"
            f"Bu işlem geri alınamaz! Devam etmek istiyor musunuz?"
        )
        if cevap:
            try:
                self.session.delete(self.personel)
                self.session.commit()
                self.done(2)  # 2 = silindi sinyali
            except Exception as e:
                self.session.rollback()
                ModernMesaj.hata(self, f"Silme hatası: {str(e)}")

    def parse_maas(self, deger):
        if not deger:
            return 0.0
        deger = str(deger).strip()
        deger = deger.replace("₺", "").replace("TL", "").strip()
        deger = deger.replace(".", "")
        deger = deger.replace(",", ".")
        try:
            return float(deger)
        except:
            return 0.0


# ==================== PERSONEL DETAY DIALOGU ====================
class PersonelDetayDialog(QDialog):
    def __init__(self, session, personel_id, kullanici=None, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.session = session
        self.kullanici = kullanici
        self.personel = self.session.get(Personel, personel_id)
        self.main_window = self.get_main_window()
        self._maas_gizli = False
        if self.kullanici and not self.kullanici.admin:
            yetkili = {y.modul_adi for y in self.kullanici.yetkileri}
            self._maas_gizli = "maas" not in yetkili
        self._drag_pos = None
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(950, 700)
        self.setAutoFillBackground(True)
        self.setStyleSheet("""
            PersonelDetayDialog { background-color: transparent; }
            QGroupBox {
                font-weight: bold; border: 1px solid rgba(255,255,255,0.12);
                border-radius: 10px; background-color: #34495e;
                margin-top: 8px; padding-top: 10px; color: #ecf0f1;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #bdc3c7; font-size: 11px; }
            QTableWidget { border: none; background-color: transparent; gridline-color: rgba(255,255,255,0.08); color: #ecf0f1; }
            QTableWidget::item { padding: 4px; font-size: 11px; background-color: transparent; color: #ecf0f1; }
            QTableWidget::item:selected { background-color: rgba(52,152,219,0.4); color: white; }
            QHeaderView::section { background-color: rgba(255,255,255,0.08); color: #7f8c8d; font-weight: bold; padding: 5px; border: none; font-size: 10px; }
            QScrollBar:vertical { background: rgba(255,255,255,0.05); width: 5px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); border-radius: 3px; }
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                border: none;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.init_ui()
        self.load_maas_odemeleri()
        self.load_elden_odemeleri()
        self.load_izin_ucreti_odemeleri()
        make_frameless(self, header_height=40)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.pos().y() <= 40:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def get_main_window(self):
        parent = self.parent()
        while parent is not None:
            if parent.__class__.__name__ == "MainWindow":
                return parent
            parent = parent.parent()
        return None

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("QFrame#outer{background:#2c3e50;border-radius:16px;border:1px solid #4a6278;}")
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        # Frameless üst çubuk (sürükleme alanı)
        drag_bar = QFrame()
        drag_bar.setFixedHeight(40)
        drag_bar.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a2a38,stop:1 #2c3e50);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        drag_lay = QHBoxLayout(drag_bar)
        drag_lay.setContentsMargins(14, 0, 10, 0)
        drag_icon = QLabel("👤")
        drag_icon.setStyleSheet("font-size:15px;background:transparent;")
        drag_title = QLabel(self.personel.ad_soyad)
        drag_title.setStyleSheet("color:#ecf0f1;font-size:13px;font-weight:bold;background:transparent;")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.08);color:#ecf0f1;font-size:16px;font-weight:bold;border:none;border-radius:13px;} QPushButton:hover{background:rgba(231,76,60,0.7);color:white;}")
        close_btn.clicked.connect(self.accept)
        drag_lay.addWidget(drag_icon)
        drag_lay.addSpacing(8)
        drag_lay.addWidget(drag_title)
        drag_lay.addStretch()
        drag_lay.addWidget(close_btn)
        outer_lay.addWidget(drag_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: #2c3e50; border: none; }
            QScrollArea > QWidget > QWidget { background: #2c3e50; }
            QScrollBar:vertical { background: rgba(255,255,255,0.05); width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: #2c3e50;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        scroll.setWidget(container)
        scroll.viewport().setStyleSheet("background: #2c3e50;")
        scroll.viewport().setAutoFillBackground(True)
        from PyQt5.QtCore import Qt as _Qt
        scroll.setAttribute(_Qt.WA_StyledBackground, True)
        container.setAutoFillBackground(True)
        outer_lay.addWidget(scroll)

        # Header
        header = QFrame()
        header.setStyleSheet("QFrame { background-color: #34495e; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }")
        header.setFixedHeight(68)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(14, 10, 14, 10)
        h_lay.setSpacing(12)

        initials = "".join([p[0] for p in self.personel.ad_soyad.split()[:2]]).upper()
        avatar = QLabel(initials)
        avatar.setFixedSize(44, 44)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("background-color: #2980b9; border: 2px solid #3498db; border-radius: 22px; color: white; font-size: 15px; font-weight: bold;")
        h_lay.addWidget(avatar)

        name_col = QVBoxLayout()
        name_col.setSpacing(3)
        name_lbl = QLabel(self.personel.ad_soyad)
        name_lbl.setStyleSheet("color: #ecf0f1; font-size: 15px; font-weight: bold; background: transparent;")
        gorev_text = self.personel.gorev.ad if self.personel.gorev else "-"
        sube_text = self.personel.sube.ad if self.personel.sube else "-"
        sub_lbl = QLabel(f"Görevi: {gorev_text}  ·  Şubesi: {sube_text}")
        sub_lbl.setStyleSheet("color: #7f8c8d; font-size: 12px; background: transparent;")
        name_col.addWidget(name_lbl)
        name_col.addWidget(sub_lbl)
        h_lay.addLayout(name_col)
        h_lay.addStretch()

        durum = self.personel.durum or "Aktif"
        if durum == "Aktif":
            ds = "background-color: #1a5276; color: #5dade2; border: 1px solid #2980b9;"
        elif durum == "Ayrıldı":
            ds = "background-color: #641e16; color: #ec7063; border: 1px solid #c0392b;"
        else:
            ds = "background-color: #784212; color: #f0b27a; border: 1px solid #e67e22;"
        durum_lbl = QLabel(durum)
        durum_lbl.setStyleSheet(f"{ds} border-radius: 10px; padding: 4px 14px; font-size: 12px; font-weight: bold;")
        h_lay.addWidget(durum_lbl)

        guncelle_btn = QPushButton("  Bilgileri Güncelle")
        guncelle_btn.setFixedSize(150, 34)
        guncelle_btn.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; border-radius: 8px; font-size: 12px; border: none;")
        guncelle_btn.clicked.connect(self.personel_guncelle)

        ozluk_btn = QPushButton("📄 Özlük Evrakları")
        ozluk_btn.setFixedSize(140, 34)
        ozluk_btn.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; border-radius: 8px; font-size: 12px; border: none;")
        ozluk_btn.clicked.connect(self.ozluk_evraklari)

        if self.kullanici and not self.kullanici.admin:
            yetkili = {y.modul_adi for y in self.kullanici.yetkileri}
            if "personel_guncelle" not in yetkili:
                guncelle_btn.setVisible(False)
                ozluk_btn.setVisible(False)

        h_lay.addWidget(guncelle_btn)
        h_lay.addWidget(ozluk_btn)

        layout.addWidget(header)

        # Kartlar
        def make_card(label, value, val_color="#ecf0f1", accent="#3498db"):
            f = QFrame()
            f.setStyleSheet(f"QFrame {{ background-color: #34495e; border-left: 3px solid {accent}; border-radius: 8px; }}")
            vb = QVBoxLayout(f)
            vb.setContentsMargins(14, 12, 14, 12)
            vb.setSpacing(6)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #7f8c8d; font-size: 10px; letter-spacing: 0.8px; background: transparent;")
            val = QLabel(value)
            val.setStyleSheet(f"color: {val_color}; font-size: 16px; font-weight: bold; background: transparent;")
            val.setWordWrap(True)
            vb.addWidget(lbl)
            vb.addWidget(val)
            return f

        row1 = QHBoxLayout(); row1.setSpacing(8)
        row1.addWidget(make_card("SİCİL NO", self.personel.sicil_no or "-"))
        row1.addWidget(make_card("TC KİMLİK NO", self.personel.tc_no or "-"))
        row1.addWidget(make_card("İŞE GİRİŞ TARİHİ", self.personel.ise_baslama.strftime("%d.%m.%Y") if self.personel.ise_baslama else "-"))
        brut_val = "*****" if self._maas_gizli else f"{self.personel.maas:,.2f} ₺".replace(",", ".")
        row1.addWidget(make_card("BRÜT MAAŞ", brut_val, val_color="#2ecc71" if not self._maas_gizli else "#7f8c8d", accent="#27ae60" if not self._maas_gizli else "#4a6278"))
        layout.addLayout(row1)

        row2 = QHBoxLayout(); row2.setSpacing(8)
        row2.addWidget(make_card("GÖREV", self.personel.gorev.ad if self.personel.gorev else "-", accent="#8e44ad"))
        row2.addWidget(make_card("ŞUBE", self.personel.sube.ad if self.personel.sube else "-", accent="#8e44ad"))
        ayrilma_val = self.personel.isten_ayrilma.strftime("%d.%m.%Y") if self.personel.isten_ayrilma else "-"
        row2.addWidget(make_card("AYRILMA TARİHİ", ayrilma_val, val_color="#ec7063" if self.personel.isten_ayrilma else "#566573", accent="#c0392b" if self.personel.isten_ayrilma else "#2c3e50"))
        row2.addWidget(make_card("TELEFON", self.personel.telefon or "-", val_color="#ecf0f1" if self.personel.telefon else "#566573", accent="#2c3e50"))
        layout.addLayout(row2)

        row3 = QHBoxLayout(); row3.setSpacing(8)
        row3.addWidget(make_card("BABA ADI", self.personel.baba_adi or "-", accent="#f39c12"))
        row3.addWidget(make_card("DOĞUM YERİ", self.personel.dogum_yeri or "-", accent="#f39c12"))
        dogum_tarihi_val = self.personel.dogum_tarihi.strftime("%d.%m.%Y") if self.personel.dogum_tarihi else "-"
        row3.addWidget(make_card("DOĞUM TARİHİ", dogum_tarihi_val, accent="#f39c12"))
        layout.addLayout(row3)

        iban_row = QHBoxLayout(); iban_row.setSpacing(8)
        iban_frame = QFrame()
        iban_frame.setStyleSheet("QFrame { background-color: #34495e; border-left: 3px solid #16a085; border-radius: 8px; }")
        iban_vb = QVBoxLayout(iban_frame)
        iban_vb.setContentsMargins(14, 12, 14, 12); iban_vb.setSpacing(6)
        iban_lbl = QLabel("IBAN")
        iban_lbl.setStyleSheet("color: #7f8c8d; font-size: 10px; letter-spacing: 0.8px; background: transparent;")
        iban_val = QLabel(self.personel.iban or "-")
        iban_val.setStyleSheet("color: #ecf0f1; font-size: 13px; font-weight: bold; background: transparent; font-family: Consolas, monospace; letter-spacing: 1.5px;")
        iban_vb.addWidget(iban_lbl); iban_vb.addWidget(iban_val)
        iban_row.addWidget(iban_frame, 2)

        if self.personel.aciklama:
            ac_frame = QFrame()
            ac_frame.setStyleSheet("QFrame { background-color: #34495e; border-left: 3px solid #e67e22; border-radius: 8px; }")
            ac_vb = QVBoxLayout(ac_frame)
            ac_vb.setContentsMargins(14, 12, 14, 12); ac_vb.setSpacing(6)
            ac_lbl = QLabel("AÇIKLAMA")
            ac_lbl.setStyleSheet("color: #7f8c8d; font-size: 10px; letter-spacing: 0.8px; background: transparent;")
            ac_val = QLabel(self.personel.aciklama)
            ac_val.setStyleSheet("color: #f0b27a; font-size: 14px; font-weight: bold; background: transparent;")
            ac_val.setWordWrap(True)
            ac_vb.addWidget(ac_lbl); ac_vb.addWidget(ac_val)
            iban_row.addWidget(ac_frame, 1)
        layout.addLayout(iban_row)

        # İşlem Butonları (2 satır, modern çerçeve)
        islemler_grp = QGroupBox("  Hızlı İşlemler")
        islemler_grp.setStyleSheet("""
            QGroupBox {
                color: #bdc3c7;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #4a6278;
                border-radius: 10px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)
        islemler_layout = QVBoxLayout(islemler_grp)
        islemler_layout.setSpacing(10)
        islemler_layout.setContentsMargins(15, 15, 15, 15)

        # İşlem Butonları (2 satır, modern çerçeve)
        islemler_grp = QGroupBox("  Hızlı İşlemler")
        islemler_grp.setStyleSheet("""
            QGroupBox {
                color: #bdc3c7;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #4a6278;
                border-radius: 10px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)
        islemler_layout = QVBoxLayout(islemler_grp)
        islemler_layout.setSpacing(10)
        islemler_layout.setContentsMargins(15, 15, 15, 15)

        # 1. SATIR: İzin Geçmişi, Avans Ekle, Kasa Açığı, Sigara Açığı
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.izin_gecmisi_btn = QPushButton("📅 İzin Geçmişi")
        self.avans_btn = QPushButton("💸 Avans Ekle")
        self.kasa_btn = QPushButton("💰 Kasa Açığı")
        self.sigara_btn = QPushButton("🚬 Sigara Açığı")

        # İzin Geçmişi butonu (mavi gradient)
        self.izin_gecmisi_btn.setFixedHeight(38)
        self.izin_gecmisi_btn.setCursor(Qt.PointingHandCursor)
        self.izin_gecmisi_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a3a5c,stop:1 #2980b9);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 0 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0e2a4a,stop:1 #1a5276);
            }
        """)

        # Avans, Kasa, Sigara butonları (kırmızı gradient)
        for btn in [self.avans_btn, self.kasa_btn, self.sigara_btn]:
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4a0a0a,stop:1 #c0392b);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3a0808,stop:1 #a93226);
                }
            """)

        row1.addWidget(self.izin_gecmisi_btn)
        row1.addWidget(self.avans_btn)
        row1.addWidget(self.kasa_btn)
        row1.addWidget(self.sigara_btn)
        row1.addStretch()
        islemler_layout.addLayout(row1)

        # 2. SATIR: Senelik İzin, Bordro Hesapla, Maaş Ödemesi, Haciz Ödemesi
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        self.senelik_izin_btn = QPushButton("🏖️ Senelik İzin")
        self.bordro_hesapla_btn = QPushButton("📊 Bordro Hesapla")
        self.maas_odeme_btn = QPushButton("💵 Maaş Ödemesi")
        self.haciz_odeme_btn = QPushButton("⚖️ Haciz Ödemesi")
        self.elden_gecmis_btn = QPushButton("🤝 Elden Geçmiş")

        # Senelik İzin butonu (mavi gradient - izin geçmişi ile aynı)
        self.senelik_izin_btn.setFixedHeight(38)
        self.senelik_izin_btn.setCursor(Qt.PointingHandCursor)
        self.senelik_izin_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a3a5c,stop:1 #2980b9);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 0 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0e2a4a,stop:1 #1a5276);
            }
        """)

        # Bordro Hesapla, Maaş Ödemesi, Haciz Ödemesi (turuncu gradient)
        for btn in [self.bordro_hesapla_btn, self.maas_odeme_btn, self.haciz_odeme_btn]:
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3a2000,stop:1 #e67e22);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2a1800,stop:1 #d35400);
                }
            """)

        # Elden Geçmiş butonu (yeşil)
        self.elden_gecmis_btn.setFixedHeight(38)
        self.elden_gecmis_btn.setCursor(Qt.PointingHandCursor)
        self.elden_gecmis_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a4a2a,stop:1 #27ae60);
                border: none; border-radius: 8px; color: white;
                font-weight: bold; font-size: 12px; padding: 0 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0e3a1a,stop:1 #1e8449);
            }
        """)

        row2.addWidget(self.senelik_izin_btn)
        row2.addWidget(self.bordro_hesapla_btn)
        row2.addWidget(self.maas_odeme_btn)
        row2.addWidget(self.haciz_odeme_btn)
        row2.addWidget(self.elden_gecmis_btn)
        row2.addStretch()
        islemler_layout.addLayout(row2)

        # Buton sinyallerini bağla
        self.izin_gecmisi_btn.clicked.connect(self.izin_gecmisi_goster)
        self.avans_btn.clicked.connect(lambda: self.avans_kasa_sigara_ekle("avans"))
        self.kasa_btn.clicked.connect(lambda: self.avans_kasa_sigara_ekle("kasa"))
        self.sigara_btn.clicked.connect(lambda: self.avans_kasa_sigara_ekle("sigara"))
        self.senelik_izin_btn.clicked.connect(self.senelik_izin_tanimla)
        self.bordro_hesapla_btn.clicked.connect(self.bordro_hesapla)
        self.maas_odeme_btn.clicked.connect(self.maas_odeme_yap)
        self.haciz_odeme_btn.clicked.connect(self.haciz_odeme_yap)
        self.elden_gecmis_btn.clicked.connect(self.elden_odeme_gecmisi_goster)

        # ── Yetki bazlı buton gizleme ──
        if self.kullanici and not self.kullanici.admin:
            yetkili = {y.modul_adi for y in self.kullanici.yetkileri}
            if "avans_ekle" not in yetkili:
                self.avans_btn.setVisible(False)
            if "kasa_ekle" not in yetkili:
                self.kasa_btn.setVisible(False)
            if "sigara_ekle" not in yetkili:
                self.sigara_btn.setVisible(False)
            if "bordro" not in yetkili:
                self.bordro_hesapla_btn.setVisible(False)
                self.maas_odeme_btn.setVisible(False)
            if "haciz" not in yetkili:
                self.haciz_odeme_btn.setVisible(False)
            if "maas" not in yetkili:
                self.elden_gecmis_btn.setVisible(False)

        layout.addWidget(islemler_grp)

        # Diğer kartlar (izin, haciz, maaş ödemeleri, avans detay)
        cards_layout = QHBoxLayout(); cards_layout.setSpacing(10)
        izin_card = QGroupBox("  Senelik İzinler")
        izin_layout = QVBoxLayout(izin_card); izin_layout.setSpacing(5)
        self.izin_table = QTableWidget()
        self.izin_table.setColumnCount(5)
        self.izin_table.setHorizontalHeaderLabels(["Yıl", "Tanım", "Kullan", "Kalan", "İşlem"])
        self.izin_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.izin_table.horizontalHeader().setStretchLastSection(False)
        for ci, cw in enumerate([60, 70, 60, 60, 50]):
            self.izin_table.setColumnWidth(ci, cw)
        self.izin_table.verticalHeader().setVisible(False)
        self.izin_table.setMinimumHeight(130)
        self.izin_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.izin_table.horizontalHeader().sectionResized.connect(self._auto_save_izin_widths)
        izin_layout.addWidget(self.izin_table)
        self.load_izin_table_widths()
        self.load_izinler()
        cards_layout.addWidget(izin_card)

        haciz_card = QGroupBox("  Haciz / İcra")
        haciz_layout = QVBoxLayout(haciz_card); haciz_layout.setSpacing(5)
        self.haciz_table = QTableWidget()
        self.haciz_table.setColumnCount(6)
        self.haciz_table.setHorizontalHeaderLabels(["Dosya No", "Borç", "Kalan", "Aylık", "Durum", "Alacaklı"])
        self.haciz_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.haciz_table.verticalHeader().setVisible(False)
        self.haciz_table.setMinimumHeight(130)
        haciz_layout.addWidget(self.haciz_table)
        self.load_hacizler()
        cards_layout.addWidget(haciz_card)
        layout.addLayout(cards_layout)

        maas_card = QGroupBox("  Maaş Ödemeleri (Banka — Son 5 Ay)")
        maas_layout2 = QVBoxLayout(maas_card); maas_layout2.setSpacing(5)
        self.odeme_table = QTableWidget()
        self.odeme_table.setColumnCount(7)
        self.odeme_table.setHorizontalHeaderLabels(["Dönem", "Brüt", "Net", "Kesinti", "İcra", "Ödeme Tarihi", "İşlem"])
        self.odeme_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.odeme_table.setColumnWidth(6, 140)
        self.odeme_table.verticalHeader().setVisible(False)
        self.odeme_table.setMinimumHeight(180)
        maas_layout2.addWidget(self.odeme_table)
        layout.addWidget(maas_card)

        elden_card = QGroupBox("  Elden Ödemeler")
        elden_layout = QVBoxLayout(elden_card); elden_layout.setSpacing(5)
        self.elden_table = QTableWidget()
        self.elden_table.setColumnCount(5)
        self.elden_table.setHorizontalHeaderLabels(["Tarih", "Dönem", "Tutar", "Açıklama", "İşlem"])
        self.elden_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.elden_table.verticalHeader().setVisible(False)
        self.elden_table.setMinimumHeight(150)
        elden_layout.addWidget(self.elden_table)
        layout.addWidget(elden_card)

        izin_ucret_card = QGroupBox("  İzin Ücreti Ödemeleri")
        izin_ucret_layout = QVBoxLayout(izin_ucret_card); izin_ucret_layout.setSpacing(5)
        self.izin_ucret_table = QTableWidget()
        self.izin_ucret_table.setColumnCount(5)
        self.izin_ucret_table.setHorizontalHeaderLabels(["Tarih", "Gün", "Tutar", "Açıklama", "İşlem"])
        self.izin_ucret_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed); self.izin_ucret_table.setColumnWidth(0, 110)
        self.izin_ucret_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed); self.izin_ucret_table.setColumnWidth(1, 70)
        self.izin_ucret_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed); self.izin_ucret_table.setColumnWidth(2, 120)
        self.izin_ucret_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.izin_ucret_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed); self.izin_ucret_table.setColumnWidth(4, 50)
        self.izin_ucret_table.verticalHeader().setVisible(False)
        self.izin_ucret_table.setMinimumHeight(120)
        self.izin_ucret_table.setEditTriggers(QTableWidget.NoEditTriggers)
        izin_ucret_layout.addWidget(self.izin_ucret_table)
        layout.addWidget(izin_ucret_card)

        acik_card = QGroupBox("  Mevcut & Gelecek Dönem Avans / Açıklar")
        acik_layout = QVBoxLayout(acik_card); acik_layout.setSpacing(6)
        self.avans_detay_table = QTableWidget()
        self.avans_detay_table.setColumnCount(4)
        self.avans_detay_table.setHorizontalHeaderLabels(["Tür", "Tarih", "Tutar", "Açıklama"])
        self.avans_detay_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.avans_detay_table.verticalHeader().setVisible(False)
        self.avans_detay_table.setMinimumHeight(120)
        self.avans_detay_table.setEditTriggers(QTableWidget.NoEditTriggers)
        acik_layout.addWidget(self.avans_detay_table)
        layout.addWidget(acik_card)
        self.load_avans_detay()

        btn_layout = QHBoxLayout()
        kapat_btn = QPushButton("Kapat")
        kapat_btn.setFixedSize(110, 34)
        kapat_btn.setStyleSheet("background-color: #34495e; color: #ecf0f1; font-weight: bold; border-radius: 8px; font-size: 12px; border: 1px solid #4a6278;")
        kapat_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(kapat_btn)
        layout.addLayout(btn_layout)

    # ========== VERİ YÜKLEME METOTLARI ==========
    def load_izinler(self):
        self.session.expire_all()
        self.izin_table.setRowCount(0)
        yillik_izinler = self.session.query(YillikIzin).filter(YillikIzin.personel_id == self.personel.id).order_by(YillikIzin.yil).all()
        for yil in yillik_izinler:
            kullanilan = self.session.query(func.sum(Izin.gun_sayisi)).filter(
                Izin.personel_id == self.personel.id,
                Izin.durum == "Onaylandı",
                Izin.baslangic_tarihi >= datetime.date(yil.yil, 1, 1),
                Izin.bitis_tarihi <= datetime.date(yil.yil, 12, 31)
            ).scalar() or 0
            kalan = yil.tanimlanan_izin - kullanilan
            row = self.izin_table.rowCount()
            self.izin_table.insertRow(row)
            self.izin_table.setRowHeight(row, 32)
            self.izin_table.setItem(row, 0, QTableWidgetItem(str(yil.yil)))
            self.izin_table.setItem(row, 1, QTableWidgetItem(str(yil.tanimlanan_izin)))
            self.izin_table.setItem(row, 2, QTableWidgetItem(str(kullanilan)))
            kalan_item = QTableWidgetItem(str(kalan))
            kalan_item.setForeground(QColor("#27ae60") if kalan >= 0 else QColor("#e74c3c"))
            self.izin_table.setItem(row, 3, kalan_item)
            sil_btn = QPushButton("🗑")
            sil_btn.setFixedSize(28, 26)
            sil_btn.setCursor(Qt.PointingHandCursor)
            sil_btn.setStyleSheet("QPushButton{background:#c0392b;color:white;border-radius:6px;border:none;font-size:13px;font-weight:bold;padding:0;} QPushButton:hover{background:#e74c3c;}")
            sil_btn.clicked.connect(lambda _, yid=yil.id: self.sil_yillik_izin_tanimi(yid))
            sw = QWidget(); sw.setFixedSize(40, 30); sl = QHBoxLayout(sw); sl.setContentsMargins(0,0,0,0); sl.setAlignment(Qt.AlignCenter); sl.addWidget(sil_btn)
            self.izin_table.setCellWidget(row, 4, sw)

    def sil_yillik_izin_tanimi(self, yillik_izin_id):
        yi = self.session.get(YillikIzin, yillik_izin_id)
        if not yi:
            return
        if not ModernMesaj.soru(self, f"{yi.yil} yılı {yi.tanimlanan_izin} günlük izin tanımı silinsin mi?"):
            return
        try:
            self.session.delete(yi)
            self.session.commit()
            self.load_izinler()
            ModernMesaj.basari(self, "İzin tanımı silindi.")
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))

    def _izin_table_widths_path(self):
        return get_config_path("senelik_izin_table_widths.json")

    def save_izin_table_widths(self):
        widths = {}
        for i in range(self.izin_table.columnCount()):
            widths[i] = self.izin_table.columnWidth(i)
        try:
            with open(self._izin_table_widths_path(), "w", encoding="utf-8") as f:
                json.dump(widths, f)
            ModernMesaj.basari(self, "Senelik izin tablosu sütun genişlikleri kaydedildi.")
        except Exception as e:
            ModernMesaj.hata(self, f"Kaydedilemedi: {str(e)}")

    def load_izin_table_widths(self):
        path = self._izin_table_widths_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    widths = json.load(f)
                for i, w in widths.items():
                    self.izin_table.setColumnWidth(int(i), int(w))
            except Exception:
                pass

    def _auto_save_izin_widths(self):
        widths = {}
        for i in range(self.izin_table.columnCount()):
            widths[i] = self.izin_table.columnWidth(i)
        try:
            with open(self._izin_table_widths_path(), "w", encoding="utf-8") as f:
                json.dump(widths, f)
        except Exception:
            pass

    def load_hacizler(self):
        self.haciz_table.setRowCount(0)
        hacizler = self.session.query(Haciz).filter(Haciz.personel_id == self.personel.id).all()
        for h in hacizler:
            row = self.haciz_table.rowCount()
            self.haciz_table.insertRow(row)
            self.haciz_table.setRowHeight(row, 22)
            self.haciz_table.setItem(row, 0, QTableWidgetItem(h.dosya_no))
            borc_val = "*****" if self._maas_gizli else f"{h.borc_miktari:,.0f} ₺"
            self.haciz_table.setItem(row, 1, QTableWidgetItem(borc_val))
            kalan_val = "*****" if self._maas_gizli else f"{h.kalan_borc:,.0f} ₺"
            self.haciz_table.setItem(row, 2, QTableWidgetItem(kalan_val))
            if self._maas_gizli:
                aylik_val = "*****"
            else:
                aylik = h.aylik_kesinti if h.aylik_kesinti else (h.personel.maas * h.kesinti_orani / 100 if h.kesinti_orani else 0)
                aylik_val = f"{aylik:,.0f} ₺"
            self.haciz_table.setItem(row, 3, QTableWidgetItem(aylik_val))
            self.haciz_table.setItem(row, 4, QTableWidgetItem(h.durum))
            self.haciz_table.setItem(row, 5, QTableWidgetItem(h.alacakli_kurum or "-"))

    def load_maas_odemeleri(self):
        self.odeme_table.setRowCount(0)
        self.odeme_table.setColumnWidth(6, 140)
        bordrolar = self.session.query(Bordro).filter(
            Bordro.personel_id == self.personel.id
        ).order_by(Bordro.yil.desc(), Bordro.ay.desc()).limit(5).all()
        for b in bordrolar:
            row = self.odeme_table.rowCount()
            self.odeme_table.insertRow(row)
            self.odeme_table.setRowHeight(row, 32)
            donem = f"{b.ay:02d}/{b.yil}"
            self.odeme_table.setItem(row, 0, QTableWidgetItem(donem))
            brut_val = "*****" if self._maas_gizli else f"{b.personel.maas:,.0f} ₺"
            brut_item = QTableWidgetItem(brut_val)
            brut_item.setTextAlignment(Qt.AlignCenter)
            self.odeme_table.setItem(row, 1, brut_item)
            odeme = self.session.query(MaasOdeme).filter(
                MaasOdeme.bordro_id == b.id,
                ~func.lower(MaasOdeme.aciklama).like("%elden%"),
                ~func.lower(MaasOdeme.aciklama).like("%izin ücreti%")
            ).first()
            if self._maas_gizli:
                net_val = "*****"
            elif odeme:
                net_val = f"{odeme.tutar:,.2f} ₺".replace(",", "@").replace(".", ",").replace("@", ".")
            else:
                net_val = f"{b.toplam_net_maas:,.2f} ₺".replace(",", "@").replace(".", ",").replace("@", ".")
            net_item = QTableWidgetItem(net_val)
            net_item.setTextAlignment(Qt.AlignCenter)
            self.odeme_table.setItem(row, 2, net_item)
            if self._maas_gizli:
                kesinti_val = "*****"
            else:
                kesinti = b.personel.maas - b.toplam_net_maas
                kesinti_val = f"{kesinti:,.0f} ₺"
            kesinti_item = QTableWidgetItem(kesinti_val)
            kesinti_item.setTextAlignment(Qt.AlignCenter)
            self.odeme_table.setItem(row, 3, kesinti_item)
            icra_val = "*****" if self._maas_gizli else f"{b.icra_kesintisi:,.0f} ₺"
            icra_item = QTableWidgetItem(icra_val)
            icra_item.setTextAlignment(Qt.AlignCenter)
            self.odeme_table.setItem(row, 4, icra_item)
            if odeme:
                if self._maas_gizli:
                    txt = odeme.tarih.strftime('%d.%m.%Y')
                else:
                    txt = f"{odeme.tarih.strftime('%d.%m.%Y')} ({odeme.tutar:,.2f} ₺)".replace(",", "@").replace(".", ",").replace("@", ".")
                self.odeme_table.setItem(row, 5, QTableWidgetItem(txt))
            else:
                self.odeme_table.setItem(row, 5, QTableWidgetItem("-"))
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)
            if not self._maas_gizli:
                if odeme:
                    odeme_sil_btn = QPushButton("🗑️ Ödeme")
                    odeme_sil_btn.setFixedSize(60, 26)
                    odeme_sil_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 4px; font-size: 8px; font-weight: bold; border: none; } QPushButton:hover { background-color: #c0392b; }")
                    odeme_sil_btn.setCursor(Qt.PointingHandCursor)
                    odeme_sil_btn.clicked.connect(lambda checked, x=odeme.id, d=donem: self.sil_maas_odemesi(x, d))
                    btn_layout.addWidget(odeme_sil_btn)
                bordro_sil_btn = QPushButton("🗑️ Bordro")
                bordro_sil_btn.setFixedSize(60, 26)
                bordro_sil_btn.setStyleSheet("QPushButton { background-color: #e67e22; color: white; border-radius: 4px; font-size: 8px; font-weight: bold; border: none; } QPushButton:hover { background-color: #d35400; }")
                bordro_sil_btn.setCursor(Qt.PointingHandCursor)
                bordro_sil_btn.clicked.connect(lambda checked, x=b.id, d=donem: self.sil_bordro(x, d))
                btn_layout.addWidget(bordro_sil_btn)
            self.odeme_table.setCellWidget(row, 6, btn_widget)

    def load_elden_odemeleri(self):
        self.elden_table.setRowCount(0)
        odemeler = self.session.query(MaasOdeme).filter(
            MaasOdeme.personel_id == self.personel.id,
            func.lower(MaasOdeme.aciklama).like("%elden%"),
            ~func.lower(MaasOdeme.aciklama).like("%izin ücreti%")
        ).order_by(MaasOdeme.tarih.desc()).limit(10).all()
        row = 0
        for o in odemeler:
            self.elden_table.insertRow(row)
            self.elden_table.setRowHeight(row, 32)
            self.elden_table.setItem(row, 0, QTableWidgetItem(o.tarih.strftime("%d.%m.%Y") if o.tarih else "—"))
            donem_str = ""
            if o.bordro:
                donem_str = f"{o.bordro.ay:02d}/{o.bordro.yil}"
            self.elden_table.setItem(row, 1, QTableWidgetItem(donem_str))
            tutar_val = "*****" if self._maas_gizli else f"{o.tutar:,.2f} ₺".replace(",", "@").replace(".", ",").replace("@", ".")
            t_item = QTableWidgetItem(tutar_val)
            t_item.setTextAlignment(Qt.AlignCenter)
            self.elden_table.setItem(row, 2, t_item)
            self.elden_table.setItem(row, 3, QTableWidgetItem(o.aciklama or "—"))
            sw = QWidget(); swl = QHBoxLayout(sw); swl.setContentsMargins(2,2,2,2); swl.setSpacing(4)
            if not self._maas_gizli:
                sil_btn = QPushButton("🗑️")
                sil_btn.setFixedSize(30, 26)
                sil_btn.setStyleSheet("QPushButton{background:#e74c3c;color:white;border-radius:4px;font-size:10px;font-weight:bold;border:none;} QPushButton:hover{background:#c0392b;}")
                sil_btn.setCursor(Qt.PointingHandCursor)
                sil_btn.clicked.connect(lambda checked, x=o.id: self.sil_maas_odemesi(x, "elden"))
                swl.addWidget(sil_btn)
            swl.addStretch()
            self.elden_table.setCellWidget(row, 4, sw)
            row += 1

    def load_izin_ucreti_odemeleri(self):
        self.izin_ucret_table.setRowCount(0)
        odemeler = self.session.query(MaasOdeme).filter(
            MaasOdeme.personel_id == self.personel.id,
            func.lower(MaasOdeme.aciklama).like("%izin ücreti%")
        ).order_by(MaasOdeme.tarih.desc()).all()
        row = 0
        for o in odemeler:
            self.izin_ucret_table.insertRow(row)
            self.izin_ucret_table.setRowHeight(row, 32)
            self.izin_ucret_table.setItem(row, 0, QTableWidgetItem(o.tarih.strftime("%d.%m.%Y") if o.tarih else "—"))
            gun_str = "—"
            if o.aciklama:
                import re as _re
                m = _re.search(r"(\d+)\s*g[üi]n", o.aciklama)
                if m:
                    gun_str = m.group(1)
            self.izin_ucret_table.setItem(row, 1, QTableWidgetItem(gun_str))
            tutar_val = "*****" if self._maas_gizli else f"{o.tutar:,.2f} ₺".replace(",", ".")
            t_item = QTableWidgetItem(tutar_val)
            t_item.setTextAlignment(Qt.AlignCenter)
            self.izin_ucret_table.setItem(row, 2, t_item)
            self.izin_ucret_table.setItem(row, 3, QTableWidgetItem(o.aciklama or "—"))
            sw = QWidget(); sw.setFixedSize(40, 30); sl = QHBoxLayout(sw); sl.setContentsMargins(0,0,0,0); sl.setAlignment(Qt.AlignCenter)
            if not self._maas_gizli:
                sil_btn = QPushButton("🗑")
                sil_btn.setFixedSize(28, 26)
                sil_btn.setCursor(Qt.PointingHandCursor)
                sil_btn.setStyleSheet("QPushButton{background:#c0392b;color:white;border-radius:6px;border:none;font-size:13px;font-weight:bold;padding:0;} QPushButton:hover{background:#e74c3c;}")
                sil_btn.clicked.connect(lambda _, oid=o.id: self.sil_izin_ucreti_odemesi(oid))
                sl.addWidget(sil_btn)
            self.izin_ucret_table.setCellWidget(row, 4, sw)
            row += 1

    def sil_izin_ucreti_odemesi(self, odeme_id):
        odeme = self.session.get(MaasOdeme, odeme_id)
        if not odeme:
            return
        if not ModernMesaj.soru(self, f"{odeme.tarih.strftime('%d.%m.%Y')} tarihli {odeme.tutar:,.2f} ₺ izin ücreti ödemesi silinsin mi?"):
            return
        try:
            m = re.search(r"(\d+)\s*g[üi]n", odeme.aciklama or "")
            if m:
                ilgili = self.session.query(Izin).filter(
                    Izin.personel_id == odeme.personel_id,
                    Izin.gun_sayisi == int(m.group(1)),
                    func.lower(Izin.aciklama).like("%izin ücreti ödemesi%kullan%")
                ).all()
                for izin in ilgili:
                    self.session.delete(izin)
            self.session.delete(odeme)
            self.session.commit()
            self.load_izin_ucreti_odemeleri()
            self.load_izinler()
            ModernMesaj.basari(self, "İzin ücreti ödemesi silindi.")
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))

    def load_avans_detay(self):
        from models import Avans, KasaAcigi, SigaraAcigi
        self.avans_detay_table.setRowCount(0)
        bugun = datetime.date.today()
        ilk_gun = datetime.date(bugun.year, bugun.month, 1)
        tur_renk = {
            "Avans": ("#3498db", "#1a5276"),
            "Kasa Açığı": ("#e67e22", "#784212"),
            "Sigara Açığı": ("#8e44ad", "#4a235a"),
        }
        for model, tur_ad in [(Avans, "Avans"), (KasaAcigi, "Kasa Açığı"), (SigaraAcigi, "Sigara Açığı")]:
            kayitlar = self.session.query(model).filter(
                model.personel_id == self.personel.id,
                model.tarih >= ilk_gun
            ).order_by(model.tarih).all()
            for k in kayitlar:
                row = self.avans_detay_table.rowCount()
                self.avans_detay_table.insertRow(row)
                self.avans_detay_table.setRowHeight(row, 24)
                tur_item = QTableWidgetItem(tur_ad)
                renk, _ = tur_renk[tur_ad]
                tur_item.setForeground(QColor(renk))
                tur_item.setTextAlignment(Qt.AlignCenter)
                font = QFont(); font.setBold(True)
                tur_item.setFont(font)
                self.avans_detay_table.setItem(row, 0, tur_item)
                tarih_item = QTableWidgetItem(k.tarih.strftime("%d.%m.%Y"))
                tarih_item.setTextAlignment(Qt.AlignCenter)
                self.avans_detay_table.setItem(row, 1, tarih_item)
                tutar_val = "*****" if self._maas_gizli else f"{k.tutar:,.2f} ₺".replace(",", ".")
                tutar_item = QTableWidgetItem(tutar_val)
                tutar_item.setTextAlignment(Qt.AlignCenter)
                tutar_item.setForeground(QColor(renk))
                self.avans_detay_table.setItem(row, 2, tutar_item)
                acik_item = QTableWidgetItem(k.aciklama or "-")
                self.avans_detay_table.setItem(row, 3, acik_item)

    # ========== PERSONEL GÜNCELLEME ==========
    def personel_guncelle(self):
        dialog = PersonelDialog(self.session, personel=self.personel, parent=self)
        result = dialog.exec_()
        if result == 2:  # Silindi
            ModernMesaj.basari(self, "Personel kaydı silindi.")
            self.accept()
        elif result == QDialog.Accepted:
            self.personel.sicil_no = dialog.sicil_input.text().strip() or None
            self.personel.ad_soyad = dialog.ad_input.text()
            self.personel.tc_no = dialog.tc_input.text()
            self.personel.baba_adi = dialog.baba_adi_input.text()
            self.personel.dogum_yeri = dialog.dogum_yeri_input.text()
            self.personel.dogum_tarihi = dialog.dogum_tarihi.get_pydate()
            self.personel.iban = dialog.iban_input.text()
            self.personel.telefon = dialog.telefon_input.text()
            self.personel.gorev_id = dialog.gorev_cb.currentData()
            self.personel.maas = dialog.parse_maas(dialog.maas_input.text())
            self.personel.sube_id = dialog.sube_cb.currentData()
            self.personel.ise_baslama = dialog.giris_label.property("tarih")
            self.personel.isten_ayrilma = dialog.ayrilma_label.property("tarih") if dialog.ayrilma_label.property("tarih") else None
            self.personel.durum = dialog.durum_cb.currentText()
            self.personel.aciklama = dialog.aciklama_input.text()
            self.session.commit()
            ModernMesaj.basari(self, "Personel bilgileri güncellendi.")
            self.accept()

    def sil_maas_odemesi(self, odeme_id, donem):
        cevap = ModernMesaj.soru(self, f"{donem} dönemine ait maaş ödemesini silmek istediğinize emin misiniz?")
        if cevap:
            try:
                odeme = self.session.get(MaasOdeme, odeme_id)
                if odeme:
                    self.session.delete(odeme)
                    self.session.commit()
                    self.load_maas_odemeleri()
                    self.load_elden_odemeleri()
                    if self.main_window and hasattr(self.main_window, 'bordro_page'):
                        self.main_window.bordro_page.load_data()
                    ModernMesaj.basari(self, "Ödeme kaydı silindi.")
            except Exception as e:
                self.session.rollback()
                ModernMesaj.hata(self, f"Silme hatası: {str(e)}")

    def sil_bordro(self, bordro_id, donem):
        cevap = ModernMesaj.soru(self, f"{donem} dönemine ait bordro kaydını silmek istediğinize emin misiniz?\nBu işlem geri alınamaz ve ilişkili tüm ödemeler silinir!")
        if cevap:
            try:
                bordro = self.session.get(Bordro, bordro_id)
                if bordro:
                    self.session.query(MaasOdeme).filter(MaasOdeme.bordro_id == bordro_id).delete()
                    self.session.query(HacizOdeme).filter(HacizOdeme.bordro_id == bordro_id).delete()
                    self.session.delete(bordro)
                    self.session.commit()
                    self.load_maas_odemeleri()
                    if self.main_window and hasattr(self.main_window, 'bordro_page'):
                        self.main_window.bordro_page.load_data()
                    ModernMesaj.basari(self, "Bordro kaydı silindi.")
            except Exception as e:
                self.session.rollback()
                ModernMesaj.hata(self, f"Silme hatası: {str(e)}")

    def ozluk_evraklari(self):
        dialog = OzlukEvraklariDialog(self.personel, parent=self)
        dialog.exec_()

    def elden_odeme_gecmisi_goster(self):
        from ui.personel_detay_islemleri import EldenOdemeGecmisDialog
        dialog = EldenOdemeGecmisDialog(self.session, self.personel, kullanici=self.kullanici, parent=self)
        dialog.exec_()

    def senelik_izin_tanimla(self):
        dialog = SenelikIzinDialog(self.session, self.personel, parent=self)
        if dialog.exec_():
            self.load_izinler()

    def avans_kasa_sigara_ekle(self, tur):
        dialog = AvansKasaSigaraDialog(self.session, self.personel, tur, parent=self)
        if dialog.exec_():
            self.load_avans_detay()
            if self.main_window and hasattr(self.main_window, 'avans_page'):
                self.main_window.avans_page.load_data()

    def maas_odeme_yap(self):
        from ui.personel_maas_odeme_dialog import PersonelDonemSecDialog
        from ui.maas_odeme_dialog import MaasOdemeDialog
        from models import Bordro

        # Önce dönem seç
        donem_dialog = PersonelDonemSecDialog(self.session, self.personel, parent=self)
        if donem_dialog.exec_() != PersonelDonemSecDialog.Accepted:
            return

        yil = donem_dialog.secilen_yil
        ay  = donem_dialog.secilen_ay

        # O döneme ait tüm bordrolar
        bordrolar = self.session.query(Bordro).filter(
            Bordro.yil == yil,
            Bordro.ay  == ay
        ).all()
        gecerli = [b for b in bordrolar if b.personel is not None]

        if not gecerli:
            from ui.utils import ModernMesaj
            ModernMesaj.uyari(self, "Bu dönem için hesaplanmış bordro bulunamadı.")
            return

        # Maaş ödeme dialog
        elden_sistem = any((b.elden_odenecek or 0) > 0 for b in gecerli)
        dialog = MaasOdemeDialog(
            session=self.session,
            yil=yil,
            ay=ay,
            gecerli_bordrolar=gecerli,
            elden_sistem=elden_sistem,
            format_tl_fn=lambda v: f"{v:,.2f} ₺".replace(",", "."),
            parent=self
        )
        if dialog.exec_():
            self.load_maas_odemeleri()
            if self.main_window and hasattr(self.main_window, 'bordro_page'):
                self.main_window.bordro_page.load_data()

    def haciz_odeme_yap(self):
        dialog = HacizOdemeDialog(self.session, self.personel, parent=self)
        if dialog.exec_():
            self.load_hacizler()
            if self.main_window and hasattr(self.main_window, 'haciz_page'):
                self.main_window.haciz_page.load_data()

    def bordro_hesapla(self):
        dialog = BordroHesaplaDialog(self.session, self.personel, parent=self)
        if dialog.exec_():
            self.load_maas_odemeleri()
            if self.main_window and hasattr(self.main_window, 'bordro_page'):
                self.main_window.bordro_page.load_data()

    def izin_gecmisi_goster(self):
        dialog = IzinGecmisiDialog(self.session, self.personel, parent=self)
        if dialog.exec_():
            self.load_izinler()
            self.load_izin_ucreti_odemeleri()


# ==================== ANA PERSONEL YÖNETİM SAYFASI ====================
class PersonelPage(QWidget):
    def __init__(self, kullanici=None):
        super().__init__()
        self.kullanici = kullanici
        self.session = get_session()
        self.current_sort_column = "ad_soyad"
        self.current_sort_order = "asc"
        self.filters = []
        self.init_ui()
        self._yetki_uygula()
        self.load_data()

    def _yetki_uygula(self):
        if not self.kullanici or self.kullanici.admin:
            self._btn_delegate.set_enabled(True)
            return
        yetkili = {y.modul_adi for y in self.kullanici.yetkileri}
        duz_yetkili = "personel_duzenle" in yetkili
        self._btn_delegate.set_enabled(duz_yetkili)
        if not duz_yetkili:
            self.add_btn.setVisible(False)
            self.import_btn.setVisible(False)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(10)
        self.setStyleSheet("background-color: #2c3e50;")

        # Üst panel
        top_panel = QFrame()
        top_panel.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 12px;
                border: 1px solid #4a6278;
            }
            QLabel { color: #bdc3c7; font-weight: bold; font-size: 11px; background: transparent; }
            QLineEdit, QComboBox {
                background-color: #2c3e50; border: 1px solid #4a6278;
                border-radius: 6px; color: white; padding: 6px 10px; font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #3498db; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView { background: #34495e; color: white; selection-background-color: #3498db; }
        """)
        top_panel.setFixedHeight(100)
        top_lay = QVBoxLayout(top_panel)
        top_lay.setContentsMargins(14, 10, 14, 10)
        top_lay.setSpacing(8)

        # 1. SATIR: Personel arama + Durum filtresi
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.main_search = QLineEdit()
        self.main_search.setPlaceholderText("🔍 Personel Ara (Sicil, Ad, TC)...")
        self.main_search.setMinimumWidth(250)
        self.main_search.textChanged.connect(self.load_data)

        self.status_main_cb = QComboBox()
        self.status_main_cb.clear()
        self.status_main_cb.addItems(["Aktif ve Pasif", "Aktif", "Pasif", "Ayrıldı", "Tümü"])
        self.status_main_cb.setCurrentIndex(0)  # Aktif ve Pasif
        self.status_main_cb.currentTextChanged.connect(self.load_data)
        self.status_main_cb.setStyleSheet("""
            QComboBox QAbstractItemView {
                background-color: #ecf0f1;
                color: #2c3e50;
                selection-background-color: #3498db;
                selection-color: white;
            }
        """)

        row1.addWidget(QLabel("Personel:"))
        row1.addWidget(self.main_search, 1)
        row1.addWidget(QLabel("Durum:"))
        row1.addWidget(self.status_main_cb)
        row1.addStretch()
        top_lay.addLayout(row1)

        # 2. SATIR: Butonlar
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.add_btn = self.create_btn("➕ Yeni", "#a6289a", self.add_personel)
        self.import_btn = self.create_btn("📥 Excel'den Aktar", "#e67e22", self.excel_import)
        self.export_btn = self.create_btn("📤 Excel'e Aktar", "#1fb50b", self.excel_export)
        self.template_btn = self.create_btn("📄 Şablon İndir", "#7f8c8d", self.download_template)

        row2.addWidget(self.add_btn)
        row2.addWidget(self.import_btn)
        row2.addWidget(self.export_btn)
        row2.addWidget(self.template_btn)
        row2.addStretch()
        top_lay.addLayout(row2)

        layout.addWidget(top_panel)

        # Filtre paneli
        filter_panel = QFrame()
        filter_panel.setFixedHeight(55)
        filter_panel.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 8px;
                border: 1px solid #4a6278;
            }
            QLabel { color: #7f8c8d; font-size: 11px; font-weight: bold; background: transparent; }
        """)
        filter_layout = QHBoxLayout(filter_panel)
        filter_layout.setContentsMargins(14, 8, 14, 8)
        filter_layout.setSpacing(12)

        self.gorev_filter = MultiSelectFilter("Görev")
        self.sube_filter  = MultiSelectFilter("Şube")
        self.durum_filter_ms = MultiSelectFilter("Durum")
        self.aciklama_filter = MultiSelectFilter("Açıklama")

        for lbl_txt, widget in [("GÖREV", self.gorev_filter), ("ŞUBE", self.sube_filter),
                                  ("DURUM", self.durum_filter_ms), ("AÇIKLAMA", self.aciklama_filter)]:
            vb = QVBoxLayout()
            vb.setSpacing(2)
            lbl = QLabel(lbl_txt)
            vb.addWidget(lbl)
            vb.addWidget(widget)
            filter_layout.addLayout(vb, 1)

        for f in [self.gorev_filter, self.sube_filter, self.durum_filter_ms, self.aciklama_filter]:
            f.selectionChanged.connect(self.load_data)

        layout.addWidget(filter_panel)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "SİCİL\nNO", "AD\nSOYAD", "TELEFON", "GÖREV", "ŞUBE",
            "GİRİŞ\nTARİHİ", "AYRILMA\nTARİHİ", "MAAŞ", "AÇIKLAMA", "DURUM", "İŞLEMLER"
        ])

        self.table.setStyleSheet("""
            QTableWidget {
                background: white;
                border-radius: 10px;
                border: none;
                gridline-color: #f1f2f6;
            }
            QHeaderView::section {
                background-color: #2f3542;
                color: white;
                font-weight: bold;
                height: 50px;
                border: none;
                text-align: center;
                padding: 2px 4px;
            }
            QTableWidget::item {
                color: #1a1a1a;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(10, 140)

        self.table.horizontalHeader().sectionClicked.connect(self.on_column_sort)

        self._btn_delegate = ButtonDelegate([
            {"text": "✏️ Düzenle", "width": 70, "bg": "#3498db"},
            {"text": "🗑️ Sil", "width": 50, "bg": "#e74c3c"},
        ], parent=self.table)
        self.table.setItemDelegateForColumn(10, self._btn_delegate)
        self._btn_delegate.buttonClicked.connect(self._on_table_button)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_column_context_menu)

        self.table.itemDoubleClicked.connect(self.personel_detay_goster)

        layout.addWidget(self.table)

        self.load_column_widths()

    def create_btn(self, text, color, func):
        btn = QPushButton(text)
        btn.setFixedSize(120, 35)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        btn.clicked.connect(func)
        return btn

    def tr_lower(self, text):
        if not text:
            return ""
        return str(text).replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'ğ').replace('Ü', 'ü').replace('Ş', 'ş').replace('Ö', 'ö').replace('Ç', 'ç').lower()

    def on_column_sort(self, col):
        column_map = {
            0: "sicil_no",
            1: "ad_soyad",
            2: "telefon",
            3: "gorev.ad",
            4: "sube.ad",
            5: "ise_baslama",
            6: "isten_ayrilma",
            7: "maas",
            8: "aciklama",
            9: "durum"
        }
        if col in column_map:
            if self.current_sort_column == column_map[col]:
                self.current_sort_order = "desc" if self.current_sort_order == "asc" else "asc"
            else:
                self.current_sort_column = column_map[col]
                self.current_sort_order = "asc"
            self.load_data()

    def load_data(self):
        self.table.setRowCount(0)
        query = self.session.query(Personel)

        durum_secim = self.status_main_cb.currentText()
        if durum_secim == "Aktif ve Pasif":
            query = query.filter(Personel.durum.in_(["Aktif", "Pasif"]))
        elif durum_secim != "Tümü":
            query = query.filter(Personel.durum == durum_secim)

        if self.kullanici and not self.kullanici.admin:
            yetkili_sube_ids = [s.sube_id for s in self.kullanici.subeleri]
            if yetkili_sube_ids:
                query = query.filter(Personel.sube_id.in_(yetkili_sube_ids))

        if self.current_sort_column == "gorev.ad":
            query = query.join(Gorev).order_by(
                Gorev.ad.asc() if self.current_sort_order == "asc" else Gorev.ad.desc()
            )
        elif self.current_sort_column == "sube.ad":
            query = query.join(Sube).order_by(
                Sube.ad.asc() if self.current_sort_order == "asc" else Sube.ad.desc()
            )
        elif self.current_sort_column == "sicil_no":
            query = query.order_by(Personel.sicil_no.asc() if self.current_sort_order == "asc" else Personel.sicil_no.desc())
        else:
            order_col = getattr(Personel, self.current_sort_column, Personel.ad_soyad)
            if self.current_sort_order == "asc":
                query = query.order_by(order_col.asc())
            else:
                query = query.order_by(order_col.desc())

        arama = self.tr_lower(self.main_search.text())
        personeller = query.all()

        if self.current_sort_column == "sicil_no":
            def _sicil_key(p):
                try:
                    return int(p.sicil_no)
                except (TypeError, ValueError):
                    return float('inf')
            personeller.sort(key=_sicil_key, reverse=(self.current_sort_order == "desc"))

        if arama:
            personeller = [p for p in personeller if
                           (p.sicil_no and arama in self.tr_lower(p.sicil_no)) or
                           (p.ad_soyad and arama in self.tr_lower(p.ad_soyad)) or
                           (p.tc_no and arama in self.tr_lower(p.tc_no))]

        sel_gorev    = self.gorev_filter.get_selected()
        sel_sube     = self.sube_filter.get_selected()
        sel_durum    = self.durum_filter_ms.get_selected()
        sel_aciklama = self.aciklama_filter.get_selected()

        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        try:
            for p in personeller:
                gorev_val = p.gorev.ad if p.gorev else ""
                sube_val = p.sube.ad if p.sube else ""
                durum_val = p.durum or ""
                aciklama_val = p.aciklama or ""

                if sel_gorev and gorev_val not in sel_gorev:
                    continue
                if sel_sube and sube_val not in sel_sube:
                    continue
                if sel_durum and durum_val not in sel_durum:
                    continue
                if sel_aciklama and aciklama_val not in sel_aciklama:
                    continue

                row = self.table.rowCount()
                self.table.insertRow(row)

                aciklama_lower = self.tr_lower(p.aciklama or "")
                bg_color = None
                if "emekli" in aciklama_lower:
                    bg_color = QColor("#d1ecf1")
                elif "engelli" in aciklama_lower:
                    bg_color = QColor("#fff3cd")

                ayrilma_str = p.isten_ayrilma.strftime("%d.%m.%Y") if p.isten_ayrilma else "-"
                giris_str = p.ise_baslama.strftime("%d.%m.%Y") if p.ise_baslama else "-"
                maas_str = f"{p.maas:,.2f} ₺".replace(",", ".") if p.maas else "0,00 ₺"

                items = [
                    QTableWidgetItem(p.sicil_no or ""),
                    QTableWidgetItem(p.ad_soyad or ""),
                    QTableWidgetItem(p.telefon or "-"),
                    QTableWidgetItem(gorev_val or "-"),
                    QTableWidgetItem(sube_val or "-"),
                    QTableWidgetItem(giris_str),
                    QTableWidgetItem(ayrilma_str),
                    QTableWidgetItem(maas_str),
                    QTableWidgetItem(aciklama_val or ""),
                    QTableWidgetItem(durum_val),
                    QTableWidgetItem("")
                ]

                for col, item in enumerate(items):
                    if bg_color and col != 10:
                        item.setBackground(bg_color)
                    if col == 9:
                        if durum_val == "Aktif":
                            item.setForeground(QColor("#27ae60"))
                        else:
                            item.setForeground(QColor("#e74c3c"))
                    if col == 1:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, col, item)

                self.table.item(row, 10).setData(Qt.UserRole, p.id)
                self.table.item(row, 10).setData(Qt.UserRole + 1, p.ad_soyad)

        finally:
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)

        self._update_filter_options()

        maas_gizli = False
        if self.kullanici and not self.kullanici.admin:
            yetkili = {y.modul_adi for y in self.kullanici.yetkileri}
            maas_gizli = "maas" not in yetkili
        self.table.setColumnHidden(7, maas_gizli)

    def _update_filter_options(self):
        all_personel = self.session.query(Personel).all()
        gorev_vals = [p.gorev.ad for p in all_personel if p.gorev]
        sube_vals  = [p.sube.ad  for p in all_personel if p.sube]
        durum_vals = [p.durum    for p in all_personel if p.durum]
        acik_vals  = [p.aciklama for p in all_personel if p.aciklama]
        self.gorev_filter.set_options(gorev_vals)
        self.sube_filter.set_options(sube_vals)
        self.durum_filter_ms.set_options(durum_vals)
        self.aciklama_filter.set_options(acik_vals)

    def add_personel(self):
        dialog = PersonelDialog(self.session, parent=self)
        if dialog.exec_():
            yeni = Personel(
                sicil_no=dialog.sicil_input.text().strip() or None,
                ad_soyad=dialog.ad_input.text(),
                tc_no=dialog.tc_input.text(),
                baba_adi=dialog.baba_adi_input.text(),
                dogum_yeri=dialog.dogum_yeri_input.text(),
                dogum_tarihi=dialog.dogum_tarihi.get_pydate(),
                iban=dialog.iban_input.text(),
                telefon=dialog.telefon_input.text(),
                gorev_id=dialog.gorev_cb.currentData(),
                maas=dialog.parse_maas(dialog.maas_input.text()),
                sube_id=dialog.sube_cb.currentData(),
                ise_baslama=dialog.giris_label.property("tarih"),
                isten_ayrilma=dialog.ayrilma_label.property("tarih") if dialog.ayrilma_label.property("tarih") else None,
                durum=dialog.durum_cb.currentText(),
                aciklama=dialog.aciklama_input.text()
            )
            self.session.add(yeni)
            self.session.commit()
            self.load_data()
            ModernMesaj.basari(self, "Personel eklendi.")

    def _on_table_button(self, row, btn_idx):
        item = self.table.item(row, 10)
        if not item:
            return
        pid = item.data(Qt.UserRole)
        if btn_idx == 0:
            self.edit_personel(pid)
        elif btn_idx == 1:
            ad_soyad = item.data(Qt.UserRole + 1)
            if ad_soyad:
                self.sil_personel(pid, ad_soyad)

    def edit_personel(self, personel_id):
        p = self.session.get(Personel, personel_id)
        if not p:
            return
        dialog = PersonelDialog(self.session, personel=p, parent=self)
        result = dialog.exec_()
        if result == 2:  # Silindi
            self.load_data()
            ModernMesaj.basari(self, "Personel kaydı silindi.")
        elif result == QDialog.Accepted:
            p.sicil_no = dialog.sicil_input.text().strip() or None
            p.ad_soyad = dialog.ad_input.text()
            p.tc_no = dialog.tc_input.text()
            p.baba_adi = dialog.baba_adi_input.text()
            p.dogum_yeri = dialog.dogum_yeri_input.text()
            p.dogum_tarihi = dialog.dogum_tarihi.get_pydate()
            p.iban = dialog.iban_input.text()
            p.telefon = dialog.telefon_input.text()
            p.gorev_id = dialog.gorev_cb.currentData()
            p.maas = dialog.parse_maas(dialog.maas_input.text())
            p.sube_id = dialog.sube_cb.currentData()
            p.ise_baslama = dialog.giris_label.property("tarih")
            p.isten_ayrilma = dialog.ayrilma_label.property("tarih") if dialog.ayrilma_label.property("tarih") else None
            p.durum = dialog.durum_cb.currentText()
            p.aciklama = dialog.aciklama_input.text()
            self.session.commit()
            self.load_data()
            ModernMesaj.basari(self, "Personel güncellendi.")

    def sil_personel(self, personel_id, ad_soyad):
        cevap = ModernMesaj.soru(self, f"{ad_soyad} adlı personeli silmek istediğinize emin misiniz?\nBu işlem geri alınamaz!")
        if cevap:
            try:
                p = self.session.get(Personel, personel_id)
                if p:
                    self.session.delete(p)
                    self.session.commit()
                    self.load_data()
                    ModernMesaj.basari(self, "Personel silindi.")
            except Exception as e:
                self.session.rollback()
                ModernMesaj.hata(self, f"Silme hatası: {str(e)}")

    def personel_detay_goster(self, item):
        row = self.table.currentRow()
        if row < 0:
            return
        sicil = self.table.item(row, 0).text()
        personel = self.session.query(Personel).filter(Personel.sicil_no == sicil).first()
        if not personel:
            return
        dialog = PersonelDetayDialog(self.session, personel.id, kullanici=self.kullanici, parent=self)
        dialog.exec_()
        self.load_data()

    def save_column_widths(self):
        widths = {}
        for i in range(self.table.columnCount()):
            widths[i] = self.table.columnWidth(i)
        try:
            with open(get_config_path("personel_table_widths.json"), "w", encoding="utf-8") as f:
                json.dump(widths, f)
            ModernMesaj.basari(self, "Sütun genişlikleri kaydedildi.")
        except Exception as e:
            ModernMesaj.hata(self, f"Kaydedilemedi: {str(e)}")

    def load_column_widths(self):
        if os.path.exists(get_config_path("personel_table_widths.json")):
            try:
                with open(get_config_path("personel_table_widths.json"), "r", encoding="utf-8") as f:
                    widths = json.load(f)
                for i, w in widths.items():
                    self.table.setColumnWidth(int(i), w)
            except:
                pass

    def show_column_context_menu(self, pos):
        menu = QMenu()
        save_action = menu.addAction("Görünümü Kaydet")
        save_action.triggered.connect(self.save_column_widths)
        menu.exec_(self.table.mapToGlobal(pos))

    def excel_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Excel Aktar", "Personel_Listesi.xlsx", "Excel (*.xlsx)")
        if path:
            try:
                data = []
                for r in range(self.table.rowCount()):
                    row_data = []
                    for c in range(10):
                        item = self.table.item(r, c)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)
                df = pd.DataFrame(data, columns=[
                    "Sicil No", "Ad Soyad", "Telefon", "Görev", "Şube",
                    "Giriş Tarihi", "Ayrılma Tarihi", "Maaş", "Açıklama", "Durum"
                ])
                df.to_excel(path, index=False)
                ModernMesaj.basari(self, "Excel dosyası oluşturuldu.")
            except Exception as e:
                ModernMesaj.hata(self, str(e))

    def excel_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel (*.xlsx *.xls)")
        if not path:
            return
        try:
            df = pd.read_excel(path)
            mevcut_subeler = {s.ad: s.id for s in self.session.query(Sube).all()}
            mevcut_gorevler = {g.ad: g.id for g in self.session.query(Gorev).all()}

            eklenen = 0
            guncellenen = 0
            hata = 0

            for _, row in df.iterrows():
                try:
                    ad_soyad = str(row.get("Ad Soyad", "")).strip()
                    if not ad_soyad or ad_soyad == "nan":
                        continue

                    sicil_no = str(row.get("Sicil No", "")).strip()
                    tc_no = str(row.get("TC No", "")).strip() if pd.notna(row.get("TC No")) else ""
                    baba_adi = str(row.get("Baba Adı", "")).strip() if pd.notna(row.get("Baba Adı")) else ""
                    dogum_yeri = str(row.get("Doğum Yeri", "")).strip() if pd.notna(row.get("Doğum Yeri")) else ""
                    dogum_tarihi = None
                    dt = row.get("Doğum Tarihi")
                    if pd.notna(dt):
                        try:
                            if isinstance(dt, (datetime.datetime, pd.Timestamp)):
                                dogum_tarihi = dt.date()
                            else:
                                dogum_tarihi = datetime.datetime.strptime(str(dt), "%d.%m.%Y").date()
                        except:
                            pass
                    iban = str(row.get("IBAN", "")).strip() if pd.notna(row.get("IBAN")) else ""
                    telefon = str(row.get("Telefon", "")).strip() if pd.notna(row.get("Telefon")) else ""
                    maas_str = str(row.get("Maaş", "0")).strip()
                    maas = self.parse_maas(maas_str)
                    durum = str(row.get("Durum", "Aktif")).strip()
                    if durum not in ["Aktif", "Pasif", "Ayrıldı"]:
                        durum = "Aktif"

                    giris = row.get("Giriş Tarihi")
                    if pd.notna(giris):
                        if isinstance(giris, (datetime.datetime, pd.Timestamp)):
                            giris_tarihi = giris.date()
                        else:
                            try:
                                giris_tarihi = datetime.datetime.strptime(str(giris), "%d.%m.%Y").date()
                            except:
                                giris_tarihi = datetime.date.today()
                    else:
                        giris_tarihi = datetime.date.today()

                    ayrilma = row.get("Ayrılma Tarihi")
                    ayrilma_tarihi = None
                    if pd.notna(ayrilma):
                        if isinstance(ayrilma, (datetime.datetime, pd.Timestamp)):
                            ayrilma_tarihi = ayrilma.date()
                        else:
                            try:
                                ayrilma_tarihi = datetime.datetime.strptime(str(ayrilma), "%d.%m.%Y").date()
                            except:
                                pass

                    sube_adi = str(row.get("Şube", "")).strip()
                    sube_id = None
                    if sube_adi and sube_adi != "nan":
                        if sube_adi in mevcut_subeler:
                            sube_id = mevcut_subeler[sube_adi]
                        else:
                            yeni_sube = Sube(ad=sube_adi)
                            self.session.add(yeni_sube)
                            self.session.flush()
                            sube_id = yeni_sube.id
                            mevcut_subeler[sube_adi] = sube_id

                    gorev_adi = str(row.get("Görev", "")).strip()
                    gorev_id = None
                    if gorev_adi and gorev_adi != "nan":
                        if gorev_adi in mevcut_gorevler:
                            gorev_id = mevcut_gorevler[gorev_adi]
                        else:
                            yeni_gorev = Gorev(ad=gorev_adi)
                            self.session.add(yeni_gorev)
                            self.session.flush()
                            gorev_id = yeni_gorev.id
                            mevcut_gorevler[gorev_adi] = gorev_id

                    aciklama = str(row.get("Açıklama", "")) if pd.notna(row.get("Açıklama")) else ""

                    personel = None
                    if sicil_no:
                        personel = self.session.query(Personel).filter(Personel.sicil_no == sicil_no).first()
                    if not personel and tc_no:
                        personel = self.session.query(Personel).filter(Personel.tc_no == tc_no).first()

                    if personel:
                        personel.ad_soyad = ad_soyad
                        personel.tc_no = tc_no or personel.tc_no
                        personel.baba_adi = baba_adi or personel.baba_adi
                        personel.dogum_yeri = dogum_yeri or personel.dogum_yeri
                        if dogum_tarihi:
                            personel.dogum_tarihi = dogum_tarihi
                        personel.iban = iban or personel.iban
                        personel.telefon = telefon or personel.telefon
                        personel.sicil_no = sicil_no or personel.sicil_no
                        personel.maas = maas
                        personel.durum = durum
                        personel.ise_baslama = giris_tarihi
                        personel.isten_ayrilma = ayrilma_tarihi
                        personel.aciklama = aciklama or personel.aciklama
                        personel.sube_id = sube_id or personel.sube_id
                        personel.gorev_id = gorev_id or personel.gorev_id
                        guncellenen += 1
                    else:
                        yeni = Personel(
                            sicil_no=sicil_no or None,
                            ad_soyad=ad_soyad,
                            tc_no=tc_no or None,
                            baba_adi=baba_adi or None,
                            dogum_yeri=dogum_yeri or None,
                            dogum_tarihi=dogum_tarihi,
                            iban=iban or None,
                            telefon=telefon or None,
                            maas=maas,
                            durum=durum,
                            ise_baslama=giris_tarihi,
                            isten_ayrilma=ayrilma_tarihi,
                            aciklama=aciklama or None,
                            sube_id=sube_id,
                            gorev_id=gorev_id
                        )
                        self.session.add(yeni)
                        eklenen += 1

                except Exception as e:
                    hata += 1
                    print(f"Satır hatası: {e}")

            self.session.commit()
            self.load_data()
            ModernMesaj.basari(self, f"Excel'den aktarıldı.\nYeni eklenen: {eklenen}\nGüncellenen: {guncellenen}\nHatalı: {hata}")
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, f"Dosya okuma hatası: {str(e)}")

    def parse_maas(self, deger):
        if not deger or deger == "nan":
            return 0.0
        deger = str(deger).strip()
        if deger == "":
            return 0.0
        deger = deger.replace("₺", "").replace("TL", "").strip()
        deger = deger.replace(".", "")
        deger = deger.replace(",", ".")
        try:
            return float(deger)
        except:
            rakamlar = re.findall(r'[\d,\.]+', deger)
            if rakamlar:
                return self.parse_maas(rakamlar[0])
            return 0.0

    def download_template(self):
        path, _ = QFileDialog.getSaveFileName(self, "Şablon Kaydet", "Personel_Sablonu.xlsx", "Excel (*.xlsx)")
        if path:
            columns = [
                "Sicil No", "Ad Soyad", "TC No", "Baba Adı", "Doğum Yeri", "Doğum Tarihi",
                "IBAN", "Telefon", "Görev", "Şube", "Giriş Tarihi", "Ayrılma Tarihi",
                "Maaş", "Açıklama", "Durum"
            ]
            df = pd.DataFrame(columns=columns)
            df.to_excel(path, index=False)
            ModernMesaj.basari(self, "Şablon oluşturuldu.")