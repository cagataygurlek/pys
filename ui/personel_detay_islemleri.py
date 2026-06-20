# ui/personel_detay_islemleri.py

from PyQt5.QtWidgets import(
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QDoubleSpinBox, QSpinBox,
    QGroupBox, QFrame, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate, QLocale
from database import get_session
from models import Personel, Avans, KasaAcigi, SigaraAcigi, YillikIzin, Izin, Bordro, MaasOdeme, HacizOdeme, Haciz, Puantaj, IzinTuru
from sqlalchemy import func
from ui.utils import ModernMesaj, TarihAlani, make_frameless
from ui.widgets import ToggleSwitch
import datetime
import calendar

# ==================== AVANS/KASA/SİGARA DIALOGU ====================
class AvansKasaSigaraDialog(QDialog):
    def __init__(self, session, personel, tur, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.personel = personel
        self.tur = tur
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(460, 400)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; font-size:12px; }
            QLineEdit, QTextEdit {
                background-color:#34495e; border:1px solid #4a6278; border-radius:6px;
                color:white; padding:8px; font-size:13px;
            }
            QLineEdit:focus, QTextEdit:focus { border-color:#3498db; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a5c38,stop:1 #27ae60);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 12, 0); hdr_lay.setSpacing(12)
        ikon = QLabel({"avans": "💵", "kasa": "💰", "sigara": "🚬"}.get(tur, "📝"))
        ikon.setFixedSize(40, 40); ikon.setAlignment(Qt.AlignCenter)
        ikon.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:20px;font-size:18px;")
        tl = QLabel(f"{self._get_baslik()} Ekle")
        tl.setStyleSheet("color:white;font-size:13px;font-weight:bold;")
        sub = QLabel(f"{personel.ad_soyad} ({personel.sicil_no})")
        sub.setStyleSheet("color:rgba(255,255,255,0.6);font-size:11px;")
        txt = QVBoxLayout(); txt.setSpacing(1); txt.addWidget(tl); txt.addWidget(sub)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.08);color:#ecf0f1;font-size:16px;font-weight:bold;border:none;border-radius:13px;} QPushButton:hover{background:rgba(231,76,60,0.7);color:white;}")
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(ikon); hdr_lay.addLayout(txt); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body); body_lay.setContentsMargins(20, 16, 20, 10); body_lay.setSpacing(12)

        lbl_tur = QLabel(f"{self._get_baslik()} Tutarı (₺):")
        self.tutar_edit = QLineEdit()
        self.tutar_edit.setPlaceholderText("Örn: 1250,50")
        body_lay.addWidget(lbl_tur)
        body_lay.addWidget(self.tutar_edit)

        lbl_tarih = QLabel("Tarih:")
        self.tarih_edit = TarihAlani()
        self.tarih_edit.set_date(QDate.currentDate())
        body_lay.addWidget(lbl_tarih)
        body_lay.addWidget(self.tarih_edit)

        lbl_aciklama = QLabel("Açıklama:")
        self.aciklama_edit = QTextEdit()
        self.aciklama_edit.setFixedHeight(90)
        body_lay.addWidget(lbl_aciklama)
        body_lay.addWidget(self.aciklama_edit)

        outer_lay.addWidget(body, 1)

        footer = QFrame()
        footer.setFixedHeight(54)
        footer.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border:none;border-top:1px solid #1a2a38;}")
        foot_lay = QHBoxLayout(footer); foot_lay.setContentsMargins(16, 8, 16, 8)
        
        kaydet_btn = QPushButton("Kaydet")
        kaydet_btn.setFixedHeight(36)
        kaydet_btn.setCursor(Qt.PointingHandCursor)
        kaydet_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a5c38, stop:1 #27ae60);
                color: white; font-weight: bold; border-radius: 8px; border: none; padding: 0 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0e462a, stop:1 #219a52);
            }
        """)
        kaydet_btn.clicked.connect(self.kaydet)

        iptal_btn = QPushButton("İptal")
        iptal_btn.setFixedHeight(36)
        iptal_btn.setCursor(Qt.PointingHandCursor)
        iptal_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 16px;font-size:12px;} QPushButton:hover{background:#34495e;color:white;}")
        iptal_btn.clicked.connect(self.reject)

        foot_lay.addWidget(kaydet_btn); foot_lay.addWidget(iptal_btn); foot_lay.addStretch()
        outer_lay.addWidget(footer)
        make_frameless(self)

    def _get_baslik(self):
        return {"avans": "Avans", "kasa": "Kasa Açığı", "sigara": "Sigara Açığı"}.get(self.tur, "Kayıt")

    def parse_tutar(self, metin):
        if not metin:
            return 0.0
        metin = metin.replace("₺", "").replace("TL", "").strip()
        metin = metin.replace(".", "")
        metin = metin.replace(",", ".")
        try:
            return float(metin)
        except:
            return 0.0

    def kaydet(self):
        tutar = self.parse_tutar(self.tutar_edit.text())
        if tutar <= 0:
            ModernMesaj.uyari(self, "Geçerli bir tutar girin.")
            return
        tarih = self.tarih_edit.get_pydate()
        aciklama = self.aciklama_edit.toPlainText()
        if self.tur == "avans":
            model = Avans
        elif self.tur == "kasa":
            model = KasaAcigi
        else:
            model = SigaraAcigi
        kayit = model(
            personel_id=self.personel.id,
            tarih=tarih,
            tutar=tutar,
            aciklama=aciklama
        )
        self.session.add(kayit)
        try:
            self.session.commit()
            ModernMesaj.basari(self, f"{self._get_baslik()} eklendi.")
            self.accept()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))


# ==================== SENELİK İZİN DIALOGU (Tanımla + Kullan) ====================
class SenelikIzinDialog(QDialog):
    def __init__(self, session, personel, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.personel = personel
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(580, 540)
        self.init_ui()
        self.mevcut_bilgileri_yukle()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; font-size:12px; }
            QSpinBox, QComboBox {
                background-color:#34495e; border:1px solid #4a6278; border-radius:6px;
                color:white; padding:5px; font-size:13px;
            }
            QGroupBox {
                color:white; border:1px solid #4a6278; border-radius:8px; margin-top:10px;
            }
            QGroupBox::title { color:#bdc3c7; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a5276,stop:1 #3498db);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 12, 0); hdr_lay.setSpacing(12)
        ikon = QLabel("🏖️"); ikon.setFixedSize(40, 40); ikon.setAlignment(Qt.AlignCenter)
        ikon.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:20px;font-size:18px;")
        tl = QLabel("Senelik İzin Tanımla/Kullan")
        tl.setStyleSheet("color:white;font-size:13px;font-weight:bold;")
        sub = QLabel(f"{self.personel.ad_soyad} ({self.personel.sicil_no})")
        sub.setStyleSheet("color:rgba(255,255,255,0.6);font-size:11px;")
        txt = QVBoxLayout(); txt.setSpacing(1); txt.addWidget(tl); txt.addWidget(sub)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.08);color:#ecf0f1;font-size:16px;font-weight:bold;border:none;border-radius:13px;} QPushButton:hover{background:rgba(231,76,60,0.7);color:white;}")
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(ikon); hdr_lay.addLayout(txt); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body); body_lay.setContentsMargins(20, 16, 20, 10); body_lay.setSpacing(12)

        # Tanımlama bölümü
        tanim_grp = QGroupBox("İzin Tanımlama")
        tanim_layout = QVBoxLayout(tanim_grp)

        yil_row = QHBoxLayout()
        yil_lbl = QLabel("Yıl:")
        self.yil_cb = QComboBox()
        for y in range(2020, 2035):
            self.yil_cb.addItem(str(y), y)
        self.yil_cb.setCurrentText(str(datetime.date.today().year))
        self.yil_cb.currentIndexChanged.connect(self.mevcut_bilgileri_yukle)
        yil_row.addWidget(yil_lbl)
        yil_row.addWidget(self.yil_cb)
        tanim_layout.addLayout(yil_row)

        gun_row = QHBoxLayout()
        gun_lbl = QLabel("Tanımlanan İzin Günü:")
        self.gun_spin = QSpinBox()
        self.gun_spin.setRange(0, 365)
        self.gun_spin.setSuffix(" gün")
        gun_row.addWidget(gun_lbl)
        gun_row.addWidget(self.gun_spin)
        tanim_layout.addLayout(gun_row)

        tanim_kaydet_btn = QPushButton("Tanımı Kaydet")
        tanim_kaydet_btn.setFixedHeight(34)
        tanim_kaydet_btn.setCursor(Qt.PointingHandCursor)
        tanim_kaydet_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a5c38, stop:1 #27ae60);
                color: white; font-weight: bold; border-radius: 8px; border: none; padding: 0 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0e462a, stop:1 #219a52);
            }
        """)
        tanim_kaydet_btn.clicked.connect(self.tanim_kaydet)
        tanim_layout.addWidget(tanim_kaydet_btn)

        body_lay.addWidget(tanim_grp)

        # Kullanım bölümü
        kullanim_grp = QGroupBox("İzin Kullanımı")
        kullanim_layout = QVBoxLayout(kullanim_grp)

        kullan_yil_row = QHBoxLayout()
        kullan_yil_lbl = QLabel("Yıl:")
        self.kullan_yil_cb = QComboBox()
        for y in range(2020, 2035):
            self.kullan_yil_cb.addItem(str(y), y)
        self.kullan_yil_cb.setCurrentText(str(datetime.date.today().year))
        kullan_yil_row.addWidget(kullan_yil_lbl)
        kullan_yil_row.addWidget(self.kullan_yil_cb)
        kullanim_layout.addLayout(kullan_yil_row)

        gun_kullan_row = QHBoxLayout()
        kullan_gun_lbl = QLabel("Kullanılacak Gün Sayısı:")
        self.kullan_gun_spin = QSpinBox()
        self.kullan_gun_spin.setRange(1, 365)
        self.kullan_gun_spin.setSuffix(" gün")
        gun_kullan_row.addWidget(kullan_gun_lbl)
        gun_kullan_row.addWidget(self.kullan_gun_spin)
        kullanim_layout.addLayout(gun_kullan_row)

        tarih_row = QHBoxLayout()
        baslangic_lbl = QLabel("Başlangıç Tarihi:")
        self.baslangic_tarihi = TarihAlani()
        self.baslangic_tarihi.set_date(QDate.currentDate())
        bitis_lbl = QLabel("Bitiş Tarihi:")
        self.bitis_tarihi = TarihAlani()
        self.bitis_tarihi.set_date(QDate.currentDate().addDays(1))
        tarih_row.addWidget(baslangic_lbl)
        tarih_row.addWidget(self.baslangic_tarihi)
        tarih_row.addWidget(bitis_lbl)
        tarih_row.addWidget(self.bitis_tarihi)
        kullanim_layout.addLayout(tarih_row)

        kullan_kaydet_btn = QPushButton("İzin Kullanımını Kaydet")
        kullan_kaydet_btn.setFixedHeight(34)
        kullan_kaydet_btn.setCursor(Qt.PointingHandCursor)
        kullan_kaydet_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a5276, stop:1 #3498db);
                color: white; font-weight: bold; border-radius: 8px; border: none; padding: 0 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0e3a5c, stop:1 #2980b9);
            }
        """)
        kullan_kaydet_btn.clicked.connect(self.kullanim_kaydet)
        kullanim_layout.addWidget(kullan_kaydet_btn)

        body_lay.addWidget(kullanim_grp)

        self.kalan_label = QLabel("Kalan izin: -")
        self.kalan_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        body_lay.addWidget(self.kalan_label)

        outer_lay.addWidget(body, 1)

        footer = QFrame()
        footer.setFixedHeight(54)
        footer.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border:none;border-top:1px solid #1a2a38;}")
        foot_lay = QHBoxLayout(footer); foot_lay.setContentsMargins(16, 8, 16, 8)
        kapat_btn = QPushButton("Kapat")
        kapat_btn.setFixedHeight(36)
        kapat_btn.setCursor(Qt.PointingHandCursor)
        kapat_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 16px;font-size:12px;} QPushButton:hover{background:#34495e;color:white;}")
        kapat_btn.clicked.connect(self.accept)
        foot_lay.addStretch(); foot_lay.addWidget(kapat_btn)
        outer_lay.addWidget(footer)

    def mevcut_bilgileri_yukle(self):
        yil = self.yil_cb.currentData()
        yillik = self.session.query(YillikIzin).filter(
            YillikIzin.personel_id == self.personel.id,
            YillikIzin.yil == yil
        ).first()
        if yillik:
            self.gun_spin.setValue(yillik.tanimlanan_izin)
        else:
            self.gun_spin.setValue(0)
        self.kalan_goster()

    def kalan_goster(self):
        yil = self.yil_cb.currentData()
        yillik = self.session.query(YillikIzin).filter(
            YillikIzin.personel_id == self.personel.id,
            YillikIzin.yil == yil
        ).first()
        if yillik:
            kullanilan = self.session.query(func.sum(Izin.gun_sayisi)).filter(
                Izin.personel_id == self.personel.id,
                Izin.durum == "Onaylandı",
                Izin.baslangic_tarihi >= datetime.date(yil, 1, 1),
                Izin.bitis_tarihi <= datetime.date(yil, 12, 31)
            ).scalar() or 0
            kalan = yillik.tanimlanan_izin - kullanilan
            self.kalan_label.setText(f"Kalan izin: {kalan} gün")
        else:
            self.kalan_label.setText("Kalan izin: Tanım yapılmamış")

    def tanim_kaydet(self):
        yil = self.yil_cb.currentData()
        gun = self.gun_spin.value()
        yillik = self.session.query(YillikIzin).filter(
            YillikIzin.personel_id == self.personel.id,
            YillikIzin.yil == yil
        ).first()
        if yillik:
            yillik.tanimlanan_izin = gun
        else:
            yillik = YillikIzin(personel_id=self.personel.id, yil=yil, tanimlanan_izin=gun)
            self.session.add(yillik)
        try:
            self.session.commit()
            ModernMesaj.basari(self, "Senelik izin tanımlandı.")
            self.kalan_goster()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))

    def kullanim_kaydet(self):
        yil = self.kullan_yil_cb.currentData()
        gun = self.kullan_gun_spin.value()
        baslangic = self.baslangic_tarihi.get_pydate()
        bitis = self.bitis_tarihi.get_pydate()
        if gun <= 0:
            ModernMesaj.uyari(self, "Kullanılacak gün sayısı 0'dan büyük olmalı.")
            return
        if not baslangic or not bitis:
            ModernMesaj.uyari(self, "Başlangıç ve bitiş tarihlerini seçin.")
            return
        if bitis < baslangic:
            ModernMesaj.uyari(self, "Bitiş tarihi başlangıç tarihinden küçük olamaz.")
            return
        # Kullanılan gün sayısını kontrol et (yeterli izin var mı?)
        yillik = self.session.query(YillikIzin).filter(
            YillikIzin.personel_id == self.personel.id,
            YillikIzin.yil == yil
        ).first()
        if not yillik:
            ModernMesaj.uyari(self, "Bu yıl için izin tanımı yapılmamış. Önce tanımlayın.")
            return
        kullanilan = self.session.query(func.sum(Izin.gun_sayisi)).filter(
            Izin.personel_id == self.personel.id,
            Izin.durum == "Onaylandı",
            Izin.baslangic_tarihi >= datetime.date(yil, 1, 1),
            Izin.bitis_tarihi <= datetime.date(yil, 12, 31)
        ).scalar() or 0
        if kullanilan + gun > yillik.tanimlanan_izin:
            ModernMesaj.uyari(self, f"Yeterli izin yok. Kalan izin: {yillik.tanimlanan_izin - kullanilan} gün")
            return
        # İzin türü: Senelik İzin
        izin_turu = self.session.query(IzinTuru).filter(IzinTuru.ad == "Senelik İzin").first()
        if not izin_turu:
            izin_turu = IzinTuru(ad="Senelik İzin", renk="#3498db", ucretli_mi=True)
            self.session.add(izin_turu)
            self.session.flush()
            return
        yeni_izin = Izin(
            personel_id=self.personel.id,
            izin_turu_id=izin_turu.id,
            baslangic_tarihi=baslangic,
            bitis_tarihi=bitis,
            gun_sayisi=gun,
            aciklama=f"{yil} yılı senelik izin kullanımı",
            durum="Onaylandı",
            talep_tarihi=datetime.date.today(),
            onaylayan="Admin",
            onay_tarihi=datetime.date.today()
        )
        self.session.add(yeni_izin)
        try:
            self.session.commit()
            ModernMesaj.basari(self, f"{gun} gün izin kullanımı kaydedildi.")
            self.kalan_goster()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))


# ==================== MAAŞ ÖDEMESİ DIALOGU (Bordro seçimli - QLineEdit) ====================
class MaasOdemeDialog(QDialog):
    def __init__(self, session, personel, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.personel = personel
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(520, 440)
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; font-size:12px; }
            QComboBox, QLineEdit, QTextEdit {
                background-color:#34495e; border:1px solid #4a6278; border-radius:6px;
                color:white; padding:6px; font-size:13px;
            }
            QComboBox::drop-down { border:none; }
            QComboBox QAbstractItemView { background:#34495e; color:white; }
            QPushButton { font-weight:bold; border-radius:8px; border:none; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3a2000,stop:1 #e67e22);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 12, 0); hdr_lay.setSpacing(12)
        ic = QLabel("💵"); ic.setFixedSize(40, 40); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:20px;font-size:18px;")
        tl = QLabel(f"Maaş Ödemesi — {personel.ad_soyad}")
        tl.setStyleSheet("color:white;font-size:13px;font-weight:bold;")
        sub = QLabel(personel.sicil_no or "")
        sub.setStyleSheet("color:rgba(255,255,255,0.6);font-size:11px;")
        txt = QVBoxLayout(); txt.setSpacing(1); txt.addWidget(tl); txt.addWidget(sub)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.08);color:#ecf0f1;font-size:16px;font-weight:bold;border:none;border-radius:13px;} QPushButton:hover{background:rgba(231,76,60,0.7);color:white;}")
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(ic); hdr_lay.addLayout(txt); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body); bl.setContentsMargins(20, 14, 20, 10); bl.setSpacing(10)
        outer_lay.addWidget(body, 1)

        bl.addWidget(QLabel("Ödenecek Dönem (Bordro):"))
        self.bordro_cb = QComboBox()
        bordrolar = self.session.query(Bordro).filter(
            Bordro.personel_id == self.personel.id,
            ~Bordro.id.in_(self.session.query(MaasOdeme.bordro_id))
        ).order_by(Bordro.yil.desc(), Bordro.ay.desc()).all()
        for b in bordrolar:
            donem_adi = f"{b.ay:02d}/{b.yil} - Net: {b.toplam_net_maas:,.2f} ₺".replace(",", ".")
            self.bordro_cb.addItem(donem_adi, b.id)
        if bordrolar:
            self.bordro_cb.setCurrentIndex(0)
            self.bordro_cb.currentIndexChanged.connect(self.bordro_secildi)
        bl.addWidget(self.bordro_cb)

        bl.addWidget(QLabel("Ödenecek Tutar (₺):"))
        self.tutar_edit = QLineEdit()
        self.tutar_edit.setPlaceholderText("Örn: 18500,50")
        bl.addWidget(self.tutar_edit)

        bl.addWidget(QLabel("Ödeme Tarihi:"))
        self.tarih_edit = TarihAlani()
        self.tarih_edit.set_date(QDate.currentDate())
        bl.addWidget(self.tarih_edit)

        bl.addWidget(QLabel("Açıklama:"))
        self.aciklama_edit = QTextEdit()
        self.aciklama_edit.setFixedHeight(60)
        bl.addWidget(self.aciklama_edit)

        footer = QFrame()
        footer.setFixedHeight(54)
        footer.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border:none;border-top:1px solid #1a2a38;}")
        fl = QHBoxLayout(footer); fl.setContentsMargins(16, 8, 16, 8)
        kaydet_btn = QPushButton("💾  Ödeme Yap"); kaydet_btn.setFixedHeight(36)
        kaydet_btn.setCursor(Qt.PointingHandCursor)
        kaydet_btn.setStyleSheet("QPushButton{background:#27ae60;color:white;font-weight:bold;border-radius:8px;padding:0 20px;font-size:12px;}QPushButton:hover{background:#2ecc71;}")
        kaydet_btn.clicked.connect(self.kaydet)
        iptal_btn = QPushButton("İptal"); iptal_btn.setFixedHeight(36)
        iptal_btn.setCursor(Qt.PointingHandCursor)
        iptal_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 16px;font-size:12px;}QPushButton:hover{background:#34495e;color:white;}")
        iptal_btn.clicked.connect(self.reject)
        fl.addWidget(kaydet_btn); fl.addStretch(); fl.addWidget(iptal_btn)
        outer_lay.addWidget(footer)

        self.bordro_secildi()

        self.bordro_secildi()

    def bordro_secildi(self):
        bordro_id = self.bordro_cb.currentData()
        if bordro_id:
            bordro = self.session.get(Bordro, bordro_id)
            if bordro:
                self.tutar_edit.setText(f"{bordro.toplam_net_maas:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))

    def parse_tutar(self, metin):
        if not metin:
            return 0.0
        metin = metin.replace("₺", "").replace("TL", "").strip()
        metin = metin.replace(".", "")
        metin = metin.replace(",", ".")
        try:
            return float(metin)
        except:
            return 0.0

    def kaydet(self):
        bordro_id = self.bordro_cb.currentData()
        if not bordro_id:
            ModernMesaj.uyari(self, "Ödenecek dönem seçin.")
            return
        tutar = self.parse_tutar(self.tutar_edit.text())
        if tutar <= 0:
            ModernMesaj.uyari(self, "Geçerli bir tutar girin.")
            return
        tarih = self.tarih_edit.get_pydate()
        aciklama = self.aciklama_edit.toPlainText()
        odeme = MaasOdeme(
            personel_id=self.personel.id,
            bordro_id=bordro_id,
            tarih=tarih,
            tutar=tutar,
            aciklama=aciklama
        )
        self.session.add(odeme)
        try:
            self.session.commit()
            ModernMesaj.basari(self, "Maaş ödemesi kaydedildi.")
            self.accept()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))


# ==================== HACİZ ÖDEMESİ DIALOGU (QLineEdit) ====================
class HacizOdemeDialog(QDialog):
    def __init__(self, session, personel, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.personel = personel
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(500, 460)
        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; font-size:12px; }
            QComboBox, QLineEdit {
                background-color:#34495e; border:1px solid #4a6278; border-radius:6px;
                color:white; padding:6px; font-size:13px;
            }
            QComboBox::drop-down { border:none; }
            QComboBox QAbstractItemView { background:#34495e; color:white; }
            QTextEdit {
                background-color:#34495e; border:1px solid #4a6278; border-radius:6px;
                color:white; padding:6px; font-size:13px;
            }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        lay.addWidget(outer)

        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6c1e1e,stop:1 #c0392b);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 12, 0); hdr_lay.setSpacing(12)
        ikon = QLabel("⚖️"); ikon.setFixedSize(40, 40); ikon.setAlignment(Qt.AlignCenter)
        ikon.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:20px;font-size:18px;")
        tl = QLabel("Haciz Ödemesi Yap")
        tl.setStyleSheet("color:white;font-size:13px;font-weight:bold;")
        sub = QLabel(f"{self.personel.ad_soyad} ({self.personel.sicil_no})")
        sub.setStyleSheet("color:rgba(255,255,255,0.6);font-size:11px;")
        txt = QVBoxLayout(); txt.setSpacing(1); txt.addWidget(tl); txt.addWidget(sub)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.08);color:#ecf0f1;font-size:16px;font-weight:bold;border:none;border-radius:13px;} QPushButton:hover{background:rgba(231,76,60,0.7);color:white;}")
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(ikon); hdr_lay.addLayout(txt); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body); body_lay.setContentsMargins(20, 16, 20, 10); body_lay.setSpacing(12)

        lbl_haciz = QLabel("Haciz Dosyası:")
        self.haciz_cb = QComboBox()
        self.hacizler = self.session.query(Haciz).filter(
            Haciz.personel_id == self.personel.id,
            Haciz.durum == "Aktif",
            Haciz.kalan_borc > 0
        ).all()
        for h in self.hacizler:
            self.haciz_cb.addItem(f"{h.dosya_no} - Kalan: {h.kalan_borc:,.2f} ₺", h.id)
        self.haciz_cb.currentIndexChanged.connect(self.haciz_secildi)
        body_lay.addWidget(lbl_haciz)
        body_lay.addWidget(self.haciz_cb)

        lbl_tutar = QLabel("Ödeme Tutarı (₺):")
        self.tutar_edit = QLineEdit()
        self.tutar_edit.setPlaceholderText("Örn: 18500,50")
        body_lay.addWidget(lbl_tutar)
        body_lay.addWidget(self.tutar_edit)

        lbl_tarih = QLabel("Ödeme Tarihi:")
        self.tarih_edit = TarihAlani()
        self.tarih_edit.set_date(QDate.currentDate())
        body_lay.addWidget(lbl_tarih)
        body_lay.addWidget(self.tarih_edit)

        lbl_aciklama = QLabel("Açıklama:")
        self.aciklama_edit = QTextEdit()
        self.aciklama_edit.setFixedHeight(90)
        body_lay.addWidget(lbl_aciklama)
        body_lay.addWidget(self.aciklama_edit)

        outer_lay.addWidget(body, 1)

        footer = QFrame()
        footer.setFixedHeight(54)
        footer.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border:none;border-top:1px solid #1a2a38;}")
        foot_lay = QHBoxLayout(footer); foot_lay.setContentsMargins(16, 8, 16, 8)

        kaydet_btn = QPushButton("Ödeme Yap")
        kaydet_btn.setFixedHeight(36)
        kaydet_btn.setCursor(Qt.PointingHandCursor)
        kaydet_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6c1e1e, stop:1 #c0392b);
                color: white; font-weight: bold; border-radius: 8px; border: none; padding: 0 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a0a0a, stop:1 #a93226);
            }
        """)
        kaydet_btn.clicked.connect(self.kaydet)

        iptal_btn = QPushButton("İptal")
        iptal_btn.setFixedHeight(36)
        iptal_btn.setCursor(Qt.PointingHandCursor)
        iptal_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 16px;font-size:12px;} QPushButton:hover{background:#34495e;color:white;}")
        iptal_btn.clicked.connect(self.reject)

        foot_lay.addWidget(kaydet_btn); foot_lay.addWidget(iptal_btn); foot_lay.addStretch()
        outer_lay.addWidget(footer)

        self.haciz_secildi()

    def haciz_secildi(self):
        idx = self.haciz_cb.currentIndex()
        if idx >= 0 and idx < len(self.hacizler):
            h = self.hacizler[idx]
            self.tutar_edit.setPlaceholderText(f"Max: {h.kalan_borc:,.2f} ₺".replace(",", "."))

    def parse_tutar(self, metin):
        if not metin:
            return 0.0
        metin = metin.replace("₺", "").replace("TL", "").strip()
        metin = metin.replace(".", "")
        metin = metin.replace(",", ".")
        try:
            return float(metin)
        except:
            return 0.0

    def kaydet(self):
        if self.haciz_cb.count() == 0:
            ModernMesaj.uyari(self, "Bu personele ait aktif haciz bulunamadı.")
            return
        haciz_id = self.haciz_cb.currentData()
        tutar = self.parse_tutar(self.tutar_edit.text())
        if tutar <= 0:
            ModernMesaj.uyari(self, "Geçerli bir tutar girin.")
            return
        tarih = self.tarih_edit.get_pydate()
        aciklama = self.aciklama_edit.toPlainText()
        haciz = self.session.get(Haciz, haciz_id)
        if tutar > haciz.kalan_borc:
            ModernMesaj.uyari(self, f"Ödeme tutarı kalan borçtan ({haciz.kalan_borc:,.2f} ₺) büyük olamaz.")
            return
        odeme = HacizOdeme(
            haciz_id=haciz_id,
            tarih=tarih,
            tutar=tutar,
            aciklama=aciklama
        )
        self.session.add(odeme)
        haciz.kalan_borc -= tutar
        if haciz.kalan_borc <= 0:
            haciz.durum = "Tamamlandı"
        try:
            self.session.commit()
            ModernMesaj.basari(self, "Haciz ödemesi kaydedildi.")
            self.accept()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))


