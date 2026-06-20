# ui/ozluk_evraklari_dialog.py
#
# Word şablonunu (ÖZLÜK_EVRAKLARI_FRESH_2026.docx) kullanarak
# personel verilerini doldurur ve PDF'e dönüştürür.
# Bu yöntemle tüm biçimlendirme, imza alanları ve tablo yapısı korunur.

import os
import sys
import shutil
import tempfile
import datetime
import subprocess

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QFrame, QWidget, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor

from ui.utils import ModernMesaj, make_frameless


# ── Şablon dosyasının konumunu bul ───────────────────────────────────────────
def _sablon_yolu():
    """
    Şablon dosyasını şu sırayla arar:
      1. PyInstaller paketi: sys._MEIPASS/templates/
      2. Proje kökü: templates/
      3. ui/ klasörü yanında: templates/
    """
    dosya_adi = "ÖZLÜK_EVRAKLARI_FRESH_2026.docx"
    aradiginlar = []

    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    adaylar = [
        os.path.join(base, "templates", dosya_adi),
        os.path.join(base, dosya_adi),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", dosya_adi),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), dosya_adi),
    ]
    for yol in adaylar:
        if os.path.exists(yol):
            return yol
    return None


# ── Paragraf içi metin değiştirici ───────────────────────────────────────────
def _run_degistir(paragraf, run_idx, yeni_metin):
    """Belirtilen run'ın metnini değiştirir, diğer özellikler (bold, font vb.) korunur."""
    if run_idx < len(paragraf.runs):
        paragraf.runs[run_idx].text = yeni_metin


def _paragrafta_degistir(paragraf, eski, yeni):
    """
    Paragraftaki tüm run'ları tarar, eski metni yeni ile değiştirir.
    Metin birden fazla run'a bölünmüş olsa bile düzgün çalışır.
    """
    # Önce tek run içinde dene
    for run in paragraf.runs:
        if eski in run.text:
            run.text = run.text.replace(eski, yeni)
            return True

    # Birden fazla run'a bölünmüş olabilir — tüm metni birleştir
    tam_metin = "".join(r.text for r in paragraf.runs)
    if eski not in tam_metin:
        return False

    yeni_metin = tam_metin.replace(eski, yeni)
    # İlk run'a tümünü yaz, diğerlerini boşalt
    if paragraf.runs:
        paragraf.runs[0].text = yeni_metin
        for run in paragraf.runs[1:]:
            run.text = ""
    return True


def _tarih_alanini_degistir(paragraf, tarih_str):
    """
    "......./…..../2026" veya "……/……/2026" kalıplarını tek bir tarih ile değiştirir.
    Bu kalıplar genellikle birden fazla run'a bölünmüştür.
    """
    kaliplar = [
        ("......./.....…/2026", tarih_str),
        ("......./…..../2026",  tarih_str),
        ("……/……/2026",          tarih_str),
        ("……/……202",            ""),   # artık ayrı birleşir
    ]
    for eski, yeni in kaliplar:
        _paragrafta_degistir(paragraf, eski, yeni)

    # Run parçaları olarak bölünmüş tarih kalıplarını yakala
    TARIH_PARCALARI = [
        (["......."],    ["/…..../202", "6"]),
        (["……"],         ["/……/202",    "6"]),
        (["……"],         ["/……202",     "6"]),
    ]
    for ilk_parcalar, kalan_parcalar in TARIH_PARCALARI:
        runs = paragraf.runs
        for i, run in enumerate(runs):
            if run.text in ilk_parcalar:
                # Sonraki run'ları kontrol et
                eslesme = True
                for j, parca in enumerate(kalan_parcalar):
                    if i + 1 + j >= len(runs) or runs[i + 1 + j].text != parca:
                        eslesme = False
                        break
                if eslesme:
                    run.text = tarih_str
                    for j in range(len(kalan_parcalar)):
                        runs[i + 1 + j].text = ""
                    break


