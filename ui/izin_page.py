# ui/izin_page.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QComboBox, QLabel, QPushButton, QFrame, QLineEdit, QHeaderView,
    QDialog, QSpinBox, QTextEdit, QScrollArea, QListWidget, QListWidgetItem,
    QAbstractButton, QAbstractItemView, QDoubleSpinBox, QAbstractSpinBox,
    QCheckBox, QSizePolicy, QTabWidget
)
from PyQt5.QtGui import QFont
import os
import json
from PyQt5.QtCore import Qt, QDate, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QRectF
from PyQt5.QtGui import QColor, QPainter, QPainterPath

from database import get_session
from models import Izin, Personel, IzinTuru, YillikIzin, MaasOdeme, Bordro
from sqlalchemy import func

import datetime, calendar, re

from ui.utils import ModernMesaj, TarihAlani, tr_lower, get_config_path
from ui.izin_dialog import IzinDialog

class ToggleSwitch(QAbstractButton):
    stateChanged = pyqtSignal(int)

    def __init__(self, parent=None, width=36, height=20):
        super().__init__(parent)
        self.setCheckable(True)
        self._pos = 0.0
        self._anim = QPropertyAnimation(self, b"thumbPos")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.setFixedSize(width, height)
        self._r = height // 2
        self.toggled.connect(lambda c: (
            self._anim.setStartValue(self._pos),
            self._anim.setEndValue(1.0 if c else 0.0),
            self._anim.start()
        ))

    @pyqtProperty(float)
    def thumbPos(self): return self._pos

    @thumbPos.setter
    def thumbPos(self, v):
        self._pos = v
        self.update()
        self.stateChanged.emit(Qt.Checked if v > 0.5 else Qt.Unchecked)

    def paintEvent(self, e):
        from PyQt5.QtGui import QColor
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        track = QColor("#27ae60") if self.isChecked() else QColor("#4a6278")
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), self._r, self._r)
        p.fillPath(path, track)
        thumb_x = 2 + self._pos * (w - h + 2)
        p.setBrush(QColor("white"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(thumb_x, 2, h - 4, h - 4))

# ── Gradient header ───────────────────────────────────────────────────────────
def _make_header(ikon, baslik, r1, r2, parent=None):
    hdr = QFrame(parent); hdr.setFixedHeight(56)
    hdr.setStyleSheet(
        f"QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        f"stop:0 {r1},stop:1 {r2});border-top-left-radius:16px;border-top-right-radius:16px;border:none;}}")
    hl = QHBoxLayout(hdr); hl.setContentsMargins(18,0,12,0); hl.setSpacing(12)
    ic = QLabel(ikon); ic.setFixedSize(38,38); ic.setAlignment(Qt.AlignCenter)
    ic.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:19px;font-size:18px;")
    ttl = QLabel(baslik); ttl.setStyleSheet("color:white;font-size:13px;font-weight:bold;background:transparent;")
    close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
    close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:14px;border:none;border-radius:13px;} QPushButton:hover{background:rgba(255,255,255,0.15);color:white;}")
    close_btn.setCursor(Qt.PointingHandCursor)
    hl.addWidget(ic); hl.addWidget(ttl); hl.addStretch(); hl.addWidget(close_btn)
    return hdr, close_btn

def _make_footer():
    f = QFrame(); f.setFixedHeight(54)
    f.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border:none;border-top:1px solid #1a2a38;}")
    return f

def _setup_drag(widget, header_height=56):
    widget._drag_pos = None
    def _press(e):
        if e.button() == Qt.LeftButton and e.pos().y() <= header_height:
            widget._drag_pos = e.globalPos() - widget.frameGeometry().topLeft()
    def _move(e):
        if widget._drag_pos and e.buttons() == Qt.LeftButton:
            widget.move(e.globalPos() - widget._drag_pos)
    def _release(e):
        widget._drag_pos = None
    widget.mousePressEvent = _press
    widget.mouseMoveEvent = _move
    widget.mouseReleaseEvent = _release

ORTAK_DIALOG_CSS = """
    QDialog { background-color: #2c3e50; }
    QLabel  { color: #ecf0f1; background: transparent; font-size: 12px; }
    QComboBox, QSpinBox, QLineEdit {
        background: #34495e; border: 1px solid #4a6278;
        border-radius: 8px; color: white; padding: 7px 12px; font-size: 13px;
    }
    QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
        border-color: #3498db; background: #1a2a38;
    }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox QAbstractItemView {
        background:#34495e; color:white;
        selection-background-color:#2980b9; selection-color:white;
    }
    QListWidget {
        background:#1a2a38; color:#ecf0f1;
        border:1px solid #3498db; border-radius:6px; font-size:12px;
    }
    QListWidget::item { padding:5px 10px; }
    QListWidget::item:hover { background:#2c4a6a; }
    QListWidget::item:selected { background:#2980b9; color:white; }
    QSpinBox::up-button {
        subcontrol-origin:border; subcontrol-position:top right;
        width:20px; background:#3d566e; border-left:1px solid #4a6278; border-top-right-radius:6px;
    }
    QSpinBox::up-button:hover { background:#2980b9; }
    QSpinBox::up-arrow { image:none; width:0;height:0;
        border-left:4px solid transparent;border-right:4px solid transparent;border-bottom:5px solid #ecf0f1; }
    QSpinBox::down-button {
        subcontrol-origin:border; subcontrol-position:bottom right;
        width:20px; background:#3d566e; border-left:1px solid #4a6278; border-bottom-right-radius:6px;
    }
    QSpinBox::down-button:hover { background:#2980b9; }
    QSpinBox::down-arrow { image:none; width:0;height:0;
        border-left:4px solid transparent;border-right:4px solid transparent;border-top:5px solid #ecf0f1; }
    QPushButton { font-weight:bold; padding:8px 20px; border-radius:8px; border:none; }
"""


# ── Personel arama bileşeni (tekrar kullanılabilir) ───────────────────────────
class PersonelArama(QWidget):
    """Arama kutusu + açılır liste + seçildi etiketi."""
    secildi = pyqtSignal(int, str)   # (personel_id, ad_soyad)

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._all = []
        self._pid = None
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(4)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Ad veya sicil no yazın...")
        self.search.textChanged.connect(self._filtrele)
        lay.addWidget(self.search)

        self.liste = QListWidget()
        self.liste.setFixedHeight(110)
        self.liste.setVisible(False)
        self.liste.setStyleSheet("""
            QListWidget {
                background:#1a2a38; color:#ecf0f1;
                border:1px solid #3498db; border-radius:6px; font-size:12px;
            }
            QListWidget::item { padding:6px 10px; }
            QListWidget::item:hover { background:#2c4a6a; }
            QListWidget::item:selected { background:#2980b9; color:white; }
        """)
        self.liste.itemClicked.connect(self._sec)
        lay.addWidget(self.liste)

        self.secili_lbl = QLabel("— Personel seçilmedi —")
        self.secili_lbl.setStyleSheet(
            "color:#f39c12;font-size:11px;font-weight:bold;background:#1a2a38;"
            "border:1px solid #f39c12;border-radius:6px;padding:5px 10px;")
        lay.addWidget(self.secili_lbl)

        self._all = self.session.query(Personel).filter(
            Personel.durum.in_(["Aktif","Pasif"])
        ).order_by(Personel.ad_soyad).all()

    def pid(self): return self._pid

    def set_personel(self, pid, ad_soyad, sicil):
        self._pid = pid
        self.secili_lbl.setText(f"✅  {ad_soyad} ({sicil or '-'})")
        self.secili_lbl.setStyleSheet(
            "color:#2ecc71;font-size:11px;font-weight:bold;background:#0e2a1a;"
            "border:1px solid #27ae60;border-radius:6px;padding:5px 10px;")

    def _filtrele(self, text):
        arama = tr_lower(text.strip())
        self.liste.clear()
        if not arama:
            self.liste.setVisible(False); return
        sonuc = [p for p in self._all
                 if arama in tr_lower(p.ad_soyad) or
                    (p.sicil_no and arama in tr_lower(p.sicil_no))]
        for p in sonuc:
            it = QListWidgetItem(f"{p.ad_soyad}  ({p.sicil_no or '-'})")
            it.setData(Qt.UserRole, (p.id, p.ad_soyad, p.sicil_no))
            self.liste.addItem(it)
        self.liste.setVisible(bool(sonuc))

    def _sec(self, item):
        pid, ad, sicil = item.data(Qt.UserRole)
        self.set_personel(pid, ad, sicil)
        self.liste.setVisible(False)
        self.search.clear()
        self.secildi.emit(pid, ad)


