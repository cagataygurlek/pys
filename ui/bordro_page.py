# ui/bordro_page.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QComboBox, QLabel, QPushButton, QFrame,
    QHeaderView, QMessageBox, QFileDialog, QDialog,
    QFormLayout, QDoubleSpinBox, QLineEdit, QApplication,
    QAbstractItemView, QDateEdit, QCheckBox, QStackedWidget,
    QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QClipboard, QKeySequence
import pandas as pd
from database import get_session
from models import Personel, Bordro, Haciz, Avans, Puantaj, HacizOdeme, KasaAcigi, SigaraAcigi, MaasOdeme, SistemAyarlari
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from ui.utils import ModernMesaj, TarihAlani, ModernTarihSecici, tr_lower, make_frameless, get_config_path, make_header
from ui.widgets import ToggleSwitch
import datetime
import calendar
import os
import json

# PDF için gerekli importlar
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

try:
    arial_path = "C:/Windows/Fonts/arial.ttf"
    if os.path.exists(arial_path):
        pdfmetrics.registerFont(TTFont('Arial', arial_path))
        font_name = 'Arial'
    else:
        font_name = 'Helvetica'
except:
    font_name = 'Helvetica'

try:
    from pdf_generator import bordro_pdf_olustur
except ImportError:
    bordro_pdf_olustur = None
    print("Uyarı: pdf_generator modülü bulunamadı, PDF çıktısı alınamayabilir.")