# ── Ana doldurma fonksiyonu ───────────────────────────────────────────────────
def _sablonu_doldur(sablon_yolu, personel, cikti_docx):
    """
    Word şablonunu kopyalar, personel verilerini yerleştirir,
    dolu .docx dosyasını cikti_docx yoluna kaydeder.
    """
    from docx import Document

    shutil.copy2(sablon_yolu, cikti_docx)
    doc = Document(cikti_docx)

    p = personel
    bugun     = datetime.date.today()
    baslama   = p.ise_baslama or bugun
    tarih_str = bugun.strftime("%d/%m/%Y")
    bas_str   = baslama.strftime("%d/%m/%Y")

    tc_no        = p.tc_no        or ""
    ad_soyad     = p.ad_soyad     or ""
    baba_adi     = getattr(p, "baba_adi", "") or ""
    dogum_yeri   = getattr(p, "dogum_yeri", "") or ""
    dogum_tar    = p.dogum_tarihi.strftime("%d/%m/%Y") if getattr(p, "dogum_tarihi", None) else ""
    gsm          = p.telefon      or ""
    gorev        = p.gorev.ad     if p.gorev  else ""
    maas_str     = (f"{p.maas:,.2f} ₺".replace(",", ".")) if (p.maas and p.maas > 0) else "Asgari Ücret"

    paralar = doc.paragraphs

    # ── İŞÇİNİN bölümü ───────────────────────────────────────────────────────
    # Para 11: TC No
    if len(paralar) > 11 and "TC No" in paralar[11].text:
        _run_degistir(paralar[11], -1, tc_no)

    # Para 12: Adı soyadı
    if len(paralar) > 12 and "Adı soyadı" in paralar[12].text and "unvanı" not in paralar[12].text:
        _run_degistir(paralar[12], -1, ad_soyad)

    # Para 13: Baba adı
    if len(paralar) > 13 and "Baba adı" in paralar[13].text:
        _run_degistir(paralar[13], -1, baba_adi)

    # Para 14: Doğum yeri ve tarihi
    if len(paralar) > 14 and "Doğum yeri" in paralar[14].text:
        dogum_birlesik = f"{dogum_yeri}, {dogum_tar}" if dogum_yeri else dogum_tar
        _run_degistir(paralar[14], -1, dogum_birlesik)

    # Para 15: GSM
    if len(paralar) > 15 and "GSM" in paralar[15].text:
        _run_degistir(paralar[15], -1, gsm)

    # ── YAPILACAK İŞ ─────────────────────────────────────────────────────────
    if len(paralar) > 19 and "YAPILACAK İŞ" in paralar[19].text:
        _run_degistir(paralar[19], -1, gorev)

    # ── Tarih alanları ───────────────────────────────────────────────────────
    # Para 21: Sözleşme süresi
    if len(paralar) > 21 and "SÖZLEŞMENİN SÜRESİ" in paralar[21].text:
        _tarih_alanini_degistir(paralar[21], tarih_str)

    # Para 22: İşe başlama tarihi
    if len(paralar) > 22 and "İŞE BAŞLAMA TARİHİ" in paralar[22].text:
        _tarih_alanini_degistir(paralar[22], bas_str)

    # Para 81: Sözleşme imza tarihi
    if len(paralar) > 81 and "iki nüsha" in paralar[81].text:
        _tarih_alanini_degistir(paralar[81], tarih_str)

    # ── Fazla mesai onay belgesi ─────────────────────────────────────────────
    # Para 94: TC + tarih
    if len(paralar) > 94 and "TC Kimlik" in paralar[94].text:
        _paragrafta_degistir(paralar[94], "…………………", tc_no)
        _tarih_alanini_degistir(paralar[94], tarih_str)

    # Para 103: Ad soyad
    if len(paralar) > 103 and "İŞÇİNİN ADI SOYADI" in paralar[103].text:
        _paragrafta_degistir(paralar[103], "………………………….","")
        _run_degistir(paralar[103], -1, ad_soyad)

    # ── İşyeri kuralları bölümü ──────────────────────────────────────────────
    # Para 164: Nüsha tarihi
    if len(paralar) > 164 and "Nüshasını Elden Aldım" in paralar[164].text:
        _tarih_alanini_degistir(paralar[164], tarih_str)

    # Para 166: Adı Soyadı
    if len(paralar) > 166 and "Adı Soyadı" in paralar[166].text:
        _paragrafta_degistir(paralar[166], "………………………………", ad_soyad)

    # ── Çalışma şartları değişikliği bildirimi ───────────────────────────────
    # Para 267: Sayın ...
    if len(paralar) > 267 and "Sayın" in paralar[267].text:
        _paragrafta_degistir(paralar[267], "…………………………..","")
        _paragrafta_degistir(paralar[267], "…………………………….", ad_soyad)

    # Para 279: Nüsha tarihi
    if len(paralar) > 279 and "Nüshasını Elden Aldım" in paralar[279].text:
        _tarih_alanini_degistir(paralar[279], tarih_str)

    # Para 281: Adı Soyadı
    if len(paralar) > 281 and "Adı Soyadı" in paralar[281].text:
        _paragrafta_degistir(paralar[281], "………………………………", ad_soyad)

    # ── Genel noktalı yer tutucu taraması (kalan "………" kalıpları) ──────────
    nokta_kaliplari = [
        "………………………….","………………………………","…………………………..","…………………………….",
        "…………………","……………", "…………"
    ]
    ad_konuldu_sayac = 0
    for para in doc.paragraphs:
        metin = para.text
        for kalip in nokta_kaliplari:
            if kalip in metin:
                # Zaten yukarıda işlenenler hariç
                if "TC Kimlik" in metin:
                    continue
                if "İŞÇİNİN ADI SOYADI" in metin:
                    continue
                # İmza satırları gibi boş bırakılacaklar
                if "İmza" in metin:
                    break
                break

    doc.save(cikti_docx)
    return cikti_docx


