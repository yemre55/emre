"""
Faz 4 + Faz 6 — Kritik fonksiyonlar için birim testler
========================================================
Test edilen fonksiyonlar:
  - DashboardVeriErisim.stok_analizi_getir
  - DashboardVeriErisim.otomatik_siparis_taslagi_olustur
  - DashboardVeriErisim.kullanici_dogrula
  - DashboardVeriErisim.siparis_onayla
  - DashboardVeriErisim.urun_islemleri

Bu testler GERÇEK bir MySQL bağlantısına ihtiyaç duymaz. Veritabanı
katmanı (baglanti_getir / pd.read_sql) mock'lanarak fonksiyonların
SADECE kendi iş mantığı (business logic) test edilir.

Çalıştırmak için:
    pytest test_database.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from database import DashboardVeriErisim, Error


@pytest.fixture
def veri():
    """
    DashboardVeriErisim örneğini, __init__ içinde gerçek bir MySQL
    bağlantı havuzu açmaya ÇALIŞMADAN oluşturur. Böylece testler
    veritabanı ayakta olmasa bile çalışır.
    """
    with patch("database.pooling.MySQLConnectionPool"):
        instance = DashboardVeriErisim()
    return instance


# ----------------------------------------------------------------------
# otomatik_siparis_taslagi_olustur testleri
# ----------------------------------------------------------------------

class TestOtomatikSiparisTaslagiOlustur:

    def test_mukerrer_siparis_varsa_yeni_siparis_acilmaz(self, veri):
        """Aynı ürün için zaten açık/bekleyen bir sipariş varsa fonksiyon
        False dönmeli ve YENİ bir INSERT çalıştırmamalı."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = [1]  # açık sipariş sayısı = 1
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        sonuc = veri.otomatik_siparis_taslagi_olustur("Kablosuz Mouse", 50)

        assert sonuc is False
        fake_conn.commit.assert_not_called()

    def test_mukerrer_siparis_yoksa_yeni_siparis_acilir(self, veri):
        """Açık sipariş yoksa fonksiyon True dönmeli, INSERT çalıştırılmalı
        ve işlem commit edilmeli."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = [0]  # açık sipariş yok
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        sonuc = veri.otomatik_siparis_taslagi_olustur("Kablosuz Mouse", 50)

        assert sonuc is True
        fake_conn.commit.assert_called_once()
        # INSERT sorgusunun doğru parametrelerle çağrıldığını doğrula
        insert_cagrisi = fake_cursor.execute.call_args_list[-1]
        assert "INSERT INTO Purchase_Orders" in insert_cagrisi.args[0]
        assert insert_cagrisi.args[1] == ("Kablosuz Mouse", 50)

    def test_db_hatasinda_false_doner_ve_rollback_yapilir(self, veri):
        """Veritabanı sırasında bir hata oluşursa fonksiyon çökmemeli,
        False dönmeli ve rollback çağrılmalı."""
        fake_conn = MagicMock()
        fake_conn.cursor.side_effect = Exception("Bağlantı koptu")
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        sonuc = veri.otomatik_siparis_taslagi_olustur("Kablosuz Mouse", 50)

        assert sonuc is False
        fake_conn.rollback.assert_called_once()


# ----------------------------------------------------------------------
# stok_analizi_getir testleri
# ----------------------------------------------------------------------

class TestStokAnaliziGetir:

    def test_satisi_olan_urun_icin_kalan_gun_dogru_hesaplanir(self, veri):
        """30 günde 60 adet satılmış (günlük hız = 2) ve stokta 20 adet
        varsa, kalan gün tahmini 20 / 2 = 10 gün olmalı."""
        sahte_df = pd.DataFrame({
            "ProductName": ["UrunA"],
            "StockQuantity": [20],
            "UnitPrice": [100],
            "Toplam_Satis": [60],
        })
        veri.baglanti_getir = MagicMock(return_value=MagicMock())

        with patch("database.pd.read_sql", return_value=sahte_df):
            sonuc = veri.stok_analizi_getir()

        assert sonuc.loc[0, "Kalan_Gun_Tahmini"] == 10.0

    def test_hic_satisi_olmayan_urun_999_doner(self, veri):
        """Hiç satışı olmayan bir ürün için (sıfıra bölme hatası yerine)
        özel değer 999 dönmeli."""
        sahte_df = pd.DataFrame({
            "ProductName": ["UrunB"],
            "StockQuantity": [15],
            "UnitPrice": [50],
            "Toplam_Satis": [0],
        })
        veri.baglanti_getir = MagicMock(return_value=MagicMock())

        with patch("database.pd.read_sql", return_value=sahte_df):
            sonuc = veri.stok_analizi_getir()

        assert sonuc.loc[0, "Kalan_Gun_Tahmini"] == 999

    def test_veritabani_hatasinda_none_doner(self, veri):
        """SQL sorgusu sırasında hata oluşursa fonksiyon None dönmeli,
        exception fırlatmamalı (dashboard.py'nin çökmemesi için kritik)."""
        veri.baglanti_getir = MagicMock(return_value=MagicMock())

        with patch("database.pd.read_sql", side_effect=Exception("SQL hatası")):
            sonuc = veri.stok_analizi_getir()

        assert sonuc is None


# ----------------------------------------------------------------------
# kullanici_dogrula testleri
# ----------------------------------------------------------------------

class TestKullaniciDogrula:

    def test_dogru_kullanici_adi_ve_sifre_ile_basarili_dogrulama(self, veri):
        """Kullanıcı adı bulunuyor VE bcrypt şifreyi doğruluyorsa
        (True, Rol) dönmeli."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "Role": "Yonetici",
            "PasswordHash": "sahte_hash_degeri",
        }
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        with patch("database.bcrypt.checkpw", return_value=True):
            sonuc = veri.kullanici_dogrula("yonetici", "dogru_sifre")

        assert sonuc == (True, "Yonetici")

    def test_yanlis_sifre_ile_basarisiz_dogrulama(self, veri):
        """Kullanıcı adı bulunuyor ama bcrypt şifreyi reddediyorsa
        (False, None) dönmeli."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "Role": "Yonetici",
            "PasswordHash": "sahte_hash_degeri",
        }
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        with patch("database.bcrypt.checkpw", return_value=False):
            sonuc = veri.kullanici_dogrula("yonetici", "yanlis_sifre")

        assert sonuc == (False, None)

    def test_olmayan_kullanici_ile_basarisiz_dogrulama(self, veri):
        """Kullanıcı adı veritabanında hiç yoksa (fetchone None dönerse)
        bcrypt hiç çağrılmadan (False, None) dönmeli."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = None
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        sonuc = veri.kullanici_dogrula("olmayan_kullanici", "herhangi_bir_sifre")

        assert sonuc == (False, None)

    def test_db_hatasinda_false_ve_none_doner(self, veri):
        """Veritabanı bağlantısı sırasında bir hata oluşursa fonksiyon
        çökmemeli, (False, None) dönmeli."""
        veri.baglanti_getir = MagicMock(side_effect=Error("Bağlantı koptu"))

        sonuc = veri.kullanici_dogrula("yonetici", "herhangi_bir_sifre")

        assert sonuc == (False, None)


# ----------------------------------------------------------------------
# siparis_onayla testleri
# ----------------------------------------------------------------------

class TestSiparisOnayla:

    def test_gecerli_siparis_onaylanir_ve_stok_artar(self, veri):
        """Sipariş bulunuyorsa: Purchase_Orders güncellenmeli, Products
        stoğu artırılmalı, commit edilmeli ve True dönmeli."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "ProductName": "Kablosuz Mouse",
            "OrderQuantity": 50,
        }
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        sonuc = veri.siparis_onayla(order_id=7)

        assert sonuc is True
        fake_conn.commit.assert_called_once()
        # İki UPDATE de çalıştırılmış olmalı (Purchase_Orders + Products)
        calistirilan_sorgular = [c.args[0] for c in fake_cursor.execute.call_args_list]
        assert any("UPDATE Purchase_Orders" in s for s in calistirilan_sorgular)
        assert any("UPDATE Products" in s for s in calistirilan_sorgular)

    def test_olmayan_siparis_false_doner(self, veri):
        """Verilen OrderID'ye ait bir sipariş bulunamazsa False dönmeli
        ve hiçbir UPDATE/commit çalışmamalı."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = None
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        sonuc = veri.siparis_onayla(order_id=999)

        assert sonuc is False
        fake_conn.commit.assert_not_called()

    def test_hata_durumunda_false_doner_ve_rollback_yapilir(self, veri):
        """İşlem sırasında bir hata oluşursa fonksiyon çökmemeli, False
        dönmeli ve rollback çağrılmalı."""
        fake_conn = MagicMock()
        fake_conn.cursor.side_effect = Exception("Bağlantı koptu")
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        sonuc = veri.siparis_onayla(order_id=7)

        assert sonuc is False
        fake_conn.rollback.assert_called_once()


# ----------------------------------------------------------------------
# urun_islemleri testleri
# ----------------------------------------------------------------------

class TestUrunIslemleri:

    def test_urun_ekleme_dogru_parametrelerle_insert_calistirir(self, veri):
        """islem='ekle' verildiğinde INSERT doğru parametrelerle
        çalışmalı (fiyat float'a, stok int'e çevrilmeli) ve commit
        edilmeli."""
        fake_cursor = MagicMock()
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        veri.urun_islemleri("Yeni Ürün", "199.90", "25", islem="ekle")

        insert_cagrisi = fake_cursor.execute.call_args
        assert "INSERT INTO Products" in insert_cagrisi.args[0]
        assert insert_cagrisi.args[1] == ("Yeni Ürün", 199.90, 25)
        fake_conn.commit.assert_called_once()

    def test_urun_silme_dogru_urunu_siler(self, veri):
        """islem='sil' verildiğinde (veya 'ekle' dışında herhangi bir
        değerde) DELETE çalışmalı."""
        fake_cursor = MagicMock()
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        veri.urun_islemleri("Eski Ürün", 0, 0, islem="sil")

        delete_cagrisi = fake_cursor.execute.call_args
        assert "DELETE FROM Products" in delete_cagrisi.args[0]
        assert delete_cagrisi.args[1] == ("Eski Ürün",)
        fake_conn.commit.assert_called_once()

    def test_hata_durumunda_sessizce_loglanir_ve_commit_edilmez(self, veri):
        """execute() bir hata fırlatırsa fonksiyon dışarıya exception
        sızdırmamalı (dashboard.py'nin çökmemesi için kritik) ve commit
        çalışmamalı."""
        fake_cursor = MagicMock()
        fake_cursor.execute.side_effect = Error("Kısıtlama ihlali")
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        # Exception fırlatmadan tamamlanmalı:
        veri.urun_islemleri("Sorunlu Ürün", 10.0, 5, islem="ekle")

        fake_conn.commit.assert_not_called()
