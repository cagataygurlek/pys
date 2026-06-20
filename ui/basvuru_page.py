# ui/basvuru_page.py - Güncellenmiş sürüm (Türkçe karakter arama düzeltmesi + 2 satırlı toolbar)

import datetime
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QFrame, QHeaderView, QMessageBox,
    QLineEdit, QComboBox, QDialog, QFormLayout, QDoubleSpinBox,
    QDateEdit, QAbstractItemView, QFileDialog, QCheckBox, QApplication
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QColor, QFont

from database import get_session
from models import BasvuruAday, Personel, Sube, Gorev
from sqlalchemy import func
from ui.utils import ModernMesaj, TarihAlani, ModernTarihSecici, get_config_path
import os
import json


class ModernCheckBox(QCheckBox):
    """Modern görünümlü QCheckBox"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QCheckBox {
                color: #ecf0f1;
                font-size: 12px;
                spacing: 10px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #4a6278;
                background: #34495e;
            }
            QCheckBox::indicator:hover {
                border-color: #3498db;
            }
            QCheckBox::indicator:checked {
                background: #3498db;
                border-color: #3498db;
            }
            QCheckBox::indicator:unchecked {
                background: #34495e;
                border-color: #4a6278;
            }
            QCheckBox::indicator:checked:hover {
                background: #2980b9;
                border-color: #2980b9;
            }
        """)


