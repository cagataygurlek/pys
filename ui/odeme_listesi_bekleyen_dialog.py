# ui/odeme_listesi_bekleyen_dialog.py
"""
Havuzda bekleyen (bordrodan kesilmiş ama henüz haciz borcuna işlenmemiş)
ödemeleri listeler. Çıktı alınabilir, seçilenler için ödeme yapılabilir.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QFrame, QWidget, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
import datetime
import calendar

from models import Haciz, HacizOdeme, Bordro, Personel
from ui.utils import ModernMesaj, make_frameless
from ui.widgets import ToggleSwitch


class OdemeListesiBekleyenDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.session = session
        self.selected_keys = set()   # (bordro_id, haciz_id)
        self._row_keys = {}          # row → (bordro_id, haciz_id)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1100, 580)
        self.init_ui()
        self.load_data()
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self._ortala)
        make_frameless(self)

    def _ortala(self):
        p = self.parent()
        ref = p.frameGeometry() if p else None
        if ref:
            self.move(ref.x() + (ref.width() - self.width()) // 2,
                      ref.y() + (ref.height() - self.height()) // 2 - 30)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        outer = QFrame(self)
        outer.setObjectName("outer")
        outer.setStyleSheet("""
            QFrame#outer {
                background: #2c3e50;
                border-radius: 16px;
                border: 1px solid #4a6278;
            }
        """)
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        layout.addWidget(outer)

        # Başlık
        hdr = QFrame()
        hdr.setFixedHeight(62)
        hdr.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #16a085, stop:1 #1abc9c);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border: none;
            }
        """)
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(20, 0, 16, 0)
        hdr_lay.setSpacing(12)
        ic = QLabel("📄"); ic.setFixedSize(40, 40); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background: rgba(255,255,255,0.18); border-radius: 20px; font-size: 18px;")
        tl = QLabel("Ödeme Listesi — Havuzda Bekleyen Haciz Ödemeleri")
        tl.setStyleSheet("color: white; font-size: 14px; font-weight: bold; background: transparent;")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.6);font-size:16px;border:none;} QPushButton:hover{color:white;}")
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(ic); hdr_lay.addWidget(tl); hdr_lay.addStretch(); hdr_lay.addWidget(close_btn)
        outer_lay.addWidget(hdr)

        # Tablo
        body = QWidget(); body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 14, 16, 10)
        body_lay.setSpacing(10)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Seç", "Sıra No", "Personel Adı Soyadı", "TC No",
            "IBAN", "Alacaklı Kurum", "Dosya No", "Tutar", "Açıklama"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 55)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 50)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #34495e;
                border: 1px solid #4a6278;
                border-radius: 8px;
                color: #ecf0f1;
                gridline-color: rgba(255,255,255,0.07);
                outline: none;
            }
            QHeaderView::section {
                background: #1a2a38; color: #bdc3c7;
                font-weight: bold; padding: 8px; border: none;
            }
            QTableWidget::item { padding: 6px; background: #34495e; color: #ecf0f1; }
            QTableWidget::item:selected { background: #2980b9; color: white; }
        """)
        body_lay.addWidget(self.table)
        outer_lay.addWidget(body)

        # Alt bar
        footer = QFrame()
        footer.setFixedHeight(62)
        footer.setStyleSheet("""
            QFrame {
                background: #243342;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
                border: none;
                border-top: 1px solid #1a2a38;
            }
        """)
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(16, 10, 16, 10)
        foot_lay.setSpacing(8)

        def _btn(text, color, slot):
            b = QPushButton(text)
            b.setFixedHeight(38)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"QPushButton{{background:{color};color:white;border-radius:8px;font-size:12px;font-weight:bold;border:none;padding:0 14px;}} QPushButton:hover{{opacity:0.85;}}")
            b.clicked.connect(slot)
            return b

        self.tumu_sec_btn = _btn("✅ Tümünü Seç", "#3498db", self._tumunu_sec)
        self.kaldir_btn   = _btn("❌ Kaldır",      "#636e72", self._secimi_kaldir)
        self.odeme_btn    = _btn("⚖️ Seçilenlere Ödeme Yap", "#8e44ad", self._odeme_yap)
        self.cikti_btn    = _btn("🖨️ Çıktı Al (Excel)", "#27ae60", self._excel_cikti)
        kapat_btn = QPushButton("Kapat")
        kapat_btn.setFixedHeight(38)
        kapat_btn.setStyleSheet("QPushButton{background:transparent;color:#bdc3c7;border:1px solid #4a6278;border-radius:8px;padding:0 16px;font-size:12px;} QPushButton:hover{background:#34495e;color:white;}")
        kapat_btn.clicked.connect(self.reject)

        foot_lay.addWidget(self.tumu_sec_btn)
        foot_lay.addWidget(self.kaldir_btn)
        foot_lay.addStretch()
        foot_lay.addWidget(self.odeme_btn)
        foot_lay.addWidget(self.cikti_btn)
        foot_lay.addWidget(kapat_btn)
        outer_lay.addWidget(footer)

    def load_data(self):
        self.table.setRowCount(0)
        self.selected_keys.clear()
        self._row_keys.clear()

        # Tüm dönemlerdeki ödenmeyen bordrolar
        bordrolar = self.session.query(Bordro).filter(
            Bordro.icra_kesintisi > 0
        ).order_by(Bordro.yil, Bordro.ay).all()

        sira = 1
        for bordro in bordrolar:
            odeme_var = self.session.query(HacizOdeme).filter(
                HacizOdeme.bordro_id == bordro.id
            ).first()
            if odeme_var:
                continue

            ilk_gun = datetime.date(bordro.yil, bordro.ay, 1)
            son_gun = datetime.date(bordro.yil, bordro.ay,
                                    calendar.monthrange(bordro.yil, bordro.ay)[1])

            hacizler = self.session.query(Haciz).filter(
                Haciz.personel_id == bordro.personel_id,
                Haciz.durum == "Aktif",
                Haciz.kalan_borc > 0,
                Haciz.baslangic_tarihi <= son_gun,
                (Haciz.bitis_tarihi >= ilk_gun) | (Haciz.bitis_tarihi == None)
            ).order_by(Haciz.baslangic_tarihi).all()

            if not hacizler:
                continue

            kalan_havuz = bordro.icra_kesintisi
            for h in hacizler:
                if kalan_havuz <= 0:
                    break
                bu_hacize = min(h.kalan_borc, kalan_havuz)
                if bu_hacize <= 0:
                    continue

                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setRowHeight(row, 38)

                key = (bordro.id, h.id)
                self._row_keys[row] = key

                toggle = ToggleSwitch(width=30, height=16)
                toggle.setChecked(False)
                toggle.stateChanged.connect(lambda st, k=key: self._toggle(k, st))
                tw = QWidget(); tw.setStyleSheet("background:transparent;")
                tl = QHBoxLayout(tw); tl.setContentsMargins(4,4,4,4); tl.setAlignment(Qt.AlignCenter)
                tl.addWidget(toggle)
                self.table.setCellWidget(row, 0, tw)

                p = h.personel
                ay_adi = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                          "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"][bordro.ay - 1]
                aciklama = f"{h.dosya_no} {p.ad_soyad} {ay_adi} {bordro.yil} kesintisi"

                items = [
                    QTableWidgetItem(str(sira)),
                    QTableWidgetItem(p.ad_soyad),
                    QTableWidgetItem(p.tc_no or "-"),
                    QTableWidgetItem(h.iban or "-"),
                    QTableWidgetItem(h.alacakli_kurum or "-"),
                    QTableWidgetItem(h.dosya_no),
                    QTableWidgetItem(f"{bu_hacize:,.2f} ₺".replace(",", ".")),
                    QTableWidgetItem(aciklama),
                ]
                for col, item in enumerate(items, 1):
                    if col == 2:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    elif col == 7:
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setForeground(QColor("#2ecc71"))
                        f = QFont(); f.setBold(True); item.setFont(f)
                    else:
                        item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, col, item)

                kalan_havuz -= bu_hacize
                sira += 1

    def _toggle(self, key, state):
        if state: self.selected_keys.add(key)
        else:     self.selected_keys.discard(key)

    def _tumunu_sec(self):
        for row in range(self.table.rowCount()):
            w = self.table.cellWidget(row, 0)
            if w:
                t = w.findChild(ToggleSwitch)
                if t: t.setChecked(True)

    def _secimi_kaldir(self):
        for row in range(self.table.rowCount()):
            w = self.table.cellWidget(row, 0)
            if w:
                t = w.findChild(ToggleSwitch)
                if t: t.setChecked(False)

    def _odeme_yap(self):
        if not self.selected_keys:
            ModernMesaj.uyari(self, "Lütfen ödeme yapılacak satırları seçin.")
            return

        odenecekler = []
        toplam = 0.0
        for row, key in self._row_keys.items():
            if key not in self.selected_keys:
                continue
            tutar_item = self.table.item(row, 7)
            if not tutar_item:
                continue
            try:
                tutar = float(tutar_item.text().replace(" ₺","").replace(".","").replace(",","."))
            except Exception:
                continue
            odenecekler.append((key[0], key[1], tutar))
            toplam += tutar

        if not odenecekler:
            return

        if not ModernMesaj.soru(self, f"{len(odenecekler)} ödeme, toplam {toplam:,.2f} ₺ yapılacak. Onaylıyor musunuz?"):
            return

        try:
            for bordro_id, haciz_id, tutar in odenecekler:
                h = self.session.get(Haciz, haciz_id)
                bordro = self.session.get(Bordro, bordro_id)
                if not h or not bordro:
                    continue
                son_gun = datetime.date(bordro.yil, bordro.ay,
                                        calendar.monthrange(bordro.yil, bordro.ay)[1])
                odeme = HacizOdeme(
                    haciz_id=haciz_id,
                    bordro_id=bordro_id,
                    tarih=son_gun,
                    tutar=tutar,
                    aciklama=f"{bordro.ay}. ay {bordro.yil} bordro haciz kesintisi"
                )
                self.session.add(odeme)
                h.kalan_borc = max(0.0, (h.kalan_borc or 0) - tutar)
                if h.kalan_borc <= 0:
                    h.kalan_borc = 0
                    h.durum = "Tamamlandı"
            self.session.commit()
            ModernMesaj.basari(self, f"{len(odenecekler)} ödeme kaydedildi.")
            self.accept()
        except Exception as e:
            self.session.rollback()
            ModernMesaj.hata(self, str(e))

    def _excel_cikti(self):
        import pandas as pd
        path, _ = QFileDialog.getSaveFileName(
            self, "Excel Kaydet", "odeme_listesi.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            rows = []
            for row in range(self.table.rowCount()):
                r = []
                for col in range(1, self.table.columnCount()):
                    item = self.table.item(row, col)
                    r.append(item.text() if item else "")
                rows.append(r)
            import pandas as pd
            df = pd.DataFrame(rows, columns=[
                "Sıra No", "Personel Adı Soyadı", "TC No",
                "IBAN", "Alacaklı Kurum", "Dosya No", "Tutar", "Açıklama"
            ])
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Ödeme Listesi")
                ws = writer.sheets["Ödeme Listesi"]
                # Yatay tek sayfaya sığsın
                from openpyxl.styles import Alignment, Font, PatternFill
                for col_cells in ws.columns:
                    max_len = max((len(str(c.value or "")) for c in col_cells), default=10)
                    ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 40)
                ws.page_setup.orientation = "landscape"
                ws.page_setup.fitToPage = True
                ws.page_setup.fitToWidth = 1
                ws.page_setup.fitToHeight = 0
            ModernMesaj.basari(self, f"Excel kaydedildi:\n{path}")
        except Exception as e:
            ModernMesaj.hata(self, str(e))