# ==================== BORDRO HESAPLAMA DIALOGU ====================
class BordroHesaplaDialog(QDialog):
    def __init__(self, session, personel, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.personel = personel
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(540, 520)
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; font-size:12px; }
            QComboBox {
                background:#34495e; border:1px solid #4a6278; border-radius:6px;
                color:white; padding:6px 10px; font-size:13px;
            }
            QComboBox:focus { border-color:#f39c12; background:#1a2a38; }
            QComboBox::drop-down { border:none; width:20px; }
            QComboBox::down-arrow { image:none; width:0; height:0;
                border-left:4px solid transparent; border-right:4px solid transparent;
                border-top:5px solid #bdc3c7; }
            QComboBox QAbstractItemView { background:#34495e; color:white;
                selection-background-color:#e67e22; selection-color:white; border:1px solid #4a6278; padding:4px; }
            QPushButton { font-weight:bold; border-radius:8px; border:none; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3a2000,stop:1 #d35400);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 12, 0); hdr_lay.setSpacing(12)
        ic = QLabel("📊"); ic.setFixedSize(40, 40); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:20px;font-size:18px;")
        tl = QLabel(f"Bordro Hesapla — {self.personel.ad_soyad}")
        tl.setStyleSheet("color:white;font-size:13px;font-weight:bold;")
        sub = QLabel(personel.sicil_no or "")
        sub.setStyleSheet("color:rgba(255,255,255,0.6);font-size:11px;")
        txt = QVBoxLayout(); txt.setSpacing(1); txt.addWidget(tl); txt.addWidget(sub)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.08);color:#ecf0f1;font-size:16px;font-weight:bold;border:none;border-radius:13px;} QPushButton:hover{background:rgba(231,76,60,0.7);color:white;}")
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(ic); hdr_lay.addLayout(txt); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body); bl.setContentsMargins(20, 14, 20, 10); bl.setSpacing(12)
        outer_lay.addWidget(body, 1)

        def mk_lbl(t):
            l = QLabel(t)
            l.setStyleSheet("color:#f0b27a;font-size:10px;font-weight:bold;letter-spacing:0.8px;background:transparent;")
            return l

        # Dönem seçimi yan yana
        dr = QHBoxLayout(); dr.setSpacing(12)
        av = QVBoxLayout(); av.setSpacing(4); av.addWidget(mk_lbl("AY"))
        self.ay_cb = QComboBox()
        self.ay_cb.addItems(["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                             "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"])
        self.ay_cb.setCurrentIndex(datetime.date.today().month - 1)
        av.addWidget(self.ay_cb); dr.addLayout(av, 2)

        yv = QVBoxLayout(); yv.setSpacing(4); yv.addWidget(mk_lbl("YIL"))
        self.yil_cb = QComboBox()
        for y in range(2020, 2035): self.yil_cb.addItem(str(y))
        self.yil_cb.setCurrentText(str(datetime.date.today().year))
        yv.addWidget(self.yil_cb); dr.addLayout(yv, 1)
        bl.addLayout(dr)

        # Bilgi kartları
        brut = self.personel.maas or 0
        emekli = "emekli" in (self.personel.aciklama or "").lower()
        resmi = 30181.00 if emekli else 28075.50
        cr = QHBoxLayout(); cr.setSpacing(10)
        for lbl_t, val, renk in [
            ("BRÜT MAAŞ",      f"{brut:,.2f} ₺".replace(",","."),       "#f39c12"),
            ("RESMİ MAAŞ",     f"{resmi:,.2f} ₺".replace(",","."),      "#3498db"),
            ("MAX HACİZ %25",  f"{resmi*0.25:,.2f} ₺".replace(",","."), "#e74c3c"),
        ]:
            krt = QFrame()
            krt.setStyleSheet(f"QFrame{{background:#1a2a38;border:1px solid {renk};border-radius:10px;}}")
            kv = QVBoxLayout(krt); kv.setContentsMargins(12,10,12,10); kv.setSpacing(4)
            l1 = QLabel(lbl_t); l1.setStyleSheet(f"color:{renk};font-size:9px;font-weight:bold;letter-spacing:0.8px;background:transparent;")
            l2 = QLabel(val);   l2.setStyleSheet(f"color:{renk};font-size:13px;font-weight:bold;background:transparent;")
            kv.addWidget(l1); kv.addWidget(l2); cr.addWidget(krt)
        bl.addLayout(cr)

        # Bilgi notu
        gunluk = brut / 30 if brut > 0 else 0
        info = QLabel(
            f"• 'R' (raporlu) günler {gunluk:,.2f} ₺/gün üzerinden kesilir\n"
            f"• 'G' ve 'Ü' kodları devamsızlık kesintisinedir\n"
            f"• Haciz kesintisi resmi maaşın %%25'ini geçemez\n"
            f"• Avans, kasa ve sigara açıkları brütten düşülür"
        )
        info.setStyleSheet(
            "color:#7f8c8d;font-size:11px;background:#1a2a38;"
            "border-radius:8px;padding:10px 14px;line-height:1.6;"
        )
        info.setWordWrap(True)
        bl.addWidget(info)
        outer_lay.addWidget(body, 1)

        footer = QFrame()
        footer.setFixedHeight(54)
        footer.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border:none;border-top:1px solid #1a2a38;}")
        fl = QHBoxLayout(footer); fl.setContentsMargins(16, 8, 16, 8)
        hesapla_btn = QPushButton("📊  Hesapla ve Kaydet"); hesapla_btn.setFixedHeight(36)
        hesapla_btn.setCursor(Qt.PointingHandCursor)
        hesapla_btn.setStyleSheet("QPushButton{background:#e67e22;color:white;font-weight:bold;border-radius:8px;border:none;padding:0 20px;font-size:12px;}QPushButton:hover{background:#d35400;}")
        hesapla_btn.clicked.connect(self.hesapla)
        iptal_btn = QPushButton("İptal"); iptal_btn.setFixedHeight(36)
        iptal_btn.setCursor(Qt.PointingHandCursor)
        iptal_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 16px;font-size:12px;}QPushButton:hover{background:#34495e;color:white;}")
        iptal_btn.clicked.connect(self.reject)
        fl.addWidget(hesapla_btn); fl.addStretch(); fl.addWidget(iptal_btn)
        outer_lay.addWidget(footer)

    def hesapla(self):
        yil = int(self.yil_cb.currentText())
        ay = self.ay_cb.currentIndex() + 1
        ilk_gun = datetime.date(yil, ay, 1)
        son_gun = datetime.date(yil, ay, calendar.monthrange(yil, ay)[1])

        brut = self.personel.maas
        if brut <= 0:
            ModernMesaj.uyari(self, "Personelin maaşı 0 veya negatif.")
            return

        emekli_mi = "emekli" in (self.personel.aciklama or "").lower()
        asgari_normal = 28075.50
        asgari_emekli = 30181.00
        resmi_maas = asgari_emekli if emekli_mi else asgari_normal

        gunluk = brut / 30

        avans_toplam = self.session.query(func.sum(Avans.tutar)).filter(
            Avans.personel_id == self.personel.id,
            Avans.tarih >= ilk_gun,
            Avans.tarih <= son_gun
        ).scalar() or 0.0
        kasa_toplam = self.session.query(func.sum(KasaAcigi.tutar)).filter(
            KasaAcigi.personel_id == self.personel.id,
            KasaAcigi.tarih >= ilk_gun,
            KasaAcigi.tarih <= son_gun
        ).scalar() or 0.0
        sigara_toplam = self.session.query(func.sum(SigaraAcigi.tutar)).filter(
            SigaraAcigi.personel_id == self.personel.id,
            SigaraAcigi.tarih >= ilk_gun,
            SigaraAcigi.tarih <= son_gun
        ).scalar() or 0.0

        puantaj = self.session.query(Puantaj).filter(
            Puantaj.personel_id == self.personel.id,
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
        raporlu_kesinti = raporlu_gun * gunluk
        devamsizlik_kesinti = devamsizlik_gun * gunluk

        diger_kesinti = avans_toplam + kasa_toplam + sigara_toplam + raporlu_kesinti + devamsizlik_kesinti
        net_diger_sonrasi = brut - diger_kesinti
        if net_diger_sonrasi < 0:
            net_diger_sonrasi = 0

        banka_limiti = min(net_diger_sonrasi, resmi_maas)

        aktif_hacizler = self.session.query(Haciz).filter(
            Haciz.personel_id == self.personel.id,
            Haciz.durum == "Aktif",
            Haciz.kalan_borc > 0,
            Haciz.baslangic_tarihi <= son_gun,
            (Haciz.bitis_tarihi >= ilk_gun) | (Haciz.bitis_tarihi == None)
        ).order_by(Haciz.baslangic_tarihi).all()

        toplam_haciz_kesintisi = 0.0
        kalan_butce = banka_limiti
        for haciz in aktif_hacizler:
            if kalan_butce <= 0:
                break
            if haciz.aylik_kesinti and haciz.aylik_kesinti > 0:
                aylik_kesinti = haciz.aylik_kesinti
            else:
                aylik_kesinti = resmi_maas * 0.25
            maks_kesinti = min(haciz.kalan_borc, aylik_kesinti)
            gercek_kesinti = min(maks_kesinti, kalan_butce)
            if gercek_kesinti > 0:
                toplam_haciz_kesintisi += gercek_kesinti
                kalan_butce -= gercek_kesinti

        banka = banka_limiti - toplam_haciz_kesintisi
        if banka < 0:
            banka = 0
        elden = net_diger_sonrasi - banka_limiti
        net_maas = net_diger_sonrasi - toplam_haciz_kesintisi

        bordro = self.session.query(Bordro).filter(
            Bordro.personel_id == self.personel.id,
            Bordro.yil == yil,
            Bordro.ay == ay
        ).first()
        if not bordro:
            bordro = Bordro(personel_id=self.personel.id, yil=yil, ay=ay)
            self.session.add(bordro)
        bordro.toplam_net_maas = net_maas
        bordro.resmi_maas = banka
        bordro.icra_kesintisi = toplam_haciz_kesintisi
        bordro.elden_odenecek = elden

        try:
            self.session.commit()
            ModernMesaj.basari(self, f"Bordro hesaplandı.\nNet Maaş: {net_maas:,.2f} ₺".replace(",", "."))
            self.accept()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))


class EldenOdemeGecmisDialog(QDialog):
    def __init__(self, session, personel, kullanici=None, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.personel = personel
        self.kullanici = kullanici
        self._maas_gizli = False
        if self.kullanici and not self.kullanici.admin:
            yetkili = {y.modul_adi for y in self.kullanici.yetkileri}
            self._maas_gizli = "maas" not in yetkili
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(500, 380)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; }
            QTableWidget { background:#34495e; border:1px solid #4a6278; border-radius:8px; color:white;
                           gridline-color:rgba(255,255,255,0.07); }
            QHeaderView::section { background:#1a2a38; color:#bdc3c7;
                                   font-weight:bold; padding:8px; border:none; }
            QTableWidget::item { padding:5px; }
            QTableWidget::item:selected { background:rgba(52,152,219,0.35); color:white; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a5c38,stop:1 #27ae60);border-top-left-radius:16px;border-top-right-radius:16px;border:none;}")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 12, 0); hdr_lay.setSpacing(12)
        ic = QLabel("📋"); ic.setFixedSize(40, 40); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.15);border-radius:20px;font-size:18px;")
        tl = QLabel("Elden Ödeme Geçmişi")
        tl.setStyleSheet("color:white;font-size:13px;font-weight:bold;")
        sub = QLabel(f"{personel.ad_soyad} ({personel.sicil_no})")
        sub.setStyleSheet("color:rgba(255,255,255,0.6);font-size:11px;")
        txt = QVBoxLayout(); txt.setSpacing(1); txt.addWidget(tl); txt.addWidget(sub)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.08);color:#ecf0f1;font-size:16px;font-weight:bold;border:none;border-radius:13px;} QPushButton:hover{background:rgba(231,76,60,0.7);color:white;}")
        close_btn.clicked.connect(self.close)
        hdr_lay.addWidget(ic); hdr_lay.addLayout(txt); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background:transparent;")
        self.body_lay = QVBoxLayout(body); self.body_lay.setContentsMargins(16, 14, 16, 10); self.body_lay.setSpacing(10)
        outer_lay.addWidget(body, 1)

        self._build_table(self.body_lay)

        footer = QFrame()
        footer.setFixedHeight(54)
        footer.setStyleSheet("QFrame{background:#243342;border-bottom-left-radius:16px;border-bottom-right-radius:16px;border:none;border-top:1px solid #1a2a38;}")
        foot_lay = QHBoxLayout(footer); foot_lay.setContentsMargins(16, 8, 16, 8)
        kapat_btn = QPushButton("Kapat")
        kapat_btn.setFixedHeight(36)
        kapat_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 16px;font-size:12px;} QPushButton:hover{background:#34495e;color:white;}")
        kapat_btn.clicked.connect(self.close)
        foot_lay.addStretch(); foot_lay.addWidget(kapat_btn)
        outer_lay.addWidget(footer)

    def _build_table(self, body_lay):
        odemeler = self.session.query(MaasOdeme).filter(
            MaasOdeme.personel_id == self.personel.id,
            func.lower(MaasOdeme.aciklama).like("%elden%")
        ).order_by(MaasOdeme.tarih).all()

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Tarih", "Tutar", ""])
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed)
        table.setColumnWidth(2, 50)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setRowCount(len(odemeler))
        toplam = 0
        for i, o in enumerate(odemeler):
            table.setRowHeight(i, 36)
            table.setItem(i, 0, QTableWidgetItem(o.tarih.strftime("%d.%m.%Y") if o.tarih else ""))
            if self._maas_gizli:
                item = QTableWidgetItem("*****")
            else:
                item = QTableWidgetItem(f"{o.tutar:,.2f}".replace(",", "."))
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 1, item)
            if not self._maas_gizli:
                toplam += o.tutar

                sil_btn = QPushButton("🗑")
                sil_btn.setFixedSize(34, 26)
                sil_btn.setCursor(Qt.PointingHandCursor)
                sil_btn.setToolTip("Bu ödemeyi sil")
                sil_btn.setStyleSheet("QPushButton{background:#c0392b;color:white;border-radius:4px;border:none;font-size:12px;} QPushButton:hover{background:#e74c3c;}")
                sil_btn.clicked.connect(lambda checked, oid=o.id: self._odeme_sil(oid))
                sil_w = QWidget(); sil_w.setStyleSheet("background:transparent;")
                sil_l = QHBoxLayout(sil_w); sil_l.setContentsMargins(2,2,2,2); sil_l.setAlignment(Qt.AlignCenter)
                sil_l.addWidget(sil_btn)
                table.setCellWidget(i, 2, sil_w)

        body_lay.addWidget(table)

        if self._maas_gizli:
            ozet = QLabel(f"<b style='color:#7f8c8d'>*****</b>  |  {len(odemeler)} ödeme")
        else:
            ozet = QLabel(f"Toplam: <b style='color:#e67e22'>{toplam:,.2f}</b>  |  {len(odemeler)} ödeme")
        ozet.setTextFormat(Qt.RichText)
        ozet.setStyleSheet("color:#bdc3c7;font-size:12px;")
        body_lay.addWidget(ozet)

    def _odeme_sil(self, odeme_id):
        try:
            o = self.session.query(MaasOdeme).get(odeme_id)
            if not o:
                ModernMesaj.uyari(self, "Ödeme kaydı bulunamadı.")
                return
            if not ModernMesaj.soru(self, f"{o.tutar:,.2f} ₺".replace(",", ".") + " tutarındaki elden ödeme silinecek. Onaylıyor musunuz?"):
                return
            self.session.delete(o)
            self.session.commit()
            ModernMesaj.basari(self, "Elden ödeme silindi.")
            for i in reversed(range(self.body_lay.count())):
                item = self.body_lay.itemAt(i)
                if item and item.widget():
                    item.widget().deleteLater()
            self._build_table(self.body_lay)
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))