# ── PDF dönüştürme ────────────────────────────────────────────────────────────
def _docx_to_pdf(docx_yolu, pdf_yolu):
    """
    .docx → .pdf dönüştürür.
    Önce docx2pdf (Word COM) dener, başarısız olursa LibreOffice'i dener.
    """
    # Yöntem 1: docx2pdf (Windows'ta Word, diğerlerinde LibreOffice)
    try:
        from docx2pdf import convert
        convert(docx_yolu, pdf_yolu)
        if os.path.exists(pdf_yolu):
            return True, None
    except Exception as e1:
        pass

    # Yöntem 2: LibreOffice
    try:
        cikti_klasor = os.path.dirname(pdf_yolu)
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf",
             "--outdir", cikti_klasor, docx_yolu],
            capture_output=True, timeout=60
        )
        # LibreOffice dosyayı aynı isimle .pdf olarak kaydeder
        lo_pdf = os.path.splitext(docx_yolu)[0] + ".pdf"
        if os.path.exists(lo_pdf):
            if lo_pdf != pdf_yolu:
                shutil.move(lo_pdf, pdf_yolu)
            return True, None
    except Exception as e2:
        pass

    return False, (
        "PDF dönüştürme başarısız.\n\n"
        "Lütfen bilgisayarınızda Microsoft Word veya LibreOffice yüklü olduğundan emin olun.\n\n"
        "Word dosyası (.docx) kaydedildi — onu açıp manuel olarak PDF'e aktarabilirsiniz."
    )


# ── Arka plan işçisi ──────────────────────────────────────────────────────────
class DonusturmeWorker(QThread):
    tamamlandi = pyqtSignal(bool, str, str)   # basarili, mesaj, docx_yolu

    def __init__(self, sablon, personel, pdf_yolu):
        super().__init__()
        self.sablon    = sablon
        self.personel  = personel
        self.pdf_yolu  = pdf_yolu

    def run(self):
        try:
            tmp_dir  = tempfile.mkdtemp()
            ad       = (self.personel.ad_soyad or "Personel").replace(" ", "_")
            docx_yol = os.path.join(tmp_dir, f"{ad}_Ozluk.docx")

            _sablonu_doldur(self.sablon, self.personel, docx_yol)

            basarili, hata = _docx_to_pdf(docx_yol, self.pdf_yolu)
            if basarili:
                self.tamamlandi.emit(True, "", docx_yol)
            else:
                # PDF olmadı ama docx var; kullanıcıya docx'i sun
                docx_kayit = os.path.splitext(self.pdf_yolu)[0] + ".docx"
                shutil.copy2(docx_yol, docx_kayit)
                self.tamamlandi.emit(False, hata, docx_kayit)
        except Exception as e:
            self.tamamlandi.emit(False, str(e), "")


