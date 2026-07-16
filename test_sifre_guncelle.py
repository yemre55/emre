"""
sifre_guncelle.py için birim testler
=====================================
Madde 6 düzeltmesi: bu betik artık çalışmadan önce hedef veritabanı
adının elle yazılarak onaylanmasını istiyor. Bu testler:
  - Yanlış/boş onay girildiğinde VERİTABANINA HİÇ BAĞLANILMADIĞINI,
  - Doğru onay girildiğinde işlemin tamamlandığını,
  - --force / onay_atla=True ile onay adımının tamamen atlanabildiğini
doğrular.

Gerçek bir MySQL bağlantısına ihtiyaç duymaz; mysql.connector.connect
ve builtins.input mock'lanır.

Çalıştırmak için:
    pytest test_sifre_guncelle.py -v
"""

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("DB_HOST", "testhost")
os.environ.setdefault("DB_NAME", "erp_stok_projesi")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "test")

import sifre_guncelle  # noqa: E402  (env değişkenlerinden sonra import edilmeli)


class TestSifreGuncelleOnayAdimi:

    def test_yanlis_veritabani_adinda_iptal_edilir_ve_baglanti_kurulmaz(self):
        """DÜZELTME testi: kullanıcı hedef veritabanı adını yanlış girerse
        işlem iptal edilmeli ve mysql.connector.connect HİÇ çağrılmamalı
        (yanlışlıkla production'a bağlanılmasını önlemek için kritik)."""
        with patch("builtins.input", return_value="yanlis_isim"), \
             patch("sifre_guncelle.mysql.connector.connect") as mock_connect:
            sonuc = sifre_guncelle.sifreleri_bcrypt_yap()

        assert sonuc is False
        mock_connect.assert_not_called()

    def test_bos_input_ile_iptal_edilir(self):
        """Kullanıcı hiçbir şey yazıp direkt Enter'a basarsa (boş string)
        da işlem iptal edilmeli."""
        with patch("builtins.input", return_value=""), \
             patch("sifre_guncelle.mysql.connector.connect") as mock_connect:
            sonuc = sifre_guncelle.sifreleri_bcrypt_yap()

        assert sonuc is False
        mock_connect.assert_not_called()

    def test_dogru_veritabani_adiyla_islem_tamamlanir(self):
        """Kullanıcı hedef veritabanı adını AYNEN girerse işlem devam
        etmeli: tüm kullanıcılar için UPDATE çalıştırılmalı ve commit
        edilmeli."""
        fake_cursor = MagicMock()
        fake_cursor.fetchall.return_value = [{"Username": "ali"}, {"Username": "veli"}]
        fake_db = MagicMock()
        fake_db.cursor.return_value = fake_cursor
        fake_db.is_connected.return_value = True

        with patch("builtins.input", return_value=os.environ["DB_NAME"]), \
             patch("sifre_guncelle.mysql.connector.connect", return_value=fake_db) as mock_connect:
            sonuc = sifre_guncelle.sifreleri_bcrypt_yap(yeni_sifre_metni="GucluSifre!42")

        assert sonuc is True
        mock_connect.assert_called_once()
        # 1 SELECT + 2 kullanıcı için UPDATE = 3 execute çağrısı
        assert fake_cursor.execute.call_count == 3
        fake_db.commit.assert_called_once()

    def test_onay_atla_true_ise_input_hic_istenmez(self):
        """onay_atla=True (CLI'da --force) verildiğinde input() HİÇ
        çağrılmamalı; betik doğrudan işleme geçmeli. Bu mod SADECE
        otomatik test/CI ortamları için tasarlanmıştır."""
        fake_cursor = MagicMock()
        fake_cursor.fetchall.return_value = [{"Username": "test_ci_user"}]
        fake_db = MagicMock()
        fake_db.cursor.return_value = fake_cursor
        fake_db.is_connected.return_value = True

        with patch("builtins.input", side_effect=AssertionError("input istenmemeli!")), \
             patch("sifre_guncelle.mysql.connector.connect", return_value=fake_db) as mock_connect:
            sonuc = sifre_guncelle.sifreleri_bcrypt_yap(onay_atla=True)

        assert sonuc is True
        mock_connect.assert_called_once()

    def test_kullanici_yoksa_baglanti_kapatilir_ve_true_doner(self):
        """Users tablosu boşsa (hiç kullanıcı yoksa) fonksiyon hata
        vermeden True dönmeli ve hiçbir UPDATE çalıştırılmamalı."""
        fake_cursor = MagicMock()
        fake_cursor.fetchall.return_value = []
        fake_db = MagicMock()
        fake_db.cursor.return_value = fake_cursor
        fake_db.is_connected.return_value = True

        with patch("builtins.input", return_value=os.environ["DB_NAME"]), \
             patch("sifre_guncelle.mysql.connector.connect", return_value=fake_db):
            sonuc = sifre_guncelle.sifreleri_bcrypt_yap()

        assert sonuc is True
        # Sadece SELECT çalışmalı, hiç UPDATE olmamalı
        assert fake_cursor.execute.call_count == 1

    def test_db_hatasinda_false_doner_ve_cokmez(self):
        """Bağlantı sırasında bir istisna oluşursa fonksiyon exception
        fırlatmadan False dönmeli."""
        with patch("builtins.input", return_value=os.environ["DB_NAME"]), \
             patch("sifre_guncelle.mysql.connector.connect", side_effect=Exception("Bağlantı koptu")):
            sonuc = sifre_guncelle.sifreleri_bcrypt_yap()

        assert sonuc is False
