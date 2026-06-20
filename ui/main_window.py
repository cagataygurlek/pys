# ui/main_window.py

import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLabel, QFrame, QPushButton,
    QApplication
)
from PyQt5.QtCore import Qt, QTimer, QSize, QSettings, QPoint, QRect
from PyQt5.QtWidgets import QDialog
from PyQt5.QtGui import QFont, QIcon

from ui.dashboard_page import DashboardPage
from ui.personel_page import PersonelPage
from ui.bordro_page import BordroPage
from ui.puantaj_page import PuantajPage
from ui.ayarlar_page import AyarlarPage
from ui.izin_page import IzinPage
from ui.haciz_page import HacizPage
from ui.avans_page import AvansPage
from ui.basvuru_page import BasvuruPage

from backup import backup_database, clean_old_backups
from ui.firma_secim_dialog import FirmaSecimDialog
from ui.utils import ModernMesaj
from database import set_database, get_session, get_current_db_path


def get_base_dir():
    """Uygulama ana dizinini döndürür (exe veya python dosyasının bulunduğu yer)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller ile derlenmiş exe
        return sys._MEIPASS
    else:
        # Normal python çalıştırması
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MainWindow(QMainWindow):
    def __init__(self, kullanici=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint)
        self.kullanici = kullanici

        self.setWindowTitle("Personel Yönetim Sistemi (PYS)")
        self.resize(1024, 680)
        self.setMinimumSize(900, 560)
        self.setStyleSheet("QMainWindow { background-color: #2c3e50; }")
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start = None
        self._resize_geom = None

        # İkonu ayarla (birden çok boyut desteği)
        icon = QIcon()
        base_dir = get_base_dir()
        # Olası icon dosyaları (büyükten küçüğe)
        icon_sizes = [256, 128, 64, 48, 32, 24, 16]
        for size in icon_sizes:
            icon_path = os.path.join(base_dir, f"pys_icon_{size}x{size}.png")
            if os.path.exists(icon_path):
                icon.addFile(icon_path, QSize(size, size))
        if not icon.isNull():
            self.setWindowIcon(icon)
        else:
            # Alternatif: icons klasörüne bak
            alt_path = os.path.join(base_dir, "icons", "pys_app_icon.ico")
            if os.path.exists(alt_path):
                self.setWindowIcon(QIcon(alt_path))
            else:
                print("Uyarı: İkon dosyası bulunamadı!")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.setMouseTracking(True)
        central_widget.setMouseTracking(True)
        central_widget.installEventFilter(self)

        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sol menü
        self.menu_frame = QFrame()
        self.menu_frame.setFixedWidth(220)
        self.menu_frame.setStyleSheet("""
            QFrame {
                background-color: #1a2a38;
                border-right: 1px solid #243342;
            }
            QPushButton {
                background-color: transparent;
                color: #bdc3c7;
                text-align: left;
                padding: 11px 18px 11px 20px;
                border: none;
                font-size: 13px;
                font-weight: 500;
                border-radius: 0px;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                background-color: rgba(52,152,219,0.12);
                color: #ecf0f1;
                border-left: 3px solid #3498db;
            }
            QPushButton:checked {
                background-color: rgba(41,128,185,0.25);
                color: white;
                font-weight: bold;
                border-left: 3px solid #3498db;
            }
        """)

        menu_layout = QVBoxLayout(self.menu_frame)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(0)

        # Logo / Başlık (iki satırlı metin)
        logo_label = QLabel()
        logo_label.setTextFormat(Qt.RichText)
        logo_label.setText("""
            <div style='text-align: center;'>
                <span style='font-size: 22px; font-weight: bold; color: #3498db; letter-spacing: 2px;'>PYS</span><br>
                <span style='font-size: 10px; font-weight: normal; color: #7f8c8d; letter-spacing: 0.5px;'>Personel Yönetim Sistemi</span>
            </div>
        """)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("""
            background-color: #111f2d;
            border-bottom: 1px solid #243342;
            padding: 18px 10px;
        """)
        menu_layout.addWidget(logo_label)

        menu_layout.addSpacing(10)

        self.add_menu_header("ANA SAYFA")
        self.dashboard_btn = self.create_menu_button("📊 Dashboard", 0)

        self.add_menu_header("PERSONEL")
        self.personel_btn = self.create_menu_button("👥 Personel", 1)
        self.izin_btn = self.create_menu_button("🏖️ İzin Yönetimi", 2)

        self.add_menu_header("PUANTAJ & BORDRO")
        self.puantaj_btn = self.create_menu_button("📅 Puantaj", 3)
        self.bordro_btn = self.create_menu_button("💰 Bordro", 4)
        self.avans_btn = self.create_menu_button("💸 Avanslar", 5)

        self.add_menu_header("DİĞER")
        self.haciz_btn = self.create_menu_button("⚖️ Haciz", 6)
        self.basvuru_btn = self.create_menu_button("📋 Başvurular", 7)
        self.ayarlar_btn = self.create_menu_button("⚙️ Ayarlar", 8)

        menu_layout.addStretch()

        # Firma değiştir
        self.firma_degistir_btn = QPushButton("🏢 Firma Değiştir")
        self.firma_degistir_btn.setFixedHeight(50)
        self.firma_degistir_btn.setCursor(Qt.PointingHandCursor)
        self.firma_degistir_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(52,152,219,0.12);
                color: #ecf0f1;
                text-align: center;
                border: 1px solid rgba(52,152,219,0.35);
                border-radius: 8px;
                margin: 10px 14px 6px 14px;
                font-weight: bold;
        	padding: 6px 10px;           /* iç boşluk eklendi */
        	font-size: 13px;            /* yazı hafif büyüdü */
            }
            QPushButton:hover {
                background-color: rgba(52,152,219,0.22);
                border-color: rgba(52,152,219,0.55);
            }
        """)
        self.firma_degistir_btn.clicked.connect(self.firma_degistir)
        menu_layout.addWidget(self.firma_degistir_btn)

        footer = QLabel("ßy Çağatay © 2026")
        footer.setStyleSheet("""
            color: #4a6278;
            padding: 12px;
            font-size: 10px;
            border-top: 1px solid #243342;
            background: transparent;
        """)
        footer.setAlignment(Qt.AlignCenter)
        menu_layout.addWidget(footer)

        self._modul_haritasi = {
            "dashboard": self.dashboard_btn,
            "personel": self.personel_btn,
            "izin": self.izin_btn,
            "puantaj": self.puantaj_btn,
            "bordro": self.bordro_btn,
            "avans": self.avans_btn,
            "haciz": self.haciz_btn,
            "basvuru": self.basvuru_btn,
            "ayarlar": self.ayarlar_btn,
        }
        self._yetkileri_uygula()

        main_layout.addWidget(self.menu_frame)

        # Sağ içerik
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background-color: #2c3e50; border: none;")
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        top_bar = QFrame()
        top_bar.setFixedHeight(52)
        top_bar.setObjectName("titlebar")
        top_bar.setStyleSheet("""
            QFrame#titlebar {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a2a38, stop:1 #2c3e50);
                border-radius: 10px;
                border: 1px solid #4a6278;
            }
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 8, 0)

        self.page_title = QLabel("Dashboard")
        self.page_title.setStyleSheet("font-size: 17px; font-weight: bold; color: white; background: transparent;")
        kullanici_adi = self.kullanici.ad_soyad if self.kullanici else "Admin Kullanıcı"
        self.user_label = QLabel(f"👤 {kullanici_adi}")
        self.user_label.setStyleSheet("color: #7f8c8d; background: transparent;")

        top_layout.addWidget(self.page_title)
        top_layout.addStretch()
        top_layout.addWidget(self.user_label)
        top_layout.addSpacing(12)

        def _tb_btn(text, tip, click_fn):
            b = QPushButton(text)
            b.setFixedSize(32, 28)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(tip)
            b.setStyleSheet("""
                QPushButton{background:transparent;color:#7f8c8d;border:none;border-radius:6px;font-size:13px;}
                QPushButton:hover{background:#34495e;color:white;}
            """)
            b.clicked.connect(click_fn)
            return b

        top_layout.addWidget(_tb_btn("🗕", "Küçült", self.showMinimized))
        top_layout.addWidget(_tb_btn("🗖", "Büyüt/Küçült", lambda: self.showMaximized() if not self.isMaximized() else self.showNormal()))
        top_layout.addWidget(_tb_btn("✕", "Kapat", self.close))
        content_layout.addWidget(top_bar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #2c3e50; border: none;")

        self.dashboard_page = DashboardPage(kullanici=self.kullanici)
        self.personel_page = PersonelPage(kullanici=self.kullanici)
        self.izin_page = IzinPage()
        self.puantaj_page = PuantajPage(kullanici=self.kullanici)
        self.bordro_page = BordroPage()
        self.avans_page = AvansPage(kullanici=self.kullanici)
        self.haciz_page = HacizPage()
        self.ayarlar_page = AyarlarPage()
        self.basvuru_page = BasvuruPage()

        # Bordro hesaplanınca/silinince haciz sayfası havuzunu anında güncelle
        self.bordro_page.bordro_hesaplandi.connect(self.haciz_page.load_data)
        self.bordro_page.bordro_silindi.connect(self.haciz_page.load_data)

        self.stack.addWidget(self.dashboard_page)   # 0
        self.stack.addWidget(self.personel_page)    # 1
        self.stack.addWidget(self.izin_page)        # 2
        self.stack.addWidget(self.puantaj_page)     # 3
        self.stack.addWidget(self.bordro_page)      # 4
        self.stack.addWidget(self.avans_page)       # 5
        self.stack.addWidget(self.haciz_page)       # 6
        self.stack.addWidget(self.basvuru_page)     # 7
        self.stack.addWidget(self.ayarlar_page)     # 8

        content_layout.addWidget(self.stack)
        main_layout.addWidget(self.content_frame)

        self.show_page(0)

        # Otomatik yedekleme ayarları
        self.auto_backup_settings = {
            'enabled': False,
            'interval': 'Her kapanışta',
            'max_backups': 30
        }

        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.auto_backup)
        self.update_backup_timer()

        QApplication.instance().aboutToQuit.connect(self.on_quit)

        # Pencere boyutu/konumunu son halinden geri yükle
        self._restore_window_settings()

        # En son açık kalan sayfayı geri yükle
        self._restore_last_page()

    def firma_degistir(self):
        d = FirmaSecimDialog(parent=self)

        if d.exec_() != QDialog.Accepted or not d.selected_db:
            return
        yeni_db = d.selected_db
        mevcut = get_current_db_path()
        if mevcut and str(mevcut) == str(yeni_db):
            ModernMesaj.basari(self, "Zaten bu firma açık.")
            return
        if not ModernMesaj.soru(self, "Firma (veritabanı) değiştirilecek. Devam edilsin mi?"):
            return
        try:
            set_database(yeni_db)
            self._reload_pages_after_db_change()
            ModernMesaj.basari(self, "Firma değiştirildi.")
        except Exception as e:
            ModernMesaj.hata(self, str(e))

    def _reload_pages_after_db_change(self):
        # Sayfalardaki session'ları yeni DB'ye bağla ve görünümü yenile
        for page_name in [
            "dashboard_page", "personel_page", "izin_page", "puantaj_page",
            "bordro_page", "avans_page", "haciz_page", "ayarlar_page", "basvuru_page"
        ]:
            page = getattr(self, page_name, None)
            if not page:
                continue
            if hasattr(page, "session"):
                try:
                    page.session.close()
                except Exception:
                    pass
                try:
                    page.session = get_session()
                except Exception:
                    pass
            # sayfaya göre refresh
            for m in ["load_data", "refresh_data", "puantaj_olustur", "load_tum_avanslar", "load_backup_settings"]:
                if hasattr(page, m):
                    try:
                        getattr(page, m)()
                        break
                    except Exception:
                        # bazı sayfalarda metot farklı parametre bekleyebilir
                        continue

    def _settings(self) -> QSettings:
        # Uygulama genelinde tek bir settings alanı (Windows: Registry)
        return QSettings("PYS", "PersonelYonetimSistemi")

    def _restore_window_settings(self):
        s = self._settings()
        geom = s.value("main_window/geometry")
        state = s.value("main_window/windowState")
        if geom is not None:
            try:
                self.restoreGeometry(geom)
            except Exception:
                pass
        if state is not None:
            try:
                self.restoreState(state)
            except Exception:
                pass

    def _restore_last_page(self):
        s = self._settings()
        try:
            last_idx = int(s.value("main_window/lastPageIndex", 0))
        except Exception:
            last_idx = 0
        if 0 <= last_idx < self.stack.count():
            self.show_page(last_idx)

    def _save_window_settings(self):
        s = self._settings()
        try:
            s.setValue("main_window/geometry", self.saveGeometry())
            s.setValue("main_window/windowState", self.saveState())
            s.setValue("main_window/lastPageIndex", int(self.stack.currentIndex()))
            s.sync()
        except Exception:
            pass

    def closeEvent(self, event):
        self._save_window_settings()
        super().closeEvent(event)

    def add_menu_header(self, title):
        label = QLabel(title)
        label.setStyleSheet("""
            font-size: 10px;
            font-weight: bold;
            color: #4a6278;
            padding: 14px 20px 4px 20px;
            letter-spacing: 1px;
            background: transparent;
        """)
        self.menu_frame.layout().addWidget(label)

    def create_menu_button(self, text, index):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.show_page(index))
        if index == 0:
            btn.setChecked(True)
        self.menu_frame.layout().addWidget(btn)
        return btn

    def show_page(self, index):
        buttons = {
            0: self.dashboard_btn,
            1: self.personel_btn,
            2: self.izin_btn,
            3: self.puantaj_btn,
            4: self.bordro_btn,
            5: self.avans_btn,
            6: self.haciz_btn,
            7: self.basvuru_btn,
            8: self.ayarlar_btn,
        }
        if index in buttons and not buttons[index].isEnabled():
            return
        for btn in self.findChildren(QPushButton):
            if btn.isCheckable():
                btn.setChecked(False)
        buttons = {
            0: self.dashboard_btn,
            1: self.personel_btn,
            2: self.izin_btn,
            3: self.puantaj_btn,
            4: self.bordro_btn,
            5: self.avans_btn,
            6: self.haciz_btn,
            7: self.basvuru_btn,
            8: self.ayarlar_btn,
        }
        if index in buttons:
            buttons[index].setChecked(True)
            titles = {
                0: "Dashboard",
                1: "Personel Yönetimi",
                2: "İzin Yönetimi",
                3: "Puantaj",
                4: "Bordro",
                5: "Avans Yönetimi",
                6: "Haciz Yönetimi",
                7: "İş Başvuruları",
                8: "Ayarlar",
            }
            self.page_title.setText(titles.get(index, "PYS"))
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.dashboard_page.refresh_data()
        elif index == 3:
            self.puantaj_page.puantaj_olustur()

    def _yetkileri_uygula(self):
        if not self.kullanici or self.kullanici.admin:
            return
        yetkili_moduller = set()
        for y in self.kullanici.yetkileri:
            yetkili_moduller.add(y.modul_adi)
        ilk_aktif = None
        for modul_kodu, btn in self._modul_haritasi.items():
            if modul_kodu not in yetkili_moduller:
                btn.setEnabled(False)
                btn.setStyleSheet(btn.styleSheet() + "color:#4a6278;")
            else:
                if ilk_aktif is None:
                    ilk_aktif = modul_kodu
        if ilk_aktif:
            idx = list(self._modul_haritasi.keys()).index(ilk_aktif)
            QTimer.singleShot(100, lambda i=idx: self.show_page(i))

    def update_backup_timer(self):
        if not self.auto_backup_settings['enabled']:
            self.backup_timer.stop()
            return
        interval = self.auto_backup_settings['interval']
        if interval == 'Saatlik':
            msec = 60 * 60 * 1000
        elif interval == 'Günlük':
            msec = 24 * 60 * 60 * 1000
        elif interval == 'Haftalık':
            msec = 7 * 24 * 60 * 60 * 1000
        else:
            self.backup_timer.stop()
            return
        self.backup_timer.start(msec)

    def auto_backup(self):
        if self.auto_backup_settings['enabled']:
            backup_database()
            max_count = self.auto_backup_settings.get('max_backups', 30)
            clean_old_backups(max_count)

    def on_quit(self):
        if self.auto_backup_settings['enabled'] and self.auto_backup_settings['interval'] == 'Her kapanışta':
            backup_database()
            max_count = self.auto_backup_settings.get('max_backups', 30)
            clean_old_backups(max_count)

    def eventFilter(self, obj, event):
        et = event.type()
        if et == event.MouseMove:
            pos = event.pos()
            if obj != self:
                pos = obj.mapTo(self, pos)
            if self._resize_edge:
                gpos = event.globalPos()
                diff = gpos - self._resize_start
                g = self._resize_geom
                new_geom = QRect(g)
                if self._resize_edge & Qt.LeftEdge:
                    new_geom.setLeft(g.left() + diff.x())
                if self._resize_edge & Qt.RightEdge:
                    new_geom.setRight(g.right() + diff.x())
                if self._resize_edge & Qt.TopEdge:
                    new_geom.setTop(g.top() + diff.y())
                if self._resize_edge & Qt.BottomEdge:
                    new_geom.setBottom(g.bottom() + diff.y())
                if new_geom.width() >= self.minimumWidth() and new_geom.height() >= self.minimumHeight():
                    self.setGeometry(new_geom)
                return True
            elif self._drag_pos is not None and event.buttons() == Qt.LeftButton:
                self.move(event.globalPos() - self._drag_pos)
                return True
            else:
                edge = self._edge_at(pos)
                if edge & Qt.LeftEdge or edge & Qt.RightEdge:
                    self.setCursor(Qt.SizeHorCursor)
                elif edge & Qt.TopEdge or edge & Qt.BottomEdge:
                    self.setCursor(Qt.SizeVerCursor)
                else:
                    self.unsetCursor()
        elif et == event.MouseButtonPress and event.button() == Qt.LeftButton:
            pos = event.pos()
            if obj != self:
                pos = obj.mapTo(self, pos)
            titlebar = self.findChild(QFrame, "titlebar")
            if titlebar and titlebar.geometry().contains(pos):
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
                return True
            edge = self._edge_at(pos)
            if edge:
                self._resize_edge = edge
                self._resize_start = event.globalPos()
                self._resize_geom = self.geometry()
                event.accept()
                return True
        elif et == event.MouseButtonRelease:
            if self._resize_edge or self._drag_pos:
                self._drag_pos = None
                self._resize_edge = None
                self.unsetCursor()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        pass

    def _edge_at(self, pos):
        edges = 0
        rect = self.rect()
        margin = 8
        if pos.x() <= rect.left() + margin:
            edges |= Qt.LeftEdge
        elif pos.x() >= rect.right() - margin:
            edges |= Qt.RightEdge
        if pos.y() <= rect.top() + margin:
            edges |= Qt.TopEdge
        elif pos.y() >= rect.bottom() - margin:
            edges |= Qt.BottomEdge
        return edges