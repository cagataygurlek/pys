# ui/haciz_detay_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QMessageBox, QFormLayout, QDateEdit, QDoubleSpinBox, QLineEdit,
    QTextEdit, QGroupBox, QFileDialog, QFrame, QWidget, QGridLayout
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont
from database import get_session
from models import Haciz, HacizOdeme
from ui.utils import ModernMesaj, TarihAlani, ModernTarihSecici, make_frameless
import datetime
import os

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

class HacizDetayDialog(QDialog):
    def __init__(self, session, haciz_id, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.haciz_id = haciz_id
        self.haciz = self.session.get(Haciz, haciz_id)
        self.resize(820, 620)
        self.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QLabel { color: #ecf0f1; background: transparent; }
            QGroupBox { font-weight: bold; border: 1px solid rgba(255,255,255,0.12); border-radius: 10px;
                background-color: #34495e; margin-top: 10px; padding-top: 14px; color: #ecf0f1; }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; top: -6px; padding: 0 6px;
                color: #bdc3c7; background: #34495e; }
            QTableWidget { background-color: #34495e; border: none; color: white; gridline-color: rgba(255,255,255,0.1); }
            QHeaderView::section { background-color: #1a2a38; color: #bdc3c7; font-weight: bold; padding: 8px; border: none; }
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background-color: rgba(52,152,219,0.4); }
        """)
        self.init_ui()
        self.load_odemeler()
        make_frameless(self)

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        hdr = QFrame(); hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame { background-color: #7b241c; }")
        hdr_lay = QHBoxLayout(hdr); hdr_lay.setContentsMargins(18, 0, 12, 0); hdr_lay.setSpacing(12)
        ic = QLabel("⚖️"); ic.setFixedSize(38, 38); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background-color: #e74c3c; border-radius: 19px; font-size: 18px;")
        tl = QLabel(f"Haciz Detay — {self.haciz.dosya_no}")
        tl.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:14px;border:none;border-radius:13px;} QPushButton:hover{background:rgba(255,255,255,0.15);color:white;}")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        hdr_lay.addWidget(ic); hdr_lay.addWidget(tl); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body); body_lay.setContentsMargins(16, 12, 16, 10); body_lay.setSpacing(10)

        # Bilgi kartları
        info_group = QGroupBox("Dosya Bilgileri")
        ig = QGridLayout(info_group); ig.setSpacing(8); ig.setContentsMargins(14, 20, 14, 14)

        personel = self.haciz.personel

        def info_pair(lbl, val, row, col_start=0, bold=False):
            l = QLabel(lbl); l.setStyleSheet("color: #7f8c8d; font-size: 11px;")
            v = QLabel(val); v.setStyleSheet(f"color: {'#2ecc71' if bold else '#ecf0f1'}; font-size: 13px; {'font-weight: bold;' if bold else ''}")
            ig.addWidget(l, row, col_start); ig.addWidget(v, row, col_start+1)

        info_pair("Personel:", f"{personel.ad_soyad} ({personel.sicil_no})", 0)
        info_pair("Dosya No:", self.haciz.dosya_no, 0, 2)
        info_pair("Alacaklı:", self.haciz.alacakli_kurum or "-", 1)
        info_pair("IBAN:", self.haciz.iban or "-", 1, 2)
        info_pair("Borç:", f"{self.haciz.borc_miktari:,.2f} ₺".replace(",", "."), 2)
        self.kalan_label = QLabel(f"{self.haciz.kalan_borc:,.2f} ₺".replace(",", "."))
        self.kalan_label.setStyleSheet("color: #e74c3c; font-size: 13px; font-weight: bold;")
        kalan_lbl = QLabel("Kalan:"); kalan_lbl.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        ig.addWidget(kalan_lbl, 2, 2); ig.addWidget(self.kalan_label, 2, 3)
        info_pair("Durum:", self.haciz.durum, 3)
        info_pair("Başlangıç:", self.haciz.baslangic_tarihi.strftime("%d.%m.%Y"), 3, 2)

        body_lay.addWidget(info_group)

        # Ödemeler tablosu
        odeme_lbl = QLabel("Yapılan Ödemeler")
        odeme_lbl.setStyleSheet("color: #bdc3c7; font-size: 13px; font-weight: bold;")
        body_lay.addWidget(odeme_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Tarih", "Tutar", "Açıklama", "İşlem"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 80)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        body_lay.addWidget(self.table)
        lay.addWidget(body)

        # Alt butonlar
        btn_frame = QFrame(); btn_frame.setFixedHeight(60)
        btn_frame.setStyleSheet("QFrame { background-color: #243342; border-top: 1px solid #1a2a38; }")
        btn_lay = QHBoxLayout(btn_frame); btn_lay.setContentsMargins(16, 10, 16, 10); btn_lay.setSpacing(8); btn_lay.addStretch()

        def mk_btn(text, color, hover):
            b = QPushButton(text); b.setFixedHeight(38)
            b.setStyleSheet(f"QPushButton {{ background:{color}; color:white; font-weight:bold; border-radius:8px; border:none; padding:0 18px; }} QPushButton:hover {{ background:{hover}; }}")
            return b

        self.yeni_odeme_btn = mk_btn("➕ Yeni Ödeme", "#27ae60", "#2ecc71")
        self.yeni_odeme_btn.clicked.connect(self.yeni_odeme)
        self.pdf_btn = mk_btn("📄 PDF Aktar", "#e67e22", "#d35400")
        self.pdf_btn.clicked.connect(self.pdf_aktar)
        self.kapat_btn = mk_btn("Kapat", "#636e72", "#4a4f52")
        self.kapat_btn.clicked.connect(self.accept)

        btn_lay.addWidget(self.yeni_odeme_btn); btn_lay.addWidget(self.pdf_btn); btn_lay.addWidget(self.kapat_btn)
        lay.addWidget(btn_frame)

    def load_odemeler(self):
        """Bu hacze ait ödemeleri tabloya yükle ve kalan borcu kontrol et"""
        self.table.setRowCount(0)
        odemeler = self.session.query(HacizOdeme).filter(
            HacizOdeme.haciz_id == self.haciz_id
        ).order_by(HacizOdeme.tarih.desc()).all()

        # Toplam ödemeyi hesapla
        toplam_odeme = sum(o.tutar for o in odemeler)
        hesaplanan_kalan = self.haciz.borc_miktari - toplam_odeme
        if abs(hesaplanan_kalan - self.haciz.kalan_borc) > 0.01:
            self.haciz.kalan_borc = hesaplanan_kalan
            if self.haciz.kalan_borc <= 0:
                self.haciz.kalan_borc = 0
                self.haciz.durum = "Tamamlandı"
            self.session.commit()
            self.kalan_label.setText(f"{self.haciz.kalan_borc:,.2f} ₺".replace(",", "."))
            if hasattr(self, 'durum_label') and self.durum_label:
                self.durum_label.setText(self.haciz.durum)

        for o in odemeler:
            row = self.table.rowCount()
            self.table.insertRow(row)

            items = [
                QTableWidgetItem(o.tarih.strftime("%d.%m.%Y")),
                QTableWidgetItem(f"{o.tutar:,.2f} ₺".replace(",", ".")),
                QTableWidgetItem(o.aciklama or "-"),
                QTableWidgetItem("Sil")
            ]

            for col, item in enumerate(items):
                if col == 1:
                    item.setForeground(QColor("#27ae60"))
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

            sil_btn = QPushButton("🗑️")
            sil_btn.setFixedSize(30, 25)
            sil_btn.setStyleSheet("background: #e74c3c; color: white; border-radius: 4px;")
            sil_btn.clicked.connect(lambda _, x=o.id: self.odeme_sil(x))
            self.table.setCellWidget(row, 3, sil_btn)

    def yeni_odeme(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Yeni Ödeme")
        dialog.setFixedWidth(420)
        dialog.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QLabel { color: #bdc3c7; background: transparent; font-size: 11px; }
            QDoubleSpinBox, QTextEdit {
                background-color: #34495e; border: 1px solid #4a6278; border-radius: 8px;
                color: white; font-size: 13px; padding: 8px 12px;
            }
            QDoubleSpinBox:focus, QTextEdit:focus { border-color: #27ae60; }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0px; }
        """)
        lay = QVBoxLayout(dialog); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        hdr = QFrame(); hdr.setFixedHeight(60)
        hdr.setStyleSheet("QFrame { background-color: #1a5c38; }")
        hdr_lay = QHBoxLayout(hdr); hdr_lay.setContentsMargins(16,0,16,0)
        tl = QLabel("Yeni Ödeme Ekle"); tl.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        hdr_lay.addWidget(tl)
        lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body); body_lay.setContentsMargins(20,14,20,10); body_lay.setSpacing(10)

        def field(lbl, widget):
            l = QLabel(lbl); vb = QVBoxLayout(); vb.setSpacing(4)
            vb.addWidget(l); vb.addWidget(widget); return vb

        tarih_edit = TarihAlani(); tarih_edit.set_date(QDate.currentDate())
        body_lay.addLayout(field("TARİH", tarih_edit))

        tutar_edit = QLineEdit()
        tutar_edit.setPlaceholderText("Örn: 2.050,90")
        tutar_edit.setStyleSheet("""
            QLineEdit {
                background-color: #34495e; border: 1px solid #4a6278;
                border-radius: 8px; color: white; padding: 8px 12px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #27ae60; background-color: #1a2a38; }
        """)
        body_lay.addLayout(field("TUTAR", tutar_edit))

        aciklama_edit = QTextEdit(); aciklama_edit.setFixedHeight(60)
        aciklama_edit.setPlaceholderText("Ödeme açıklaması...")
        body_lay.addLayout(field("AÇIKLAMA", aciklama_edit))
        lay.addWidget(body)

        btn_frame = QFrame(); btn_frame.setFixedHeight(56)
        btn_frame.setStyleSheet("QFrame { background-color: #243342; border-top: 1px solid #1a2a38; }")
        btn_lay = QHBoxLayout(btn_frame); btn_lay.setContentsMargins(16,8,16,8); btn_lay.setSpacing(8); btn_lay.addStretch()
        kaydet = QPushButton("Kaydet"); kaydet.setFixedHeight(38)
        kaydet.setStyleSheet("QPushButton { background:#27ae60; color:white; font-weight:bold; border-radius:8px; border:none; padding:0 20px; } QPushButton:hover { background:#2ecc71; }")
        kaydet.clicked.connect(dialog.accept)
        iptal = QPushButton("İptal"); iptal.setFixedHeight(38)
        iptal.setStyleSheet("QPushButton { background:transparent; color:#7f8c8d; border:1px solid #4a6278; border-radius:8px; padding:0 14px; } QPushButton:hover { background:#34495e; color:white; }")
        iptal.clicked.connect(dialog.reject)
        btn_lay.addWidget(kaydet); btn_lay.addWidget(iptal)
        lay.addWidget(btn_frame)

        if dialog.exec_() == QDialog.Accepted:
            tarih = tarih_edit.get_pydate()
            # Türk para formatını parse et: "2.050,90" → 2050.90
            tutar_str = tutar_edit.text().replace("₺","").replace(" ","").strip()
            try:
                tutar = float(tutar_str.replace(".", "").replace(",", "."))
            except ValueError:
                ModernMesaj.uyari(self, "Geçerli bir tutar girin. Örn: 2.050,90")
                return
            aciklama = aciklama_edit.toPlainText()

            if tutar <= 0:
                ModernMesaj.uyari(self, "Tutar 0'dan büyük olmalı.")
                return

            yeni_odeme = HacizOdeme(
                haciz_id=self.haciz_id,
                tarih=tarih,
                tutar=tutar,
                aciklama=aciklama
            )
            self.session.add(yeni_odeme)

            self.haciz.kalan_borc -= tutar
            if self.haciz.kalan_borc < 0:
                self.haciz.kalan_borc = 0
            if self.haciz.kalan_borc == 0 and self.haciz.durum == "Aktif":
                self.haciz.durum = "Tamamlandı"

            try:
                self.session.commit()
                self.load_odemeler()
                self.update_info_labels()
                ModernMesaj.basari(self, "Ödeme kaydedildi.")
            except Exception as e:
                self.session.rollback()
                ModernMesaj.hata(self, str(e))

    def odeme_sil(self, odeme_id):
        cevap = ModernMesaj.soru(self, "Bu ödeme kaydı silinsin mi?")
        if cevap == True:
            odeme = self.session.get(HacizOdeme, odeme_id)
            if odeme:
                tutar = odeme.tutar
                self.session.delete(odeme)
                self.haciz.kalan_borc += tutar
                if self.haciz.durum == "Tamamlandı" and self.haciz.kalan_borc > 0:
                    self.haciz.durum = "Aktif"
                try:
                    self.session.commit()
                    self.load_odemeler()
                    self.update_info_labels()
                except Exception as e:
                    self.session.rollback()
                    ModernMesaj.hata(self, str(e))

    def update_info_labels(self):
        self.kalan_label.setText(f"{self.haciz.kalan_borc:,.2f} ₺".replace(",", "."))

    def pdf_aktar(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "PDF Kaydet",
            f"Haciz_{self.haciz.dosya_no}_Detay.pdf",
            "PDF (*.pdf)"
        )
        if not path:
            return

        try:
            doc = SimpleDocTemplate(path)
            elements = []

            styles = getSampleStyleSheet()
            style_normal = ParagraphStyle(
                name='Normal',
                fontName=font_name,
                fontSize=10,
                leading=12
            )
            style_bold = ParagraphStyle(
                name='Bold',
                fontName=font_name,
                fontSize=14,
                leading=16,
                alignment=1
            )
            style_title = ParagraphStyle(
                name='Title',
                fontName=font_name,
                fontSize=12,
                leading=14,
                alignment=0
            )

            elements.append(Paragraph(f"<b>HACİZ DETAY RAPORU</b>", style_bold))
            elements.append(Spacer(1, 0.2 * inch))

            elements.append(Paragraph("<b>DOSYA BİLGİLERİ</b>", style_title))
            elements.append(Spacer(1, 0.1 * inch))

            data = [
                ["Personel:", f"{self.haciz.personel.ad_soyad} (TC: {self.haciz.personel.tc_no})"],
                ["Sicil No:", self.haciz.personel.sicil_no],
                ["Dosya No:", self.haciz.dosya_no],
                ["Alacaklı Kurum:", self.haciz.alacakli_kurum or "-"],
                ["IBAN:", self.haciz.iban or "-"],
                ["Borç Miktarı:", f"{self.haciz.borc_miktari:,.2f} ₺".replace(",", ".")],
                ["Kalan Borç:", f"{self.haciz.kalan_borc:,.2f} ₺".replace(",", ".")],
                ["Durum:", self.haciz.durum],
                ["Başlangıç:", self.haciz.baslangic_tarihi.strftime("%d.%m.%Y")],
                ["Bitiş:", self.haciz.bitis_tarihi.strftime("%d.%m.%Y") if self.haciz.bitis_tarihi else "Süresiz"],
                ["Açıklama:", self.haciz.aciklama or "-"]
            ]

            table = Table(data, colWidths=[120, 350])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

            elements.append(Paragraph("<b>YAPILAN ÖDEMELER</b>", style_title))
            elements.append(Spacer(1, 0.1 * inch))

            odemeler = self.session.query(HacizOdeme).filter(
                HacizOdeme.haciz_id == self.haciz_id
            ).order_by(HacizOdeme.tarih.desc()).all()

            odeme_data = [["Tarih", "Tutar", "Açıklama"]]
            for o in odemeler:
                odeme_data.append([
                    o.tarih.strftime("%d.%m.%Y"),
                    f"{o.tutar:,.2f} ₺".replace(",", "."),
                    o.aciklama or ""
                ])

            odeme_table = Table(odeme_data, colWidths=[100, 100, 300])
            odeme_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(odeme_table)

            elements.append(Spacer(1, 0.3 * inch))
            elements.append(Paragraph(f"Rapor Tarihi: {datetime.date.today().strftime('%d.%m.%Y')}", style_normal))

            doc.build(elements)
            ModernMesaj.basari(self, f"PDF oluşturuldu:\n{path}")
        except Exception as e:
            ModernMesaj.hata(self, f"PDF oluşturulamadı:\n{str(e)}")