# ui/dashboard_page.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QTableWidget, QScrollArea,
    QTableWidgetItem, QHeaderView, QSizePolicy, QStackedWidget
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation
from PyQt5.QtGui import QColor, QFont
from database import get_session
from models import Personel, Gorev, HacizOdeme, Haciz, Bordro, Sube, Avans, Izin, BasvuruAday, SistemAyarlari
from sqlalchemy import func
import datetime
import calendar



RENKLER = ["#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#e74c3c", "#1abc9c", "#e67e22", "#bdc3c7"]

# Şubeye göre sabit renk — veritabanındaki şube adlarıyla eşleşir
SUBE_RENKLERI = {
    "DEPO":       "#f39c12",
    "DOĞUKENT":   "#9b59b6",
    "İSTASYON":   "#3498db",
    "MAX GROSS":  "#2ecc71",
    "MEVLANA":    "#1abc9c",
    "NUMUNE":     "#e74c3c",
    "2001":       "#e67e22",
}

TABLE_STYLE = """
    QTableWidget {
        background-color: #34495e; border: none;
        gridline-color: rgba(255,255,255,0.06);
        color: #ecf0f1; font-size: 12px;
    }
    QHeaderView::section {
        background-color: #1a2a38; color: #7f8c8d;
        font-size: 10px; font-weight: bold;
        padding: 6px 8px; border: none; letter-spacing: 0.5px;
    }
    QTableWidget::item { padding: 6px 8px; border-bottom: 1px solid rgba(255,255,255,0.04); }
    QTableWidget::item:selected { background-color: rgba(52,152,219,0.25); color: white; }
    QTableWidget::item:alternate { background-color: rgba(26,42,56,0.6); }
"""


