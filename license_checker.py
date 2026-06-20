"""
Lisans kontrol modülü — Google Sheets API + 7 gün offline grace period.
Google Sheets sütun sırası:
  A: Anahtar  B: Durum(aktif/pasif)  C: Bitiş Tarihi (GG/AA/YYYY)
  D: Firma Adı  E: Max Kullanıcı  F: Max Şube  G: MAC Adresi (boşsa her cihaz)
"""

import json
import os
import sys
import datetime
import uuid

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

GRACE_DAYS = 7

# ─── Yol yardımı ────────────────────────────────────────────────────────

def _appdata_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "PYS")
    os.makedirs(d, exist_ok=True)
    return d

def _cache_path():
    return os.path.join(_appdata_dir(), "lisans_cache.json")

def _service_account_path():
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "service_account.json")

# ─── MAC adresi ─────────────────────────────────────────────────────────

def get_mac_address():
    mac = uuid.getnode()
    return ":".join(f"{(mac >> i) & 0xFF:02x}" for i in range(40, -1, -8))

# ─── Local cache ────────────────────────────────────────────────────────

def _load_cache():
    p = _cache_path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_cache(data):
    with open(_cache_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _save_key_only(key):
    cache = _load_cache()
    cache["license_key"] = key
    _save_cache(cache)

# ─── Google Sheets okuma ───────────────────────────────────────────────

_SPREADSHEET_ID = "1jM7ZqqbFNo-DUvufcWIUBbziyrBU7eJw7xc01x3ktVg"
_RANGE = "Sayfa1!A:G"

def _get_service():
    if not HAS_GOOGLE:
        return None
    sa_path = _service_account_path()
    if not os.path.exists(sa_path):
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            sa_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
        return build("sheets", "v4", credentials=creds, cache_discovery=False)
    except Exception:
        return None

def _normalize_header(h):
    tr_map = str.maketrans(
        {"İ": "i", "ı": "i", "Ş": "s", "ş": "s", "Ç": "c", "ç": "c",
         "Ğ": "g", "ğ": "g", "Ü": "u", "ü": "u", "Ö": "o", "ö": "o"}
    )
    return h.strip().lower().translate(tr_map).replace("  ", " ")

def _fetch_licenses():
    service = _get_service()
    if not service or not _SPREADSHEET_ID:
        return None
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=_SPREADSHEET_ID, range=_RANGE
        ).execute()
        rows = result.get("values", [])
        if not rows:
            return []
        headers = [_normalize_header(h) for h in rows[0]]
        licenses = []
        for row in rows[1:]:
            entry = {}
            for i, h in enumerate(headers):
                entry[h] = row[i].strip() if i < len(row) else ""
            licenses.append(entry)
        return licenses
    except Exception:
        return None

# ─── Ana kontrol ────────────────────────────────────────────────────────

def check_license(license_key=None):
    """
    Retorna: (gecerli: bool, mesaj: str, bitis_tarihi: str|None)
    """
    cache = _load_cache()

    if license_key is None:
        license_key = cache.get("license_key", "")

    if not license_key:
        return False, "Lisans anahtarı bulunamadı.", None

    # Google Sheets'ten çek
    licenses = _fetch_licenses()

    if licenses is None:
        # İnternet yok veya service_account yok → grace period kontrol
        last_ok = cache.get("last_ok_date")
        if last_ok:
            try:
                last_dt = datetime.datetime.strptime(last_ok, "%Y-%m-%d").date()
                diff = (datetime.date.today() - last_dt).days
                if diff <= GRACE_DAYS:
                    bitis = cache.get("bitis_tarihi", "")
                    firma = cache.get("firma_adi", "")
                    kalan = GRACE_DAYS - diff
                    return True, (
                        f"Çevrimdışı — Son başarılı kontrol: {last_ok} "
                        f"({kalan} gün kaldı). Firma: {firma}"
                    ), bitis
                else:
                    return False, (
                        f"Çevrimdışı grace period süresi doldu "
                        f"({GRACE_DAYS} gün). İnternet bağlantısı gerekli."
                    ), None
            except Exception:
                pass
        return False, (
            "İnternet bağlantısı yok ve önceki bir doğrulama bulunamadı. "
            "Lütfen internete bağlanın."
        ), None

    # Online doğrulama
    for lic in licenses:
        if lic.get("anahtar", "") == license_key:
            durum = lic.get("durum", "").lower()
            if durum != "aktif":
                _save_key_only(license_key)
                return False, f"Lisans durumu: {durum.upper()}.", None

            bitis_str = lic.get("bitis tarihi", "")
            if bitis_str:
                try:
                    bitis_dt = datetime.datetime.strptime(bitis_str, "%d/%m/%Y").date()
                    if bitis_dt < datetime.date.today():
                        _save_key_only(license_key)
                        return False, (
                            f"Lisansın süresi dolmuş ({bitis_str})."
                        ), bitis_str
                except ValueError:
                    pass

            mac_izinli = lic.get("mac adresi", "").strip()
            if mac_izinli:
                my_mac = get_mac_address().lower()
                if mac_izinli.lower() != my_mac:
                    _save_key_only(license_key)
                    return False, "Bu lisans bu cihaz için geçerli değil.", None

            # Başarılı — cache'i güncelle
            cache["license_key"] = license_key
            cache["last_ok_date"] = datetime.date.today().strftime("%Y-%m-%d")
            cache["bitis_tarihi"] = bitis_str
            cache["firma_adi"] = lic.get("firma adi", "")
            cache["max_kullanici"] = lic.get("max kullanici", "")
            cache["max_sube"] = lic.get("max sube", "")
            _save_cache(cache)

            return True, (
                f"Lisans aktif — Firma: {lic.get('firma adi', '')} "
                f"— Bitiş: {bitis_str}"
            ), bitis_str

    _save_key_only(license_key)
    return False, "Lisans anahtarı kayıtlı değil.", None


def get_saved_key():
    return _load_cache().get("license_key", "")

def set_license_key(key):
    _save_key_only(key)
