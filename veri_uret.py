import os
import mysql.connector
from mysql.connector import Error
import random
from datetime import datetime, timedelta
from typing import List, Tuple
from dotenv import load_dotenv

load_dotenv()

class VeriUretici:
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
        """Veritabanı bağlantısını güvenli bir şekilde kurar."""
        try:
            self.db = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                # NOT (madde 8): bkz. stok_takip.py'deki aynı not.
                charset='utf8mb4'
            )
            self.cursor = self.db.cursor()
            print("Veritabanı bağlantısı başarılı.")
            return True
        except Error as e:
            print(f"KRİTİK HATA: Veritabanına bağlanılamadı. MySQL servisi kapalı olabilir. Detay: {e}")
            return False

    def temel_verileri_ekle(self) -> None:
        """Ürünler ve müşteriler gibi sabit verileri tabloya ekler."""
        if not self.db or not self.cursor:
            return

        urunler: List[Tuple[str, str, int]] = [
            ("Dizüstü Bilgisayar", "Elektronik", 25000),
            ("Kablosuz Mouse", "Aksesuar", 750),
            ("Monitör", "Elektronik", 4000),
            ("Klavye", "Aksesuar", 500)
        ]
        musteriler: List[Tuple[str, str]] = [
            ("Ahmet Yılmaz", "İstanbul"),
            ("Ayşe Demir", "Ankara"),
            ("Mehmet Kaya", "İzmir")
        ]

        try:
            for p in urunler:
                self.cursor.execute("INSERT INTO Products (ProductName, Category, UnitPrice) VALUES (%s, %s, %s)", p)

            for c in musteriler:
                self.cursor.execute("INSERT INTO Customers (CustomerName, City) VALUES (%s, %s)", c)

            self.db.commit()
            print("Temel veriler (Ürünler ve Müşteriler) başarıyla eklendi.")
        except Error as e:
            print(f"HATA: Temel veriler eklenirken sorun oluştu. Detay: {e}")
            self.db.rollback()

    def rastgele_satis_olustur(self, islem_sayisi: int = 50) -> None:
        """Belirtilen sayıda rastgele satış işlemi ve detayı oluşturur."""
        if not self.db or not self.cursor:
            return

        try:
            for _ in range(islem_sayisi):
                customer_id = random.randint(1, 3)
                sale_date = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d')

                self.cursor.execute("INSERT INTO Sales_Headers (CustomerID, SaleDate) VALUES (%s, %s)", (customer_id, sale_date))
                sale_id = self.cursor.lastrowid

                for _ in range(random.randint(1, 3)):
                    product_id = random.randint(1, 4)
                    quantity = random.randint(1, 5)
                    self.cursor.execute("INSERT INTO Sales_Details (SaleID, ProductID, Quantity) VALUES (%s, %s, %s)", (sale_id, product_id, quantity))

            self.db.commit()
            print(f"{islem_sayisi} adet satış işlemi başarıyla oluşturuldu!")
        except Error as e:
            print(f"HATA: Satış verileri oluşturulurken sorun yaşandı. Detay: {e}")
            self.db.rollback()

    def baglantiyi_kapat(self) -> None:
        """Açık olan veritabanı bağlantılarını RAM'i şişirmemek için güvenlice kapatır."""
        if self.cursor:
            self.cursor.close()
        if self.db and self.db.is_connected():
            self.db.close()
            print("Veritabanı bağlantısı güvenlice kapatıldı.\n---")

# Bu blok sadece bu dosya doğrudan çalıştırılırsa devreye girer.
if __name__ == "__main__":
    uretici = VeriUretici()
    if uretici.baglan():
        uretici.temel_verileri_ekle()
        uretici.rastgele_satis_olustur(50)
        uretici.baglantiyi_kapat()