class DashboardPage(QWidget):
    def __init__(self, kullanici=None):
        super().__init__()
        self.kullanici = kullanici
        self.session = get_session()
        self.setStyleSheet("background-color: #2c3e50;")
        self.init_ui()
        self._yetki_uygula()
        self._load_slider_speed()
        self.refresh_data()

    def _yetki_uygula(self):
        if not self.kullanici or self.kullanici.admin:
            return
        yetkili = {y.modul_adi for y in self.kullanici.yetkileri}
        if "maas" not in yetkili:
            self.maas_card.setVisible(False)
            self.haciz_card.setVisible(False)
            self.haciz_uyari.setVisible(False)

    def _load_slider_speed(self):
        ayar = self.session.query(SistemAyarlari).filter_by(anahtar='dashboard_slider_speed').first()
        if ayar and ayar.deger:
            try:
                self.SLIDER_INTERVAL_MS = int(ayar.deger) * 1000
            except Exception:
                pass
        if hasattr(self, '_slider_timer'):
            self._slider_timer.setInterval(self.SLIDER_INTERVAL_MS)

    # ── YARDIMCI BİLEŞENLER ──────────────────────────────────────────

    def _panel_hdr(self, title, extra_widget=None):
        hdr = QFrame()
        hdr.setFixedHeight(40)
        hdr.setStyleSheet("QFrame { background-color: #1a2a38; border-radius: 10px 10px 0 0; border-bottom: 1px solid #4a6278; }")
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(14, 0, 10, 0)
        t = QLabel(title)
        t.setStyleSheet("color: #ecf0f1; font-size: 13px; font-weight: bold; background: transparent;")
        lay.addWidget(t)
        lay.addStretch()
        if extra_widget:
            lay.addWidget(extra_widget)
        return hdr

    def _stat_kart(self, title, icon, color, sub=""):
        card = QFrame()
        card.setMinimumHeight(100)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #34495e; border-radius: 10px;
                border-left: 4px solid {color};
                border-top: 1px solid #4a6278;
                border-right: 1px solid #4a6278;
                border-bottom: 1px solid #4a6278;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(4)
        top_row = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setStyleSheet("color: #7f8c8d; font-size: 11px; background: transparent; border: none;")
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        top_row.addWidget(lbl)
        top_row.addStretch()
        top_row.addWidget(icon_lbl)
        lay.addLayout(top_row)
        val = QLabel("—")
        val.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold; background: transparent; border: none;")
        lay.addWidget(val)
        if sub:
            sub_lbl = QLabel(sub)
            sub_lbl.setStyleSheet("color: #4a6278; font-size: 10px; background: transparent; border: none;")
            lay.addWidget(sub_lbl)
        card.value_label = val
        return card

    def _tablo(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.setAlternatingRowColors(True)
        t.setStyleSheet(TABLE_STYLE)
        return t

    def _qcard(self, label, color):
        card = QFrame()
        card.setMinimumHeight(62)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #2c3e50; border-radius: 8px;
                border: 1px solid #4a6278; border-top: 3px solid {color};
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #7f8c8d; font-size: 10px; background: transparent;")
        lbl.setWordWrap(True)
        val = QLabel("—")
        val.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold; background: transparent;")
        lay.addWidget(lbl)
        lay.addWidget(val)
        card.value_label = val
        return card

    def _tab_btn(self, text, active=False):
        btn = QPushButton(text)
        btn.setFixedHeight(26)
        btn.setFixedWidth(60)
        btn.setCursor(Qt.PointingHandCursor)
        self._tab_btn_style(btn, active)
        return btn

    def _tab_btn_style(self, btn, active):
        if active:
            btn.setStyleSheet("QPushButton { background: #3498db; color: white; border-radius: 4px; font-size: 10px; font-weight: bold; border: none; }")
        else:
            btn.setStyleSheet("QPushButton { background: #1a2a38; color: #7f8c8d; border-radius: 4px; font-size: 10px; border: none; } QPushButton:hover { color: #bdc3c7; }")

    # Görev adına göre emoji ikon eşlemesi
    GOREV_IKONLARI = {
        "BÖLGE MÜDÜRÜ":    ("🌍", "#e74c3c"),
        "DEPO GÖREVLİSİ":  ("📦", "#f39c12"),
        "EKMEK REYONU":    ("🥪", "#e67e22"),
        "GRAFİKER":        ("🎨", "#9b59b6"),
        "KASAP":           ("🔪", "#e74c3c"),
        "KASAP SÖKÜM":     ("🥩", "#c0392b"),
        "KASAP ŞARKÜTERİ": ("🥩", "#e74c3c"),
        "KASİYER":         ("💳", "#3498db"),
        "MAĞAZA MDR YRD":  ("🏬", "#2ecc71"),
        "MAĞAZA MÜDÜRÜ":   ("🏪", "#2ecc71"),
        "MAL KABUL":       ("📋", "#1abc9c"),
        "MANAV":           ("🍓", "#27ae60"),
        "MUHASEBE MÜDÜRÜ": ("📊", "#9b59b6"),
        "ÖN MUHASEBE":     ("📱", "#8e44ad"),
        "PERSONEL MÜDÜRÜ": ("👔", "#3498db"),
        "REYON":           ("🛒", "#3498db"),
        "SATINALMA":       ("🛍️",  "#f39c12"),
        "ŞOFÖR":           ("🚛", "#7f8c8d"),
    }

    def _gorev_kart(self, gorev_ad, sayi, ort_maas, sube_dagilim, renk):
        """Tek bir görev için istatistik kartı — mockup stili."""
        ikon_bilgi = self.GOREV_IKONLARI.get(gorev_ad.upper(), ("💼", renk))
        ikon = ikon_bilgi[0]

        card = QFrame()
        card.setMinimumWidth(160)
        card.setStyleSheet(f"""
            QFrame#gorev_card {{
                background-color: #1a2a38;
                border-radius: 10px;
                border: 1.5px solid {renk};
            }}
        """)
        card.setObjectName("gorev_card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        # ── Başlık: İkon + Görev adı + sayı ──
        hdr = QFrame()
        hdr.setStyleSheet("QFrame { background: transparent; border: none; }")
        hdr_h = QHBoxLayout(hdr)
        hdr_h.setContentsMargins(0, 0, 0, 0)
        hdr_h.setSpacing(6)

        # İkon kutusu
        ikon_lbl = QLabel(ikon)
        ikon_lbl.setFixedSize(28, 28)
        ikon_lbl.setAlignment(Qt.AlignCenter)
        ikon_lbl.setStyleSheet(f"background: rgba(255,255,255,0.08); border-radius: 6px; font-size: 14px; border: none;")

        ad_lbl = QLabel(gorev_ad.upper())
        ad_lbl.setStyleSheet(f"color: {renk}; font-size: 10px; font-weight: bold; background: transparent; letter-spacing: 0.4px;")
        ad_lbl.setWordWrap(False)

        sayi_lbl = QLabel(str(sayi))
        sayi_lbl.setStyleSheet(f"color: {renk}; font-size: 22px; font-weight: bold; background: transparent;")
        sayi_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        hdr_h.addWidget(ikon_lbl)
        hdr_h.addWidget(ad_lbl, 1)
        hdr_h.addWidget(sayi_lbl)
        lay.addWidget(hdr)

        # ── Kişi sayısı kutusu ──
        kisi_box = QFrame()
        kisi_box.setStyleSheet(f"QFrame {{ background: rgba(255,255,255,0.05); border-radius: 5px; border: 1px solid rgba(255,255,255,0.07); }}")
        kisi_box.setFixedHeight(26)
        kisi_h = QHBoxLayout(kisi_box)
        kisi_h.setContentsMargins(8, 0, 8, 0)
        kisi_lbl = QLabel(f"{sayi} kişi")
        kisi_lbl.setStyleSheet("color: #7f8c8d; font-size: 10px; background: transparent;")
        kisi_h.addWidget(kisi_lbl)
        lay.addWidget(kisi_box)

        # ── Ort. Maaş kutusu ──
        goster_maas = True
        if self.kullanici and not self.kullanici.admin:
            yetkili = {y.modul_adi for y in self.kullanici.yetkileri}
            goster_maas = "maas" in yetkili
        if goster_maas:
            maas_box = QFrame()
            maas_box.setStyleSheet(f"QFrame {{ background: rgba(255,255,255,0.05); border-radius: 5px; border: 1px solid rgba(255,255,255,0.07); }}")
            maas_v = QVBoxLayout(maas_box)
            maas_v.setContentsMargins(8, 4, 8, 4)
            maas_v.setSpacing(1)
            maas_lbl = QLabel("Ort. Maaş")
            maas_lbl.setStyleSheet("color: #7f8c8d; font-size: 9px; background: transparent;")
            maas_val = QLabel(f"{ort_maas:,.2f} ₺".replace(",", "."))
            maas_val.setStyleSheet(f"color: {renk}; font-size: 12px; font-weight: bold; background: transparent;")
            maas_v.addWidget(maas_lbl)
            maas_v.addWidget(maas_val)
            lay.addWidget(maas_box)

        # ── Şube Dağılımı — mini slider ──
        if sube_dagilim and sayi > 0:
            dag_box = QFrame()
            dag_box.setStyleSheet("QFrame { background: rgba(255,255,255,0.05); border-radius: 5px; border: 1px solid rgba(255,255,255,0.07); }")
            dag_v = QVBoxLayout(dag_box)
            dag_v.setContentsMargins(8, 5, 8, 5)
            dag_v.setSpacing(4)

            # Mini slider başlık + nokta
            mini_hdr = QHBoxLayout()
            mini_hdr.setContentsMargins(0, 0, 0, 0)
            dag_lbl = QLabel("Şube Dağılımı")
            dag_lbl.setStyleSheet("color: #7f8c8d; font-size: 9px; background: transparent;")
            mini_noktalar = QLabel("")
            mini_noktalar.setStyleSheet("color: #4a6278; font-size: 8px; background: transparent; letter-spacing: 2px;")
            mini_noktalar.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            mini_hdr.addWidget(dag_lbl)
            mini_hdr.addStretch()
            mini_hdr.addWidget(mini_noktalar)
            dag_v.addLayout(mini_hdr)

            # Segment bar (sabit — tüm şubeler)
            bar_frame = QFrame()
            bar_frame.setFixedHeight(7)
            bar_frame.setStyleSheet("QFrame { background: #0d1b26; border-radius: 3px; border: none; }")
            bar_lay = QHBoxLayout(bar_frame)
            bar_lay.setContentsMargins(0, 0, 0, 0)
            bar_lay.setSpacing(1)
            for i, (sube_ad, s_sayi) in enumerate(sube_dagilim[:5]):
                sube_renk = SUBE_RENKLERI.get(sube_ad.upper(), RENKLER[i % len(RENKLER)])
                seg = QFrame()
                seg.setStyleSheet(f"QFrame {{ background: {sube_renk}; border-radius: 2px; border: none; }}")
                bar_lay.addWidget(seg, max(s_sayi, 1))
            dag_v.addWidget(bar_frame)

            # Mini slider: şubeler tek tek döner
            mini_stack = QStackedWidget()
            mini_stack.setStyleSheet("background: transparent;")
            mini_stack.setFixedHeight(18)

            for i, (sube_ad, s_sayi) in enumerate(sube_dagilim):
                sube_renk = SUBE_RENKLERI.get(sube_ad.upper(), RENKLER[i % len(RENKLER)])
                sube_w = QWidget()
                sube_w.setStyleSheet("background: transparent;")
                sube_h = QHBoxLayout(sube_w)
                sube_h.setContentsMargins(0, 0, 0, 0)
                sube_h.setSpacing(4)
                dot = QLabel("■")
                dot.setStyleSheet(f"color: {sube_renk}; font-size: 10px; background: transparent;")
                dot.setFixedWidth(12)
                s_lbl = QLabel(f"{sube_ad}")
                s_lbl.setStyleSheet(f"color: {sube_renk}; font-size: 10px; font-weight: bold; background: transparent;")
                sayi_w = QLabel(f"{s_sayi} kişi")
                sayi_w.setStyleSheet("color: #bdc3c7; font-size: 10px; background: transparent;")
                sayi_w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                sube_h.addWidget(dot)
                sube_h.addWidget(s_lbl, 1)
                sube_h.addWidget(sayi_w)
                mini_stack.addWidget(sube_w)

            dag_v.addWidget(mini_stack)
            lay.addWidget(dag_box)

            # Mini timer — 4 saniyede bir şube değiştir
            mini_idx = [0]
            toplam_sube = len(sube_dagilim)

            def _guncelle_noktalar(idx):
                noktalar = "".join("●" if j == idx else "○" for j in range(min(toplam_sube, 6)))
                mini_noktalar.setText(noktalar)

            def _mini_ilerle():
                mini_idx[0] = (mini_idx[0] + 1) % toplam_sube
                mini_stack.setCurrentIndex(mini_idx[0])
                _guncelle_noktalar(mini_idx[0])

            _guncelle_noktalar(0)

            mini_timer = QTimer(card)
            mini_timer.setInterval(4000)
            mini_timer.timeout.connect(_mini_ilerle)
            mini_timer.start()
            # Timer'ı card'a bağla — card silinince timer da durur
            card._mini_timer = mini_timer

        lay.addStretch()
        return card

    def _hareket_satir(self, text, color, zaman):
        row = QFrame()
        row.setStyleSheet("QFrame { border: none; border-bottom: 1px solid rgba(255,255,255,0.05); background: transparent; }")
        row.setFixedHeight(36)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)
        dot = QLabel("●")
        dot.setFixedWidth(12)
        dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
        txt = QLabel(text)
        txt.setStyleSheet("color: #bdc3c7; font-size: 12px; background: transparent;")
        tim = QLabel(zaman)
        tim.setStyleSheet("color: #4a6278; font-size: 10px; background: transparent;")
        tim.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(dot)
        lay.addWidget(txt, 1)
        lay.addWidget(tim)
        return row

    # ── UI KURULUMU ──────────────────────────────────────────────────

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── 6 STAT KARTI ─────────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.toplam_card  = self._stat_kart("Toplam Personel",  "👥", "#3498db", "+bu ay")
        self.aktif_card   = self._stat_kart("Aktif Personel",   "✅", "#2ecc71", "")
        self.emekli_card  = self._stat_kart("Emekli Personel",  "🏅", "#9b59b6", "")
        self.engelli_card = self._stat_kart("Engelli Personel", "♿", "#e67e22", "")
        self.maas_card    = self._stat_kart("Toplam Maaş",      "💰", "#f39c12", "Aylık brüt")
        self.haciz_card   = self._stat_kart("Haciz Kesintisi",  "⚖️", "#e74c3c", "Bu ay")
        for c in [self.toplam_card, self.aktif_card, self.emekli_card,
                  self.engelli_card, self.maas_card, self.haciz_card]:
            row1.addWidget(c)
        root.addLayout(row1)

        # ── ORTA BÖLÜM ────────────────────────────────────────────────
        mid = QHBoxLayout()
        mid.setSpacing(10)

        # Sol: Şube/Görev sekmeli tablo
        sol = QFrame()
        sol.setStyleSheet("QFrame { background-color: #34495e; border-radius: 10px; border: 1px solid #4a6278; }")
        sol_lay = QVBoxLayout(sol)
        sol_lay.setContentsMargins(0, 0, 0, 0)
        sol_lay.setSpacing(0)

        # Tab butonları widget
        tab_w = QWidget()
        tab_w.setStyleSheet("background: transparent;")
        tab_h = QHBoxLayout(tab_w)
        tab_h.setContentsMargins(6, 0, 6, 0)
        tab_h.setSpacing(4)
        self.btn_sube  = self._tab_btn("Şube", active=True)
        self.btn_gorev = self._tab_btn("Görev", active=False)
        tab_h.addWidget(self.btn_sube)
        tab_h.addWidget(self.btn_gorev)

        sol_lay.addWidget(self._panel_hdr("🏢 Personel Dağılımı", tab_w))

        self.dag_stack = QStackedWidget()
        self.dag_stack.setStyleSheet("background: transparent;")

        # Şube tablosu
        self.sube_table = self._tablo(["Şube", "Kişi", "Oran"])
        self.sube_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.sube_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.sube_table.setColumnWidth(1, 55)
        self.sube_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.sube_table.setColumnWidth(2, 70)
        self.dag_stack.addWidget(self.sube_table)

        # Görev tablosu
        self.gorev_table = self._tablo(["Görev", "Kişi", "Oran"])
        self.gorev_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.gorev_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.gorev_table.setColumnWidth(1, 55)
        self.gorev_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.gorev_table.setColumnWidth(2, 70)
        self.dag_stack.addWidget(self.gorev_table)

        sol_lay.addWidget(self.dag_stack, 1)
        mid.addWidget(sol, 3)

        self.btn_sube.clicked.connect(lambda: self._switch_tab(0))
        self.btn_gorev.clicked.connect(lambda: self._switch_tab(1))

        # Sağ: Haciz uyarı + Doğum günleri
        sag_lay = QVBoxLayout()
        sag_lay.setSpacing(10)

        # Haciz havuzu uyarı kartı
        self.haciz_uyari = QFrame()
        self.haciz_uyari.setStyleSheet("QFrame { background-color: #34495e; border-radius: 10px; border: 1px solid #4a6278; }")
        self.haciz_uyari_lay = QVBoxLayout(self.haciz_uyari)
        self.haciz_uyari_lay.setContentsMargins(0, 0, 0, 0)
        self.haciz_uyari_lay.setSpacing(0)
        self.haciz_uyari_hdr_lbl = QLabel("⚖️ Haciz Havuzu — Ödeme Bekliyor")
        self.haciz_uyari_hdr_lbl.setStyleSheet("color: #e74c3c; font-size: 13px; font-weight: bold; background: #3d1f1f; padding: 10px 14px; border-radius: 10px 10px 0 0; border-bottom: 1px solid #4a6278;")
        self.haciz_uyari_lay.addWidget(self.haciz_uyari_hdr_lbl)
        self.haciz_uyari_table = self._tablo(["Personel", "Havuz", ""])
        self.haciz_uyari_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.haciz_uyari_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.haciz_uyari_table.setColumnWidth(1, 100)
        self.haciz_uyari_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.haciz_uyari_table.setColumnWidth(2, 70)
        self.haciz_uyari_lay.addWidget(self.haciz_uyari_table, 1)
        # Toplam satırı
        self.haciz_toplam_lbl = QLabel("")
        self.haciz_toplam_lbl.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold; background: #243342; padding: 6px 14px; border-radius: 0 0 10px 10px; border-top: 1px solid #1a2a38;")
        self.haciz_uyari_lay.addWidget(self.haciz_toplam_lbl)
        sag_lay.addWidget(self.haciz_uyari, 3)

        # Doğum günleri
        dogum_frame = QFrame()
        dogum_frame.setStyleSheet("QFrame { background-color: #34495e; border-radius: 10px; border: 1px solid #4a6278; }")
        dogum_lay = QVBoxLayout(dogum_frame)
        dogum_lay.setContentsMargins(0, 0, 0, 0)
        dogum_lay.setSpacing(0)
        dogum_lay.addWidget(self._panel_hdr("🎂 Bu Ay Doğum Günleri"))
        dogum_scroll_w = QWidget()
        dogum_scroll_w.setStyleSheet("background: transparent;")
        self.dogum_v = QVBoxLayout(dogum_scroll_w)
        self.dogum_v.setContentsMargins(0, 0, 0, 0)
        self.dogum_v.setSpacing(0)
        self.dogum_scroll = QScrollArea()
        self.dogum_scroll.setWidgetResizable(True)
        self.dogum_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dogum_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dogum_scroll.setFixedHeight(220)
        self.dogum_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.dogum_scroll.setWidget(dogum_scroll_w)
        self._dogum_scroll_pos = 0.0
        self._dogum_scroll_dir = 1
        self._dogum_scroll_timer = QTimer(self)
        self._dogum_scroll_timer.setInterval(30)
        self._dogum_scroll_timer.timeout.connect(self._auto_scroll_dogum)
        self._dogum_scroll_timer.start()
        dogum_lay.addWidget(self.dogum_scroll, 1)
        sag_lay.addWidget(dogum_frame, 2)

        sag_w = QWidget()
        sag_w.setStyleSheet("background: transparent;")
        sag_w.setLayout(sag_lay)
        mid.addWidget(sag_w, 2)
        root.addLayout(mid, 3)

        # ── GÖREV İSTATİSTİKLERİ ──────────────────────────────────────
        # ── GÖREV SLIDER PANELİ ───────────────────────────────────────
        self._slider_sayfa = 0
        self._slider_sayfalar = []  # Her sayfa = liste of (g_ad, g_sayi, g_ort, sube_dag, renk)
        self.SLIDER_SAYFA_BOYUTU = 5
        self.SLIDER_INTERVAL_MS  = 8000
        gorev_panel = QFrame()
        gorev_panel.setStyleSheet("QFrame { background-color: #34495e; border-radius: 10px; border: 1px solid #4a6278; }")
        gorev_panel_lay = QVBoxLayout(gorev_panel)
        gorev_panel_lay.setContentsMargins(0, 0, 0, 0)
        gorev_panel_lay.setSpacing(0)

        # Başlık + nokta göstergesi + ok butonları
        self._slider_hdr_w = QWidget()
        self._slider_hdr_w.setStyleSheet("background: transparent;")
        slider_hdr_h = QHBoxLayout(self._slider_hdr_w)
        slider_hdr_h.setContentsMargins(6, 0, 6, 0)
        slider_hdr_h.setSpacing(4)

        self._slider_prev_btn = QPushButton("◀")
        self._slider_prev_btn.setFixedSize(22, 22)
        self._slider_prev_btn.setCursor(Qt.PointingHandCursor)
        self._slider_prev_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.1); color: #bdc3c7; border-radius: 4px; font-size: 10px; border: none; } QPushButton:hover { background: rgba(255,255,255,0.2); }")
        self._slider_prev_btn.clicked.connect(self._slider_prev)

        self._slider_pause_btn = QPushButton("⏸")
        self._slider_pause_btn.setFixedSize(20, 20)
        self._slider_pause_btn.setCursor(Qt.PointingHandCursor)
        self._slider_pause_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.08); color: #bdc3c7; border-radius: 10px; font-size: 9px; border: none; } QPushButton:hover { background: rgba(255,255,255,0.18); }")
        self._slider_pause_btn.clicked.connect(self._slider_toggle_pause)
        self._slider_paused = False

        self._noktalar_lbl = QLabel("")
        self._noktalar_lbl.setStyleSheet("color: #4a6278; font-size: 10px; background: transparent; letter-spacing: 3px;")
        self._noktalar_lbl.setAlignment(Qt.AlignCenter)

        self._slider_next_btn = QPushButton("▶")
        self._slider_next_btn.setFixedSize(22, 22)
        self._slider_next_btn.setCursor(Qt.PointingHandCursor)
        self._slider_next_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.1); color: #bdc3c7; border-radius: 4px; font-size: 10px; border: none; } QPushButton:hover { background: rgba(255,255,255,0.2); }")
        self._slider_next_btn.clicked.connect(self._slider_next)

        slider_hdr_h.addWidget(self._slider_prev_btn)

        # Noktalar: sol yarı | daire pause | sağ yarı
        self._noktalar_sol = QLabel("")
        self._noktalar_sol.setStyleSheet("color: #4a6278; font-size: 10px; background: transparent; letter-spacing: 3px;")
        self._noktalar_sol.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._noktalar_sag = QLabel("")
        self._noktalar_sag.setStyleSheet("color: #4a6278; font-size: 10px; background: transparent; letter-spacing: 3px;")
        self._noktalar_sag.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        slider_hdr_h.addWidget(self._noktalar_sol)
        slider_hdr_h.addWidget(self._slider_pause_btn)
        slider_hdr_h.addWidget(self._noktalar_sag)
        slider_hdr_h.addWidget(self._slider_next_btn)

        gorev_panel_lay.addWidget(self._panel_hdr("💼 Görev Bazlı İstatistikler", self._slider_hdr_w))

        # QStackedWidget — her sayfa = bir grup kart
        self.gorev_stack = QStackedWidget()
        self.gorev_stack.setStyleSheet("background: transparent;")
        gorev_panel_lay.addWidget(self.gorev_stack)
        root.addWidget(gorev_panel, 2)

        # Timer
        self._slider_timer = QTimer(self)
        self._slider_timer.setInterval(self.SLIDER_INTERVAL_MS)
        self._slider_timer.timeout.connect(self._slider_next)
        self._slider_timer.start()

    def _switch_tab(self, idx):
        self.dag_stack.setCurrentIndex(idx)
        self._tab_btn_style(self.btn_sube,  idx == 0)
        self._tab_btn_style(self.btn_gorev, idx == 1)

    def _slider_goster(self, sayfa_idx):
        """Belirtilen sayfayı göster, nokta göstergesini güncelle."""
        if not self._slider_sayfalar:
            return
        sayfa_idx = sayfa_idx % len(self._slider_sayfalar)
        self._slider_sayfa = sayfa_idx
        self.gorev_stack.setCurrentIndex(sayfa_idx)

        # Noktaları ortadan ikiye böl — pause butonu tam ortada durur
        toplam = len(self._slider_sayfalar)
        orta = toplam // 2
        sol = ""
        sag = ""
        for i in range(toplam):
            nokta = "●" if i == sayfa_idx else "○"
            if i < orta:
                sol += nokta
            else:
                sag += nokta
        self._noktalar_sol.setText(sol)
        self._noktalar_sag.setText(sag)

    def _slider_toggle_pause(self):
        """Ana slider'ı durdur / devam ettir."""
        self._slider_paused = not self._slider_paused
        if self._slider_paused:
            self._slider_timer.stop()
            self._slider_pause_btn.setText("▶")
            self._slider_pause_btn.setStyleSheet(
                "QPushButton { background: rgba(52,152,219,0.35); color: #3498db; border-radius: 10px; font-size: 9px; border: none; } "
                "QPushButton:hover { background: rgba(52,152,219,0.55); }")
        else:
            self._slider_timer.start()
            self._slider_pause_btn.setText("⏸")
            self._slider_pause_btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.08); color: #bdc3c7; border-radius: 10px; font-size: 9px; border: none; } "
                "QPushButton:hover { background: rgba(255,255,255,0.18); }")

    def _slider_next(self):
        if self._slider_sayfalar:
            self._slider_goster((self._slider_sayfa + 1) % len(self._slider_sayfalar))
            self._slider_timer.start()  # Timer'ı sıfırla

    def _slider_prev(self):
        if self._slider_sayfalar:
            self._slider_goster((self._slider_sayfa - 1) % len(self._slider_sayfalar))
            self._slider_timer.start()  # Timer'ı sıfırla

    def _auto_scroll_dogum(self):
        sb = self.dogum_scroll.verticalScrollBar()
        max_val = sb.maximum()
        if max_val <= 0:
            return
        self._dogum_scroll_pos += self._dogum_scroll_dir * 1.0
        if self._dogum_scroll_pos >= max_val:
            self._dogum_scroll_pos = max_val
            self._dogum_scroll_dir = -1
        elif self._dogum_scroll_pos <= 0:
            self._dogum_scroll_pos = 0
            self._dogum_scroll_dir = 1
        sb.setValue(int(self._dogum_scroll_pos))

    # ── VERİ YENİLEME ────────────────────────────────────────────────

    def refresh_data(self):
        try:
            bugun = datetime.date.today()
            yil, ay = bugun.year, bugun.month
            ilk_gun = datetime.date(yil, ay, 1)
            son_gun = datetime.date(yil, ay, calendar.monthrange(yil, ay)[1])

            # ── Stat kartları ──
            toplam  = self.session.query(Personel).count()
            aktif   = self.session.query(Personel).filter(Personel.isten_ayrilma == None).count()
            pasif   = self.session.query(Personel).filter(Personel.durum == "Pasif").count()
            emekli  = self.session.query(Personel).filter(
                Personel.isten_ayrilma == None,
                func.lower(Personel.aciklama).contains("emekli")
            ).count()
            engelli = self.session.query(Personel).filter(
                Personel.isten_ayrilma == None,
                func.lower(Personel.aciklama).contains("engelli")
            ).count()
            toplam_maas = self.session.query(func.sum(Personel.maas)).filter(
                Personel.isten_ayrilma == None
            ).scalar() or 0.0
            haciz_kesinti = self.session.query(func.sum(HacizOdeme.tutar)).filter(
                HacizOdeme.tarih >= ilk_gun,
                HacizOdeme.tarih <= son_gun
            ).scalar() or 0.0

            self.toplam_card.value_label.setText(str(toplam))
            self.aktif_card.value_label.setText(str(aktif))
            self.emekli_card.value_label.setText(str(emekli))
            self.engelli_card.value_label.setText(str(engelli))
            self.maas_card.value_label.setText(f"{toplam_maas:,.2f} ₺".replace(",", "."))
            self.haciz_card.value_label.setText(f"{haciz_kesinti:,.2f} ₺".replace(",", "."))

            toplam_aktif = aktif or 1

            # ── Şube tablosu ──
            subeler = self.session.query(
                Sube.ad, func.count(Personel.id)
            ).outerjoin(
                Personel,
                (Personel.sube_id == Sube.id) & (Personel.isten_ayrilma == None)
            ).group_by(Sube.id).order_by(func.count(Personel.id).desc()).all()

            self.sube_table.setRowCount(0)
            for i, (sube_ad, sayi) in enumerate(subeler):
                row = self.sube_table.rowCount()
                self.sube_table.insertRow(row)
                renk = RENKLER[i % len(RENKLER)]
                oran = int((sayi / toplam_aktif) * 100)
                ad_item = QTableWidgetItem(sube_ad or "Atanmamış")
                ad_item.setForeground(QColor("#ecf0f1"))
                say_item = QTableWidgetItem(str(sayi))
                say_item.setTextAlignment(Qt.AlignCenter)
                say_item.setForeground(QColor(renk))
                oran_item = QTableWidgetItem(f"%{oran}")
                oran_item.setTextAlignment(Qt.AlignCenter)
                oran_item.setForeground(QColor("#7f8c8d"))
                self.sube_table.setItem(row, 0, ad_item)
                self.sube_table.setItem(row, 1, say_item)
                self.sube_table.setItem(row, 2, oran_item)
                self.sube_table.setRowHeight(row, 32)

            # ── Görev dağılım tablosu ──
            gorevler_dag = self.session.query(
                Gorev.ad, func.count(Personel.id)
            ).outerjoin(
                Personel,
                (Personel.gorev_id == Gorev.id) & (Personel.isten_ayrilma == None)
            ).group_by(Gorev.id).order_by(func.count(Personel.id).desc()).all()

            self.gorev_table.setRowCount(0)
            for i, (gorev_ad, sayi) in enumerate(gorevler_dag):
                row = self.gorev_table.rowCount()
                self.gorev_table.insertRow(row)
                renk = RENKLER[i % len(RENKLER)]
                oran = int((sayi / toplam_aktif) * 100)
                ad_item = QTableWidgetItem(gorev_ad or "Atanmamış")
                ad_item.setForeground(QColor("#ecf0f1"))
                say_item = QTableWidgetItem(str(sayi))
                say_item.setTextAlignment(Qt.AlignCenter)
                say_item.setForeground(QColor(renk))
                oran_item = QTableWidgetItem(f"%{oran}")
                oran_item.setTextAlignment(Qt.AlignCenter)
                oran_item.setForeground(QColor("#7f8c8d"))
                self.gorev_table.setItem(row, 0, ad_item)
                self.gorev_table.setItem(row, 1, say_item)
                self.gorev_table.setItem(row, 2, oran_item)
                self.gorev_table.setRowHeight(row, 32)

            # ── Haciz havuzu ─────────────────────────────────────────
            self.haciz_uyari_table.setRowCount(0)
            bekleyen_toplam = 0.0
            bekleyen_kisi = 0

            bordrolar = self.session.query(Bordro).filter(
                Bordro.icra_kesintisi > 0
            ).all()

            personel_havuz = {}
            for b in bordrolar:
                odeme_var = self.session.query(HacizOdeme).filter(
                    HacizOdeme.bordro_id == b.id
                ).first()
                if not odeme_var:
                    pid = b.personel_id
                    personel_havuz[pid] = personel_havuz.get(pid, 0.0) + b.icra_kesintisi

            for i, (pid, tutar) in enumerate(
                sorted(personel_havuz.items(), key=lambda x: -x[1])
            ):
                p = self.session.get(Personel, pid)
                if not p:
                    continue
                bekleyen_toplam += tutar
                bekleyen_kisi += 1
                row = self.haciz_uyari_table.rowCount()
                self.haciz_uyari_table.insertRow(row)
                self.haciz_uyari_table.setRowHeight(row, 28)
                ad_item = QTableWidgetItem(f"{p.ad_soyad} ({p.sicil_no})")
                ad_item.setForeground(QColor("#ecf0f1"))
                tutar_item = QTableWidgetItem(f"{tutar:,.2f} ₺".replace(",", "."))
                tutar_item.setTextAlignment(Qt.AlignCenter)
                tutar_item.setForeground(QColor("#e74c3c"))
                fnt = QFont(); fnt.setBold(True); tutar_item.setFont(fnt)
                durum_item = QTableWidgetItem("Bekliyor")
                durum_item.setTextAlignment(Qt.AlignCenter)
                durum_item.setForeground(QColor("#f39c12"))
                self.haciz_uyari_table.setItem(row, 0, ad_item)
                self.haciz_uyari_table.setItem(row, 1, tutar_item)
                self.haciz_uyari_table.setItem(row, 2, durum_item)

            if bekleyen_kisi > 0:
                self.haciz_uyari.setStyleSheet("QFrame { background-color: #34495e; border-radius: 10px; border: 1.5px solid #e74c3c; }")
                self.haciz_uyari_hdr_lbl.setText(f"⚖️ Haciz Havuzu — Ödeme Bekliyor  ({bekleyen_kisi} kişi)")
                self.haciz_toplam_lbl.setText(f"  Toplam bekleyen: {bekleyen_toplam:,.2f} ₺".replace(",", "."))
            else:
                self.haciz_uyari.setStyleSheet("QFrame { background-color: #34495e; border-radius: 10px; border: 1px solid #4a6278; }")
                self.haciz_uyari_hdr_lbl.setText("⚖️ Haciz Havuzu")
                self.haciz_uyari_hdr_lbl.setStyleSheet("color: #2ecc71; font-size: 13px; font-weight: bold; background: #1a2a38; padding: 10px 14px; border-radius: 10px 10px 0 0; border-bottom: 1px solid #4a6278;")
                self.haciz_toplam_lbl.setText("  Bekleyen ödeme yok ✓")
                self.haciz_toplam_lbl.setStyleSheet("color: #2ecc71; font-size: 11px; font-weight: bold; background: #243342; padding: 6px 14px; border-radius: 0 0 10px 10px; border-top: 1px solid #1a2a38;")

            # ── Doğum günleri ─────────────────────────────────────────
            self._dogum_scroll_pos = 0.0
            self._dogum_scroll_dir = 1
            self.dogum_scroll.verticalScrollBar().setValue(0)
            while self.dogum_v.count():
                item = self.dogum_v.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            bugun_ay = bugun.month
            dogumlar = []
            personeller = self.session.query(Personel).filter(
                Personel.isten_ayrilma == None
            ).all()
            for p in personeller:
                if p.dogum_tarihi and p.dogum_tarihi.month == bugun_ay:
                    dogumlar.append(p)
            dogumlar.sort(key=lambda x: x.dogum_tarihi.day)

            if not dogumlar:
                bos = QLabel("Bu ay doğum günü olan personel yok.")
                bos.setStyleSheet("color: #4a6278; font-size: 11px; padding: 12px 14px; background: transparent;")
                self.dogum_v.addWidget(bos)
            else:
                for p in dogumlar:
                    row_w = QFrame()
                    row_w.setStyleSheet("QFrame { border: none; border-bottom: 1px solid rgba(255,255,255,0.05); background: transparent; }")
                    row_w.setFixedHeight(38)
                    row_h = QHBoxLayout(row_w)
                    row_h.setContentsMargins(10, 0, 10, 0)
                    row_h.setSpacing(8)

                    initials = "".join([w[0] for w in p.ad_soyad.split()[:2]])
                    av = QLabel(initials)
                    av.setFixedSize(28, 28)
                    av.setAlignment(Qt.AlignCenter)
                    idx_color = abs(hash(p.ad_soyad)) % len(RENKLER)
                    av.setStyleSheet(f"background: rgba(52,152,219,0.2); color: #3498db; border-radius: 14px; font-size: 10px; font-weight: bold;")

                    ad_lbl = QLabel(p.ad_soyad)
                    ad_lbl.setStyleSheet("color: #ecf0f1; font-size: 11px; font-weight: bold; background: transparent;")

                    gun = p.dogum_tarihi.day
                    fark = gun - bugun.day
                    if fark == 0:
                        tarih_lbl = QLabel(f"{gun} {self._ay_adi(bugun_ay)}")
                        tarih_lbl.setStyleSheet("color: #ecf0f1; font-size: 10px; background: transparent;")
                        bugün_badge = QLabel("Bugün!")
                        bugün_badge.setStyleSheet("background: #2ecc71; color: #0a3a1a; border-radius: 8px; font-size: 9px; font-weight: bold; padding: 1px 6px;")
                        row_h.addWidget(av)
                        row_h.addWidget(ad_lbl, 1)
                        row_h.addWidget(tarih_lbl)
                        row_h.addWidget(bugün_badge)
                    else:
                        tarih_lbl = QLabel(f"{gun} {self._ay_adi(bugun_ay)}")
                        tarih_lbl.setStyleSheet("color: #ecf0f1; font-size: 10px; background: transparent;")
                        gun_lbl = QLabel(f"{abs(fark)} gün sonra" if fark > 0 else "geçti")
                        gun_lbl.setStyleSheet("color: #7f8c8d; font-size: 9px; background: transparent;")
                        gun_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        row_h.addWidget(av)
                        row_h.addWidget(ad_lbl, 1)
                        row_h.addWidget(tarih_lbl)
                        row_h.addWidget(gun_lbl)

                    self.dogum_v.addWidget(row_w)

            self.dogum_scroll.widget().setMinimumHeight(self.dogum_v.sizeHint().height())

            # ── Görev slider kartları ─────────────────────────────────
            # Mevcut stack sayfalarını temizle
            while self.gorev_stack.count():
                w = self.gorev_stack.widget(0)
                self.gorev_stack.removeWidget(w)
                w.deleteLater()
            self._slider_sayfalar = []
            self._slider_sayfa = 0

            gorev_detay = self.session.query(
                Gorev.ad,
                func.count(Personel.id).label("sayi"),
                func.avg(Personel.maas).label("ort_maas")
            ).outerjoin(
                Personel,
                (Personel.gorev_id == Gorev.id) & (Personel.isten_ayrilma == None)
            ).group_by(Gorev.id).order_by(func.count(Personel.id).desc()).all()

            # Sadece kişisi olan görevler
            aktif_gorevler = [(g_ad, g_sayi, g_ort) for g_ad, g_sayi, g_ort in gorev_detay if g_sayi and g_sayi > 0]

            if not aktif_gorevler:
                bos_w = QWidget()
                bos_w.setStyleSheet("background: transparent;")
                bos_lay = QHBoxLayout(bos_w)
                bos = QLabel("Henüz görev tanımı yok.")
                bos.setStyleSheet("color: #4a6278; font-size: 12px; padding: 14px; background: transparent;")
                bos_lay.addWidget(bos)
                self.gorev_stack.addWidget(bos_w)
                self._noktalar_lbl.setText("")
                return

            # Sayfalara böl (SAYFA_BOYUTU'ar görev)
            N = self.SLIDER_SAYFA_BOYUTU
            for sayfa_no in range(0, len(aktif_gorevler), N):
                grup = aktif_gorevler[sayfa_no:sayfa_no + N]

                sayfa_w = QWidget()
                sayfa_w.setStyleSheet("background: transparent;")
                sayfa_lay = QHBoxLayout(sayfa_w)
                sayfa_lay.setContentsMargins(10, 10, 10, 10)
                sayfa_lay.setSpacing(10)

                for i, (g_ad, g_sayi, g_ort) in enumerate(grup):
                    global_idx = sayfa_no + i
                    renk = RENKLER[global_idx % len(RENKLER)]
                    g_obj = self.session.query(Gorev).filter(Gorev.ad == g_ad).first()
                    sube_dag = []
                    if g_obj:
                        sube_dag = self.session.query(
                            Sube.ad, func.count(Personel.id)
                        ).join(
                            Personel, Personel.sube_id == Sube.id
                        ).filter(
                            Personel.gorev_id == g_obj.id,
                            Personel.isten_ayrilma == None
                        ).group_by(Sube.id).order_by(func.count(Personel.id).desc()).all()

                    kart = self._gorev_kart(g_ad, g_sayi, g_ort or 0, sube_dag, renk)
                    sayfa_lay.addWidget(kart)

                sayfa_lay.addStretch()
                self.gorev_stack.addWidget(sayfa_w)
                self._slider_sayfalar.append(grup)

            # İlk sayfayı göster ve timer'ı başlat
            self._slider_goster(0)
            self._slider_timer.start()

        except Exception as e:
            import traceback
            print(f"Dashboard refresh hatası: {e}")
            traceback.print_exc()

    def _ay_adi(self, ay_no):
        return ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"][ay_no - 1]
