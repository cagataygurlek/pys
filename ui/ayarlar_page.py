# ui/ayarlar_page.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QLineEdit, QLabel, QMessageBox, QDialog, QFormLayout,
    QFileDialog, QGroupBox, QCheckBox, QComboBox, QSpinBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QGridLayout
)
from PyQt5.QtCore import Qt
import pandas as pd
import os
import hashlib
from database import get_session, get_db_type, get_current_firma, get_current_db_path, load_config, test_postgresql_connection
from models import Sube, Gorev, IzinTuru, SistemAyarlari, Kullanici, KullaniciYetki, KullaniciSube
from ui.utils import ModernMesaj
from backup import backup_database, list_backups, restore_database, clean_old_backups
from ui.widgets import ToggleSwitch
from ui.connection_dialog import ConnectionDialog


class AyarlarPage(QWidget):
    def __init__(self):
        super().__init__()
        self.session = get_session()
        self._yukle_fns = []   # Her sekmenin yukle() fonksiyonları buraya kaydedilir
        self.init_ui()
        self.load_backup_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
            }
            QTabWidget::pane {
                border: 1px solid #4a6278;
                border-radius: 8px;
                background: #2c3e50;
                margin-top: -1px;
                padding: 10px;
            }
            QTabBar::tab {
                background: #34495e;
                border: 1px solid #4a6278;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 7px 10px;
                margin-right: 1px;
                font-weight: bold;
                font-size: 11px;
                color: #bdc3c7;
                min-width: 80px;
                min-height: 34px;
                height: auto;
            }
            QTabBar::tab:selected {
                background: #2c3e50;
                border-bottom: 2px solid #3498db;
                color: #3498db;
            }
            QTabBar::tab:hover {
                background: #3d566e;
                color: white;
            }
            QFrame#card {
                background-color: #34495e;
                border: 1px solid #4a6278;
                border-radius: 12px;
            }
            QLabel#card_title {
                font-size: 13px;
                font-weight: bold;
                color: #ecf0f1;
                background: transparent;
                padding: 0 8px;
            }
            QListWidget {
                border: 1px solid #4a6278;
                border-radius: 8px;
                background-color: #2c3e50;
                color: #ecf0f1;
                font-size: 13px;
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 6px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #3d566e;
            }
            QLineEdit, QComboBox, QSpinBox {
                border: 1px solid #3498db;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #2c3e50;
                color: #ecf0f1;
                font-size: 13px;
                min-height: 24px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #e74c3c;
                background-color: #1a2a38;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background: #2c3e50;
                color: white;
                selection-background-color: #3498db;
                border: 1px solid #4a6278;
            }
            QLabel {
                color: #bdc3c7;
                background: transparent;
                font-size: 12px;
            }
            QPushButton {
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 6px 12px;
                border: none;
                color: white;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QTableWidget {
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: 8px;
                color: #ecf0f1;
                gridline-color: rgba(255,255,255,0.1);
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
                background-color: #3498db;
                color: white;
            }
        """)

        tabs = QTabWidget()
        tabs.setUsesScrollButtons(False)
        tabs.setDocumentMode(True)

        tabs.addTab(self._liste_sekmesi("Şubeler", Sube), "🏢 Şubeler")
        tabs.addTab(self._liste_sekmesi("Görevler", Gorev), "💼 Görevler")
        tabs.addTab(self._liste_sekmesi("İzin Türleri", IzinTuru), "🏖️ İzin Türleri")
        tabs.addTab(self._excel_yedek_sekmesi(), "💾 Excel & Yedekleme")
        tabs.addTab(self._sifre_uretici_sekmesi(), "🔐 Şifre Üreteci")
        tabs.addTab(self._dashboard_ayar_sekmesi(), "📊 Gösterge Paneli")
        tabs.addTab(self._baglanti_sekmesi(), "🔌 Veritabanı Bağlantısı")
        tabs.addTab(self._kullanicilar_sekmesi(), "👥 Kullanıcılar")

        main_layout.addWidget(tabs)

    def _kart(self, baslik, ikon=""):
        """Modern kart container (QFrame + başlık)"""
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        if ikon:
            icon_lbl = QLabel(ikon)
            icon_lbl.setStyleSheet("font-size: 16px; color: #3498db; background: transparent;")
            title_layout.addWidget(icon_lbl)
        title_lbl = QLabel(baslik)
        title_lbl.setObjectName("card_title")
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout.addWidget(content)

        return frame, content

    def _btn(self, text, color, hover=None):
        btn = QPushButton(text)
        btn.setFixedHeight(38)
        btn.setMinimumWidth(140)
        btn.setCursor(Qt.PointingHandCursor)
        hover_c = hover or color
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: white;
                font-weight: bold;
                border-radius: 8px;
                font-size: 12px;
                border: none;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: {hover_c};
            }}
        """)
        return btn

    def _liste_sekmesi(self, baslik, model):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        kart, content = self._kart(baslik)
        klay = QVBoxLayout(content)
        klay.setContentsMargins(0, 0, 0, 0)
        klay.setSpacing(10)

        liste = QListWidget()
        liste.setMinimumHeight(220)
        klay.addWidget(liste)

        row = QHBoxLayout()
        row.setSpacing(8)
        inp = QLineEdit()
        inp.setPlaceholderText(f"Yeni {baslik.capitalize()[:]}...")
        row.addWidget(inp, 1)

        ekle_btn = self._btn("➕ Ekle", "#27ae60", "#2ecc71")
        guncelle_btn = self._btn("✏️ Güncelle", "#f39c12", "#e67e22")
        sil_btn = self._btn("🗑️ Sil", "#e74c3c", "#c0392b")
        row.addWidget(ekle_btn)
        row.addWidget(guncelle_btn)
        row.addWidget(sil_btn)
        klay.addLayout(row)

        lay.addWidget(kart)
        lay.addStretch()

        def yukle():
            liste.clear()
            for item in self.session.query(model).order_by(model.ad).all():
                liste.addItem(item.ad)

        self._yukle_fns.append(yukle)

        def ekle():
            ad = inp.text().strip()
            if not ad:
                ModernMesaj.uyari(widget, "Lütfen bir isim girin.")
                return
            if self.session.query(model).filter(model.ad == ad).first():
                ModernMesaj.uyari(widget, f"'{ad}' zaten mevcut.")
                return
            self.session.add(model(ad=ad))
            self.session.commit()
            inp.clear()
            yukle()
            ModernMesaj.basari(widget, f"'{ad}' eklendi.")

        def guncelle():
            sel = liste.currentItem()
            if not sel:
                ModernMesaj.uyari(widget, "Lütfen güncellenecek kaydı seçin.")
                return
            yeni_ad = inp.text().strip()
            if not yeni_ad:
                ModernMesaj.uyari(widget, "Yeni isim girin.")
                return
            kayit = self.session.query(model).filter(model.ad == sel.text()).first()
            if kayit:
                eski = kayit.ad
                kayit.ad = yeni_ad
                self.session.commit()
                inp.clear()
                yukle()
                ModernMesaj.basari(widget, f"'{eski}' → '{yeni_ad}' güncellendi.")

        def sil():
            sel = liste.currentItem()
            if not sel:
                ModernMesaj.uyari(widget, "Lütfen silinecek kaydı seçin.")
                return
            if not ModernMesaj.soru(widget, f"'{sel.text()}' silinsin mi?"):
                return
            kayit = self.session.query(model).filter(model.ad == sel.text()).first()
            if kayit:
                try:
                    self.session.delete(kayit)
                    self.session.commit()
                    yukle()
                    ModernMesaj.basari(widget, f"'{sel.text()}' silindi.")
                except Exception as e:
                    self.session.rollback()
                    ModernMesaj.hata(widget, f"Silinemedi: {str(e)}")

        ekle_btn.clicked.connect(ekle)
        guncelle_btn.clicked.connect(guncelle)
        sil_btn.clicked.connect(sil)
        liste.itemClicked.connect(lambda i: inp.setText(i.text()))
        yukle()
        return widget

    def _excel_yedek_sekmesi(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        # Excel işlemleri kartı
        excel_kart, excel_content = self._kart("Excel İşlemleri", "📊")
        elay = QHBoxLayout(excel_content)
        elay.setContentsMargins(0, 0, 0, 0)
        elay.setSpacing(10)

        exp_btn = self._btn("📤 Ayarları Dışa Aktar", "#27ae60", "#2ecc71")
        imp_btn = self._btn("📥 Excel'den İçe Aktar", "#e67e22", "#d35400")
        tmpl_btn = self._btn("📄 Şablon İndir", "#3498db", "#2980b9")
        elay.addWidget(exp_btn)
        elay.addWidget(imp_btn)
        elay.addWidget(tmpl_btn)
        lay.addWidget(excel_kart)

        # Yedekleme kartı
        yedek_kart, yedek_content = self._kart("Veritabanı Yedekleme", "💾")
        ylay = QVBoxLayout(yedek_content)
        ylay.setContentsMargins(0, 0, 0, 0)
        ylay.setSpacing(12)

        # Manuel yedek butonları
        btn_row = QHBoxLayout()
        self.manual_backup_btn = self._btn("💾 Şimdi Yedek Al", "#27ae60", "#2ecc71")
        self.show_backups_btn = self._btn("📋 Yedekleri Göster", "#3498db", "#2980b9")
        self.manual_backup_btn.clicked.connect(self.manual_backup)
        self.show_backups_btn.clicked.connect(self.show_backups)
        btn_row.addWidget(self.manual_backup_btn)
        btn_row.addWidget(self.show_backups_btn)
        ylay.addLayout(btn_row)

        # Otomatik yedekleme (ToggleSwitch + QLabel)
        auto_widget = QWidget()
        auto_layout = QHBoxLayout(auto_widget)
        auto_layout.setContentsMargins(0, 0, 0, 0)
        auto_layout.setSpacing(8)
        self.auto_backup_cb = ToggleSwitch(width=50, height=24)
        auto_label = QLabel("Otomatik yedeklemeyi etkinleştir")
        auto_label.setStyleSheet("color: #ecf0f1; background: transparent; font-size: 12px;")
        auto_layout.addWidget(self.auto_backup_cb)
        auto_layout.addWidget(auto_label)
        auto_layout.addStretch()
        ylay.addWidget(auto_widget)

        form_row = QHBoxLayout()
        form_row.setSpacing(16)

        interval_lbl = QLabel("Aralık:")
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["Her kapanışta", "Saatlik", "Günlük", "Haftalık"])
        self.interval_combo.setEnabled(False)
        self.interval_combo.setFixedWidth(160)

        max_lbl = QLabel("Maks. yedek:")
        self.max_backups_spin = QSpinBox()
        self.max_backups_spin.setRange(1, 100)
        self.max_backups_spin.setValue(30)
        self.max_backups_spin.setSuffix(" adet")
        self.max_backups_spin.setFixedWidth(120)

        form_row.addWidget(interval_lbl)
        form_row.addWidget(self.interval_combo)
        form_row.addSpacing(20)
        form_row.addWidget(max_lbl)
        form_row.addWidget(self.max_backups_spin)
        form_row.addStretch()
        ylay.addLayout(form_row)

        from backup import get_backup_folder
        klasor_lbl = QLabel(f"📁 Yedek klasörü: {get_backup_folder()}")
        klasor_lbl.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 4px 0;")
        ylay.addWidget(klasor_lbl)

        lay.addWidget(yedek_kart)
        lay.addStretch()

        self.auto_backup_cb.stateChanged.connect(self.toggle_auto_backup)
        self.interval_combo.currentTextChanged.connect(self.save_backup_settings)
        self.max_backups_spin.valueChanged.connect(self.save_backup_settings)

        return widget

    def _sifre_uretici_sekmesi(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        kart, content = self._kart("Şifre Üreteci", "🔐")
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        # Uzunluk ayarı
        uzunluk_layout = QHBoxLayout()
        uzunluk_layout.setSpacing(10)
        uzunluk_layout.addWidget(QLabel("Şifre Uzunluğu:"))
        self.sifre_uzunluk = QSpinBox()
        self.sifre_uzunluk.setRange(6, 32)
        self.sifre_uzunluk.setValue(6)
        self.sifre_uzunluk.setFixedWidth(70)
        uzunluk_layout.addWidget(self.sifre_uzunluk)
        uzunluk_layout.addStretch()
        layout.addLayout(uzunluk_layout)

        # Karakter seçenekleri (ToggleSwitch + QLabel)
        self.chk_upper = ToggleSwitch(width=50, height=24)
        self.chk_lower = ToggleSwitch(width=50, height=24)
        self.chk_digits = ToggleSwitch(width=50, height=24)
        self.chk_symbols = ToggleSwitch(width=50, height=24)
        self.chk_digits.setChecked(True)

        option_layout = QGridLayout()
        option_layout.setSpacing(8)
        option_layout.addWidget(self._toggle_label("Büyük Harf (A-Z)", self.chk_upper), 0, 0)
        option_layout.addWidget(self._toggle_label("Küçük Harf (a-z)", self.chk_lower), 0, 1)
        option_layout.addWidget(self._toggle_label("Rakam (0-9)", self.chk_digits), 1, 0)
        option_layout.addWidget(self._toggle_label("Özel Karakter (!@#$%^&*)", self.chk_symbols), 1, 1)
        layout.addLayout(option_layout)

        # Şifre gösterim alanı
        self.sifre_goster = QLineEdit()
        self.sifre_goster.setReadOnly(True)
        self.sifre_goster.setPlaceholderText("Şifre burada görünecek...")
        self.sifre_goster.setStyleSheet("""
            QLineEdit {
                background-color: #2c3e50;
                border: 2px solid #3498db;
                border-radius: 8px;
                color: #2ecc71;
                font-size: 16px;
                font-weight: bold;
                font-family: monospace;
                padding: 10px;
            }
        """)
        layout.addWidget(self.sifre_goster)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.uretilen_btn = self._btn("🔄 Yeni Şifre", "#27ae60")
        self.uretilen_btn.clicked.connect(self.sifre_uret)

        self.kopyala_btn = self._btn("📋 Kopyala", "#3498db")
        self.kopyala_btn.clicked.connect(self.sifre_kopyala)

        btn_layout.addWidget(self.uretilen_btn)
        btn_layout.addWidget(self.kopyala_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        lay.addWidget(kart)
        lay.addStretch()

        self.sifre_uret()
        return widget

    def _dashboard_ayar_sekmesi(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        kart, content = self._kart("Gösterge Paneli – Kayar Slider", "📊")
        layout = QVBoxLayout(content)
        layout.setSpacing(16)

        # Slider hızı
        hiz_layout = QHBoxLayout()
        hiz_layout.setSpacing(10)
        hiz_layout.addWidget(QLabel("Slider geçiş süresi (saniye):"))
        self.slider_hiz = QSpinBox()
        self.slider_hiz.setRange(2, 60)
        self.slider_hiz.setValue(8)
        self.slider_hiz.setSuffix(" sn")
        self.slider_hiz.setFixedWidth(100)
        hiz_layout.addWidget(self.slider_hiz)
        hiz_layout.addWidget(QLabel("(Her sayfada bekleme süresi)"))
        hiz_layout.addStretch()
        layout.addLayout(hiz_layout)

        # Kaydet butonu
        btn_layout = QHBoxLayout()
        kaydet_btn = self._btn("💾 Kaydet", "#27ae60")
        kaydet_btn.clicked.connect(self._slider_hiz_kaydet)
        btn_layout.addWidget(kaydet_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

        # Bilgi kartı
        info = QLabel("Bu ayar, Gösterge Paneli'ndeki görev istatistikleri slider'ının\n"
                      "her sayfada ne kadar süre bekleyeceğini belirler.")
        info.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 8px; "
                           "background: #2c3e50; border: 1px solid #4a6278; border-radius: 6px;")
        layout.addWidget(info)

        lay.addWidget(kart)
        lay.addStretch()

        # Kayıtlı değeri yükle
        self._slider_hiz_yukle()
        return widget

    def _slider_hiz_yukle(self):
        ayar = self.session.query(SistemAyarlari).filter_by(anahtar='dashboard_slider_speed').first()
        if ayar and ayar.deger:
            try:
                self.slider_hiz.setValue(int(ayar.deger))
            except Exception:
                pass

    def _slider_hiz_kaydet(self):
        value = self.slider_hiz.value()
        ayar = self.session.query(SistemAyarlari).filter_by(anahtar='dashboard_slider_speed').first()
        if not ayar:
            ayar = SistemAyarlari(anahtar='dashboard_slider_speed')
            self.session.add(ayar)
        ayar.deger = str(value)
        self.session.commit()

        # Canlı uygula
        mw = self.window()
        if hasattr(mw, 'dashboard_page'):
            try:
                mw.dashboard_page._load_slider_speed()
                ModernMesaj.basari(self, "Slider hızı güncellendi.")
                return
            except Exception:
                pass

        # Canlı uygulanamazsa restart öner
        from PyQt5.QtWidgets import QApplication
        import sys
        from PyQt5.QtCore import QProcess
        if ModernMesaj.soru(self, "Ayarların uygulanması için programın yeniden başlatılması gerekiyor. Şimdi yeniden başlatmak istiyor musunuz?"):
            QProcess.startDetached(sys.executable, sys.argv)
            QApplication.quit()

    def _baglanti_sekmesi(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        kart, content = self._kart("Veritabanı Bağlantı Ayarları", "🔌")
        cl = QVBoxLayout(content)
        cl.setSpacing(12)

        # Mevcut bağlantı bilgisi
        db_type = get_db_type()
        firma = get_current_firma()
        db_path = get_current_db_path()

        info_style = "color: #bdc3c7; font-size: 12px; background: #34495e; padding: 12px; border-radius: 8px;"
        info = QLabel()
        if db_type == "postgresql":
            info.setText(
                f"🐘 PostgreSQL (Ağ)\n"
                f"Firma: {firma}\n"
                f"Bağlantı: {db_path}"
            )
        else:
            info.setText(
                f"💾 SQLite (Yerel)\n"
                f"Firma: {firma}\n"
                f"Dosya: {db_path}"
            )
        info.setStyleSheet(info_style)
        info.setWordWrap(True)
        cl.addWidget(info)

        # Bağlantı değiştirme butonu
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        degistir_btn = self._btn("🔄 Bağlantı Değiştir", "#e67e22")
        degistir_btn.clicked.connect(self._baglanti_degistir)
        btn_row.addWidget(degistir_btn)

        if db_type == "postgresql":
            test_btn = self._btn("🔄 Test Et", "#3498db")
            test_btn.clicked.connect(self._pg_test_baglanti)
            btn_row.addWidget(test_btn)

        btn_row.addStretch()
        cl.addLayout(btn_row)

        # Bilgi notu
        not1 = QLabel(
            "SQLite: Tek kullanıcı, yerel çalışma.\n"
            "PostgreSQL: Çok kullanıcı, ağ üzerinden paylaşımlı kullanım.\n\n"
            "📌 PostgreSQL'e geçiş için 'Bağlantı Değiştir'e tıklayın.\n"
            "📌 SQLite verilerinizi PostgreSQL'e taşımak için pg_migration.py kullanın.\n"
            "📌 JSON ayar dosyaları artık her kullanıcı için ayrı saklanır (%APPDATA%/PYS/configs)."
        )
        not1.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 8px; "
                            "background: #2c3e50; border: 1px solid #4a6278; border-radius: 6px;")
        not1.setWordWrap(True)
        cl.addWidget(not1)

        lay.addWidget(kart)
        lay.addStretch()
        return widget

    MODULLER = [
        ("dashboard", "📊 Dashboard"),
        ("personel", "👥 Personel"),
        ("personel_duzenle", "✏️ Personel Düzenleme"),
        ("personel_guncelle", "🔄 Bilgi Güncelleme"),
        ("izin", "🏖️ İzin Yönetimi"),
        ("puantaj", "📅 Puantaj"),
        ("bordro", "💰 Bordro"),
        ("avans", "💸 Avans Görme"),
        ("avans_ekle", "💸 Avans Ekleme"),
        ("avans_duzenle", "✏️ Avans Düzenleme"),
        ("kasa", "💰 Kasa Açığı Görme"),
        ("kasa_ekle", "💰 Kasa Açığı Ekleme"),
        ("kasa_duzenle", "✏️ Kasa Açığı Düzenleme"),
        ("sigara", "🚬 Sigara Açığı Görme"),
        ("sigara_ekle", "🚬 Sigara Açığı Ekleme"),
        ("sigara_duzenle", "✏️ Sigara Açığı Düzenleme"),
        ("haciz", "⚖️ Haciz"),
        ("basvuru", "📋 Başvurular"),
        ("ayarlar", "⚙️ Ayarlar"),
        ("maas", "💰 Maaş Görme"),
    ]

    def _kullanicilar_sekmesi(self):
        import hashlib as _hl
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        kart, content = self._kart("Kullanıcı Yönetimi")
        klay = QVBoxLayout(content)
        klay.setContentsMargins(0, 0, 0, 0)
        klay.setSpacing(10)

        self.kullanici_table = QTableWidget()
        self.kullanici_table.setColumnCount(5)
        self.kullanici_table.setHorizontalHeaderLabels(["Kullanıcı Adı", "Ad Soyad", "Admin", "Aktif", "Oluşturma"])
        self.kullanici_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.kullanici_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.kullanici_table.verticalHeader().setVisible(False)
        self.kullanici_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.kullanici_table.doubleClicked.connect(lambda: self._kullanici_duzenle())
        klay.addWidget(self.kullanici_table)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        ekle_btn = self._btn("➕ Yeni Kullanıcı", "#27ae60", "#2ecc71")
        ekle_btn.clicked.connect(self._kullanici_ekle)
        duzenle_btn = self._btn("✏️ Düzenle / Yetki Ata", "#f39c12", "#e67e22")
        duzenle_btn.clicked.connect(self._kullanici_duzenle)
        sil_btn = self._btn("🗑️ Sil", "#e74c3c", "#c0392b")
        sil_btn.clicked.connect(self._kullanici_sil)
        btn_row.addWidget(ekle_btn)
        btn_row.addWidget(duzenle_btn)
        btn_row.addWidget(sil_btn)
        btn_row.addStretch()
        klay.addLayout(btn_row)

        lay.addWidget(kart)
        lay.addStretch()

        def yukle():
            self.kullanici_table.setRowCount(0)
            for k in self.session.query(Kullanici).order_by(Kullanici.username).all():
                row = self.kullanici_table.rowCount()
                self.kullanici_table.insertRow(row)
                self.kullanici_table.setItem(row, 0, QTableWidgetItem(k.username))
                self.kullanici_table.setItem(row, 1, QTableWidgetItem(k.ad_soyad))
                self.kullanici_table.setItem(row, 2, QTableWidgetItem("✅" if k.admin else "—"))
                self.kullanici_table.setItem(row, 3, QTableWidgetItem("✅" if k.aktif else "❌"))
                self.kullanici_table.setItem(row, 4, QTableWidgetItem(
                    k.olusturma_tarihi.strftime("%d.%m.%Y") if k.olusturma_tarihi else "—"))
                self.kullanici_table.setRowHeight(row, 32)
                self.kullanici_table.item(row, 0).setData(Qt.UserRole, k.id)

        self._yukle_fns.append(yukle)
        yukle()

        return widget

    def _kullanici_ekle(self):
        self._kullanici_dialog()

    def _kullanici_duzenle(self):
        sel = self.kullanici_table.currentRow()
        if sel < 0:
            ModernMesaj.uyari(self, "Lütfen bir kullanıcı seçin.")
            return
        kid = self.kullanici_table.item(sel, 0).data(Qt.UserRole)
        kullanici = self.session.query(Kullanici).get(kid)
        if kullanici:
            self._kullanici_dialog(kullanici)

    def _kullanici_sil(self):
        sel = self.kullanici_table.currentRow()
        if sel < 0:
            ModernMesaj.uyari(self, "Lütfen bir kullanıcı seçin.")
            return
        kid = self.kullanici_table.item(sel, 0).data(Qt.UserRole)
        kullanici = self.session.query(Kullanici).get(kid)
        if not kullanici:
            return
        if kullanici.admin and self.session.query(Kullanici).filter(Kullanici.admin == True, Kullanici.id != kid).count() == 0:
            ModernMesaj.uyari(self, "Son admin kullanıcısı silinemez.")
            return
        if not ModernMesaj.soru(self, f"'{kullanici.ad_soyad}' kullanıcısı silinsin mi?"):
            return
        self.session.delete(kullanici)
        self.session.commit()
        ModernMesaj.basari(self, "Kullanıcı silindi.")
        for fn in self._yukle_fns:
            fn()

    def _kullanici_dialog(self, mevcut_kullanici=None):
        import hashlib as _hl
        from ui.utils import make_frameless, make_header

        dugme = "Güncelle" if mevcut_kullanici else "Ekle"
        dlg = QDialog(self, Qt.Dialog | Qt.FramelessWindowHint)
        dlg.setAttribute(Qt.WA_TranslucentBackground)
        dlg.setFixedSize(680, 860)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        outer = QFrame(dlg)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer { background:#2c3e50; border-radius:16px; border:1px solid #4a6278; }
            QLabel { background:transparent; color:#ecf0f1; }
            QLineEdit { background:#1a2a38; border:1px solid #4a6278; border-radius:8px;
                        color:white; padding:10px 14px; font-size:13px; }
            QLineEdit:focus { border-color:#3498db; }
            QCheckBox { color:#ecf0f1; background:transparent; spacing:8px; font-size:12px; }
            QCheckBox::indicator { width:20px; height:20px; border-radius:5px; border:1px solid #4a6278;
                                   background:#1a2a38; }
            QCheckBox::indicator:checked { background:#3498db; border-color:#3498db; }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        root.addWidget(outer)

        make_frameless(dlg, header_height=52)

        hdr, close_btn = make_header("👤", f"Kullanıcı {dugme}", "#1a3a5c", "#2980b9", dlg)
        close_btn.clicked.connect(dlg.reject)
        outer_lay.addWidget(hdr)

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(28, 20, 28, 16)
        body_lay.setSpacing(10)
        outer_lay.addWidget(body, 1)

        form = QGridLayout()
        form.setSpacing(10)

        lbl_style = "color:#bdc3c7;font-size:11px;font-weight:bold;"

        form.addWidget(QLabel("Kullanıcı Adı"), 0, 0)
        username_inp = QLineEdit()
        username_inp.setPlaceholderText("Kullanıcı adı...")
        username_inp.setFixedHeight(38)
        if mevcut_kullanici:
            username_inp.setText(mevcut_kullanici.username)
            username_inp.setEnabled(False)
        form.addWidget(username_inp, 0, 1)

        form.addWidget(QLabel("Ad Soyad"), 1, 0)
        adsoyad_inp = QLineEdit()
        adsoyad_inp.setPlaceholderText("Ad Soyad...")
        adsoyad_inp.setFixedHeight(38)
        if mevcut_kullanici:
            adsoyad_inp.setText(mevcut_kullanici.ad_soyad)
        form.addWidget(adsoyad_inp, 1, 1)

        form.addWidget(QLabel("Şifre"), 2, 0)
        sifre_inp = QLineEdit()
        sifre_inp.setEchoMode(QLineEdit.Password)
        sifre_inp.setPlaceholderText("Şifre..." + (" (değiştirmek için doldurun)" if mevcut_kullanici else ""))
        sifre_inp.setFixedHeight(38)
        form.addWidget(sifre_inp, 2, 1)

        form.addWidget(QLabel("Şifre (Tekrar)"), 3, 0)
        sifre2_inp = QLineEdit()
        sifre2_inp.setEchoMode(QLineEdit.Password)
        sifre2_inp.setPlaceholderText("Şifre tekrar...")
        sifre2_inp.setFixedHeight(38)
        form.addWidget(sifre2_inp, 3, 1)

        admin_cb = QCheckBox("Admin Yetkisi")
        if mevcut_kullanici and mevcut_kullanici.admin:
            admin_cb.setChecked(True)
        form.addWidget(admin_cb, 4, 0, 1, 2)

        aktif_cb = QCheckBox("Aktif Kullanıcı")
        aktif_cb.setChecked(True if not mevcut_kullanici else mevcut_kullanici.aktif)
        form.addWidget(aktif_cb, 5, 0, 1, 2)

        body_lay.addLayout(form)

        yetki_title = QLabel("Modül Yetkileri")
        yetki_title.setStyleSheet("font-size:12px; font-weight:bold; color:#bdc3c7; margin-top:4px;")
        body_lay.addWidget(yetki_title)

        yetki_frame = QFrame()
        yetki_frame.setStyleSheet("QFrame{background:#1a2a38;border-radius:10px;padding:10px;}")
        yetki_lay = QGridLayout(yetki_frame)
        yetki_lay.setSpacing(8)
        yetki_lay.setContentsMargins(12, 12, 12, 12)

        yetki_cbs = {}
        mevcut_yetkiler = set()
        if mevcut_kullanici:
            for y in mevcut_kullanici.yetkileri:
                mevcut_yetkiler.add(y.modul_adi)

        for i, (modul_kodu, modul_adi) in enumerate(self.MODULLER):
            cb = QCheckBox(modul_adi)
            cb.setStyleSheet("QCheckBox{font-size:12px;spacing:8px;} QCheckBox::indicator{width:18px;height:18px;}")
            if mevcut_kullanici and mevcut_kullanici.admin:
                cb.setChecked(True)
                cb.setEnabled(False)
            elif modul_kodu in mevcut_yetkiler:
                cb.setChecked(True)
            yetki_cbs[modul_kodu] = cb
            yetki_lay.addWidget(cb, i // 3, i % 3)

        if mevcut_kullanici and mevcut_kullanici.admin:
            admin_info = QLabel("(Admin tüm modüllere erişebilir)")
            admin_info.setStyleSheet("color:#7f8c8d;font-size:10px;")
            yetki_lay.addWidget(admin_info, (len(self.MODULLER) // 3) + 1, 0, 1, 3)

        body_lay.addWidget(yetki_frame)

        sube_title = QLabel("Şube Yetkileri")
        sube_title.setStyleSheet("font-size:12px; font-weight:bold; color:#bdc3c7; margin-top:4px;")
        body_lay.addWidget(sube_title)

        tum_subeler = self.session.query(Sube).order_by(Sube.ad).all()

        sube_frame = QFrame()
        sube_frame.setStyleSheet("QFrame{background:#1a2a38;border-radius:10px;padding:10px;}")
        sube_lay = QGridLayout(sube_frame)
        sube_lay.setSpacing(8)
        sube_lay.setContentsMargins(12, 12, 12, 12)

        sube_cbs = {}
        mevcut_sube_ids = set()
        if mevcut_kullanici:
            for s in mevcut_kullanici.subeleri:
                mevcut_sube_ids.add(s.sube_id)

        if tum_subeler:
            for i, sube in enumerate(tum_subeler):
                cb = QCheckBox(sube.ad)
                cb.setStyleSheet("QCheckBox{font-size:12px;spacing:8px;} QCheckBox::indicator{width:18px;height:18px;}")
                if mevcut_kullanici and mevcut_kullanici.admin:
                    cb.setChecked(True)
                    cb.setEnabled(False)
                elif sube.id in mevcut_sube_ids:
                    cb.setChecked(True)
                sube_cbs[sube.id] = cb
                sube_lay.addWidget(cb, i // 3, i % 3)
        else:
            no_sube = QLabel("Henüz şube eklenmemiş")
            no_sube.setStyleSheet("color:#7f8c8d;font-style:italic;font-size:11px;")
            sube_lay.addWidget(no_sube, 0, 0)

        if mevcut_kullanici and mevcut_kullanici.admin:
            admin_sube_info = QLabel("(Admin tüm şubelere erişebilir)")
            admin_sube_info.setStyleSheet("color:#7f8c8d;font-size:10px;")
            sube_lay.addWidget(admin_sube_info, (len(tum_subeler) // 3) + 1, 0, 1, 3)

        body_lay.addWidget(sube_frame)

        admin_cb.stateChanged.connect(lambda: self._admin_changed(admin_cb, yetki_cbs, sube_cbs))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()
        iptal_btn = QPushButton("İptal")
        iptal_btn.setFixedHeight(40)
        iptal_btn.setFixedWidth(100)
        iptal_btn.setCursor(Qt.PointingHandCursor)
        iptal_btn.setStyleSheet("""
            QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;font-size:12px;font-weight:bold;}
            QPushButton:hover{background:#34495e;color:white;}
        """)
        iptal_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(iptal_btn)
        kaydet_btn = QPushButton(f"💾 {dugme}")
        kaydet_btn.setFixedHeight(40)
        kaydet_btn.setFixedWidth(140)
        kaydet_btn.setCursor(Qt.PointingHandCursor)
        kaydet_btn.setStyleSheet("""
            QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1e8449,stop:1 #27ae60);color:white;font-weight:bold;border:none;border-radius:8px;font-size:12px;}
            QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #196f3d,stop:1 #229954);}
        """)
        btn_row.addWidget(kaydet_btn)
        body_lay.addLayout(btn_row)

        def kaydet():
            username = username_inp.text().strip()
            adsoyad = adsoyad_inp.text().strip()
            sifre = sifre_inp.text()
            sifre2 = sifre2_inp.text()

            if not username:
                ModernMesaj.uyari(dlg, "Kullanıcı adı gereklidir.")
                return
            if not adsoyad:
                ModernMesaj.uyari(dlg, "Ad Soyad gereklidir.")
                return
            if not mevcut_kullanici and not sifre:
                ModernMesaj.uyari(dlg, "Şifre gereklidir.")
                return
            if sifre and sifre != sifre2:
                ModernMesaj.uyari(dlg, "Şifreler uyuşmuyor.")
                return
            if sifre and len(sifre) < 6:
                ModernMesaj.uyari(dlg, "Şifre en az 6 karakter olmalıdır.")
                return

            if mevcut_kullanici:
                mevcut_kullanici.ad_soyad = adsoyad
                mevcut_kullanici.admin = admin_cb.isChecked()
                mevcut_kullanici.aktif = aktif_cb.isChecked()
                if sifre:
                    mevcut_kullanici.password_hash = _hl.sha256(sifre.encode()).hexdigest()
                hedef = mevcut_kullanici
            else:
                var_mi = self.session.query(Kullanici).filter(Kullanici.username == username).first()
                if var_mi:
                    ModernMesaj.uyari(dlg, f"'{username}' kullanıcı adı zaten mevcut.")
                    return
                hedef = Kullanici(
                    username=username,
                    password_hash=_hl.sha256(sifre.encode()).hexdigest(),
                    ad_soyad=adsoyad,
                    admin=admin_cb.isChecked(),
                    aktif=aktif_cb.isChecked()
                )
                self.session.add(hedef)
                self.session.flush()

            self.session.query(KullaniciYetki).filter(KullaniciYetki.kullanici_id == hedef.id).delete()
            if not admin_cb.isChecked():
                for modul_kodu, cb in yetki_cbs.items():
                    if cb.isChecked():
                        self.session.add(KullaniciYetki(kullanici_id=hedef.id, modul_adi=modul_kodu))

            self.session.query(KullaniciSube).filter(KullaniciSube.kullanici_id == hedef.id).delete()
            if not admin_cb.isChecked():
                for sube_id, cb in sube_cbs.items():
                    if cb.isChecked():
                        self.session.add(KullaniciSube(kullanici_id=hedef.id, sube_id=sube_id))

            self.session.commit()
            ModernMesaj.basari(dlg, f"Kullanıcı {dugme.lower()} başarıyla.")
            dlg.accept()
            for fn in self._yukle_fns:
                fn()

        kaydet_btn.clicked.connect(kaydet)
        dlg.exec_()

    def _admin_changed(self, admin_cb, yetki_cbs, sube_cbs=None):
        is_admin = admin_cb.isChecked()
        for cb in yetki_cbs.values():
            cb.setChecked(is_admin)
            cb.setEnabled(not is_admin)
        if sube_cbs:
            for cb in sube_cbs.values():
                cb.setChecked(is_admin)
                cb.setEnabled(not is_admin)

    def _baglanti_degistir(self):
        dialog = ConnectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.selected_type == "postgresql" and dialog.selected_db:
                from database import set_database
                set_database(dialog.selected_db)
                ModernMesaj.basari(self, "PostgreSQL bağlantısı kuruldu. Program yeniden başlatılıyor...")
                from PyQt5.QtWidgets import QApplication
                import sys
                from PyQt5.QtCore import QProcess
                QProcess.startDetached(sys.executable, sys.argv)
                QApplication.quit()
            else:
                ModernMesaj.basari(self, "SQLite moduna geçildi. Firma seçim ekranına yönlendiriliyorsunuz.")
                from database import set_database
                from ui.firma_secim_dialog import FirmaSecimDialog
                d = FirmaSecimDialog(parent=self)
                if d.exec_() == QDialog.Accepted:
                    set_database(d.selected_db)
                    from PyQt5.QtWidgets import QApplication
                    import sys
                    from PyQt5.QtCore import QProcess
                    QProcess.startDetached(sys.executable, sys.argv)
                    QApplication.quit()

    def _pg_test_baglanti(self):
        config = load_config()
        pg = config.get("postgresql", {})
        ok, msg = test_postgresql_connection(
            pg.get("host", "localhost"),
            pg.get("port", 5432),
            pg.get("database", "pys"),
            pg.get("user", "postgres"),
            pg.get("password", "")
        )
        if ok:
            ModernMesaj.basari(self, f"✅ {msg}")
        else:
            ModernMesaj.hata(self, f"❌ {msg}")

    def _toggle_label(self, text, toggle):
        """ToggleSwitch ve yanında metin içeren widget oluşturur"""
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.addWidget(toggle)
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #ecf0f1; background: transparent; font-size: 12px;")
        h.addWidget(lbl)
        h.addStretch()
        return w

    # -------------------- Excel İşlemleri --------------------
    def excel_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Ayarları Dışa Aktar", "Ayarlar.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            with pd.ExcelWriter(path, engine='openpyxl') as writer:
                subeler = self.session.query(Sube).all()
                df_sube = pd.DataFrame([(s.id, s.ad) for s in subeler], columns=["ID", "Ad"])
                df_sube.to_excel(writer, sheet_name="Subeler", index=False)

                gorevler = self.session.query(Gorev).all()
                df_gorev = pd.DataFrame([(g.id, g.ad) for g in gorevler], columns=["ID", "Ad"])
                df_gorev.to_excel(writer, sheet_name="Gorevler", index=False)

                izinler = self.session.query(IzinTuru).all()
                df_izin = pd.DataFrame([(i.id, i.ad, i.renk, i.ucretli_mi) for i in izinler],
                                        columns=["ID", "Ad", "Renk", "UcretliMi"])
                df_izin.to_excel(writer, sheet_name="IzinTurleri", index=False)

            ModernMesaj.basari(self, "Ayarlar Excel dosyasına aktarıldı.")
        except Exception as e:
            ModernMesaj.hata(self, f"Aktarım hatası: {str(e)}")

    def excel_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            excel_file = pd.ExcelFile(path)
            if "Subeler" in excel_file.sheet_names:
                df = pd.read_excel(excel_file, "Subeler")
                for _, row in df.iterrows():
                    if pd.notna(row.get("Ad")):
                        ad = str(row["Ad"]).strip()
                        if pd.notna(row.get("ID")):
                            obj = self.session.get(Sube, int(row["ID"]))
                            if obj:
                                obj.ad = ad
                            else:
                                self.session.add(Sube(ad=ad))
                        else:
                            self.session.add(Sube(ad=ad))

            if "Gorevler" in excel_file.sheet_names:
                df = pd.read_excel(excel_file, "Gorevler")
                for _, row in df.iterrows():
                    if pd.notna(row.get("Ad")):
                        ad = str(row["Ad"]).strip()
                        if pd.notna(row.get("ID")):
                            obj = self.session.get(Gorev, int(row["ID"]))
                            if obj:
                                obj.ad = ad
                            else:
                                self.session.add(Gorev(ad=ad))
                        else:
                            self.session.add(Gorev(ad=ad))

            if "IzinTurleri" in excel_file.sheet_names:
                df = pd.read_excel(excel_file, "IzinTurleri")
                for _, row in df.iterrows():
                    if pd.notna(row.get("Ad")):
                        ad = str(row["Ad"]).strip()
                        renk = row.get("Renk") if pd.notna(row.get("Renk")) else "#3498db"
                        ucretli = bool(row.get("UcretliMi")) if pd.notna(row.get("UcretliMi")) else True
                        if pd.notna(row.get("ID")):
                            obj = self.session.get(IzinTuru, int(row["ID"]))
                            if obj:
                                obj.ad = ad
                                obj.renk = renk
                                obj.ucretli_mi = ucretli
                            else:
                                self.session.add(IzinTuru(ad=ad, renk=renk, ucretli_mi=ucretli))
                        else:
                            self.session.add(IzinTuru(ad=ad, renk=renk, ucretli_mi=ucretli))

            self.session.commit()
            self.refresh_all_panels()
            ModernMesaj.basari(self, "Excel dosyası başarıyla içe aktarıldı.")
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, f"İçe aktarma hatası: {str(e)}")

    def download_template(self):
        path, _ = QFileDialog.getSaveFileName(self, "Şablon Kaydet", "Ayarlar_Sablonu.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            with pd.ExcelWriter(path, engine='openpyxl') as writer:
                df_sube = pd.DataFrame(columns=["ID", "Ad"])
                df_sube.to_excel(writer, sheet_name="Subeler", index=False)

                df_gorev = pd.DataFrame(columns=["ID", "Ad"])
                df_gorev.to_excel(writer, sheet_name="Gorevler", index=False)

                df_izin = pd.DataFrame(columns=["ID", "Ad", "Renk", "UcretliMi"])
                df_izin.to_excel(writer, sheet_name="IzinTurleri", index=False)

            ModernMesaj.basari(self, "Şablon oluşturuldu.")
        except Exception as e:
            ModernMesaj.hata(self, str(e))

    def load_data(self):
        """Firma değişince session yenilenir ve tüm listeler tekrar yüklenir."""
        for fn in self._yukle_fns:
            try:
                fn()
            except Exception:
                pass
        self.load_backup_settings()

    def refresh_all_panels(self):
        self.session.close()
        self.session = get_session()
        for i in reversed(range(self.layout().count())):
            item = self.layout().itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        self.init_ui()
        self.load_backup_settings()

    # -------------------- Şifre Üreteci Metotları --------------------
    def sifre_uret(self):
        import secrets
        import string
        uzunluk = self.sifre_uzunluk.value()
        karakterler = ""
        if self.chk_upper.isChecked():
            karakterler += string.ascii_uppercase
        if self.chk_lower.isChecked():
            karakterler += string.ascii_lowercase
        if self.chk_digits.isChecked():
            karakterler += string.digits
        if self.chk_symbols.isChecked():
            karakterler += "!@#$%^&*"
        if not karakterler:
            ModernMesaj.uyari(self, "En az bir karakter türü seçmelisiniz!")
            return
        sifre = ''.join(secrets.choice(karakterler) for _ in range(uzunluk))
        self.sifre_goster.setText(sifre)

    def sifre_kopyala(self):
        sifre = self.sifre_goster.text()
        if not sifre:
            ModernMesaj.uyari(self, "Önce bir şifre üretin!")
            return
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(sifre)
        ModernMesaj.basari(self, "Şifre panoya kopyalandı!")

    # -------------------- Yedekleme İşlemleri --------------------
    def load_backup_settings(self):
        # Yüklerken sinyalleri geçici kapat (aksi halde init sırasında kaydet tetiklenebiliyor)
        self.auto_backup_cb.blockSignals(True)
        self.interval_combo.blockSignals(True)
        self.max_backups_spin.blockSignals(True)
        try:
            enabled = self.session.query(SistemAyarlari).filter_by(anahtar='auto_backup_enabled').first()
            enabled_val = (enabled.deger == 'True') if enabled and enabled.deger is not None else False
            self.auto_backup_cb.setChecked(enabled_val)
            self.interval_combo.setEnabled(enabled_val)

            interval = self.session.query(SistemAyarlari).filter_by(anahtar='auto_backup_interval').first()
            if interval and interval.deger:
                idx = self.interval_combo.findText(interval.deger)
                if idx >= 0:
                    self.interval_combo.setCurrentIndex(idx)

            # Maks yedek ayarını, otomatik yedek kapalı olsa bile yükle (kullanıcı kaydedebilmeli)
            maxb = self.session.query(SistemAyarlari).filter_by(anahtar='auto_backup_max').first()
            if maxb and maxb.deger:
                try:
                    self.max_backups_spin.setValue(int(maxb.deger))
                except Exception:
                    pass
        finally:
            self.auto_backup_cb.blockSignals(False)
            self.interval_combo.blockSignals(False)
            self.max_backups_spin.blockSignals(False)

    def toggle_auto_backup(self, state):
        checked = (state == Qt.Checked)
        self.interval_combo.setEnabled(checked)
        self.save_backup_settings()

    def save_backup_settings(self):
        ayar = self.session.query(SistemAyarlari).filter_by(anahtar='auto_backup_enabled').first()
        if not ayar:
            ayar = SistemAyarlari(anahtar='auto_backup_enabled')
            self.session.add(ayar)
        ayar.deger = str(self.auto_backup_cb.isChecked())

        ayar = self.session.query(SistemAyarlari).filter_by(anahtar='auto_backup_interval').first()
        if not ayar:
            ayar = SistemAyarlari(anahtar='auto_backup_interval')
            self.session.add(ayar)
        ayar.deger = self.interval_combo.currentText()

        ayar = self.session.query(SistemAyarlari).filter_by(anahtar='auto_backup_max').first()
        if not ayar:
            ayar = SistemAyarlari(anahtar='auto_backup_max')
            self.session.add(ayar)
        ayar.deger = str(self.max_backups_spin.value())

        self.session.commit()

    def manual_backup(self):
        from backup import backup_database
        cevap = ModernMesaj.soru(self, "Şimdi yedek almak istediğinize emin misiniz?", "Yedekleme Onayı")
        if not cevap:
            return
        path = backup_database()
        if path:
            ModernMesaj.basari(self, f"Yedekleme tamamlandı.\nDosya: {os.path.basename(path)}")
        else:
            ModernMesaj.hata(self, "Yedekleme başarısız! Terminaldeki hata mesajlarını kontrol edin.")

    def show_backups(self):
        backups = list_backups()
        if not backups:
            ModernMesaj.basari(self, "Hiç yedek bulunamadı.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Yedekler")
        dialog.resize(500, 300)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                border-radius: 12px;
            }
            QLabel {
                color: #ecf0f1;
                background: transparent;
            }
            QTableWidget {
                background-color: #34495e;
                border: 1px solid #4a6278;
                border-radius: 8px;
                color: #ecf0f1;
                gridline-color: rgba(255,255,255,0.1);
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
                background-color: #3498db;
                color: white;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                border: none;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        layout = QVBoxLayout(dialog)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Yedek Adı", "İşlem"])
        table.horizontalHeader().setStretchLastSection(True)

        for i, f in enumerate(backups):
            table.insertRow(i)
            table.setItem(i, 0, QTableWidgetItem(f))
            restore_btn = QPushButton("Geri Yükle")
            restore_btn.setStyleSheet("background: #e67e22; color: white; border-radius: 4px; padding: 4px;")
            restore_btn.clicked.connect(lambda _, x=f: self.restore_backup(x))
            table.setCellWidget(i, 1, restore_btn)

        layout.addWidget(table)

        clean_btn = QPushButton("Eski Yedekleri Temizle (sadece son 30'u tut)")
        clean_btn.setStyleSheet("background: #e74c3c; color: white; border-radius: 4px; padding: 8px;")
        clean_btn.clicked.connect(lambda: self.clean_backups(dialog))
        layout.addWidget(clean_btn)

        kapat_btn = QPushButton("Kapat")
        kapat_btn.clicked.connect(dialog.accept)
        layout.addWidget(kapat_btn)

        dialog.exec_()

    def restore_backup(self, filename):
        cevap = ModernMesaj.soru(
            self,
            f"{filename} dosyasını geri yüklemek mevcut veritabanını değiştirecektir.\n\nDevam edilsin mi?",
            "Geri Yükleme Onayı"
        )
        if not cevap:
            return
        success, msg = restore_database(filename)
        if success:
            ModernMesaj.basari(self, msg)
        else:
            ModernMesaj.hata(self, msg)

    def clean_backups(self, dialog):
        max_count = self.max_backups_spin.value()
        cevap = ModernMesaj.soru(
            self,
            f"Eski yedekler temizlenecek. Sadece son {max_count} yedek tutulacak.\nDevam edilsin mi?",
            "Temizleme Onayı"
        )
        if not cevap:
            return
        clean_old_backups(max_count)
        ModernMesaj.basari(self, f"Eski yedekler temizlendi. Son {max_count} yedek tutuldu.")
        dialog.accept()
        self.show_backups()