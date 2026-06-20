# ui/puantaj_page.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QComboBox, QLabel, QPushButton, QFrame,
    QHeaderView, QMessageBox, QFileDialog, QLineEdit, QDialog,
    QCheckBox, QScrollArea as QSA
)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal, QObject, QEvent, QSize
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QFontMetrics
from PyQt5.QtCore import QRectF
import calendar
import pandas as pd
import re
import datetime
from database import get_session
from models import Personel, Sube, Puantaj, Izin, IzinTuru, KullaniciSube
from ui.utils import ModernMesaj, make_frameless, get_config_path
import os
import json


# ==================== ÖZEL YUVARLAK TOOLTIP ====================
class ModernToolTip(QWidget):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = ModernToolTip()
        return cls._instance

    @classmethod
    def show_tip(cls, global_pos, text):
        tip = cls.instance()
        tip._text = text
        sz = tip.sizeHint()
        tip.resize(sz)
        x = global_pos.x() + 14
        y = global_pos.y() - sz.height() - 10
        tip.move(x, y)
        tip.show()
        tip.raise_()
        tip.update()

    @classmethod
    def hide_tip(cls):
        if cls._instance:
            cls._instance.hide()

    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._text = ""
        self._font = QFont("Arial", 10)
        self._font.setLetterSpacing(QFont.AbsoluteSpacing, 0.3)
        self._radius = 12
        self._pad_v = 12
        self._pad_h = 12
        self._accent_w = 3

    def sizeHint(self):
        fm = QFontMetrics(self._font)
        clean = self._text.replace("⚠️", "").replace("⚠", "").strip()
        lines = clean.split("\n")
        text_w = max(fm.horizontalAdvance(l.strip()) for l in lines)
        w = text_w + self._pad_h * 2 + self._accent_w + 30
        h = fm.lineSpacing() * len(lines) + self._pad_v * 2
        return QSize(max(w, 200), max(h, 40))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect().adjusted(1, 1, -1, -1))
        path = QPainterPath()
        path.addRoundedRect(r, self._radius, self._radius)
        painter.fillPath(path, QColor("#1a2a38"))
        painter.setPen(QPen(QColor("#2c4a5e"), 1))
        painter.drawPath(path)
        painter.setClipPath(path)
        accent_x = int(r.left()) + 1
        painter.setPen(QPen(QColor("#e67e22"), self._accent_w, Qt.SolidLine, Qt.FlatCap))
        painter.drawLine(accent_x, int(r.top()), accent_x, int(r.bottom()))
        painter.setClipping(False)
        painter.setFont(self._font)
        painter.setPen(QColor("#ecf0f1"))
        tx = int(r.left()) + self._accent_w + self._pad_h
        ty = int(r.top()) + self._pad_v
        tw = int(r.width()) - self._accent_w - self._pad_h * 2
        th = int(r.height()) - self._pad_v * 2
        from PyQt5.QtCore import QRect as _QRect
        painter.drawText(_QRect(tx, ty, tw, th),
                         Qt.AlignLeft | Qt.AlignVCenter, self._text)


class PuantajTooltipFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.ToolTip:
            table = obj.parent()
            item = table.itemAt(event.pos())
            if item and item.toolTip():
                ModernToolTip.show_tip(event.globalPos(), item.toolTip())
                return True
            else:
                ModernToolTip.hide_tip()
        elif event.type() in (QEvent.Leave, QEvent.MouseButtonPress, QEvent.Wheel):
            ModernToolTip.hide_tip()
        return False


# ==================== MODERN ÇOKLU SEÇİM BUTONU ====================
class MultiSelectFilter(QPushButton):
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
            for disp, oid in self._options:
                if oid in self._selected:
                    short = disp if len(disp) <= 12 else disp[:12] + "…"
                    self.setText(f"▾  {short}")
                    break
        else:
            self.setText(f"▾  {len(self._selected)} seçili")

    def set_items(self, items):
        self._options = items
        self._selected = set()
        self._update_text()
        self.selectionChanged.emit()

    def set_selected_ids(self, ids):
        self._selected = set(ids)
        self._update_text()
        self.selectionChanged.emit()

    def get_selected_ids(self):
        return self._selected

    def get_selected_texts(self):
        return [disp for disp, oid in self._options if oid in self._selected]

    def clear_selection(self):
        self._selected = set()
        self._update_text()
        self.selectionChanged.emit()

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
        for disp, oid in self._options:
            chk = QCheckBox(disp)
            chk.setChecked(oid in self._selected)
            inner_lay.addWidget(chk)
            self._checkboxes.append((oid, chk))
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
        self._selected = {oid for oid, chk in self._checkboxes if chk.isChecked()}
        self._update_text()
        if self._popup:
            self._popup.close()
            self._popup = None
        self.selectionChanged.emit()


