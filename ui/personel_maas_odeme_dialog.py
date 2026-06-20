# ui/personel_maas_odeme_dialog.py
"""
Personel detay sayfasından maaş ödemesi yapılırken dönem seçimi için dialog.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QComboBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from ui.utils import make_frameless


class PersonelDonemSecDialog(QDialog):
    """Personel detay sayfasından maaş ödemesi için dönem seçimi."""
    def __init__(self, session, personel, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.personel = personel
        self.secilen_yil = None
        self.secilen_ay = None

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 220)
        QTimer.singleShot(0, self._ortala)
        self._init_ui()
        make_frameless(self)

    def _ortala(self):
        if self.parent():
            pg = self.parent().frameGeometry()
            self.move(pg.x() + (pg.width() - self.width()) // 2,
                      pg.y() + (pg.height() - self.height()) // 2 - 30)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:14px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; }
            QComboBox { background:#1a2a38; color:white; border:1px solid #4a6278;
                        border-radius:6px; padding:5px 10px; font-size:12px; }
            QComboBox::drop-down { border:none; width:20px; }
            QComboBox QAbstractItemView { background:#34495e; color:white;
                                          selection-background-color:#3498db; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        # Başlık
        hdr = QFrame()
        hdr.setFixedHeight(54)
        hdr.setStyleSheet("""
            QFrame { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a5c38,stop:1 #27ae60);
                     border-top-left-radius:14px; border-top-right-radius:14px; border:none; }
        """)
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(16, 0, 12, 0)
        ic = QLabel("💸"); ic.setStyleSheet("font-size:18px;")
        tl = QLabel(f"Maaş Ödemesi — {self.personel.ad_soyad}")
        tl.setStyleSheet("color:white; font-size:12px; font-weight:bold;")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:13px;border:none;} QPushButton:hover{color:white;}")
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(ic); hdr_lay.addWidget(tl, 1); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        # İçerik
        body = QFrame()
        body.setStyleSheet("QFrame{background:transparent;border:none;}")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(20, 16, 20, 16)
        body_lay.setSpacing(12)

        # Bordro seçimi
        import datetime
        from models import Bordro
        self.bordro_cb = QComboBox()
        bordrolar = self.session.query(Bordro).filter(
            Bordro.personel_id == self.personel.id
        ).order_by(Bordro.yil.desc(), Bordro.ay.desc()).all()

        if not bordrolar:
            lbl = QLabel("Bu personel için bordro bulunamadı.")
            lbl.setStyleSheet("color:#e74c3c; font-size:11px;")
            body_lay.addWidget(lbl)
        else:
            aylar = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                     "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
            for b in bordrolar:
                self.bordro_cb.addItem(f"{aylar[b.ay-1]} {b.yil}", (b.yil, b.ay))

        donem_lbl = QLabel("Ödeme Dönemi:")
        donem_lbl.setStyleSheet("color:#bdc3c7; font-size:11px;")
        body_lay.addWidget(donem_lbl)
        body_lay.addWidget(self.bordro_cb)

        outer_lay.addWidget(body)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(54)
        footer.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:14px;border-bottom-right-radius:14px;border:none;border-top:1px solid #1a2a38;}")
        foot_h = QHBoxLayout(footer)
        foot_h.setContentsMargins(16, 10, 16, 10)
        foot_h.setSpacing(8)

        devam_btn = QPushButton("Devam →")
        devam_btn.setFixedHeight(34)
        devam_btn.setCursor(Qt.PointingHandCursor)
        devam_btn.setStyleSheet("QPushButton{background:#27ae60;color:white;font-weight:bold;border-radius:8px;border:none;padding:0 16px;} QPushButton:hover{background:#2ecc71;}")
        devam_btn.clicked.connect(self._devam)
        devam_btn.setEnabled(len(bordrolar) > 0)

        iptal_btn = QPushButton("İptal")
        iptal_btn.setFixedHeight(34)
        iptal_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 14px;} QPushButton:hover{background:#34495e;color:white;}")
        iptal_btn.clicked.connect(self.reject)

        foot_h.addStretch()
        foot_h.addWidget(devam_btn)
        foot_h.addWidget(iptal_btn)
        outer_lay.addWidget(footer)

    def _devam(self):
        data = self.bordro_cb.currentData()
        if data:
            self.secilen_yil, self.secilen_ay = data
            self.accept()
