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
    UserID        INT AUTO_INCREMENT PRIMARY KEY,
    Username      VARCHAR(100) NOT NULL UNIQUE,
    PasswordHash  VARCHAR(255) NOT NULL,
    Role          ENUM('Yonetici', 'Depo_Calisani') NOT NULL
);

CREATE TABLE IF NOT EXISTS Products (
    ProductID     INT AUTO_INCREMENT PRIMARY KEY,
    ProductName   VARCHAR(200) NOT NULL UNIQUE,
    UnitPrice     DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    StockQuantity INT NOT NULL DEFAULT 0
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
INSERT INTO Products (ProductName, UnitPrice, StockQuantity) VALUES
    ('Kablosuz Mouse', 249.90, 40),
    ('Mekanik Klavye', 899.00, 15),
    ('USB-C Hub', 349.50, 3)
ON DUPLICATE KEY UPDATE ProductName = ProductName;

-- NOT: Admin kullanıcısını buraya düz metin şifreyle EKLEMİYORUZ çünkü
-- PasswordHash bcrypt ile üretilmeli. Konteynerler ayağa kalktıktan
-- sonra bir kullanıcı eklemek için README'deki "İlk kullanıcıyı oluşturma"
-- bölümündeki tek satırlık Python komutunu kullanın.
