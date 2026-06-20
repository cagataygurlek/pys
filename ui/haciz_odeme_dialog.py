# ui/haciz_odeme_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QFileDialog, QFrame, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from models import Haciz, HacizOdeme, Bordro   # 🆕 Bordro eklendi
from ui.utils import ModernMesaj, make_frameless
from ui.widgets import ToggleSwitch
import datetime
import calendar


class HacizOdemeDialog(QDialog):
    def __init__(self, session, yil, ay, asgari_normal, asgari_emekli, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.yil = yil
        self.ay = ay
        self.asgari_normal = asgari_normal
        self.asgari_emekli = asgari_emekli
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(f"⚖️ Haciz Ödemeleri - {self.ay}/{self.yil}")
        self.resize(940, 560)
        self.setStyleSheet("""
            QDialog { background: transparent; }
            QLabel { background: transparent; color: #ecf0f1; }
            QPushButton { border: none; border-radius: 6px; color: white; font-weight: bold; }
        """)
        self.selected_haciz_ids = set()
        self.init_ui()
        self.load_data()
        make_frameless(self)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer {
                background-color: #2c3e50;
                border-radius: 16px;
                border: 1px solid #4a6278;
            }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        layout.addWidget(outer)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(66)
        hdr.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6c1e1e,stop:1 #c0392b);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border: none;
            }
        """)
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(20, 0, 20, 0)
        hdr_lay.setSpacing(12)

        ic = QLabel("⚖️")
        ic.setFixedSize(44, 44)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background: rgba(255,255,255,0.15); border-radius: 22px; font-size: 20px;")

        tl = QLabel(f"{self.ay}. Ay / {self.yil} — Haciz Ödeme Listesi")
        tl.setStyleSheet("color: white; font-size: 14px; font-weight: bold; background: transparent;")

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: rgba(255,255,255,0.6);
                          font-size: 16px; border: none; }
            QPushButton:hover { color: white; }
        """)
        close_btn.clicked.connect(self.reject)

        hdr_lay.addWidget(ic)
        hdr_lay.addWidget(tl)
        hdr_lay.addStretch()
        hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 14, 16, 10)
        body_lay.setSpacing(10)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Seç", "Sıra", "Personel", "Dosya No", "Borç Miktarı",
            "Kalan Borç", "Havuzdaki Tutar", "Ödenecek Tutar"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #34495e;
                border: 1px solid #4a6278;
                border-radius: 8px;
                color: #ecf0f1;
                gridline-color: rgba(255,255,255,0.07);
                outline: none;
            }
            QHeaderView::section {
                background-color: #1a2a38;
                color: #bdc3c7;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background: #2980b9; color: white; }
        """)
        body_lay.addWidget(self.table)
        outer_lay.addWidget(body)

        # Alt buton barı
        btn_frame = QFrame()
        btn_frame.setFixedHeight(66)
        btn_frame.setStyleSheet("""
            QFrame {
                background-color: #243342;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
                border: none;
                border-top: 1px solid #1a2a38;
            }
        """)
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setContentsMargins(16, 10, 16, 10)
        btn_lay.setSpacing(8)

        self.tumu_sec_btn = QPushButton("✅ Tümünü Seç")
        self.tumu_sec_btn.setFixedHeight(40)
        self.tumu_sec_btn.setStyleSheet("QPushButton { background:#3498db; border-radius:8px; padding:0 14px; font-size:12px; font-weight:bold; color:white; border:none; } QPushButton:hover { background:#2980b9; }")
        self.tumu_sec_btn.clicked.connect(self.tumunu_sec)

        self.tumu_kaldir_btn = QPushButton("❌ Kaldır")
        self.tumu_kaldir_btn.setFixedHeight(40)
        self.tumu_kaldir_btn.setStyleSheet("QPushButton { background:#636e72; border-radius:8px; padding:0 14px; font-size:12px; font-weight:bold; color:white; border:none; } QPushButton:hover { background:#4a4f52; }")
        self.tumu_kaldir_btn.clicked.connect(self.tumunu_kaldir)

        self.odeme_yap_btn = QPushButton("⚖️ Haciz\nÖdemesi Yap")
        self.odeme_yap_btn.setFixedHeight(40)
        self.odeme_yap_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8e44ad,stop:1 #c0392b);
                border-radius: 8px; padding: 0 18px;
                font-size: 11px; font-weight: bold; color: white; border: none;
                line-height: 1.3;
            }
            QPushButton:hover { background: #7d3c98; }
        """)
        self.odeme_yap_btn.clicked.connect(self.odeme_yap)

        self.kapat_btn = QPushButton("Kapat")
        self.kapat_btn.setFixedHeight(40)
        self.kapat_btn.setStyleSheet("QPushButton { background:transparent; color:#bdc3c7; border:1px solid #4a6278; border-radius:8px; padding:0 18px; font-size:12px; } QPushButton:hover { background:#34495e; color:white; }")
        self.kapat_btn.clicked.connect(self.reject)

        btn_lay.addWidget(self.tumu_sec_btn)
        btn_lay.addWidget(self.tumu_kaldir_btn)
        btn_lay.addStretch()
        btn_lay.addWidget(self.odeme_yap_btn)
        btn_lay.addWidget(self.kapat_btn)
        outer_lay.addWidget(btn_frame)

        # Ortala
        from PyQt5.QtCore import QTimer
        def _ortala():
            p = self.parent()
            if p:
                pg = p.frameGeometry()
                self.move(pg.x() + (pg.width() - self.width()) // 2,
                          pg.y() + (pg.height() - self.height()) // 2 - 40)
            else:
                from PyQt5.QtWidgets import QApplication
                sc = QApplication.primaryScreen().availableGeometry()
                self.move(sc.x() + (sc.width() - self.width()) // 2,
                          sc.y() + (sc.height() - self.height()) // 2)
        QTimer.singleShot(0, _ortala)

    def load_data(self):
        self.table.setRowCount(0)

        ilk_gun = datetime.date(self.yil, self.ay, 1)
        son_gun = datetime.date(self.yil, self.ay, calendar.monthrange(self.yil, self.ay)[1])

        tum_hacizler = self.session.query(Haciz).filter(
            Haciz.durum == "Aktif",
            Haciz.kalan_borc > 0,
            Haciz.baslangic_tarihi <= son_gun,
            (Haciz.bitis_tarihi >= ilk_gun) | (Haciz.bitis_tarihi == None)
        ).order_by(Haciz.personel_id, Haciz.baslangic_tarihi).all()

        personel_gorulen = set()
        hacizler = []
        for h in tum_hacizler:
            if h.personel_id not in personel_gorulen:
                personel_gorulen.add(h.personel_id)
                hacizler.append(h)

        for idx, h in enumerate(hacizler, 1):
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Seçim toggle
            toggle = ToggleSwitch(width=30, height=16)
            toggle.setChecked(False)
            toggle.stateChanged.connect(lambda state, x=h.id: self.toggle_degisti(x, state))
            toggle_widget = QWidget()
            toggle_layout = QHBoxLayout(toggle_widget)
            toggle_layout.setAlignment(Qt.AlignCenter)
            toggle_layout.setContentsMargins(4, 4, 4, 4)
            toggle_layout.addWidget(toggle)
            self.table.setCellWidget(row, 0, toggle_widget)

            self.table.setItem(row, 1, QTableWidgetItem(str(idx)))
            self.table.setItem(row, 2, QTableWidgetItem(f"{h.personel.ad_soyad} ({h.personel.sicil_no})"))
            self.table.setItem(row, 3, QTableWidgetItem(h.dosya_no))
            self.table.setItem(row, 4, QTableWidgetItem(f"{h.borc_miktari:,.2f} ₺".replace(",", ".")))

            kalan_item = QTableWidgetItem(f"{h.kalan_borc:,.2f} ₺".replace(",", "."))
            kalan_item.setForeground(QColor("#27ae60") if h.kalan_borc > 0 else QColor("#e74c3c"))
            self.table.setItem(row, 5, kalan_item)

            emekli_mi = "emekli" in (h.personel.aciklama or "").lower()
            resmi_maas = self.asgari_emekli if emekli_mi else self.asgari_normal
            aylik_kesinti_tutari = resmi_maas * 0.25
            self.table.setItem(row, 6, QTableWidgetItem(f"{aylik_kesinti_tutari:,.2f} ₺".replace(",", ".")))

            odenecek = min(h.kalan_borc, aylik_kesinti_tutari)
            odenecek_item = QTableWidgetItem(f"{odenecek:,.2f} ₺".replace(",", "."))
            odenecek_item.setForeground(QColor("#e67e22"))
            self.table.setItem(row, 7, odenecek_item)

    def toggle_degisti(self, haciz_id, state):
        if state:
            self.selected_haciz_ids.add(haciz_id)
        else:
            self.selected_haciz_ids.discard(haciz_id)

    def tumunu_sec(self):
        for row in range(self.table.rowCount()):
            w = self.table.cellWidget(row, 0)
            if w:
                toggle = w.findChild(ToggleSwitch)
                if toggle:
                    toggle.setChecked(True)

    def tumunu_kaldir(self):
        for row in range(self.table.rowCount()):
            w = self.table.cellWidget(row, 0)
            if w:
                toggle = w.findChild(ToggleSwitch)
                if toggle:
                    toggle.setChecked(False)

    def odeme_yap(self):
        if not self.selected_haciz_ids:
            ModernMesaj.uyari(self, "Lütfen ödeme yapılacak hacizleri seçin.")
            return

        toplam_tutar = 0
        odenecekler = {}
        for h_id in self.selected_haciz_ids:
            h = self.session.get(Haciz, h_id)
            if h:
                emekli_mi = "emekli" in (h.personel.aciklama or "").lower()
                resmi_maas = self.asgari_emekli if emekli_mi else self.asgari_normal
                aylik = resmi_maas * 0.25
                odenecek = min(h.kalan_borc, aylik)
                odenecekler[h_id] = odenecek
                toplam_tutar += odenecek

        if toplam_tutar == 0:
            ModernMesaj.uyari(self, "Seçili hacizler için ödenecek tutar sıfır.")
            return

        msg = f"Seçili {len(self.selected_haciz_ids)} haciz için toplam {toplam_tutar:,.2f} TL ödeme yapılacak. Onaylıyor musunuz?"
        if not ModernMesaj.soru(self, msg):
            return

        son_gun = datetime.date(self.yil, self.ay, calendar.monthrange(self.yil, self.ay)[1])
        try:
            for h_id, tutar in odenecekler.items():
                h = self.session.get(Haciz, h_id)

                # 🆕 İlgili bordroyu bul (güncel ay/yıl)
                bordro = self.session.query(Bordro).filter(
                    Bordro.personel_id == h.personel_id,
                    Bordro.yil == self.yil,
                    Bordro.ay == self.ay
                ).first()

                # Ödeme kaydı oluştur
                odeme = HacizOdeme(
                    haciz_id=h_id,
                    bordro_id=bordro.id if bordro else None,  # 🆕 bordro ilişkisi
                    tarih=son_gun,
                    tutar=tutar,
                    aciklama=f"{self.ay}. ay {self.yil} maaş kesintisi (%25)"
                )
                self.session.add(odeme)

                # Haciz kalan borcunu düş
                h.kalan_borc -= tutar
                if h.kalan_borc <= 0:
                    h.kalan_borc = 0
                    h.durum = "Tamamlandı"

                # 🆕 Bordrodaki bekleyen haciz tutarını azalt
                if bordro:
                    bordro.bekleyen_haciz_tutari = max(0, (bordro.bekleyen_haciz_tutari or 0) - tutar)

            self.session.commit()
            ModernMesaj.basari(self, f"{len(self.selected_haciz_ids)} haciz için ödeme yapıldı.")
            self.accept()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))