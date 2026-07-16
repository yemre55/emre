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
                user=self.user,
                password=self.password,
                database=self.database,
                # NOT (madde 8): Diğer tüm bağlantılarla (database.py,
                # tedarikci_yonetimi.py) tutarlı olması için charset açıkça
                # utf8mb4 olarak ayarlandı. Aksi halde Türkçe karakterler
                # (ç, ğ, ı, ö, ş, ü) sürücünün/sunucunun varsayılan charset'ine
                # göre bozuk (mojibake) görünebilir veya hataya yol açabilir.
                charset='utf8mb4'
            )
            self.cursor = self.db.cursor()
            return True
        except Error as e:
            print(f"KRİTİK HATA: Stok Takip modülü veritabanına bağlanamadı. Detay: {e}")
            return False

    def kritik_stok_raporu_getir(self) -> List[Tuple[str, int]]:
        """Sadece veritabanından satış toplamlarını çeker ve veriyi döndürür (Ekrana yazdırmaz)."""
        if not self.db or not self.cursor:
            return []

        sorgu = """
            SELECT p.ProductName, SUM(d.Quantity) as Toplam_Satis
            FROM Sales_Details d
            JOIN Products p ON d.ProductID = p.ProductID
            GROUP BY p.ProductName
        """
        try:
            self.cursor.execute(sorgu)
            return self.cursor.fetchall()
        except Error as e:
            print(f"HATA: Stok verileri çekilirken sorun oluştu. Detay: {e}")
            return []

    def raporu_yazdir(self) -> None:
        """Çekilen veriyi alır, iş mantığına (business logic) göre değerlendirip ekrana basar."""
        results = self.kritik_stok_raporu_getir()

        if not results:
            print("İncelenecek stok verisi bulunamadı veya bağlantı hatası oluştu.")
            return

        print("\n--- KRİTİK STOK RAPORU ---")
        for row in results:
            urun_adi = row[0]
            toplam_satis = int(row[1]) if row[1] is not None else 0

            if toplam_satis > self.kritik_seviye:
                print(f"UYARI: {urun_adi} çok hızlı satıldı! Toplam çıkış: {toplam_satis}. Stok yenilenmeli.")
            else:
                print(f"DURUM: {urun_adi} için stok durumu stabil. Toplam çıkış: {toplam_satis}.")

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

