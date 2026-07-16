# ERP Yönetim Sistemi

Streamlit tabanlı, MySQL destekli bir stok / tedarikçi / satın alma ERP sistemi.
Rol bazlı giriş (Yönetici / Depo Çalışanı), kritik stok seviyesi altına düşen
ürünler için otomatik e-posta bildirimi ve otomatik satın alma taslağı oluşturur.

## Gereksinimler

- Docker ve Docker Compose (önerilen kurulum yolu)
- *Docker'sız* çalıştırmak isterseniz: Python 3.11+, çalışan bir MySQL 8 sunucusu

## Hızlı Başlangıç (Docker)

1. `.env.example` dosyasını kopyalayıp `.env` olarak kaydedin ve değerleri kendinize göre doldurun:

   ```bash
   cp .env.example .env
   ```

2. Servisleri ayağa kaldırın:

   ```bash
   docker-compose up --build
   ```

   Bu komut iki konteyner başlatır:
   - `erp_mysql` — MySQL 8.0, `init.sql` ile şema ve birkaç örnek ürün otomatik oluşturulur.
   - `erp_dashboard` — Streamlit uygulaması.

3. Tarayıcıda açın: [http://localhost:8501](http://localhost:8501)

> ⚠️ `init.sql` yalnızca MySQL verisinin bulunduğu Docker volume **ilk kez**
> oluşturulduğunda çalışır. Şemayı değiştirdiyseniz ve yeniden çalıştırmak
> istiyorsanız: `docker-compose down -v` ile volume'ü silip tekrar
> `docker-compose up --build` çalıştırın (bu, mevcut tüm verinizi siler).

### İlk kullanıcıyı oluşturma

`init.sql` bilinçli olarak bir kullanıcı eklemez, çünkü `PasswordHash` alanı
bcrypt ile üretilmelidir. Bir hash üretmek için:

```bash
docker-compose exec app python3 -c "import bcrypt; print(bcrypt.hashpw(b'sifreniz', bcrypt.gensalt()).decode())"
```

Çıkan hash'i MySQL'e ekleyin:

```bash
docker-compose exec mysql mysql -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" -e \
  "INSERT INTO Users (Username, PasswordHash, Role) VALUES ('yonetici1', '<ÜRETİLEN_HASH>', 'Yonetici');"
```

### Türkçe karakter / charset notu

Uygulama (Python tarafı: `database.py`, `tedarikci_yonetimi.py`, `stok_takip.py`,
`veri_uret.py`, `sifre_guncelle.py`) tüm MySQL bağlantılarında `charset='utf8mb4'`
kullanır ve loglama (`erp_sistem.log`) `encoding='utf-8'` ile yazılır. Ancak
MySQL **CLI**'a manuel bağlandığınızda (örn. yukarıdaki komut veya
`docker exec -it erp_mysql mysql -u root -p`) istemcinin kendi varsayılan
charset'i farklı olabilir ve Türkçe karakterler (ç, ğ, ı, ö, ş, ü) terminalde
bozuk (mojibake) görünebilir. Bunu önlemek için CLI'a bağlanırken de charset'i
açıkça belirtin:

```bash
docker exec -it erp_mysql mysql -u root -p --default-character-set=utf8mb4
```

Bağlandıktan sonra oturumun charset'ini `SHOW VARIABLES LIKE 'character_set%';`
ile doğrulayabilirsiniz; `utf8mb4` görmelisiniz.

## Güvenlik

### Brute-force koruması

`Users` tablosuna `FailedAttempts` ve `LockedUntil` kolonları eklendi.
Üst üste `MAX_BASARISIZ_GIRIS_DENEMESI` (varsayılan: 5, `config.py`) kadar
başarısız giriş denemesinden sonra hesap `HESAP_KILITLEME_SURESI_DAKIKA`
(varsayılan: 15 dakika, `config.py`) boyunca otomatik olarak kilitlenir.
Bu mantık `kullanici_dogrula` fonksiyonunda uygulanır; eşikleri değiştirmek
için kod içinde arama yapmanıza gerek yok, `config.py`'deki bu iki değeri
güncellemeniz yeterlidir.

