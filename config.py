"""
Merkezi Konfigürasyon Dosyası
=============================
Projede farklı dosyalara (dashboard.py, database.py, stok_takip.py,
tedarikci_yonetimi.py) dağılmış sabit eşik değerlerini burada topluyoruz.

Bir eşiği değiştirmek istediğinde artık kod içinde dosya dosya arama
yapmana gerek yok, tek yer burası.
"""

# Bir ürünün "kritik stok" sayılması için StockQuantity bu değerin altına
# düşmeli. Altına düşünce: e-posta bildirimi + otomatik sipariş taslağı tetiklenir.
KRITIK_STOK_ESIGI = 5

# Otomatik sipariş taslağı oluşturulurken tedarikçiden istenecek varsayılan miktar
OTOMATIK_SIPARIS_MIKTARI = 50

# stok_takip.py / tedarikci_yonetimi.py modüllerinde "hızlı satan / az stoklu"
# ürün tespiti için kullanılan varsayılan kritik seviye
VARSAYILAN_KRITIK_SEVIYE = 50

# Dashboard'daki "Stok Bitme Tahmini" panelinde bir ürünü listeye/uyarıya
# almak için kalan gün tahmini bu değerin altında olmalı
TAHMIN_GUN_ESIGI = 7

# Satış hızı hesaplanırken baz alınan gün sayısı (örn. son 30 günlük satışlara göre)
SATIS_HIZI_HESAPLAMA_GUN_SAYISI = 30

# --- Brute-force / Hesap Kilitleme Ayarları ---
# Üst üste bu kadar başarısız giriş denemesinden sonra hesap geçici
# olarak kilitlenir (kullanici_dogrula fonksiyonunda kullanılır).
MAX_BASARISIZ_GIRIS_DENEMESI = 5

# Hesap kilitlendiğinde kaç dakika boyunca giriş engellenecek.
HESAP_KILITLEME_SURESI_DAKIKA = 15

