# pdf_generator.py (Güncel - avans, devamsızlık, haciz detaylarıyla)

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import os

# Windows'ta Arial fontunu dene (Türkçe karakter için)
arial_path = "C:/Windows/Fonts/arial.ttf"
if os.path.exists(arial_path):
    pdfmetrics.registerFont(TTFont('Arial', arial_path))
    font_name = 'Arial'
else:
    font_name = 'Helvetica'  # yedek (Türkçe sorunlu)

def bordro_pdf_olustur(personel_adi, ay, sonuc_dict):
    """
    sonuc_dict içinde şunlar olmalı:
        brut, avans, avans_detay, toplam_haciz, haciz_detay,
        devamsizlik_gun, devamsizlik_kesinti, devamsizlik_detay,
        net, banka, elden
    """
    klasor = "bordrolar"
    if not os.path.exists(klasor):
        os.makedirs(klasor)

    dosya_adi = f"{klasor}/{personel_adi}_{ay}.pdf".replace(" ", "_").replace("ı", "i")

    doc = SimpleDocTemplate(dosya_adi)
    elements = []

    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle(
        name='Normal',
        fontName=font_name,
        fontSize=10,
        leading=12
    )
    style_bold = ParagraphStyle(
        name='Bold',
        fontName=font_name,
        fontSize=12,
        leading=14,
        alignment=1  # center
    )

    # Başlık
    elements.append(Paragraph(f"<b>BORDRO</b>", style_bold))
    elements.append(Spacer(1, 0.2 * inch))

    # Personel ve Dönem
    elements.append(Paragraph(f"Personel: {personel_adi}", style_normal))
    elements.append(Paragraph(f"Dönem: {ay}", style_normal))
    elements.append(Spacer(1, 0.2 * inch))

    # Ana tablo (özet)
    data = [
        ["Brüt Maaş", f"{sonuc_dict['brut']:.2f} TL"],
        ["Avans", f"{sonuc_dict['avans']:.2f} TL"],
        ["Devamsızlık Kesintisi", f"{sonuc_dict['devamsizlik_kesinti']:.2f} TL ({sonuc_dict['devamsizlik_gun']} gün)"],
        ["Haciz Kesintisi", f"{sonuc_dict['toplam_haciz']:.2f} TL"],
        ["Net Maaş (Toplam)", f"{sonuc_dict['net']:.2f} TL"],
        ["Bankaya Yatan", f"{sonuc_dict['banka']:.2f} TL"],
        ["Elden Ödenen", f"{sonuc_dict['elden']:.2f} TL"]
    ]

    table = Table(data, colWidths=[200, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))

    # Detaylar
    elements.append(Paragraph("<b>Avans Detayları:</b>", style_normal))
    if sonuc_dict.get('avans_detay'):
        elements.append(Paragraph(sonuc_dict['avans_detay'].replace("\n", "<br/>"), style_normal))
    else:
        elements.append(Paragraph("Avans bulunmamaktadır.", style_normal))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("<b>Devamsızlık Detayları:</b>", style_normal))
    if sonuc_dict.get('devamsizlik_detay') and sonuc_dict['devamsizlik_detay'] != "Yok":
        elements.append(Paragraph(sonuc_dict['devamsizlik_detay'].replace("\n", "<br/>"), style_normal))
    else:
        elements.append(Paragraph("Devamsızlık yok.", style_normal))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("<b>Haciz Detayları:</b>", style_normal))
    if sonuc_dict.get('haciz_detay'):
        elements.append(Paragraph(sonuc_dict['haciz_detay'].replace("\n", "<br/>"), style_normal))
    else:
        elements.append(Paragraph("Haciz yok.", style_normal))

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("Bu bordro sistem tarafından oluşturulmuştur.", style_normal))

    doc.build(elements)
    return dosya_adi