class BordroPage(QWidget):
    bordro_silindi    = pyqtSignal()
    bordro_hesaplandi = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.session = get_session()
        self.asgari_ucret_normal = 28075.50
        self.asgari_ucret_emekli = 30181.00
        self._load_asgari_ucret()   # Veritabanından yükle
        self.init_ui()
        self.load_data()

    def _load_asgari_ucret(self):
        """Veritabanından asgari ücret değerlerini yükle"""
        ayar_normal = self.session.query(SistemAyarlari).filter_by(anahtar='asgari_ucret_normal').first()
        if ayar_normal:
            try:
                self.asgari_ucret_normal = float(ayar_normal.deger)
            except:
                pass
        ayar_emekli = self.session.query(SistemAyarlari).filter_by(anahtar='asgari_ucret_emekli').first()
        if ayar_emekli:
            try:
                self.asgari_ucret_emekli = float(ayar_emekli.deger)
            except:
                pass

    def _save_asgari_ucret(self):
        """Asgari ücret değerlerini veritabanına kaydet"""
        ayar_normal = self.session.query(SistemAyarlari).filter_by(anahtar='asgari_ucret_normal').first()
        if not ayar_normal:
            ayar_normal = SistemAyarlari(anahtar='asgari_ucret_normal')
            self.session.add(ayar_normal)
        ayar_normal.deger = str(self.asgari_ucret_normal)

        ayar_emekli = self.session.query(SistemAyarlari).filter_by(anahtar='asgari_ucret_emekli').first()
        if not ayar_emekli:
            ayar_emekli = SistemAyarlari(anahtar='asgari_ucret_emekli')
            self.session.add(ayar_emekli)
        ayar_emekli.deger = str(self.asgari_ucret_emekli)

        self.session.commit()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        self.setStyleSheet("background-color: #2c3e50;")

        # ========== ÜST PANEL ==========
        top_panel = QFrame()
        top_panel.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 12px;
                border: 1px solid #4a6278;
            }
            QLabel { color: #bdc3c7; background: transparent; }
            QLineEdit, QComboBox {
                background-color: #2c3e50; border: 1px solid #4a6278;
                border-radius: 6px; color: white; padding: 6px 10px;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #3498db; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView { background: #34495e; color: white; selection-background-color: #3498db; }
        """)
        top_panel.setFixedHeight(170)
        top_lay = QVBoxLayout(top_panel)
        top_lay.setContentsMargins(15, 10, 15, 10)

        # 1. SATIR: Dönem + Arama + Filtre
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("📅 Dönem:"))
        self.ay_cb = QComboBox()
        self.ay_cb.addItems(["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])
        self.ay_cb.setCurrentIndex(QDate.currentDate().month() - 1)
        self.ay_cb.setFixedWidth(100)
        self.ay_cb.activated.connect(self.load_data)
        row1.addWidget(self.ay_cb)

        self.yil_cb = QComboBox()
        for y in range(2020, 2035):
            self.yil_cb.addItem(str(y))
        self.yil_cb.setCurrentText(str(QDate.currentDate().year()))
        self.yil_cb.setFixedWidth(80)
        self.yil_cb.activated.connect(self.load_data)
        row1.addWidget(self.yil_cb)

        self.personel_search = QLineEdit()
        self.personel_search.setPlaceholderText("🔍 Personel ara (isim veya sicil)...")
        self.personel_search.setFixedHeight(35)
        self.personel_search.setStyleSheet("border: 1px solid #ced4da; border-radius: 6px; padding-left: 10px;")
        self.personel_search.textChanged.connect(self.load_data)
        row1.addWidget(self.personel_search, 1)

        row1.addWidget(QLabel("Filtre:"))
        self.durum_filter = QComboBox()
        self.durum_filter.addItems(["Tüm Personel", "Sadece Hesaplananlar", "Hesaplanmayanlar"])
        self.durum_filter.setFixedWidth(150)
        self.durum_filter.currentIndexChanged.connect(self.load_data)
        row1.addWidget(self.durum_filter)

        top_lay.addLayout(row1)

        # 2. SATIR: İlk 5 buton
        row2 = QHBoxLayout()
        self.asgari_btn = self.create_btn("💰 Asgari Ücret Ayarla", "#f39c12", self.asgari_ucret_dialog)
        self.hesapla_btn = self.create_btn("⚙️ Maaşları Hesapla", "#3498db", self.bordro_hesapla)
        self.toplu_btn = self.create_btn("📊 Toplu Bordro", "#e1f505", self.toplu_bordro)
        self.excel_btn = self.create_btn("📥 Excel Aktar", "#27ae60", self.excel_aktar)
        self.pdf_btn = self.create_btn("📄 PDF Bordro", "#e67e22", self.pdf_aktar)

        # Elden maaş toggle
        toggle_widget = QWidget()
        toggle_widget.setStyleSheet("background: transparent;")
        toggle_lay = QHBoxLayout(toggle_widget)
        toggle_lay.setContentsMargins(8, 0, 8, 0)
        toggle_lay.setSpacing(6)
        self.elden_toggle = ToggleSwitch(width=46, height=22)
        self.elden_toggle.setChecked(True)
        self.elden_toggle_lbl = QLabel("Elden Maaş Ödemeli Sistem")
        self.elden_toggle_lbl.setStyleSheet("color: #ecf0f1; font-size: 12px; font-weight: bold; background: transparent;")
        self.elden_toggle.toggled.connect(self._elden_toggle_degisti)
        toggle_lay.addWidget(self.elden_toggle)
        toggle_lay.addWidget(self.elden_toggle_lbl)

        row2.addWidget(self.asgari_btn)
        row2.addWidget(self.hesapla_btn)
        row2.addWidget(self.toplu_btn)
        row2.addWidget(self.excel_btn)
        row2.addWidget(self.pdf_btn)
        row2.addWidget(toggle_widget)
        row2.addStretch()
        top_lay.addLayout(row2)

        # 3. SATIR: Kalan butonlar
        row3 = QHBoxLayout()
        self.gecmis_btn = self.create_btn("📆 Bordro Geçmişi", "#21d9c6", self.bordro_gecmis)
        self.maas_odeme_btn = self.create_btn("💰 Maaş Ödemesi Yap", "#2ecc71", self.maas_odeme_yap)
        self.toplu_sil_btn = self.create_btn("🗑️ Toplu Bordro Sil", "#e74c3c", self.toplu_bordro_sil)

        row3.addWidget(self.gecmis_btn)
        row3.addWidget(self.maas_odeme_btn)
        row3.addWidget(self.toplu_sil_btn)
        row3.addStretch()
        top_lay.addLayout(row3)

        layout.addWidget(top_panel)

        # ========== TABLO ==========
        self.table = QTableWidget()
        self.table.setColumnCount(16)
        headers = [
            "SİCİL NO", "PERSONEL", "BRÜT MAAŞ", "RESMİ MAAŞ",
            "HACİZ", "AVANS", "KASA AÇIĞI", "SİGARA AÇIĞI",
            "RAPORLU GÜN", "DEVAMSIZLIK", "KESİNTİ TOPLAM",
            "BANKA", "ELDEN", "DURUM", "PERSONEL DURUMU", "İŞLEMLER"
        ]
        # PyQt5 QHeaderView metin kaydırmayı doğrudan desteklemez.
        # Pratik çözüm: çok kelimeli başlıklarda satır kırılımı kullan.
        headers = [h.replace(" ", "\n") if " " in h else h for h in headers]
        self.table.setHorizontalHeaderLabels(headers)

        hdr = self.table.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignCenter)
        hdr.setFixedHeight(60)

        # Kullanıcı sütun genişliği ayarlayabilsin + sağ tıkla kaydedebilsin
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_column_context_menu)

        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 100)
        self.table.setColumnWidth(6, 100)
        self.table.setColumnWidth(7, 100)
        self.table.setColumnWidth(8, 100)
        self.table.setColumnWidth(9, 100)
        self.table.setColumnWidth(10, 120)
        self.table.setColumnWidth(11, 120)
        self.table.setColumnWidth(12, 120)
        self.table.setColumnWidth(13, 100)
        self.table.setColumnWidth(14, 100)
        self.table.setColumnWidth(15, 80)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #4a6278;
                gridline-color: rgba(0,0,0,0.08);
            }
            QHeaderView::section {
                background-color: #1a2a38;
                color: #ecf0f1;
                font-weight: bold;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid #2c3e50;
            }
            QTableWidget::item {
                padding: 5px;
                color: #1a1a1a;
            }
            QTableWidget::item:selected {
                background-color: rgba(18,52,96,0.85);
                color: white;
            }
            QTableWidget::item:alternate {
                background-color: #f8f9fa;
            }
        """)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self.bordro_gecmis)

        hdr = self.table.horizontalHeader()
        hdr.setSectionsMovable(True)
        hdr.sectionMoved.connect(self._auto_save_layout)
        hdr.sectionResized.connect(self._auto_save_layout)

        layout.addWidget(self.table)
        self.load_column_widths()

    def _widths_path(self):
        return get_config_path("bordro_table_widths.json")

    def _auto_save_layout(self, *args):
        widths = {}; order = []
        hdr = self.table.horizontalHeader()
        for logical in range(self.table.columnCount()):
            widths[str(logical)] = self.table.columnWidth(logical)
        for visual in range(self.table.columnCount()):
            order.append(hdr.logicalIndex(visual))
        try:
            with open(self._widths_path(), "w", encoding="utf-8") as f:
                json.dump({"widths": widths, "order": order}, f)
        except Exception:
            pass

    def save_column_widths(self):
        self._auto_save_layout()
        ModernMesaj.basari(self, "Bordro tablosu düzeni kaydedildi.")

    def load_column_widths(self):
        path = self._widths_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "widths" not in data:
                for i, w in data.items():
                    self.table.setColumnWidth(int(i), int(w))
                return
            widths = data.get("widths", {})
            order = data.get("order", [])
            for i, w in widths.items():
                self.table.setColumnWidth(int(i), int(w))
            hdr = self.table.horizontalHeader()
            for visual, logical in enumerate(order):
                cur = hdr.logicalIndex(visual)
                if cur != logical:
                    hdr.moveSection(hdr.visualIndex(logical), visual)
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
        btn.setFixedSize(140, 40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        btn.clicked.connect(func)
        return btn

    def format_tl(self, deger):
        try:
            val = float(deger)
            parts = f"{abs(val):,.2f}".split(".")
            tam = parts[0].replace(",", ".")
            kesir = parts[1]
            isaret = "-" if val < 0 else ""
            return f"{isaret}{tam},{kesir} ₺"
        except:
            return "0,00 ₺"

    def parse_tl(self, metin):
        if not metin:
            return 0.0
        metin = str(metin).replace("₺", "").replace("TL", "").replace("€", "").strip()
        metin = metin.replace(".", "")
        metin = metin.replace(",", ".")
        try:
            return float(metin)
        except:
            return 0.0

    def _elden_toggle_degisti(self, durum):
        if durum:
            self.elden_toggle_lbl.setText("Elden Maaş Ödemeli Sistem")
            self.elden_toggle_lbl.setStyleSheet("color: #ecf0f1; font-size: 12px; font-weight: bold; background: transparent;")
        else:
            self.elden_toggle_lbl.setText("Tek Maaş Sistemi")
            self.elden_toggle_lbl.setStyleSheet("color: #f39c12; font-size: 12px; font-weight: bold; background: transparent;")

    def asgari_ucret_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Asgari Ücret Ayarları")
        dialog.setFixedWidth(380)
        dialog.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QLabel { color: #bdc3c7; background: transparent; font-size: 11px; }
            QDoubleSpinBox { background-color: #34495e; border: 1px solid #4a6278; border-radius: 8px; color: white; padding: 8px 12px; font-size: 13px; }
            QDoubleSpinBox:focus { border-color: #3498db; }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0px; }
        """)
        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)

        hdr = QFrame(); hdr.setFixedHeight(60)
        hdr.setStyleSheet("QFrame { background-color: #1a3a4a; }")
        hdr_lay = QHBoxLayout(hdr); hdr_lay.setContentsMargins(16, 0, 16, 0)
        tl = QLabel("Asgari Ücret Ayarları")
        tl.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        hdr_lay.addWidget(tl)
        lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body); body_lay.setContentsMargins(20, 16, 20, 10); body_lay.setSpacing(12)

        def field(lbl, widget):
            l = QLabel(lbl); vb = QVBoxLayout(); vb.setSpacing(4)
            vb.addWidget(l); vb.addWidget(widget); return vb

        self.normal_spin = QDoubleSpinBox()
        self.normal_spin.setRange(0, 100000); self.normal_spin.setSuffix(" ₺")
        self.normal_spin.setValue(self.asgari_ucret_normal)
        body_lay.addLayout(field("NORMAL ASGARİ ÜCRET", self.normal_spin))

        self.emekli_spin = QDoubleSpinBox()
        self.emekli_spin.setRange(0, 100000); self.emekli_spin.setSuffix(" ₺")
        self.emekli_spin.setValue(self.asgari_ucret_emekli)
        body_lay.addLayout(field("EMEKLİ ASGARİ ÜCRET", self.emekli_spin))
        lay.addWidget(body)

        btn_frame = QFrame(); btn_frame.setFixedHeight(56)
        btn_frame.setStyleSheet("QFrame { background-color: #243342; border-top: 1px solid #1a2a38; }")
        btn_lay = QHBoxLayout(btn_frame); btn_lay.setContentsMargins(16, 8, 16, 8); btn_lay.setSpacing(8); btn_lay.addStretch()
        kaydet_btn = QPushButton("Kaydet")
        kaydet_btn.setFixedHeight(38)
        kaydet_btn.setStyleSheet("QPushButton { background:#27ae60; color:white; font-weight:bold; border-radius:8px; border:none; padding:0 20px; } QPushButton:hover { background:#2ecc71; }")
        kaydet_btn.clicked.connect(lambda: self.asgari_kaydet(dialog))
        iptal_btn = QPushButton("İptal")
        iptal_btn.setFixedHeight(38)
        iptal_btn.setStyleSheet("QPushButton { background:transparent; color:#7f8c8d; border:1px solid #4a6278; border-radius:8px; padding:0 14px; } QPushButton:hover { background:#34495e; color:white; }")
        iptal_btn.clicked.connect(dialog.reject)
        btn_lay.addWidget(kaydet_btn); btn_lay.addWidget(iptal_btn)
        lay.addWidget(btn_frame)
        dialog.exec_()

    def asgari_kaydet(self, dialog):
        self.asgari_ucret_normal = self.normal_spin.value()
        self.asgari_ucret_emekli = self.emekli_spin.value()
        self._save_asgari_ucret()   # Veritabanına kaydet
        dialog.accept()
        ModernMesaj.basari(self, "Asgari ücret değerleri güncellendi ve kaydedildi.")

    # ---------- BORDRO HESAPLA ----------
    def bordro_hesapla(self):
        yil = int(self.yil_cb.currentText())
        ay = self.ay_cb.currentIndex() + 1
        ilk_gun = datetime.date(yil, ay, 1)
        son_gun = datetime.date(yil, ay, calendar.monthrange(yil, ay)[1])

        # Tüm personelleri al (durum fark etmez)
        # Ancak dönemde çalışmış olanları filtrele: işe başlama <= dönem sonu VE (ayrılma tarihi yoksa veya ayrılma >= dönem başı)
        self.session.expire_all()
        personeller = self.session.query(Personel).filter(
            Personel.ise_baslama <= son_gun,
            (Personel.isten_ayrilma == None) | (Personel.isten_ayrilma >= ilk_gun)
        ).all()

        if not personeller:
            ModernMesaj.uyari(self, "Bu dönemde çalışmış personel bulunamadı.")
            return

        sayac = 0
        hata_sayac = 0
        for p in personeller:
            try:
                brut = p.maas
                if brut <= 0:
                    continue

                # Dönem içindeki çalışma gün sayısını hesapla
                baslangic = max(p.ise_baslama, ilk_gun)
                bitis = min(p.isten_ayrilma if p.isten_ayrilma else son_gun, son_gun)
                if bitis < baslangic:
                    continue  # Bu dönemde hiç çalışmamış
                calisma_gunu = (bitis - baslangic).days + 1
                ay_gun_sayisi = (son_gun - ilk_gun).days + 1
                brut_oran = calisma_gunu / ay_gun_sayisi
                brut_maas = brut * brut_oran

                emekli_mi = "emekli" in (p.aciklama or "").lower()
                resmi_maas = self.asgari_ucret_emekli if emekli_mi else self.asgari_ucret_normal
                resmi_maas = resmi_maas * brut_oran

                gunluk = brut_maas / calisma_gunu if calisma_gunu > 0 else 0

                # Kesintiler
                avans_toplam = self.session.query(func.sum(Avans.tutar)).filter(
                    Avans.personel_id == p.id,
                    Avans.tarih >= ilk_gun,
                    Avans.tarih <= son_gun
                ).scalar() or 0.0

                kasa_toplam = self.session.query(func.sum(KasaAcigi.tutar)).filter(
                    KasaAcigi.personel_id == p.id,
                    KasaAcigi.tarih >= ilk_gun,
                    KasaAcigi.tarih <= son_gun
                ).scalar() or 0.0

                sigara_toplam = self.session.query(func.sum(SigaraAcigi.tutar)).filter(
                    SigaraAcigi.personel_id == p.id,
                    SigaraAcigi.tarih >= ilk_gun,
                    SigaraAcigi.tarih <= son_gun
                ).scalar() or 0.0

                # Puantaj (sadece çalışılan günler için)
                puantaj = self.session.query(Puantaj).filter(
                    Puantaj.personel_id == p.id,
                    Puantaj.yil == yil,
                    Puantaj.ay == ay
                ).first()

                raporlu_gun = 0
                devamsizlik_gun = 0
                if puantaj:
                    for gun in range(1, son_gun.day + 1):
                        tarih = datetime.date(yil, ay, gun)
                        if tarih < baslangic or tarih > bitis:
                            continue
                        kod = getattr(puantaj, f"gun_{gun}", "").upper()
                        if not kod and p.durum == "Pasif":
                            kod = "G"
                        if kod == "R":
                            raporlu_gun += 1
                        elif kod in ("G", "Ü"):
                            devamsizlik_gun += 1
                elif p.durum == "Pasif":
                    devamsizlik_gun = calisma_gunu

                raporlu_kesinti = raporlu_gun * gunluk
                devamsizlik_kesinti = devamsizlik_gun * gunluk
                diger_kesinti = avans_toplam + kasa_toplam + sigara_toplam + raporlu_kesinti + devamsizlik_kesinti
                net_diger_sonrasi = max(brut_maas - diger_kesinti, 0)

                elden_sistem = self.elden_toggle.isChecked()

                if elden_sistem:
                    banka_limiti = min(net_diger_sonrasi, resmi_maas)
                    varsayilan_taksit_baz = resmi_maas
                else:
                    banka_limiti = net_diger_sonrasi
                    varsayilan_taksit_baz = brut_maas

                # Kural 4: En eski tarihli haciz önce
                aktif_hacizler = self.session.query(Haciz).filter(
                    Haciz.personel_id == p.id,
                    Haciz.durum == "Aktif",
                    Haciz.kalan_borc > 0,
                    Haciz.baslangic_tarihi <= son_gun,
                    (Haciz.bitis_tarihi >= ilk_gun) | (Haciz.bitis_tarihi == None)
                ).order_by(Haciz.baslangic_tarihi).all()

                toplam_haciz_kesintisi = 0.0

                if aktif_hacizler:
                    # Kural 2: Taksit ilk (en eski) hacize göre belirlenir
                    ilk_haciz = aktif_hacizler[0]
                    if ilk_haciz.aylik_kesinti and ilk_haciz.aylik_kesinti > 0:
                        aylik_taksit = ilk_haciz.aylik_kesinti
                    else:
                        aylik_taksit = varsayilan_taksit_baz * 0.25

                    # Kural 3: Banka limitini aşamaz
                    kalan_butce = min(aylik_taksit, banka_limiti)

                    for haciz in aktif_hacizler:
                        if kalan_butce <= 0:
                            break
                        # Kesilebilecek: kalan borç ve kalan bütçeden küçük olan
                        gercek_kesinti = min(haciz.kalan_borc, kalan_butce)
                        if gercek_kesinti > 0:
                            toplam_haciz_kesintisi += gercek_kesinti
                            kalan_butce -= gercek_kesinti
                        # NOT: haciz.kalan_borc BURADA GÜNCELLENMİYOR.
                        # kalan_borc yalnızca "Haciz Ödemesi Yap" ile güncellenir.

                banka = max(banka_limiti - toplam_haciz_kesintisi, 0)
                if elden_sistem:
                    elden = net_diger_sonrasi - banka_limiti
                    net_maas = net_diger_sonrasi - toplam_haciz_kesintisi
                else:
                    elden = 0.0
                    net_maas = banka

                bordro = self.session.query(Bordro).filter(
                    Bordro.personel_id == p.id,
                    Bordro.yil == yil,
                    Bordro.ay == ay
                ).first()
                if not bordro:
                    bordro = Bordro(personel_id=p.id, yil=yil, ay=ay)
                    self.session.add(bordro)

                bordro.toplam_net_maas = net_maas
                bordro.resmi_maas = banka
                bordro.icra_kesintisi = toplam_haciz_kesintisi
                bordro.elden_odenecek = elden

                sayac += 1
            except Exception as e:
                hata_sayac += 1
                print(f"Hata - {p.ad_soyad}: {str(e)}")

        try:
            self.session.commit()
            ModernMesaj.basari(self, f"Bordro hesaplandı!\n{len(personeller)} personelden {sayac} kişi hesaplandı.\nHata: {hata_sayac}")
            self.load_data()
            self.bordro_hesaplandi.emit()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, f"Kayıt hatası: {str(e)}")

    # ---------- YÜKLEME METODLARI ----------
    def load_data(self):
        self.table.setRowCount(0)
        yil = int(self.yil_cb.currentText())
        ay = self.ay_cb.currentIndex() + 1
        filtre = self.durum_filter.currentText()
        arama = tr_lower(self.personel_search.text().strip())

        # Bu döneme ait tüm bordroları al
        bordrolar = self.session.query(Bordro).options(joinedload(Bordro.personel)).filter(
            Bordro.yil == yil,
            Bordro.ay == ay
        ).all()

        if filtre == "Sadece Hesaplananlar":
            for b in bordrolar:
                if b.personel is None:
                    continue
                if arama and arama not in tr_lower(b.personel.ad_soyad) and (not b.personel.sicil_no or arama not in tr_lower(b.personel.sicil_no)):
                    continue
                self._satir_ekle(b)

        elif filtre == "Hesaplanmayanlar":
            mevcut_personel_ids = [b.personel_id for b in bordrolar if b.personel]
            personeller = self.session.query(Personel).filter(
                Personel.durum.in_(["Aktif", "Pasif"]),
                ~Personel.id.in_(mevcut_personel_ids)
            ).all()
            if arama:
                personeller = [p for p in personeller if arama in tr_lower(p.ad_soyad) or (p.sicil_no and arama in tr_lower(p.sicil_no))]
            for p in personeller:
                self._satir_ekle_bos(p)

        else:  # Tüm Personel
            for b in bordrolar:
                if b.personel is None:
                    continue
                if arama and arama not in tr_lower(b.personel.ad_soyad) and (not b.personel.sicil_no or arama not in tr_lower(b.personel.sicil_no)):
                    continue
                self._satir_ekle(b)

    def _satir_ekle_bos(self, p):
        arama = tr_lower(self.personel_search.text().strip())
        if arama:
            if arama not in tr_lower(p.ad_soyad) and (not p.sicil_no or arama not in tr_lower(p.sicil_no)):
                return
        """Bordro hesaplanmamış personel için satır ekler"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        # Satır yüksekliğini kompakt tut.
        self.table.setRowHeight(row, 34)
        items = [
            QTableWidgetItem(p.sicil_no or ""),
            QTableWidgetItem(p.ad_soyad),
            QTableWidgetItem(self.format_tl(p.maas)),
            QTableWidgetItem("-"),
            QTableWidgetItem("-"),
            QTableWidgetItem("-"),
            QTableWidgetItem("-"),
            QTableWidgetItem("-"),
            QTableWidgetItem("-"),
            QTableWidgetItem("-"),
            QTableWidgetItem("-"),
            QTableWidgetItem("-"),
            QTableWidgetItem("-"),
            QTableWidgetItem("⚠️ Bekliyor"),
            QTableWidgetItem(p.durum),
            QTableWidgetItem("")
        ]
        for col, item in enumerate(items):
            if col == 13:
                item.setForeground(QColor("#e74c3c"))
            if col == 14:
                if p.durum == "Pasif":
                    item.setForeground(QColor("#e67e22"))
                else:
                    item.setForeground(QColor("#27ae60"))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, item)

    def _satir_ekle(self, bordro):
        p = bordro.personel
        if p is None:
            print(f"Uyarı: Bordro ID {bordro.id} için personel bulunamadı, atlanıyor.")
            return

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 34)

        yil = bordro.yil
        ay = bordro.ay
        ilk_gun = datetime.date(yil, ay, 1)
        son_gun = datetime.date(yil, ay, calendar.monthrange(yil, ay)[1])

        avans_toplam = self.session.query(func.sum(Avans.tutar)).filter(
            Avans.personel_id == p.id,
            Avans.tarih >= ilk_gun,
            Avans.tarih <= son_gun
        ).scalar() or 0.0

        kasa_toplam = self.session.query(func.sum(KasaAcigi.tutar)).filter(
            KasaAcigi.personel_id == p.id,
            KasaAcigi.tarih >= ilk_gun,
            KasaAcigi.tarih <= son_gun
        ).scalar() or 0.0

        sigara_toplam = self.session.query(func.sum(SigaraAcigi.tutar)).filter(
            SigaraAcigi.personel_id == p.id,
            SigaraAcigi.tarih >= ilk_gun,
            SigaraAcigi.tarih <= son_gun
        ).scalar() or 0.0

        puantaj = self.session.query(Puantaj).filter(
            Puantaj.personel_id == p.id,
            Puantaj.yil == yil,
            Puantaj.ay == ay
        ).first()
        raporlu_gun = 0
        devamsizlik_gun = 0
        if puantaj:
            for gun in range(1, son_gun.day + 1):
                kod = getattr(puantaj, f"gun_{gun}", "").upper()
                if not kod and p.durum == "Pasif":
                    kod = "G"
                if kod == "R":
                    raporlu_gun += 1
                elif kod in ("G", "Ü"):
                    devamsizlik_gun += 1
        elif p.durum == "Pasif":
            devamsizlik_gun = son_gun.day
        raporlu_kesinti = raporlu_gun * (p.maas / 30)
        devamsizlik_kesinti = devamsizlik_gun * (p.maas / 30)

        emekli_mi = "emekli" in (p.aciklama or "").lower()
        resmi_maas = self.asgari_ucret_emekli if emekli_mi else self.asgari_ucret_normal

        haciz_tutari = bordro.icra_kesintisi

        odeme_var = self.session.query(MaasOdeme).filter(MaasOdeme.bordro_id == bordro.id).first()
        durum_text = "✅ Ödendi" if odeme_var else "✅ Hesaplandı"
        durum_rengi = QColor("#27ae60") if odeme_var else QColor("#2980b9")

        items = [
            QTableWidgetItem(p.sicil_no or ""),
            QTableWidgetItem(p.ad_soyad),
            QTableWidgetItem(self.format_tl(p.maas)),
            QTableWidgetItem(self.format_tl(resmi_maas)),
            QTableWidgetItem(self.format_tl(haciz_tutari)),
            QTableWidgetItem(self.format_tl(avans_toplam)),
            QTableWidgetItem(self.format_tl(kasa_toplam)),
            QTableWidgetItem(self.format_tl(sigara_toplam)),
            QTableWidgetItem(f"{raporlu_gun} gün ({self.format_tl(raporlu_kesinti)})"),
            QTableWidgetItem(f"{devamsizlik_gun} gün ({self.format_tl(devamsizlik_kesinti)})"),
            QTableWidgetItem(self.format_tl(avans_toplam + kasa_toplam + sigara_toplam + raporlu_kesinti + devamsizlik_kesinti + bordro.icra_kesintisi)),
            QTableWidgetItem(self.format_tl(bordro.resmi_maas)),
            QTableWidgetItem(self.format_tl(bordro.elden_odenecek)),
            QTableWidgetItem(durum_text),
            QTableWidgetItem(p.durum),
            QTableWidgetItem("")
        ]
        for col, item in enumerate(items):
            if col == 12:
                item.setForeground(QColor("#e67e22"))
            if col == 11:
                item.setForeground(QColor("#27ae60"))
            if col == 13:
                item.setForeground(durum_rengi)
            if col == 14:
                if p.durum == "Pasif":
                    item.setForeground(QColor("#e67e22"))
                else:
                    item.setForeground(QColor("#27ae60"))
            if col == 1:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, item)

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setAlignment(Qt.AlignCenter)

        # Emoji bazı fontlarda kırpılabildiği için font/padding ile stabilize ediyoruz.
        sil_btn = QPushButton("🗑")
        sil_btn.setFixedSize(24, 24)
        sil_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 4px;
                font-family: "Segoe UI Emoji";
                font-size: 12px;
                font-weight: bold;
                border: none;
                padding: 0px;
                padding-bottom: 1px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        sil_btn.setCursor(Qt.PointingHandCursor)
        sil_btn.clicked.connect(lambda checked, bid=bordro.id: self.sil_bordro(bid))
        btn_layout.addWidget(sil_btn)

        self.table.setCellWidget(row, 15, btn_widget)

    def sil_bordro(self, bordro_id):
        cevap = ModernMesaj.soru(self, "Bu bordro kaydını silmek istediğinize emin misiniz?\nİlişkili tüm ödemeler de silinecektir!")
        if cevap:
            try:
                bordro = self.session.get(Bordro, bordro_id)
                if bordro:
                    self.session.query(MaasOdeme).filter(MaasOdeme.bordro_id == bordro_id).delete()
                    self.session.query(HacizOdeme).filter(HacizOdeme.bordro_id == bordro_id).delete()
                    self.session.delete(bordro)
                    self.session.commit()
                    self.load_data()
                    self.bordro_silindi.emit()
                    ModernMesaj.basari(self, "Bordro silindi.")
            except Exception as e:
                self.session.rollback()
                ModernMesaj.hata(self, f"Silme hatası: {str(e)}")

    # ---------- TOPLU BORDRO SİL ----------
    def toplu_bordro_sil(self):
        yil = int(self.yil_cb.currentText())
        ay = self.ay_cb.currentIndex() + 1

        bordrolar = self.session.query(Bordro).filter(
            Bordro.yil == yil,
            Bordro.ay == ay
        ).all()

        gecerli_bordrolar = [b for b in bordrolar if b.personel is not None]

        if not gecerli_bordrolar:
            ModernMesaj.uyari(self, "Bu dönem için silinecek bordro bulunamadı.")
            return

        dialog = QDialog(self, Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setWindowTitle("Toplu Bordro Sil")
        dialog.resize(820, 520)
        dialog.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QLabel { background: transparent; color: #ecf0f1; }
            QTableWidget { background-color: #34495e; border: none; color: white; gridline-color: rgba(255,255,255,0.1); }
            QHeaderView::section { background-color: #1a2a38; color: #bdc3c7; font-weight: bold; padding: 8px; border: none; }
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background-color: rgba(231,76,60,0.4); }
        """)
        make_frameless(dialog)

        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QFrame(); hdr.setFixedHeight(70)
        hdr.setStyleSheet("QFrame { background-color: #7b241c; }")
        hdr_lay = QHBoxLayout(hdr); hdr_lay.setContentsMargins(20, 0, 20, 0); hdr_lay.setSpacing(12)
        ic = QLabel("🗑️"); ic.setFixedSize(44, 44); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background-color: #e74c3c; border-radius: 22px; font-size: 20px;")
        tl = QLabel("Toplu Bordro Sil"); tl.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        hdr_lay.addWidget(ic); hdr_lay.addWidget(tl); hdr_lay.addStretch()
        lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body); body_lay.setContentsMargins(16, 12, 16, 10); body_lay.setSpacing(10)

        uyari = QLabel("⚠️ Seçilen bordrolar ve ilişkili tüm ödemeler (maaş, haciz) silinecektir. Bu işlem geri alınamaz!")
        uyari.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 8px 12px; background-color: rgba(231,76,60,0.15); border-radius: 6px; border: 1px solid rgba(231,76,60,0.3);")
        uyari.setWordWrap(True)
        body_lay.addWidget(uyari)

        # ========== TABLO OLUŞTURMA VE SÜTUN AYARLARI ==========
        self.sil_table = QTableWidget()
        self.sil_table.setColumnCount(5)
        self.sil_table.setHorizontalHeaderLabels(["Seçim", "Sicil No", "Personel", "Net Maaş", "Durum"])
        
        # Seçim ve Sicil No sütunlarını sabit genişlikte yap
        self.sil_table.setColumnWidth(0, 60)          # Seçim sütunu
        self.sil_table.setColumnWidth(1, 90)          # Sicil No sütunu
        self.sil_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.sil_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        
        # Diğer sütunları esnek yap (kalan alana yayılır)
        self.sil_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Personel
        self.sil_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # Net Maaş
        self.sil_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)  # Durum
        
        # Son sütunun gereksiz esnemesini engellemek için
        self.sil_table.horizontalHeader().setStretchLastSection(False)
        
        self.sil_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sil_table.verticalHeader().setVisible(False)
        self.sil_table.setRowCount(len(gecerli_bordrolar))
        self.sil_table.verticalHeader().setDefaultSectionSize(30)  # Satır yüksekliği

        for i, bordro in enumerate(gecerli_bordrolar):
            toggle = ToggleSwitch(width=28, height=16)
            toggle.setChecked(False)
            toggle.setProperty("bordro_id", bordro.id)
            toggle.stateChanged.connect(lambda state, idx=i: self.sil_toggle_changed(idx, state))
            toggle_widget = QWidget()
            toggle_widget.setFixedSize(36, 24)
            toggle_layout = QHBoxLayout(toggle_widget)
            toggle_layout.setAlignment(Qt.AlignCenter)
            toggle_layout.setContentsMargins(0, 0, 0, 0)
            toggle_layout.addWidget(toggle)
            self.sil_table.setCellWidget(i, 0, toggle_widget)
            self.sil_table.setRowHeight(i, 28)

            self.sil_table.setItem(i, 1, QTableWidgetItem(bordro.personel.sicil_no or ""))
            self.sil_table.setItem(i, 2, QTableWidgetItem(bordro.personel.ad_soyad))
            self.sil_table.setItem(i, 3, QTableWidgetItem(self.format_tl(bordro.toplam_net_maas)))
            odeme_var = self.session.query(MaasOdeme).filter(MaasOdeme.bordro_id == bordro.id).first()
            self.sil_table.setItem(i, 4, QTableWidgetItem("Ödendi" if odeme_var else "Hesaplandı"))

        body_lay.addWidget(self.sil_table)

        # ========== SEÇİM BUTONLARI ==========
        sec_row = QHBoxLayout()
        sec_row.setSpacing(8)
        self.tumunu_sec_btn = QPushButton("✅ Tümünü Seç")
        self.tumunu_sec_btn.setFixedHeight(34)
        self.tumunu_sec_btn.setStyleSheet("QPushButton { background:#3498db; color:white; font-weight:bold; border-radius:6px; border:none; padding:0 12px; } QPushButton:hover { background:#2980b9; }")
        self.tumunu_sec_btn.clicked.connect(lambda: self.tumunu_isaretle_sil(True))
        self.tumunu_kaldir_btn = QPushButton("❌ Tümünü Kaldır")
        self.tumunu_kaldir_btn.setFixedHeight(34)
        self.tumunu_kaldir_btn.setStyleSheet("QPushButton { background:#636e72; color:white; font-weight:bold; border-radius:6px; border:none; padding:0 12px; } QPushButton:hover { background:#4a4f52; }")
        self.tumunu_kaldir_btn.clicked.connect(lambda: self.tumunu_isaretle_sil(False))
        sec_row.addWidget(self.tumunu_sec_btn)
        sec_row.addWidget(self.tumunu_kaldir_btn)
        sec_row.addStretch()
        body_lay.addLayout(sec_row)
        lay.addWidget(body)

        # ========== ALT BUTONLAR ==========
        btn_frame = QFrame()
        btn_frame.setFixedHeight(60)
        btn_frame.setStyleSheet("QFrame { background-color: #243342; border-top: 1px solid #1a2a38; }")
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setContentsMargins(16, 10, 16, 10)
        btn_lay.setSpacing(10)
        btn_lay.addStretch()

        sil_btn = QPushButton("  Seçilenleri Sil")
        sil_btn.setFixedHeight(40)
        sil_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color:white; font-weight:bold; border-radius:8px; border:none; padding:0 24px; } QPushButton:hover { background-color:#c0392b; }")
        sil_btn.clicked.connect(lambda: self.toplu_sil_kaydet(dialog, gecerli_bordrolar))

        iptal_btn = QPushButton("İptal")
        iptal_btn.setFixedHeight(40)
        iptal_btn.setStyleSheet("QPushButton { background:transparent; color:#7f8c8d; border:1px solid #4a6278; border-radius:8px; padding:0 16px; } QPushButton:hover { background:#34495e; color:white; }")
        iptal_btn.clicked.connect(dialog.reject)

        btn_lay.addWidget(sil_btn)
        btn_lay.addWidget(iptal_btn)
        lay.addWidget(btn_frame)

        dialog.exec_()

    def sil_toggle_changed(self, row, state):
        # Bu metod, toggle durumu değiştiğinde çağrılır. Gerekirse seçili listeyi güncelleyebilirsiniz.
        pass

    def tumunu_isaretle_sil(self, sec):
        for row in range(self.sil_table.rowCount()):
            w = self.sil_table.cellWidget(row, 0)
            if w:
                toggle = w.findChild(ToggleSwitch)
                if toggle:
                    toggle.blockSignals(True)
                    toggle.setChecked(sec)
                    toggle.blockSignals(False)

    def toplu_sil_kaydet(self, dialog, bordrolar):
        secilenler = []
        for i, bordro in enumerate(bordrolar):
            w = self.sil_table.cellWidget(i, 0)
            if w:
                toggle = w.findChild(ToggleSwitch)
                if toggle and toggle.isChecked():
                    secilenler.append(bordro)

        if not secilenler:
            ModernMesaj.uyari(dialog, "Lütfen en az bir bordro seçin.")
            return

        cevap = ModernMesaj.soru(
            dialog,
            f"{len(secilenler)} bordro kaydı silinecek. İlişkili tüm ödemeler de silinecektir. Devam edilsin mi?"
        )
        if not cevap:
            return

        try:
            silinen = 0
            for bordro in secilenler:
                self.session.query(MaasOdeme).filter(MaasOdeme.bordro_id == bordro.id).delete()
                self.session.query(HacizOdeme).filter(HacizOdeme.bordro_id == bordro.id).delete()
                self.session.delete(bordro)
                silinen += 1

            self.session.commit()
            ModernMesaj.basari(dialog, f"{silinen} bordro silindi.")
            dialog.accept()
            self.load_data()
            self.bordro_silindi.emit()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(dialog, f"Silme hatası: {str(e)}")

    # ---------- TOPLU BORDRO ----------
    def toplu_bordro(self):
        yil = int(self.yil_cb.currentText())
        ay = self.ay_cb.currentIndex() + 1

        bordrolar = self.session.query(Bordro).filter(
            Bordro.yil == yil,
            Bordro.ay == ay
        ).all()

        gecerli_bordrolar = [b for b in bordrolar if b.personel is not None]

        if not gecerli_bordrolar:
            ModernMesaj.uyari(self, "Bu dönem için bordro hesaplanmamış veya geçerli personel bulunamadı.")
            return

        dialog = QDialog(self, Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setWindowTitle("📊 Toplu Bordro Özeti")
        dialog.resize(760, 620)
        dialog.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QLabel { background: transparent; color: #ecf0f1; }
            QTableWidget { background-color: #34495e; border: none; gridline-color: rgba(255,255,255,0.07); }
            QHeaderView::section { background-color: #1a2a38; color: #bdc3c7; font-weight: bold; padding: 8px; border: none; }
            QTableWidget::item { padding: 6px; color: #1a1a1a; background-color: white; }
            QTableWidget::item:alternate { background-color: #f5f8fa; color: #1a1a1a; }
            QTableWidget::item:selected { background-color: rgba(52,152,219,0.5); color: white; }
        """)
        make_frameless(dialog)
        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QFrame(); hdr.setFixedHeight(70)
        hdr.setStyleSheet("QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a5276,stop:1 #2980b9); }")
        hdr_lay = QHBoxLayout(hdr); hdr_lay.setContentsMargins(20,0,20,0); hdr_lay.setSpacing(12)
        ic = QLabel("📊"); ic.setFixedSize(44,44); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.2); border-radius:22px; font-size:22px;")
        ttl_col = QVBoxLayout(); ttl_col.setSpacing(2)
        ttl_col.addWidget(_lbl := QLabel(f"{self.ay_cb.currentText()} {yil} Dönemi Bordro Özeti"))
        _lbl.setStyleSheet("color:white; font-size:15px; font-weight:bold; background:transparent;")
        _sub = QLabel(f"{len(gecerli_bordrolar)} personel")
        _sub.setStyleSheet("color:rgba(255,255,255,0.65); font-size:11px; background:transparent;")
        ttl_col.addWidget(_sub)
        hdr_lay.addWidget(ic); hdr_lay.addLayout(ttl_col); hdr_lay.addStretch()
        lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background:#2c3e50;")
        body_lay = QVBoxLayout(body); body_lay.setContentsMargins(16,12,16,10); body_lay.setSpacing(10)

        toplam_brut = sum(b.personel.maas for b in gecerli_bordrolar)
        toplam_net = sum(b.toplam_net_maas for b in gecerli_bordrolar)
        toplam_kesinti = toplam_brut - toplam_net
        personel_sayisi = len(gecerli_bordrolar)

        kart_layout = QHBoxLayout(); kart_layout.setSpacing(8)
        kart_layout.addWidget(self._kart_olustur("👥 Personel", str(personel_sayisi), "#3498db"))
        kart_layout.addWidget(self._kart_olustur("💰 Toplam Brüt", self.format_tl(toplam_brut), "#27ae60"))
        kart_layout.addWidget(self._kart_olustur("💵 Toplam Net", self.format_tl(toplam_net), "#2980b9"))
        kart_layout.addWidget(self._kart_olustur("📉 Toplam Kesinti", self.format_tl(toplam_kesinti), "#e74c3c"))
        body_lay.addLayout(kart_layout)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Personel", "Brüt Maaş", "Net Maaş", "Kesinti"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setStyleSheet("""
            QTableWidget { background-color: white; border-radius: 8px; border: none; gridline-color: #ecf0f1; }
            QHeaderView::section { background-color: #2c3e50; color: white; font-weight: bold; padding: 8px; border: none; }
            QTableWidget::item { color: #1a1a1a; padding: 6px; }
            QTableWidget::item:alternate { background-color: #f5f8fa; color: #1a1a1a; }
            QTableWidget::item:selected { background-color: #3498db; color: white; }
        """)

        for i, b in enumerate(gecerli_bordrolar):
            table.insertRow(i)
            table.setItem(i, 0, QTableWidgetItem(b.personel.ad_soyad))
            brut_item = QTableWidgetItem(self.format_tl(b.personel.maas))
            brut_item.setForeground(QColor("#27ae60"))
            table.setItem(i, 1, brut_item)
            net_item = QTableWidgetItem(self.format_tl(b.toplam_net_maas))
            net_item.setForeground(QColor("#2980b9"))
            table.setItem(i, 2, net_item)
            kes = b.personel.maas - b.toplam_net_maas
            kes_item = QTableWidgetItem(self.format_tl(kes))
            if kes > 0: kes_item.setForeground(QColor("#e74c3c"))
            table.setItem(i, 3, kes_item)
            for c in range(4):
                if table.item(i,c): table.item(i,c).setTextAlignment(Qt.AlignCenter)

        body_lay.addWidget(table)
        lay.addWidget(body)

        btn_frame = QFrame(); btn_frame.setFixedHeight(60)
        btn_frame.setStyleSheet("QFrame { background-color: #243342; border-top: 1px solid #1a2a38; }")
        btn_lay = QHBoxLayout(btn_frame); btn_lay.setContentsMargins(16,10,16,10); btn_lay.setSpacing(8); btn_lay.addStretch()

        excel_btn = QPushButton("📥 Excel Aktar")
        excel_btn.setFixedHeight(38)
        excel_btn.setStyleSheet("QPushButton { background:#27ae60; color:white; font-weight:bold; border-radius:8px; border:none; padding:0 16px; } QPushButton:hover { background:#2ecc71; }")
        excel_btn.clicked.connect(lambda: self.toplu_excel_aktar(dialog, gecerli_bordrolar, yil, ay))

        pdf_btn = QPushButton("📄 PDF Aktar")
        pdf_btn.setFixedHeight(38)
        pdf_btn.setStyleSheet("QPushButton { background:#e67e22; color:white; font-weight:bold; border-radius:8px; border:none; padding:0 16px; } QPushButton:hover { background:#d35400; }")
        pdf_btn.clicked.connect(lambda: self.toplu_pdf_aktar(dialog, gecerli_bordrolar, yil, ay))

        kapat_btn = QPushButton("Kapat")
        kapat_btn.setFixedHeight(38)
        kapat_btn.setStyleSheet("QPushButton { background:transparent; color:#7f8c8d; border:1px solid #4a6278; border-radius:8px; padding:0 16px; } QPushButton:hover { background:#34495e; color:white; }")
        kapat_btn.clicked.connect(dialog.accept)

        btn_lay.addWidget(excel_btn); btn_lay.addWidget(pdf_btn); btn_lay.addWidget(kapat_btn)
        lay.addWidget(btn_frame)

        dialog.exec_()

    def _kart_olustur(self, baslik, deger, renk):
        kart = QFrame()
        kart.setFixedHeight(100)
        kart.setStyleSheet(f"""
            QFrame {{
                background-color: {renk};
                border-radius: 10px;
                color: white;
            }}
        """)
        vbox = QVBoxLayout(kart)
        baslik_label = QLabel(baslik)
        baslik_label.setStyleSheet("font-size: 14px; font-weight: normal; color: white;")
        baslik_label.setAlignment(Qt.AlignCenter)
        deger_label = QLabel(deger)
        deger_label.setStyleSheet("font-size: 22px; font-weight: bold; color: white;")
        deger_label.setAlignment(Qt.AlignCenter)
        vbox.addWidget(baslik_label)
        vbox.addWidget(deger_label)
        return kart

    def toplu_excel_aktar(self, dialog, bordrolar, yil, ay):
        path, _ = QFileDialog.getSaveFileName(
            dialog,
            "Excel Dosyası Kaydet",
            f"Toplu_Bordro_Ozeti_{self.ay_cb.currentText()}_{yil}.xlsx",
            "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            data = []
            for b in bordrolar:
                data.append([
                    b.personel.ad_soyad,
                    b.personel.maas,
                    b.toplam_net_maas,
                    b.personel.maas - b.toplam_net_maas
                ])
            df = pd.DataFrame(data, columns=["Personel", "Brüt", "Net", "Kesinti"])
            df.to_excel(path, index=False)
            ModernMesaj.basari(dialog, "Excel dosyası oluşturuldu.")
        except Exception as e:
            ModernMesaj.hata(dialog, str(e))

    def toplu_pdf_aktar(self, dialog, bordrolar, yil, ay):
        path, _ = QFileDialog.getSaveFileName(
            dialog,
            "PDF Dosyası Kaydet",
            f"Toplu_Bordro_Ozeti_{self.ay_cb.currentText()}_{yil}.pdf",
            "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            doc = SimpleDocTemplate(path)
            elements = []

            styles = getSampleStyleSheet()
            style_title = ParagraphStyle(
                name='Title',
                fontName=font_name,
                fontSize=16,
                leading=20,
                alignment=1
            )

            elements.append(Paragraph(f"<b>{self.ay_cb.currentText()} {yil} Dönemi Bordro Özeti</b>", style_title))
            elements.append(Spacer(1, 0.2 * inch))

            toplam_brut = sum(b.personel.maas for b in bordrolar)
            toplam_net = sum(b.toplam_net_maas for b in bordrolar)
            toplam_kesinti = toplam_brut - toplam_net
            personel_sayisi = len(bordrolar)

            data = [
                ["Personel Sayısı:", str(personel_sayisi)],
                ["Toplam Brüt Maaş:", f"{toplam_brut:.2f} TL"],
                ["Toplam Net Maaş:", f"{toplam_net:.2f} TL"],
                ["Toplam Kesinti:", f"{toplam_kesinti:.2f} TL"]
            ]
            table = Table(data, colWidths=[150, 200])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

            detay_data = [["Personel", "Brüt (TL)", "Net (TL)", "Kesinti (TL)", "İmza"]]
            for b in bordrolar:
                detay_data.append([
                    b.personel.ad_soyad,
                    f"{b.personel.maas:.2f}",
                    f"{b.toplam_net_maas:.2f}",
                    f"{b.personel.maas - b.toplam_net_maas:.2f}",
                    "__________________"
                ])

            detay_table = Table(detay_data, colWidths=[200, 80, 80, 80, 150])
            detay_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(detay_table)

            doc.build(elements)
            ModernMesaj.basari(dialog, "PDF dosyası oluşturuldu.")
        except Exception as e:
            ModernMesaj.hata(dialog, str(e))

    # ---------- EXCEL AKTAR (Ana tablo) ----------
    def excel_aktar(self):
        yil = int(self.yil_cb.currentText())
        ay = self.ay_cb.currentIndex() + 1
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel Dosyası Kaydet",
            f"Bordro_{self.ay_cb.currentText()}_{yil}.xlsx",
            "Excel (*.xlsx)"
        )
        if not path:
            return

        try:
            data = []
            for r in range(self.table.rowCount()):
                sicil = self.table.item(r, 0).text() if self.table.item(r, 0) else ""
                personel = self.session.query(Personel).filter(Personel.sicil_no == sicil).first() if sicil else None
                iban = personel.iban if personel and personel.iban else ""

                satir = []
                for c in range(self.table.columnCount() - 1):
                    item = self.table.item(r, c)
                    text = item.text() if item else ""
                    if c in (2, 3, 4, 5, 6, 7, 10, 11, 12):
                        satir.append(self.parse_tl(text))
                    else:
                        satir.append(text)
                satir.append(iban)
                data.append(satir)

            columns = [
                "Sicil No", "Personel", "Brüt Maaş", "Resmi Maaş",
                "Haciz", "Avans", "Kasa Açığı", "Sigara Açığı",
                "Raporlu Gün", "Devamsızlık", "Kesinti Toplam",
                "Banka", "Elden", "Durum", "Personel Durumu", "IBAN"
            ]
            df = pd.DataFrame(data, columns=columns)
            df.to_excel(path, index=False)
            ModernMesaj.basari(self, "Excel dosyası oluşturuldu.")
        except Exception as e:
            ModernMesaj.hata(self, str(e))

    # ---------- PDF AKTAR (Bireysel bordro) ----------
    def pdf_aktar(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            ModernMesaj.uyari(self, "Lütfen bir personel seçin.")
            return

        sicil = self.table.item(selected_row, 0).text()
        personel = self.session.query(Personel).filter(Personel.sicil_no == sicil).first()
        if not personel:
            return

        yil = int(self.yil_cb.currentText())
        ay = self.ay_cb.currentIndex() + 1
        bordro = self.session.query(Bordro).filter(
            Bordro.personel_id == personel.id,
            Bordro.yil == yil,
            Bordro.ay == ay
        ).first()

        if not bordro:
            ModernMesaj.uyari(self, "Bu personel için bordro hesaplanmamış.")
            return

        ilk_gun = datetime.date(yil, ay, 1)
        son_gun = datetime.date(yil, ay, calendar.monthrange(yil, ay)[1])

        avanslar = self.session.query(Avans).filter(
            Avans.personel_id == personel.id,
            Avans.tarih >= ilk_gun,
            Avans.tarih <= son_gun
        ).all()
        avans_toplam = sum(a.tutar for a in avanslar)
        avans_detay = "\n".join([f"{a.tarih.strftime('%d.%m.%Y')}: {a.tutar:.2f} TL" for a in avanslar])

        kasa_aciklari = self.session.query(KasaAcigi).filter(
            KasaAcigi.personel_id == personel.id,
            KasaAcigi.tarih >= ilk_gun,
            KasaAcigi.tarih <= son_gun
        ).all()
        kasa_toplam = sum(k.tutar for k in kasa_aciklari)
        kasa_detay = "\n".join([f"{k.tarih.strftime('%d.%m.%Y')}: {k.tutar:.2f} TL" for k in kasa_aciklari])

        sigara_aciklari = self.session.query(SigaraAcigi).filter(
            SigaraAcigi.personel_id == personel.id,
            SigaraAcigi.tarih >= ilk_gun,
            SigaraAcigi.tarih <= son_gun
        ).all()
        sigara_toplam = sum(s.tutar for s in sigara_aciklari)
        sigara_detay = "\n".join([f"{s.tarih.strftime('%d.%m.%Y')}: {s.tutar:.2f} TL" for s in sigara_aciklari])

        puantaj = self.session.query(Puantaj).filter(
            Puantaj.personel_id == personel.id,
            Puantaj.yil == yil,
            Puantaj.ay == ay
        ).first()
        raporlu_gun = 0
        devamsizlik_gun = 0
        if puantaj:
            for gun in range(1, son_gun.day + 1):
                kod = getattr(puantaj, f"gun_{gun}", "").upper()
                if kod == "R":
                    raporlu_gun += 1
                elif kod in ("G", "Ü"):
                    devamsizlik_gun += 1
        raporlu_kesinti = raporlu_gun * (personel.maas / 30)
        devamsizlik_kesinti = devamsizlik_gun * (personel.maas / 30)
        raporlu_detay = f"{raporlu_gun} gün"
        devamsizlik_detay = f"{devamsizlik_gun} gün"

        haciz_odemeleri = self.session.query(HacizOdeme).join(Haciz).filter(
            Haciz.personel_id == personel.id,
            HacizOdeme.tarih >= ilk_gun,
            HacizOdeme.tarih <= son_gun
        ).all()
        haciz_toplam = sum(o.tutar for o in haciz_odemeleri)
        haciz_detay = "\n".join([f"{o.tarih.strftime('%d.%m.%Y')}: {o.tutar:.2f} TL (Dosya: {o.haciz.dosya_no})" for o in haciz_odemeleri])

        if bordro_pdf_olustur is None:
            ModernMesaj.hata(self, "PDF oluşturma modülü bulunamadı.")
            return

        sonuc = {
            'brut': personel.maas,
            'avans': avans_toplam,
            'avans_detay': avans_detay,
            'kasa': kasa_toplam,
            'kasa_detay': kasa_detay,
            'sigara': sigara_toplam,
            'sigara_detay': sigara_detay,
            'toplam_haciz': haciz_toplam,
            'haciz_detay': haciz_detay,
            'raporlu_gun': raporlu_gun,
            'raporlu_kesinti': raporlu_kesinti,
            'raporlu_detay': raporlu_detay,
            'devamsizlik_gun': devamsizlik_gun,
            'devamsizlik_kesinti': devamsizlik_kesinti,
            'devamsizlik_detay': devamsizlik_detay,
            'net': bordro.toplam_net_maas,
            'banka': bordro.resmi_maas,
            'elden': bordro.elden_odenecek
        }
        try:
            dosya = bordro_pdf_olustur(
                personel.ad_soyad,
                f"{self.ay_cb.currentText()}_{bordro.yil}",
                sonuc
            )
            ModernMesaj.basari(self, f"PDF oluşturuldu:\n{dosya}")
        except Exception as e:
            ModernMesaj.hata(self, f"PDF hatası: {str(e)}")

    # ---------- BORDRO GEÇMİŞİ ----------
    def bordro_gecmis(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            ModernMesaj.uyari(self, "Lütfen bir personel seçin.")
            return

        sicil = self.table.item(selected_row, 0).text()
        personel = self.session.query(Personel).filter(Personel.sicil_no == sicil).first()
        if not personel:
            return

        bordrolar = self.session.query(Bordro).filter(
            Bordro.personel_id == personel.id
        ).order_by(Bordro.yil.desc(), Bordro.ay.desc()).all()

        if not bordrolar:
            ModernMesaj.uyari(self, "Bu personel için bordro geçmişi bulunamadı.")
            return

        dialog = QDialog(self, Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setWindowTitle(f"📆 Bordro Geçmişi - {personel.ad_soyad}")
        dialog.resize(600, 400)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Frameless dialog with drag support
        make_frameless(dialog, header_height=50)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                border-radius: 15px;
                border: 2px solid #1a2a38;
            }
            QLabel {
                color: #ecf0f1;
                background: transparent;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        # Gradient header
        header, close_btn = make_header("📆", "Bordro Geçmişi", "#1a3a5c", "#2980b9", dialog)
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(header)

        # Content area with dark background
        content = QWidget()
        content.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
            }
            QTableWidget {
                background-color: #34495e;
                border: none;
                gridline-color: rgba(255,255,255,0.1);
                color: #ecf0f1;
                font-size: 12px;
                selection-background-color: rgba(52,152,219,0.5);
            }
            QHeaderView::section {
                background-color: #1a2a38;
                color: #bdc3c7;
                font-weight: bold;
                border: none;
                padding: 8px;
            }
            QTableWidget::item {
                color: #ecf0f1;
                padding: 6px;
            }
        """)

        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(8)

        table = QTableWidget()
        table.setColumnCount(8)
        headers = ["Dönem", "Brüt Maaş", "Kesinti", "İcra",
                   "Banka Ödeme Tarihi", "Banka Ödeme Tutarı",
                   "Elden Ödeme Tarihi", "Elden Ödeme Tutarı"]
        headers = [h.replace(" ", "\n") if " " in h and "\n" not in h else h for h in headers]
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        hdr = table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setDefaultAlignment(Qt.AlignCenter)
        hdr.setFixedHeight(60)
        hdr.sectionResized.connect(lambda: _save_gecmis_widths(table))

        def _save_gecmis_widths(t):
            widths = {str(i): t.columnWidth(i) for i in range(t.columnCount())}
            try:
                with open(get_config_path("bordro_gecmis_table_widths.json"), "w", encoding="utf-8") as f:
                    json.dump(widths, f)
            except Exception:
                pass

        gecmis_widths_path = get_config_path("bordro_gecmis_table_widths.json")
        if os.path.exists(gecmis_widths_path):
            try:
                with open(gecmis_widths_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for i, w in saved.items():
                    table.setColumnWidth(int(i), int(w))
            except Exception:
                pass

        for i, b in enumerate(bordrolar):
            table.insertRow(i)
            donem = f"{b.ay:02d}/{b.yil}"
            table.setItem(i, 0, QTableWidgetItem(donem))
            table.setItem(i, 1, QTableWidgetItem(self.format_tl(b.personel.maas)))
            table.setItem(i, 2, QTableWidgetItem(self.format_tl(b.personel.maas - b.toplam_net_maas)))
            table.setItem(i, 3, QTableWidgetItem(self.format_tl(b.icra_kesintisi)))

            banka_odeme = self.session.query(MaasOdeme).filter(
                MaasOdeme.bordro_id == b.id,
                ~func.lower(MaasOdeme.aciklama).like("%elden%")
            ).first()
            elden_odeme = self.session.query(MaasOdeme).filter(
                MaasOdeme.bordro_id == b.id,
                func.lower(MaasOdeme.aciklama).like("%elden%")
            ).first()

            if banka_odeme:
                table.setItem(i, 4, QTableWidgetItem(banka_odeme.tarih.strftime("%d/%m/%Y") if banka_odeme.tarih else "-"))
                table.setItem(i, 5, QTableWidgetItem(self.format_tl(banka_odeme.tutar) if banka_odeme.tutar else "-"))
            else:
                table.setItem(i, 4, QTableWidgetItem("-"))
                table.setItem(i, 5, QTableWidgetItem("-"))

            if elden_odeme:
                table.setItem(i, 6, QTableWidgetItem(elden_odeme.tarih.strftime("%d/%m/%Y") if elden_odeme.tarih else "-"))
                table.setItem(i, 7, QTableWidgetItem(self.format_tl(elden_odeme.tutar) if elden_odeme.tutar else "-"))
            else:
                table.setItem(i, 6, QTableWidgetItem("-"))
                table.setItem(i, 7, QTableWidgetItem("-"))

        vbox.addWidget(table)

        kapat_btn = QPushButton("Kapat")
        kapat_btn.setFixedHeight(35)
        kapat_btn.setFixedWidth(120)
        kapat_btn.clicked.connect(dialog.close)
        vbox.addWidget(kapat_btn, alignment=Qt.AlignCenter)

        layout.addWidget(content)

        dialog.exec_()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copy_selection()
        else:
            super().keyPressEvent(event)

    def copy_selection(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return
        clipboard_text = ""
        for rng in selected_ranges:
            for row in range(rng.topRow(), rng.bottomRow() + 1):
                row_text = []
                for col in range(rng.leftColumn(), rng.rightColumn() + 1):
                    item = self.table.item(row, col)
                    row_text.append(item.text() if item else "")
                clipboard_text += "\t".join(row_text) + "\n"
            clipboard_text += "\n"
        QApplication.clipboard().setText(clipboard_text.strip())

    def haciz_odeme_yap(self):
        from .haciz_odeme_dialog import HacizOdemeDialog
        yil = int(self.yil_cb.currentText())
        ay = self.ay_cb.currentIndex() + 1
        dialog = HacizOdemeDialog(
            self.session, yil, ay,
            self.asgari_ucret_normal,
            self.asgari_ucret_emekli,
            parent=self
        )
        if dialog.exec_():
            self.load_data()

    # ---------- MAAŞ ÖDEMESİ YAP ----------
    def maas_odeme_yap(self):
        from PyQt5.QtWidgets import QStackedWidget
        from ui.maas_odeme_dialog import MaasOdemeDialog
        yil = int(self.yil_cb.currentText())
        ay = self.ay_cb.currentIndex() + 1

        def load_bordrolar_fn(yil, ay):
            bordrolar = self.session.query(Bordro).filter(
                Bordro.yil == yil, Bordro.ay == ay
            ).all()
            return [b for b in bordrolar if b.personel is not None]

        gecerli_bordrolar = load_bordrolar_fn(yil, ay)

        if not gecerli_bordrolar:
            ModernMesaj.uyari(self, "Bu dönem için bordro hesaplanmış geçerli personel bulunamadı.")
            return

        dialog = MaasOdemeDialog(
            session=self.session,
            yil=yil,
            ay=ay,
            gecerli_bordrolar=gecerli_bordrolar,
            elden_sistem=self.elden_toggle.isChecked(),
            format_tl_fn=self.format_tl,
            parent=self,
            load_bordrolar_fn=load_bordrolar_fn
        )
        if dialog.exec_():
            self.load_data()