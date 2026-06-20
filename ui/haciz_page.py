# ui/haciz_page.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QFrame,
    QHeaderView, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDateEdit, QComboBox, QTextEdit, QDoubleSpinBox,
    QCompleter, QInputDialog, QScrollArea
)
from PyQt5.QtCore import Qt, QDate, QStringListModel
from PyQt5.QtGui import QColor
from sqlalchemy import func
from database import get_session
from models import Personel, Haciz, HacizOdeme, Bordro, SistemAyarlari
from ui.utils import ModernMesaj, TarihAlani, ModernTarihSecici, tr_lower, get_config_path
import datetime
import os
import json


class CustomLineEdit(QLineEdit):
    """Focus olduğunda tüm metni seçen QLineEdit"""
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()


class HacizPage(QWidget):
    def __init__(self):
        super().__init__()
        self.session = get_session()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        self.setStyleSheet("""
            background-color: #f8f9fa;
            QLabel { color: white; background: transparent; }
        """)

        # Üst Panel
        top_panel = QFrame()
        top_panel.setStyleSheet("""
            background: #34495e; border-radius: 12px; border: 1px solid #4a6278;
            QLabel { color: white; background: transparent; }
        """)
        top_panel.setFixedHeight(145)  # 3 satır için yükseklik

        self.personel_search = QLineEdit()
        self.personel_search.setPlaceholderText("🔍 Personel ara (isim veya sicil)...")
        self.personel_search.setFixedHeight(35)
        self.personel_search.setStyleSheet("""
            border: 1px solid #ced4da;
            border-radius: 6px;
            padding-left: 10px;
            background-color: #2c3e50;
            color: white;
            font-size: 13px;
        """)
        self.personel_search.textChanged.connect(self.load_data)

        self.durum_filter = QComboBox()
        self.durum_filter.addItems(["Tümü", "Aktif", "Pasif", "Tamamlandı"])
        self.durum_filter.setFixedWidth(150)
        self.durum_filter.setStyleSheet("""
            background-color: #2c3e50;
            color: white;
            border: 1px solid #4a6278;
            border-radius: 6px;
            padding: 5px;
            font-size: 13px;
        """)
        self.durum_filter.currentTextChanged.connect(self.load_data)

        self.ekle_btn = self.create_btn("➕ Yeni Haciz", "#27ae60", self.yeni_haciz)
        self.duzenle_btn = self.create_btn("✏️ Düzenle", "#2980b9", self.duzenle_haciz)
        self.sil_btn = self.create_btn("🗑️ Sil", "#e74c3c", self.sil_haciz)
        self.odeme_listesi_btn = self.create_btn("📋 Tüm Ödemeler", "#9b59b6", self.tum_odemeleri_goster)
        self.haciz_odeme_btn = self.create_btn("⚖️ Haciz Ödemesi Yap", "#8e44ad", self.haciz_odeme_yap)
        self.excel_btn = self.create_btn("📥 Excel'e Aktar", "#27ae60", self.excel_aktar)

        # LAYOUT DÜZENİ
        top_lay = QVBoxLayout(top_panel)
        top_lay.setContentsMargins(15, 10, 15, 10)
        top_lay.setSpacing(8)

        # 1. satır - arama
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        lbl_personel = QLabel("Personel:")
        lbl_personel.setStyleSheet("color: white; background: transparent;")
        row1.addWidget(lbl_personel)
        row1.addWidget(self.personel_search, 1)
        lbl_durum = QLabel("Durum:")
        lbl_durum.setStyleSheet("color: white; background: transparent;")
        row1.addWidget(lbl_durum)
        row1.addWidget(self.durum_filter)
        row1.addStretch()
        top_lay.addLayout(row1)

        # 2. satır - temel butonlar
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        row2.addWidget(self.ekle_btn)
        row2.addWidget(self.duzenle_btn)
        row2.addWidget(self.sil_btn)
        row2.addWidget(self.odeme_listesi_btn)
        row2.addStretch()
        top_lay.addLayout(row2)

        # 3. satır - ödeme ve excel
        row3 = QHBoxLayout()
        row3.setSpacing(10)
        row3.addWidget(self.haciz_odeme_btn)
        row3.addWidget(self.excel_btn)
        row3.addStretch()
        top_lay.addLayout(row3)

        layout.addWidget(top_panel)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(15)
        self.table.setHorizontalHeaderLabels([
            "ID", "Personel", "Dosya No", "Borç Miktarı", "Kalan Borç",
            "Planlanan Kesinti", "Aylık Kesinti (Sabit)", "Kesinti Oranı %",
            "Başlangıç", "Bitiş", "Durum", "Alacaklı Kurum", "IBAN",
            "Gecikme Faizi", "Havuzda Bekleyen"
        ])
        self.table.setColumnHidden(0, True)
        # Sütun genişliği ayarlanabilir + kaydedilebilir
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().sectionMoved.connect(self._auto_save_layout)
        self.table.horizontalHeader().sectionResized.connect(self._auto_save_layout)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #dcdde1;
                gridline-color: #ecf0f1;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
                color: #1a1a1a;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            /* Scrollbar: son ekran görüntüsüne göre (kalınlık/oklar değişmeden sadece renk) */
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #7f8c8d; /* zemin */
                border: 1px solid rgba(255,255,255,0.35);
            }
            QScrollBar::add-page, QScrollBar::sub-page {
                background: #7f8c8d;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #2b3744; /* tutma kolu */
                border: 1px solid rgba(255,255,255,0.35);
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background: #1e2b35;
            }
            QScrollBar::add-line:vertical {
                background: #ffffff;
                height: 16px;
                subcontrol-position: bottom;
                subcontrol-origin: scroll;
                border-top: 2px solid #7f8c8d;
            }
            QScrollBar::sub-line:vertical {
                background: #ffffff;
                height: 16px;
                subcontrol-position: top;
                subcontrol-origin: scroll;
                border-bottom: 2px solid #7f8c8d;
            }
            QScrollBar::add-line:horizontal {
                background: #ffffff;
                width: 16px;
                subcontrol-position: right;
                subcontrol-origin: scroll;
                border-left: 2px solid #7f8c8d;
            }
            QScrollBar::sub-line:horizontal {
                background: #ffffff;
                width: 16px;
                subcontrol-position: left;
                subcontrol-origin: scroll;
                border-right: 2px solid #7f8c8d;
            }
            QScrollBar::up-arrow:vertical {
                width: 0; height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 9px solid #2c3e50;
            }
            QScrollBar::down-arrow:vertical {
                width: 0; height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 9px solid #2c3e50;
            }
            QScrollBar::left-arrow:horizontal {
                width: 0; height: 0;
                border-top: 5px solid transparent;
                border-bottom: 5px solid transparent;
                border-right: 9px solid #2c3e50;
            }
            QScrollBar::right-arrow:horizontal {
                width: 0; height: 0;
                border-top: 5px solid transparent;
                border-bottom: 5px solid transparent;
                border-left: 9px solid #2c3e50;
            }
        """)
        self.table.itemDoubleClicked.connect(self.haciz_detay_goster)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_column_context_menu)
        layout.addWidget(self.table)

        self.load_column_widths()

    def _widths_path(self):
        return get_config_path("haciz_table_widths.json")

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
        ModernMesaj.basari(self, "Haciz tablosu düzeni kaydedildi.")

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
        btn.setFixedSize(120, 35)
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

    def load_data(self):
        self.table.setRowCount(0)
        query = self.session.query(Haciz).join(Personel)

        arama = tr_lower(self.personel_search.text().strip())
        
        durum = self.durum_filter.currentText()
        if durum != "Tümü":
            query = query.filter(Haciz.durum == durum)

        hacizler = query.all()
    
        if arama:
            hacizler = [h for h in hacizler if 
                        arama in tr_lower(h.personel.ad_soyad) or 
                        (h.personel.sicil_no and arama in tr_lower(h.personel.sicil_no))]

        # ── Tüm personeller için havuz dağılımını önce hesapla ──
        # Her personelin ödenmeyen bordro havuzunu, hacizlerine sırayla dağıt
        havuz_dagilimi = {}  # {haciz_id: havuzda_bekleyen_tutar}
        try:
            tum_personel_ids = set(h.personel_id for h in hacizler)
            if tum_personel_ids:
                # Toplu sorgu: tüm bordrolar
                tum_bordrolar = self.session.query(Bordro).filter(
                    Bordro.personel_id.in_(tum_personel_ids),
                    Bordro.icra_kesintisi > 0
                ).order_by(Bordro.personel_id, Bordro.yil, Bordro.ay).all()

                # Personel_id -> bordro listesi
                pid_bordro = {}
                for b in tum_bordrolar:
                    pid_bordro.setdefault(b.personel_id, []).append(b)

                # Toplu sorgu: ödenmiş bordrolar
                tum_bordro_ids = [b.id for b in tum_bordrolar]
                odenen_ids = set()
                if tum_bordro_ids:
                    odenenler = self.session.query(HacizOdeme.bordro_id).filter(
                        HacizOdeme.bordro_id.in_(tum_bordro_ids)
                    ).all()
                    odenen_ids = {r[0] for r in odenenler}

                # Toplu sorgu: tüm hacizler
                tum_hacizler = self.session.query(Haciz).filter(
                    Haciz.personel_id.in_(tum_personel_ids),
                    Haciz.durum.in_(["Aktif", "Tamamlandı"])
                ).order_by(Haciz.personel_id, Haciz.baslangic_tarihi).all()

                # Personel_id -> haciz listesi
                pid_haciz = {}
                for hc in tum_hacizler:
                    pid_haciz.setdefault(hc.personel_id, []).append(hc)

                # Havuz dağıtımını hesapla
                for pid in tum_personel_ids:
                    bordrolar = pid_bordro.get(pid, [])
                    havuz_toplam = sum(b.icra_kesintisi for b in bordrolar if b.id not in odenen_ids)

                    hacizler_sirali = pid_haciz.get(pid, [])
                    kalan_havuz = havuz_toplam
                    for haciz in hacizler_sirali:
                        if kalan_havuz <= 0:
                            havuz_dagilimi[haciz.id] = 0.0
                        else:
                            bu_hacize = min(haciz.kalan_borc or 0, kalan_havuz)
                            havuz_dagilimi[haciz.id] = bu_hacize
                            kalan_havuz -= bu_hacize
        except Exception:
            havuz_dagilimi = {}

        # Asgari ücretleri bir kez yükle
        asgari_normal = 28075.50
        asgari_emekli = 30181.00
        try:
            ayar_n = self.session.query(SistemAyarlari).filter_by(anahtar='asgari_ucret_normal').first()
            ayar_e = self.session.query(SistemAyarlari).filter_by(anahtar='asgari_ucret_emekli').first()
            if ayar_n: asgari_normal = float(ayar_n.deger)
            if ayar_e: asgari_emekli = float(ayar_e.deger)
        except Exception:
            pass

        for h in hacizler:
            row = self.table.rowCount()
            self.table.insertRow(row)

            row_color = QColor(255, 255, 255)

            emekli_mi = "emekli" in (h.personel.aciklama or "").lower()
            baz = asgari_emekli if emekli_mi else asgari_normal
            if h.aylik_kesinti and h.aylik_kesinti > 0:
                planlanan = h.aylik_kesinti
                planlanan_str = f"{planlanan:,.2f} ₺".replace(",", ".")
            else:
                planlanan = baz * 0.25
                planlanan_str = f"{planlanan:,.2f} ₺ (%25)".replace(",", ".")

            # Havuzu önceden hesaplanan dağılımdan al
            havuzda = havuz_dagilimi.get(h.id, 0.0)

            items = [
                QTableWidgetItem(str(h.id)),
                QTableWidgetItem(f"{h.personel.ad_soyad} ({h.personel.sicil_no})"),
                QTableWidgetItem(h.dosya_no),
                QTableWidgetItem(f"{h.borc_miktari:,.2f} ₺".replace(",", ".")),
                QTableWidgetItem(f"{h.kalan_borc:,.2f} ₺".replace(",", ".") if h.kalan_borc else "0,00 ₺"),
                QTableWidgetItem(planlanan_str),
                QTableWidgetItem(f"{h.aylik_kesinti:,.2f} ₺".replace(",", ".") if h.aylik_kesinti and h.aylik_kesinti > 0 else "-"),
                QTableWidgetItem(f"%{h.kesinti_orani:.1f}" if h.kesinti_orani > 0 else "-"),
                QTableWidgetItem(h.baslangic_tarihi.strftime("%d.%m.%Y")),
                QTableWidgetItem(h.bitis_tarihi.strftime("%d.%m.%Y") if h.bitis_tarihi else "-"),
                QTableWidgetItem(h.durum),
                QTableWidgetItem(h.alacakli_kurum or "-"),
                QTableWidgetItem(h.iban or "-"),
                QTableWidgetItem(f"{h.gecikme_faizi:,.2f} ₺".replace(",", ".") if h.gecikme_faizi else "0,00 ₺"),
                QTableWidgetItem(f"{havuzda:,.2f} ₺".replace(",", ".") if havuzda > 0 else "-"),
            ]

            for col, item in enumerate(items):
                item.setBackground(row_color)
                if col == 1:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                elif col == 14:  # Havuzda Bekleyen - turuncu
                    item.setTextAlignment(Qt.AlignCenter)
                    if havuzda > 0:
                        item.setForeground(QColor("#e67e22"))
                        item.setFont(__import__('PyQt5.QtGui', fromlist=['QFont']).QFont())
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

    def yeni_haciz(self):
        dialog = HacizDialog(self.session, parent=self)
        if dialog.exec_():
            self.load_data()
            ModernMesaj.basari(self, "Haciz kaydı eklendi.")

    def duzenle_haciz(self):
        row = self.table.currentRow()
        if row < 0:
            ModernMesaj.uyari(self, "Lütfen bir haciz kaydı seçin.")
            return
        haciz_id = int(self.table.item(row, 0).text())
        haciz = self.session.get(Haciz, haciz_id)
        dialog = HacizDialog(self.session, haciz=haciz, parent=self)
        if dialog.exec_():
            self.load_data()
            ModernMesaj.basari(self, "Haciz kaydı güncellendi.")

    def sil_haciz(self):
        row = self.table.currentRow()
        if row < 0:
            ModernMesaj.uyari(self, "Lütfen bir haciz kaydı seçin.")
            return
        haciz_id = int(self.table.item(row, 0).text())
        haciz = self.session.get(Haciz, haciz_id)
        if ModernMesaj.soru(self, f"{haciz.dosya_no} dosya no'lu haciz silinsin mi?"):
            self.session.delete(haciz)
            self.session.commit()
            self.load_data()

    def haciz_detay_goster(self, item):
        row = self.table.currentRow()
        if row < 0:
            return
        haciz_id = int(self.table.item(row, 0).text())
        from .haciz_detay_dialog import HacizDetayDialog
        dialog = HacizDetayDialog(self.session, haciz_id, parent=self)
        if dialog.exec_():
            self.load_data()

    def haciz_odeme_yap(self):
        from .haciz_odeme_dialog import HacizOdemeDialog
        # Asgari ücretleri yükle
        asgari_normal = 28075.50
        asgari_emekli = 30181.00
        try:
            ayar_n = self.session.query(SistemAyarlari).filter_by(anahtar='asgari_ucret_normal').first()
            ayar_e = self.session.query(SistemAyarlari).filter_by(anahtar='asgari_ucret_emekli').first()
            if ayar_n: asgari_normal = float(ayar_n.deger)
            if ayar_e: asgari_emekli = float(ayar_e.deger)
        except Exception:
            pass

        # Yıl/ay seçimi için basit dialog
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton
        secim = QDialog(self)
        secim.setWindowTitle("Dönem Seçin")
        secim.setFixedSize(300, 130)
        secim.setStyleSheet("background: #2c3e50; color: white;")
        vl = QVBoxLayout(secim)
        vl.setSpacing(12)
        hl = QHBoxLayout()
        lbl = QLabel("Yıl:")
        lbl.setStyleSheet("color:white; background:transparent;")
        yil_cb = QComboBox()
        bugun = datetime.date.today()
        for y in range(bugun.year - 2, bugun.year + 2):
            yil_cb.addItem(str(y))
        yil_cb.setCurrentText(str(bugun.year))
        ay_cb = QComboBox()
        for i, m in enumerate(["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                                "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]):
            ay_cb.addItem(m)
        ay_cb.setCurrentIndex(bugun.month - 1)
        for w in [yil_cb, ay_cb]:
            w.setStyleSheet("background:#34495e; color:white; border:1px solid #4a6278; border-radius:4px; padding:4px;")
        hl.addWidget(lbl)
        hl.addWidget(yil_cb)
        hl.addWidget(QLabel("Ay:"))
        hl.addWidget(ay_cb)
        vl.addLayout(hl)
        tamam = QPushButton("Devam")
        tamam.setStyleSheet("background:#3498db; color:white; border-radius:6px; font-weight:bold; padding:6px;")
        tamam.clicked.connect(secim.accept)
        vl.addWidget(tamam)
        if secim.exec_() != QDialog.Accepted:
            return

        yil = int(yil_cb.currentText())
        ay = ay_cb.currentIndex() + 1
        dialog = HacizOdemeDialog(self.session, yil, ay, asgari_normal, asgari_emekli, parent=self)
        if dialog.exec_():
            self.load_data()

    def excel_aktar(self):
        import pandas as pd
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Excel Kaydet", "haciz_listesi.xlsx",
                                               "Excel (*.xlsx)")
        if not path:
            return
        try:
            hacizler = self.session.query(Haciz).join(Personel).all()
            rows = []
            for h in hacizler:
                rows.append({
                    "Personel": f"{h.personel.ad_soyad} ({h.personel.sicil_no})",
                    "Dosya No": h.dosya_no,
                    "Borç Miktarı": h.borc_miktari,
                    "Kalan Borç": h.kalan_borc or 0,
                    "Aylık Kesinti": h.aylik_kesinti or 0,
                    "Başlangıç": h.baslangic_tarihi.strftime("%d.%m.%Y"),
                    "Bitiş": h.bitis_tarihi.strftime("%d.%m.%Y") if h.bitis_tarihi else "-",
                    "Durum": h.durum,
                    "Alacaklı Kurum": h.alacakli_kurum or "-",
                    "IBAN": h.iban or "-",
                    "Gecikme Faizi": h.gecikme_faizi or 0,
                })
            df = pd.DataFrame(rows)
            df.to_excel(path, index=False)
            ModernMesaj.basari(self, f"Excel dosyası kaydedildi:\n{path}")
        except Exception as e:
            ModernMesaj.hata(self, f"Excel aktarım hatası:\n{str(e)}")

    def tum_odemeleri_goster(self):
        from .odeme_listesi_dialog import OdemeListesiDialog
        dialog = OdemeListesiDialog(self.session, parent=self)
        dialog.exec_()


class HacizDialog(QDialog):
    def __init__(self, session, haciz=None, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.haciz = haciz
        self.selected_personel_id = None
        self.setWindowTitle("Haciz / İcra Kaydı" if not haciz else "Haciz Düzenle")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(580, 680)
        self.init_ui()
        if haciz:
            self.load_haciz()
        from ui.utils import make_frameless
        make_frameless(self)

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("QFrame#outer{background:#2c3e50;border-radius:16px;border:1px solid #4a6278;}")
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(70)
        hdr.setStyleSheet("QFrame { background-color: #7b241c; border-top-left-radius:16px; border-top-right-radius:16px; }")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(20, 0, 20, 0); hdr_lay.setSpacing(12)
        ic = QLabel("⚖️")
        ic.setFixedSize(44, 44)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background-color: #e74c3c; border-radius: 22px; font-size: 20px;")
        tl = QLabel("Haciz / İcra Kaydı" if not self.haciz else "Haciz Düzenle")
        tl.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        hdr_lay.addWidget(ic)
        hdr_lay.addWidget(tl)
        hdr_lay.addStretch()
        outer_lay.addWidget(hdr)

        # Scroll alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: #2c3e50; border: none; }
            QScrollArea > QWidget > QWidget { background: #2c3e50; }
            QScrollBar:vertical { background: rgba(255,255,255,0.05); width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        form_w = QWidget()
        form_w.setStyleSheet("background: #2c3e50;")
        form_lay = QVBoxLayout(form_w)
        form_lay.setContentsMargins(20, 14, 20, 10)
        form_lay.setSpacing(10)

        # Tüm giriş alanları için ortak stil (belirgin border)
        input_style = """
            QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox {
                background-color: #2c3e50;
                border: 1px solid #3498db;
                border-radius: 8px;
                color: #ffffff;
                font-size: 13px;
                padding: 9px 13px;
                min-height: 22px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDoubleSpinBox:focus {
                border-color: #e74c3c;
                background-color: #1a2a38;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2c3e50;
                color: #ffffff;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0px;
            }
        """

        # TarihAlani için ayrı stil
        tarih_stili = """
            QFrame {
                background-color: #ecf0f1;
                border: 3px solid #3498db;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #ecf0f1;
                border: none;
                color: #2c3e50;
                font-size: 13px;
                padding: 9px 13px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 6px;
                font-size: 12px;
                padding: 5px 10px;
            }
        """

        def _mk_lbl(text):
            l = QLabel(text)
            l.setStyleSheet("color: #85c1e9; font-size: 10px; font-weight: bold; letter-spacing: 0.8px; background: transparent;")
            return l

        def field(lbl, widget):
            l = _mk_lbl(lbl)
            vb = QVBoxLayout()
            vb.setSpacing(4)
            vb.addWidget(l)
            vb.addWidget(widget)
            return vb

        # Personel
        self.personel_edit = QLineEdit()
        self.personel_edit.setPlaceholderText("Personel adı yazın...")
        self.personel_edit.setStyleSheet(input_style)
        personeller = self.session.query(Personel).filter(Personel.durum == "Aktif").all()
        self.personel_list = [(f"{p.ad_soyad} ({p.sicil_no})", p.id) for p in personeller]
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setModel(QStringListModel([i[0] for i in self.personel_list]))
        self.personel_edit.setCompleter(self.completer)
        self.completer.activated.connect(self.on_personel_selected)
        form_lay.addLayout(field("PERSONEL", self.personel_edit))

        # Dosya No
        self.dosya_no = QLineEdit()
        self.dosya_no.setPlaceholderText("İcra dosya numarası...")
        self.dosya_no.setStyleSheet(input_style)
        form_lay.addLayout(field("DOSYA NO", self.dosya_no))

        # Borç ve Kalan
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.borc_miktari = CustomLineEdit()
        self.borc_miktari.setPlaceholderText("Örn: 15000,50")
        self.borc_miktari.setStyleSheet(input_style)
        self.borc_miktari.textChanged.connect(self.borc_degisti)
        b_vb = QVBoxLayout()
        b_vb.setSpacing(4)
        b_vb.addWidget(_mk_lbl("BORÇ MİKTARI"))
        b_vb.addWidget(self.borc_miktari)
        self.kalan_borc = CustomLineEdit()
        self.kalan_borc.setPlaceholderText("Otomatik hesaplanır")
        self.kalan_borc.setStyleSheet(input_style)
        k_vb = QVBoxLayout()
        k_vb.setSpacing(4)
        k_vb.addWidget(_mk_lbl("KALAN BORÇ"))
        k_vb.addWidget(self.kalan_borc)
        row1.addLayout(b_vb)
        row1.addLayout(k_vb)
        form_lay.addLayout(row1)

        # Gecikme Faizi
        faiz_row = QHBoxLayout()
        faiz_row.setSpacing(6)
        self.gecikme_faizi_label = QLabel("0,00 ₺")
        self.gecikme_faizi_label.setStyleSheet("background-color: #34495e; border: 1px solid #4a6278; border-radius: 8px; padding: 8px 12px; color: #f39c12; font-size: 13px; font-weight: bold;")
        self.faiz_ekle_btn = QPushButton("➕ Ekle")
        self.faiz_ekle_btn.setFixedSize(80, 36)
        self.faiz_ekle_btn.setStyleSheet("QPushButton { background:#f39c12; color:white; border-radius:6px; border:none; font-weight:bold; } QPushButton:hover { background:#e67e22; }")
        self.faiz_ekle_btn.clicked.connect(self.faiz_ekle)
        self.faiz_sil_btn = QPushButton("➖ Sil")
        self.faiz_sil_btn.setFixedSize(80, 36)
        self.faiz_sil_btn.setStyleSheet("QPushButton { background:#e74c3c; color:white; border-radius:6px; border:none; font-weight:bold; } QPushButton:hover { background:#c0392b; }")
        self.faiz_sil_btn.clicked.connect(self.faiz_sil)
        faiz_row.addWidget(self.gecikme_faizi_label, 1)
        faiz_row.addWidget(self.faiz_ekle_btn)
        faiz_row.addWidget(self.faiz_sil_btn)
        faiz_vb = QVBoxLayout()
        faiz_vb.setSpacing(4)
        faiz_vb.addWidget(_mk_lbl("GECİKME FAİZİ"))
        faiz_vb.addLayout(faiz_row)
        form_lay.addLayout(faiz_vb)

        # Aylık Kesinti ve Oran
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.aylik_kesinti = CustomLineEdit()
        self.aylik_kesinti.setPlaceholderText("Sabit tutar (opsiyonel)")
        self.aylik_kesinti.setStyleSheet(input_style)
        ak_vb = QVBoxLayout()
        ak_vb.setSpacing(4)
        ak_vb.addWidget(_mk_lbl("AYLIK KESİNTİ (SABİT)"))
        ak_vb.addWidget(self.aylik_kesinti)
        self.kesinti_orani = QDoubleSpinBox()
        self.kesinti_orani.setRange(0, 100)
        self.kesinti_orani.setSuffix(" %")
        self.kesinti_orani.setSpecialValueText("Yüzde yok")
        self.kesinti_orani.setStyleSheet(input_style)
        ko_vb = QVBoxLayout()
        ko_vb.setSpacing(4)
        ko_vb.addWidget(_mk_lbl("KESİNTİ ORANI"))
        ko_vb.addWidget(self.kesinti_orani)
        row2.addLayout(ak_vb)
        row2.addLayout(ko_vb)
        form_lay.addLayout(row2)

        # Tarihler
        row3 = QHBoxLayout()
        row3.setSpacing(10)
        self.baslangic = TarihAlani()
        self.baslangic.set_date(QDate.currentDate())
        self.baslangic.line.setStyleSheet(input_style)   # <--- EKLE
        bas_vb = QVBoxLayout()
        bas_vb.setSpacing(4)
        bas_vb.addWidget(_mk_lbl("BAŞLANGIÇ TARİHİ"))
        bas_vb.addWidget(self.baslangic)
        self.bitis = TarihAlani(placeholder="Süresiz (boş bırakın)")
        self.bitis.set_date(QDate(2099, 12, 31))
        self.bitis.line.setStyleSheet(input_style)       # <--- EKLE
        bit_vb = QVBoxLayout()
        bit_vb.setSpacing(4)
        bit_vb.addWidget(_mk_lbl("BİTİŞ TARİHİ"))
        bit_vb.addWidget(self.bitis)
        row3.addLayout(bas_vb)
        row3.addLayout(bit_vb)
        form_lay.addLayout(row3)

        # Durum
        self.durum_cb = QComboBox()
        self.durum_cb.addItems(["Aktif", "Pasif", "Tamamlandı"])
        self.durum_cb.setStyleSheet(input_style)
        form_lay.addLayout(field("DURUM", self.durum_cb))

        # Alacaklı Kurum
        self.alacakli = QLineEdit()
        self.alacakli.setPlaceholderText("İcra dairesi veya alacaklı...")
        self.alacakli.setStyleSheet(input_style)
        form_lay.addLayout(field("ALACAKLI KURUM", self.alacakli))

        # IBAN
        self.iban = QLineEdit()
        self.iban.setPlaceholderText("TR... (opsiyonel)")
        self.iban.setMaxLength(34)
        self.iban.setStyleSheet(input_style)
        form_lay.addLayout(field("IBAN", self.iban))

        # Açıklama
        self.aciklama = QTextEdit()
        self.aciklama.setFixedHeight(70)
        self.aciklama.setPlaceholderText("Açıklama...")
        self.aciklama.setStyleSheet(input_style)
        form_lay.addLayout(field("AÇIKLAMA", self.aciklama))

        scroll.setWidget(form_w)
        scroll.setStyleSheet("background: #2c3e50; border: none;")
        scroll.viewport().setStyleSheet("background: #2c3e50;")
        scroll.viewport().setAutoFillBackground(True)
        from PyQt5.QtCore import Qt as _Qt
        scroll.setAttribute(_Qt.WA_StyledBackground, True)
        form_w.setAutoFillBackground(True)
        outer_lay.addWidget(scroll)

        # Butonlar
        btn_frame = QFrame()
        btn_frame.setFixedHeight(60)
        btn_frame.setStyleSheet("QFrame { background-color: #243342; border-bottom-left-radius:16px; border-bottom-right-radius:16px; border-top: 1px solid #1a2a38; }")
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setContentsMargins(20, 10, 20, 10)
        btn_lay.setSpacing(10)
        btn_lay.addStretch()

        self.kaydet_btn = QPushButton("  Kaydet")
        self.kaydet_btn.setFixedHeight(40)
        self.kaydet_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color:white; font-weight:bold; border-radius:8px; border:none; padding:0 24px; } QPushButton:hover { background-color:#c0392b; }")
        self.kaydet_btn.clicked.connect(self.kaydet)

        self.iptal_btn = QPushButton("İptal")
        self.iptal_btn.setFixedHeight(40)
        self.iptal_btn.setStyleSheet("QPushButton { background:transparent; color:#7f8c8d; border:1px solid #4a6278; border-radius:8px; padding:0 16px; } QPushButton:hover { background:#34495e; color:white; }")
        self.iptal_btn.clicked.connect(self.reject)

        btn_lay.addWidget(self.kaydet_btn)
        btn_lay.addWidget(self.iptal_btn)
        outer_lay.addWidget(btn_frame)

    def borc_degisti(self, text):
        """Yeni kayıt sırasında borç miktarı girildikçe kalan borcu otomatik doldur."""
        if not self.haciz:  # Yeni kayıt
            self.kalan_borc.setText(text)

    def _faiz_dialog(self, baslik, aciklama):
        """Modern faiz giriş dialogu. Tutar döner veya None."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
        dialog = QDialog(self, Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setWindowTitle(baslik)
        dialog.setFixedWidth(360)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                border: 1px solid #e67e22;
                border-radius: 12px;
            }
            QLabel { background: transparent; }
        """)
        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Üst şerit
        top = QFrame()
        top.setFixedHeight(68)
        top.setStyleSheet("QFrame { background-color: #7d5109; border-top-left-radius: 12px; border-top-right-radius: 12px; }")
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(20, 0, 20, 0)
        ikon = QLabel("₺")
        ikon.setFixedSize(40, 40)
        ikon.setAlignment(Qt.AlignCenter)
        ikon.setStyleSheet("background-color: #e67e22; color: white; font-size: 18px; font-weight: bold; border-radius: 20px;")
        baslik_lbl = QLabel(baslik)
        baslik_lbl.setStyleSheet("color: white; font-size: 14px; font-weight: bold; padding-left: 12px;")
        top_lay.addWidget(ikon)
        top_lay.addWidget(baslik_lbl)
        top_lay.addStretch()
        lay.addWidget(top)

        # Form
        form_frame = QFrame()
        form_frame.setStyleSheet("QFrame { background-color: #2c3e50; }")
        form_lay = QVBoxLayout(form_frame)
        form_lay.setContentsMargins(24, 18, 24, 14)
        form_lay.setSpacing(8)

        acik_lbl = QLabel(aciklama)
        acik_lbl.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        form_lay.addWidget(acik_lbl)

        inp = QLineEdit("0")
        inp.setPlaceholderText("Tutar girin...")
        inp.setStyleSheet("""
            QLineEdit {
                background-color: #34495e;
                border: 1px solid #4a6278;
                border-radius: 8px;
                color: white;
                font-size: 15px;
                font-weight: bold;
                padding: 10px 14px;
            }
            QLineEdit:focus { border-color: #e67e22; }
        """)
        inp.selectAll()
        form_lay.addWidget(inp)
        lay.addWidget(form_frame)

        # Butonlar
        btn_frame = QFrame()
        btn_frame.setFixedHeight(58)
        btn_frame.setStyleSheet("QFrame { background-color: #243342; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; border-top: 1px solid #1a2a38; }")
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setContentsMargins(16, 10, 16, 10)
        btn_lay.setSpacing(8)
        btn_lay.addStretch()

        tamam = QPushButton("Uygula")
        tamam.setFixedSize(100, 36)
        tamam.setStyleSheet("QPushButton { background-color: #e67e22; color: white; font-weight: bold; border-radius: 8px; border: none; } QPushButton:hover { background-color: #d35400; }")
        iptal = QPushButton("İptal")
        iptal.setFixedSize(90, 36)
        iptal.setStyleSheet("QPushButton { background-color: transparent; color: #7f8c8d; border: 1px solid #4a6278; border-radius: 8px; font-weight: bold; } QPushButton:hover { background-color: #34495e; color: white; }")
        tamam.clicked.connect(dialog.accept)
        iptal.clicked.connect(dialog.reject)
        btn_lay.addWidget(tamam)
        btn_lay.addWidget(iptal)
        lay.addWidget(btn_frame)

        dialog.setResult(0)
        if dialog.exec_() == QDialog.Accepted:
            try:
                val = float(inp.text().replace(",", ".").replace("₺", "").strip() or 0)
                return val if val > 0 else None
            except ValueError:
                return None
        return None

    def faiz_ekle(self):
        tutar = self._faiz_dialog("Gecikme Faizi Ekle", "Eklenecek faiz tutarını girin (₺):")
        if tutar is None:
            return

        # Label'dan değil doğrudan alan değerlerinden oku
        borc  = self.parse_tl(self.borc_miktari.text())
        kalan = self.parse_tl(self.kalan_borc.text())
        faiz  = float(self.haciz.gecikme_faizi or 0) if self.haciz else self.parse_tl(
            self.gecikme_faizi_label.text().replace("₺", "").strip())

        yeni_borc  = borc  + tutar
        yeni_kalan = kalan + tutar
        yeni_faiz  = faiz  + tutar

        self.borc_miktari.setText(f"{yeni_borc:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))
        self.kalan_borc.setText(f"{yeni_kalan:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))
        self.gecikme_faizi_label.setText(f"{yeni_faiz:,.2f} ₺".replace(",", "@").replace(".", ",").replace("@", "."))
        # Modeli de güncelle ki sonraki eklemede doğru okusun
        if self.haciz:
            self.haciz.gecikme_faizi = yeni_faiz

    def faiz_sil(self):
        tutar = self._faiz_dialog("Gecikme Faizi Sil", "Silinecek faiz tutarını girin (₺):")
        if tutar is None:
            return

        borc  = self.parse_tl(self.borc_miktari.text())
        kalan = self.parse_tl(self.kalan_borc.text())
        faiz  = float(self.haciz.gecikme_faizi or 0) if self.haciz else self.parse_tl(
            self.gecikme_faizi_label.text().replace("₺", "").strip())

        if tutar > faiz:
            ModernMesaj.uyari(self, "Silinecek tutar mevcut faizden büyük olamaz.")
            return

        yeni_borc  = borc  - tutar
        yeni_kalan = kalan - tutar
        yeni_faiz  = faiz  - tutar

        self.borc_miktari.setText(f"{yeni_borc:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))
        self.kalan_borc.setText(f"{yeni_kalan:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))
        self.gecikme_faizi_label.setText(f"{yeni_faiz:,.2f} ₺".replace(",", "@").replace(".", ",").replace("@", "."))
        if self.haciz:
            self.haciz.gecikme_faizi = yeni_faiz

    def on_personel_selected(self, text):
        for display, pid in self.personel_list:
            if display == text:
                self.selected_personel_id = pid
                break

    def load_haciz(self):
        p = self.haciz.personel
        display = f"{p.ad_soyad} ({p.sicil_no})"
        self.personel_edit.setText(display)
        self.selected_personel_id = p.id
        self.dosya_no.setText(self.haciz.dosya_no)
        self.borc_miktari.setText(f"{self.haciz.borc_miktari:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))
        self.kalan_borc.setText(f"{self.haciz.kalan_borc:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))
        self.gecikme_faizi_label.setText(f"{self.haciz.gecikme_faizi:,.2f} ₺".replace(",", "@").replace(".", ",").replace("@", "."))
        self.aylik_kesinti.setText(f"{self.haciz.aylik_kesinti:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".") if self.haciz.aylik_kesinti else "0")
        self.kesinti_orani.setValue(self.haciz.kesinti_orani)
        self.baslangic.set_pydate(self.haciz.baslangic_tarihi)
        if self.haciz.bitis_tarihi:
            self.bitis.set_pydate(self.haciz.bitis_tarihi)
        self.durum_cb.setCurrentText(self.haciz.durum)
        self.alacakli.setText(self.haciz.alacakli_kurum or "")
        self.iban.setText(self.haciz.iban or "")
        self.aciklama.setPlainText(self.haciz.aciklama or "")

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

    def kaydet(self):
        if self.selected_personel_id is None:
            ModernMesaj.uyari(self, "Lütfen geçerli bir personel seçin.")
            return

        try:
            if self.haciz:
                h = self.haciz
            else:
                h = Haciz()
                self.session.add(h)

            h.personel_id = self.selected_personel_id
            h.dosya_no = self.dosya_no.text()
            h.borc_miktari = self.parse_tl(self.borc_miktari.text())
            h.kalan_borc = self.parse_tl(self.kalan_borc.text())
            h.gecikme_faizi = self.parse_tl(self.gecikme_faizi_label.text().replace("₺", "").strip())
            h.aylik_kesinti = self.parse_tl(self.aylik_kesinti.text())
            h.kesinti_orani = self.kesinti_orani.value()
            bas_py = self.baslangic.get_pydate()
            if not bas_py:
                ModernMesaj.uyari(self, "Lütfen başlangıç tarihini girin.")
                return
            h.baslangic_tarihi = bas_py
            bitis_py = self.bitis.get_pydate()
            h.bitis_tarihi = bitis_py if (bitis_py and bitis_py.year < 2099) else None
            h.durum = self.durum_cb.currentText()
            h.alacakli_kurum = self.alacakli.text()
            h.iban = self.iban.text()
            h.aciklama = self.aciklama.toPlainText()

            self.session.commit()
            self.accept()
        except Exception as e:
            ModernMesaj.hata(self, str(e))