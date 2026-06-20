# PYS Mobile - Android APK Derleme (Google Colab)
#
# Bu notebook'u Google Colab'da çalıştırarak APK oluşturabilirsiniz.
# Adım 1: mobile.zip dosyasını bu notebook ile aynı dizine yükleyin
# Adım 2: Tüm hücreleri sırasıyla çalıştırın
# Adım 3: Oluşan APK'yi indirin

# ═══════════════════════════════════════════════════════════
# HÜCRE 1: Buildozer ve bağımlılıkları kur
# ═══════════════════════════════════════════════════════════
!sudo apt-get update
!sudo apt-get install -y python3-pip build-essential git ffmpeg \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev \
    zlib1g-dev libgstreamer1.0-0 gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good openjdk-17-jdk autoconf automake \
    libtool pkg-config cmake unzip lld

!pip install --upgrade pip setuptools wheel cython virtualenv
!pip install buildozer kivy kivymd sqlalchemy psycopg2-binary requests

# ═══════════════════════════════════════════════════════════
# HÜCRE 2: Zip dosyasını yükle ve çıkar
# ═══════════════════════════════════════════════════════════
from google.colab import files
import os, zipfile

# Zip dosyasını yükle
uploaded = files.upload()

# Çıkar
zip_filename = list(uploaded.keys())[0]
with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
    zip_ref.extractall('/content/pys_mobile')

# İçeriği göster
for root, dirs, files_list in os.walk('/content/pys_mobile'):
    level = root.replace('/content/pys_mobile', '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for file in files_list:
        print(f'{subindent}{file}')

os.chdir('/content/pys_mobile')
print(f'\nÇalışma dizini: {os.getcwd()}')

# ═══════════════════════════════════════════════════════════
# HÜCRE 3: buildozer.spec'i ayarla
# ═══════════════════════════════════════════════════════════
%%writefile buildozer.spec
[app]

title = PYS Mobile
package.name = pysmobile
package.domain = com.pys
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

requirements = python3,kivy==2.3.1,kivymd==1.2.0,sqlalchemy,requests,hashlib

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True

android.release_artifact = apk

p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1

# ═══════════════════════════════════════════════════════════
# HÜCRE 4: Android SDK'yi kur
# ═══════════════════════════════════════════════════════════
import os

ANDROID_SDK_ROOT = os.path.expanduser('~/android-sdk-cmdline-tools')
os.makedirs(ANDROID_SDK_ROOT, exist_ok=True)

# Android SDK Command Line Tools
!cd {ANDROID_SDK_ROOT} && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip && \
    unzip -qo commandlinetools-linux-11076708_latest.zip && \
    mkdir -p cmdline-tools/latest && \
    mv cmdline-tools/{bin,lib,NOTICE.txt,source.properties} cmdline-tools/latest/ 2>/dev/null || true

os.environ['ANDROID_SDK_ROOT'] = ANDROID_SDK_ROOT
os.environ['ANDROID_HOME'] = ANDROID_SDK_ROOT

# Accept licenses ve SDK kur
!yes | {ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager --licenses
!{ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager "platform-tools" \
    "platforms;android-33" "build-tools;33.0.2"

print("Android SDK kuruldu!")

# ═══════════════════════════════════════════════════════════
# HÜCRE 5: APK'yi derle (bu uzun sürer ~15-30 dk)
# ═══════════════════════════════════════════════════════════
!buildozer -v android debug 2>&1 | tail -100

# ═══════════════════════════════════════════════════════════
# HÜCRE 6: APK'yi indir
# ═══════════════════════════════════════════════════════════
import os, glob

apk_files = glob.glob('/content/pys_mobile/bin/*.apk')
if apk_files:
    for apk in apk_files:
        print(f"APK bulundu: {apk}")
        files.download(apk)
        print("İndirme başladı!")
else:
    print("APK bulunamadı. Bin klasörünü kontrol edin:")
    if os.path.exists('/content/pys_mobile/bin'):
        print(os.listdir('/content/pys_mobile/bin'))
    else:
        print("bin klasörü yok - derleme başarısız olmuş olabilir")
