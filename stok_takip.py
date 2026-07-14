import os
import mysql.connector
from mysql.connector import Error
from typing import List, Tuple
from dotenv import load_dotenv
from config import VARSAYILAN_KRITIK_SEVIYE

load_dotenv()

class StokTakip:
    def __init__(
        self,
        host: str = None,
        user: str = None,
        password: str = None,
        database: str = None,
        default_kritik_seviye: int = VARSAYILAN_KRITIK_SEVIYE,
    ):
        # Parametre verilmezse .env'den okunur (root/boş şifre varsayılanı KALDIRILDI)
        self.host = host or os.getenv("DB_HOST")
        self.user = user or os.getenv("DB_USER")
        self.password = password if password is not None else os.getenv("DB_PASSWORD")
        self.database = database or os.getenv("DB_NAME")
        self.kritik_seviye = default_kritik_seviye
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
                database=self.database
            )
            self.cursor = self.db.cursor()
            return True
        except Error as e:
            print(f"KRİTİK HATA: Stok Takip modülü veritabanına bağlanamadı. Detay: {e}")
            return False

    def kritik_stok_raporu_getir(self) -> List[Tuple[str, int]]:
        """Ürünlerin GERÇEK (o anki) stok miktarlarını Products tablosundan çeker."""
        if not self.db or not self.cursor:
            return []

        sorgu = "SELECT ProductName, StockQuantity FROM Products"
        try:
            self.cursor.execute(sorgu)
            return self.cursor.fetchall()
        except Error as e:
            print(f"HATA: Stok verileri çekilirken sorun oluştu. Detay: {e}")
            return []

    def raporu_yazdir(self) -> None:
        """Çekilen veriyi alır, iş mantığına göre değerlendirip ekrana basar."""
        results = self.kritik_stok_raporu_getir()

        if not results:
            print("İncelenecek stok verisi bulunamadı veya bağlantı hatası oluştu.")
            return

        print("\n--- KRİTİK STOK RAPORU ---")
        for row in results:
            urun_adi = row[0]
            mevcut_stok = int(row[1]) if row[1] is not None else 0

            if mevcut_stok < self.kritik_seviye:
                print(f"UYARI: {urun_adi} kritik seviyenin altında! Mevcut stok: {mevcut_stok}. Sipariş gerekli.")
            else:
                print(f"DURUM: {urun_adi} için stok durumu stabil. Mevcut stok: {mevcut_stok}.")    

    def baglantiyi_kapat(self) -> None:
        """Açık bağlantıları temizler."""
        if self.cursor:
            self.cursor.close()
        if self.db and self.db.is_connected():
            self.db.close()

# Doğrudan test etmek için çalışma bloğu
if __name__ == "__main__":
    stok_yoneticisi = StokTakip(default_kritik_seviye=VARSAYILAN_KRITIK_SEVIYE)
    if stok_yoneticisi.baglan():
        stok_yoneticisi.raporu_yazdir()
        stok_yoneticisi.baglantiyi_kapat()
