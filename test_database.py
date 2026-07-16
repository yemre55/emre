"""
Faz 4 + Faz 6 — Kritik fonksiyonlar için birim testler
========================================================
Test edilen fonksiyonlar:
  - DashboardVeriErisim.stok_analizi_getir
  - DashboardVeriErisim.otomatik_siparis_taslagi_olustur
  - DashboardVeriErisim.kullanici_dogrula
  - DashboardVeriErisim.siparis_onayla
  - DashboardVeriErisim.urun_islemleri
  - DashboardVeriErisim.stok_guncelle
  - DashboardVeriErisim.stok_listesini_getir
  - DashboardVeriErisim.satis_verilerini_getir
  - DashboardVeriErisim.log_verilerini_getir
  - TedarikciYonetimi.tedarikci_bilgisi_getir

Bu testler GERÇEK bir MySQL bağlantısına ihtiyaç duymaz. Veritabanı
katmanı (baglanti_getir / pd.read_sql) mock'lanarak fonksiyonların
SADECE kendi iş mantığı (business logic) test edilir.

Çalıştırmak için:
    pytest test_database.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import pandas as pd

from database import DashboardVeriErisim
from mysql.connector import Error
from tedarikci_yonetimi import TedarikciYonetimi


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


@pytest.fixture
def tedarikci():
    """
    TedarikciYonetimi örneğini gerçek bir MySQL bağlantısı açmadan
    oluşturur; db/cursor alanları teste özel MagicMock ile doldurulur.
    """
    instance = TedarikciYonetimi(host="test", user="test", password="test", database="test")
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

    # --- Brute-force koruması testleri ---

    def test_kilitli_hesaba_dogru_sifreyle_bile_giris_reddedilir(self, veri):
        """DÜZELTME testi: LockedUntil ileri bir tarihteyse, şifre doğru
        olsa bile giriş reddedilmeli ve bcrypt hiç çağrılmamalı (kilit
        kontrolü şifre kontrolünden ÖNCE yapılmalı)."""
        ileri_tarih = datetime.now() + timedelta(minutes=10)
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "Role": "Yonetici",
            "PasswordHash": "sahte_hash_degeri",
            "FailedAttempts": 5,
            "LockedUntil": ileri_tarih,
        }
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        with patch("database.bcrypt.checkpw") as mock_checkpw:
            sonuc = veri.kullanici_dogrula("yonetici", "dogru_sifre")

        assert sonuc == (False, None)
        mock_checkpw.assert_not_called()

    def test_kilit_suresi_gecmisse_normal_akisa_devam_eder(self, veri):
        """LockedUntil geçmişte bir tarihse (kilit süresi dolmuşsa),
        fonksiyon normal şifre kontrolüne devam etmeli ve doğru şifreyle
        giriş başarılı olmalı."""
        gecmis_tarih = datetime.now() - timedelta(minutes=1)
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "Role": "Yonetici",
            "PasswordHash": "sahte_hash_degeri",
            "FailedAttempts": 5,
            "LockedUntil": gecmis_tarih,
        }
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        with patch("database.bcrypt.checkpw", return_value=True):
            sonuc = veri.kullanici_dogrula("yonetici", "dogru_sifre")

        assert sonuc == (True, "Yonetici")

    def test_esik_altinda_basarisiz_denemede_kilitlenmez(self, veri):
        """MAX_BASARISIZ_GIRIS_DENEMESI'nin altında bir deneme sayısında
        (örn. 2. yanlış deneme) hesap kilitlenmemeli, sadece sayaç
        UPDATE ile artırılmalı."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "Role": "Yonetici",
            "PasswordHash": "sahte_hash_degeri",
            "FailedAttempts": 1,
            "LockedUntil": None,
        }
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        with patch("database.bcrypt.checkpw", return_value=False):
            sonuc = veri.kullanici_dogrula("yonetici", "yanlis_sifre")

        assert sonuc == (False, None)
        update_cagrisi = fake_cursor.execute.call_args_list[-1]
        assert "FailedAttempts = %s WHERE Username" in update_cagrisi.args[0]
        assert update_cagrisi.args[1] == (2, "yonetici")
        assert "LockedUntil" not in update_cagrisi.args[0]

    def test_esige_ulasinca_hesap_kilitlenir(self, veri):
        """FailedAttempts, MAX_BASARISIZ_GIRIS_DENEMESI eşiğine (5)
        ulaştığında UPDATE sorgusu artık LockedUntil'i de ayarlamalı."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "Role": "Yonetici",
            "PasswordHash": "sahte_hash_degeri",
            "FailedAttempts": 4,  # bu deneme 5. olacak -> kilitlenmeli
            "LockedUntil": None,
        }
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        with patch("database.bcrypt.checkpw", return_value=False):
            sonuc = veri.kullanici_dogrula("yonetici", "yanlis_sifre")

        assert sonuc == (False, None)
        update_cagrisi = fake_cursor.execute.call_args_list[-1]
        assert "LockedUntil = NOW() + INTERVAL %s MINUTE" in update_cagrisi.args[0]
        assert update_cagrisi.args[1] == (5, 15, "yonetici")

    def test_basarili_giriste_sayac_sifirlanir_ve_kilit_kalkar(self, veri):
        """Doğru şifreyle giriş yapıldığında, önceki başarısız denemeler
        olsa bile FailedAttempts=0 ve LockedUntil=NULL olacak şekilde bir
        UPDATE çalıştırılmalı (bir sonraki girişte eski sayaç kalmamalı)."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "Role": "Depo_Calisani",
            "PasswordHash": "sahte_hash_degeri",
            "FailedAttempts": 3,
            "LockedUntil": None,
        }
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        with patch("database.bcrypt.checkpw", return_value=True):
            sonuc = veri.kullanici_dogrula("depocu", "dogru_sifre")

        assert sonuc == (True, "Depo_Calisani")
        update_cagrisi = fake_cursor.execute.call_args_list[-1]
        assert "FailedAttempts = 0, LockedUntil = NULL" in update_cagrisi.args[0]
        fake_conn.commit.assert_called_once()


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

    def test_taninmayan_islem_hicbir_sey_yapmaz(self, veri):
        """DÜZELTME testi: islem='sil' veya 'ekle' DIŞINDA bir değer
        (örn. yazım hatası 'sill') verildiğinde artık DELETE ÇALIŞMAMALI,
        hiçbir sorgu execute edilmemeli ve commit çağrılmamalı. Önceki
        davranışta bu durum sessizce DELETE'e düşüyordu; bu riskliydi."""
        fake_cursor = MagicMock()
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        veri.urun_islemleri("Herhangi Ürün", 10.0, 5, islem="sill")  # yazım hatası

        fake_cursor.execute.assert_not_called()
        fake_conn.commit.assert_not_called()

    def test_islem_bos_string_ise_hicbir_sey_yapmaz(self, veri):
        """islem='' (boş string) gibi beklenmedik bir değerde de aynı
        şekilde hiçbir veritabanı işlemi yapılmamalı."""
        fake_cursor = MagicMock()
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        veri.urun_islemleri("Herhangi Ürün", 10.0, 5, islem="")

        fake_cursor.execute.assert_not_called()
        fake_conn.commit.assert_not_called()


