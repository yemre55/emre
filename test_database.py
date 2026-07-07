"""
Faz 4 — Kritik fonksiyonlar için birim testler
================================================
Test edilen fonksiyonlar:
  - DashboardVeriErisim.stok_analizi_getir
  - DashboardVeriErisim.otomatik_siparis_taslagi_olustur

Bu testler GERÇEK bir MySQL bağlantısına ihtiyaç duymaz. Veritabanı
katmanı (baglanti_getir / pd.read_sql) mock'lanarak fonksiyonların
SADECE kendi iş mantığı (business logic) test edilir.

Çalıştırmak için:
    pytest test_database.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from database import DashboardVeriErisim


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
