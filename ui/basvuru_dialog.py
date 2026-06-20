# ui/basvuru_dialog.py - Tam ve düzeltilmiş sürüm

import os
import datetime
import calendar
import traceback

import pandas as pd
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit, QTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QGroupBox, QScrollArea, QWidget, QRadioButton,
    QButtonGroup, QFrame, QSizePolicy, QCheckBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont

from database import get_session
from ui.utils import ModernMesaj, TarihAlani, ModernTarihSecici, make_frameless
from ui.widgets import ToggleSwitch
from models import BasvuruAday, BasvuruTecrube, Personel, Sube, Gorev

# PDF için
try:
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    try:
        arial_path = "C:/Windows/Fonts/arial.ttf"
        if os.path.exists(arial_path):
            pdfmetrics.registerFont(TTFont("Arial", arial_path))
            pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
            PDF_FONT = "Arial"
        else:
            PDF_FONT = "Helvetica"
    except Exception:
        PDF_FONT = "Helvetica"
    PDF_OK = True
except ImportError:
    PDF_OK = False


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


# ─────────────────────────────────────────────
# YARDIMCI: label + widget satırı oluştur
# ─────────────────────────────────────────────
def _lbl(text):
    l = QLabel(text)
    l.setStyleSheet("font-size: 12px; color: white; background: transparent;")
    return l


