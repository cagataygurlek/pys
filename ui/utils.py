# ui/utils.py
# Paylaşılan UI yardımcı sınıfları

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QStyledItemDelegate
)
from PyQt5.QtCore import Qt, QEvent, pyqtSignal, QRect
from PyQt5.QtGui import QPainter, QColor, QFont

class ModernMesaj(QDialog):
    """QMessageBox yerine kullanılan koyu temalı modern mesaj kutusu."""

    BASARI = "basari"
    UYARI  = "uyari"
    HATA   = "hata"
    SORU   = "soru"

    def __init__(self, parent, tip, baslik, mesaj):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setFixedWidth(400)
        self.cevap = False

        renk_map = {
            self.BASARI: ("#27ae60", "#1a5c38"),
            self.UYARI:  ("#f39c12", "#7d5109"),
            self.HATA:   ("#e74c3c", "#7b241c"),
            self.SORU:   ("#3498db", "#1a5276"),
        }
        ikon_map = {
            self.BASARI: "✓",
            self.UYARI:  "!",
            self.HATA:   "✕",
            self.SORU:   "?",
        }
        ana_renk, koyu_renk = renk_map.get(tip, renk_map[self.BASARI])
        ikon = ikon_map.get(tip, "✓")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: #2c3e50;
                border: 1px solid {ana_renk};
                border-radius: 12px;
            }}
            QLabel {{ background: transparent; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Üst renkli şerit
        top = QFrame()
        top.setFixedHeight(72)
        top.setStyleSheet(f"""
            QFrame {{
                background-color: {koyu_renk};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
        """)
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(20, 0, 20, 0)

        ikon_lbl = QLabel(ikon)
        ikon_lbl.setFixedSize(40, 40)
        ikon_lbl.setAlignment(Qt.AlignCenter)
        ikon_lbl.setStyleSheet(f"""
            background-color: {ana_renk};
            color: white; font-size: 20px; font-weight: bold;
            border-radius: 20px;
        """)
        top_lay.addWidget(ikon_lbl)

        baslik_lbl = QLabel(baslik)
        baslik_lbl.setStyleSheet(
            "color: white; font-size: 14px; font-weight: bold; padding-left: 12px;")
        top_lay.addWidget(baslik_lbl)
        top_lay.addStretch()
        lay.addWidget(top)

        # Mesaj alanı
        msg_frame = QFrame()
        msg_frame.setStyleSheet("QFrame { background-color: #2c3e50; }")
        msg_lay = QVBoxLayout(msg_frame)
        msg_lay.setContentsMargins(24, 18, 24, 14)

        msg_lbl = QLabel(mesaj)
        msg_lbl.setStyleSheet("color: #ecf0f1; font-size: 12px; line-height: 1.5;")
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        msg_lay.addWidget(msg_lbl)
        lay.addWidget(msg_frame)

        # Buton şeridi
        btn_frame = QFrame()
        btn_frame.setStyleSheet("""
            QFrame {
                background-color: #243342;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                border-top: 1px solid #1a2a38;
            }
        """)
        btn_frame.setFixedHeight(56)
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setContentsMargins(16, 8, 16, 8)
        btn_lay.setSpacing(8)
        btn_lay.addStretch()

        if tip == self.SORU:
            evet_btn = QPushButton("Evet")
            evet_btn.setFixedSize(90, 36)
            evet_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ana_renk}; color: white;
                    font-weight: bold; border-radius: 6px; border: none;
                }}
                QPushButton:hover {{ background-color: {koyu_renk}; }}
            """)
            evet_btn.clicked.connect(self._evet)
            btn_lay.addWidget(evet_btn)

            hayir_btn = QPushButton("Hayır")
            hayir_btn.setFixedSize(90, 36)
            hayir_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent; color: #bdc3c7;
                    font-weight: bold; border-radius: 6px;
                    border: 1px solid #4a6278;
                }
                QPushButton:hover { background-color: #34495e; color: white; }
            """)
            hayir_btn.clicked.connect(self.reject)
            btn_lay.addWidget(hayir_btn)
        else:
            tamam_btn = QPushButton("Tamam")
            tamam_btn.setFixedSize(100, 36)
            tamam_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ana_renk}; color: white;
                    font-weight: bold; border-radius: 6px; border: none;
                }}
                QPushButton:hover {{ background-color: {koyu_renk}; }}
            """)
            tamam_btn.clicked.connect(self.accept)
            btn_lay.addWidget(tamam_btn)

        lay.addWidget(btn_frame)
        self.adjustSize()

    def _evet(self):
        self.cevap = True
        self.accept()

    @staticmethod
    def basari(parent, mesaj, baslik="Başarılı"):
        ModernMesaj(parent, ModernMesaj.BASARI, baslik, mesaj).exec_()

    @staticmethod
    def uyari(parent, mesaj, baslik="Uyarı"):
        ModernMesaj(parent, ModernMesaj.UYARI, baslik, mesaj).exec_()

    @staticmethod
    def hata(parent, mesaj, baslik="Hata"):
        ModernMesaj(parent, ModernMesaj.HATA, baslik, mesaj).exec_()

    @staticmethod
    def soru(parent, mesaj, baslik="Onay") -> bool:
        d = ModernMesaj(parent, ModernMesaj.SORU, baslik, mesaj)
        d.exec_()
        return d.cevap


# ─────────────────────────────────────────────
# MODERN TAKVİM DİALOGU
# ─────────────────────────────────────────────

class ModernTarihSecici(QDialog):
    """Tüm sayfalar için ortak modern takvim dialogu"""
    def __init__(self, parent=None, baslangic_tarihi=None):
        from PyQt5.QtWidgets import QCalendarWidget, QDialogButtonBox, QVBoxLayout
        from PyQt5.QtCore import QDate, QLocale
        super().__init__(parent)
        self.setWindowTitle("Tarih Seç")
        self.setModal(True)
        self.setFixedSize(440, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                border-radius: 15px;
            }
            QCalendarWidget {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #3498db;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                min-height: 44px;
            }
            QCalendarWidget QToolButton {
                background-color: transparent;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 6px 12px;
                min-width: 60px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #2980b9;
                border-radius: 5px;
            }
            QCalendarWidget QSpinBox {
                background-color: white;
                color: #2c3e50;
                font-weight: bold;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 3px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: white;
                color: #2c3e50;
                selection-background-color: #3498db;
                selection-color: white;
                alternate-background-color: #f8f9fa;
            }
            QDialogButtonBox QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 20px;
                min-width: 80px;
                margin: 4px;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.takvim = QCalendarWidget()
        self.takvim.setGridVisible(True)
        self.takvim.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.takvim.setLocale(QLocale(QLocale.Turkish))

        if baslangic_tarihi:
            self.takvim.setSelectedDate(baslangic_tarihi)
        else:
            self.takvim.setSelectedDate(QDate.currentDate())

        layout.addWidget(self.takvim)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def secilen_tarih(self):
        return self.takvim.selectedDate()


# ─────────────────────────────────────────────
# TARİH ALANI (QLineEdit + Seç Butonu)
# ─────────────────────────────────────────────

class TarihAlani(QFrame):
    """
    Tek satırlık tarih giriş alanı: [ 04.07.2021 ] [ 📅 Seç ]
    """
    from PyQt5.QtCore import pyqtSignal
    dateChanged = pyqtSignal(object)  # QDate yayınlar

    def __init__(self, parent=None, placeholder="", zorunlu=False):
        from PyQt5.QtWidgets import QHBoxLayout, QLineEdit, QPushButton
        from PyQt5.QtCore import QDate
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self._zorunlu = zorunlu

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.line = QLineEdit()
        self.line.setPlaceholderText(placeholder or "gg.aa.yyyy")
        self.line.setReadOnly(True)
        self.line.setFixedWidth(110)
        self.line.setAlignment(Qt.AlignCenter)
        self.line.setStyleSheet("""
            QLineEdit {
                background-color: #2c3e50;
                border: 1px solid #3498db;
                border-radius: 8px;
                color: #ffffff;
                font-size: 13px;
                padding: 8px 6px;
                selection-background-color: #e74c3c;
            }
            QLineEdit:focus {
                border-color: #e74c3c;
                background-color: #1a2a38;
            }
            QLineEdit:disabled {
                background-color: #34495e;
                color: #7f8c8d;
                border-color: #4a6278;
            }
        """)

        self.sec_btn = QPushButton("📅 Seç")
        self.sec_btn.setFixedSize(80, 34)
        self.sec_btn.setCursor(Qt.PointingHandCursor)
        self.sec_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                border: none;
                font-size: 12px;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.sec_btn.clicked.connect(self._sec)

        lay.addWidget(self.line)
        lay.addWidget(self.sec_btn)

        self._qdate = None

    def _sec(self):
        from PyQt5.QtCore import QDate
        dialog = ModernTarihSecici(self, self._qdate or QDate.currentDate())
        if dialog.exec_():
            self.set_date(dialog.secilen_tarih())

    def set_date(self, qdate):
        from PyQt5.QtCore import QDate
        if isinstance(qdate, QDate) and qdate.isValid():
            self._qdate = qdate
            self.line.setText(qdate.toString("dd.MM.yyyy"))
            self.dateChanged.emit(qdate)
        else:
            self._qdate = None
            self.line.clear()

    def setDate(self, qdate):
        """QDateEdit uyumluluğu"""
        self.set_date(qdate)

    def date(self):
        """QDateEdit uyumluluğu - QDate döner"""
        from PyQt5.QtCore import QDate
        return self._qdate or QDate()

    def set_pydate(self, pydate):
        from PyQt5.QtCore import QDate
        import datetime
        if isinstance(pydate, datetime.date):
            self.set_date(QDate(pydate.year, pydate.month, pydate.day))
        else:
            self.set_date(None)

    def get_date(self):
        return self._qdate

    def get_pydate(self):
        import datetime
        if self._qdate and self._qdate.isValid():
            return datetime.date(self._qdate.year(), self._qdate.month(), self._qdate.day())
        return None

    def clear(self):
        self._qdate = None
        self.line.clear()

    def is_empty(self):
        return self._qdate is None

    # QDateEdit uyumluluk metodları
    def setMinimumDate(self, d): pass
    def setMaximumDate(self, d): pass
    def setReadOnly(self, v): self.sec_btn.setEnabled(not v)
    def setEnabled(self, v):
        super().setEnabled(v)
        self.sec_btn.setEnabled(v)
    def setDisplayFormat(self, fmt): pass
    def setCalendarPopup(self, v): pass
    def setSpecialValueText(self, t): self.line.setPlaceholderText(t)


# Geriye dönük uyumluluk için eski fonksiyonlar
TAKVIM_STYLE = ""

def modern_date_edit(parent=None, date=None):
    """Geriye dönük uyumluluk - TarihAlani kullanımına geçin"""
    from PyQt5.QtWidgets import QDateEdit
    from PyQt5.QtCore import QDate
    d = QDateEdit(parent)
    d.setCalendarPopup(True)
    d.setDisplayFormat("dd.MM.yyyy")
    d.setDate(date if date else QDate.currentDate())
    return d


# ─────────────────────────────────────────────
# MODERN TAKVİM STİLİ
# ─────────────────────────────────────────────

TAKVIM_STYLE = """
    QDateEdit {
        background-color: #34495e;
        border: 1px solid #4a6278;
        border-radius: 8px;
        color: white;
        font-size: 13px;
        padding: 6px 10px;
        min-height: 20px;
    }
    QDateEdit:focus {
        border-color: #3498db;
    }
    QDateEdit::drop-down {
        border: none;
        width: 20px;
    }
    QDateEdit::down-arrow {
        image: none;
        border: none;
    }
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
"""


def modern_date_edit(parent=None, date=None):
    """Modern koyu temalı QDateEdit döndürür"""
    from PyQt5.QtWidgets import QDateEdit
    from PyQt5.QtCore import QDate
    d = QDateEdit(parent)
    d.setCalendarPopup(True)
    d.setDisplayFormat("dd.MM.yyyy")
    d.setDate(date if date else QDate.currentDate())
    d.setStyleSheet(TAKVIM_STYLE)
    return d

def tr_lower(text):
    if not text:
        return ""
    return str(text).replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'ğ').replace('Ü', 'ü').replace('Ş', 'ş').replace('Ö', 'ö').replace('Ç', 'ç').lower()


# ── Frameless dialog helpers ─────────────────────────────────────────────
def make_frameless(dialog, header_height=56):
    """Add FramelessWindowHint + drag support. Call at end of __init__."""
    if not (dialog.windowFlags() & Qt.FramelessWindowHint):
        has_translucent = dialog.testAttribute(Qt.WA_TranslucentBackground)
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        if has_translucent:
            dialog.setAttribute(Qt.WA_TranslucentBackground, True)
    dialog._drag_pos = None
    orig_press = dialog.mousePressEvent
    orig_move = dialog.mouseMoveEvent
    orig_release = dialog.mouseReleaseEvent
    def _press(e):
        if e.button() == Qt.LeftButton and e.y() <= header_height:
            dialog._drag_pos = e.globalPos() - dialog.frameGeometry().topLeft()
            e.accept()
        elif orig_press:
            orig_press(e)
    def _move(e):
        if dialog._drag_pos and e.buttons() == Qt.LeftButton:
            dialog.move(e.globalPos() - dialog._drag_pos)
            e.accept()
        elif orig_move:
            orig_move(e)
    def _release(e):
        if dialog._drag_pos:
            dialog._drag_pos = None
            e.accept()
        elif orig_release:
            orig_release(e)
    dialog.mousePressEvent = _press
    dialog.mouseMoveEvent = _move
    dialog.mouseReleaseEvent = _release

def make_header(ikon, baslik, r1, r2, parent=None):
    """Gradient header + close button. Returns (hdr, close_btn)."""
    hdr = QFrame(parent); hdr.setFixedHeight(56)
    hdr.setStyleSheet(
        f"QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        f"stop:0 {r1},stop:1 {r2});border:none;}}")
    hl = QHBoxLayout(hdr); hl.setContentsMargins(18,0,12,0); hl.setSpacing(12)
    ic = QLabel(ikon); ic.setFixedSize(38,38); ic.setAlignment(Qt.AlignCenter)
    ic.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:19px;font-size:18px;")
    ttl = QLabel(baslik); ttl.setStyleSheet("color:white;font-size:13px;font-weight:bold;background:transparent;")
    close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
    close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:14px;border:none;border-radius:13px;} QPushButton:hover{background:rgba(255,255,255,0.15);color:white;}")
    close_btn.setCursor(Qt.PointingHandCursor)
    hl.addWidget(ic); hl.addWidget(ttl); hl.addStretch(); hl.addWidget(close_btn)
    return hdr, close_btn


class ButtonDelegate(QStyledItemDelegate):
    """Paint clickable buttons in table cells instead of setCellWidget (avoids native Win32 window flash)."""
    buttonClicked = pyqtSignal(int, int)  # row, button_index

    def __init__(self, buttons, parent=None):
        super().__init__(parent)
        self._buttons = buttons
        self._enabled = True

    def set_enabled(self, enabled):
        self._enabled = enabled

    def paint(self, painter, option, index):
        if not self._enabled:
            return
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = option.rect
        x = rect.left() + 2
        y = rect.top() + 2
        h = rect.height() - 4
        for btn in self._buttons:
            w = btn.get("width", 70)
            bg = btn.get("bg", "#3498db")
            btn_rect = QRect(x, y, w, h)
            painter.setBrush(QColor(bg))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(btn_rect, 3, 3)
            painter.setPen(QColor("white"))
            font = QFont("Segoe UI", btn.get("font_size", 9))
            painter.setFont(font)
            painter.drawText(btn_rect, Qt.AlignCenter, btn["text"])
            x += w + 2
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if not self._enabled:
            return False
        if event.type() not in (QEvent.MouseButtonRelease, QEvent.MouseButtonPress):
            return False
        pos = event.pos()
        rect = option.rect
        x = rect.left() + 2
        for i, btn in enumerate(self._buttons):
            w = btn.get("width", 70)
            btn_rect = QRect(x, rect.top() + 2, w, rect.height() - 4)
            if btn_rect.contains(pos):
                if event.type() == QEvent.MouseButtonRelease:
                    self.buttonClicked.emit(index.row(), i)
                return True
            x += w + 2
        return False


import os
def get_config_path(filename):
    """JSON config dosyalarını per-user AppData klasöründe tut (ağ paylaşımında çakışma önleme)."""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    config_dir = os.path.join(appdata, "PYS", "configs")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, filename)