class BasvuruPage(QWidget):
    def __init__(self):
        super().__init__()
        self.session = get_session()
        self.setStyleSheet("background-color: #2c3e50;")
        self._build_ui()
        self.load_data()

    # ── UI (2 satırlı toolbar) ──────────────────────────────────────
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(12)

        # Üst araç çubuğu (2 satır)
        toolbar = QFrame()
        toolbar.setStyleSheet("background: #34495e; border-radius: 10px; border: 1px solid #4a6278;")
        toolbar.setFixedHeight(110)   # 2 satır için yükseklik artırıldı
        tl = QVBoxLayout(toolbar)
        tl.setContentsMargins(12, 8, 12, 8)
        tl.setSpacing(8)

        # 1. SATIR: Arama ve Durum filtresi
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.arama = QLineEdit()
        self.arama.setPlaceholderText("🔍 Aday ara (isim, pozisyon)...")
        self.arama.setFixedHeight(36)
        self.arama.setStyleSheet("""
            border: 1px solid #ced4da;
            border-radius: 10px;
            padding: 0 10px;
            font-size: 12px;
            background-color: #2c3e50;
            color: white;
            QLineEdit::placeholder { color: #bdc3c7; }
        """)
        self.arama.textChanged.connect(self.load_data)
        row1.addWidget(self.arama, 2)

        self.durum_filter = QComboBox()
        self.durum_filter.addItems(["Tüm Durumlar", "Beklemede", "Uygun", "Uygun Değil", "İşe Alındı"])
        self.durum_filter.setFixedSize(150, 36)
        self.durum_filter.setStyleSheet("""
            background-color: #2c3e50;
            color: white;
            border: 1px solid #4a6278;
            border-radius: 6px;
            padding: 5px;
            font-size: 12px;
        """)
        self.durum_filter.currentIndexChanged.connect(self.load_data)
        row1.addWidget(self.durum_filter)
        row1.addStretch()
        tl.addLayout(row1)

        # 2. SATIR: Butonlar
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        yeni_btn = self._btn("➕ Yeni Başvuru", "#27ae60")
        yeni_btn.clicked.connect(self._yeni_basvuru)
        row2.addWidget(yeni_btn)

        import_btn = self._btn("📂 Excel Aktar", "#2980b9")
        import_btn.clicked.connect(self._excel_import)
        row2.addWidget(import_btn)

        toplu_excel_btn = self._btn("📥 Listeyi Dışa", "#16a085")
        toplu_excel_btn.clicked.connect(self._toplu_excel)
        row2.addWidget(toplu_excel_btn)

        row2.addStretch()
        tl.addLayout(row2)

        lay.addWidget(toolbar)

        # İstatistik kartları
        self.stat_lay = QHBoxLayout()
        self.stat_lay.setSpacing(10)
        self.card_toplam = self._stat_card("Toplam Aday", "0", "#3498db")
        self.card_bekle = self._stat_card("Beklemede", "0", "#f39c12")
        self.card_uygun = self._stat_card("Uygun", "0", "#27ae60")
        self.card_uygun_d = self._stat_card("Uygun Değil", "0", "#e74c3c")
        self.card_alindi = self._stat_card("İşe Alındı", "0", "#9b59b6")
        for c in [self.card_toplam, self.card_bekle, self.card_uygun, self.card_uygun_d, self.card_alindi]:
            self.stat_lay.addWidget(c)
        lay.addLayout(self.stat_lay)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Ad Soyad", "Pozisyon", "Başvuru Tarihi",
            "Telefon", "Ücret Beklentisi", "Durum", "Notlar", "İşlemler"
        ])
        self.table.setColumnWidth(7, 280)
        # Sütun genişliği ayarlanabilir + kaydedilebilir
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(7, 280)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: white; border-radius: 10px;
                border: 1px solid #dcdde1; gridline-color: #ecf0f1;
            }
            QHeaderView::section {
                background: #1a2a38; color: white;
                font-weight: bold; padding: 8px; border: none; font-size: 12px;
            }
            QTableWidget::item { padding: 5px; font-size: 12px; color: #1a1a1a; }
            QTableWidget::item:selected { background: #1a2a38; color: white; }
        """)
        lay.addWidget(self.table)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_column_context_menu)
        self.load_column_widths()

    def _widths_path(self):
        return get_config_path("basvuru_table_widths.json")

    def save_column_widths(self):
        widths = {}
        for i in range(self.table.columnCount()):
            widths[i] = self.table.columnWidth(i)
        try:
            with open(self._widths_path(), "w", encoding="utf-8") as f:
                json.dump(widths, f)
            ModernMesaj.basari(self, "Başvurular tablosu sütun genişlikleri kaydedildi.")
        except Exception as e:
            ModernMesaj.hata(self, f"Kaydedilemedi: {str(e)}")

    def load_column_widths(self):
        path = self._widths_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    widths = json.load(f)
                for i, w in widths.items():
                    self.table.setColumnWidth(int(i), int(w))
            except Exception:
                pass

    def show_column_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu
        menu = QMenu()
        save_action = menu.addAction("Sütun genişliklerini kaydet")
        save_action.triggered.connect(self.save_column_widths)
        menu.exec_(self.table.mapToGlobal(pos))

    # ── VERİ YÜKLE (Türkçe karakter düzeltmesi) ──────────────────────────────
    def tr_lower(self, text):
        """Türkçe karakterleri normalize eder"""
        if not text:
            return ""
        return str(text).replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'g').replace('Ü', 'u').replace('Ş', 's').replace('Ö', 'o').replace('Ç', 'c').lower()

    def load_data(self):
        self.table.setRowCount(0)
        arama = self.tr_lower(self.arama.text().strip())
        arama = self.tr_lower(arama)   # Türkçe karakter normalize
        durum_filter = self.durum_filter.currentText()

        adaylar = self.session.query(BasvuruAday).order_by(
            BasvuruAday.basvuru_tarihi.desc()).all()

        # Filtrele
        if arama:
            adaylar = [a for a in adaylar if
                       arama in self.tr_lower(a.ad or "") or
                       arama in self.tr_lower(a.soyad or "") or
                       arama in self.tr_lower(a.pozisyon or "")]
        if durum_filter != "Tüm Durumlar":
            adaylar = [a for a in adaylar if a.durum == durum_filter]

        # İstatistikler
        tumu = self.session.query(BasvuruAday).all()
        self.card_toplam.findChild(QLabel, "val").setText(str(len(tumu)))
        for durum, card in [
            ("Beklemede", self.card_bekle),
            ("Uygun", self.card_uygun),
            ("Uygun Değil", self.card_uygun_d),
            ("İşe Alındı", self.card_alindi),
        ]:
            sayi = sum(1 for a in tumu if a.durum == durum)
            card.findChild(QLabel, "val").setText(str(sayi))

        # Tablo doldur
        for a in adaylar:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 40)

            ad_soyad = f"{a.ad or ''} {a.soyad or ''}".strip()
            tarih = a.basvuru_tarihi.strftime("%d.%m.%Y") if a.basvuru_tarihi else "-"
            tel = a.telefon_cep1 or a.telefon_ev or "-"
            ucret = f"{a.ucret_beklenti:,.0f} ₺".replace(",", ".") if a.ucret_beklenti else "-"

            for col, val in enumerate([ad_soyad, a.pozisyon or "-", tarih, tel, ucret]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row, col, item)

            # Durum badge
            durum_item = QTableWidgetItem(a.durum or "Beklemede")
            durum_item.setTextAlignment(Qt.AlignCenter)
            durum_colors = {
                "Beklemede": ("#f39c12", "#fef9e7"),
                "Uygun": ("#27ae60", "#eafaf1"),
                "Uygun Değil": ("#e74c3c", "#fdedec"),
                "İşe Alındı": ("#9b59b6", "#f5eef8"),
            }
            fc, bc = durum_colors.get(a.durum or "Beklemede", ("#7f8c8d", "#f2f3f4"))
            durum_item.setForeground(QColor(fc))
            durum_item.setBackground(QColor(bc))
            font = QFont(); font.setBold(True)
            durum_item.setFont(font)
            self.table.setItem(row, 5, durum_item)

            # Not
            not_item = QTableWidgetItem(a.notlar or "")
            not_item.setForeground(QColor("#7f8c8d"))
            self.table.setItem(row, 6, not_item)

            # İşlem butonları
            btn_widget = QWidget()
            btn_lay = QHBoxLayout(btn_widget)
            btn_lay.setContentsMargins(4, 4, 4, 4)
            btn_lay.setSpacing(4)

            detay_btn = self._mini_btn("Detay", "#2980b9")
            detay_btn.clicked.connect(lambda _, aid=a.id: self._detay(aid))
            btn_lay.addWidget(detay_btn)

            if a.durum == "Beklemede":
                uygun_btn = self._mini_btn("Uygun", "#27ae60")
                uygun_btn.clicked.connect(lambda _, aid=a.id: self._durum_guncelle(aid, "Uygun"))
                btn_lay.addWidget(uygun_btn)
                ud_btn = self._mini_btn("Uygun Değil", "#e74c3c")
                ud_btn.clicked.connect(lambda _, aid=a.id: self._durum_guncelle(aid, "Uygun Değil"))
                btn_lay.addWidget(ud_btn)
            elif a.durum == "Uygun":
                aktar_btn = self._mini_btn("Personele Aktar", "#9b59b6")
                aktar_btn.clicked.connect(lambda _, aid=a.id: self._personele_aktar(aid))
                btn_lay.addWidget(aktar_btn)
                beklet_btn = self._mini_btn("Beklet", "#f39c12")
                beklet_btn.clicked.connect(lambda _, aid=a.id: self._durum_guncelle(aid, "Beklemede"))
                btn_lay.addWidget(beklet_btn)
            elif a.durum == "İşe Alındı":
                alindi_lbl = QLabel("✓ Aktarıldı")
                alindi_lbl.setStyleSheet("color: #9b59b6; font-size: 11px; font-weight: bold;")
                btn_lay.addWidget(alindi_lbl)
                iptal_btn = self._mini_btn("İşe Alımı İptal Et", "#c0392b")
                iptal_btn.clicked.connect(lambda _, aid=a.id: self._ise_alim_iptal(aid))
                btn_lay.addWidget(iptal_btn)
            elif a.durum == "Uygun Değil":
                beklet_btn = self._mini_btn("Beklet", "#f39c12")
                beklet_btn.clicked.connect(lambda _, aid=a.id: self._durum_guncelle(aid, "Beklemede"))
                btn_lay.addWidget(beklet_btn)

            sil_btn = self._mini_btn("🗑", "#e74c3c")
            sil_btn.setFixedWidth(28)
            sil_btn.clicked.connect(lambda _, aid=a.id: self._sil(aid))
            btn_lay.addWidget(sil_btn)
            btn_lay.addStretch()

            self.table.setCellWidget(row, 7, btn_widget)

    # ── EYLEMLER (tamamen aynı, değişmedi) ────────────────────────────────
    def _yeni_basvuru(self):
        from ui.basvuru_dialog import BasvuruFormDialog
        d = BasvuruFormDialog(self.session, parent=self)
        if d.exec_() == QDialog.Accepted:
            self.load_data()

    def _detay(self, aday_id):
        from ui.basvuru_dialog import BasvuruFormDialog
        a = self.session.get(BasvuruAday, aday_id)
        if a:
            d = BasvuruFormDialog(self.session, aday=a, parent=self)
            if d.exec_() == QDialog.Accepted:
                self.load_data()

    def _durum_guncelle(self, aday_id, yeni_durum):
        a = self.session.get(BasvuruAday, aday_id)
        if a:
            a.durum = yeni_durum
            self.session.commit()
            self.load_data()

    def _sil(self, aday_id):
        a = self.session.get(BasvuruAday, aday_id)
        if not a:
            return
        if not ModernMesaj.soru(self, f"{a.ad} {a.soyad} adayı silinsin mi?", "Sil"):
            return
        self.session.delete(a)
        self.session.commit()
        self.load_data()

    def _personele_aktar(self, aday_id):
        a = self.session.get(BasvuruAday, aday_id)
        if not a:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Personele Aktar — {a.ad} {a.soyad}")
        dialog.setFixedSize(460, 480)
        dialog.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QLabel#baslik {
                color: white; font-size: 15px; font-weight: bold;
                background: transparent;
            }
            QLabel#alt_baslik {
                color: #7f8c8d; font-size: 11px;
                background: transparent;
            }
            QLabel#field_lbl {
                color: #bdc3c7; font-size: 11px;
                letter-spacing: 0.5px; background: transparent;
            }
            QLineEdit, QComboBox, QDoubleSpinBox {
                background-color: #34495e;
                border: 1px solid #4a6278;
                border-radius: 8px;
                color: white;
                font-size: 13px;
                padding: 8px 12px;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus,
            QDoubleSpinBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #34495e; color: white;
                selection-background-color: #3498db;
                border: 1px solid #4a6278;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0px; }
            QCalendarWidget {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #4a6278;
                border-radius: 8px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #1a2a38;
                border-radius: 8px;
                min-height: 36px;
            }
            QCalendarWidget QToolButton {
                background-color: transparent;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #3498db;
            }
            QCalendarWidget QSpinBox {
                background-color: #34495e;
                color: white;
                border: 1px solid #4a6278;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 12px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #2c3e50;
                color: #ecf0f1;
                selection-background-color: #3498db;
                selection-color: white;
                alternate-background-color: #34495e;
                font-size: 12px;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #4a6278;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #34495e;
            }
        """)

        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1a3a4a, stop:1 #2c3e50);
                border-bottom: 1px solid #1a2a38;
            }
        """)
        header.setFixedHeight(80)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 14, 20, 14)
        h_lay.setSpacing(14)

        initials = "".join([p[0] for p in f"{a.ad} {a.soyad}".split()[:2]])
        av = QLabel(initials)
        av.setFixedSize(46, 46)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet("""
            background-color: #27ae60;
            border-radius: 23px;
            color: white; font-size: 15px; font-weight: bold;
        """)
        h_lay.addWidget(av)

        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        name_lbl = QLabel(f"{a.ad} {a.soyad}")
        name_lbl.setObjectName("baslik")
        sub_lbl = QLabel(f"Pozisyon: {a.pozisyon or '-'}  ·  Ücret Beklentisi: "
                         f"{a.ucret_beklenti:,.0f} ₺".replace(",", ".") if a.ucret_beklenti
                         else f"Pozisyon: {a.pozisyon or '-'}")
        sub_lbl.setObjectName("alt_baslik")
        name_col.addWidget(name_lbl)
        name_col.addWidget(sub_lbl)
        h_lay.addLayout(name_col)
        h_lay.addStretch()

        badge = QLabel("Uygun")
        badge.setStyleSheet("""
            background-color: rgba(39,174,96,0.2);
            color: #2ecc71;
            border: 1px solid rgba(39,174,96,0.4);
            border-radius: 10px;
            padding: 3px 12px;
            font-size: 11px; font-weight: bold;
        """)
        h_lay.addWidget(badge)
        lay.addWidget(header)

        form_container = QWidget()
        form_container.setStyleSheet("background: transparent;")
        form_lay = QVBoxLayout(form_container)
        form_lay.setContentsMargins(20, 18, 20, 10)
        form_lay.setSpacing(12)

        def field(label_text, widget):
            lbl = QLabel(label_text)
            lbl.setObjectName("field_lbl")
            vb = QVBoxLayout()
            vb.setSpacing(4)
            vb.addWidget(lbl)
            vb.addWidget(widget)
            return vb

        mevcut_siciller = [
            p.sicil_no for p in self.session.query(Personel).all()
            if p.sicil_no and p.sicil_no.isdigit()
        ]
        if mevcut_siciller:
            yeni_sicil = str(max(int(s) for s in mevcut_siciller) + 1)
        else:
            yeni_sicil = "1"

        sicil_input = QLineEdit()
        sicil_input.setText(yeni_sicil)
        sicil_input.setPlaceholderText("Örn: 0042")
        form_lay.addLayout(field("SİCİL NO", sicil_input))

        sube_cb = QComboBox()
        for s in self.session.query(Sube).all():
            sube_cb.addItem(s.ad, s.id)
        form_lay.addLayout(field("ŞUBE", sube_cb))

        gorev_cb = QComboBox()
        for g in self.session.query(Gorev).all():
            gorev_cb.addItem(g.ad, g.id)
        form_lay.addLayout(field("GÖREV", gorev_cb))

        row_lay = QHBoxLayout()
        row_lay.setSpacing(12)

        maas_input = QDoubleSpinBox()
        maas_input.setRange(0, 999999)
        maas_input.setSuffix(" ₺")
        maas_input.setDecimals(2)
        if a.ucret_beklenti:
            maas_input.setValue(a.ucret_beklenti)
        maas_vb = QVBoxLayout()
        maas_vb.setSpacing(4)
        maas_lbl = QLabel("MAAŞ")
        maas_lbl.setObjectName("field_lbl")
        maas_vb.addWidget(maas_lbl)
        maas_vb.addWidget(maas_input)
        row_lay.addLayout(maas_vb)

        ise_giris = TarihAlani()
        ise_giris.set_date(QDate.currentDate())
        giris_vb = QVBoxLayout()
        giris_vb.setSpacing(4)
        giris_lbl = QLabel("İŞE GİRİŞ TARİHİ")
        giris_lbl.setObjectName("field_lbl")
        giris_vb.addWidget(giris_lbl)
        giris_vb.addWidget(ise_giris)
        row_lay.addLayout(giris_vb)

        form_lay.addLayout(row_lay)
        lay.addWidget(form_container)
        lay.addStretch()

        btn_frame = QFrame()
        btn_frame.setStyleSheet("""
            QFrame {
                background-color: #243342;
                border-top: 1px solid #1a2a38;
            }
        """)
        btn_frame.setFixedHeight(62)
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setContentsMargins(20, 10, 20, 10)
        btn_lay.setSpacing(10)

        aktar_btn = QPushButton("  Personele Aktar")
        aktar_btn.setFixedHeight(40)
        aktar_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white; font-weight: bold;
                border-radius: 8px; font-size: 13px;
                border: none; padding: 0 20px;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)

        iptal_btn = QPushButton("İptal")
        iptal_btn.setFixedHeight(40)
        iptal_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #7f8c8d; font-weight: bold;
                border-radius: 8px; font-size: 13px;
                border: 1px solid #4a6278; padding: 0 20px;
            }
            QPushButton:hover { background-color: #34495e; color: white; }
        """)
        iptal_btn.clicked.connect(dialog.reject)

        btn_lay.addStretch()
        btn_lay.addWidget(aktar_btn)
        btn_lay.addWidget(iptal_btn)
        lay.addWidget(btn_frame)

        def _aktar():
            sicil = sicil_input.text().strip()
            if not sicil:
                ModernMesaj.uyari(dialog, "Sicil no zorunludur.")
                return
            if self.session.query(Personel).filter(Personel.sicil_no == sicil).first():
                ModernMesaj.uyari(dialog, "Bu sicil no zaten kayıtlı.")
                return
            try:
                qt_d = ise_giris.get_date()
                p = Personel(
                    sicil_no=sicil,
                    ad_soyad=f"{a.ad} {a.soyad}",
                    tc_no=a.tc_no,
                    telefon=a.telefon_cep1 or a.telefon_ev,
                    maas=maas_input.value(),
                    sube_id=sube_cb.currentData(),
                    gorev_id=gorev_cb.currentData(),
                    ise_baslama=datetime.date(qt_d.year(), qt_d.month(), qt_d.day()),
                    durum="Aktif",
                    aciklama=a.notlar,
                )
                self.session.add(p)
                a.durum = "İşe Alındı"
                self.session.commit()
                ModernMesaj.basari(dialog, f"{p.ad_soyad} personel listesine eklendi.")
                dialog.accept()
                self.load_data()
            except Exception as e:
                self.session.rollback()
                ModernMesaj.hata(dialog, str(e))

        aktar_btn.clicked.connect(_aktar)
        dialog.exec_()

    def _ise_alim_iptal(self, aday_id):
        a = self.session.get(BasvuruAday, aday_id)
        if not a:
            return

        if not ModernMesaj.soru(
            self,
            f"{a.ad} {a.soyad} adlı kişinin işe alımı iptal edilecek.\n\n"
            f"Personel listesinden silinecek ve başvuru durumu 'Uygun' olarak geri alınacak.\n\n"
            f"Emin misiniz?",
            "İşe Alımı İptal Et"
        ):
            return

        try:
            ad_soyad = f"{a.ad} {a.soyad}"
            personel = None

            if a.tc_no:
                personel = self.session.query(Personel).filter(
                    Personel.tc_no == a.tc_no
                ).first()

            if not personel:
                personel = self.session.query(Personel).filter(
                    Personel.ad_soyad == ad_soyad
                ).first()

            if personel:
                self.session.delete(personel)
            else:
                ModernMesaj.uyari(
                    self,
                    "Personel listesinde eşleşen kayıt bulunamadı.\n"
                    "Başvuru durumu 'Uygun' olarak güncelleniyor."
                )

            a.durum = "Uygun"
            self.session.commit()
            ModernMesaj.basari(self,
                f"{ad_soyad} personel listesinden silindi ve\nbaşvuru 'Uygun' durumuna getirildi.")
            self.load_data()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))

    def _excel_import(self):
        from ui.basvuru_dialog import BasvuruExcelImportDialog
        d = BasvuruExcelImportDialog(self.session, parent=self)
        d.exec_()
        self.load_data()

    def _toplu_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Excel Kaydet", "Basvuru_Listesi.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            adaylar = self.session.query(BasvuruAday).order_by(
                BasvuruAday.basvuru_tarihi.desc()).all()
            data = []
            for a in adaylar:
                data.append({
                    "Başvuru Tarihi": a.basvuru_tarihi.strftime("%d.%m.%Y") if a.basvuru_tarihi else "",
                    "Ad": a.ad, "Soyad": a.soyad,
                    "Pozisyon": a.pozisyon or "",
                    "Telefon": a.telefon_cep1 or a.telefon_ev or "",
                    "E-posta": a.eposta or "",
                    "Ücret Beklentisi": a.ucret_beklenti or "",
                    "Durum": a.durum or "",
                    "Notlar": a.notlar or "",
                })
            pd.DataFrame(data).to_excel(path, index=False)
            ModernMesaj.basari(self, "Liste Excel'e aktarıldı.")
        except Exception as e:
            ModernMesaj.hata(self, str(e))

    # ── YARDIMCI WİDGET'LAR ──────────────────────
    def _btn(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}; color: white;
                font-weight: bold; border-radius: 6px;
                font-size: 12px; padding: 0 12px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        return btn

    def _mini_btn(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(26)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}; color: white;
                font-weight: bold; border-radius: 4px;
                font-size: 10px; padding: 0 6px;
                border: none;
            }}
            QPushButton:hover {{ opacity: 0.85; }}
        """)
        return btn

    def _stat_card(self, baslik, deger, renk):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 10px;
                border-left: 4px solid {renk};
                border-top: 1px solid #dcdde1;
                border-right: 1px solid #dcdde1;
                border-bottom: 1px solid #dcdde1;
            }}
        """)
        card.setFixedHeight(70)
        vl = QVBoxLayout(card)
        vl.setContentsMargins(14, 8, 14, 8)
        vl.setSpacing(2)
        lbl = QLabel(baslik)
        lbl.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        val = QLabel(deger)
        val.setObjectName("val")
        val.setStyleSheet(f"color: {renk}; font-size: 22px; font-weight: bold;")
        vl.addWidget(lbl)
        vl.addWidget(val)
        return card