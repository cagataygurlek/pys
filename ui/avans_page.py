# ui/avans_page.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QFrame,
    QHeaderView, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDateEdit, QComboBox, QTextEdit,
    QFileDialog, QCompleter, QTabWidget, QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt, QDate, QStringListModel
from PyQt5.QtGui import QColor, QFont
from database import get_session
from models import Personel, Avans, KasaAcigi, SigaraAcigi, KullaniciSube
from sqlalchemy import func
from ui.utils import ModernMesaj, TarihAlani, ModernTarihSecici, make_frameless, get_config_path
from ui.widgets import ToggleSwitch
import datetime
import pandas as pd
import os
import re
import calendar
import json

# PDF için gerekli importlar
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Font ayarı
try:
    arial_path = "C:/Windows/Fonts/arial.ttf"
    if os.path.exists(arial_path):
        pdfmetrics.registerFont(TTFont('Arial', arial_path))
        font_name = 'Arial'
    else:
        font_name = 'Helvetica'
except:
    font_name = 'Helvetica'


class CustomLineEdit(QLineEdit):
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()


class AvansPage(QWidget):
    def __init__(self, kullanici=None):
        super().__init__()
        self.kullanici = kullanici
        self.session = get_session()
        self.init_ui()
        self.current_tab = 0
        self._yetki_uygula()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        self.setStyleSheet("background-color: #2c3e50;")

        # ========== ÜST PANEL ==========
        top_panel = QFrame()
        top_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #34495e,stop:1 #2c3e50);
                border-radius: 12px;
                border: 1px solid #4a6278;
            }
        """)
        top_panel.setFixedHeight(120)
        top_lay = QVBoxLayout(top_panel)
        top_lay.setContentsMargins(16, 10, 16, 10)
        top_lay.setSpacing(8)

        cb_style = """
            QComboBox {
                background: #2c3e50; color: white;
                border: 1px solid #4a6278; border-radius: 6px;
                padding: 5px 10px; font-size: 12px; min-width: 100px;
            }
            QComboBox:focus { border-color: #3498db; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #2c3e50; color: white;
                selection-background-color: #3498db;
            }
        """
        lbl_style = "color: #bdc3c7; font-size: 11px; font-weight: bold; background: transparent;"
        search_style = """
            QLineEdit {
                border: 1px solid #4a6278; border-radius: 6px;
                padding-left: 10px; background: #2c3e50;
                color: white; font-size: 12px;
            }
            QLineEdit:focus { border-color: #3498db; }
        """

        # Filtre satırı
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.personel_search = QLineEdit()
        self.personel_search.setPlaceholderText("🔍 Personel ara (isim, sicil veya TC)...")
        self.personel_search.setFixedHeight(34)
        self.personel_search.setStyleSheet(search_style)
        self.personel_search.textChanged.connect(self.load_data)

        lbl_personel = QLabel("Personel:")
        lbl_personel.setStyleSheet(lbl_style)

        self.ay_cb = QComboBox()
        self.ay_cb.addItem("Tüm Zamanlar", 0)
        aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                 "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        for i, ay in enumerate(aylar, 1):
            self.ay_cb.addItem(ay, i)
        self.ay_cb.setCurrentIndex(QDate.currentDate().month())
        self.ay_cb.setStyleSheet(cb_style)
        self.ay_cb.currentIndexChanged.connect(self.load_data)

        self.yil_cb = QComboBox()
        self.yil_cb.addItem("Tüm Yıllar", 0)
        for y in range(2020, 2035):
            self.yil_cb.addItem(str(y), y)
        self.yil_cb.setCurrentText(str(QDate.currentDate().year()))
        self.yil_cb.setStyleSheet(cb_style)
        self.yil_cb.currentIndexChanged.connect(self.load_data)

        lbl_ay = QLabel("Ay:")
        lbl_ay.setStyleSheet(lbl_style)
        lbl_yil = QLabel("Yıl:")
        lbl_yil.setStyleSheet(lbl_style)

        filter_layout.addWidget(lbl_personel)
        filter_layout.addWidget(self.personel_search, 1)
        filter_layout.addWidget(lbl_ay)
        filter_layout.addWidget(self.ay_cb)
        filter_layout.addWidget(lbl_yil)
        filter_layout.addWidget(self.yil_cb)
        filter_layout.addStretch()
        top_lay.addLayout(filter_layout)

        # Butonlar
        btn_row1 = QHBoxLayout()
        self.ekle_btn = self.create_btn("➕ Yeni Kayıt", "#27ae60", self.yeni_kayit)
        self.duzenle_btn = self.create_btn("✏️ Düzenle", "#2980b9", self.duzenle_kayit)
        self.sil_btn = self.create_btn("🗑️ Sil", "#e74c3c", self.sil_kayit)
        btn_row1.addWidget(self.ekle_btn)
        btn_row1.addWidget(self.duzenle_btn)
        btn_row1.addWidget(self.sil_btn)
        btn_row1.addStretch()
        top_lay.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self.excel_export_btn = self.create_btn("📥 Excel Aktar", "#8e44ad", self.excel_aktar)
        self.excel_import_btn = self.create_btn("📤 Excel'den Al", "#f39c12", self.excel_import)
        self.template_btn = self.create_btn("📄 Şablon İndir", "#7f8c8d", self.download_template)
        self.pdf_btn = self.create_btn("📑 PDF Aktar", "#e67e22", self.pdf_aktar)
        btn_row2.addWidget(self.excel_export_btn)
        btn_row2.addWidget(self.excel_import_btn)
        btn_row2.addWidget(self.template_btn)
        btn_row2.addWidget(self.pdf_btn)
        btn_row2.addStretch()
        top_lay.addLayout(btn_row2)

        layout.addWidget(top_panel)

        # ========== SEKMELER ==========
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #4a6278;
                border-radius: 8px;
                background: #2c3e50;
            }
            QTabBar::tab {
                background: #34495e;
                border: 1px solid #4a6278;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 10px 22px;
                margin-right: 2px;
                font-weight: bold;
                color: #bdc3c7;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background: #2c3e50;
                border-bottom: 2px solid #3498db;
                color: #3498db;
            }
            QTabBar::tab:hover {
                background: #3d566e;
                color: white;
            }
        """)

        self.avans_table = QTableWidget()
        self.avans_table.setColumnCount(6)
        self.avans_table.setHorizontalHeaderLabels(["ID", "Personel", "Tarih", "Tutar", "Açıklama", "İşlem"])
        self.avans_table.setColumnHidden(0, True)
        self.avans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.avans_table.horizontalHeader().setStretchLastSection(True)
        self.avans_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.avans_table.setColumnWidth(5, 90)
        self.avans_table.horizontalHeader().setSectionsMovable(True)
        self.avans_table.horizontalHeader().sectionMoved.connect(lambda: self._auto_save_layout(self.avans_table, "avans"))
        self.avans_table.horizontalHeader().sectionResized.connect(lambda: self._auto_save_layout(self.avans_table, "avans"))
        self.avans_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.avans_table.setStyleSheet(self.get_table_style())
        self.avans_table.itemDoubleClicked.connect(self.duzenle_kayit)

        self.kasa_table = QTableWidget()
        self.kasa_table.setColumnCount(6)
        self.kasa_table.setHorizontalHeaderLabels(["ID", "Personel", "Tarih", "Tutar", "Açıklama", "İşlem"])
        self.kasa_table.setColumnHidden(0, True)
        self.kasa_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.kasa_table.horizontalHeader().setStretchLastSection(True)
        self.kasa_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.kasa_table.setColumnWidth(5, 90)
        self.kasa_table.horizontalHeader().setSectionsMovable(True)
        self.kasa_table.horizontalHeader().sectionMoved.connect(lambda: self._auto_save_layout(self.kasa_table, "kasa"))
        self.kasa_table.horizontalHeader().sectionResized.connect(lambda: self._auto_save_layout(self.kasa_table, "kasa"))
        self.kasa_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.kasa_table.setStyleSheet(self.get_table_style())
        self.kasa_table.itemDoubleClicked.connect(self.duzenle_kayit)

        self.sigara_table = QTableWidget()
        self.sigara_table.setColumnCount(6)
        self.sigara_table.setHorizontalHeaderLabels(["ID", "Personel", "Tarih", "Tutar", "Açıklama", "İşlem"])
        self.sigara_table.setColumnHidden(0, True)
        self.sigara_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.sigara_table.horizontalHeader().setStretchLastSection(True)
        self.sigara_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.sigara_table.setColumnWidth(5, 90)
        self.sigara_table.horizontalHeader().setSectionsMovable(True)
        self.sigara_table.horizontalHeader().sectionMoved.connect(lambda: self._auto_save_layout(self.sigara_table, "sigara"))
        self.sigara_table.horizontalHeader().sectionResized.connect(lambda: self._auto_save_layout(self.sigara_table, "sigara"))
        self.sigara_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sigara_table.setStyleSheet(self.get_table_style())
        self.sigara_table.itemDoubleClicked.connect(self.duzenle_kayit)

        self.tum_avans_table = QTableWidget()
        self.tum_avans_table.setColumnCount(3)
        self.tum_avans_table.setHorizontalHeaderLabels(["Personel ID", "Personel", "Toplam Avans"])
        self.tum_avans_table.setColumnHidden(0, True)
        self.tum_avans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tum_avans_table.horizontalHeader().setStretchLastSection(True)
        self.tum_avans_table.verticalHeader().setVisible(False)
        self.tum_avans_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tum_avans_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tum_avans_table.setStyleSheet(self.get_table_style())
        self.tum_avans_table.itemDoubleClicked.connect(self.tum_avans_detay)

        self.tabs.addTab(self.avans_table, "💸 Avans")
        self.tabs.addTab(self.kasa_table, "💰 Kasa Açığı")
        self.tabs.addTab(self.sigara_table, "🚬 Sigara Açığı")
        self.tabs.addTab(self.tum_avans_table, "📋 Tüm Avanslar")
        self.tabs.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self.tabs)

        # Sağ tık menüsü: aktif tablonun sütun genişliklerini kaydet
        for t in [self.avans_table, self.kasa_table, self.sigara_table, self.tum_avans_table]:
            t.setContextMenuPolicy(Qt.CustomContextMenu)
            t.customContextMenuRequested.connect(lambda pos, tab=t: self.show_column_context_menu(tab, pos))
        self.load_all_column_widths()

    def _yetki_uygula(self):
        if not self.kullanici or self.kullanici.admin:
            return
        yetkili = {y.modul_adi for y in self.kullanici.yetkileri}
        if "avans_ekle" not in yetkili:
            self.ekle_btn.setVisible(False)
        if "avans_duzenle" not in yetkili:
            self.duzenle_btn.setVisible(False)
            self.sil_btn.setVisible(False)
        yetkili_sube_ids = {s.sube_id for s in self.kullanici.subeleri}
        self._yetkili_sube_ids = yetkili_sube_ids

    def _yetkili_mi(self, yetki):
        if not self.kullanici or self.kullanici.admin:
            return True
        yetkili = {y.modul_adi for y in self.kullanici.yetkileri}
        return yetki in yetkili

    def _auto_save_layout(self, table, key, *args):
        widths = {}
        order = []
        hdr = table.horizontalHeader()
        for logical in range(table.columnCount()):
            widths[str(logical)] = table.columnWidth(logical)
        for visual in range(table.columnCount()):
            order.append(hdr.logicalIndex(visual))
        try:
            with open(self._widths_path(key), "w", encoding="utf-8") as f:
                json.dump({"widths": widths, "order": order}, f)
        except Exception:
            pass

    def _widths_path(self, key):
        return get_config_path(f"avans_{key}_table_widths.json")

    def save_column_widths(self, table, key):
        widths = {}
        for i in range(table.columnCount()):
            widths[i] = table.columnWidth(i)
        try:
            with open(self._widths_path(key), "w", encoding="utf-8") as f:
                json.dump(widths, f)
            ModernMesaj.basari(self, "Sütun genişlikleri kaydedildi.")
        except Exception as e:
            ModernMesaj.hata(self, f"Kaydedilemedi: {str(e)}")

    def load_column_widths(self, table, key):
        path = self._widths_path(key)
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "widths" not in data:
                for i, w in data.items():
                    table.setColumnWidth(int(i), int(w))
                return
            widths = data.get("widths", {})
            order = data.get("order", [])
            for i, w in widths.items():
                table.setColumnWidth(int(i), int(w))
            hdr = table.horizontalHeader()
            for visual, logical in enumerate(order):
                cur = hdr.logicalIndex(visual)
                if cur != logical:
                    hdr.moveSection(hdr.visualIndex(logical), visual)
        except Exception:
            pass

    def load_all_column_widths(self):
        self.load_column_widths(self.avans_table, "avans")
        self.load_column_widths(self.kasa_table, "kasa")
        self.load_column_widths(self.sigara_table, "sigara")
        self.load_column_widths(self.tum_avans_table, "tum")

    def show_column_context_menu(self, table, pos):
        from PyQt5.QtWidgets import QMenu
        key_map = {
            self.avans_table: "avans",
            self.kasa_table: "kasa",
            self.sigara_table: "sigara",
            self.tum_avans_table: "tum",
        }
        key = key_map.get(table, "avans")
        menu = QMenu()
        save_action = menu.addAction("Sütun genişliklerini kaydet")
        save_action.triggered.connect(lambda: self.save_column_widths(table, key))
        menu.exec_(table.mapToGlobal(pos))

    def get_table_style(self):
        return """
            QTableWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #dcdde1;
                gridline-color: #e0e0e0;
                color: #2c3e50;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
            QTableWidget::item {
                padding: 8px;
                color: #2c3e50;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QTableWidget::item:alternate {
                background-color: #f5f8fa;
            }
        """

    def create_btn(self, text, color, func):
        btn = QPushButton(text)
        btn.setFixedSize(130, 35)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                font-size: 11px;
                border: none;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        btn.clicked.connect(func)
        return btn

    def on_tab_changed(self, index):
        self.current_tab = index
        if index == 3:
            self.load_tum_avanslar()
        else:
            self.load_data()

    def get_current_table(self):
        if self.current_tab == 0:
            return self.avans_table, Avans, "avans"
        elif self.current_tab == 1:
            return self.kasa_table, KasaAcigi, "kasa"
        elif self.current_tab == 2:
            return self.sigara_table, SigaraAcigi, "sigara"
        else:
            return self.avans_table, Avans, "avans"

    def load_tum_avanslar(self):
        self.tum_avans_table.setRowCount(0)
        try:
            sonuclar = self.session.query(
                Personel.id,
                Personel.ad_soyad,
                Personel.sicil_no,
                func.sum(Avans.tutar)
            ).join(Avans, Avans.personel_id == Personel.id).group_by(
                Personel.id
            ).order_by(Personel.ad_soyad).all()
            for p_id, ad_soyad, sicil, toplam in sonuclar:
                row = self.tum_avans_table.rowCount()
                self.tum_avans_table.insertRow(row)
                id_item = QTableWidgetItem(str(p_id))
                self.tum_avans_table.setItem(row, 0, id_item)
                isim_item = QTableWidgetItem(f"{ad_soyad} ({sicil or '-'})")
                isim_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.tum_avans_table.setItem(row, 1, isim_item)
                tutar_item = QTableWidgetItem(f"{toplam:,.2f} ₺".replace(",", "."))
                tutar_item.setTextAlignment(Qt.AlignCenter)
                tutar_item.setForeground(QColor("#27ae60"))
                font = QFont(); font.setBold(True)
                tutar_item.setFont(font)
                self.tum_avans_table.setItem(row, 2, tutar_item)
        except Exception as e:
            ModernMesaj.hata(self, str(e))

    def tum_avans_detay(self, item):
        row = item.row()
        p_id_item = self.tum_avans_table.item(row, 0)
        isim_item = self.tum_avans_table.item(row, 1)
        if not p_id_item:
            return
        p_id = int(p_id_item.text())
        personel_ad = isim_item.text() if isim_item else ""
        avanslar = self.session.query(Avans).filter(
            Avans.personel_id == p_id
        ).order_by(Avans.tarih.desc()).all()
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Avans Geçmişi — {personel_ad}")
        dialog.setFixedSize(550, 400)
        dialog.setStyleSheet("background-color: #2c3e50;")
        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        baslik = QLabel(f"  {personel_ad} — Avans Geçmişi")
        baslik.setStyleSheet("color: white; font-size: 14px; font-weight: bold; background: transparent;")
        lay.addWidget(baslik)
        tablo = QTableWidget()
        tablo.setColumnCount(3)
        tablo.setHorizontalHeaderLabels(["Tarih", "Tutar", "Açıklama"])
        tablo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tablo.verticalHeader().setVisible(False)
        tablo.setEditTriggers(QTableWidget.NoEditTriggers)
        tablo.setStyleSheet("""
            QTableWidget { background: #34495e; border: none; color: white; gridline-color: rgba(255,255,255,0.1); }
            QHeaderView::section { background: #1a2a38; color: #bdc3c7; font-weight: bold; padding: 6px; border: none; }
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background: #3498db; }
        """)
        toplam = 0
        for a in avanslar:
            r = tablo.rowCount()
            tablo.insertRow(r)
            tablo.setItem(r, 0, QTableWidgetItem(a.tarih.strftime("%d.%m.%Y")))
            tutar_i = QTableWidgetItem(f"{a.tutar:,.2f} ₺".replace(",", "."))
            tutar_i.setForeground(QColor("#2ecc71"))
            tutar_i.setTextAlignment(Qt.AlignCenter)
            tablo.setItem(r, 1, tutar_i)
            tablo.setItem(r, 2, QTableWidgetItem(a.aciklama or ""))
            toplam += a.tutar
        lay.addWidget(tablo)
        toplam_lbl = QLabel(f"  Toplam: {toplam:,.2f} ₺".replace(",", "."))
        toplam_lbl.setStyleSheet("color: #2ecc71; font-size: 13px; font-weight: bold; background: transparent;")
        lay.addWidget(toplam_lbl)
        kapat_btn = QPushButton("Kapat")
        kapat_btn.setFixedHeight(36)
        kapat_btn.setStyleSheet("background: #34495e; color: white; border-radius: 6px; border: 1px solid #4a6278;")
        kapat_btn.clicked.connect(dialog.accept)
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        btn_lay.addWidget(kapat_btn)
        lay.addLayout(btn_lay)
        dialog.exec_()

    def tr_lower(self, text):
        if not text:
            return ""
        return str(text).replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'ğ').replace('Ü', 'ü').replace('Ş', 'ş').replace('Ö', 'ö').replace('Ç', 'ç').lower()

    def load_data(self):
        try:
            table, model, _ = self.get_current_table()
            table.setRowCount(0)
            table.setColumnWidth(5, 100)
            query = self.session.query(model).join(Personel)
            ay = self.ay_cb.currentData()
            yil = self.yil_cb.currentData()
            if ay and yil:
                ilk_gun = datetime.date(yil, ay, 1)
                son_gun = datetime.date(yil, ay, calendar.monthrange(yil, ay)[1])
                query = query.filter(model.tarih >= ilk_gun, model.tarih <= son_gun)
            elif yil:
                query = query.filter(model.tarih >= datetime.date(yil, 1, 1),
                                      model.tarih <= datetime.date(yil, 12, 31))
            kayitlar = query.order_by(model.tarih.desc()).all()

            yetkili_sube_ids = getattr(self, '_yetkili_sube_ids', None)
            if yetkili_sube_ids is not None and not (self.kullanici and self.kullanici.admin):
                kayitlar = [k for k in kayitlar if k.personel.sube_id in yetkili_sube_ids]

            arama = self.personel_search.text().strip().lower()
            if arama:
                def uygun_mu(k):
                    ad = self.tr_lower(k.personel.ad_soyad)
                    sicil = self.tr_lower(k.personel.sicil_no or "")
                    tc = self.tr_lower(k.personel.tc_no or "")
                    return arama in ad or arama in sicil or arama in tc
                kayitlar = [k for k in kayitlar if uygun_mu(k)]
            for k in kayitlar:
                row = table.rowCount()
                table.insertRow(row)
                table.setRowHeight(row, 40)
                items = [
                    QTableWidgetItem(str(k.id)),
                    QTableWidgetItem(f"{k.personel.ad_soyad} ({k.personel.sicil_no})"),
                    QTableWidgetItem(k.tarih.strftime("%d.%m.%Y")),
                    QTableWidgetItem(f"{k.tutar:,.2f} ₺".replace(",", ".")),
                    QTableWidgetItem(k.aciklama or ""),
                    QTableWidgetItem("")
                ]
                for col, item in enumerate(items):
                    if col == 1:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignCenter)
                    if col == 3:
                        item.setForeground(QColor("#27ae60"))
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    table.setItem(row, col, item)
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2, 2, 2, 2)
                yetki_map = {"avans": "avans_duzenle", "kasa": "kasa_duzenle", "sigara": "sigara_duzenle"}
                _, _, tip = self.get_current_table()
                duz_yetkili = self._yetkili_mi(yetki_map.get(tip, ""))
                duzenle_btn = QPushButton("✏️")
                duzenle_btn.setFixedSize(28, 20)
                duzenle_btn.setStyleSheet("background: #3498db; color: white; border-radius: 4px; font-size: 14px; border: none;")
                duzenle_btn.clicked.connect(lambda _, x=k.id: self.duzenle_kayit_id(x))
                duzenle_btn.setVisible(duz_yetkili)
                sil_btn = QPushButton("🗑️")
                sil_btn.setFixedSize(28, 20)
                sil_btn.setStyleSheet("background: #e74c3c; color: white; border-radius: 4px; font-size: 14px; border: none;")
                sil_btn.clicked.connect(lambda _, x=k.id: self.sil_kayit_id(x))
                sil_btn.setVisible(duz_yetkili)
                btn_layout.addWidget(duzenle_btn)
                btn_layout.addWidget(sil_btn)
                btn_widget.setLayout(btn_layout)
                table.setCellWidget(row, 5, btn_widget)
        except Exception as e:
            ModernMesaj.hata(self, f"Veri yüklenirken hata oluştu:\n{str(e)}")

    def yeni_kayit(self):
        _, model, tip = self.get_current_table()
        yetki_map = {"avans": "avans_ekle", "kasa": "kasa_ekle", "sigara": "sigara_ekle"}
        if not self._yetkili_mi(yetki_map.get(tip, "")):
            ModernMesaj.uyari(self, f"{tip.title()} ekleme yetkiniz yok.")
            return
        dialog = KayitDialog(self.session, model, tip, kullanici=self.kullanici, parent=self)
        if dialog.exec_():
            self.load_data()

    def duzenle_kayit(self):
        table, model, tip = self.get_current_table()
        row = table.currentRow()
        if row < 0:
            return
        kayit_id = int(table.item(row, 0).text())
        self.duzenle_kayit_id(kayit_id)

    def duzenle_kayit_id(self, kayit_id):
        _, model, tip = self.get_current_table()
        yetki_map = {"avans": "avans_duzenle", "kasa": "kasa_duzenle", "sigara": "sigara_duzenle"}
        if not self._yetkili_mi(yetki_map.get(tip, "")):
            ModernMesaj.uyari(self, f"{tip.title()} düzenleme yetkiniz yok.")
            return
        kayit = self.session.get(model, kayit_id)
        dialog = KayitDialog(self.session, model, tip, kayit=kayit, kullanici=self.kullanici, parent=self)
        if dialog.exec_():
            self.load_data()

    def sil_kayit(self):
        table, model, tip = self.get_current_table()
        row = table.currentRow()
        if row < 0:
            ModernMesaj.uyari(self, "Lütfen silinecek kaydı seçin.")
            return
        kayit_id = int(table.item(row, 0).text())
        self.sil_kayit_id(kayit_id)

    def sil_kayit_id(self, kayit_id):
        _, model, tip = self.get_current_table()
        yetki_map = {"avans": "avans_duzenle", "kasa": "kasa_duzenle", "sigara": "sigara_duzenle"}
        if not self._yetkili_mi(yetki_map.get(tip, "")):
            ModernMesaj.uyari(self, f"{tip.title()} silme yetkiniz yok.")
            return
        kayit = self.session.get(model, kayit_id)
        if ModernMesaj.soru(self, f"{kayit.tutar:.2f} TL tutarındaki kayıt silinsin mi?"):
            self.session.delete(kayit)
            self.session.commit()
            self.load_data()

    def excel_aktar(self):
        table, _, tip = self.get_current_table()
        path, _ = QFileDialog.getSaveFileName(self, "Excel Aktar", f"{tip}_Listesi.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            data = []
            for r in range(table.rowCount()):
                row_data = []
                for c in range(5):
                    item = table.item(r, c)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            df = pd.DataFrame(data, columns=["ID", "Personel", "Tarih", "Tutar", "Açıklama"])
            df.to_excel(path, index=False)
            ModernMesaj.basari(self, "Excel dosyası oluşturuldu.")
        except Exception as e:
            ModernMesaj.hata(self, str(e))

    def excel_import(self):
        table, model, tip = self.get_current_table()
        path, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            df = pd.read_excel(path)
            eklenen = 0
            for _, row in df.iterrows():
                personel_str = str(row.get("Personel", "")).strip()
                if not personel_str or personel_str == "nan":
                    continue
                if "(" in personel_str and ")" in personel_str:
                    ad_soyad = personel_str.split("(")[0].strip()
                    sicil = personel_str.split("(")[1].replace(")", "").strip()
                    personel = self.session.query(Personel).filter_by(sicil_no=sicil).first()
                else:
                    personel = self.session.query(Personel).filter_by(ad_soyad=personel_str).first()
                if not personel:
                    continue
                tarih_str = row.get("Tarih")
                if pd.notna(tarih_str):
                    if isinstance(tarih_str, datetime.datetime):
                        tarih = tarih_str.date()
                    elif isinstance(tarih_str, pd.Timestamp):
                        tarih = tarih_str.date()
                    else:
                        try:
                            tarih = datetime.datetime.strptime(str(tarih_str), "%d.%m.%Y").date()
                        except:
                            tarih = datetime.date.today()
                else:
                    tarih = datetime.date.today()
                tutar_str = str(row.get("Tutar", "0")).replace("₺", "").replace("TL", "").strip()
                tutar_str = tutar_str.replace(".", "").replace(",", ".")
                try:
                    tutar = float(tutar_str)
                except:
                    tutar = 0.0
                aciklama = str(row.get("Açıklama", "")) if pd.notna(row.get("Açıklama")) else ""
                yeni = model(
                    personel_id=personel.id,
                    tarih=tarih,
                    tutar=tutar,
                    aciklama=aciklama
                )
                self.session.add(yeni)
                eklenen += 1
            self.session.commit()
            self.load_data()
            ModernMesaj.basari(self, f"{eklenen} kayıt eklendi.")
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))

    def download_template(self):
        _, _, tip = self.get_current_table()
        path, _ = QFileDialog.getSaveFileName(self, "Şablon Kaydet", f"{tip}_Sablonu.xlsx", "Excel (*.xlsx)")
        if path:
            df = pd.DataFrame(columns=["Personel", "Tarih", "Tutar", "Açıklama"])
            df.to_excel(path, index=False)
            ModernMesaj.basari(self, "Şablon oluşturuldu.")

    def pdf_aktar(self):
        table, _, tip = self.get_current_table()
        path, _ = QFileDialog.getSaveFileName(self, "PDF Kaydet", f"{tip}_Listesi.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            doc = SimpleDocTemplate(path)
            elements = []
            styles = getSampleStyleSheet()
            style_title = ParagraphStyle(
                name='Title',
                fontName=font_name,
                fontSize=14,
                leading=16,
                alignment=1
            )
            ay_text = self.ay_cb.currentText()
            yil_text = self.yil_cb.currentText()
            if ay_text == "Tüm Zamanlar":
                baslik = f"Tüm {tip} Kayıtları"
            else:
                baslik = f"{tip} - {ay_text} {yil_text}"
            elements.append(Paragraph(f"<b>{baslik}</b>", style_title))
            elements.append(Spacer(1, 0.2 * inch))
            data = [["Personel", "Tarih", "Tutar", "Açıklama"]]
            for r in range(table.rowCount()):
                row = []
                for c in [1, 2, 3, 4]:
                    item = table.item(r, c)
                    row.append(item.text() if item else "")
                data.append(row)
            pdf_table = Table(data, colWidths=[200, 80, 100, 200])
            pdf_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(pdf_table)
            doc.build(elements)
            ModernMesaj.basari(self, "PDF oluşturuldu.")
        except Exception as e:
            ModernMesaj.hata(self, f"PDF hatası: {str(e)}")


class KayitDialog(QDialog):
    def __init__(self, session, model, tip, kayit=None, kullanici=None, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.model = model
        self.tip = tip
        self.kayit = kayit
        self.kullanici = kullanici
        self.selected_personel_id = None
        basliklar = {"avans": "Avans", "kasa": "Kasa Açığı", "sigara": "Sigara Açığı"}
        ikon_renk = {"avans": ("#3498db","#1a5276"), "kasa": ("#e67e22","#784212"), "sigara": ("#8e44ad","#4a235a")}
        self.baslik_text = basliklar.get(tip, 'Kayıt')
        self.ana_renk, self.koyu_renk = ikon_renk.get(tip, ("#3498db","#1a5276"))
        eylem = "Düzenle" if kayit else "Yeni Kayıt"
        self.setWindowTitle(f"{self.baslik_text} — {eylem}")
        self.setFixedWidth(480)
        self.setStyleSheet(f"""
            QDialog {{ background-color: #2c3e50; }}
            QLabel {{ background: transparent; color: #bdc3c7; font-size: 11px; letter-spacing: 0.5px; }}
            QLineEdit, QTextEdit, QSpinBox {{
                background-color: #2c3e50; border: 1px solid #3498db;
                border-radius: 8px; color: white; font-size: 13px; padding: 8px 12px;
            }}
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {{ border-color: {self.ana_renk}; background-color: #1a2a38; }}
            QCheckBox {{ color: #ecf0f1; font-size: 13px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 2px solid #4a6278; background: #34495e; }}
            QCheckBox::indicator:checked {{ background: {self.ana_renk}; border-color: {self.ana_renk}; }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: 0px; }}
        """)
        self.init_ui()
        if kayit:
            self.load_kayit()
        make_frameless(self)

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet(f"QFrame {{ background-color: {self.koyu_renk}; border-top-left-radius: 0px; border-top-right-radius: 0px; }}")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(18, 0, 12, 0); h_lay.setSpacing(12)
        ikon_lbl = QLabel("₺" if self.tip == "avans" else ("💰" if self.tip == "kasa" else "🚬"))
        ikon_lbl.setFixedSize(38, 38)
        ikon_lbl.setAlignment(Qt.AlignCenter)
        ikon_lbl.setStyleSheet(f"background-color: {self.ana_renk}; border-radius: 19px; color: white; font-size: 16px; font-weight: bold;")
        baslik_lbl = QLabel(f"{self.baslik_text} {'Düzenle' if self.kayit else 'Yeni Kayıt'}")
        baslik_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold; letter-spacing: 0px;")
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.08);color:#ecf0f1;font-size:16px;font-weight:bold;border:none;border-radius:13px;} QPushButton:hover{background:rgba(231,76,60,0.7);color:white;}")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        h_lay.addWidget(ikon_lbl); h_lay.addWidget(baslik_lbl); h_lay.addStretch(); h_lay.addWidget(close_btn)
        lay.addWidget(header)
        form_w = QWidget()
        form_w.setStyleSheet("background: transparent;")
        form_lay = QVBoxLayout(form_w)
        form_lay.setContentsMargins(20, 16, 20, 10)
        form_lay.setSpacing(12)
        def field(lbl_text, widget):
            lbl = QLabel(lbl_text)
            vb = QVBoxLayout(); vb.setSpacing(4)
            vb.addWidget(lbl); vb.addWidget(widget)
            return vb
        self.personel_edit = QLineEdit()
        self.personel_edit.setPlaceholderText("Personel adı yazın...")
        personeller = self.session.query(Personel).filter(Personel.durum == "Aktif")
        if self.kullanici and not self.kullanici.admin:
            yetkili_sube_ids = [s.sube_id for s in self.kullanici.subeleri]
            if yetkili_sube_ids:
                personeller = personeller.filter(Personel.sube_id.in_(yetkili_sube_ids))
        personeller = personeller.all()
        self.personel_list = [(f"{p.ad_soyad} ({p.sicil_no})", p.id) for p in personeller]

        # QCompleter Türkçe İ→i / I→ı dönüşümünü bilmez; manuel popup kullanıyoruz
        from PyQt5.QtWidgets import QListWidget
        self._popup = QListWidget(self)
        self._popup.setWindowFlags(Qt.ToolTip)
        self._popup.setStyleSheet("""
            QListWidget { background:#34495e; color:white; border:1px solid #3498db; font-size:12px; }
            QListWidget::item { padding:6px 10px; }
            QListWidget::item:selected { background:#3498db; color:white; }
            QListWidget::item:hover { background:#4a6278; }
        """)
        self._popup.setFocusPolicy(Qt.NoFocus)
        self._popup.hide()

        def _tr_lower(t):
            return str(t).replace('İ','i').replace('I','ı').replace('Ğ','ğ').replace('Ü','ü').replace('Ş','ş').replace('Ö','ö').replace('Ç','ç').lower()

        def _filtrele(text):
            self._popup.clear()
            if not text.strip():
                self._popup.hide(); return
            aranan = _tr_lower(text)
            eslesler = [d for d, _ in self.personel_list if aranan in _tr_lower(d)]
            if not eslesler:
                self._popup.hide(); return
            for d in eslesler[:20]:
                self._popup.addItem(d)
            pos = self.personel_edit.mapToGlobal(self.personel_edit.rect().bottomLeft())
            self._popup.move(pos)
            self._popup.setFixedWidth(self.personel_edit.width())
            self._popup.setFixedHeight(min(len(eslesler), 8) * 30 + 4)
            self._popup.show()

        def _popup_sec(item):
            self.personel_edit.blockSignals(True)
            self.personel_edit.setText(item.text())
            self.personel_edit.blockSignals(False)
            self.on_personel_selected(item.text())
            self._popup.hide()

        self._popup.itemClicked.connect(_popup_sec)
        self.personel_edit.textChanged.connect(_filtrele)

        orig_focus_out = self.personel_edit.focusOutEvent
        def _focus_out(e):
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(150, self._popup.hide)
            orig_focus_out(e)
        self.personel_edit.focusOutEvent = _focus_out

        form_lay.addLayout(field("PERSONEL", self.personel_edit))
        self.tarih = TarihAlani()
        self.tarih.set_date(QDate.currentDate())
        form_lay.addLayout(field("TARİH", self.tarih))
        tutar_row = QHBoxLayout(); tutar_row.setSpacing(8)
        self.tutar = CustomLineEdit()
        self.tutar.setPlaceholderText("Örn: 1250,50")
        tutar_row.addWidget(self.tutar, 2)
        if self.tip == "avans":
            self.taksit_cb = ToggleSwitch(width=50, height=24)
            self.taksit_cb.stateChanged.connect(self.taksit_changed)
            tutar_row.addWidget(self.taksit_cb)
            self.taksit_spin = QSpinBox()
            self.taksit_spin.setRange(2, 12); self.taksit_spin.setValue(3)
            self.taksit_spin.setSuffix(" ay"); self.taksit_spin.setEnabled(False)
            self.taksit_spin.setFixedWidth(80)
            tutar_row.addWidget(self.taksit_spin)
        tutar_lbl = QLabel("TUTAR"); tutar_vb = QVBoxLayout(); tutar_vb.setSpacing(4)
        tutar_vb.addWidget(tutar_lbl); tutar_vb.addLayout(tutar_row)
        form_lay.addLayout(tutar_vb)
        self.aciklama = QTextEdit()
        self.aciklama.setFixedHeight(70)
        self.aciklama.setPlaceholderText("Açıklama...")
        form_lay.addLayout(field("AÇIKLAMA", self.aciklama))
        lay.addWidget(form_w)
        lay.addStretch()
        btn_frame = QFrame()
        btn_frame.setFixedHeight(60)
        btn_frame.setStyleSheet("QFrame { background-color: #243342; border-top: 1px solid #1a2a38; }")
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setContentsMargins(20, 10, 20, 10); btn_lay.setSpacing(10)
        btn_lay.addStretch()
        self.kaydet_btn = QPushButton("  Kaydet")
        self.kaydet_btn.setFixedHeight(40)
        self.kaydet_btn.setStyleSheet(f"QPushButton {{ background-color: {self.ana_renk}; color: white; font-weight: bold; border-radius: 8px; border: none; padding: 0 20px; }} QPushButton:hover {{ background-color: {self.koyu_renk}; }}")
        self.kaydet_btn.clicked.connect(self.kaydet)
        self.iptal_btn = QPushButton("İptal")
        self.iptal_btn.setFixedHeight(40)
        self.iptal_btn.setStyleSheet("QPushButton { background-color: transparent; color: #7f8c8d; border: 1px solid #4a6278; border-radius: 8px; padding: 0 16px; } QPushButton:hover { background-color: #34495e; color: white; }")
        self.iptal_btn.clicked.connect(self.reject)
        btn_lay.addWidget(self.kaydet_btn); btn_lay.addWidget(self.iptal_btn)
        lay.addWidget(btn_frame)

    def taksit_changed(self, state):
        self.taksit_spin.setEnabled(state == Qt.Checked)

    def on_personel_selected(self, text):
        for display, pid in self.personel_list:
            if display == text:
                self.selected_personel_id = pid
                break

    def load_kayit(self):
        p = self.kayit.personel
        display = f"{p.ad_soyad} ({p.sicil_no})"
        self.personel_edit.setText(display)
        self.selected_personel_id = p.id
        self.tarih.set_pydate(self.kayit.tarih)
        self.tutar.setText(f"{self.kayit.tutar:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))
        self.aciklama.setPlainText(self.kayit.aciklama or "")
        if hasattr(self, 'taksit_cb'):
            self.taksit_cb.setChecked(False)

    def parse_tutar(self, metin):
        if not metin:
            return 0.0
        metin = metin.replace("₺", "").replace("TL", "").strip()
        metin = metin.replace(".", "")
        metin = metin.replace(",", ".")
        try:
            return float(metin)
        except:
            return 0.0

    def add_months(self, source_date, months):
        month = source_date.month - 1 + months
        year = source_date.year + month // 12
        month = month % 12 + 1
        day = min(source_date.day, calendar.monthrange(year, month)[1])
        return datetime.date(year, month, day)

    def kaydet(self):
        if self.selected_personel_id is None:
            ModernMesaj.uyari(self, "Lütfen geçerli bir personel seçin.")
            return
        try:
            tarih = self.tarih.get_pydate()
            toplam_tutar = self.parse_tutar(self.tutar.text())
            taksitli = self.taksit_cb.isChecked() if hasattr(self, 'taksit_cb') else False
            if taksitli:
                if self.tip != "avans":
                    ModernMesaj.uyari(self, "Taksitli özelliği sadece Avans için geçerlidir.")
                    return
                taksit_sayisi = self.taksit_spin.value()
                aylik_tutar = toplam_tutar / taksit_sayisi
                for i in range(taksit_sayisi):
                    yeni_tarih = self.add_months(tarih, i)
                    aciklama = f"{self.aciklama.toPlainText()} (Taksit {i+1}/{taksit_sayisi})".strip()
                    yeni = self.model(
                        personel_id=self.selected_personel_id,
                        tarih=yeni_tarih,
                        tutar=aylik_tutar,
                        aciklama=aciklama
                    )
                    self.session.add(yeni)
            else:
                if self.kayit:
                    k = self.kayit
                else:
                    k = self.model()
                    self.session.add(k)
                k.personel_id = self.selected_personel_id
                k.tarih = tarih
                k.tutar = toplam_tutar
                k.aciklama = self.aciklama.toPlainText()
            self.session.commit()
            self.accept()
        except Exception as e:
            ModernMesaj.hata(self, str(e))