# ── Ana Dialog ────────────────────────────────────────────────────────────────
class OzlukEvraklariDialog(QDialog):
    def __init__(self, personel, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.personel   = personel
        self.sablon_yol = _sablon_yolu()
        self.worker     = None

        self.setFixedSize(500, 320)
        self.setStyleSheet("""
            QDialog { background-color: #2c3e50; }
            QLabel  { color: #ecf0f1; background: transparent; }
            QPushButton {
                background-color: #3498db; color: white;
                font-weight: bold; border-radius: 8px; border: none; padding: 9px 18px;
            }
            QPushButton:hover    { background-color: #2980b9; }
            QPushButton:disabled { background-color: #4a6278; color: #7f8c8d; }
            QProgressBar {
                border: 1px solid #4a6278; border-radius: 6px;
                background-color: #34495e; color: white; text-align: center;
            }
            QProgressBar::chunk { background-color: #27ae60; border-radius: 5px; }
        """)
        self.init_ui()
        make_frameless(self)

    def init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        hdr = QFrame(); hdr.setFixedHeight(56)
        hdr.setStyleSheet("QFrame { background-color: #1e4d7b; border: none; }")
        hl  = QHBoxLayout(hdr); hl.setContentsMargins(18, 0, 12, 0); hl.setSpacing(12)
        ic  = QLabel("📄"); ic.setFixedSize(38, 38); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:rgba(255,255,255,0.15); border-radius:19px; font-size:18px;")
        ttl = QLabel(f"Özlük Evrakları — {self.personel.ad_soyad}")
        ttl.setStyleSheet("color:white; font-size:13px; font-weight:bold; background:transparent;")
        close_btn = QPushButton("✕"); close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.5);font-size:14px;border:none;border-radius:13px;} QPushButton:hover{background:rgba(255,255,255,0.15);color:white;}")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        hl.addWidget(ic); hl.addWidget(ttl); hl.addStretch(); hl.addWidget(close_btn)
        lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet("background:transparent;")
        bl   = QVBoxLayout(body); bl.setContentsMargins(22, 18, 22, 14); bl.setSpacing(12)

        # Şablon durum bildirimi
        if self.sablon_yol:
            durum_lbl = QLabel(
                f"✅  Şablon bulundu.\n"
                f"Word şablonu kullanılarak formatı korunan PDF oluşturulacak.\n"
                f"Şablon: {os.path.basename(self.sablon_yol)}"
            )
            durum_lbl.setStyleSheet(
                "color:#2ecc71; background:#0e2a1a; border:1px solid #27ae60; "
                "border-radius:8px; padding:10px 14px; font-size:11px; line-height:1.5;"
            )
        else:
            durum_lbl = QLabel(
                "⚠️  Şablon dosyası bulunamadı!\n\n"
                "'ÖZLÜK_EVRAKLARI_FRESH_2026.docx' dosyasını\n"
                "projenin 'templates/' klasörüne koyun."
            )
            durum_lbl.setStyleSheet(
                "color:#e74c3c; background:#2c1010; border:1px solid #e74c3c; "
                "border-radius:8px; padding:10px 14px; font-size:11px;"
            )
        durum_lbl.setWordWrap(True)
        bl.addWidget(durum_lbl)

        self.progress = QProgressBar(); self.progress.setRange(0, 0)
        self.progress.setFixedHeight(14); self.progress.setVisible(False)
        bl.addWidget(self.progress)

        self.durum_lbl2 = QLabel("")
        self.durum_lbl2.setStyleSheet("color:#f39c12; font-size:11px;")
        self.durum_lbl2.setVisible(False)
        bl.addWidget(self.durum_lbl2)

        lay.addWidget(body); lay.addStretch()

        footer = QFrame(); footer.setFixedHeight(58)
        footer.setStyleSheet("QFrame { background-color:#1a2530; border-top:1px solid #1a2a38; }")
        fl = QHBoxLayout(footer); fl.setContentsMargins(18,10,18,10); fl.setSpacing(10); fl.addStretch()

        self.pdf_btn = QPushButton("📄  PDF Oluştur")
        self.pdf_btn.setFixedHeight(36)
        self.pdf_btn.setEnabled(bool(self.sablon_yol))
        self.pdf_btn.clicked.connect(self.pdf_olustur)

        kapat_btn = QPushButton("Kapat"); kapat_btn.setFixedHeight(36)
        kapat_btn.setStyleSheet("QPushButton{background:transparent;color:#7f8c8d;border:1px solid #4a6278;border-radius:8px;padding:0 16px;}QPushButton:hover{background:#34495e;color:white;}")
        kapat_btn.clicked.connect(self.accept)

        fl.addWidget(self.pdf_btn); fl.addWidget(kapat_btn)
        lay.addWidget(footer)

    def pdf_olustur(self):
        ad = (self.personel.ad_soyad or "Personel").replace(" ", "_")
        pdf_yolu, _ = QFileDialog.getSaveFileName(
            self, "Özlük Evrakları PDF Kaydet",
            f"{ad}_Ozluk_Evraklari.pdf", "PDF (*.pdf)"
        )
        if not pdf_yolu:
            return

        self.pdf_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.durum_lbl2.setText("İşleniyor, lütfen bekleyin...")
        self.durum_lbl2.setVisible(True)

        self.worker = DonusturmeWorker(self.sablon_yol, self.personel, pdf_yolu)
        self.worker.tamamlandi.connect(self._islem_bitti)
        self.worker.start()

    def _islem_bitti(self, basarili, hata_mesaj, ek_dosya):
        self.progress.setVisible(False)
        self.pdf_btn.setEnabled(True)
        self.durum_lbl2.setVisible(False)

        if basarili:
            ModernMesaj.basari(
                self,
                "Özlük evrakları başarıyla oluşturuldu!\n"
                "Orijinal Word formatı ve imza alanları korundu."
            )
            self.accept()
        else:
            if ek_dosya and os.path.exists(ek_dosya):
                ModernMesaj.uyari(
                    self,
                    f"{hata_mesaj}\n\nWord dosyası kaydedildi:\n{os.path.basename(ek_dosya)}"
                )
            else:
                ModernMesaj.hata(self, hata_mesaj)
