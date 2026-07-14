import os
import logging
import pandas as pd
import numpy as np
import bcrypt
from typing import Optional, Tuple
from dotenv import load_dotenv
from mysql.connector import pooling, Error

# .env dosyasını yüklüyoruz
load_dotenv()

# --- MERKEZİ VERİTABANI BAĞLANTI HAVUZU ---

# --- VERİ ERİŞİM KATMANI ---
class DashboardVeriErisim:
    def __init__(self):
        # Havuz bir kez oluşturulur ve sınıfın bir özelliği olur
        self.db_pool = pooling.MySQLConnectionPool(
            pool_name="erp_pool",
            pool_size=32,
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=int(os.getenv("DB_PORT", 3306)),
            database=os.getenv("DB_NAME"),
            charset='utf8mb4'
        )
        

    def baglanti_getir(self):
        return self.db_pool.get_connection()

    def kullanici_dogrula(self, username, password) -> Tuple[bool, Optional[str]]:
        db = None
        try:
            db = self.baglanti_getir()
            cursor = db.cursor(dictionary=True, buffered=True)
            cursor.execute("SELECT Role, PasswordHash FROM Users WHERE Username = %s", (username,))
            kullanici = cursor.fetchone()

            if kullanici:
                db_hash = kullanici['PasswordHash'].encode('utf-8')
                girilen_sifre = password.encode('utf-8')

                if bcrypt.checkpw(girilen_sifre, db_hash):
                    logging.info(f"Kullanıcı giriş yaptı: {username}")
                    return True, kullanici['Role']

            logging.warning(f"Başarısız giriş denemesi: {username}")
            return False, None

        except Error as e:
            logging.error(f"Kimlik doğrulama sırasında bir veritabanı hatası oluştu: {e}")
            return False, None
        finally:
            if db: db.close()

    def stok_listesini_getir(self):
        db = None
        try:
            db = self.baglanti_getir()
            df = pd.read_sql("SELECT ProductName, StockQuantity, UnitPrice FROM Products", db)
            return df
        except Error as e:
            logging.error(f"Stok listesi çekilirken hata oluştu: {e}")
            return None
        finally:
            if db: db.close()

    def stok_guncelle(self, urun_adi, yeni_miktar, username):
        db = None
        try:
            db = self.baglanti_getir()
            cursor = db.cursor(dictionary=True, buffered=True)

            cursor.execute("SELECT StockQuantity FROM Products WHERE ProductName = %s", (urun_adi,))
            eski = cursor.fetchone()['StockQuantity']

            cursor.execute("UPDATE Products SET StockQuantity = %s WHERE ProductName = %s", (yeni_miktar, urun_adi))
            cursor.execute("INSERT INTO AuditLogs (Username, Action, ProductName, OldValue, NewValue) VALUES (%s, %s, %s, %s, %s)",
                           (username, "Stok Güncelleme", urun_adi, eski, yeni_miktar))
            db.commit()
        except Error as e:
            logging.error(f"Stok güncellenirken hata oluştu: {e}")
        finally:
            if db: db.close()

    def otomatik_siparis_taslagi_olustur(self, urun_adi, miktar):
        """
        NOT: Bu fonksiyonun ürettiği sipariş durumu ('Beklemede') ile
        onay_bekleyenleri_getir() sorgusundaki durum ('Beklemede') artık TUTARLI.
        Önceden burası 'Beklemede' yazıyordu ama onay paneli 'Onay Bekliyor'
        arıyordu; otomatik açılan siparişler hiç görünmüyordu. Düzeltildi.
        """
        db = None
        try:
            db = self.baglanti_getir()
            cursor = db.cursor()

            # MÜKERRER KONTROLÜ (NULL ihtimali eklendi)
            cursor.execute("""
                SELECT COUNT(*) FROM Purchase_Orders
                WHERE ProductName = %s
                AND (Status != 'Onaylandı' OR Status IS NULL)
            """, (urun_adi,))

            acik_siparis_sayisi = cursor.fetchone()[0]

            if acik_siparis_sayisi > 0:
                return False

            sorgu = "INSERT INTO Purchase_Orders (ProductName, OrderQuantity, Status) VALUES (%s, %s, 'Beklemede')"
            cursor.execute(sorgu, (urun_adi, miktar))
            db.commit()
            return True

        except Exception as e:
            logging.error(f"Otomatik sipariş taslağı oluşturulurken hata: {e}")
            if db: db.rollback()
            return False
        finally:
            if db: db.close()

    def log_verilerini_getir(self):
        db = None
        try:
            db = self.baglanti_getir()
            df = pd.read_sql("SELECT * FROM AuditLogs ORDER BY Timestamp DESC", db)
            return df
        except Error as e:
            logging.error(f"Denetim izi logları çekilirken hata: {e}")
            return None
        finally:
            if db: db.close()

    def onay_bekleyenleri_getir(self):
        db = None
        try:
            db = self.baglanti_getir()
            cursor = db.cursor(dictionary=True)
            # DÜZELTİLDİ: 'Onay Bekliyor' -> 'Beklemede'
            # (otomatik_siparis_taslagi_olustur ile aynı statü değerini kullanıyoruz)
            cursor.execute("SELECT * FROM Purchase_Orders WHERE Status = 'Beklemede'")
            return cursor.fetchall()
        except Exception as e:
            logging.error(f"Onay bekleyen siparişler çekilirken hata: {e}")
            return []
        finally:
            if db: db.close()

    def siparis_onayla(self, order_id):
        db = None
        try:
            db = self.baglanti_getir()
            cursor = db.cursor(dictionary=True)

            cursor.execute("SELECT ProductName, OrderQuantity FROM Purchase_Orders WHERE OrderID = %s", (order_id,))
            siparis = cursor.fetchone()

            if siparis:
                urun_adi = siparis['ProductName']
                miktar = siparis['OrderQuantity']

                cursor.execute("UPDATE Purchase_Orders SET Status = 'Onaylandı' WHERE OrderID = %s", (order_id,))
                cursor.execute("UPDATE Products SET StockQuantity = StockQuantity + %s WHERE ProductName = %s", (miktar, urun_adi))

                db.commit()
                return True
            else:
                return False

        except Exception as e:
            logging.error(f"Sipariş onaylanırken hata: {e}")
            if db: db.rollback()
            return False
        finally:
            if db: db.close()

    def urun_islemleri(self, ad, fiyat, stok, islem="ekle"):
        db = None
        try:
            db = self.baglanti_getir()
            cursor = db.cursor()
            if islem == "ekle":
                cursor.execute("INSERT INTO Products (ProductName, UnitPrice, StockQuantity) VALUES (%s, %s, %s)", (ad, float(fiyat), int(stok)))
            else:
                cursor.execute("DELETE FROM Products WHERE ProductName = %s", (ad,))
            db.commit()
        except Error as e:
            logging.error(f"Ürün işlemi başarısız: {e}")
        finally:
            if db: db.close()

    def satis_verilerini_getir(self):
        """
        Dashboard'daki 'Satış Analizi' bar grafiği için ürün bazında
        toplam satış adetlerini döndürür.
        """
        db = None
        try:
            db = self.baglanti_getir()
            query = """
            SELECT p.ProductName, COALESCE(SUM(s.Quantity), 0) as Toplam_Satis
            FROM Products p
            LEFT JOIN Sales_Details s ON p.ProductID = s.ProductID
            GROUP BY p.ProductName
            ORDER BY Toplam_Satis DESC
            """
            df = pd.read_sql(query, db)
            return df
        except Exception as e:
            logging.error(f"Satış verileri çekilirken hata: {e}")
            return pd.DataFrame(columns=['ProductName', 'Toplam_Satis'])
        finally:
            if db: db.close()

    def stok_analizi_getir(self, gun_penceresi: int = 30):
        """
        NOT: Toplam_Satis artık TÜM ZAMANLARIN toplamı değil, son
        `gun_penceresi` (varsayılan 30) gün içindeki satışların toplamı.
        Önceden tarih filtresi yoktu; bu da "tüm zamanlar toplamı / 30"
        gibi anlamsız (ve firma büyüdükçe/yıllar geçtikçe giderek
        yanlışlaşan) bir günlük satış hızı üretiyordu. SaleDate sütunu
        zaten Sales_Details şemasında mevcut, sadece kullanılmıyordu.
        """
        db = None
        try:
            db = self.baglanti_getir()
            query = """
            SELECT p.ProductName, p.StockQuantity, p.UnitPrice,
                   COALESCE(SUM(CASE WHEN s.SaleDate >= NOW() - INTERVAL %s DAY
                                      THEN s.Quantity ELSE 0 END), 0) as Toplam_Satis
            FROM Products p
            LEFT JOIN Sales_Details s ON p.ProductID = s.ProductID
            GROUP BY p.ProductName, p.StockQuantity, p.UnitPrice
            """
            df = pd.read_sql(query, db, params=(gun_penceresi,))

            df['Gunluk_Satis_Hizi'] = df['Toplam_Satis'] / gun_penceresi
            df['Kalan_Gun_Tahmini'] = np.where(
                df['Gunluk_Satis_Hizi'] > 0,
                (df['StockQuantity'] / df['Gunluk_Satis_Hizi']).round(0),
                999
            )
            return df
        except Exception as e:
            logging.error(f"Tahminleme algoritması hatası: {e}")
            return None
        finally:
            if db: db.close()
