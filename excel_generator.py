from openpyxl import Workbook
import os


def excel_maas_listesi_olustur(ay, maas_listesi):

    klasor = "excel_raporlar"
    if not os.path.exists(klasor):
        os.makedirs(klasor)

    dosya_adi = f"{klasor}/{ay}_Maas_Listesi.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Maas Listesi"

    # Başlıklar
    ws.append(["Personel", "Brüt Maaş", "Avans", "Toplam Haciz", "Net Maaş"])

    for personel in maas_listesi:
        ws.append([
            personel["ad"],
            personel["brut"],
            personel["avans"],
            personel["toplam_haciz"],
            personel["net"]
        ])

    wb.save(dosya_adi)

    return dosya_adi
