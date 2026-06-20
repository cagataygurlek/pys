# models.py

from sqlalchemy import (
    Column, Integer, String, Float, Date, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

# -------------------------
# ŞUBE
# -------------------------
class Sube(Base):
    __tablename__ = "sube"
    id = Column(Integer, primary_key=True)
    ad = Column(String(100), nullable=False)
    personel = relationship("Personel", back_populates="sube")

# -------------------------
# GÖREV
# -------------------------
class Gorev(Base):
    __tablename__ = "gorev"
    id = Column(Integer, primary_key=True)
    ad = Column(String(100), nullable=False)
    personel = relationship("Personel", back_populates="gorev")

# -------------------------
# ÖZEL DURUM
# -------------------------
class OzelDurum(Base):
    __tablename__ = "ozel_durum"
    id = Column(Integer, primary_key=True)
    ad = Column(String(100), nullable=False)
    personel = relationship("Personel", back_populates="ozel_durum")

# -------------------------
# İZİN TÜRÜ
# -------------------------
class IzinTuru(Base):
    __tablename__ = "izin_turu"
    
    id = Column(Integer, primary_key=True)
    ad = Column(String(50), nullable=False)
    renk = Column(String(20), default="#3498db")
    ucretli_mi = Column(Boolean, default=True)
    
    izinler = relationship("Izin", back_populates="izin_turu")

# -------------------------
# İZİN
# -------------------------
class Izin(Base):
    __tablename__ = "izin"
    
    id = Column(Integer, primary_key=True)
    personel_id = Column(Integer, ForeignKey("personel.id"), nullable=False)
    izin_turu_id = Column(Integer, ForeignKey("izin_turu.id"), nullable=False)
    baslangic_tarihi = Column(Date, nullable=False)
    bitis_tarihi = Column(Date, nullable=False)
    gun_sayisi = Column(Integer, nullable=False)
    aciklama = Column(Text)
    durum = Column(String(20), default="Onay Bekliyor")
    talep_tarihi = Column(Date, default=datetime.date.today)
    onaylayan = Column(String(100))
    onay_tarihi = Column(Date)
    
    personel = relationship("Personel", back_populates="izinler")
    izin_turu = relationship("IzinTuru", back_populates="izinler")

# -------------------------
# PUANTAJ
# -------------------------
class Puantaj(Base):
    __tablename__ = "puantajlar"

    id = Column(Integer, primary_key=True, index=True)
    personel_id = Column(Integer, ForeignKey("personel.id"))
    yil = Column(Integer)
    ay = Column(Integer)
    
    gun_1 = Column(String(10), nullable=True)
    gun_2 = Column(String(10), nullable=True)
    gun_3 = Column(String(10), nullable=True)
    gun_4 = Column(String(10), nullable=True)
    gun_5 = Column(String(10), nullable=True)
    gun_6 = Column(String(10), nullable=True)
    gun_7 = Column(String(10), nullable=True)
    gun_8 = Column(String(10), nullable=True)
    gun_9 = Column(String(10), nullable=True)
    gun_10 = Column(String(10), nullable=True)
    gun_11 = Column(String(10), nullable=True)
    gun_12 = Column(String(10), nullable=True)
    gun_13 = Column(String(10), nullable=True)
    gun_14 = Column(String(10), nullable=True)
    gun_15 = Column(String(10), nullable=True)
    gun_16 = Column(String(10), nullable=True)
    gun_17 = Column(String(10), nullable=True)
    gun_18 = Column(String(10), nullable=True)
    gun_19 = Column(String(10), nullable=True)
    gun_20 = Column(String(10), nullable=True)
    gun_21 = Column(String(10), nullable=True)
    gun_22 = Column(String(10), nullable=True)
    gun_23 = Column(String(10), nullable=True)
    gun_24 = Column(String(10), nullable=True)
    gun_25 = Column(String(10), nullable=True)
    gun_26 = Column(String(10), nullable=True)
    gun_27 = Column(String(10), nullable=True)
    gun_28 = Column(String(10), nullable=True)
    gun_29 = Column(String(10), nullable=True)
    gun_30 = Column(String(10), nullable=True)
    gun_31 = Column(String(10), nullable=True)

    personel = relationship("Personel", back_populates="puantajlar")

# -------------------------
# BORDRO
# -------------------------
class Bordro(Base):
    __tablename__ = "bordro"
    id = Column(Integer, primary_key=True)
    personel_id = Column(Integer, ForeignKey("personel.id"), nullable=False)
    yil = Column(Integer, nullable=False)
    ay = Column(Integer, nullable=False)
    
    toplam_net_maas = Column(Float, default=0.0)
    resmi_maas = Column(Float, default=0.0)
    icra_kesintisi = Column(Float, default=0.0)
    elden_odenecek = Column(Float, default=0.0)
    
    personel = relationship("Personel")
    haciz_odemeleri = relationship("HacizOdeme", back_populates="bordro")
    maas_odemeleri = relationship("MaasOdeme", back_populates="bordro")  # YENİ

# -------------------------
# HACİZ
# -------------------------
class Haciz(Base):
    __tablename__ = "haciz"

    id = Column(Integer, primary_key=True)
    personel_id = Column(Integer, ForeignKey("personel.id"), nullable=False)
    dosya_no = Column(String(50), nullable=False)
    borc_miktari = Column(Float, default=0.0)
    aylik_kesinti = Column(Float, default=0.0)
    kesinti_orani = Column(Float, default=0.0)
    baslangic_tarihi = Column(Date, nullable=False)
    bitis_tarihi = Column(Date, nullable=True)
    aciklama = Column(Text)
    durum = Column(String(20), default="Aktif")
    alacakli_kurum = Column(String(200))
    iban = Column(String(34), nullable=True)
    kalan_borc = Column(Float, default=0.0)
    gecikme_faizi = Column(Float, default=0.0)   # <--- YENİ ALAN
    
    personel = relationship("Personel", back_populates="hacizler")
    odemeler = relationship("HacizOdeme", back_populates="haciz", cascade="all, delete-orphan")
    

# -------------------------
# HACİZ ÖDEME KAYITLARI
# -------------------------
class HacizOdeme(Base):
    __tablename__ = "haciz_odeme"
    
    id = Column(Integer, primary_key=True)
    haciz_id = Column(Integer, ForeignKey("haciz.id"), nullable=False)
    bordro_id = Column(Integer, ForeignKey("bordro.id"), nullable=True)
    tarih = Column(Date, nullable=False, default=datetime.date.today)
    tutar = Column(Float, nullable=False)
    aciklama = Column(Text)

    haciz = relationship("Haciz", back_populates="odemeler")
    bordro = relationship("Bordro", back_populates="haciz_odemeleri")

# -------------------------
# AVANS
# -------------------------
class Avans(Base):
    __tablename__ = "avans"
    id = Column(Integer, primary_key=True)
    personel_id = Column(Integer, ForeignKey("personel.id"), nullable=False)
    tarih = Column(Date, nullable=False)
    tutar = Column(Float, nullable=False, default=0.0)
    aciklama = Column(Text)
    
    personel = relationship("Personel", back_populates="avanslar")

# -------------------------
# KASA AÇIĞI
# -------------------------
class KasaAcigi(Base):
    __tablename__ = "kasa_acigi"
    id = Column(Integer, primary_key=True)
    personel_id = Column(Integer, ForeignKey("personel.id"), nullable=False)
    tarih = Column(Date, nullable=False)
    tutar = Column(Float, nullable=False, default=0.0)
    aciklama = Column(Text)
    
    personel = relationship("Personel", back_populates="kasa_aciklari")

# -------------------------
# SİGARA AÇIĞI
# -------------------------
class SigaraAcigi(Base):
    __tablename__ = "sigara_acigi"
    id = Column(Integer, primary_key=True)
    personel_id = Column(Integer, ForeignKey("personel.id"), nullable=False)
    tarih = Column(Date, nullable=False)
    tutar = Column(Float, nullable=False, default=0.0)
    aciklama = Column(Text)
    
    personel = relationship("Personel", back_populates="sigara_aciklari")

# -------------------------
# SİSTEM AYARLARI
# -------------------------
class SistemAyarlari(Base):
    __tablename__ = "sistem_ayarlari"
    
    id = Column(Integer, primary_key=True)
    anahtar = Column(String(50), unique=True, nullable=False)
    deger = Column(String(200))
    aciklama = Column(String(200))

# -------------------------
# YILLIK İZİN
# -------------------------
class YillikIzin(Base):
    __tablename__ = "yillik_izin"
    id = Column(Integer, primary_key=True)
    personel_id = Column(Integer, ForeignKey("personel.id"), nullable=False)
    yil = Column(Integer, nullable=False)
    tanimlanan_izin = Column(Integer, default=0)

    personel = relationship("Personel", back_populates="yillik_izinler")

# -------------------------
# MAAŞ ÖDEMESİ (YENİ)
# -------------------------
class MaasOdeme(Base):
    __tablename__ = "maas_odemeleri"
    id = Column(Integer, primary_key=True)
    personel_id = Column(Integer, ForeignKey("personel.id"), nullable=False)
    bordro_id = Column(Integer, ForeignKey("bordro.id"), nullable=False)
    tarih = Column(Date, nullable=False, default=datetime.date.today)
    tutar = Column(Float, nullable=False)
    aciklama = Column(Text, nullable=True)

    personel = relationship("Personel", back_populates="maas_odemeleri")
    bordro = relationship("Bordro", back_populates="maas_odemeleri")

# -------------------------
# PERSONEL
# -------------------------
class Personel(Base):
    __tablename__ = "personel"

    id = Column(Integer, primary_key=True)
    sicil_no = Column(String(50), unique=True)
    ad_soyad = Column(String(200), nullable=False)
    tc_no = Column(String(11), nullable=True)
    iban = Column(String(34), nullable=True)
    telefon = Column(String(20), nullable=True)
    ise_baslama = Column(Date, nullable=False, default=datetime.date.today)
    isten_ayrilma = Column(Date, nullable=True)
    maas = Column(Float, nullable=False, default=0.0)
    durum = Column(String(20), default="Aktif")
    aciklama = Column(Text, nullable=True)
    kalan_yillik_izin = Column(Float, default=0.0)

    sube_id = Column(Integer, ForeignKey("sube.id"))
    gorev_id = Column(Integer, ForeignKey("gorev.id"))
    ozel_durum_id = Column(Integer, ForeignKey("ozel_durum.id"))

    # İlişkiler
    sube = relationship("Sube", back_populates="personel")
    gorev = relationship("Gorev", back_populates="personel")
    ozel_durum = relationship("OzelDurum", back_populates="personel")
    puantajlar = relationship("Puantaj", back_populates="personel", cascade="all, delete-orphan")
    izinler = relationship("Izin", back_populates="personel", cascade="all, delete-orphan")
    hacizler = relationship("Haciz", back_populates="personel", cascade="all, delete-orphan")
    avanslar = relationship("Avans", back_populates="personel", cascade="all, delete-orphan")
    yillik_izinler = relationship("YillikIzin", back_populates="personel", cascade="all, delete-orphan")
    kasa_aciklari = relationship("KasaAcigi", back_populates="personel", cascade="all, delete-orphan")
    sigara_aciklari = relationship("SigaraAcigi", back_populates="personel", cascade="all, delete-orphan")
    maas_odemeleri = relationship("MaasOdeme", back_populates="personel", cascade="all, delete-orphan")  # YENİ
# -------------------------
# BAŞVURU ADAYI
# -------------------------
class BasvuruAday(Base):
    __tablename__ = "basvuru_aday"

    id = Column(Integer, primary_key=True)
    basvuru_tarihi = Column(Date, nullable=False, default=datetime.date.today)
    pozisyon = Column(String(100), nullable=True)

    # A. Kişisel
    ad = Column(String(100), nullable=False)
    soyad = Column(String(100), nullable=False)
    tc_no = Column(String(11), nullable=True)
    dogum_yeri = Column(String(100), nullable=True)
    dogum_tarihi = Column(Date, nullable=True)
    cinsiyet = Column(String(10), nullable=True)
    adres = Column(Text, nullable=True)
    telefon_ev = Column(String(20), nullable=True)
    telefon_cep1 = Column(String(20), nullable=True)
    telefon_cep2 = Column(String(20), nullable=True)
    eposta = Column(String(100), nullable=True)

    # Askerlik
    askerlik_durum = Column(String(20), nullable=True)  # Tamamlandı / Tecilli / Muaf
    askerlik_tarih = Column(String(50), nullable=True)
    askerlik_muafiyet = Column(String(200), nullable=True)

    # Ehliyet / Medeni / Sigara
    surucu_belgesi = Column(String(50), nullable=True)
    medeni_durum = Column(String(10), nullable=True)
    es_meslegi = Column(String(100), nullable=True)
    cocuk_sayisi = Column(Integer, nullable=True)
    sigara = Column(String(5), nullable=True)

    # B. Bilgisayar
    excel_seviye = Column(String(20), nullable=True)
    word_seviye = Column(String(20), nullable=True)
    powerpoint_seviye = Column(String(20), nullable=True)

    # D. Diğer
    saglik_sorunu = Column(String(5), nullable=True)
    saglik_aciklama = Column(Text, nullable=True)
    mahkumiyet = Column(String(5), nullable=True)
    mahkumiyet_aciklama = Column(Text, nullable=True)
    acil_kisi_adsoyad = Column(String(100), nullable=True)
    acil_kisi_yakinlik = Column(String(50), nullable=True)
    acil_kisi_telefon = Column(String(20), nullable=True)

    # E. Ücret
    ucret_beklenti = Column(Float, nullable=True)

    # F. Notlar
    notlar = Column(Text, nullable=True)

    # Durum
    durum = Column(String(20), default="Beklemede")  # Beklemede / Uygun / Uygun Değil / İşe Alındı

    # İlişkiler
    tecrubeleri = relationship("BasvuruTecrube", back_populates="aday", cascade="all, delete-orphan")


# -------------------------
# BAŞVURU İŞ TECRÜBESİ
# -------------------------
class BasvuruTecrube(Base):
    __tablename__ = "basvuru_tecrube"

    id = Column(Integer, primary_key=True)
    aday_id = Column(Integer, ForeignKey("basvuru_aday.id"), nullable=False)
    firma_adi = Column(String(200), nullable=True)
    gorev = Column(String(100), nullable=True)
    giris_tarihi = Column(String(20), nullable=True)
    cikis_tarihi = Column(String(20), nullable=True)
    ayrilma_sebebi = Column(String(200), nullable=True)
    alinan_ucret = Column(String(50), nullable=True)

    aday = relationship("BasvuruAday", back_populates="tecrubeleri")