### `sifre_guncelle.py` ile şifre sıfırlama

Bir kullanıcının şifresini komut satırından sıfırlamak için:

```bash
python3 sifre_guncelle.py
```

Yanlışlıkla üretim veritabanında çalıştırmayı önlemek için betik artık
işlem yapmadan önce **hedef veritabanının adını elle yazarak onaylamanızı**
ister (`.env`'deki `DB_NAME` ile eşleşmelidir). Onay adımı atlanamaz;
girilen ad `DB_NAME` ile eşleşmiyorsa betik işlemi iptal eder.

## Docker'sız Çalıştırma (yerel geliştirme)

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # DB_HOST=localhost olarak bırakın, MySQL'inizi kendiniz kurun

streamlit run dashboard.py
```

## Testleri Çalıştırma

```bash
pytest -v
```

`test_database.py`, gerçek bir MySQL bağlantısına ihtiyaç duymadan
(mock'lanmış) veri katmanının iş mantığını test eder; `stok_guncelle`,
`stok_listesini_getir`, `satis_verilerini_getir`, `log_verilerini_getir`
ve `tedarikci_bilgisi_getir` fonksiyonları için mock testler içerir.

`test_sifre_guncelle.py`, `sifre_guncelle.py`'deki veritabanı adı onay
adımını test eder.

## Lint

```bash
ruff check .
```

## Sürekli Entegrasyon (CI)

`.github/workflows/ci.yml`, her push/PR'da otomatik olarak:
1. `ruff check .` ile lint,
2. `pytest -v` ile testleri çalıştırır.

## Proje Yapısı

```
.
├── dashboard.py            # Streamlit UI katmanı
├── database.py             # Veri erişim katmanı (DashboardVeriErisim sınıfı)
├── services.py             # İş mantığı / e-posta bildirim servisi
├── config.py               # Merkezi eşik değerleri (KRITIK_STOK_ESIGI vb.)
├── stok_takip.py           # Stok takip / kritik seviye mantığı
├── tedarikci_yonetimi.py   # Tedarikçi/teslimat bilgisi (Docker imajına dahildir)
├── sifre_guncelle.py       # CLI ile şifre sıfırlama (onay adımlı)
├── veri_uret.py            # Örnek/test verisi üretme betiği
├── yapiyi_goster.py        # Veritabanı şema/yapı görüntüleme betiği
├── main.py                 # CLI orkestrasyon betiği
├── test_database.py        # pytest birim testleri (veri katmanı)
├── test_sifre_guncelle.py  # pytest birim testleri (şifre sıfırlama onayı)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── init.sql                # MySQL şeması (docker-compose ile otomatik yüklenir)
├── ruff.toml                # Lint kuralları
├── .env.example
└── .github/workflows/ci.yml
```

> Not: Docker imajı yalnızca `dashboard.py`, `database.py`, `services.py`,
> `config.py` ve `tedarikci_yonetimi.py` dosyalarını içerir (bkz. `Dockerfile`).
> `main.py`, `stok_takip.py`, `sifre_guncelle.py`, `veri_uret.py` ve
> `yapiyi_goster.py` yerel/CLI kullanım için tasarlanmıştır ve imaja dahil
> edilmemiştir.

## Ortam Değişkenleri

| Değişken | Açıklama |
|---|---|
| `DB_HOST` | MySQL sunucu adresi (docker-compose'da `mysql` olarak sabittir) |
| `DB_USER` / `DB_PASSWORD` / `DB_NAME` | MySQL kimlik bilgileri |
| `DB_ROOT_PASSWORD` | Yalnızca docker-compose ilk kurulumunda kullanılır |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | Brevo SMTP bilgileri |
| `EPOSTA_GONDEREN` / `EPOSTA_ALICI` | Kritik stok bildirim e-postası gönderen/alıcı adresleri |
| `DB_POOL_SIZE` | MySQL bağlantı havuzu boyutu (varsayılan: 8). Önceden 32'ydi; yük altında gereksiz bağlantı tüketimini azaltmak için düşürüldü ve `.env`'den ayarlanabilir hale getirildi. |

`.env` dosyasını **asla** git'e commit etmeyin.

