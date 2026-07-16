-- ==========================================================
-- ERP Veritabanı Şeması
-- ==========================================================
-- Bu şema, database.py / dashboard.py içindeki SQL sorgularından
-- (SELECT/INSERT/UPDATE ifadelerinden) çıkarılmıştır. Gerçek üretim
-- veritabanınızdaki kolon tipleri (uzunluklar, ek indeksler, foreign
-- key'ler vb.) farklıysa bu dosyayı kendi şemanızla güncelleyin — bu
-- sadece "docker-compose up" ile sıfırdan ayağa kalkan bir geliştirme
-- ortamı için başlangıç noktasıdır.
--
-- Bu dosya, docker-compose.yml'de MySQL konteynerine
-- /docker-entrypoint-initdb.d altında mount edilir ve konteyner İLK
-- kez oluşturulduğunda (veri klasörü boşken) otomatik çalışır.
-- ==========================================================

CREATE TABLE IF NOT EXISTS Users (
    UserID          INT AUTO_INCREMENT PRIMARY KEY,
    Username        VARCHAR(100) NOT NULL UNIQUE,
    PasswordHash    VARCHAR(255) NOT NULL,
    Role            ENUM('Yonetici', 'Depo_Calisani') NOT NULL,
    -- Brute-force koruması (kullanici_dogrula fonksiyonu tarafından
    -- yönetilir): üst üste başarısız deneme sayısı ve, eşik aşılırsa,
    -- hesabın ne zamana kadar kilitli kalacağı.
    FailedAttempts  INT NOT NULL DEFAULT 0,
    LockedUntil     DATETIME NULL
);

CREATE TABLE IF NOT EXISTS Suppliers (
    SupplierID    INT AUTO_INCREMENT PRIMARY KEY,
    SupplierName  VARCHAR(200) NOT NULL,
    LeadTimeDays  INT NOT NULL DEFAULT 0,
    ContactEmail  VARCHAR(200),
    ContactPhone  VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS Products (
    ProductID     INT AUTO_INCREMENT PRIMARY KEY,
    ProductName   VARCHAR(200) NOT NULL UNIQUE,
    UnitPrice     DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    StockQuantity INT NOT NULL DEFAULT 0,
    SupplierID    INT NULL,
    FOREIGN KEY (SupplierID) REFERENCES Suppliers(SupplierID)
);

CREATE TABLE IF NOT EXISTS Sales_Details (
    SaleID     INT AUTO_INCREMENT PRIMARY KEY,
    ProductID  INT NOT NULL,
    Quantity   INT NOT NULL,
    SaleDate   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Purchase_Orders (
    OrderID       INT AUTO_INCREMENT PRIMARY KEY,
    ProductName   VARCHAR(200) NOT NULL,
    OrderQuantity INT NOT NULL,
    Status        VARCHAR(50) DEFAULT 'Beklemede',
    OrderDate     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS AuditLogs (
    LogID        INT AUTO_INCREMENT PRIMARY KEY,
    Username     VARCHAR(100) NOT NULL,
    Action       VARCHAR(100) NOT NULL,
    ProductName  VARCHAR(200),
    OldValue     VARCHAR(200),
    NewValue     VARCHAR(200),
    Timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================
-- Örnek veri (opsiyonel) — istemezseniz bu bölümü silin
-- ==========================================================
INSERT INTO Suppliers (SupplierName, LeadTimeDays, ContactEmail, ContactPhone) VALUES
    ('Anka Elektronik Ltd.', 3, 'siparis@ankaelektronik.com.tr', '0212 555 10 20'),
    ('Bilişim Tedarik A.Ş.', 7, 'satis@bilisimtedarik.com.tr', '0216 555 30 40')
ON DUPLICATE KEY UPDATE SupplierName = SupplierName;

INSERT INTO Products (ProductName, UnitPrice, StockQuantity, SupplierID) VALUES
    ('Kablosuz Mouse', 249.90, 40, 1),
    ('Mekanik Klavye', 899.00, 15, 1),
    ('USB-C Hub', 349.50, 3, 2)
ON DUPLICATE KEY UPDATE ProductName = ProductName;

-- NOT: Admin kullanıcısını buraya düz metin şifreyle EKLEMİYORUZ çünkü
-- PasswordHash bcrypt ile üretilmeli. Konteynerler ayağa kalktıktan
-- sonra bir kullanıcı eklemek için README'deki "İlk kullanıcıyı oluşturma"
-- bölümündeki tek satırlık Python komutunu kullanın.

-- ==========================================================
-- ÖNEMLİ — MEVCUT (ZATEN İLKLENDİRİLMİŞ) ORTAMLAR İÇİN NOT:
-- ==========================================================
-- Bu dosya sadece MySQL veri klasörü BOŞKEN (konteyner ilk kez
-- oluşturulduğunda) otomatik çalışır. Daha önce "docker-compose up"
-- çalıştırdıysanız ve bir veri klasörünüz (volume) zaten varsa, Suppliers
-- tablosu ve Products.SupplierID sütunu otomatik eklenmez. Mevcut
-- veritabanınızda bunu manuel çalıştırmanız gerekir:
--
--   CREATE TABLE IF NOT EXISTS Suppliers (
--       SupplierID    INT AUTO_INCREMENT PRIMARY KEY,
--       SupplierName  VARCHAR(200) NOT NULL,
--       LeadTimeDays  INT NOT NULL DEFAULT 0,
--       ContactEmail  VARCHAR(200),
--       ContactPhone  VARCHAR(50)
--   );
--
--   ALTER TABLE Products ADD COLUMN SupplierID INT NULL,
--       ADD FOREIGN KEY (SupplierID) REFERENCES Suppliers(SupplierID);
--
-- Aynı şekilde, brute-force koruması (FailedAttempts/LockedUntil) daha
-- sonra eklendiği için mevcut bir Users tablonuz varsa bunu da elle
-- eklemeniz gerekir:
--
--   ALTER TABLE Users
--       ADD COLUMN FailedAttempts INT NOT NULL DEFAULT 0,
--       ADD COLUMN LockedUntil DATETIME NULL;
--
-- Alternatif: geliştirme ortamında veriyi kaybetmeyi göze alıyorsanız
-- "docker-compose down -v" ile volume'u silip yeniden "up" yapmak da
-- bu dosyayı sıfırdan çalıştırır.

