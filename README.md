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
(mock'lanmış) veri katmanının iş mantığını test eder.

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
├── dashboard.py          # Streamlit UI katmanı
├── database.py           # Veri erişim katmanı (DashboardVeriErisim sınıfı)
├── services.py           # İş mantığı / e-posta bildirim servisi
├── config.py             # Merkezi eşik değerleri (KRITIK_STOK_ESIGI vb.)
├── test_database.py      # pytest birim testleri
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── init.sql              # MySQL şeması (docker-compose ile otomatik yüklenir)
├── .env.example
└── .github/workflows/ci.yml
```

> Not: `main.py` (CLI orkestrasyon betiği) bu pakete dahil edilmemiştir çünkü
> bu depoda yer almayan `stok_takip.py` ve `tedarikci_yonetimi.py`
> modüllerine bağımlıdır. Docker imajı doğrudan `dashboard.py`'yi çalıştırır.

## Ortam Değişkenleri

| Değişken | Açıklama |
|---|---|
| `DB_HOST` | MySQL sunucu adresi (docker-compose'da `mysql` olarak sabittir) |
| `DB_USER` / `DB_PASSWORD` / `DB_NAME` | MySQL kimlik bilgileri |
| `DB_ROOT_PASSWORD` | Yalnızca docker-compose ilk kurulumunda kullanılır |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | Brevo SMTP bilgileri |
| `EPOSTA_GONDEREN` / `EPOSTA_ALICI` | Kritik stok bildirim e-postası gönderen/alıcı adresleri |

`.env` dosyasını **asla** git'e commit etmeyin.