class SubeSelectDialog(QDialog):
    def __init__(self, subeler, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setWindowTitle("Excel Veri Aktarımı")
        self.setFixedSize(420, 260)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            QDialog { background-color: transparent; }
            QLabel { background: transparent; color: #ecf0f1; }
            QComboBox {
                background-color: #34495e;
                border: 1px solid #4a6278;
                border-radius: 8px;
                color: white;
                padding: 8px 12px;
                font-size: 13px;
                min-height: 22px;
            }
            QComboBox:focus { border-color: #e67e22; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #34495e;
                color: white;
                selection-background-color: #e67e22;
                selection-color: white;
            }
            QPushButton {
                font-weight: bold;
                border-radius: 6px;
                border: none;
                padding: 8px 16px;
                color: white;
            }
            QPushButton#cancelBtn {
                background: transparent;
                border: 1px solid #4a6278;
                color: #bdc3c7;
            }
            QPushButton#cancelBtn:hover {
                background: #34495e;
                color: white;
            }
            QPushButton#okBtn {
                background: #e67e22;
            }
            QPushButton#okBtn:hover {
                background: #d35400;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("QFrame#outer{background:#2c3e50;border-radius:12px;border:1px solid #4a6278;}")
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        lay.addWidget(outer)

        hdr = QFrame()
        hdr.setFixedHeight(66)
        hdr.setStyleSheet("QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #ca6f1e,stop:1 #e67e22); }")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 18, 0); hdr_lay.setSpacing(12)
        ic = QLabel("📥"); ic.setFixedSize(42, 42); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.2); border-radius:21px; font-size:20px; color:white;")
        ttl = QLabel("Excel Veri Aktarımı")
        ttl.setStyleSheet("color:white; font-size:15px; font-weight:bold; background:transparent;")
        sub_lbl = QLabel("Şube belirleyerek aktarımı başlatın")
        sub_lbl.setStyleSheet("color:rgba(255,255,255,0.7); font-size:11px; background:transparent;")
        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(ttl); col.addWidget(sub_lbl)
        hdr_lay.addWidget(ic); hdr_lay.addLayout(col)
        outer_lay.addWidget(hdr)
        body = QWidget(); body.setStyleSheet("background: #2c3e50;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(18, 14, 18, 10); body_lay.setSpacing(8)
        sube_lbl = QLabel("ŞUBE SEÇİN")
        sube_lbl.setStyleSheet("color:#7f8c8d; font-size:10px; font-weight:bold; letter-spacing:0.8px;")
        body_lay.addWidget(sube_lbl)
        self.sube_cb = QComboBox()
        for s in subeler:
            self.sube_cb.addItem(s.ad, s.id)
        body_lay.addWidget(self.sube_cb)
        outer_lay.addWidget(body)
        btn_frame = QFrame(); btn_frame.setFixedHeight(58)
        btn_frame.setStyleSheet("QFrame { background-color: #243342; border-top: 1px solid #1a2a38; }")
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setContentsMargins(16, 10, 16, 10); btn_lay.setSpacing(10)
        self.cancel_btn = QPushButton("Vazgeç")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.setFixedHeight(38)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn = QPushButton("✅  Aktarımı Başlat")
        self.ok_btn.setObjectName("okBtn")
        self.ok_btn.setFixedHeight(38)
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.clicked.connect(self.accept)
        btn_lay.addStretch()
        btn_lay.addWidget(self.cancel_btn)
        btn_lay.addWidget(self.ok_btn)
        outer_lay.addWidget(btn_frame)
        make_frameless(self)


# ==================== ANA PUANTAJ SAYFASI ====================
class PuantajPage(QWidget):
    def __init__(self, kullanici=None):
        super().__init__()
        self.kullanici = kullanici
        self.session = get_session()
        self.init_ui()
        self.original_colors = {}

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)
        self.setStyleSheet("background-color: #2c3e50;")

        # Kontrol paneli (3 satır)
        self.control_panel = QFrame()
        self.control_panel.setFixedHeight(160)
        self.control_panel.setObjectName("ControlPanel")
        self.control_panel.setStyleSheet("""
            QFrame#ControlPanel {
                background-color: #34495e;
                border: 1px solid #4a6278;
                border-radius: 12px;
            }
            QLabel {
                color: #bdc3c7;
                font-weight: bold;
                font-size: 11px;
                background: transparent;
            }
        """)

        control_lay = QVBoxLayout(self.control_panel)
        control_lay.setContentsMargins(20, 10, 20, 10)
        control_lay.setSpacing(10)

        # 1. SATIR: Personel arama
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        row1.addWidget(QLabel("Personel Ara:"))
        self.personel_search = QLineEdit()
        self.personel_search.setPlaceholderText("🔍 Ad, soyad veya sicil no girin...")
        self.personel_search.setFixedHeight(35)
        self.personel_search.setStyleSheet("""
            QLineEdit {
                border: 1px solid #3498db;
                border-radius: 6px;
                padding: 5px 10px;
                background-color: #2c3e50;
                color: white;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #e74c3c;
            }
        """)
        self.personel_search.textChanged.connect(self.puantaj_olustur)
        row1.addWidget(self.personel_search, 1)
        control_lay.addLayout(row1)

        # 2. SATIR: Şube, Ay, Yıl
        row2 = QHBoxLayout()
        row2.setSpacing(25)

        sube_grp = QVBoxLayout()
        sube_grp.setSpacing(4)
        sube_grp.addWidget(QLabel("ŞUBE SEÇİMİ"))
        self.sube_filter = MultiSelectFilter("Şube Seçiniz...")
        self.sube_filter.setFixedWidth(240)
        self.sube_filter.setFixedHeight(35)
        sube_items = [(s.ad, s.id) for s in self.session.query(Sube).all()]
        self.sube_filter.set_items(sube_items)
        self.sube_filter.selectionChanged.connect(self.puantaj_olustur)
        sube_grp.addWidget(self.sube_filter)
        row2.addLayout(sube_grp)

        ay_grp = QVBoxLayout()
        ay_grp.setSpacing(4)
        ay_grp.addWidget(QLabel("AY"))
        self.ay_cb = QComboBox()
        self.ay_cb.setStyleSheet("""
            QComboBox {
                border: 1px solid #4a6278;
                border-radius: 6px;
                padding: 5px;
                background-color: #2c3e50;
                color: white;
                font-size: 13px;
            }
            QComboBox:hover { border-color: #3498db; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView { background: #34495e; color: white; selection-background-color: #3498db; }
        """)
        self.ay_cb.setFixedSize(140, 35)
        self.ay_cb.addItems(["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                              "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])
        self.ay_cb.setCurrentIndex(QDate.currentDate().month() - 1)
        self.ay_cb.currentIndexChanged.connect(self.puantaj_olustur)
        ay_grp.addWidget(self.ay_cb)
        row2.addLayout(ay_grp)

        yil_grp = QVBoxLayout()
        yil_grp.setSpacing(4)
        yil_grp.addWidget(QLabel("YIL"))
        self.yil_cb = QComboBox()
        self.yil_cb.setStyleSheet("""
            QComboBox {
                border: 1px solid #4a6278;
                border-radius: 6px;
                padding: 5px;
                background-color: #2c3e50;
                color: white;
                font-size: 13px;
            }
            QComboBox:hover { border-color: #3498db; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView { background: #34495e; color: white; selection-background-color: #3498db; }
        """)
        self.yil_cb.setFixedSize(100, 35)
        for y in range(2024, 2035):
            self.yil_cb.addItem(str(y))
        self.yil_cb.setCurrentText(str(QDate.currentDate().year()))
        self.yil_cb.currentIndexChanged.connect(self.puantaj_olustur)
        yil_grp.addWidget(self.yil_cb)
        row2.addLayout(yil_grp)

        row2.addStretch()
        control_lay.addLayout(row2)

        # 3. SATIR: Butonlar
        row3 = QHBoxLayout()
        row3.setSpacing(10)
        self.import_btn = self.create_btn("📥 Veri Al", "#e67e22", self.excel_import)
        self.export_btn = self.create_btn("📤 Excel", "#1fb50b", self.excel_export)
        self.kaydet_btn = self.create_btn("💾 Kaydet", "#21d9c6", self.puantaj_kaydet)
        row3.addWidget(self.import_btn)
        row3.addWidget(self.export_btn)
        row3.addWidget(self.kaydet_btn)
        row3.addStretch()
        control_lay.addLayout(row3)

        self.main_layout.addWidget(self.control_panel)

        # Lejant
        lejant_frame = QFrame()
        lejant_frame.setFixedHeight(40)
        lejant_frame.setStyleSheet("background: #34495e; border-radius: 8px; border: 1px solid #4a6278;")
        lejant_layout = QHBoxLayout(lejant_frame)
        lejant_layout.setContentsMargins(10, 5, 10, 5)

        kodlar = [
            ("X", "Çalıştı (kesinti yok)", "#27ae60"),
            ("R", "Raporlu (kesinti)", "#e74c3c"),
            ("G", "Gelmedi (kesinti)", "#e67e22"),
            ("İ", "İzinli (kesinti yok)", "#3498db"),
            ("Ü", "Ücretsiz izin (kesinti)", "#9b59b6"),
            ("T", "Resmi Tatil (kesinti yok)", "#7f8c8d")
        ]

        for kod, aciklama, renk in kodlar:
            lbl = QLabel(f"<b>{kod}</b> : {aciklama}")
            lbl.setStyleSheet(f"color: {renk}; padding: 2px 8px; border-right: 1px solid rgba(255,255,255,0.1);")
            lejant_layout.addWidget(lbl)

        lejant_layout.addStretch()
        self.main_layout.addWidget(lejant_frame)

        # Tablo
        self.table = QTableWidget()
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #e0e0e0;
                border: 1px solid #dcdde1;
                color: #2c3e50;
                font-size: 12px;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                font-weight: bold;
                height: 40px;
                border: 1px solid #1a2a38;
            }
            QTableWidget::item:alternate {
                background-color: #f5f8fa;
            }
            QTableWidget QLineEdit {
                color: white;
                background-color: #34495e;
                selection-background-color: #2980b9;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 2px;
            }
        """)
        self.main_layout.addWidget(self.table)

        # Sütun genişliği ayarlanabilir + sağ tıkla kaydet/yükle
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_column_context_menu)

        self._tooltip_filter = PuantajTooltipFilter(self)
        self.table.viewport().installEventFilter(self._tooltip_filter)

        self.puantaj_olustur()

    def _widths_path(self):
        return get_config_path("puantaj_table_widths.json")

    def save_column_widths(self):
        widths = {}
        for i in range(self.table.columnCount()):
            widths[i] = self.table.columnWidth(i)
        try:
            with open(self._widths_path(), "w", encoding="utf-8") as f:
                json.dump(widths, f)
            ModernMesaj.basari(self, "Puantaj tablosu sütun genişlikleri kaydedildi.")
        except Exception as e:
            ModernMesaj.hata(self, f"Kaydedilemedi: {str(e)}")

    def load_column_widths(self):
        path = self._widths_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    widths = json.load(f)
                for i, w in widths.items():
                    idx = int(i)
                    if 0 <= idx < self.table.columnCount():
                        self.table.setColumnWidth(idx, int(w))
            except Exception:
                pass

    def show_column_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu
        menu = QMenu()
        save_action = menu.addAction("Sütun genişliklerini kaydet")
        save_action.triggered.connect(self.save_column_widths)
        menu.exec_(self.table.mapToGlobal(pos))

    def create_btn(self, text, color, func):
        btn = QPushButton(text)
        btn.setFixedSize(110, 38)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                border-radius: 8px;
                font-size: 12px;
                border: none;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        btn.clicked.connect(func)
        return btn

    def tr_lower(self, text):
        if not text:
            return ""
        text = str(text)
        text = text.replace('Ç', 'c').replace('Ğ', 'g').replace('İ', 'i').replace('I', 'ı').replace('Ö', 'o').replace('Ş', 's').replace('Ü', 'u')
        text = text.replace('ç', 'c').replace('ğ', 'g').replace('ı', 'i').replace('ö', 'o').replace('ş', 's').replace('ü', 'u')
        return text.lower()
    def puantaj_olustur(self):
        if getattr(self, '_building_puantaj', False):
            return
        self._building_puantaj = True
        try:
            yil = int(self.yil_cb.currentText())
            ay = self.ay_cb.currentIndex() + 1
            gun_sayisi = calendar.monthrange(yil, ay)[1]
            selected_ids = list(self.sube_filter.get_selected_ids())
            arama = self.tr_lower(self.personel_search.text().strip())
            arama = self.tr_lower(arama)  # Türkçe karakter normalize

            self.session.expire_all()
            ay_basi = datetime.date(yil, ay, 1)
            query = self.session.query(Personel).filter(
                Personel.durum.in_(["Aktif", "Pasif", "Ayrıldı"]),
                (Personel.isten_ayrilma == None) | (Personel.isten_ayrilma >= ay_basi)
            )
            if selected_ids:
                query = query.filter(Personel.sube_id.in_(selected_ids))

            if self.kullanici and not self.kullanici.admin:
                yetkili_sube_ids = [s.sube_id for s in self.kullanici.subeleri]
                if yetkili_sube_ids:
                    query = query.filter(Personel.sube_id.in_(yetkili_sube_ids))

            personeller = query.all()

            if arama:
                def uygun(p):
                    return (arama in self.tr_lower(p.ad_soyad) or 
                            (p.sicil_no and arama in self.tr_lower(p.sicil_no)))
                personeller = [p for p in personeller if uygun(p)]

            # ── Toplu sorgular: tüm personel için tek seferde ──
            personel_ids = [p.id for p in personeller]

            puantaj_map = {}
            ucretsiz_map = {}
            if personel_ids:
                puantaj_list = self.session.query(Puantaj).filter(
                    Puantaj.personel_id.in_(personel_ids),
                    Puantaj.yil == yil,
                    Puantaj.ay == ay
                ).all()
                puantaj_map = {p.personel_id: p for p in puantaj_list}

                ay_basi_dt = datetime.date(yil, ay, 1)
                ay_sonu_dt = datetime.date(yil, ay, gun_sayisi)
                ucretsiz_list = self.session.query(Izin).join(IzinTuru).filter(
                    Izin.personel_id.in_(personel_ids),
                    Izin.durum == "Onaylandı",
                    IzinTuru.ucretli_mi == False,
                    Izin.baslangic_tarihi <= ay_sonu_dt,
                    Izin.bitis_tarihi >= ay_basi_dt
                ).all()
                for izin in ucretsiz_list:
                    pid = izin.personel_id
                    ucretsiz_map.setdefault(pid, set())
                    gun = izin.baslangic_tarihi
                    while gun <= izin.bitis_tarihi:
                        if gun.year == yil and gun.month == ay:
                            ucretsiz_map[pid].add(gun.day)
                        gun += datetime.timedelta(days=1)

            self.table.setUpdatesEnabled(False)
            self.table.blockSignals(True)
            self.table.clearContents()
            self.table.setRowCount(0)
            self.table.setColumnCount(gun_sayisi + 1)

            headers = ["AD SOYAD"] + [str(i) for i in range(1, gun_sayisi + 1)]
            self.table.setHorizontalHeaderLabels(headers)

            for row, p in enumerate(personeller):
                self.table.insertRow(row)
                name_item = QTableWidgetItem(p.ad_soyad)
                name_item.setData(Qt.UserRole, p.id)
                name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if p.durum == "Pasif":
                    name_item.setBackground(QColor("#ffe6e6"))
                    name_item.setToolTip("⚠️ Pasif personel puantajı varsayılan olarak Gelmedi (G) sayılır")
                elif p.durum == "Ayrıldı":
                    name_item.setBackground(QColor("#e0e0e0"))
                    name_item.setToolTip("⚠️ Ayrılmış personel - Ayrıldığı günden sonraki alanlar boş bırakılırsa 'G' sayılır")
                self.table.setItem(row, 0, name_item)

                saved_p = puantaj_map.get(p.id)

                ayrilma_tarihi = p.isten_ayrilma
                ayrilma_gunu = ayrilma_tarihi.day if ayrilma_tarihi and ayrilma_tarihi.year == yil and ayrilma_tarihi.month == ay else None

                ucretsiz_gunler = ucretsiz_map.get(p.id, set())

                for col in range(1, gun_sayisi + 1):
                    db_val = getattr(saved_p, f"gun_{col}", "") if saved_p else ""

                    # DB'de değer yoksa ve onaylı ücretsiz izin günüyse otomatik "Ü" koy
                    izin_auto = False
                    if not db_val and col in ucretsiz_gunler:
                        db_val = "Ü"
                        izin_auto = True

                    item = QTableWidgetItem(str(db_val) if db_val else "")
                    item.setTextAlignment(Qt.AlignCenter)

                    if p.durum == "Ayrıldı" and ayrilma_gunu and col > ayrilma_gunu:
                        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                        item.setBackground(QColor("#555555"))
                        item.setForeground(QColor("#000000"))
                        item.setToolTip("Bu personel bu tarihten sonra ayrıldı. Boş bırakılırsa 'G' (Gelmedi) sayılır.")
                    else:
                        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                        if izin_auto:
                            item.setBackground(QColor("#d5aef8"))
                            item.setForeground(QColor("#4a235a"))
                            item.setToolTip("⚠️ Onaylı ücretsiz izin — İzin sayfasından otomatik aktarıldı. Elle değiştirilebilir.")
                        elif p.durum == "Pasif" and not db_val:
                            item.setForeground(QColor("#e67e22"))
                            item.setToolTip("⚠️ Pasif personel puantajı varsayılan olarak Gelmedi (G) sayılır")
                        if QDate(yil, ay, col).dayOfWeek() >= 6:
                            if not izin_auto:
                                item.setBackground(QColor("#ffe6e6"))
                                item.setForeground(QColor("#c0392b"))
                        else:
                            if not izin_auto:
                                item.setBackground(QColor("#ffffff"))
                                item.setForeground(QColor("#2c3e50"))
                    self.table.setItem(row, col, item)

            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
            self.table.setColumnWidth(0, 200)
            for i in range(1, gun_sayisi + 1):
                self.table.setColumnWidth(i, 40)

            # Kullanıcının kaydettiği genişlikleri uygula (varsa)
            self.load_column_widths()
        finally:
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)
            self._building_puantaj = False

    def normalize_isim(self, isim):
        if not isim:
            return ""
        isim = str(isim).strip().upper()
        isim = isim.replace('İ', 'I').replace('Ö', 'O').replace('Ü', 'U').replace('Ğ', 'G').replace('Ş', 'S').replace('Ç', 'C')
        isim = re.sub(r'\s+', ' ', isim)
        return isim

    def excel_import(self):
        subeler = self.session.query(Sube).all()
        dialog = SubeSelectDialog(subeler, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel (*.xlsx *.xls)")
        if not path:
            return
        try:
            df = pd.read_excel(path, header=None, dtype=str)
            found_count = 0
            not_found = []
            personel_map = {}
            for r in range(self.table.rowCount()):
                item = self.table.item(r, 0)
                if item:
                    orijinal_isim = item.text()
                    normalized = self.normalize_isim(orijinal_isim)
                    personel_map[normalized] = r
            for index, row_data in df.iterrows():
                row_list = row_data.tolist()
                matched = False
                for cell in row_list[:5]:
                    if pd.isna(cell):
                        continue
                    excel_isim = str(cell).strip()
                    if not excel_isim:
                        continue
                    normalized_excel = self.normalize_isim(excel_isim)
                    if normalized_excel in personel_map:
                        satir_no = personel_map[normalized_excel]
                        data_start = row_list.index(cell) + 1
                        col_idx = 1
                        for val in row_list[data_start:]:
                            if col_idx >= self.table.columnCount():
                                break
                            if pd.notna(val):
                                deger = str(val).strip().upper()
                                if deger in ("X", "R", "G", "İ", "Ü", "T"):
                                    self.table.setItem(satir_no, col_idx, QTableWidgetItem(deger))
                                else:
                                    self.table.setItem(satir_no, col_idx, QTableWidgetItem(""))
                            col_idx += 1
                        found_count += 1
                        matched = True
                        break
                if not matched:
                    for cell in row_list[:3]:
                        if pd.notna(cell):
                            not_found.append(str(cell).strip())
                            break
            if found_count > 0:
                msg = f"{found_count} personelin verisi aktarıldı. Kaydetmeyi unutmayın."
                if not_found:
                    msg += f"\n\nEşleşmeyen {len(not_found)} satır var. Örnek: {', '.join(not_found[:5])}"
                ModernMesaj.basari(self, msg)
            else:
                ModernMesaj.uyari(self, "Excel'deki isimler ile tablodaki isimler eşleşmedi.\n"
                    f"Örnek eşleşmeyenler: {', '.join(not_found[:5])}")
        except Exception as e:
            ModernMesaj.hata(self, f"Yükleme hatası: {str(e)}")
            import traceback
            traceback.print_exc()

    def excel_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Excel Kaydet", f"Puantaj_{self.ay_cb.currentText()}.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            writer = pd.ExcelWriter(path, engine='xlsxwriter')
            workbook = writer.book
            worksheet = workbook.add_worksheet('Puantaj')
            title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
            info_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1, 'align': 'center'})
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#2f3640', 'font_color': 'white', 'border': 1, 'align': 'center'})
            cell_fmt = workbook.add_format({'border': 1, 'align': 'center'})
            col_count = self.table.columnCount()
            secili_sube_isimleri = self.sube_filter.get_selected_texts()
            sube_bilgisi = ", ".join(secili_sube_isimleri) if secili_sube_isimleri else "TÜM ŞUBELER"
            worksheet.merge_range(0, 0, 1, col_count - 1, f"{self.ay_cb.currentText().upper()} {self.yil_cb.currentText()} PUANTAJ CETVELİ", title_fmt)
            worksheet.merge_range(2, 0, 2, col_count - 1, f"ŞUBE: {sube_bilgisi}", info_fmt)
            for col in range(col_count):
                worksheet.write(4, col, self.table.horizontalHeaderItem(col).text(), header_fmt)
            for r in range(self.table.rowCount()):
                for c in range(col_count):
                    item = self.table.item(r, c)
                    if item:
                        val = item.text().upper()
                    else:
                        val = ""
                    worksheet.write(r + 5, c, val, cell_fmt)
            worksheet.set_column(0, 0, 30)
            writer.close()
            ModernMesaj.basari(self, "Excel dosyası oluşturuldu.")
        except Exception as e:
            ModernMesaj.hata(self, str(e))

    def puantaj_kaydet(self):
        yil = int(self.yil_cb.currentText())
        ay = self.ay_cb.currentIndex() + 1
        try:
            for r in range(self.table.rowCount()):
                p_id = self.table.item(r, 0).data(Qt.UserRole)
                p_record = self.session.query(Puantaj).filter(
                    Puantaj.personel_id == p_id,
                    Puantaj.yil == yil,
                    Puantaj.ay == ay
                ).first()
                if not p_record:
                    p_record = Puantaj(personel_id=p_id, yil=yil, ay=ay)
                    self.session.add(p_record)

                personel = self.session.get(Personel, p_id)
                ayrilma_tarihi = personel.isten_ayrilma
                ayrilma_gunu = None
                if ayrilma_tarihi and ayrilma_tarihi.year == yil and ayrilma_tarihi.month == ay:
                    ayrilma_gunu = ayrilma_tarihi.day

                for c in range(1, self.table.columnCount()):
                    item = self.table.item(r, c)
                    if item:
                        val = item.text().upper()
                    else:
                        val = ""

                    if personel.durum == "Ayrıldı" and ayrilma_gunu and c > ayrilma_gunu and val == "":
                        val = "G"

                    if personel and personel.durum == "Pasif" and val == "":
                        val = "G"

                    setattr(p_record, f"gun_{c}", val)
            self.session.commit()
            ModernMesaj.basari(self, "Veriler kaydedildi.")
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))