# ==================== SENELİK İZİN TANIM DIALOGU ====================
class SenelikIzinTanimDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; font-size:12px; }
            QTabWidget::pane { background:#2c3e50; border:none; border-radius:0 0 12px 12px; }
            QTabWidget::tab-bar { alignment:center; }
            QTabBar::tab { background:#1a2a38; color:#7f8c8d; border:none;
                           min-width:120px; min-height:32px; padding:4px 16px; font-size:11px; font-weight:bold; }
            QTabBar::tab:selected { background:#34495e; color:white; border-bottom:2px solid #f39c12; }
            QTabBar::tab:hover:!selected { background:#2a3a48; color:#bdc3c7; }
            QTableWidget { background:#34495e; border:1px solid #4a6278; border-radius:8px; color:white;
                           gridline-color:rgba(255,255,255,0.07); }
            QHeaderView::section { background:#1a2a38; color:#bdc3c7;
                                   font-weight:bold; padding:8px; border:none; }
            QTableWidget::item { padding:5px; }
            QTableWidget::item:selected { background:rgba(18,52,96,0.85); color:white; }
            QComboBox { background:#34495e; color:white; border:1px solid #4a6278; border-radius:6px; padding:4px 8px; }
            QComboBox::drop-down { border:none; }
            QComboBox QAbstractItemView { background:#34495e; color:white; }
            QSpinBox { background:#34495e; border:1px solid #4a6278; border-radius:6px; color:white; padding:4px 8px; }
            QSpinBox::up-button { subcontrol-origin:border; subcontrol-position:top right;
                width:18px; background:#3d566e; border-left:1px solid #4a6278; border-top-right-radius:5px; }
            QSpinBox::down-button { subcontrol-origin:border; subcontrol-position:bottom right;
                width:18px; background:#3d566e; border-left:1px solid #4a6278; border-bottom-right-radius:5px; }
            QLineEdit { background:#1a2a38; color:white; border:1px solid #4a6278; border-radius:6px; padding:6px 10px; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0e4060,stop:1 #1a7aad);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 12, 0); hdr_lay.setSpacing(12)
        ic = QLabel("📅"); ic.setFixedSize(40, 40); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:20px;font-size:18px;")
        tl = QLabel("Senelik İzin Tanımlama")
        tl.setStyleSheet("color:white;font-size:13px;font-weight:bold;")
        txt = QVBoxLayout(); txt.setSpacing(1); txt.addWidget(tl)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:14px;border:none;} QPushButton:hover{color:white;}")
        close_btn.clicked.connect(self.accept)
        hdr_lay.addWidget(ic); hdr_lay.addLayout(txt); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { background:transparent; border:none; }
            QTabBar::tab { background:#1a2a38; color:#7f8c8d; font-size:12px; font-weight:bold;
                           padding:8px 20px; border:none; min-width:160px; }
            QTabBar::tab:selected { background:#2c3e50; color:#f39c12; border-bottom:2px solid #f39c12; }
            QTabBar::tab:hover:!selected { background:#243342; color:#bdc3c7; }
        """)
        outer_lay.addWidget(self.tabs, 1)

        # ── Tab 1: Yeni Tanımlama ────────────────────────────────────────────
        tab1 = QWidget()
        t1 = QVBoxLayout(tab1); t1.setContentsMargins(20, 14, 20, 10); t1.setSpacing(10)
        t1.addWidget(self._lbl("PERSONEL"))
        self.p_arama = PersonelArama(self.session)
        self.p_arama.secildi.connect(lambda pid, ad: self._kalan_goster())
        t1.addWidget(self.p_arama)
        yd = QHBoxLayout(); yd.setSpacing(12)
        yv = QVBoxLayout(); yv.setSpacing(4); yv.addWidget(self._lbl("YIL"))
        self.yil_cb = QComboBox()
        for y in range(2020, 2035): self.yil_cb.addItem(str(y), y)
        self.yil_cb.setCurrentText(str(datetime.date.today().year))
        self.yil_cb.currentIndexChanged.connect(self._kalan_goster)
        yv.addWidget(self.yil_cb); yd.addLayout(yv, 1)
        gv = QVBoxLayout(); gv.setSpacing(4); gv.addWidget(self._lbl("TANIMLANACAK GÜN"))
        self.gun_spin = QSpinBox(); self.gun_spin.setRange(1, 365); self.gun_spin.setValue(14); self.gun_spin.setSuffix(" gün")
        gv.addWidget(self.gun_spin); yd.addLayout(gv, 1)
        t1.addLayout(yd)
        self.kalan_lbl = QLabel("Personel seçince kalan izin görünür.")
        self.kalan_lbl.setStyleSheet("color:#f39c12;font-size:11px;background:#1a2a38;border:1px solid #f39c12;border-radius:6px;padding:7px 12px;")
        t1.addWidget(self.kalan_lbl)
        t1.addStretch()
        btn_row1 = QHBoxLayout(); btn_row1.setSpacing(8)
        k = QPushButton("💾  Kaydet"); k.setFixedHeight(34)
        k.setStyleSheet("QPushButton{background:#27ae60;color:white;font-weight:bold;border-radius:8px;border:none;padding:0 20px;font-size:11px;}QPushButton:hover{background:#2ecc71;}")
        k.clicked.connect(self.kaydet)
        sil_btn = QPushButton("🗑️  Tanımı Sil"); sil_btn.setFixedHeight(34)
        sil_btn.setStyleSheet("QPushButton{background:transparent;color:#e74c3c;border:1px solid #e74c3c;border-radius:8px;padding:0 14px;font-size:11px;font-weight:bold;}QPushButton:hover{background:#e74c3c;color:white;}")
        sil_btn.clicked.connect(self.tanim_sil)
        btn_row1.addStretch(); btn_row1.addWidget(sil_btn); btn_row1.addWidget(k)
        t1.addLayout(btn_row1)
        self.tabs.addTab(tab1, "✏️  Yeni Tanımlama")

        # ── Tab 2: Tanımlanmış İzinler ────────────────────────────────────────
        tab2 = QWidget()
        t2 = QVBoxLayout(tab2); t2.setContentsMargins(20, 14, 20, 10); t2.setSpacing(10)
        filtre_row = QHBoxLayout()
        filtre_row.addWidget(QLabel("Yıl:"))
        self.liste_yil_cb = QComboBox()
        self.liste_yil_cb.setFixedWidth(100)
        for y in range(2020, 2035): self.liste_yil_cb.addItem(str(y), y)
        self.liste_yil_cb.setCurrentText(str(datetime.date.today().year))
        self.liste_yil_cb.currentIndexChanged.connect(self._tabloyu_doldur)
        filtre_row.addWidget(self.liste_yil_cb)
        filtre_row.addStretch()
        t2.addLayout(filtre_row)
        self.tanim_table = QTableWidget()
        self.tanim_table.setColumnCount(6)
        self.tanim_table.setHorizontalHeaderLabels(["Personel", "Sicil No", "Yıl", "Tanımlanan", "Kullanılan", "Sil"])
        h = self.tanim_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.Fixed); self.tanim_table.setColumnWidth(1, 90)
        h.setSectionResizeMode(2, QHeaderView.Fixed); self.tanim_table.setColumnWidth(2, 60)
        h.setSectionResizeMode(3, QHeaderView.Fixed); self.tanim_table.setColumnWidth(3, 100)
        h.setSectionResizeMode(4, QHeaderView.Fixed); self.tanim_table.setColumnWidth(4, 100)
        h.setSectionResizeMode(5, QHeaderView.Fixed); self.tanim_table.setColumnWidth(5, 60)
        self.tanim_table.verticalHeader().setVisible(False)
        self.tanim_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tanim_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t2.addWidget(self.tanim_table)
        self.tabs.addTab(tab2, "📋  Tanımlanmış İzinler")

        self.tabs.currentChanged.connect(self._tab_degisti)
        _setup_drag(self)

    def _lbl(self, t):
        l = QLabel(t)
        l.setStyleSheet("color:#85c1e9;font-size:10px;font-weight:bold;letter-spacing:0.8px;background:transparent;")
        return l

    def _tab_degisti(self, idx):
        if idx == 1:
            self._tabloyu_doldur()

    def _tabloyu_doldur(self):
        yil = self.liste_yil_cb.currentData()
        self.tanim_table.setRowCount(0)
        kayitlar = self.session.query(YillikIzin).filter(
            YillikIzin.yil == yil
        ).order_by(YillikIzin.personel_id).all()
        row = 0
        for yi in kayitlar:
            p = yi.personel
            if not p:
                continue
            kul = self.session.query(func.sum(Izin.gun_sayisi)).filter(
                Izin.personel_id == p.id, Izin.durum == "Onaylandı",
                Izin.baslangic_tarihi >= datetime.date(yil, 1, 1),
                Izin.bitis_tarihi <= datetime.date(yil, 12, 31)
            ).scalar() or 0
            self.tanim_table.insertRow(row)
            self.tanim_table.setRowHeight(row, 36)
            self.tanim_table.setItem(row, 0, QTableWidgetItem(p.ad_soyad))
            self.tanim_table.setItem(row, 1, QTableWidgetItem(p.sicil_no or "—"))
            self.tanim_table.setItem(row, 2, QTableWidgetItem(str(yi.yil)))
            self.tanim_table.setItem(row, 3, QTableWidgetItem(str(yi.tanimlanan_izin)))
            self.tanim_table.setItem(row, 4, QTableWidgetItem(str(kul)))
            sil_btn = QPushButton("✕")
            sil_btn.setFixedSize(32, 28)
            sil_btn.setCursor(Qt.PointingHandCursor)
            sil_btn.setStyleSheet("QPushButton{background:transparent;color:#e74c3c;border:1px solid #e74c3c;border-radius:6px;font-size:11px;font-weight:bold;} QPushButton:hover{background:#e74c3c;color:white;}")
            sil_btn.clicked.connect(lambda checked, r=row, rid=yi.id: self._tanim_sil_table(rid, r))
            sw = QWidget(); sw.setFixedSize(40, 32)
            sl = QHBoxLayout(sw); sl.setAlignment(Qt.AlignCenter); sl.setContentsMargins(0, 0, 0, 0); sl.addWidget(sil_btn)
            self.tanim_table.setCellWidget(row, 5, sw)
            row += 1

    def _tanim_sil_table(self, yillik_izin_id, row):
        yi = self.session.get(YillikIzin, yillik_izin_id)
        if not yi:
            return
        p = yi.personel
        ad = p.ad_soyad if p else "?"
        if not ModernMesaj.soru(self, f"{ad} — {yi.yil} yılı izin tanımı ({yi.tanimlanan_izin} gün) silinecek. Onaylıyor musunuz?"):
            return
        try:
            self.session.delete(yi); self.session.commit()
            ModernMesaj.basari(self, "İzin tanımı silindi.")
            self._tabloyu_doldur()
        except Exception as e:
            self.session.rollback(); ModernMesaj.hata(self, str(e))

    def _kalan_goster(self):
        pid = self.p_arama.pid(); yil = self.yil_cb.currentData()
        if not pid or not yil: return
        yi = self.session.query(YillikIzin).filter_by(personel_id=pid, yil=yil).first()
        if yi:
            kul = self.session.query(func.sum(Izin.gun_sayisi)).filter(
                Izin.personel_id==pid, Izin.durum=="Onaylandı",
                Izin.baslangic_tarihi>=datetime.date(yil,1,1),
                Izin.bitis_tarihi<=datetime.date(yil,12,31)
            ).scalar() or 0
            kalan = yi.tanimlanan_izin - kul
            renk = "#2ecc71" if kalan > 0 else "#e74c3c"
            self.gun_spin.setValue(yi.tanimlanan_izin)
            self.kalan_lbl.setText(f"Tanımlanan: {yi.tanimlanan_izin} gün  |  Kullanılan: {kul}  |  Kalan: {kalan}")
            self.kalan_lbl.setStyleSheet(f"color:{renk};font-size:11px;background:#1a2a38;border:1px solid {renk};border-radius:6px;padding:7px 12px;")
        else:
            kul = self.session.query(func.sum(Izin.gun_sayisi)).filter(
                Izin.personel_id==pid, Izin.durum=="Onaylandı",
                Izin.baslangic_tarihi>=datetime.date(yil,1,1),
                Izin.bitis_tarihi<=datetime.date(yil,12,31)
            ).scalar() or 0
            if kul > 0:
                self.kalan_lbl.setText(f"Tanım yapılmamış  |  Kullanılan: {kul} gün  |  Kalan: -{kul} gün")
                self.kalan_lbl.setStyleSheet("color:#e74c3c;font-size:11px;background:#1a2a38;border:1px solid #e74c3c;border-radius:6px;padding:7px 12px;")
            else:
                self.kalan_lbl.setText("Bu yıl için henüz tanım yapılmamış.")
                self.kalan_lbl.setStyleSheet("color:#f39c12;font-size:11px;background:#1a2a38;border:1px solid #f39c12;border-radius:6px;padding:7px 12px;")

    def kaydet(self):
        pid = self.p_arama.pid(); yil = self.yil_cb.currentData(); gun = self.gun_spin.value()
        if not pid: ModernMesaj.uyari(self, "Lütfen personel seçin."); return
        yi = self.session.query(YillikIzin).filter_by(personel_id=pid, yil=yil).first()
        if yi: yi.tanimlanan_izin = gun
        else: self.session.add(YillikIzin(personel_id=pid, yil=yil, tanimlanan_izin=gun))
        try: self.session.commit(); ModernMesaj.basari(self, f"{gun} gün senelik izin tanımlandı."); self._kalan_goster()
        except Exception as e: self.session.rollback(); ModernMesaj.hata(self, str(e))

    def tanim_sil(self):
        pid = self.p_arama.pid(); yil = self.yil_cb.currentData()
        if not pid: ModernMesaj.uyari(self, "Lütfen önce personel seçin."); return
        yi = self.session.query(YillikIzin).filter_by(personel_id=pid, yil=yil).first()
        if not yi: ModernMesaj.uyari(self, "Bu personel için tanımlı izin bulunamadı."); return
        p = self.session.get(Personel, pid)
        ad = p.ad_soyad if p else "?"
        if not ModernMesaj.soru(self, f"{ad} — {yil} yılı izin tanımı ({yi.tanimlanan_izin} gün) silinecek. Onaylıyor musunuz?"): return
        try:
            self.session.delete(yi); self.session.commit()
            ModernMesaj.basari(self, "İzin tanımı silindi.")
            self.kalan_lbl.setText("Bu yıl için henüz tanım yapılmamış.")
            self.kalan_lbl.setStyleSheet("color:#f39c12;font-size:11px;background:#1a2a38;border:1px solid #f39c12;border-radius:6px;padding:7px 12px;")
        except Exception as e: self.session.rollback(); ModernMesaj.hata(self, str(e))

    def tanim_sil(self):
        pid = self.p_arama.pid(); yil = self.yil_cb.currentData()
        if not pid: ModernMesaj.uyari(self, "Lütfen önce personel seçin."); return
        yi = self.session.query(YillikIzin).filter_by(personel_id=pid, yil=yil).first()
        if not yi: ModernMesaj.uyari(self, "Bu personel için tanımlı izin bulunamadı."); return
        p = self.session.get(Personel, pid)
        ad = p.ad_soyad if p else "?"
        if not ModernMesaj.soru(self, f"{ad} — {yil} yılı izin tanımı ({yi.tanimlanan_izin} gün) silinecek. Onaylıyor musunuz?"): return
        try:
            self.session.delete(yi); self.session.commit()
            ModernMesaj.basari(self, "İzin tanımı silindi.")
            self.kalan_lbl.setText("Bu yıl için henüz tanım yapılmamış.")
            self.kalan_lbl.setStyleSheet("color:#f39c12;font-size:11px;background:#1a2a38;border:1px solid #f39c12;border-radius:6px;padding:7px 12px;")
        except Exception as e: self.session.rollback(); ModernMesaj.hata(self, str(e))


# ==================== TOPLU İZİN TANIM DIALOGU ====================
class TopluIzinTanimDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self._toggle_items = []
        self._drag_pos = None
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(520, 580)
        self.setStyleSheet(ORTAK_DIALOG_CSS + """
            QScrollArea { border:none; background:transparent; }
        """)
        self.init_ui()

    def _lbl(self, t):
        l = QLabel(t)
        l.setStyleSheet("color:#85c1e9;font-size:10px;font-weight:bold;letter-spacing:0.8px;background:transparent;")
        return l

    def init_ui(self):
        root_lay = QVBoxLayout(self); root_lay.setContentsMargins(0,0,0,0); root_lay.setSpacing(0)
        outer = QFrame(); outer.setObjectName("outer")
        outer.setStyleSheet("QFrame#outer{background:#2c3e50;border-radius:16px;border:1px solid #4a6278;}")
        lay = QVBoxLayout(outer); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        hdr, close_btn = _make_header("👥", "Toplu Senelik İzin Tanımlama", "#0e6655", "#1abc9c")
        close_btn.clicked.connect(self.reject)
        lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body); bl.setContentsMargins(20,16,20,10); bl.setSpacing(12)

        bl.addWidget(self._lbl("BU TARİHTEN ÖNCE İŞE BAŞLAYANLARA"))
        bir_yil_once = datetime.date.today().replace(year=datetime.date.today().year - 1)
        self.kriter_tarihi = TarihAlani()
        self.kriter_tarihi.set_date(QDate(bir_yil_once.year, bir_yil_once.month, bir_yil_once.day))
        bl.addWidget(self.kriter_tarihi)

        yd = QHBoxLayout(); yd.setSpacing(12)
        yv = QVBoxLayout(); yv.setSpacing(4); yv.addWidget(self._lbl("TANIMLANACAK YIL"))
        self.tanim_yili = QComboBox()
        for y in range(2020, 2035): self.tanim_yili.addItem(str(y), y)
        self.tanim_yili.setCurrentText(str(datetime.date.today().year))
        yv.addWidget(self.tanim_yili); yd.addLayout(yv, 1)
        gv = QVBoxLayout(); gv.setSpacing(4); gv.addWidget(self._lbl("VERİLECEK GÜN SAYISI"))
        self.tanim_gun = QSpinBox(); self.tanim_gun.setRange(1,365); self.tanim_gun.setValue(14); self.tanim_gun.setSuffix(" gün")
        gv.addWidget(self.tanim_gun); yd.addLayout(gv, 1)
        bl.addLayout(yd)

        # Önizle başlık + Tümünü Seç
        hdr_row = QHBoxLayout(); hdr_row.setSpacing(8)
        self.onizle_lbl = QLabel("Kriter seçince personel listesi görünür.")
        self.onizle_lbl.setStyleSheet("color:#7f8c8d;font-size:11px;background:transparent;")
        hdr_row.addWidget(self.onizle_lbl); hdr_row.addStretch()
        self.tumunu_lbl = QLabel("Tümü")
        self.tumunu_lbl.setStyleSheet("color:#bdc3c7;font-size:11px;background:transparent;")
        self.tumunu_toggle = ToggleSwitch(width=36, height=20)
        self.tumunu_toggle.setChecked(True)
        self.tumunu_toggle.toggled.connect(self._tumunu_sec)
        hdr_row.addWidget(self.tumunu_lbl); hdr_row.addWidget(self.tumunu_toggle)
        bl.addLayout(hdr_row)

        # Personel listesi scroll
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFixedHeight(210)
        self.scroll.setStyleSheet("QScrollArea{background:#1a2a38;border:1px solid #4a6278;border-radius:8px;}")
        self.liste_widget = QWidget(); self.liste_widget.setStyleSheet("background:#1a2a38;")
        self.liste_lay = QVBoxLayout(self.liste_widget)
        self.liste_lay.setContentsMargins(8,8,8,8); self.liste_lay.setSpacing(4)
        self.liste_lay.addStretch()
        self.scroll.setWidget(self.liste_widget)
        bl.addWidget(self.scroll)
        lay.addWidget(body); lay.addStretch()

        self.kriter_tarihi.dateChanged.connect(self.onizle)
        self.tanim_yili.currentIndexChanged.connect(self.onizle)

        footer = _make_footer(); fl = QHBoxLayout(footer)
        fl.setContentsMargins(18,10,18,10); fl.setSpacing(10)
        ob = QPushButton("👁️  Önizle"); ob.setFixedHeight(36)
        ob.setStyleSheet("QPushButton{background:#2980b9;color:white;font-weight:bold;border-radius:8px;border:none;padding:0 16px;}QPushButton:hover{background:#3498db;}")
        ob.clicked.connect(self.onizle)
        ub = QPushButton("✅  Uygula"); ub.setFixedHeight(36)
        ub.setStyleSheet("QPushButton{background:#16a085;color:white;font-weight:bold;border-radius:8px;border:none;padding:0 20px;}QPushButton:hover{background:#1abc9c;}")
        ub.clicked.connect(self.uygula)
        kb = QPushButton("Kapat"); kb.setFixedHeight(36)
        kb.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 14px;}QPushButton:hover{background:#34495e;color:white;}")
        kb.clicked.connect(self.accept)
        sb = QPushButton("🗑️  Toplu Sil"); sb.setFixedHeight(36)
        sb.setStyleSheet("QPushButton{background:transparent;color:#e74c3c;border:1px solid #e74c3c;border-radius:8px;border:none;padding:0 14px;font-weight:bold;}QPushButton:hover{background:#e74c3c;color:white;}")
        sb.clicked.connect(self.toplu_sil)
        fl.addWidget(ob); fl.addWidget(sb); fl.addStretch(); fl.addWidget(ub); fl.addWidget(kb)
        lay.addWidget(footer)
        root_lay.addWidget(outer)
        _setup_drag(self)
        self.onizle()

    def _kriter_personeller(self):
        kriter = self.kriter_tarihi.get_pydate()
        return self.session.query(Personel).filter(
            Personel.durum.in_(["Aktif","Pasif"]),
            Personel.ise_baslama < kriter
        ).order_by(Personel.ad_soyad).all()

    def onizle(self):
        personeller = self._kriter_personeller()
        yil = self.tanim_yili.currentData(); gun = self.tanim_gun.value()
        self._toggle_items = []
        while self.liste_lay.count() > 1:
            it = self.liste_lay.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        if not personeller:
            self.onizle_lbl.setText("Kritere uyan personel bulunamadı."); return
        self.onizle_lbl.setText(f"{len(personeller)} personel — {yil} için {gun} gün")
        for p in personeller:
            row = QWidget(); row.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row); rl.setContentsMargins(4,2,4,2); rl.setSpacing(10)
            toggle = ToggleSwitch(width=36, height=20); toggle.setChecked(True)
            yi = self.session.query(YillikIzin).filter_by(personel_id=p.id, yil=yil).first()
            bilgi = f"✓ {yi.tanimlanan_izin}g" if yi else "— Yok"
            renk = "#2ecc71" if yi else "#7f8c8d"
            ad_lbl = QLabel(p.ad_soyad); ad_lbl.setStyleSheet("color:#ecf0f1;font-size:12px;background:transparent;")
            b_lbl = QLabel(bilgi); b_lbl.setStyleSheet(f"color:{renk};font-size:10px;background:transparent;")
            rl.addWidget(toggle); rl.addWidget(ad_lbl, 1); rl.addWidget(b_lbl)
            self.liste_lay.insertWidget(self.liste_lay.count()-1, row)
            self._toggle_items.append((p, toggle))
        self.tumunu_toggle.setChecked(True)

    def _tumunu_sec(self, checked):
        for _, t in self._toggle_items:
            t.blockSignals(True); t.setChecked(checked); t.blockSignals(False); t.update()

    def uygula(self):
        secililer = [p for p, t in self._toggle_items if t.isChecked()]
        if not secililer: ModernMesaj.uyari(self, "En az bir personel seçin."); return
        yil = self.tanim_yili.currentData(); gun = self.tanim_gun.value()
        if not ModernMesaj.soru(self, f"{len(secililer)} personele {yil} için {gun} gün tanımlanacak. Onaylıyor musunuz?"): return
        try:
            for p in secililer:
                yi = self.session.query(YillikIzin).filter_by(personel_id=p.id, yil=yil).first()
                if yi: yi.tanimlanan_izin = gun
                else: self.session.add(YillikIzin(personel_id=p.id, yil=yil, tanimlanan_izin=gun))
            self.session.commit()
            ModernMesaj.basari(self, f"{len(secililer)} personele {gun} gün izin tanımlandı.")
            self.onizle()
        except Exception as e: self.session.rollback(); ModernMesaj.hata(self, str(e))

    def toplu_sil(self):
        secililer = [p for p, t in self._toggle_items if t.isChecked()]
        if not secililer: ModernMesaj.uyari(self, "En az bir personel seçin."); return
        yil = self.tanim_yili.currentData()
        # Sadece tanımı olanları sil
        silinecekler = []
        for p in secililer:
            yi = self.session.query(YillikIzin).filter_by(personel_id=p.id, yil=yil).first()
            if yi: silinecekler.append(yi)
        if not silinecekler:
            ModernMesaj.uyari(self, "Seçili personellerin hiçbirinde bu yıl için tanım bulunamadı."); return
        if not ModernMesaj.soru(self, f"{len(silinecekler)} personelin {yil} yılı izin tanımı silinecek. Onaylıyor musunuz?"): return
        try:
            for yi in silinecekler: self.session.delete(yi)
            self.session.commit()
            ModernMesaj.basari(self, f"{len(silinecekler)} personelin izin tanımı silindi.")
            self.onizle()
        except Exception as e: self.session.rollback(); ModernMesaj.hata(self, str(e))


# ==================== İZİN SAYFASI ====================
class IzinPage(QWidget):
    def __init__(self):
        super().__init__()
        self.session = get_session()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15,15,15,15); layout.setSpacing(15)

        # ── Toolbar (3 satır) ────────────────────────────────────────────────
        top_panel = QFrame()
        top_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1a2a38, stop:1 #2c3e50);
                border-radius: 12px; border: 1px solid #4a6278;
            }
            QLabel {
                color: #ecf0f1; font-size: 12px;
                font-weight: bold; background: transparent;
            }
            QLineEdit, QComboBox {
                background: #34495e; border: 1px solid #4a6278;
                border-radius: 8px; color: white;
                padding: 6px 12px; font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #3498db; background: #1a2a38;
            }
            QComboBox::drop-down { border: none; width: 22px; }
            QComboBox QAbstractItemView {
                background: #34495e; color: white;
                selection-background-color: #2980b9;
                selection-color: white; border: 1px solid #4a6278;
            }
        """)
        top_panel.setFixedHeight(130)
        top_lay = QVBoxLayout(top_panel)
        top_lay.setContentsMargins(16,10,16,10); top_lay.setSpacing(7)

        # ── Satır 1: Arama + Durum filtresi ──────────────────────────────────
        row1 = QHBoxLayout(); row1.setSpacing(8)
        self.personel_search = QLineEdit()
        self.personel_search.setPlaceholderText("🔍 Personel ara (isim veya sicil)...")
        self.personel_search.setFixedHeight(36)
        self.personel_search.textChanged.connect(self.load_data)
        self.durum_filter = QComboBox(); self.durum_filter.setFixedWidth(200); self.durum_filter.setFixedHeight(36)
        self.durum_filter.addItems(["Tümü","Onay Bekliyor","Onaylandı","Reddedildi"])
        self.durum_filter.currentTextChanged.connect(self.load_data)
        row1.addWidget(QLabel("Personel:")); row1.addWidget(self.personel_search, 1)
        row1.addWidget(QLabel("Durum:")); row1.addWidget(self.durum_filter)
        top_lay.addLayout(row1)

        # ── Satır 2: Dönem Filtresi ───────────────────────────────────────────
        row2 = QHBoxLayout(); row2.setSpacing(8)
        self.ay_cb = QComboBox(); self.ay_cb.setFixedHeight(34)
        self.ay_cb.addItem("🗓  Tüm Aylar", 0)
        for i, ad in enumerate(["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                                  "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"], 1):
            self.ay_cb.addItem(ad, i)
        self.ay_cb.setCurrentIndex(QDate.currentDate().month())
        self.ay_cb.currentIndexChanged.connect(self.load_data)

        self.yil_cb = QComboBox(); self.yil_cb.setFixedHeight(34); self.yil_cb.setFixedWidth(110)
        self.yil_cb.addItem("Tüm Yıllar", 0)
        for y in range(2022, 2032): self.yil_cb.addItem(str(y), y)
        self.yil_cb.setCurrentText(str(QDate.currentDate().year()))
        self.yil_cb.currentIndexChanged.connect(self.load_data)

        row2.addWidget(QLabel("Dönem:"))
        row2.addWidget(self.ay_cb)
        row2.addWidget(self.yil_cb)
        row2.addStretch()
        top_lay.addLayout(row2)

        # ── Satır 3: Butonlar ─────────────────────────────────────────────────
        row3 = QHBoxLayout(); row3.setSpacing(8)
        self.yeni_btn       = self._btn("➕ Yeni İzin Ekle",        "#27ae60", self.yeni_izin)
        self.senelik_btn    = self._btn("📅 Senelik İzin Tanımla",  "#2980b9", self.senelik_izin_tanimla)
        self.toplu_btn      = self._btn("👥 Toplu Tanımla",          "#16a085", self.toplu_izin_tanimla)
        self.izin_ucret_btn = self._btn("💰 İzin Ücreti Öde",       "#e67e22", self.izin_ucreti_ode)
        for b in [self.yeni_btn, self.senelik_btn, self.toplu_btn, self.izin_ucret_btn]:
            row3.addWidget(b)
        row3.addStretch()
        top_lay.addLayout(row3)
        layout.addWidget(top_panel)

        # ── Tablo ─────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID","Personel","İzin Türü","Başlangıç","Bitiş",
            "Gün","Durum","Talep Tarihi","Açıklama","İşlem"
        ])
        self.table.setColumnHidden(0, True)
        # Kullanıcı sütun genişliği ayarlayabilsin
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.itemDoubleClicked.connect(
            lambda item: self.izin_duzenle(int(self.table.item(item.row(), 0).text())))
        self.table.setStyleSheet("""
            QTableWidget {
                background: white; border: none;
                gridline-color: rgba(255,255,255,0.07);
                color: #1a1a1a; font-size: 12px;
            }
            QHeaderView::section {
                background: #1a2a38; color: #bdc3c7;
                font-weight: bold; padding: 8px; border: none;
                border-bottom: 2px solid #4a6278;
            }
            QTableWidget::item { padding: 5px; background: white; }
            QTableWidget::item:alternate { background: #f5f8fa; }
            QTableWidget::item:selected {
                background: rgba(18,52,96,0.85); color: white;
            }
        """)
        layout.addWidget(self.table)

        # Sütun genişliği kaydet/yükle (Personel sayfası ile aynı deneyim)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_column_context_menu)
        self.load_column_widths()

    def _btn(self, text, color, func):
        btn = QPushButton(text); btn.setFixedHeight(32); btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton{{background:{color};color:white;font-weight:bold;"
            f"border-radius:7px;border:none;padding:0 14px;font-size:12px;}}"
            f"QPushButton:hover{{opacity:0.88;}}")
        btn.clicked.connect(func); return btn

    def _widths_path(self):
        return get_config_path("izin_table_widths.json")

    def save_column_widths(self):
        widths = {}
        for i in range(self.table.columnCount()):
            widths[i] = self.table.columnWidth(i)
        try:
            with open(self._widths_path(), "w", encoding="utf-8") as f:
                json.dump(widths, f)
            ModernMesaj.basari(self, "Sütun genişlikleri kaydedildi.")
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

    def load_data(self):
        self.session.expire_all()
        self.table.setRowCount(0)
        arama = tr_lower(self.personel_search.text().strip())
        durum = self.durum_filter.currentText()
        yil   = self.yil_cb.currentData() or 0
        ay    = self.ay_cb.currentData() or 0

        query = self.session.query(Izin).join(Personel).join(IzinTuru)
        if durum != "Tümü": query = query.filter(Izin.durum == durum)
        if yil != 0 and ay != 0:
            _, son = calendar.monthrange(yil, ay)
            query = query.filter(Izin.baslangic_tarihi <= datetime.date(yil, ay, son),
                                 Izin.bitis_tarihi     >= datetime.date(yil, ay, 1))
        elif yil != 0:
            query = query.filter(Izin.baslangic_tarihi <= datetime.date(yil,12,31),
                                 Izin.bitis_tarihi     >= datetime.date(yil, 1, 1))
        izinler = query.order_by(Izin.talep_tarihi.desc()).all()
        if arama:
            izinler = [i for i in izinler
                       if arama in tr_lower(i.personel.ad_soyad) or
                          (i.personel.sicil_no and arama in tr_lower(i.personel.sicil_no))]

        DURUM_RENK = {
            "Onaylandı":   ("#27ae60", "#0e2a1a"),
            "Reddedildi":  ("#e74c3c", "#2a0e0e"),
            "Onay Bekliyor": ("#f39c12", "#2a1e0e"),
        }

        for izin in izinler:
            row = self.table.rowCount(); self.table.insertRow(row)
            self.table.setRowHeight(row, 46)
            durum_renk, durum_bg = DURUM_RENK.get(izin.durum, ("#7f8c8d", "#2c3e50"))

            items = [
                QTableWidgetItem(str(izin.id)),
                QTableWidgetItem(f"{izin.personel.ad_soyad} ({izin.personel.sicil_no or '-'})"),
                QTableWidgetItem(izin.izin_turu.ad if izin.izin_turu else "-"),
                QTableWidgetItem(izin.baslangic_tarihi.strftime("%d.%m.%Y")),
                QTableWidgetItem(izin.bitis_tarihi.strftime("%d.%m.%Y")),
                QTableWidgetItem(str(izin.gun_sayisi or 0)),
                QTableWidgetItem(izin.durum),
                QTableWidgetItem(izin.talep_tarihi.strftime("%d.%m.%Y") if izin.talep_tarihi else "-"),
                QTableWidgetItem(izin.aciklama or ""),
                QTableWidgetItem("")
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignCenter)
                if col == 6:
                    item.setForeground(QColor(durum_renk))
                self.table.setItem(row, col, item)

            bw = QWidget(); bl = QHBoxLayout(bw)
            bl.setContentsMargins(6,4,6,4); bl.setSpacing(4)
            bl.setAlignment(Qt.AlignCenter)
            bw.setStyleSheet("background: transparent;")
            bw.setMinimumHeight(40)

            def style_btn(bg, hover, border):
                return (
                    "QPushButton{"
                    f"background:{bg};color:white;border-radius:6px;border:1px solid {border};"
                    "font-size:13px;font-weight:bold;padding:0px;"
                    "}"
                    f"QPushButton:hover{{background:{hover};}}"
                    "QPushButton:pressed{background:#1a2a38;}"
                )
            if izin.durum == "Onay Bekliyor":
                bo = QPushButton("✅"); bo.setFixedSize(36, 32)
                bo.setStyleSheet(style_btn("#27ae60", "#2ecc71", "rgba(255,255,255,0.18)"))
                bo.clicked.connect(lambda _, iid=izin.id: self.izin_onayla(iid)); bl.addWidget(bo)
                br = QPushButton("✖"); br.setFixedSize(36, 32)
                br.setStyleSheet(style_btn("#c0392b", "#e74c3c", "rgba(255,255,255,0.22)"))
                br.clicked.connect(lambda _, iid=izin.id: self.izin_reddet(iid)); bl.addWidget(br)
            be = QPushButton("✎"); be.setFixedSize(36, 32)
            be.setStyleSheet(style_btn("#3498db", "#5dade2", "rgba(255,255,255,0.18)"))
            be.clicked.connect(lambda _, iid=izin.id: self.izin_duzenle(iid)); bl.addWidget(be)
            bd = QPushButton("🗑"); bd.setFixedSize(36, 32)
            bd.setStyleSheet(style_btn("#e74c3c", "#ff6b6b", "rgba(255,255,255,0.18)"))
            bd.clicked.connect(lambda _, iid=izin.id: self.izin_sil(iid)); bl.addWidget(bd)
            self.table.setCellWidget(row, 9, bw)

    def yeni_izin(self):
        d = IzinDialog(self.session, parent=self)
        if d.exec_(): self.load_data()

    def izin_duzenle(self, izin_id):
        izin = self.session.get(Izin, izin_id)
        if izin:
            d = IzinDialog(self.session, izin=izin, parent=self)
            if d.exec_(): self.load_data()

    def izin_sil(self, izin_id):
        izin = self.session.get(Izin, izin_id)
        if not izin: return
        if ModernMesaj.soru(self, f"{izin.personel.ad_soyad} personelinin izni silinsin mi?"):
            self.session.delete(izin); self.session.commit()
            self.load_data(); ModernMesaj.basari(self, "İzin silindi.")

    def izin_onayla(self, izin_id):
        izin = self.session.get(Izin, izin_id)
        if izin and izin.durum == "Onay Bekliyor":
            izin.durum = "Onaylandı"; izin.onay_tarihi = datetime.date.today()
            self.session.commit(); self.load_data(); ModernMesaj.basari(self, "İzin onaylandı.")

    def izin_reddet(self, izin_id):
        izin = self.session.get(Izin, izin_id)
        if izin and izin.durum == "Onay Bekliyor":
            izin.durum = "Reddedildi"
            self.session.commit(); self.load_data(); ModernMesaj.basari(self, "İzin reddedildi.")

    def senelik_izin_tanimla(self):
        SenelikIzinTanimDialog(self.session, parent=self).exec_()

    def toplu_izin_tanimla(self):
        TopluIzinTanimDialog(self.session, parent=self).exec_()

    def izin_ucreti_ode(self):
        dialog = SenelikIzinUcretDialog(self.session, parent=self)
        dialog.exec_()
        self.load_data()


class SenelikIzinUcretDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self._data = []
        self._drag_pos = None
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(740, 570)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; font-size:12px; }
            QTableWidget { background:#34495e; border:1px solid #4a6278; border-radius:8px; color:white;
                           gridline-color:rgba(255,255,255,0.07); }
            QHeaderView::section { background:#1a2a38; color:#bdc3c7;
                                   font-weight:bold; padding:8px; border:none; }
            QTableWidget::item { padding:5px; }
            QTableWidget::item:selected { background:rgba(18,52,96,0.85); color:white; }
            QLineEdit { background:#1a2a38; color:white; border:1px solid #4a6278;
                        border-radius:6px; padding:6px 10px; font-size:12px; }
            QSpinBox { background:#1a2a38; color:white; border:1px solid #4a6278;
                       border-radius:4px; padding:2px 4px; font-size:11px; }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin:border; width:16px; background:#3d566e; border:none; }
            QSpinBox::up-arrow { image:none; width:0; height:0;
                border-left:3px solid transparent; border-right:3px solid transparent;
                border-bottom:4px solid #ecf0f1; }
            QSpinBox::down-arrow { image:none; width:0; height:0;
                border-left:3px solid transparent; border-right:3px solid transparent;
                border-top:4px solid #ecf0f1; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7d5109,stop:1 #f39c12);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 12, 0); hdr_lay.setSpacing(12)
        ic = QLabel("💰"); ic.setFixedSize(40, 40); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:20px;font-size:18px;")
        tl = QLabel("İzin Ücreti Ödemesi")
        tl.setStyleSheet("color:white;font-size:13px;font-weight:bold;")
        sub = QLabel("Kullanılmayan senelik izin günleri için otomatik hesaplama")
        sub.setStyleSheet("color:rgba(255,255,255,0.6);font-size:11px;")
        txt = QVBoxLayout(); txt.setSpacing(1); txt.addWidget(tl); txt.addWidget(sub)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:14px;border:none;} QPushButton:hover{color:white;}")
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(ic); hdr_lay.addLayout(txt); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        # Sekmeler
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabBar().setExpanding(False)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { background:transparent; border:none; }
            QTabBar::tab { background:#1a2a38; color:#7f8c8d; font-size:12px; font-weight:bold;
                           padding:10px 24px; border:none; min-width:200px; border-top-left-radius:8px; border-top-right-radius:8px; margin-right:2px; }
            QTabBar::tab:selected { background:#2c3e50; color:#f39c12; border-bottom:2px solid #f39c12; }
            QTabBar::tab:hover:!selected { background:#243342; color:#bdc3c7; }
        """)

        # ════ Tab 1: İzin Ücreti Öde ════
        tab1 = QWidget(); tab1.setStyleSheet("background:transparent;")
        tab1_lay = QVBoxLayout(tab1); tab1_lay.setContentsMargins(16, 14, 16, 8); tab1_lay.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Yıl:"))
        self.yil_cb = QComboBox()
        self.yil_cb.setFixedWidth(100)
        self.yil_cb.setStyleSheet("QComboBox{background:#34495e;color:white;border:1px solid #4a6278;border-radius:6px;padding:4px 8px;} QComboBox::drop-down{border:none;} QComboBox QAbstractItemView{background:#34495e;color:white;}")
        for y in range(2022, 2032):
            self.yil_cb.addItem(str(y), y)
        self.yil_cb.setCurrentText(str(QDate.currentDate().year()))
        self.yil_cb.currentIndexChanged.connect(self._veri_yukle)
        top_row.addWidget(self.yil_cb)
        top_row.addSpacing(16)
        ara_ic = QLabel("🔍"); ara_ic.setStyleSheet("font-size:13px;")
        top_row.addWidget(ara_ic)
        self.arama_edit = QLineEdit()
        self.arama_edit.setPlaceholderText("Personel adı ile filtrele (Türkçe duyarsız)...")
        self.arama_edit.setFixedWidth(280)
        self.arama_edit.textChanged.connect(self._tabloyu_doldur)
        top_row.addWidget(self.arama_edit)
        top_row.addSpacing(16)
        top_row.addWidget(QLabel("Tarih:"))
        self.odeme_tarihi = TarihAlani()
        self.odeme_tarihi.set_date(QDate.currentDate())
        top_row.addWidget(self.odeme_tarihi)
        top_row.addStretch()
        tab1_lay.addLayout(top_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Seçim", "Personel", "Kalan İzin (gün)", "Günlük Ücret (₺)", "Hesaplanan Tutar (₺)"])
        hdr_t = self.table.horizontalHeader()
        hdr_t.setSectionResizeMode(0, QHeaderView.Fixed); self.table.setColumnWidth(0, 55)
        hdr_t.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr_t.setSectionResizeMode(2, QHeaderView.Fixed); self.table.setColumnWidth(2, 120)
        hdr_t.setSectionResizeMode(3, QHeaderView.Fixed); self.table.setColumnWidth(3, 130)
        hdr_t.setSectionResizeMode(4, QHeaderView.Fixed); self.table.setColumnWidth(4, 150)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tab1_lay.addWidget(self.table)

        self.ozet_lbl = QLabel("Seçili: 0 personel  |  Toplam: 0,00 ₺")
        self.ozet_lbl.setTextFormat(Qt.RichText)
        self.ozet_lbl.setStyleSheet("color:#bdc3c7;font-size:12px;")
        tab1_lay.addWidget(self.ozet_lbl)

        odeme_btn = QPushButton("💳 Ödeme Yap")
        odeme_btn.setFixedSize(160, 36)
        odeme_btn.setCursor(Qt.PointingHandCursor)
        odeme_btn.setStyleSheet("QPushButton{background:#27ae60;color:white;font-weight:bold;border-radius:8px;border:none;padding:0 20px;font-size:12px;} QPushButton:hover{background:#2ecc71;}")
        odeme_btn.clicked.connect(self._odeme_yap)
        tab1_lay.addWidget(odeme_btn, 0, Qt.AlignLeft)

        self.tab_widget.addTab(tab1, "💰 İzin Ücreti Öde")

        # ════ Tab 2: İzin Ücreti Ödeme Listesi ════
        tab2 = QWidget(); tab2.setStyleSheet("background:transparent;")
        tab2_lay = QVBoxLayout(tab2); tab2_lay.setContentsMargins(16, 14, 16, 8); tab2_lay.setSpacing(10)

        self.gecmis_table = QTableWidget()
        self.gecmis_table.setColumnCount(5)
        self.gecmis_table.setHorizontalHeaderLabels(["Personel", "Tarih", "Gün", "Tutar (₺)", ""])
        hdr_g = self.gecmis_table.horizontalHeader()
        hdr_g.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr_g.setSectionResizeMode(1, QHeaderView.Fixed); self.gecmis_table.setColumnWidth(1, 110)
        hdr_g.setSectionResizeMode(2, QHeaderView.Fixed); self.gecmis_table.setColumnWidth(2, 60)
        hdr_g.setSectionResizeMode(3, QHeaderView.Fixed); self.gecmis_table.setColumnWidth(3, 130)
        hdr_g.setSectionResizeMode(4, QHeaderView.Fixed); self.gecmis_table.setColumnWidth(4, 60)
        self.gecmis_table.verticalHeader().setVisible(False)
        self.gecmis_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.gecmis_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tab2_lay.addWidget(self.gecmis_table)

        self.tab_widget.addTab(tab2, "📋 İzin Ücreti Ödeme Listesi")
        outer_lay.addWidget(self.tab_widget, 1)

        footer = QFrame()
        footer.setFixedHeight(50)
        footer.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border:none;border-top:1px solid #1a2a38;}")
        foot_lay = QHBoxLayout(footer); foot_lay.setContentsMargins(16, 7, 16, 7)
        kapat_btn = QPushButton("Kapat")
        kapat_btn.setFixedHeight(34)
        kapat_btn.setCursor(Qt.PointingHandCursor)
        kapat_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 16px;font-size:12px;} QPushButton:hover{background:#34495e;color:white;}")
        kapat_btn.clicked.connect(self.reject)
        foot_lay.addStretch(); foot_lay.addWidget(kapat_btn)
        outer_lay.addWidget(footer)

        self._veri_yukle()
        self._odeme_listesini_yukle()

    def _get_gunluk_ucret(self, personel_id):
        son = self.session.query(Bordro).filter(
            Bordro.personel_id == personel_id
        ).order_by(Bordro.yil.desc(), Bordro.ay.desc()).first()
        if son and son.toplam_net_maas > 0:
            return son.toplam_net_maas / 30
        return 0

    def _veri_yukle(self):
        self.session.expire_all()
        yil = self.yil_cb.currentData()
        self._data = []
        personeller = self.session.query(Personel).order_by(Personel.ad_soyad).all()
        for p in personeller:
            yi = self.session.query(YillikIzin).filter(
                YillikIzin.personel_id == p.id, YillikIzin.yil == yil
            ).first()
            if not yi or yi.tanimlanan_izin <= 0:
                continue

            kullanilan = self.session.query(func.sum(Izin.gun_sayisi)).filter(
                Izin.personel_id == p.id,
                Izin.durum == "Onaylandı",
                Izin.baslangic_tarihi >= datetime.date(yil, 1, 1),
                Izin.bitis_tarihi <= datetime.date(yil, 12, 31)
            ).scalar() or 0
            kalan = yi.tanimlanan_izin - kullanilan
            if kalan <= 0:
                continue

            gunluk = self._get_gunluk_ucret(p.id)
            if gunluk <= 0:
                continue

            hesap = kalan * gunluk
            self._data.append((p, kalan, gunluk, hesap))
        self._tabloyu_doldur()

    def _tabloyu_doldur(self):
        arama = tr_lower(self.arama_edit.text().strip())
        self.table.setRowCount(0)
        row = 0
        for p, kalan_max, gunluk, hesap in self._data:
            if arama and arama not in tr_lower(p.ad_soyad) and arama not in tr_lower(p.sicil_no or ""):
                continue
            self.table.insertRow(row)
            self.table.setRowHeight(row, 40)

            toggle = ToggleSwitch(width=28, height=16)
            toggle.setChecked(True)
            toggle.toggled.connect(lambda: self._ozet_guncelle())
            tw = QWidget(); tw.setFixedSize(36, 28)
            tl = QHBoxLayout(tw); tl.setAlignment(Qt.AlignCenter); tl.setContentsMargins(0, 0, 0, 0); tl.addWidget(toggle)
            self.table.setCellWidget(row, 0, tw)

            self.table.setItem(row, 1, QTableWidgetItem(f"{p.ad_soyad} ({p.sicil_no})"))

            gun_spin = QSpinBox()
            gun_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
            gun_spin.setRange(1, kalan_max)
            gun_spin.setValue(kalan_max)
            gun_spin.setSuffix(" gün")
            gun_spin.setAlignment(Qt.AlignCenter)
            gun_spin.setFixedWidth(100)
            gun_spin.valueChanged.connect(lambda val, r=row, gu=gunluk: self._gun_degisti(r, val, gu))
            self.table.setCellWidget(row, 2, gun_spin)

            ucret_item = QTableWidgetItem()
            ucret_item.setData(Qt.UserRole, gunluk)
            ucret_item.setText(f"{gunluk:,.2f} ₺".replace(",", "."))
            ucret_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, ucret_item)

            hesap_item = QTableWidgetItem()
            hesap_item.setData(Qt.UserRole, hesap)
            hesap_item.setText(f"{hesap:,.2f} ₺".replace(",", "."))
            hesap_item.setTextAlignment(Qt.AlignCenter)
            hesap_item.setForeground(QColor("#e67e22"))
            fnt = QFont(); fnt.setBold(True); hesap_item.setFont(fnt)
            self.table.setItem(row, 4, hesap_item)
            row += 1
        self._ozet_guncelle()

    def _gun_degisti(self, row, gun, gunluk_ucret):
        yeni_hesap = gun * gunluk_ucret
        item = self.table.item(row, 4)
        if item:
            item.setData(Qt.UserRole, yeni_hesap)
            item.setText(f"{yeni_hesap:,.2f} ₺".replace(",", "."))
        self._ozet_guncelle()

    def _ozet_guncelle(self):
        secili = 0
        toplam = 0.0
        for r in range(self.table.rowCount()):
            w_toggle = self.table.cellWidget(r, 0)
            if not w_toggle:
                continue
            t = w_toggle.findChild(QAbstractButton)
            if t and t.isChecked():
                secili += 1
                w_spin = self.table.cellWidget(r, 2)
                gun = w_spin.value() if w_spin else 0
                ucret_item = self.table.item(r, 3)
                if ucret_item and ucret_item.data(Qt.UserRole) is not None:
                    toplam += gun * float(ucret_item.data(Qt.UserRole))
        self.ozet_lbl.setText(f"Seçili: <b style='color:#3498db'>{secili}</b> personel  |  "
                              f"Toplam: <b style='color:#e67e22'>{toplam:,.2f}</b>".replace(",", "X").replace(".", ",").replace("X", "."))

    def _odeme_yap(self):
        secilenler = []
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, 0)
            if not w:
                continue
            t = w.findChild(ToggleSwitch)
            if not t or not t.isChecked():
                continue
            w_spin = self.table.cellWidget(r, 2)
            gun = w_spin.value() if w_spin else 0
            if gun <= 0:
                continue
            ucret_item = self.table.item(r, 3)
            if not ucret_item or ucret_item.data(Qt.UserRole) is None:
                continue
            gunluk = float(ucret_item.data(Qt.UserRole))
            tutar = gun * gunluk
            secilenler.append((r, gun, tutar))

        if not secilenler:
            ModernMesaj.uyari(self, "Lütfen en az bir personel seçin.")
            return

        if not ModernMesaj.soru(self, f"{len(secilenler)} personel için toplam {sum(s[2] for s in secilenler):,.2f} ₺ izin ücreti ödenecek. Onaylıyor musunuz?"):
            return

        yil = self.yil_cb.currentData()
        izin_turu = self.session.query(IzinTuru).filter(IzinTuru.ad == "Senelik İzin").first()
        if not izin_turu:
            izin_turu = IzinTuru(ad="Senelik İzin", renk="#3498db", ucretli_mi=True)
            self.session.add(izin_turu)
            self.session.flush()

        basarili = 0
        for r, gun, tutar in secilenler:
            personel_text = self.table.item(r, 1).text()
            sicil = None
            if "(" in personel_text and ")" in personel_text:
                sicil = personel_text.split("(")[1].split(")")[0].strip()
            if not sicil:
                continue
            personel = self.session.query(Personel).filter(Personel.sicil_no == sicil).first()
            if not personel:
                continue
            son_bordro = self.session.query(Bordro).filter(
                Bordro.personel_id == personel.id
            ).order_by(Bordro.yil.desc(), Bordro.ay.desc()).first()
            if not son_bordro:
                continue

            odeme_tarihi = self.odeme_tarihi.get_pydate()

            odeme = MaasOdeme(
                personel_id=personel.id,
                bordro_id=son_bordro.id,
                tarih=odeme_tarihi,
                tutar=tutar,
                aciklama=f"{yil} yılı {gun} gün kullanılmayan izin ücreti"
            )
            self.session.add(odeme)

            izin = Izin(
                personel_id=personel.id,
                izin_turu_id=izin_turu.id,
                baslangic_tarihi=odeme_tarihi,
                bitis_tarihi=odeme_tarihi,
                gun_sayisi=gun,
                aciklama=f"{yil} yılı izin ücreti ödemesi (kullanıldı)",
                durum="Onaylandı",
                talep_tarihi=datetime.date.today(),
                onay_tarihi=datetime.date.today()
            )
            self.session.add(izin)
            basarili += 1

        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))
            return
        self._veri_yukle()
        self._odeme_listesini_yukle()
        ModernMesaj.basari(self, f"{basarili} personel için izin ücreti ödemesi kaydedildi.")

    def _odeme_listesini_yukle(self):
        self.gecmis_table.setRowCount(0)
        yeni_session = get_session()
        try:
            odemeler = yeni_session.query(MaasOdeme).filter(
                func.lower(MaasOdeme.aciklama).like("%izin ücreti%")
            ).order_by(MaasOdeme.tarih.desc()).all()

            for i, o in enumerate(odemeler):
                self.gecmis_table.insertRow(i)
                self.gecmis_table.setRowHeight(i, 38)

                personel = yeni_session.get(Personel, o.personel_id)
                ad = f"{personel.ad_soyad} ({personel.sicil_no})" if personel else f"ID:{o.personel_id}"
                self.gecmis_table.setItem(i, 0, QTableWidgetItem(ad))

                item_tarih = QTableWidgetItem(o.tarih.strftime("%d.%m.%Y") if o.tarih else "-")
                item_tarih.setTextAlignment(Qt.AlignCenter)
                self.gecmis_table.setItem(i, 1, item_tarih)

                m = re.search(r"(\d+)\s*g[üi]n", o.aciklama or "")
                gun = m.group(1) if m else "-"
                item_gun = QTableWidgetItem(gun)
                item_gun.setTextAlignment(Qt.AlignCenter)
                self.gecmis_table.setItem(i, 2, item_gun)

                item_tutar = QTableWidgetItem()
                item_tutar.setData(Qt.UserRole, o.tutar or 0)
                item_tutar.setText(f"{(o.tutar or 0):,.2f} ₺".replace(",", "."))
                item_tutar.setTextAlignment(Qt.AlignCenter)
                item_tutar.setForeground(QColor("#e67e22"))
                self.gecmis_table.setItem(i, 3, item_tutar)

                sil_btn = QPushButton("✕")
                sil_btn.setFixedSize(28, 28)
                sil_btn.setCursor(Qt.PointingHandCursor)
                sil_btn.setStyleSheet("QPushButton{background:#c0392b;color:white;border-radius:6px;border:none;font-size:12px;font-weight:bold;} QPushButton:hover{background:#e74c3c;}")
                sil_btn.clicked.connect(lambda _, oid=o.id: self._odeme_sil(oid))
                sw = QWidget(); sw.setFixedSize(40, 32); sl = QHBoxLayout(sw); sl.setContentsMargins(0,0,0,0); sl.setAlignment(Qt.AlignCenter); sl.addWidget(sil_btn)
                self.gecmis_table.setCellWidget(i, 4, sw)
        finally:
            yeni_session.close()

    def _odeme_sil(self, odeme_id):
        odeme = self.session.get(MaasOdeme, odeme_id)
        if not odeme:
            return
        personel = self.session.get(Personel, odeme.personel_id)
        ad = personel.ad_soyad if personel else "?"
        if not ModernMesaj.soru(self, f"{ad} — {odeme.tarih.strftime('%d.%m.%Y')} tarihli {odeme.tutar:,.2f} ₺ izin ücreti ödemesi silinsin mi?"):
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
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))
            return
        self._odeme_listesini_yukle()
        self._veri_yukle()
        ModernMesaj.basari(self, "İzin ücreti ödemesi silindi.")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.pos().y() <= 56:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
