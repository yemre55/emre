import os
import mysql.connector
from database import DashboardVeriErisim
from config import VARSAYILAN_KRITIK_SEVIYE, OTOMATIK_SIPARIS_MIKTARI
from mysql.connector import Error
from typing import Optional, Dict
from dotenv import load_dotenv
from config import VARSAYILAN_KRITIK_SEVIYE

load_dotenv()

class TedarikciYonetimi:
    """Stok seviyesi düştüğünde tedarikçi bilgilerini SQL'den çekip sipariş sürecini yönetir."""

    def __init__(
        self,
        host: str = None,
        user: str = None,
        password: str = None,
        database: str = None,
    ):
        # Parametre verilmezse .env'den okunur (root/boş şifre varsayılanı KALDIRILDI)
        self.host = host or os.getenv("DB_HOST")
        self.user = user or os.getenv("DB_USER")
        self.password = password if password is not None else os.getenv("DB_PASSWORD")
        self.database = database or os.getenv("DB_NAME")
        self.db = None
        self.cursor = None

    def baglan(self) -> bool:
        """Veritabanı bağlantısını kurar."""
        try:
            self.db = mysql.connector.connect(
                host=self.host,
                port=int(os.getenv("DB_PORT", 3306)),
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4'
            )
            self.cursor = self.db.cursor(dictionary=True)
            return True
        except Error as e:
            print(f"KRİTİK HATA: Tedarikçi modülü veritabanına bağlanamadı. Detay: {e}")
            return False

    def tedarikci_bilgisi_getir(self, urun_adi: str) -> Optional[Dict]:
        """SQL kullanarak girilen ürünün tedarikçi detaylarını bulur."""
        varsayilan = {"firma": "Bağlantı Yok", "teslimat_gunu": 0, "eposta": None, "telefon": None}
        if not self.db or not self.cursor:
            return varsayilan

        sorgu = """
            SELECT s.SupplierName, s.LeadTimeDays, s.ContactEmail, s.ContactPhone
            FROM Products p
            LEFT JOIN Suppliers s ON p.SupplierID = s.SupplierID
            WHERE p.ProductName = %s
        """
        try:
            self.cursor.execute(sorgu, (urun_adi,))
            sonuc = self.cursor.fetchone()

            if sonuc and sonuc['SupplierName']:
                return {
                    "firma": sonuc['SupplierName'],
                    "teslimat_gunu": sonuc['LeadTimeDays'],
                    "eposta": sonuc['ContactEmail'],
                    "telefon": sonuc['ContactPhone'],
                }
            return {"firma": "Bilinmeyen Tedarikçi (Sisteme Kayıt Edilmeli)", "teslimat_gunu": 0,
                     "eposta": None, "telefon": None}

        except Error as e:
            print(f"HATA: Tedarikçi bilgisi çekilemedi. Detay: {e}")
            return {"firma": "Hata Oluştu", "teslimat_gunu": 0, "eposta": None, "telefon": None}

    def satin_alma_talebi_olustur(
    self,
    urun_adi: str,
    mevcut_stok: int,
    kritik_seviye: int = VARSAYILAN_KRITIK_SEVIYE,
    siparis_miktari: int = OTOMATIK_SIPARIS_MIKTARI,
    ) -> bool:
        """Stok yetersizse tedarikçiyi bulup GERÇEK bir Purchase_Orders kaydı oluşturur."""
        if mevcut_stok >= kritik_seviye:
            print(f"DURUM: {urun_adi} için stok seviyesi yeterli ({mevcut_stok} adet). İşlem yapılmadı.")
            return False

        tedarikci_bilgisi = self.tedarikci_bilgisi_getir(urun_adi)
        return self._siparisi_sisteme_kaydet(urun_adi, mevcut_stok, tedarikci_bilgisi, siparis_miktari)

    def _siparisi_sisteme_kaydet(self, urun_adi: str, mevcut_stok: int, tedarikci_bilgisi: Dict, siparis_miktari: int) -> bool:
        """
        Siparişi Purchase_Orders tablosuna yazar. Mükerrer kontrolü ve INSERT
        mantığı database.py'deki DashboardVeriErisim.otomatik_siparis_taslagi_olustur
        içinde merkezi tutuluyor; hem dashboard.py hem main.py aynı tek
        kaynaktan sipariş açıyor, artık iki farklı implementasyon birbirinden
        sapmıyor (bkz. bir önceki mimari tutarsızlık tartışmamız).
        """
        print("\n--- 🚨 OTOMATİK SATIN ALMA TALEBİ ---")
        print(f"Ürün: {urun_adi}")
        print(f"Mevcut Stok: {mevcut_stok} (Kritik sınırın altında!)")
        print(f"Tedarikçi: {tedarikci_bilgisi['firma']}")
        print(f"Tahmini Teslimat: {tedarikci_bilgisi['teslimat_gunu']} gün içinde.")

        veri_erisimi = DashboardVeriErisim()
        olusturuldu = veri_erisimi.otomatik_siparis_taslagi_olustur(urun_adi, siparis_miktari)

        if olusturuldu:
            print(f"✅ Sipariş veritabanına kaydedildi ({siparis_miktari} adet). Yönetici onayı bekleniyor.\n")
        else:
            print(f"ℹ️ {urun_adi} için zaten bekleyen bir sipariş var, yenisi açılmadı.\n")

        return olusturuldu

    def baglantiyi_kapat(self) -> None:
        """Veritabanı bağlantısını güvenlice kapatır."""
        if self.cursor:
                self.cursor.close()
        if self.db and self.db.is_connected():
                self.db.close()

# Modül testi
if __name__ == "__main__":
    yonetici = TedarikciYonetimi()
    if yonetici.baglan():
        yonetici.satin_alma_talebi_olustur(urun_adi="Kablosuz Mouse", mevcut_stok=30)
        yonetici.baglantiyi_kapat()
