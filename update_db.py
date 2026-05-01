import sqlite3
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE personel ADD COLUMN baba_adi TEXT")
except: pass
try:
    cursor.execute("ALTER TABLE personel ADD COLUMN dogum_yeri TEXT")
except: pass
try:
    cursor.execute("ALTER TABLE personel ADD COLUMN dogum_tarihi DATE")
except: pass
conn.commit()
conn.close()
print("Sütunlar eklendi.")