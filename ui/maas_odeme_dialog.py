# ui/maas_odeme_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QFrame, QWidget, QHeaderView, QLineEdit,
    QAbstractItemView, QAbstractSpinBox, QStackedWidget, QSizePolicy, QScrollArea,
    QSplitter, QRubberBand, QComboBox
)
from PyQt5.QtCore import Qt, QDate, QSize, QPoint, QRect, QTimer
from PyQt5.QtGui import QColor, QFont, QCursor
import datetime, json, os

from models import MaasOdeme, Bordro, Personel
from ui.utils import ModernMesaj, TarihAlani, get_config_path
from ui.widgets import ToggleSwitch
from sqlalchemy import func


def _tr_lower(t):
    return str(t).replace('İ','i').replace('I','ı').replace('Ğ','ğ').replace('Ü','ü').replace('Ş','ş').replace('Ö','ö').replace('Ç','ç').lower()


class MaasOdemeDialog(QDialog):
    def __init__(self, session, yil, ay, gecerli_bordrolar, elden_sistem, format_tl_fn, parent=None, load_bordrolar_fn=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.session = session
        self.yil = yil
        self.ay = ay
        self.gecerli_bordrolar = gecerli_bordrolar
        self.elden_sistem = elden_sistem
        self.format_tl = format_tl_fn
        self.load_bordrolar_fn = load_bordrolar_fn
        self.elden_bordrolar = [b for b in gecerli_bordrolar if (b.elden_odenecek or 0) > 0] if elden_sistem else []
        self._elden_tarih_widgets = []
        self._drag_pos = None

        self.setAttribute(Qt.WA_TranslucentBackground)
        self._settings_path = get_config_path("maas_odeme_pencere.json")
        self._resize_margin = 8
        self._resize_dir = None
        self._drag_pos = None
        self.setMouseTracking(True)

        # Kaydedilmiş boyut/konum yükle
        saved = self._load_settings()
        if saved:
            self.resize(saved.get("w", 960), saved.get("h", 620))
        else:
            self.resize(960, 620)

        QTimer.singleShot(0, lambda: self._ortala() if not saved else self.move(saved.get("x", 0), saved.get("y", 0)))
        self._init_ui()

    def _ortala(self):
        if self.parent():
            pg = self.parent().frameGeometry()
            self.move(pg.x() + (pg.width() - self.width()) // 2,
                      pg.y() + (pg.height() - self.height()) // 2 - 20)

    # ── Ayarlar kayıt/yükleme ─────────────────────────────────────
    def _save_settings(self):
        try:
            data = {"x": self.x(), "y": self.y(), "w": self.width(), "h": self.height()}
            with open(self._settings_path, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _load_settings(self):
        try:
            if os.path.exists(self._settings_path):
                with open(self._settings_path) as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def closeEvent(self, e):
        self._save_settings()
        super().closeEvent(e)

    def accept(self):
        self._save_settings()
        super().accept()

    def reject(self):
        self._save_settings()
        super().reject()

    # ── Resize yönü hesapla ────────────────────────────────────────
    def _get_resize_dir(self, pos):
        m = self._resize_margin
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        dirs = []
        if x < m: dirs.append("left")
        if x > w - m: dirs.append("right")
        if y < m: dirs.append("top")
        if y > h - m: dirs.append("bottom")
        return dirs or None

    # ── Mouse olayları ────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            dirs = self._get_resize_dir(e.pos())
            if dirs:
                self._resize_dir = dirs
                self._resize_start = e.globalPos()
                self._resize_geom = self.geometry()
            else:
                self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._resize_dir and e.buttons() == Qt.LeftButton:
            dx = e.globalPos().x() - self._resize_start.x()
            dy = e.globalPos().y() - self._resize_start.y()
            r = QRect(self._resize_geom)
            if "right" in self._resize_dir:  r.setRight(r.right() + dx)
            if "bottom" in self._resize_dir: r.setBottom(r.bottom() + dy)
            if "left" in self._resize_dir:   r.setLeft(r.left() + dx)
            if "top" in self._resize_dir:    r.setTop(r.top() + dy)
            if r.width() >= 700 and r.height() >= 500:
                self.setGeometry(r)
        elif self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)
        else:
            dirs = self._get_resize_dir(e.pos())
            if dirs:
                if ("left" in dirs or "right" in dirs) and ("top" in dirs or "bottom" in dirs):
                    cur = Qt.SizeFDiagCursor if (("left" in dirs and "top" in dirs) or ("right" in dirs and "bottom" in dirs)) else Qt.SizeBDiagCursor
                elif "left" in dirs or "right" in dirs:
                    cur = Qt.SizeHorCursor
                else:
                    cur = Qt.SizeVerCursor
                self.setCursor(QCursor(cur))
            else:
                self.setCursor(QCursor(Qt.ArrowCursor))

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        self._resize_dir = None

    # ── UI ────────────────────────────────────────────────────────────
    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; }
            QTableWidget { background:#34495e; border:none; color:white;
                           gridline-color:rgba(255,255,255,0.07); }
            QHeaderView::section { background:#1a2a38; color:#bdc3c7;
                                   font-weight:bold; padding:8px; border:none; }
            QTableWidget::item { padding:5px; }
            QTableWidget::item:selected { background:rgba(52,152,219,0.35); color:white; }
            QLineEdit { background:#1a2a38; border:1px solid #4a6278; border-radius:6px;
                        color:white; padding:4px 10px; font-size:12px; }
            QLineEdit:focus { border-color:#3498db; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        # ── Başlık (sürüklenebilir) ────────────────────────────────
        hdr = QFrame()
        hdr.setFixedHeight(66)
        hdr.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a5c38,stop:1 #27ae60);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        hdr.mousePressEvent   = self.mousePressEvent
        hdr.mouseMoveEvent    = self.mouseMoveEvent
        hdr.mouseReleaseEvent = self.mouseReleaseEvent
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(20,0,16,0); hdr_lay.setSpacing(12)
        ic = QLabel("💸"); ic.setFixedSize(44,44); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:22px;font-size:20px;")
        self.header_title = QLabel(f"Maaş Ödemesi — {self.ay:02d}/{self.yil}")
        self.header_title.setStyleSheet("color:white;font-size:14px;font-weight:bold;")
        sub = QLabel("Elden ödemeli sistem aktif" if self.elden_sistem else "Tek maaş sistemi")
        sub.setStyleSheet("color:rgba(255,255,255,0.6);font-size:11px;")
        txt = QVBoxLayout(); txt.setSpacing(1); txt.addWidget(self.header_title); txt.addWidget(sub)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(28,28)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:15px;border:none;} QPushButton:hover{color:white;}")
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(ic); hdr_lay.addLayout(txt); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        # ── Dönem Seçici ──────────────────────────────────────────
        if self.load_bordrolar_fn:
            donem_bar = QFrame()
            donem_bar.setFixedHeight(46)
            donem_bar.setStyleSheet("QFrame{background:#1e3a50;border:none;}")
            donem_h = QHBoxLayout(donem_bar); donem_h.setContentsMargins(16,6,16,6); donem_h.setSpacing(8)

            donem_lbl = QLabel("Dönem:"); donem_lbl.setStyleSheet("color:#bdc3c7;font-size:12px;font-weight:bold;")
            donem_h.addWidget(donem_lbl)

            self.donem_yil_cb = QComboBox(); self.donem_yil_cb.setFixedWidth(80); self.donem_yil_cb.setFixedHeight(30)
            self.donem_yil_cb.setStyleSheet("QComboBox{background:#1a2a38;color:white;border:1px solid #4a6278;border-radius:4px;padding:2px 8px;font-size:12px;} QComboBox::drop-down{border:none;} QComboBox QAbstractItemView{background:#1a2a38;color:white;selection-background-color:#3498db;}")
            mevcut_yil = datetime.date.today().year
            for y in range(mevcut_yil - 5, mevcut_yil + 2):
                self.donem_yil_cb.addItem(str(y))
            self.donem_yil_cb.setCurrentText(str(self.yil))
            donem_h.addWidget(self.donem_yil_cb)

            donem_h.addWidget(QLabel("/"))

            self.donem_ay_cb = QComboBox(); self.donem_ay_cb.setFixedWidth(100); self.donem_ay_cb.setFixedHeight(30)
            self.donem_ay_cb.setStyleSheet("QComboBox{background:#1a2a38;color:white;border:1px solid #4a6278;border-radius:4px;padding:2px 8px;font-size:12px;} QComboBox::drop-down{border:none;} QComboBox QAbstractItemView{background:#1a2a38;color:white;selection-background-color:#3498db;}")
            ay_isimleri = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
            for a in ay_isimleri:
                self.donem_ay_cb.addItem(a)
            self.donem_ay_cb.setCurrentIndex(self.ay - 1)
            donem_h.addWidget(self.donem_ay_cb)

            self.donem_yukle_btn = QPushButton("📋 Dönem Getir")
            self.donem_yukle_btn.setFixedHeight(30); self.donem_yukle_btn.setCursor(Qt.PointingHandCursor)
            self.donem_yukle_btn.setStyleSheet("QPushButton{background:#3498db;color:white;font-weight:bold;border-radius:6px;border:none;padding:0 14px;font-size:11px;} QPushButton:hover{background:#2980b9;}")
            self.donem_yukle_btn.clicked.connect(self._donem_yukle)
            donem_h.addWidget(self.donem_yukle_btn)

            donem_h.addStretch()
            outer_lay.addWidget(donem_bar)

        # ── Sekmeler ──────────────────────────────────────────────
        tab_bar = QFrame()
        tab_bar.setFixedHeight(40)
        tab_bar.setStyleSheet("QFrame{background:#1a2a38;border:none;}")
        tab_h = QHBoxLayout(tab_bar); tab_h.setContentsMargins(0,0,0,0); tab_h.setSpacing(0)

        self.btn_banka = QPushButton("🏦  Banka Ödemeleri")
        self.btn_banka.setFixedHeight(40); self.btn_banka.setCursor(Qt.PointingHandCursor)
        self.btn_elden = QPushButton("🤝  Elden Ödemeler")
        self.btn_elden.setFixedHeight(40); self.btn_elden.setCursor(Qt.PointingHandCursor)
        if not self.elden_sistem:
            self.btn_elden.setEnabled(False)
            self.btn_elden.setStyleSheet("QPushButton{background:transparent;color:#4a6278;font-size:12px;border:none;padding:0 20px;}")
        tab_h.addWidget(self.btn_banka); tab_h.addWidget(self.btn_elden); tab_h.addStretch()
        outer_lay.addWidget(tab_bar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background:transparent;")
        outer_lay.addWidget(self.stack, 1)

        self._build_banka_panel()
        self._build_elden_panel()

        # ── Footer ────────────────────────────────────────────────
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border:none;border-top:1px solid #1a2a38;}")
        foot_h = QHBoxLayout(footer); foot_h.setContentsMargins(16,10,16,10); foot_h.setSpacing(8)

        self.banka_kaydet_btn = QPushButton("💳 Banka Ödemelerini Kaydet")
        self.banka_kaydet_btn.setFixedHeight(38); self.banka_kaydet_btn.setCursor(Qt.PointingHandCursor)
        self.banka_kaydet_btn.setStyleSheet("QPushButton{background:#27ae60;color:white;font-weight:bold;border-radius:8px;border:none;padding:0 16px;font-size:12px;} QPushButton:hover{background:#2ecc71;}")
        self.banka_kaydet_btn.clicked.connect(self._banka_kaydet)

        self.elden_kaydet_btn = QPushButton("🤝 Elden Ödemeleri Kaydet")
        self.elden_kaydet_btn.setFixedHeight(38); self.elden_kaydet_btn.setCursor(Qt.PointingHandCursor)
        self.elden_kaydet_btn.setStyleSheet("QPushButton{background:#e67e22;color:white;font-weight:bold;border-radius:8px;border:none;padding:0 16px;font-size:12px;} QPushButton:hover{background:#d35400;}")
        self.elden_kaydet_btn.setEnabled(bool(self.elden_bordrolar))
        self.elden_kaydet_btn.clicked.connect(self._elden_kaydet)

        iptal_btn = QPushButton("Kapat")
        iptal_btn.setFixedHeight(38)
        iptal_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 16px;} QPushButton:hover{background:#34495e;color:white;}")
        iptal_btn.clicked.connect(self.reject)

        foot_h.addWidget(self.banka_kaydet_btn)
        foot_h.addWidget(self.elden_kaydet_btn)
        foot_h.addStretch()
        foot_h.addWidget(iptal_btn)
        outer_lay.addWidget(footer)

        # Tab bağlantıları
        self.btn_banka.clicked.connect(lambda: self._switch('banka'))
        self.btn_elden.clicked.connect(lambda: self._switch('elden'))
        self._switch('banka')

    def _tab_style(self, active):
        if active:
            return "QPushButton{background:transparent;color:white;font-size:12px;font-weight:bold;border:none;border-bottom:2px solid #3498db;padding:0 20px;}"
        return "QPushButton{background:transparent;color:#7f8c8d;font-size:12px;border:none;padding:0 20px;} QPushButton:hover{color:#bdc3c7;}"

    def _switch(self, sekme):
        self.stack.setCurrentIndex(0 if sekme == 'banka' else 1)
        self.btn_banka.setStyleSheet(self._tab_style(sekme == 'banka'))
        if self.elden_sistem:
            self.btn_elden.setStyleSheet(self._tab_style(sekme == 'elden'))
        self.banka_kaydet_btn.setVisible(sekme == 'banka')
        self.elden_kaydet_btn.setVisible(sekme == 'elden')

    def _donem_yukle(self):
        yil = int(self.donem_yil_cb.currentText())
        ay = self.donem_ay_cb.currentIndex() + 1
        self.yil = yil
        self.ay = ay

        bordrolar = self.load_bordrolar_fn(yil, ay)
        self.gecerli_bordrolar = bordrolar
        self.elden_bordrolar = [b for b in bordrolar if (b.elden_odenecek or 0) > 0] if self.elden_sistem else []

        self._doldur_banka_table(self.gecerli_bordrolar)
        self._doldur_elden_table(self.elden_bordrolar)
        self.elden_kaydet_btn.setEnabled(bool(self.elden_bordrolar))

        toplam = len(self.gecerli_bordrolar)
        self.header_title.setText(f"Maaş Ödemesi — {ay:02d}/{yil}  ({toplam} personel)")

    # ── Banka Paneli ─────────────────────────────────────────────
    def _build_banka_panel(self):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w); lay.setContentsMargins(16,10,16,8); lay.setSpacing(8)

        # Tarih
        t_row = QHBoxLayout()
        t_lbl = QLabel("Ödeme Tarihi:"); t_lbl.setStyleSheet("color:#bdc3c7;font-size:12px;")
        self.banka_tarih = TarihAlani()
        self.banka_tarih.set_date(QDate.currentDate())
        t_row.addWidget(t_lbl); t_row.addWidget(self.banka_tarih); t_row.addStretch()
        lay.addLayout(t_row)

        # Tablo
        self.banka_table = QTableWidget()
        self.banka_table.setColumnCount(6)
        self.banka_table.setHorizontalHeaderLabels(["Seçim","Sicil","Personel","Net Maaş","Banka","Elden"])
        hdr = self.banka_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setSectionsMovable(True)
        hdr.setSectionResizeMode(0, QHeaderView.Fixed)
        self.banka_table.setColumnWidth(0, 55)
        self.banka_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.banka_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.banka_table.verticalHeader().setVisible(False)
        self._doldur_banka_table(self.gecerli_bordrolar)
        self._load_banka_widths()
        hdr.sectionResized.connect(self._banka_auto_save)
        hdr.sectionMoved.connect(self._banka_auto_save)
        lay.addWidget(self.banka_table)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        ts = QPushButton("✅ Tümünü Seç"); ts.setFixedHeight(30)
        ts.setStyleSheet("QPushButton{background:#3498db;color:white;font-weight:bold;border-radius:6px;border:none;padding:0 12px;font-size:11px;} QPushButton:hover{background:#2980b9;}")
        ts.clicked.connect(lambda: self._banka_isaretle(True))
        tk = QPushButton("❌ Tümünü Kaldır"); tk.setFixedHeight(30)
        tk.setStyleSheet("QPushButton{background:#636e72;color:white;font-weight:bold;border-radius:6px;border:none;padding:0 12px;font-size:11px;} QPushButton:hover{background:#4a4f52;}")
        tk.clicked.connect(lambda: self._banka_isaretle(False))
        btn_row.addWidget(ts); btn_row.addWidget(tk); btn_row.addStretch()
        lay.addLayout(btn_row)
        self.stack.addWidget(w)

    def _doldur_banka_table(self, bordrolar):
        self.banka_table.setRowCount(0)
        for i, b in enumerate(bordrolar):
            self.banka_table.insertRow(i)
            toggle = ToggleSwitch(width=28, height=16)
            toggle.setChecked(False)
            tw = QWidget(); tw.setFixedSize(36,24)
            tl = QHBoxLayout(tw); tl.setAlignment(Qt.AlignCenter); tl.setContentsMargins(0,0,0,0); tl.addWidget(toggle)
            self.banka_table.setCellWidget(i, 0, tw)
            self.banka_table.setItem(i, 1, QTableWidgetItem(b.personel.sicil_no or ""))
            self.banka_table.setItem(i, 2, QTableWidgetItem(b.personel.ad_soyad))
            self.banka_table.setItem(i, 3, QTableWidgetItem(self.format_tl(b.toplam_net_maas)))
            banka_t = b.resmi_maas if self.elden_sistem else b.toplam_net_maas
            elden_t = b.elden_odenecek if self.elden_sistem else 0
            self.banka_table.setItem(i, 4, QTableWidgetItem(self.format_tl(banka_t)))
            it5 = QTableWidgetItem(self.format_tl(elden_t) if elden_t else "—")
            if elden_t: it5.setForeground(QColor("#e67e22"))
            self.banka_table.setItem(i, 5, it5)
            self.banka_table.setRowHeight(i, 28)

    def _banka_isaretle(self, sec):
        for row in range(self.banka_table.rowCount()):
            w = self.banka_table.cellWidget(row, 0)
            if w:
                t = w.findChild(ToggleSwitch)
                if t: t.setChecked(sec)

    # ── Elden Paneli ──────────────────────────────────────────────
    def _build_elden_panel(self):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w); lay.setContentsMargins(16,10,16,8); lay.setSpacing(8)

        # Bilgi çubuğu
        bilgi = QFrame()
        bilgi.setStyleSheet("QFrame{background:#2a2a1a;border-radius:6px;border:1px solid #f39c12;}")
        bilgi_h = QHBoxLayout(bilgi); bilgi_h.setContentsMargins(10,5,10,5)
        bilgi_lbl = QLabel("ℹ️  Elden ödemeler nakit yapılır. Kısmi ödeme yapılabilir.")
        bilgi_lbl.setStyleSheet("color:#f39c12;font-size:11px;")
        bilgi_h.addWidget(bilgi_lbl)
        lay.addWidget(bilgi)

        # Arama — tam satır
        self.elden_arama = QLineEdit()
        self.elden_arama.setPlaceholderText("🔍 Personel ara... (Türkçe büyük/küçük harf duyarsız)")
        self.elden_arama.setFixedHeight(32)
        self.elden_arama.textChanged.connect(self._elden_filtrele)
        lay.addWidget(self.elden_arama)

        # Tablo — 8 sütun
        self.elden_table = QTableWidget()
        self.elden_table.setColumnCount(8)
        self.elden_table.setHorizontalHeaderLabels([
            "Seçim", "Personel", "Elden Tutar", "Önceki Ödeme", "Kalan", "Bu Sefer", "Ödeme Tarihi", "Durum"
        ])
        hdr = self.elden_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setSectionsMovable(True)
        hdr.setSectionResizeMode(0, QHeaderView.Fixed); self.elden_table.setColumnWidth(0, 50)
        self.elden_table.setColumnWidth(1, 200)
        self.elden_table.setColumnWidth(2, 100)
        self.elden_table.setColumnWidth(3, 100)
        self.elden_table.setColumnWidth(4, 90)
        self.elden_table.setColumnWidth(5, 100)
        self.elden_table.setColumnWidth(6, 110)
        self.elden_table.setColumnWidth(7, 75)
        hdr.sectionResized.connect(self._elden_auto_save)
        hdr.sectionMoved.connect(self._elden_auto_save)
        self._load_elden_widths()
        self.elden_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.elden_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.elden_table.verticalHeader().setVisible(False)
        self.elden_table.cellDoubleClicked.connect(self._elden_personel_cift_tikla)
        self._elden_tarih_widgets = []
        self._elden_tutar_widgets = []
        self._doldur_elden_table(self.elden_bordrolar)
        lay.addWidget(self.elden_table)

        # Alt butonlar + özet
        alt_row = QHBoxLayout(); alt_row.setSpacing(8)
        ts = QPushButton("✅ Tümünü Seç"); ts.setFixedHeight(30)
        ts.setStyleSheet("QPushButton{background:#3498db;color:white;font-weight:bold;border-radius:6px;border:none;padding:0 12px;font-size:11px;} QPushButton:hover{background:#2980b9;}")
        ts.clicked.connect(lambda: self._elden_isaretle(True))
        tk = QPushButton("❌ Tümünü Kaldır"); tk.setFixedHeight(30)
        tk.setStyleSheet("QPushButton{background:#636e72;color:white;font-weight:bold;border-radius:6px;border:none;padding:0 12px;font-size:11px;} QPushButton:hover{background:#4a4f52;}")
        tk.clicked.connect(lambda: self._elden_isaretle(False))
        alt_row.addWidget(ts); alt_row.addWidget(tk); alt_row.addStretch()

        toplam_elden = sum((b.elden_odenecek or 0) for b in self.elden_bordrolar)
        oz1 = QLabel(f"Toplam Elden: <b style='color:#e67e22'>{self.format_tl(toplam_elden)}</b>")
        oz1.setTextFormat(Qt.RichText)
        oz2 = QLabel(f"Personel: <b style='color:#3498db'>{len(self.elden_bordrolar)}</b>")
        oz2.setTextFormat(Qt.RichText)
        alt_row.addWidget(oz1); alt_row.addSpacing(12); alt_row.addWidget(oz2)
        lay.addLayout(alt_row)
        self.stack.addWidget(w)

    def _elden_widths_path(self):
        return get_config_path("elden_tablo_widths.json")

    def _elden_auto_save(self, *args):
        widths = {str(i): self.elden_table.columnWidth(i) for i in range(self.elden_table.columnCount())}
        order = [self.elden_table.horizontalHeader().logicalIndex(v) for v in range(self.elden_table.columnCount())]
        try:
            with open(self._elden_widths_path(), "w", encoding="utf-8") as f:
                json.dump({"widths": widths, "order": order}, f)
        except Exception:
            pass

    def _load_elden_widths(self):
        try:
            if os.path.exists(self._elden_widths_path()):
                with open(self._elden_widths_path()) as f:
                    data = json.load(f)
                widths = data if "widths" not in data else data["widths"]
                for i, w in widths.items():
                    self.elden_table.setColumnWidth(int(i), int(w))
                hdr = self.elden_table.horizontalHeader()
                for visual, logical in enumerate(data.get("order", [])):
                    cur = hdr.logicalIndex(visual)
                    if cur != logical:
                        hdr.moveSection(hdr.visualIndex(logical), visual)
        except Exception:
            pass

    def _banka_widths_path(self):
        return get_config_path("banka_tablo_widths.json")

    def _banka_auto_save(self, *args):
        widths = {str(i): self.banka_table.columnWidth(i) for i in range(self.banka_table.columnCount())}
        hdr = self.banka_table.horizontalHeader()
        order = [hdr.logicalIndex(v) for v in range(self.banka_table.columnCount())]
        try:
            with open(self._banka_widths_path(), "w", encoding="utf-8") as f:
                json.dump({"widths": widths, "order": order}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_banka_widths(self):
        try:
            if os.path.exists(self._banka_widths_path()):
                with open(self._banka_widths_path()) as f:
                    data = json.load(f)
                widths = data if "widths" not in data else data["widths"]
                for i, w in widths.items():
                    self.banka_table.setColumnWidth(int(i), int(w))
                hdr = self.banka_table.horizontalHeader()
                for visual, logical in enumerate(data.get("order", [])):
                    cur = hdr.logicalIndex(visual)
                    if cur != logical:
                        hdr.moveSection(hdr.visualIndex(logical), visual)
        except Exception:
            pass

    def _doldur_elden_table(self, bordrolar):
        from PyQt5.QtWidgets import QDoubleSpinBox
        self.elden_table.setRowCount(0)
        self._elden_tarih_widgets = []
        self._elden_tutar_widgets = []
        self._elden_row_bordrolar = []

        for i, b in enumerate(bordrolar):
            self.elden_table.insertRow(i)
            self.elden_table.setRowHeight(i, 44)
            self._elden_row_bordrolar.append(b)

            # Önceki elden ödemeler — tutar sütunu kullan
            odemeler = self.session.query(MaasOdeme).filter(
                MaasOdeme.bordro_id == b.id,
                func.lower(MaasOdeme.aciklama).like("%elden%")
            ).order_by(MaasOdeme.tarih).all()
            toplam_odenen = sum(o.tutar or 0 for o in odemeler)
            elden_tutar = b.elden_odenecek or 0
            kalan = max(elden_tutar - toplam_odenen, 0)
            zaten_tamam = kalan <= 0

            toggle = ToggleSwitch(width=28, height=16)
            toggle.setChecked(False)
            tw = QWidget(); tw.setFixedSize(36, 24)
            tl = QHBoxLayout(tw); tl.setAlignment(Qt.AlignCenter); tl.setContentsMargins(0,0,0,0); tl.addWidget(toggle)
            self.elden_table.setCellWidget(i, 0, tw)

            ad_item = QTableWidgetItem(f"{b.personel.ad_soyad} ({b.personel.sicil_no})")
            self.elden_table.setItem(i, 1, ad_item)

            t_item = QTableWidgetItem(self.format_tl(elden_tutar))
            t_item.setTextAlignment(Qt.AlignCenter)
            t_item.setForeground(QColor("#e67e22"))
            fnt = QFont(); fnt.setBold(True); t_item.setFont(fnt)
            self.elden_table.setItem(i, 2, t_item)

            o_item = QTableWidgetItem(self.format_tl(toplam_odenen) if toplam_odenen > 0 else "\u2014")
            o_item.setTextAlignment(Qt.AlignCenter)
            o_item.setForeground(QColor("#2ecc71"))
            self.elden_table.setItem(i, 3, o_item)

            k_item = QTableWidgetItem("\u2705 Tamamland\u0131" if zaten_tamam else self.format_tl(kalan))
            k_item.setTextAlignment(Qt.AlignCenter)
            k_item.setForeground(QColor("#2ecc71") if zaten_tamam else QColor("#e74c3c"))
            self.elden_table.setItem(i, 4, k_item)

            spin = QDoubleSpinBox()
            spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
            spin.setMinimum(0.0)
            spin.setMaximum(max(kalan, 0.01))
            spin.setValue(kalan)
            spin.setDecimals(2)
            spin.setEnabled(not zaten_tamam)
            spin.setStyleSheet("QDoubleSpinBox{background:#1a2a38;color:white;border:1px solid #4a6278;border-radius:4px;padding:2px 4px;font-size:11px;} QDoubleSpinBox:disabled{color:#4a6278;}")
            self.elden_table.setCellWidget(i, 5, spin)
            self._elden_tutar_widgets.append(spin)

            tarih_w = TarihAlani()
            tarih_w.set_date(QDate.currentDate())
            self.elden_table.setCellWidget(i, 6, tarih_w)
            self._elden_tarih_widgets.append(tarih_w)

            if zaten_tamam:
                d_item = QTableWidgetItem("\u2705 \u00d6dendi")
                d_item.setForeground(QColor("#2ecc71"))
            elif toplam_odenen > 0:
                d_item = QTableWidgetItem("\u23f3 K\u0131smi")
                d_item.setForeground(QColor("#f39c12"))
            else:
                d_item = QTableWidgetItem("\u23f3 Bekliyor")
                d_item.setForeground(QColor("#f39c12"))
            d_item.setTextAlignment(Qt.AlignCenter)
            self.elden_table.setItem(i, 7, d_item)



    def _elden_personel_cift_tikla(self, row, col):
        if col != 1:
            return
        if row < 0 or row >= len(self._elden_row_bordrolar):
            return
        b = self._elden_row_bordrolar[row]

        def _build_gecmis_dialog():
            nonlocal dialog
            odemeler = self.session.query(MaasOdeme).filter(
                MaasOdeme.bordro_id == b.id,
                func.lower(MaasOdeme.aciklama).like("%elden%")
            ).order_by(MaasOdeme.tarih).all()

            for i in reversed(range(body_lay.count())):
                item = body_lay.itemAt(i)
                if item and item.widget():
                    item.widget().deleteLater()

            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Tarih", "Tutar", ""])
            hdr = table.horizontalHeader()
            hdr.setSectionResizeMode(0, QHeaderView.Stretch)
            hdr.setSectionResizeMode(1, QHeaderView.Stretch)
            hdr.setSectionResizeMode(2, QHeaderView.Fixed)
            table.setColumnWidth(2, 50)
            table.verticalHeader().setVisible(False)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setRowCount(len(odemeler))
            toplam = 0
            for i, o in enumerate(odemeler):
                table.setRowHeight(i, 36)
                table.setItem(i, 0, QTableWidgetItem(o.tarih.strftime("%d.%m.%Y") if o.tarih else ""))
                item = QTableWidgetItem(f"{o.tutar:,.2f}".replace(",", "."))
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, 1, item)
                toplam += o.tutar

                sil_btn = QPushButton("🗑")
                sil_btn.setFixedSize(34, 26)
                sil_btn.setCursor(Qt.PointingHandCursor)
                sil_btn.setToolTip("Bu ödemeyi sil")
                sil_btn.setStyleSheet("QPushButton{background:#c0392b;color:white;border-radius:4px;border:none;font-size:12px;} QPushButton:hover{background:#e74c3c;}")
                sil_btn.clicked.connect(lambda checked, oid=o.id: self._elden_odeme_sil(oid, _build_gecmis_dialog))
                sil_w = QWidget(); sil_w.setStyleSheet("background:transparent;")
                sil_l = QHBoxLayout(sil_w); sil_l.setContentsMargins(2,2,2,2); sil_l.setAlignment(Qt.AlignCenter)
                sil_l.addWidget(sil_btn)
                table.setCellWidget(i, 2, sil_w)

            body_lay.addWidget(table)

            ozet = QLabel(f"Toplam: <b style='color:#e67e22'>{toplam:,.2f}</b>  |  {len(odemeler)} ödeme")
            ozet.setTextFormat(Qt.RichText)
            ozet.setStyleSheet("color:#bdc3c7;font-size:12px;")
            body_lay.addWidget(ozet)

        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QPushButton, QFrame
        from PyQt5.QtCore import Qt

        dialog = QDialog(self, Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        dialog.resize(500, 380)

        root = QVBoxLayout(dialog)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(dialog)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; }
            QTableWidget { background:#34495e; border:1px solid #4a6278; border-radius:8px; color:white;
                           gridline-color:rgba(255,255,255,0.07); }
            QHeaderView::section { background:#1a2a38; color:#bdc3c7;
                                   font-weight:bold; padding:8px; border:none; }
            QTableWidget::item { padding:5px; }
            QTableWidget::item:selected { background:rgba(52,152,219,0.35); color:white; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a5c38,stop:1 #27ae60);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 12, 0); hdr_lay.setSpacing(12)
        ic = QLabel("📋"); ic.setFixedSize(40, 40); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:20px;font-size:18px;")
        tl = QLabel(f"Elden Ödeme Geçmişi")
        tl.setStyleSheet("color:white;font-size:13px;font-weight:bold;")
        sub = QLabel(f"{b.personel.ad_soyad} ({b.personel.sicil_no})")
        sub.setStyleSheet("color:rgba(255,255,255,0.6);font-size:11px;")
        txt = QVBoxLayout(); txt.setSpacing(1); txt.addWidget(tl); txt.addWidget(sub)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:14px;border:none;} QPushButton:hover{color:white;}")
        close_btn.clicked.connect(dialog.close)
        hdr_lay.addWidget(ic); hdr_lay.addLayout(txt); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body); body_lay.setContentsMargins(16, 14, 16, 10); body_lay.setSpacing(10)
        outer_lay.addWidget(body, 1)

        footer = QFrame()
        footer.setFixedHeight(54)
        footer.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border:none;border-top:1px solid #1a2a38;}")
        foot_lay = QHBoxLayout(footer); foot_lay.setContentsMargins(16, 8, 16, 8)
        kapat_btn = QPushButton("Kapat")
        kapat_btn.setFixedHeight(36)
        kapat_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 16px;font-size:12px;} QPushButton:hover{background:#34495e;color:white;}")
        kapat_btn.clicked.connect(dialog.close)
        foot_lay.addStretch(); foot_lay.addWidget(kapat_btn)
        outer_lay.addWidget(footer)

        _build_gecmis_dialog()
        dialog.exec_()


    def _elden_filtrele(self, text):
        aranan = _tr_lower(text.strip())
        for row in range(self.elden_table.rowCount()):
            item = self.elden_table.item(row, 1)
            if item:
                goster = not aranan or aranan in _tr_lower(item.text())
                self.elden_table.setRowHidden(row, not goster)

    def _elden_isaretle(self, sec):
        for row in range(self.elden_table.rowCount()):
            if self.elden_table.isRowHidden(row):
                continue
            w = self.elden_table.cellWidget(row, 0)
            if w:
                t = w.findChild(ToggleSwitch)
                if t: t.setChecked(sec)

    # ── Kayıt ─────────────────────────────────────────────────────
    def _banka_kaydet(self):
        try:
            tarih = self.banka_tarih.get_pydate()
            secilenler = []
            for i, b in enumerate(self.gecerli_bordrolar):
                w = self.banka_table.cellWidget(i, 0)
                if w:
                    t = w.findChild(ToggleSwitch)
                    if t and t.isChecked():
                        secilenler.append(b)
            if not secilenler:
                ModernMesaj.uyari(self, "Lütfen en az bir personel seçin.")
                return
            once_odenmis = []
            yeni_eklenecek = []
            for b in secilenler:
                mev = self.session.query(MaasOdeme).filter(MaasOdeme.bordro_id == b.id,
                      ~func.lower(MaasOdeme.aciklama).like("%elden%")).first()
                if mev:
                    once_odenmis.append(b)
                else:
                    yeni_eklenecek.append(b)
            if once_odenmis:
                isim_list = [f"• {b.personel.ad_soyad}" for b in once_odenmis[:15]]
                if len(once_odenmis) > 15:
                    isim_list.append(f"• ... ve {len(once_odenmis) - 15} kişi daha")
                isimler = "\n".join(isim_list)
                if not ModernMesaj.soru(self, f"Aşağıdaki personeller için banka ödemesi zaten kayıtlı.\nTekrar ödeme yapılsın mı?\n\n{isimler}"):
                    once_odenmis = []
            for b in once_odenmis + yeni_eklenecek:
                banka_t = b.resmi_maas if self.elden_sistem else b.toplam_net_maas
                o = MaasOdeme(personel_id=b.personel.id, bordro_id=b.id, tarih=tarih,
                              tutar=banka_t, aciklama=f"{self.yil}-{self.ay} banka ödemesi")
                self.session.add(o)
            self.session.commit()
            ModernMesaj.basari(self, f"{len(once_odenmis) + len(yeni_eklenecek)} personele Bankadan Ödeme yapıldı.")
            self._donem_yukle()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))

    def _elden_odeme_sil(self, odeme_id, refresh_callback):
        from ui.utils import ModernMesaj
        try:
            o = self.session.query(MaasOdeme).get(odeme_id)
            if not o:
                ModernMesaj.uyari(self, "Ödeme kaydı bulunamadı.")
                return
            if not ModernMesaj.soru(self, f"{self.format_tl(o.tutar)} tutarındaki elden ödeme silinecek. Onaylıyor musunuz?"):
                return
            self.session.delete(o)
            self.session.commit()
            ModernMesaj.basari(self, "Elden ödeme silindi.")
            self._doldur_elden_table(self.elden_bordrolar)
            refresh_callback()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))

    def _elden_kaydet(self):
        try:
            secilenler = []
            for i in range(self.elden_table.rowCount()):
                if self.elden_table.isRowHidden(i):
                    continue
                w = self.elden_table.cellWidget(i, 0)
                if w:
                    t = w.findChild(ToggleSwitch)
                    if t and t.isChecked():
                        b = self._elden_row_bordrolar[i]
                        tarih_w = self._elden_tarih_widgets[i]
                        spin = self._elden_tutar_widgets[i]
                        tutar = spin.value()
                        if tutar > 0:
                            secilenler.append((b, tarih_w.get_pydate(), tutar))
            if not secilenler:
                ModernMesaj.uyari(self, "Lütfen en az bir personel seçin veya tutar girin.")
                return
            for b, tarih, tutar in secilenler:
                o = MaasOdeme(
                    personel_id=b.personel.id,
                    bordro_id=b.id,
                    tarih=tarih,
                    tutar=tutar,
                    aciklama=f"{self.yil}-{self.ay} elden ödeme"
                )
                self.session.add(o)
            self.session.commit()
            isimler = "\n".join(f"• {b.personel.ad_soyad} — {self.format_tl(tutar)}" for b, _, tutar in secilenler)
            ModernMesaj.basari(self, f"{len(secilenler)} personele Elden Ödeme yapıldı:\n\n{isimler}")
            self._donem_yukle()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))