# ─────────────────────────────────────────────
# BAŞVURU FORMU DİALOGU
# ─────────────────────────────────────────────
class BasvuruFormDialog(QDialog):
    """Yeni başvuru ekle / mevcut başvuruyu düzenle"""

    SEVIYELER = ["", "Çok İyi", "İyi", "Orta", "Az"]

    def __init__(self, session, aday=None, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.aday = aday  # None → yeni kayıt
        self.setMinimumSize(820, 700)
        self.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QGroupBox {
                font-weight: bold; font-size: 12px;
                border: 1px solid rgba(52,152,219,0.4); border-radius: 8px;
                margin-top: 12px; padding-top: 12px;
                background: rgba(52,152,219,0.08);
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 12px;
                padding: 0 6px; color: white; background: #2c3e50;
            }
            QLabel { background: transparent; color: white; }
            QLineEdit, QComboBox, QDateEdit, QTextEdit {
                border: 1px solid #4a6278; border-radius: 6px;
                padding: 5px 8px; font-size: 12px;
                background: #34495e; color: white;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {
                border-color: #3498db; background: #2c4a6e;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView { background: #34495e; color: white; selection-background-color: #3498db; }
            QPushButton {
                border-radius: 6px; font-size: 12px;
                font-weight: bold; padding: 7px 14px;
            }
            QTableWidget {
                background: #34495e; border: 1px solid #4a6278;
                gridline-color: rgba(255,255,255,0.2); color: white;
            }
            QHeaderView::section {
                background: #1a2a38; color: white; font-weight: bold; padding: 6px; border: none;
            }
            QTableWidget::item { color: white; }
            QTableWidget::item:selected { background: #3498db; color: white; }
        """)
        self._build_ui()
        if aday:
            self._fill_form()
        make_frameless(self)

    # ── UI İNŞASI ──────────────────────────────
    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(14, 14, 14, 14)
        main_lay.setSpacing(10)

        # Kaydırılabilir alan
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setSpacing(10)
        inner_lay.setContentsMargins(2, 2, 2, 2)

        # ── Başvuru tarihi + pozisyon ──
        top_grp = QGroupBox("Başvuru Bilgileri")
        tg = QHBoxLayout(top_grp)
        tg.addWidget(_lbl("Başvuru Tarihi:"))
        self.basvuru_tarihi = TarihAlani()
        self.basvuru_tarihi.set_date(QDate.currentDate())
        self.basvuru_tarihi.setMinimumWidth(220)
        tg.addWidget(self.basvuru_tarihi)
        tg.addSpacing(20)
        tg.addWidget(_lbl("Başvurulan Pozisyon:"))
        self.pozisyon = QLineEdit()
        self.pozisyon.setPlaceholderText("Örn: Kasiyer, Depo Görevlisi...")
        tg.addWidget(self.pozisyon, 1)
        inner_lay.addWidget(top_grp)

        # ── A. Kişisel Bilgiler ──
        a_grp = QGroupBox("A. Kişisel Bilgiler")
        ag = QGridLayout(a_grp)
        ag.setSpacing(8)

        ag.addWidget(_lbl("Adı:"), 0, 0)
        self.ad = QLineEdit(); ag.addWidget(self.ad, 0, 1)
        ag.addWidget(_lbl("Soyadı:"), 0, 2)
        self.soyad = QLineEdit(); ag.addWidget(self.soyad, 0, 3)

        ag.addWidget(_lbl("TC Kimlik No:"), 1, 0)
        self.tc_no = QLineEdit(); self.tc_no.setMaxLength(11); ag.addWidget(self.tc_no, 1, 1)
        ag.addWidget(_lbl("Doğum Yeri:"), 1, 2)
        self.dogum_yeri = QLineEdit(); ag.addWidget(self.dogum_yeri, 1, 3)

        ag.addWidget(_lbl("Doğum Tarihi:"), 2, 0)
        self.dogum_tarihi = TarihAlani()
        self.dogum_tarihi.set_date(QDate(1990, 1, 1))
        ag.addWidget(self.dogum_tarihi, 2, 1)

        ag.addWidget(_lbl("Cinsiyet:"), 2, 2)
        # Modern checkbox'lı cinsiyet seçimi
        cinsiyet_widget = QWidget()
        cinsiyet_layout = QHBoxLayout(cinsiyet_widget)
        cinsiyet_layout.setContentsMargins(0, 0, 0, 0)
        cinsiyet_layout.setSpacing(15)
        self.cinsiyet_erkek = ModernCheckBox("Erkek")
        self.cinsiyet_kadin = ModernCheckBox("Kadın")
        # Birbirini iptal etme
        self.cinsiyet_erkek.toggled.connect(lambda checked: self.cinsiyet_kadin.setChecked(False) if checked else None)
        self.cinsiyet_kadin.toggled.connect(lambda checked: self.cinsiyet_erkek.setChecked(False) if checked else None)
        cinsiyet_layout.addWidget(self.cinsiyet_erkek)
        cinsiyet_layout.addWidget(self.cinsiyet_kadin)
        cinsiyet_layout.addStretch()
        ag.addWidget(cinsiyet_widget, 2, 3)

        ag.addWidget(_lbl("Adres:"), 3, 0)
        self.adres = QLineEdit(); ag.addWidget(self.adres, 3, 1, 1, 3)

        ag.addWidget(_lbl("Telefon (Ev):"), 4, 0)
        self.tel_ev = QLineEdit(); ag.addWidget(self.tel_ev, 4, 1)
        ag.addWidget(_lbl("Cep 1:"), 4, 2)
        self.tel_cep1 = QLineEdit(); ag.addWidget(self.tel_cep1, 4, 3)

        ag.addWidget(_lbl("Cep 2:"), 5, 0)
        self.tel_cep2 = QLineEdit(); ag.addWidget(self.tel_cep2, 5, 1)
        ag.addWidget(_lbl("E-posta:"), 5, 2)
        self.eposta = QLineEdit(); ag.addWidget(self.eposta, 5, 3)

        ag.addWidget(_lbl("Askerlik Durumu:"), 6, 0)
        self.askerlik = QComboBox()
        self.askerlik.addItems(["", "Tamamlandı", "Tecilli", "Muaf"])
        ag.addWidget(self.askerlik, 6, 1)
        ag.addWidget(_lbl("Askerlik Tarih/Not:"), 6, 2)
        self.askerlik_tarih = QLineEdit(); ag.addWidget(self.askerlik_tarih, 6, 3)

        ag.addWidget(_lbl("Sürücü Belgesi:"), 7, 0)
        self.surucu = QLineEdit(); self.surucu.setPlaceholderText("B, C, D..."); ag.addWidget(self.surucu, 7, 1)
        ag.addWidget(_lbl("Medeni Durum:"), 7, 2)
        # Modern checkbox'lı medeni durum seçimi
        medeni_widget = QWidget()
        medeni_layout = QHBoxLayout(medeni_widget)
        medeni_layout.setContentsMargins(0, 0, 0, 0)
        medeni_layout.setSpacing(15)
        self.medeni_bekar = ModernCheckBox("Bekar")
        self.medeni_evli = ModernCheckBox("Evli")
        self.medeni_bekar.toggled.connect(lambda checked: self.medeni_evli.setChecked(False) if checked else None)
        self.medeni_evli.toggled.connect(lambda checked: self.medeni_bekar.setChecked(False) if checked else None)
        medeni_layout.addWidget(self.medeni_bekar)
        medeni_layout.addWidget(self.medeni_evli)
        medeni_layout.addStretch()
        ag.addWidget(medeni_widget, 7, 3)

        ag.addWidget(_lbl("Eş Mesleği:"), 8, 0)
        self.es_meslegi = QLineEdit(); ag.addWidget(self.es_meslegi, 8, 1)
        ag.addWidget(_lbl("Çocuk Sayısı:"), 8, 2)
        self.cocuk = QLineEdit(); self.cocuk.setPlaceholderText("0"); ag.addWidget(self.cocuk, 8, 3)

        ag.addWidget(_lbl("Sigara Kullanımı:"), 9, 0)
        # Modern checkbox'lı sigara seçimi
        sigara_widget = QWidget()
        sigara_layout = QHBoxLayout(sigara_widget)
        sigara_layout.setContentsMargins(0, 0, 0, 0)
        sigara_layout.setSpacing(15)
        self.sigara_evet = ModernCheckBox("Evet")
        self.sigara_hayir = ModernCheckBox("Hayır")
        self.sigara_evet.toggled.connect(lambda checked: self.sigara_hayir.setChecked(False) if checked else None)
        self.sigara_hayir.toggled.connect(lambda checked: self.sigara_evet.setChecked(False) if checked else None)
        sigara_layout.addWidget(self.sigara_evet)
        sigara_layout.addWidget(self.sigara_hayir)
        sigara_layout.addStretch()
        ag.addWidget(sigara_widget, 9, 1)

        inner_lay.addWidget(a_grp)

        # ── B. Bilgisayar ──
        b_grp = QGroupBox("B. Bilgisayar Bilgisi")
        bg = QGridLayout(b_grp)
        bg.setSpacing(8)
        for col, txt in enumerate(["Program", "Seviye"]):
            lbl = QLabel(txt)
            lbl.setStyleSheet("font-weight: bold; color: white;")
            bg.addWidget(lbl, 0, col * 2)

        for row, prog in enumerate(["Excel", "Word", "PowerPoint"], 1):
            bg.addWidget(_lbl(prog + ":"), row, 0)
            cb = QComboBox()
            cb.addItems(self.SEVIYELER)
            bg.addWidget(cb, row, 1)
            setattr(self, f"bilg_{prog.lower()}", cb)

        inner_lay.addWidget(b_grp)

        # ── C. İş Tecrübesi ──
        c_grp = QGroupBox("C. İş Tecrübesi (Sondan Başa Doğru)")
        cl = QVBoxLayout(c_grp)

        self.tecrube_table = QTableWidget(0, 6)
        self.tecrube_table.setHorizontalHeaderLabels(
            ["Firma/Kurum", "Görev", "Giriş Tarihi", "Çıkış Tarihi", "Ayrılma Sebebi", "Alınan Ücret"])
        self.tecrube_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tecrube_table.setMinimumHeight(130)
        self.tecrube_table.setStyleSheet("""
            QTableWidget { border: 1px solid #4a6278; border-radius: 6px; background: #34495e; color: white; }
            QHeaderView::section { background: #1a2a38; color: white; padding: 5px; border: none; font-size: 11px; }
            QTableWidget::item { padding: 4px; font-size: 11px; color: white; }
        """)
        cl.addWidget(self.tecrube_table)

        tb_btn_lay = QHBoxLayout()
        ekle_btn = QPushButton("+ Satır Ekle")
        ekle_btn.setStyleSheet("background: #3498db; color: white;")
        ekle_btn.clicked.connect(self._tecrube_satir_ekle)
        sil_btn = QPushButton("- Satır Sil")
        sil_btn.setStyleSheet("background: #e74c3c; color: white;")
        sil_btn.clicked.connect(self._tecrube_satir_sil)
        tb_btn_lay.addWidget(ekle_btn)
        tb_btn_lay.addWidget(sil_btn)
        tb_btn_lay.addStretch()
        cl.addLayout(tb_btn_lay)
        inner_lay.addWidget(c_grp)

        # ── D. Diğer ──
        d_grp = QGroupBox("D. Diğer Bilgiler")
        dg = QGridLayout(d_grp)
        dg.setSpacing(8)

        dg.addWidget(_lbl("Sağlık Sorunu:"), 0, 0)
        # Modern checkbox'lı sağlık sorunu seçimi
        saglik_widget = QWidget()
        saglik_layout = QHBoxLayout(saglik_widget)
        saglik_layout.setContentsMargins(0, 0, 0, 0)
        saglik_layout.setSpacing(15)
        self.saglik_evet = ModernCheckBox("Evet")
        self.saglik_hayir = ModernCheckBox("Hayır")
        self.saglik_evet.toggled.connect(lambda checked: self.saglik_hayir.setChecked(False) if checked else None)
        self.saglik_hayir.toggled.connect(lambda checked: self.saglik_evet.setChecked(False) if checked else None)
        saglik_layout.addWidget(self.saglik_evet)
        saglik_layout.addWidget(self.saglik_hayir)
        saglik_layout.addStretch()
        dg.addWidget(saglik_widget, 0, 1)
        dg.addWidget(_lbl("Açıklama:"), 0, 2)
        self.saglik_aciklama = QLineEdit(); dg.addWidget(self.saglik_aciklama, 0, 3)

        dg.addWidget(_lbl("Mahkumiyet:"), 1, 0)
        # Modern checkbox'lı mahkumiyet seçimi
        mahkumiyet_widget = QWidget()
        mahkumiyet_layout = QHBoxLayout(mahkumiyet_widget)
        mahkumiyet_layout.setContentsMargins(0, 0, 0, 0)
        mahkumiyet_layout.setSpacing(15)
        self.mahkumiyet_evet = ModernCheckBox("Evet")
        self.mahkumiyet_hayir = ModernCheckBox("Hayır")
        self.mahkumiyet_evet.toggled.connect(lambda checked: self.mahkumiyet_hayir.setChecked(False) if checked else None)
        self.mahkumiyet_hayir.toggled.connect(lambda checked: self.mahkumiyet_evet.setChecked(False) if checked else None)
        mahkumiyet_layout.addWidget(self.mahkumiyet_evet)
        mahkumiyet_layout.addWidget(self.mahkumiyet_hayir)
        mahkumiyet_layout.addStretch()
        dg.addWidget(mahkumiyet_widget, 1, 1)
        dg.addWidget(_lbl("Açıklama:"), 1, 2)
        self.mahkumiyet_aciklama = QLineEdit(); dg.addWidget(self.mahkumiyet_aciklama, 1, 3)

        dg.addWidget(_lbl("Acil Kişi Adı:"), 2, 0)
        self.acil_ad = QLineEdit(); dg.addWidget(self.acil_ad, 2, 1)
        dg.addWidget(_lbl("Yakınlık:"), 2, 2)
        self.acil_yakinlik = QLineEdit(); dg.addWidget(self.acil_yakinlik, 2, 3)

        dg.addWidget(_lbl("Acil Telefon:"), 3, 0)
        self.acil_tel = QLineEdit(); dg.addWidget(self.acil_tel, 3, 1)

        inner_lay.addWidget(d_grp)

        # ── E. Ücret ──
        e_grp = QGroupBox("E. Ücret Beklentisi")
        eg = QHBoxLayout(e_grp)
        eg.addWidget(_lbl("Beklenen Ücret (₺):"))
        self.ucret = QLineEdit(); self.ucret.setPlaceholderText("0.00"); self.ucret.setFixedWidth(150)
        eg.addWidget(self.ucret)
        eg.addStretch()
        inner_lay.addWidget(e_grp)

        # ── F. Notlar ──
        f_grp = QGroupBox("F. Eklemek İstedikleriniz / Notlar")
        fl = QVBoxLayout(f_grp)
        self.notlar = QTextEdit(); self.notlar.setFixedHeight(70)
        fl.addWidget(self.notlar)
        inner_lay.addWidget(f_grp)

        inner_lay.addStretch()
        scroll.setWidget(inner)
        main_lay.addWidget(scroll)

        # ── Alt butonlar ──
        btn_lay = QHBoxLayout()
        self.kaydet_btn = QPushButton("💾 Kaydet")
        self.kaydet_btn.setStyleSheet("background: #27ae60; color: white;")
        self.kaydet_btn.clicked.connect(self._kaydet)

        self.pdf_btn = QPushButton("📄 PDF'e Aktar")
        self.pdf_btn.setStyleSheet("background: #e67e22; color: white;")
        self.pdf_btn.clicked.connect(self._pdf_aktar)

        self.excel_btn = QPushButton("📥 Excel'e Aktar")
        self.excel_btn.setStyleSheet("background: #16a085; color: white;")
        self.excel_btn.clicked.connect(self._excel_aktar)

        iptal_btn = QPushButton("İptal")
        iptal_btn.setStyleSheet("background: #95a5a6; color: white;")
        iptal_btn.clicked.connect(self.reject)

        btn_lay.addWidget(self.kaydet_btn)
        btn_lay.addWidget(self.pdf_btn)
        btn_lay.addWidget(self.excel_btn)
        btn_lay.addStretch()
        btn_lay.addWidget(iptal_btn)
        main_lay.addLayout(btn_lay)

    # ── FORM DOLDUR (düzenleme modunda) ────────
    def _fill_form(self):
        a = self.aday
        self.basvuru_tarihi.set_date(
            QDate(a.basvuru_tarihi.year, a.basvuru_tarihi.month, a.basvuru_tarihi.day)
            if a.basvuru_tarihi else QDate.currentDate())
        self.pozisyon.setText(a.pozisyon or "")
        self.ad.setText(a.ad or "")
        self.soyad.setText(a.soyad or "")
        self.tc_no.setText(a.tc_no or "")
        self.dogum_yeri.setText(a.dogum_yeri or "")
        if a.dogum_tarihi:
            self.dogum_tarihi.set_date(QDate(a.dogum_tarihi.year, a.dogum_tarihi.month, a.dogum_tarihi.day))
        
        # Cinsiyet - modern checkbox
        if a.cinsiyet == "Erkek":
            self.cinsiyet_erkek.setChecked(True)
        elif a.cinsiyet == "Kadın":
            self.cinsiyet_kadin.setChecked(True)
        
        self.adres.setText(a.adres or "")
        self.tel_ev.setText(a.telefon_ev or "")
        self.tel_cep1.setText(a.telefon_cep1 or "")
        self.tel_cep2.setText(a.telefon_cep2 or "")
        self.eposta.setText(a.eposta or "")
        self.askerlik.setCurrentText(a.askerlik_durum or "")
        self.askerlik_tarih.setText(a.askerlik_tarih or "")
        self.surucu.setText(a.surucu_belgesi or "")
        
        # Medeni durum - modern checkbox
        if a.medeni_durum == "Evli":
            self.medeni_evli.setChecked(True)
        elif a.medeni_durum == "Bekar":
            self.medeni_bekar.setChecked(True)
        
        self.es_meslegi.setText(a.es_meslegi or "")
        self.cocuk.setText(str(a.cocuk_sayisi) if a.cocuk_sayisi is not None else "")
        
        # Sigara - modern checkbox
        if a.sigara == "Evet":
            self.sigara_evet.setChecked(True)
        elif a.sigara == "Hayır":
            self.sigara_hayir.setChecked(True)
        
        self.bilg_excel.setCurrentText(a.excel_seviye or "")
        self.bilg_word.setCurrentText(a.word_seviye or "")
        self.bilg_powerpoint.setCurrentText(a.powerpoint_seviye or "")
        
        # Sağlık sorunu - modern checkbox
        if a.saglik_sorunu == "Evet":
            self.saglik_evet.setChecked(True)
        elif a.saglik_sorunu == "Hayır":
            self.saglik_hayir.setChecked(True)
        self.saglik_aciklama.setText(a.saglik_aciklama or "")
        
        # Mahkumiyet - modern checkbox
        if a.mahkumiyet == "Evet":
            self.mahkumiyet_evet.setChecked(True)
        elif a.mahkumiyet == "Hayır":
            self.mahkumiyet_hayir.setChecked(True)
        self.mahkumiyet_aciklama.setText(a.mahkumiyet_aciklama or "")
        
        self.acil_ad.setText(a.acil_kisi_adsoyad or "")
        self.acil_yakinlik.setText(a.acil_kisi_yakinlik or "")
        self.acil_tel.setText(a.acil_kisi_telefon or "")
        self.ucret.setText(str(a.ucret_beklenti) if a.ucret_beklenti else "")
        self.notlar.setPlainText(a.notlar or "")
        for t in a.tecrubeleri:
            self._tecrube_satir_ekle(
                t.firma_adi, t.gorev, t.giris_tarihi,
                t.cikis_tarihi, t.ayrilma_sebebi, t.alinan_ucret)

    # ── TECRÜBİ SATIRLAR ───────────────────────
    def _tecrube_satir_ekle(self, firma="", gorev="", giris="", cikis="", sebep="", ucret=""):
        row = self.tecrube_table.rowCount()
        self.tecrube_table.insertRow(row)
        for col, val in enumerate([firma, gorev, giris, cikis, sebep, ucret]):
            item = QTableWidgetItem(str(val) if val else "")
            item.setForeground(QColor("white"))
            self.tecrube_table.setItem(row, col, item)

    def _tecrube_satir_sil(self):
        row = self.tecrube_table.currentRow()
        if row >= 0:
            self.tecrube_table.removeRow(row)

    # ── KAYDET ─────────────────────────────────
    def _kaydet(self):
        if not self.ad.text().strip() or not self.soyad.text().strip():
            ModernMesaj.uyari(self, "Uyarı", "Ad ve Soyad zorunludur.")
            return
        
        # Cinsiyet değerini modern checkbox'lardan al
        cinsiyet = ""
        if self.cinsiyet_erkek.isChecked():
            cinsiyet = "Erkek"
        elif self.cinsiyet_kadin.isChecked():
            cinsiyet = "Kadın"
        
        # Medeni durum değerini modern checkbox'lardan al
        medeni_durum = ""
        if self.medeni_evli.isChecked():
            medeni_durum = "Evli"
        elif self.medeni_bekar.isChecked():
            medeni_durum = "Bekar"
        
        # Sigara değerini modern checkbox'lardan al
        sigara = ""
        if self.sigara_evet.isChecked():
            sigara = "Evet"
        elif self.sigara_hayir.isChecked():
            sigara = "Hayır"
        
        # Sağlık sorunu değerini modern checkbox'lardan al
        saglik_sorunu = ""
        if self.saglik_evet.isChecked():
            saglik_sorunu = "Evet"
        elif self.saglik_hayir.isChecked():
            saglik_sorunu = "Hayır"
        
        # Mahkumiyet değerini modern checkbox'lardan al
        mahkumiyet = ""
        if self.mahkumiyet_evet.isChecked():
            mahkumiyet = "Evet"
        elif self.mahkumiyet_hayir.isChecked():
            mahkumiyet = "Hayır"
        
        try:
            if self.aday:
                a = self.aday
                for t in list(a.tecrubeleri):
                    self.session.delete(t)
            else:
                a = BasvuruAday()
                self.session.add(a)

            qt_d = self.basvuru_tarihi.get_date()
            a.basvuru_tarihi = datetime.date(qt_d.year(), qt_d.month(), qt_d.day())
            a.pozisyon = self.pozisyon.text().strip()
            a.ad = self.ad.text().strip().upper()
            a.soyad = self.soyad.text().strip().upper()
            a.tc_no = self.tc_no.text().strip() or None
            a.dogum_yeri = self.dogum_yeri.text().strip() or None
            qt_db = self.dogum_tarihi.get_date()
            a.dogum_tarihi = datetime.date(qt_db.year(), qt_db.month(), qt_db.day())
            a.cinsiyet = cinsiyet or None
            a.adres = self.adres.text().strip() or None
            a.telefon_ev = self.tel_ev.text().strip() or None
            a.telefon_cep1 = self.tel_cep1.text().strip() or None
            a.telefon_cep2 = self.tel_cep2.text().strip() or None
            a.eposta = self.eposta.text().strip() or None
            a.askerlik_durum = self.askerlik.currentText() or None
            a.askerlik_tarih = self.askerlik_tarih.text().strip() or None
            a.surucu_belgesi = self.surucu.text().strip() or None
            a.medeni_durum = medeni_durum or None
            a.es_meslegi = self.es_meslegi.text().strip() or None
            try:
                a.cocuk_sayisi = int(self.cocuk.text().strip())
            except Exception:
                a.cocuk_sayisi = None
            a.sigara = sigara or None
            a.excel_seviye = self.bilg_excel.currentText() or None
            a.word_seviye = self.bilg_word.currentText() or None
            a.powerpoint_seviye = self.bilg_powerpoint.currentText() or None
            a.saglik_sorunu = saglik_sorunu
            a.saglik_aciklama = self.saglik_aciklama.text().strip() or None
            a.mahkumiyet = mahkumiyet
            a.mahkumiyet_aciklama = self.mahkumiyet_aciklama.text().strip() or None
            a.acil_kisi_adsoyad = self.acil_ad.text().strip() or None
            a.acil_kisi_yakinlik = self.acil_yakinlik.text().strip() or None
            a.acil_kisi_telefon = self.acil_tel.text().strip() or None
            try:
                a.ucret_beklenti = float(self.ucret.text().replace(",", ".").replace("₺", "").strip())
            except Exception:
                a.ucret_beklenti = None
            a.notlar = self.notlar.toPlainText().strip() or None

            # Tecrübeler
            for row in range(self.tecrube_table.rowCount()):
                def cell(c):
                    it = self.tecrube_table.item(row, c)
                    return it.text().strip() if it else ""
                if any(cell(c) for c in range(6)):
                    t = BasvuruTecrube(
                        firma_adi=cell(0), gorev=cell(1),
                        giris_tarihi=cell(2), cikis_tarihi=cell(3),
                        ayrilma_sebebi=cell(4), alinan_ucret=cell(5)
                    )
                    a.tecrubeleri.append(t)

            self.session.commit()
            ModernMesaj.basari(self, "Başarılı", "Başvuru kaydedildi.")
            self.accept()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, "Hata", str(e))

    # ── PDF AKTAR ──────────────────────────────
    def _pdf_aktar(self):
        if not PDF_OK:
            ModernMesaj.hata(self, "Uyarı", "PDF için reportlab kütüphanesi gereklidir.\npip install reportlab")
            return
        a = self.aday
        if not a:
            ModernMesaj.hata(self, "Uyarı", "Önce kaydedin, sonra PDF alın.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "PDF Kaydet",
            f"Basvuru_{a.ad}_{a.soyad}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            doc = SimpleDocTemplate(path, rightMargin=1.5*cm, leftMargin=1.5*cm,
                                    topMargin=1.5*cm, bottomMargin=1.5*cm)
            styles = getSampleStyleSheet()
            normal = ParagraphStyle("n", fontName=PDF_FONT, fontSize=9, leading=13)
            bold = ParagraphStyle("b", fontName=PDF_FONT+"-Bold" if PDF_FONT == "Arial" else PDF_FONT, fontSize=9, leading=13)
            title_style = ParagraphStyle("t", fontName=PDF_FONT, fontSize=14, leading=18, alignment=1)
            section_style = ParagraphStyle("s", fontName=PDF_FONT, fontSize=10, leading=14,
                                           backColor=colors.HexColor("#2c3e50"), textColor=colors.white,
                                           spaceBefore=8, spaceAfter=4, leftIndent=4)

            story = []
            story.append(Paragraph("BEŞLER FRESH MARKET", title_style))
            story.append(Paragraph("İŞ BAŞVURU FORMU", title_style))
            story.append(Spacer(1, 0.3*cm))

            def row2(l1, v1, l2="", v2=""):
                return [Paragraph(f"<b>{l1}</b>", normal),
                        Paragraph(str(v1) if v1 else "-", normal),
                        Paragraph(f"<b>{l2}</b>", normal),
                        Paragraph(str(v2) if v2 else "-", normal)]

            def section(txt):
                story.append(Paragraph(txt, section_style))

            def table2col(data):
                t = Table(data, colWidths=[3.5*cm, 6*cm, 3.5*cm, 5*cm])
                t.setStyle(TableStyle([
                    ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
                    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
                    ("TOPPADDING", (0,0), (-1,-1), 4),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ]))
                story.append(t)

            story.append(Paragraph(
                f"<b>Başvuru Tarihi:</b> {a.basvuru_tarihi.strftime('%d.%m.%Y') if a.basvuru_tarihi else '-'}   "
                f"<b>Başvurulan Pozisyon:</b> {a.pozisyon or '-'}", normal))
            story.append(Spacer(1, 0.2*cm))

            section("A. KİŞİSEL BİLGİLER")
            table2col([
                row2("Adı:", a.ad, "Soyadı:", a.soyad),
                row2("TC Kimlik:", a.tc_no, "Doğum Yeri:", a.dogum_yeri),
                row2("Doğum Tarihi:", a.dogum_tarihi.strftime("%d.%m.%Y") if a.dogum_tarihi else "-",
                     "Cinsiyet:", a.cinsiyet),
                row2("Adres:", a.adres, "E-posta:", a.eposta),
                row2("Telefon Ev:", a.telefon_ev, "Cep 1:", a.telefon_cep1),
                row2("Cep 2:", a.telefon_cep2, "Sigara:", a.sigara),
                row2("Askerlik:", a.askerlik_durum, "Sürücü Belgesi:", a.surucu_belgesi),
                row2("Medeni Durum:", a.medeni_durum, "Çocuk Sayısı:", a.cocuk_sayisi),
                row2("Eş Mesleği:", a.es_meslegi, "", ""),
            ])

            section("B. BİLGİSAYAR BİLGİSİ")
            table2col([
                row2("Excel:", a.excel_seviye, "Word:", a.word_seviye),
                row2("PowerPoint:", a.powerpoint_seviye, "", ""),
            ])

            section("C. İŞ TECRÜBESİ")
            if a.tecrubeleri:
                th = [Paragraph(f"<b>{x}</b>", normal) for x in
                      ["Firma/Kurum", "Görev", "Giriş", "Çıkış", "Ayrılma Sebebi", "Ücret"]]
                rows = [th]
                for t in a.tecrubeleri:
                    rows.append([
                        Paragraph(t.firma_adi or "-", normal),
                        Paragraph(t.gorev or "-", normal),
                        Paragraph(t.giris_tarihi or "-", normal),
                        Paragraph(t.cikis_tarihi or "-", normal),
                        Paragraph(t.ayrilma_sebebi or "-", normal),
                        Paragraph(t.alinan_ucret or "-", normal),
                    ])
                tbl = Table(rows, colWidths=[4.5*cm, 3*cm, 2.2*cm, 2.2*cm, 4*cm, 2.5*cm])
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2c3e50")),
                    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                    ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
                    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
                    ("TOPPADDING", (0,0), (-1,-1), 4),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ]))
                story.append(tbl)
            else:
                story.append(Paragraph("Tecrübe kaydı bulunmuyor.", normal))

            section("D. DİĞER BİLGİLER")
            table2col([
                row2("Sağlık Sorunu:", a.saglik_sorunu, "Açıklama:", a.saglik_aciklama),
                row2("Mahkumiyet:", a.mahkumiyet, "Açıklama:", a.mahkumiyet_aciklama),
                row2("Acil Kişi:", a.acil_kisi_adsoyad, "Yakınlık:", a.acil_kisi_yakinlik),
                row2("Acil Telefon:", a.acil_kisi_telefon, "", ""),
            ])

            section("E. ÜCRET BEKLENTİSİ")
            story.append(Paragraph(
                f"{a.ucret_beklenti:,.0f} ₺".replace(",", ".") if a.ucret_beklenti else "-", normal))

            if a.notlar:
                section("F. NOTLAR")
                story.append(Paragraph(a.notlar, normal))

            doc.build(story)
            ModernMesaj.information(self, "Başarılı", "PDF oluşturuldu.")
        except Exception as e:
            ModernMesaj.critical(self, "Hata", traceback.format_exc())

    # ── EXCEL AKTAR ────────────────────────────
    def _excel_aktar(self):
        a = self.aday
        if not a:
            ModernMesaj.warning(self, "Uyarı", "Önce kaydedin, sonra Excel'e aktarın.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Excel Kaydet",
            f"Basvuru_{a.ad}_{a.soyad}.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            data = {
                "Başvuru Tarihi": [a.basvuru_tarihi.strftime("%d.%m.%Y") if a.basvuru_tarihi else ""],
                "Pozisyon": [a.pozisyon or ""],
                "Ad": [a.ad], "Soyad": [a.soyad],
                "TC No": [a.tc_no or ""],
                "Doğum Yeri": [a.dogum_yeri or ""],
                "Doğum Tarihi": [a.dogum_tarihi.strftime("%d.%m.%Y") if a.dogum_tarihi else ""],
                "Cinsiyet": [a.cinsiyet or ""],
                "Adres": [a.adres or ""],
                "Telefon Ev": [a.telefon_ev or ""],
                "Cep 1": [a.telefon_cep1 or ""],
                "Cep 2": [a.telefon_cep2 or ""],
                "E-posta": [a.eposta or ""],
                "Askerlik": [a.askerlik_durum or ""],
                "Sürücü Belgesi": [a.surucu_belgesi or ""],
                "Medeni Durum": [a.medeni_durum or ""],
                "Eş Mesleği": [a.es_meslegi or ""],
                "Çocuk Sayısı": [a.cocuk_sayisi if a.cocuk_sayisi is not None else ""],
                "Sigara": [a.sigara or ""],
                "Excel Seviye": [a.excel_seviye or ""],
                "Word Seviye": [a.word_seviye or ""],
                "PowerPoint Seviye": [a.powerpoint_seviye or ""],
                "Sağlık Sorunu": [a.saglik_sorunu or ""],
                "Sağlık Açıklama": [a.saglik_aciklama or ""],
                "Mahkumiyet": [a.mahkumiyet or ""],
                "Mahkumiyet Açıklama": [a.mahkumiyet_aciklama or ""],
                "Acil Kişi": [a.acil_kisi_adsoyad or ""],
                "Yakınlık": [a.acil_kisi_yakinlik or ""],
                "Acil Telefon": [a.acil_kisi_telefon or ""],
                "Ücret Beklentisi": [a.ucret_beklenti or ""],
                "Notlar": [a.notlar or ""],
                "Durum": [a.durum or ""],
            }
            df_ana = pd.DataFrame(data)
            rows_t = []
            for t in a.tecrubeleri:
                rows_t.append({
                    "Firma": t.firma_adi, "Görev": t.gorev,
                    "Giriş": t.giris_tarihi, "Çıkış": t.cikis_tarihi,
                    "Ayrılma Sebebi": t.ayrilma_sebebi, "Ücret": t.alinan_ucret,
                })
            df_tec = pd.DataFrame(rows_t) if rows_t else pd.DataFrame(
                columns=["Firma", "Görev", "Giriş", "Çıkış", "Ayrılma Sebebi", "Ücret"])
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df_ana.to_excel(writer, sheet_name="Başvuru", index=False)
                df_tec.to_excel(writer, sheet_name="İş Tecrübesi", index=False)
            ModernMesaj.information(self, "Başarılı", "Excel dosyası oluşturuldu.")
        except Exception as e:
            ModernMesaj.critical(self, "Hata", str(e))


# ─────────────────────────────────────────────
# EXCEL İÇERİ AKTARIM DİALOGU
# ─────────────────────────────────────────────
class BasvuruExcelImportDialog(QDialog):
    """Doldurulmuş başvuru formunu Excel'den içe aktar"""

    def __init__(self, session, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.setFixedSize(500, 260)
        self.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QLabel { color: white; background: transparent; }
            QPushButton { background-color: #3498db; color: white; font-weight: bold; border-radius: 6px; }
        """)
        self._build()
        make_frameless(self)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        info = QLabel(
            "Doldurulmuş 'Beşler Fresh Market İş Başvuru Formu' Excel dosyasını seçin.\n"
            "Sistem formdaki verileri otomatik olarak okuyacak."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: white; font-size: 12px;")
        lay.addWidget(info)

        dosya_lay = QHBoxLayout()
        self.dosya_lbl = QLabel("Dosya seçilmedi")
        self.dosya_lbl.setStyleSheet(
            "border: 1px solid #4a6278; border-radius: 6px; padding: 6px; color: white; background: #34495e;")
        dosya_lay.addWidget(self.dosya_lbl, 1)
        sec_btn = QPushButton("Dosya Seç")
        sec_btn.setStyleSheet("background: #3498db; color: white; font-weight: bold; border-radius: 6px; padding: 7px 14px;")
        sec_btn.clicked.connect(self._dosya_sec)
        dosya_lay.addWidget(sec_btn)
        lay.addLayout(dosya_lay)

        self.sonuc_lbl = QLabel("")
        self.sonuc_lbl.setStyleSheet("color: #27ae60; font-size: 11px;")
        lay.addWidget(self.sonuc_lbl)

        btn_lay = QHBoxLayout()
        self.aktar_btn = QPushButton("✅ Aktar")
        self.aktar_btn.setEnabled(False)
        self.aktar_btn.setStyleSheet("background: #27ae60; color: white; font-weight: bold; border-radius: 6px; padding: 8px 20px;")
        self.aktar_btn.clicked.connect(self._aktar)
        kapat = QPushButton("Kapat")
        kapat.setStyleSheet("background: #95a5a6; color: white; border-radius: 6px; padding: 8px 20px;")
        kapat.clicked.connect(self.reject)
        btn_lay.addStretch()
        btn_lay.addWidget(self.aktar_btn)
        btn_lay.addWidget(kapat)
        lay.addLayout(btn_lay)
        self.dosya_yolu = None

    def _dosya_sec(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Excel Dosyası Seç", "", "Excel (*.xlsx *.xls)")
        if path:
            self.dosya_yolu = path
            self.dosya_lbl.setText(os.path.basename(path))
            self.dosya_lbl.setStyleSheet(
                "border: 1px solid #27ae60; border-radius: 6px; padding: 6px; color: white; background: #34495e;")
            self.aktar_btn.setEnabled(True)

    def _aktar(self):
        if not self.dosya_yolu:
            return
        try:
            xl = pd.ExcelFile(self.dosya_yolu)
            df = xl.parse(xl.sheet_names[0], header=None, dtype=str)

            def cell(r, c):
                try:
                    v = df.iloc[r, c]
                    return str(v).strip() if pd.notna(v) and str(v).strip() not in ("nan", "None", "") else ""
                except Exception:
                    return ""

            a = BasvuruAday()

            try:
                bt = cell(2, 2)
                a.basvuru_tarihi = datetime.datetime.strptime(bt, "%d.%m.%Y").date() if bt else datetime.date.today()
            except Exception:
                a.basvuru_tarihi = datetime.date.today()

            a.pozisyon = cell(3, 2)

            a.ad = cell(5, 1).upper()
            a.soyad = cell(6, 1).upper()
            a.dogum_yeri = cell(5, 4)
            try:
                dts = cell(6, 4)
                a.dogum_tarihi = datetime.datetime.strptime(dts, "%d.%m.%Y").date() if dts else None
            except Exception:
                a.dogum_tarihi = None

            # Cinsiyet
            cin_kadin = cell(7, 1)
            cin_erkek = cell(7, 2)
            if cin_erkek and cin_erkek not in ("-", ""):
                a.cinsiyet = "Erkek"
            elif cin_kadin and cin_kadin not in ("-", ""):
                a.cinsiyet = "Kadın"

            a.adres = cell(8, 1)
            a.telefon_ev = cell(9, 2)
            a.telefon_cep1 = cell(9, 4)
            a.telefon_cep2 = cell(9, 6) if df.shape[1] > 6 else ""
            a.eposta = cell(10, 1)

            # Askerlik
            ask_tam = cell(11, 1)
            ask_tec = cell(12, 1)
            ask_muaf = cell(13, 1)
            if ask_tam:
                a.askerlik_durum = "Tamamlandı"
                a.askerlik_tarih = cell(11, 4)
            elif ask_tec:
                a.askerlik_durum = "Tecilli"
                a.askerlik_tarih = cell(12, 4)
            elif ask_muaf:
                a.askerlik_durum = "Muaf"
                a.askerlik_tarih = cell(13, 4)

            a.surucu_belgesi = cell(14, 1)

            # Medeni
            med_evli = cell(15, 1)
            med_bekar = cell(15, 2)
            a.medeni_durum = "Evli" if med_evli else ("Bekar" if med_bekar else "")
            a.es_meslegi = cell(15, 4)
            a.sigara = cell(16, 1)
            try:
                a.cocuk_sayisi = int(cell(16, 4)) if cell(16, 4) else None
            except Exception:
                a.cocuk_sayisi = None

            # Bilgisayar
            seviye_map = {"1": "Çok İyi", "2": "İyi", "3": "Orta", "4": "Az",
                          "çok iyi": "Çok İyi", "iyi": "İyi", "orta": "Orta", "az": "Az"}

            def seviye(r):
                for c in range(1, 5):
                    v = cell(r, c).lower()
                    if v and v != "nan":
                        cols = ["Çok İyi", "İyi", "Orta", "Az"]
                        return cols[c-1]
                return ""

            a.excel_seviye = seviye(19)
            a.word_seviye = seviye(20)
            a.powerpoint_seviye = seviye(21)

            # İş Tecrübesi
            for i in range(23, min(27, df.shape[0])):
                firma = cell(i, 0)
                if firma and firma not in ("-", "Firma/Kurum Adı"):
                    t = BasvuruTecrube(
                        firma_adi=firma,
                        gorev=cell(i, 1),
                        giris_tarihi=cell(i, 2),
                        cikis_tarihi=cell(i, 3),
                        ayrilma_sebebi=cell(i, 4),
                        alinan_ucret=cell(i, 5),
                    )
                    a.tecrubeleri.append(t)

            # D. Diğer
            for i in range(24, min(32, df.shape[0])):
                row_txt = " ".join(str(cell(i, c)) for c in range(3)).lower()
                if "sağlık" in row_txt:
                    a.saglik_sorunu = "Evet" if "evet" in row_txt else "Hayır"
                    a.saglik_aciklama = cell(i, 4)
                if "mahkumiyet" in row_txt:
                    a.mahkumiyet = "Evet" if "evet" in row_txt else "Hayır"
                    a.mahkumiyet_aciklama = cell(i, 4)
                if "ulaşılamadığında" in row_txt or "haber" in row_txt:
                    a.acil_kisi_adsoyad = cell(i+1, 1) if i+1 < df.shape[0] else ""
                    a.acil_kisi_yakinlik = cell(i+1, 3) if i+1 < df.shape[0] else ""
                    a.acil_kisi_telefon = cell(i+1, 4) if i+1 < df.shape[0] else ""

            # E. Ücret
            for i in range(28, min(35, df.shape[0])):
                row_txt = " ".join(str(cell(i, c)) for c in range(3)).lower()
                if "ücret" in row_txt and "beklenti" in row_txt:
                    try:
                        a.ucret_beklenti = float(cell(i, 1).replace(",", ".").replace("₺", "").strip())
                    except Exception:
                        pass

            if not a.ad:
                ModernMesaj.warning(self, "Uyarı", "Ad bilgisi okunamadı. Form yapısı uyumsuz olabilir.")
                return

            self.session.add(a)
            self.session.commit()
            self.sonuc_lbl.setText(f"✅ {a.ad} {a.soyad} başarıyla aktarıldı.")
            self.aktar_btn.setEnabled(False)
        except Exception as e:
            self.session.rollback()
            ModernMesaj.critical(self, "Hata", traceback.format_exc())