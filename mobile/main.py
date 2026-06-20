# -*- coding: utf-8 -*-
import os
import sys
import hashlib
from datetime import date

os.environ['KIVY_LOG_LEVEL'] = 'warning'
os.environ['KIVY_BUILD_DIR'] = os.path.dirname(os.path.abspath(__file__))

from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.core.window import Window

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem, ThreeLineListItem
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.screenmanager import MDScreenManager

from database import get_session, set_database, get_db_type, load_config

KV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kv')
for kv_file in os.listdir(KV_DIR):
    if kv_file.endswith('.kv'):
        with open(os.path.join(KV_DIR, kv_file), 'r', encoding='utf-8') as f:
            Builder.load_string(f.read())


class LoginScreen(MDScreen):
    def try_login(self):
        username = self.ids.username_field.text.strip()
        password = self.ids.password_field.text.strip()
        if not username or not password:
            self.ids.status_label.text = "Kullanıcı adı ve şifre gerekli"
            return
        from models import Kullanici
        session = get_session()
        try:
            user = session.query(Kullanici).filter_by(username=username).first()
            if user and user.password_hash == hashlib.sha256(password.encode()).hexdigest():
                self.manager.current_user = user
                self.manager.current = 'main_menu'
                self.ids.status_label.text = ""
            else:
                self.ids.status_label.text = "Geçersiz kullanıcı adı veya şifre"
        except Exception as e:
            self.ids.status_label.text = f"Hata: {str(e)}"
        finally:
            session.close()


class MainMenuScreen(MDScreen):
    def on_enter(self):
        user = self.manager.current_user
        if user:
            self.ids.welcome_label.text = f"Hoş Geldin, {user.ad_soyad}"

    def go_personel(self):
        self.manager.current = 'personel'

    def go_puantaj(self):
        self.manager.current = 'puantaj'

    def go_bordro(self):
        self.manager.current = 'bordro'

    def go_haciz(self):
        self.manager.current = 'haciz'

    def go_avans(self):
        self.manager.current = 'avans'

    def go_izin(self):
        self.manager.current = 'izin'

    def go_kasa(self):
        self.manager.current = 'kasa'

    def go_sigara(self):
        self.manager.current = 'sigara'

    def go_ayarlar(self):
        self.manager.current = 'ayarlar'

    def logout(self):
        self.manager.current = 'login'


class PersonelScreen(MDScreen):
    def on_enter(self):
        self.load_data()

    def load_data(self):
        from models import Personel
        session = get_session()
        try:
            arama = self.ids.search_field.text.strip().lower() if hasattr(self.ids, 'search_field') else ""
            query = session.query(Personel).order_by(Personel.ad_soyad)
            if arama:
                query = query.filter(Personel.ad_soyad.ilike(f"%{arama}%"))
            personeller = query.all()

            self.ids.personel_list.clear_widgets()
            for p in personeller:
                item = ThreeLineListItem(
                    text=f"{p.ad_soyad or ''}",
                    secondary_text=f"Sicil: {p.sicil_no or '-'}",
                    tertiary_text=f"Durum: {p.durum or '-'}",
                )
                self.ids.personel_list.add_widget(item)

            if not personeller:
                self.ids.personel_list.add_widget(
                    OneLineListItem(text="Personel bulunamadı")
                )
        except Exception as e:
            self.ids.personel_list.add_widget(
                OneLineListItem(text=f"Hata: {str(e)}")
            )
        finally:
            session.close()

    def go_back(self):
        self.manager.current = 'main_menu'


class PuantajScreen(MDScreen):
    def on_enter(self):
        today = date.today()
        self.ids.year_label.text = str(today.year)
        self.ids.month_label.text = str(today.month)
        self.load_data()

    def load_data(self):
        from models import Personel, Puantaj
        session = get_session()
        try:
            yil = int(self.ids.year_label.text)
            ay = int(self.ids.month_label.text)
            import calendar
            gun_sayisi = calendar.monthrange(yil, ay)[1]

            personeller = session.query(Personel).filter(
                Personel.durum.in_(["Aktif", "Pasif"])
            ).order_by(Personel.ad_soyad).all()

            self.ids.puantaj_list.clear_widgets()
            for p in personeller:
                saved = session.query(Puantaj).filter(
                    Puantaj.personel_id == p.id,
                    Puantaj.yil == yil,
                    Puantaj.ay == ay
                ).first()
                gunler = ""
                for g in range(1, min(gun_sayisi + 1, 16)):
                    val = getattr(saved, f"gun_{g}", "") if saved else ""
                    gunler += f"{val or '-'}"
                if gun_sayisi > 15:
                    gunler += "..."
                item = TwoLineListItem(
                    text=p.ad_soyad or '',
                    secondary_text=gunler
                )
                self.ids.puantaj_list.add_widget(item)

            if not personeller:
                self.ids.puantaj_list.add_widget(
                    OneLineListItem(text="Personel bulunamadı")
                )
        except Exception as e:
            self.ids.puantaj_list.add_widget(OneLineListItem(text=f"Hata: {str(e)}"))
        finally:
            session.close()

    def go_back(self):
        self.manager.current = 'main_menu'


class BordroScreen(MDScreen):
    def go_back(self):
        self.manager.current = 'main_menu'


class HacizScreen(MDScreen):
    def go_back(self):
        self.manager.current = 'main_menu'


class AvansScreen(MDScreen):
    def go_back(self):
        self.manager.current = 'main_menu'


class IzinScreen(MDScreen):
    def go_back(self):
        self.manager.current = 'main_menu'


class KasaScreen(MDScreen):
    def go_back(self):
        self.manager.current = 'main_menu'


class SigaraScreen(MDScreen):
    def go_back(self):
        self.manager.current = 'main_menu'


class AyarlarScreen(MDScreen):
    def go_back(self):
        self.manager.current = 'main_menu'


class PYSManager(MDScreenManager):
    current_user = ObjectProperty(None, allownone=True)


class PYSMobileApp(MDApp):
    def build(self):
        self.title = "PYS Mobile"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Dark"

        Window.size = (400, 750)

        sm = PYSManager()

        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainMenuScreen(name='main_menu'))
        sm.add_widget(PersonelScreen(name='personel'))
        sm.add_widget(PuantajScreen(name='puantaj'))
        sm.add_widget(BordroScreen(name='bordro'))
        sm.add_widget(HacizScreen(name='haciz'))
        sm.add_widget(AvansScreen(name='avans'))
        sm.add_widget(IzinScreen(name='izin'))
        sm.add_widget(KasaScreen(name='kasa'))
        sm.add_widget(SigaraScreen(name='sigara'))
        sm.add_widget(AyarlarScreen(name='ayarlar'))

        return sm


if __name__ == '__main__':
    PYSMobileApp().run()
