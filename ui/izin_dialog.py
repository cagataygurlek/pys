# ui/izin_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QTextEdit, QLabel, QPushButton,
    QFrame, QWidget, QListWidget, QListWidgetItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QFont

from database import get_session
from models import Izin, Personel, IzinTuru
import datetime

from ui.utils import ModernMesaj, TarihAlani, tr_lower


class IzinDialog(QDialog):
    def __init__(self, session, izin=None, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.izin = izin
        self.all_personeller = []
        self._updating = False
        self._drag_pos = None
        self.resize(580, 620)

        self.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QLabel { color: #ecf0f1; font-size: 12px; background: transparent; }
            QLineEdit, QComboBox, QSpinBox, QTextEdit {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #4a6278;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {
                border-color: #3498db;
                background-color: #1a2a38;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background-color: #2c3e50;
                color: #ecf0f1;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QListWidget {
                background-color: #1a2a38;
                color: #ecf0f1;
                border: 1px solid #3498db;
                border-radius: 6px;
                font-size: 12px;
            }
            QListWidget::item { padding: 5px 10px; }
            QListWidget::item:hover { background-color: #2c4a6a; }
            QListWidget::item:selected { background-color: #2980b9; color: white; }
            QSpinBox::up-button {
                subcontrol-origin: border; subcontrol-position: top right;
                width: 20px; background: #3d566e; border-left: 1px solid #4a6278; border-top-right-radius: 5px;
            }
            QSpinBox::up-button:hover { background: #2980b9; }
            QSpinBox::up-arrow { image: none; width: 0; height: 0;
                border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid #ecf0f1; }
            QSpinBox::down-button {
                subcontrol-origin: border; subcontrol-position: bottom right;
                width: 20px; background: #3d566e; border-left: 1px solid #4a6278; border-bottom-right-radius: 5px;
            }
            QSpinBox::down-button:hover { background: #2980b9; }
            QSpinBox::down-arrow { image: none; width: 0; height: 0;
                border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #ecf0f1; }
            QPushButton { font-weight: bold; padding: 8px 20px; border-radius: 8px; border: none; }
        """)

        self.init_ui()
        if self.izin:
            self.load_existing_data()

    # ── Header ───────────────────────────────────────────────────────────────
    def _make_header(self):
        hdr = QFrame(); hdr.setFixedHeight(56)
        hdr.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1a3a5c,stop:1 #2980b9); border: none; }"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(18,0,12,0); hl.setSpacing(12)
        ic = QLabel("🗓️"); ic.setFixedSize(38,38); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.15); border-radius:19px; font-size:18px;")
        ttl = QLabel("Yeni İzin Kaydı" if not self.izin else "İzin Düzenle")
        ttl.setStyleSheet("color:white; font-size:13px; font-weight:bold; background:transparent;")
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:14px;border:none;border-radius:13px;} QPushButton:hover{background:rgba(255,255,255,0.15);color:white;}")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        hl.addWidget(ic); hl.addWidget(ttl); hl.addStretch(); hl.addWidget(close_btn)
        return hdr

    # ── UI ───────────────────────────────────────────────────────────────────
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._make_header())

        body = QWidget(); body.setStyleSheet("background: transparent;")
        content = QVBoxLayout(body)
        content.setContentsMargins(24,18,24,16)
        content.setSpacing(12)

        def mk_lbl(t):
            l = QLabel(t)
            l.setStyleSheet("color:#85c1e9; font-size:10px; font-weight:bold; letter-spacing:0.8px;")
            return l

        # ── Personel arama + dropdown ────────────────────────────────────────
        content.addWidget(mk_lbl("PERSONEL"))
        self.personel_search = QLineEdit()
        self.personel_search.setPlaceholderText("🔍 Ad veya sicil no yazın...")
        self.personel_search.textChanged.connect(self._filtrele)
        content.addWidget(self.personel_search)

        self.personel_list = QListWidget()
        self.personel_list.setFixedHeight(100)
        self.personel_list.setVisible(False)
        self.personel_list.itemClicked.connect(self._personel_secildi)
        content.addWidget(self.personel_list)

        self.secili_lbl = QLabel("— Personel seçilmedi —")
        self.secili_lbl.setStyleSheet(
            "color:#f39c12; font-size:11px; font-weight:bold; background:#1a2a38; "
            "border:1px solid #f39c12; border-radius:6px; padding:5px 10px;"
        )
        content.addWidget(self.secili_lbl)

        # ── İzin türü ────────────────────────────────────────────────────────
        content.addWidget(mk_lbl("İZİN TÜRÜ"))
        self.izin_turu_combo = QComboBox()
        self.load_izin_turleri()
        content.addWidget(self.izin_turu_combo)

        # ── Tarih + Gün yan yana ─────────────────────────────────────────────
        tarih_row = QHBoxLayout(); tarih_row.setSpacing(10)

        bv = QVBoxLayout(); bv.setSpacing(4)
        bv.addWidget(mk_lbl("BAŞLANGIÇ"))
        self.baslangic_date = TarihAlani()
        self.baslangic_date.set_date(QDate.currentDate())
        self.baslangic_date.dateChanged.connect(self._bas_degisti)
        bv.addWidget(self.baslangic_date)
        tarih_row.addLayout(bv, 2)

        gv = QVBoxLayout(); gv.setSpacing(4)
        gv.addWidget(mk_lbl("GÜN"))
        self.gun_spin = QSpinBox()
        self.gun_spin.setMinimum(1); self.gun_spin.setMaximum(365); self.gun_spin.setValue(1)
        self.gun_spin.setSuffix(" gün")
        self.gun_spin.valueChanged.connect(self._gun_degisti)
        gv.addWidget(self.gun_spin)
        tarih_row.addLayout(gv, 1)

        bitev = QVBoxLayout(); bitev.setSpacing(4)
        bitev.addWidget(mk_lbl("BİTİŞ"))
        self.bitis_date = TarihAlani()
        self.bitis_date.set_date(QDate.currentDate())
        self.bitis_date.dateChanged.connect(self._bit_degisti)
        bitev.addWidget(self.bitis_date)
        tarih_row.addLayout(bitev, 2)

        content.addLayout(tarih_row)

        # ── Açıklama ────────────────────────────────────────────────────────
        content.addWidget(mk_lbl("AÇIKLAMA"))
        self.aciklama_edit = QTextEdit()
        self.aciklama_edit.setFixedHeight(70)
        self.aciklama_edit.setPlaceholderText("Açıklama (isteğe bağlı)...")
        content.addWidget(self.aciklama_edit)

        main_layout.addWidget(body)
        main_layout.addStretch()

        # ── Footer butonları ────────────────────────────────────────────────
        footer = QFrame(); footer.setFixedHeight(54)
        footer.setStyleSheet("QFrame{background:#1a2530;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border-top:1px solid #1a2a38;}")
        fl = QHBoxLayout(footer); fl.setContentsMargins(18,10,18,10); fl.setSpacing(10); fl.addStretch()
        kaydet_btn = QPushButton("💾  Kaydet"); kaydet_btn.setFixedHeight(36)
        kaydet_btn.setStyleSheet("background:#27ae60; color:white;")
        kaydet_btn.clicked.connect(self.kaydet)
        iptal_btn = QPushButton("İptal"); iptal_btn.setFixedHeight(36)
        iptal_btn.setStyleSheet("background:transparent; color:#7f8c8d; border:1px solid #4a6278;")
        iptal_btn.clicked.connect(self.reject)
        fl.addWidget(kaydet_btn); fl.addWidget(iptal_btn)
        main_layout.addWidget(footer)

        self.load_personeller()

    # ── Personel yükleme / filtreleme ────────────────────────────────────────
    def load_personeller(self):
        self.all_personeller = self.session.query(Personel).filter(
            Personel.durum == "Aktif"
        ).order_by(Personel.ad_soyad).all()
        self._liste_doldur(self.all_personeller)

    def _liste_doldur(self, personeller):
        self.personel_list.clear()
        for p in personeller:
            item = QListWidgetItem(f"{p.ad_soyad}  ({p.sicil_no or '-'})")
            item.setData(Qt.UserRole, p.id)
            self.personel_list.addItem(item)

    def _filtrele(self, text):
        arama = tr_lower(text.strip())
        if not arama:
            self._liste_doldur(self.all_personeller)
            # Boş aramada listeyi gizle (sadece gerektiğinde aç)
            self.personel_list.setVisible(False)
            return
        sonuc = [p for p in self.all_personeller
                 if arama in tr_lower(p.ad_soyad) or
                    (p.sicil_no and arama in tr_lower(p.sicil_no))]
        self._liste_doldur(sonuc)
        # Kullanıcı yazınca sonuçları göster
        self.personel_list.setVisible(bool(sonuc))

    def _personel_secildi(self, item):
        self._secili_personel_id = item.data(Qt.UserRole)
        self.secili_lbl.setText(f"✅  {item.text()}")
        self.secili_lbl.setStyleSheet(
            "color:#2ecc71; font-size:11px; font-weight:bold; background:#0e2a1a; "
            "border:1px solid #27ae60; border-radius:6px; padding:5px 10px;"
        )
        self.personel_list.setVisible(False)
        self.personel_search.clear()

    # ── Tarih / gün senkronizasyonu ──────────────────────────────────────────
    def _bas_degisti(self):
        if self._updating: return
        self._updating = True
        b = self.baslangic_date.get_pydate(); g = self.gun_spin.value()
        bit = b + datetime.timedelta(days=g - 1)
        self.bitis_date.set_date(QDate(bit.year, bit.month, bit.day))
        self._updating = False

    def _gun_degisti(self, g):
        if self._updating: return
        self._updating = True
        b = self.baslangic_date.get_pydate()
        bit = b + datetime.timedelta(days=g - 1)
        self.bitis_date.set_date(QDate(bit.year, bit.month, bit.day))
        self._updating = False

    def _bit_degisti(self):
        if self._updating: return
        self._updating = True
        b = self.baslangic_date.get_pydate(); bit = self.bitis_date.get_pydate()
        if bit >= b: self.gun_spin.setValue((bit - b).days + 1)
        self._updating = False

    # ── İzin türleri ────────────────────────────────────────────────────────
    def load_izin_turleri(self):
        self.izin_turu_combo.clear()
        for t in self.session.query(IzinTuru).all():
            self.izin_turu_combo.addItem(t.ad, t.id)

    # ── Düzenleme modu ───────────────────────────────────────────────────────
    def load_existing_data(self):
        iz = self.izin
        # Personeli seç
        self._secili_personel_id = iz.personel_id
        self.secili_lbl.setText(f"✅  {iz.personel.ad_soyad} ({iz.personel.sicil_no or '-'})")
        self.secili_lbl.setStyleSheet(
            "color:#2ecc71; font-size:11px; font-weight:bold; background:#0e2a1a; "
            "border:1px solid #27ae60; border-radius:6px; padding:5px 10px;"
        )
        # İzin türü
        idx = self.izin_turu_combo.findData(iz.izin_turu_id)
        if idx >= 0: self.izin_turu_combo.setCurrentIndex(idx)
        # Tarihler
        self.baslangic_date.set_date(QDate(iz.baslangic_tarihi.year, iz.baslangic_tarihi.month, iz.baslangic_tarihi.day))
        self.bitis_date.set_date(QDate(iz.bitis_tarihi.year, iz.bitis_tarihi.month, iz.bitis_tarihi.day))
        self.gun_spin.setValue(iz.gun_sayisi or 1)
        if iz.aciklama: self.aciklama_edit.setText(iz.aciklama)

    # ── Kaydet ──────────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.pos().y() <= 56:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)
    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def kaydet(self):
        try:
            pid = getattr(self, '_secili_personel_id', None)
            if not pid:
                ModernMesaj.uyari(self, "Lütfen listeden bir personel seçin.")
                return
            tur_id = self.izin_turu_combo.currentData()
            if not tur_id:
                ModernMesaj.uyari(self, "Lütfen izin türü seçin.")
                return
            bas = self.baslangic_date.get_pydate()
            bit = self.bitis_date.get_pydate()
            if bit < bas:
                ModernMesaj.uyari(self, "Bitiş tarihi başlangıçtan küçük olamaz.")
                return
            gun = self.gun_spin.value()

            if self.izin:
                iz = self.izin
            else:
                iz = Izin()
                self.session.add(iz)

            iz.personel_id = pid
            iz.izin_turu_id = tur_id
            iz.baslangic_tarihi = bas
            iz.bitis_tarihi = bit
            iz.gun_sayisi = gun
            iz.aciklama = self.aciklama_edit.toPlainText()
            iz.durum = "Onay Bekliyor"
            iz.talep_tarihi = datetime.date.today()

            self.session.commit()
            ModernMesaj.basari(self, "İzin kaydedildi.")
            self.accept()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))
