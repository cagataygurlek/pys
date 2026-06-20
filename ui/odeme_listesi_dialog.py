# ui/odeme_listesi_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QFileDialog, QFrame, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from ui.utils import make_frameless
import pandas as pd
from models import HacizOdeme, Haciz, Personel
from ui.utils import ModernMesaj
import locale
import calendar


# ==================== MODERN HEADER ====================
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
    close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:14px;border:none;border-radius:13px;} QPushButton:hover{background:rgba(255,255,255,0.15);color:white;}")
    close_btn.setCursor(Qt.PointingHandCursor)
    hl.addWidget(ic); hl.addWidget(ttl); hl.addStretch(); hl.addWidget(close_btn)
    return hdr, close_btn


class OdemeListesiDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.resize(950, 550)
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
                background-color: #34495e;
            }
            QTableWidget::item:alternate {
                background-color: #34495e;
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

        # Modern header
        hdr, close_btn = _make_header("📋", "Tüm Haciz Ödemeleri", "#1a3a5c", "#2980b9")
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
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Tarih", "Personel", "Dosya No", "Alacaklı Kurum",
            "IBAN", "Tutar", "Açıklama"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        body_lay.addWidget(self.table)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.export_btn = QPushButton("📥 Excel'e Aktar")
        self.export_btn.setFixedSize(150, 38)
        self.export_btn.clicked.connect(self.excel_export)

        btn_layout.addStretch()
        btn_layout.addWidget(self.export_btn)
        body_lay.addLayout(btn_layout)

        layout.addWidget(body)
        make_frameless(self)

    def load_data(self):
        self.table.setRowCount(0)
        odemeler = self.session.query(HacizOdeme).join(Haciz).join(Personel).order_by(HacizOdeme.tarih.desc()).all()

        for o in odemeler:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 32)

            h = o.haciz
            p = h.personel

            # Açıklama oluştur
            ay_adi = self._get_ay_adi(o.tarih.month)
            aciklama = f"{h.dosya_no} {p.ad_soyad} {p.tc_no or ''} {ay_adi} {o.tarih.year} maaş kesintisi"

            items = [
                QTableWidgetItem(o.tarih.strftime("%d.%m.%Y")),
                QTableWidgetItem(f"{p.ad_soyad} ({p.sicil_no})"),
                QTableWidgetItem(h.dosya_no),
                QTableWidgetItem(h.alacakli_kurum or "-"),
                QTableWidgetItem(h.iban or "-"),
                QTableWidgetItem(f"{o.tutar:,.2f} ₺".replace(",", ".")),
                QTableWidgetItem(aciklama)
            ]

            for col, item in enumerate(items):
                if col == 5:  # Tutar sütunu
                    item.setForeground(QColor("#2ecc71"))
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

    def _get_ay_adi(self, ay_no):
        aylar = [
            "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]
        return aylar[ay_no - 1] if 1 <= ay_no <= 12 else ""

    def excel_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel Dosyası Kaydet",
            "Odeme_Listesi.xlsx",
            "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            data = []
            for r in range(self.table.rowCount()):
                row_data = []
                for c in range(self.table.columnCount()):
                    item = self.table.item(r, c)
                    row_data.append(item.text() if item else "")
                data.append(row_data)

            df = pd.DataFrame(data, columns=[
                "Tarih", "Personel", "Dosya No", "Alacaklı Kurum",
                "IBAN", "Tutar", "Açıklama"
            ])
            df.to_excel(path, index=False)
            ModernMesaj.basari(self, "Ödeme listesi Excel'e aktarıldı.")
        except Exception as e:
            ModernMesaj.hata(self, str(e))