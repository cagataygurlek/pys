# ui/izin_gecmisi_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QFrame, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from ui.utils import make_frameless
from models import Izin
from sqlalchemy import func


def _make_header(ikon, baslik, renk1, renk2):
    hdr = QFrame()
    hdr.setFixedHeight(56)
    hdr.setStyleSheet(
        f"QFrame {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        f"stop:0 {renk1},stop:1 {renk2}); border:none; }}"
    )
    hl = QHBoxLayout(hdr); hl.setContentsMargins(18,0,12,0); hl.setSpacing(12)
    ic = QLabel(ikon); ic.setFixedSize(38,38); ic.setAlignment(Qt.AlignCenter)
    ic.setStyleSheet("background:rgba(255,255,255,0.15); border-radius:19px; font-size:18px;")
    ttl = QLabel(baslik)
    ttl.setStyleSheet("color:white; font-size:13px; font-weight:bold; background:transparent;")
    close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
    close_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.08);color:#ecf0f1;font-size:16px;font-weight:bold;border:none;border-radius:13px;} QPushButton:hover{background:rgba(231,76,60,0.7);color:white;}")
    close_btn.setCursor(Qt.PointingHandCursor)
    hl.addWidget(ic); hl.addWidget(ttl); hl.addStretch(); hl.addWidget(close_btn)
    return hdr, close_btn


class IzinGecmisiDialog(QDialog):
    def __init__(self, session, personel, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.personel = personel
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(900, 500)
        self.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QLabel { color: #ecf0f1; background: transparent; }
            QTableWidget {
                background-color: #34495e;
                border: none;
                gridline-color: rgba(255,255,255,0.1);
                color: #ecf0f1;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1a2a38;
                color: #bdc3c7;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
            QTableWidget::item {
                padding: 6px;
                color: #ecf0f1;
            }
            QTableWidget::item:selected {
                background-color: rgba(52,152,219,0.5);
                color: white;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                border: none;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr, close_btn = _make_header("🏖️", f"İzin Geçmişi — {self.personel.ad_soyad}", "#1a3a5c", "#2980b9")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(hdr)

        # Body
        body = QWidget()
        body.setStyleSheet("background: #2c3e50;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(15, 15, 15, 15)
        body_lay.setSpacing(12)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "İzin Türü", "Başlangıç", "Bitiş", "Gün", "Durum", "Talep Tarihi"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        body_lay.addWidget(self.table)

        layout.addWidget(body)
        make_frameless(self)

    def load_data(self):
        self.table.setRowCount(0)
        izinler = self.session.query(Izin).filter(
            Izin.personel_id == self.personel.id
        ).order_by(Izin.baslangic_tarihi.desc()).all()

        for izin in izinler:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 32)

            # Renklendirme (duruma göre)
            if izin.durum == "Onaylandı":
                renk = "#27ae60"
            elif izin.durum == "Reddedildi":
                renk = "#e74c3c"
            else:
                renk = "#f39c12"

            items = [
                QTableWidgetItem(izin.izin_turu.ad),
                QTableWidgetItem(izin.baslangic_tarihi.strftime("%d.%m.%Y")),
                QTableWidgetItem(izin.bitis_tarihi.strftime("%d.%m.%Y")),
                QTableWidgetItem(str(izin.gun_sayisi)),
                QTableWidgetItem(izin.durum),
                QTableWidgetItem(izin.talep_tarihi.strftime("%d.%m.%Y") if izin.talep_tarihi else "-")
            ]

            for col, item in enumerate(items):
                if col == 3:  # Gün sütunu
                    item.setForeground(QColor("#2ecc71"))
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                if col == 4:  # Durum sütunu
                    item.setForeground(QColor(renk))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)