# ----------------------------------------------------------------------
# stok_guncelle testleri
# ----------------------------------------------------------------------

class TestStokGuncelle:

    def test_stok_dogru_guncellenir_ve_audit_log_yazilir(self, veri):
        """Fonksiyon: (1) eski stok miktarını okumalı, (2) Products
        tablosunu yeni miktarla güncellemeli, (3) AuditLogs'a eski/yeni
        değerle bir kayıt eklemeli, (4) commit çağırmalı. Audit log +
        stok güncellemesinin BİRLİKTE yapılması kritik: biri diğeri
        olmadan işe yaramaz (izlenemeyen bir stok değişikliği olur)."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {"StockQuantity": 15}
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        veri.stok_guncelle("Kablosuz Mouse", 40, "yonetici_ali")

        tum_cagrilar = fake_cursor.execute.call_args_list
        assert len(tum_cagrilar) == 3  # SELECT + UPDATE + INSERT (AuditLogs)

        update_cagrisi = tum_cagrilar[1]
        assert "UPDATE Products" in update_cagrisi.args[0]
        assert update_cagrisi.args[1] == (40, "Kablosuz Mouse")

        audit_cagrisi = tum_cagrilar[2]
        assert "INSERT INTO AuditLogs" in audit_cagrisi.args[0]
        assert audit_cagrisi.args[1] == ("yonetici_ali", "Stok Güncelleme", "Kablosuz Mouse", 15, 40)

        fake_conn.commit.assert_called_once()

    def test_db_hatasinda_sessizce_loglanir_ve_commit_edilmez(self, veri):
        """Veritabanı hatası oluşursa (örn. SELECT sırasında) fonksiyon
        exception fırlatmamalı ve commit çağrılmamalı."""
        fake_cursor = MagicMock()
        fake_cursor.execute.side_effect = Error("Bağlantı koptu")
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        veri.baglanti_getir = MagicMock(return_value=fake_conn)

        # Exception fırlatmadan tamamlanmalı:
        veri.stok_guncelle("Kablosuz Mouse", 40, "yonetici_ali")

        fake_conn.commit.assert_not_called()


# ----------------------------------------------------------------------
# stok_listesini_getir testleri
# ----------------------------------------------------------------------

class TestStokListesiniGetir:

    def test_stok_listesi_dogru_kolonlarla_doner(self, veri):
        """Fonksiyon Products tablosundan ProductName, StockQuantity ve
        UnitPrice kolonlarını içeren bir DataFrame döndürmeli."""
        sahte_df = pd.DataFrame({
            "ProductName": ["UrunA", "UrunB"],
            "StockQuantity": [10, 5],
            "UnitPrice": [99.90, 149.50],
        })
        veri.baglanti_getir = MagicMock(return_value=MagicMock())

        with patch("database.pd.read_sql", return_value=sahte_df) as mock_read_sql:
            sonuc = veri.stok_listesini_getir()

        assert list(sonuc.columns) == ["ProductName", "StockQuantity", "UnitPrice"]
        assert len(sonuc) == 2
        sorgu_metni = mock_read_sql.call_args.args[0]
        assert "FROM Products" in sorgu_metni

    def test_veritabani_hatasinda_none_doner(self, veri):
        """SQL sorgusu sırasında hata oluşursa fonksiyon None dönmeli,
        exception fırlatmamalı (dashboard.py'nin çökmemesi için kritik).

        NOT: stok_listesini_getir sadece `mysql.connector.Error`
        yakalıyor (satis_verilerini_getir/stok_analizi_getir gibi
        `Exception` değil). Bu tutarsızlık madde #7'de ("hata yakalama
        stratejisini standartlaştır") ele alınmalı — pd.read_sql pandas
        kaynaklı bambaşka bir istisna (örn. veritabanı şeması uyuşmazlığı)
        fırlatırsa bu fonksiyon ŞU AN çökebilir, çünkü Error dışındaki
        hatalar yakalanmıyor."""
        veri.baglanti_getir = MagicMock(return_value=MagicMock())

        with patch("database.pd.read_sql", side_effect=Error("SQL hatası")):
            sonuc = veri.stok_listesini_getir()

        assert sonuc is None


# ----------------------------------------------------------------------
# satis_verilerini_getir testleri
# ----------------------------------------------------------------------

class TestSatisVerileriniGetir:

    def test_satis_verileri_urun_bazinda_dogru_doner(self, veri):
        """Fonksiyon ürün bazında toplam satış adetlerini, en çok
        satandan en aza doğru sıralı şekilde döndürmeli."""
        sahte_df = pd.DataFrame({
            "ProductName": ["UrunA", "UrunB"],
            "Toplam_Satis": [120, 30],
        })
        veri.baglanti_getir = MagicMock(return_value=MagicMock())

        with patch("database.pd.read_sql", return_value=sahte_df) as mock_read_sql:
            sonuc = veri.satis_verilerini_getir()

        assert list(sonuc["Toplam_Satis"]) == [120, 30]
        sorgu_metni = mock_read_sql.call_args.args[0]
        assert "LEFT JOIN Sales_Details" in sorgu_metni

    def test_hic_satis_yoksa_bos_dataframe_doner(self, veri):
        """Veritabanı hatası oluşursa fonksiyon exception fırlatmak
        yerine doğru kolonlara sahip BOŞ bir DataFrame dönmeli (dashboard
        grafiği çökmeden 'veri yok' durumunu gösterebilsin diye)."""
        veri.baglanti_getir = MagicMock(return_value=MagicMock())

        with patch("database.pd.read_sql", side_effect=Exception("SQL hatası")):
            sonuc = veri.satis_verilerini_getir()

        assert list(sonuc.columns) == ["ProductName", "Toplam_Satis"]
        assert len(sonuc) == 0


# ----------------------------------------------------------------------
# log_verilerini_getir testleri
# ----------------------------------------------------------------------

class TestLogVerileriniGetir:

    def test_sorguya_limit_dogru_parametreyle_eklenir(self, veri):
        """DÜZELTME testi: sorgu artık LIMIT içermeli ve varsayılan
        limit (500) parametre olarak read_sql'e geçilmeli. Bu, tablo
        büyüdükçe dashboard'un yavaşlamasını önlemek için eklendi."""
        sahte_df = pd.DataFrame({"Username": ["ali"], "Action": ["Stok Güncelleme"]})
        veri.baglanti_getir = MagicMock(return_value=MagicMock())

        with patch("database.pd.read_sql", return_value=sahte_df) as mock_read_sql:
            sonuc = veri.log_verilerini_getir()

        sorgu_metni = mock_read_sql.call_args.args[0]
        assert "LIMIT" in sorgu_metni
        assert mock_read_sql.call_args.kwargs["params"] == (500,)
        assert len(sonuc) == 1

    def test_ozel_limit_degeri_kullanilabilir(self, veri):
        """Çağıran taraf farklı bir limit isterse (örn. 50) bu değer
        sorguya doğru şekilde geçmeli."""
        veri.baglanti_getir = MagicMock(return_value=MagicMock())

        with patch("database.pd.read_sql", return_value=pd.DataFrame()) as mock_read_sql:
            veri.log_verilerini_getir(limit=50)

        assert mock_read_sql.call_args.kwargs["params"] == (50,)

    def test_veritabani_hatasinda_none_doner(self, veri):
        """SQL sorgusu sırasında hata oluşursa fonksiyon None dönmeli,
        exception fırlatmamalı.

        NOT: Bu fonksiyon da (stok_listesini_getir gibi) sadece
        `mysql.connector.Error` yakalıyor; genel `Exception` değil.
        Aynı standardizasyon ihtiyacı burada da geçerli."""
        veri.baglanti_getir = MagicMock(return_value=MagicMock())

        with patch("database.pd.read_sql", side_effect=Error("SQL hatası")):
            sonuc = veri.log_verilerini_getir()

        assert sonuc is None


# ----------------------------------------------------------------------
# tedarikci_bilgisi_getir testleri (TedarikciYonetimi sınıfı)
# ----------------------------------------------------------------------

class TestTedarikciBilgisiGetir:

    def test_baglanti_yoksa_varsayilan_deger_doner(self, tedarikci):
        """db/cursor henüz kurulmamışsa (baglan() çağrılmamışsa) fonksiyon
        veritabanına erişmeye çalışmadan varsayılan 'Bağlantı Yok' bilgisini
        dönmeli."""
        sonuc = tedarikci.tedarikci_bilgisi_getir("Kablosuz Mouse")

        assert sonuc["firma"] == "Bağlantı Yok"
        assert sonuc["teslimat_gunu"] == 0

    def test_tedarikci_bulunursa_dogru_bilgi_doner(self, tedarikci):
        """Ürünün bir tedarikçisi varsa, firma adı/teslimat süresi/iletişim
        bilgileri SQL sonucundan doğru şekilde eşlenmeli."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "SupplierName": "ABC Elektronik",
            "LeadTimeDays": 5,
            "ContactEmail": "info@abc.com",
            "ContactPhone": "0212 555 1234",
        }
        tedarikci.db = MagicMock()
        tedarikci.cursor = fake_cursor

        sonuc = tedarikci.tedarikci_bilgisi_getir("Kablosuz Mouse")

        assert sonuc == {
            "firma": "ABC Elektronik",
            "teslimat_gunu": 5,
            "eposta": "info@abc.com",
            "telefon": "0212 555 1234",
        }

    def test_urunun_tedarikcisi_yoksa_bilinmeyen_tedarikci_doner(self, tedarikci):
        """Ürün bulunuyor ama SupplierName NULL ise (tedarikçi atanmamış)
        'Bilinmeyen Tedarikçi' uyarısı dönmeli, exception fırlatılmamalı."""
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "SupplierName": None,
            "LeadTimeDays": None,
            "ContactEmail": None,
            "ContactPhone": None,
        }
        tedarikci.db = MagicMock()
        tedarikci.cursor = fake_cursor

        sonuc = tedarikci.tedarikci_bilgisi_getir("Sahipsiz Ürün")

        assert sonuc["firma"] == "Bilinmeyen Tedarikçi (Sisteme Kayıt Edilmeli)"

    def test_db_hatasinda_hata_olustu_doner(self, tedarikci):
        """Sorgu sırasında veritabanı hatası oluşursa fonksiyon
        çökmemeli, 'Hata Oluştu' bilgisini dönmeli."""
        fake_cursor = MagicMock()
        fake_cursor.execute.side_effect = Error("Bağlantı koptu")
        tedarikci.db = MagicMock()
        tedarikci.cursor = fake_cursor

        sonuc = tedarikci.tedarikci_bilgisi_getir("Kablosuz Mouse")

        assert sonuc["firma"] == "Hata Oluştu"
