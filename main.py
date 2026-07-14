import subprocess
import time
from stok_takip import StokTakip
from tedarikci_yonetimi import TedarikciYonetimi
from config import VARSAYILAN_KRITIK_SEVIYE

def erp_sistemini_calistir():
    print("=================================================")
    print("      YBS - ERP YÖNETİM SİSTEMİ BAŞLATILIYOR     ")
    print("=================================================\n")

    # 1. Stok Kontrolü ve Analiz Katmanı
    print("[ADIM 1] Stok verileri analiz ediliyor...")
    stok_modulu = StokTakip(default_kritik_seviye=VARSAYILAN_KRITIK_SEVIYE)

    if not stok_modulu.baglan():
        print("Sistem durduruldu: Veritabanı bağlantısı yok.")
        return

    # Veriyi sadece çeken fonksiyonu kullanıyoruz, ekrana yazdırmıyoruz
    rapor = stok_modulu.kritik_stok_raporu_getir()
    stok_modulu.raporu_yazdir()  # Detaylı raporu yöneticiye göster
    stok_modulu.baglantiyi_kapat()

    time.sleep(1)  # Sistem akışı hissi için kısa bir bekleme

    # 2. Tedarikçi Yönetimi ve Otomatik Sipariş Katmanı
    # 2. Tedarikçi Yönetimi ve Otomatik Sipariş Katmanı
    print("\n[ADIM 2] Tedarikçi ve Satın Alma modülü devreye giriyor...")
    tedarikci_modulu = TedarikciYonetimi()

    if tedarikci_modulu.baglan():
        for satir in rapor:
            urun_adi = satir[0]
            mevcut_stok = int(satir[1]) if satir[1] is not None else 0

            # Eğer mevcut stok kritik seviyenin altına indiyse sistem otomatik sipariş geçecek
            tedarikci_modulu.satin_alma_talebi_olustur(
                urun_adi=urun_adi,
                mevcut_stok=mevcut_stok,
                kritik_seviye=VARSAYILAN_KRITIK_SEVIYE
            )

        tedarikci_modulu.baglantiyi_kapat()

    time.sleep(1)
    # 3. Yönetici Paneli (Dashboard) Başlatma
    print("\n[ADIM 3] Streamlit Yönetici Paneli başlatılıyor...")
    print("Tarayıcınızda otomatik olarak yeni bir sekme açılacaktır.\n")
    print("=================================================")
    print("       GÜNLÜK ERP OPERASYONU TAMAMLANDI          ")
    print("=================================================")

    try:
        subprocess.run(["streamlit", "run", "dashboard.py"])
    except KeyboardInterrupt:
        print("\nSistem kullanıcı tarafından kapatıldı.")
    except Exception as e:
        print(f"Dashboard başlatılamadı: {e}")

if __name__ == "__main__":
    erp_sistemini_calistir()
