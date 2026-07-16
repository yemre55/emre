"""
Toplu Şifre Sıfırlama Betiği
=============================
DİKKAT: Bu betik .env dosyasında tanımlı veritabanındaki TÜM
kullanıcıların şifresini TEK BİR (varsayılan) şifreyle değiştirir.

DÜZELTME (madde 6): Önceden bu betik hiçbir onay istemeden,
python sifre_guncelle.py yazılır yazılmaz TÜM şifreleri sıfırlıyordu.
Yanlışlıkla production ortamında (örn. .env dosyası unutulup production
bağlantı bilgileriyle) çalıştırılırsa, sistemdeki TÜM kullanıcılar dışarıda
kalır ve herkesin şifresi aynı (ve zayıf) bir değere döner — geri alınamaz.

Artık betik:
  1. Hangi sunucuya/veritabanına bağlanacağını AÇIKÇA gösterir.
  2. Kullanıcıdan hedef veritabanının adını AYNEN yazarak onaylamasını ister.
  3. --force bayrağı SADECE otomatik test/CI ortamları için vardır;
     production'da KULLANILMAMALIDIR.
"""

import argparse
import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()


def sifreleri_bcrypt_yap(yeni_sifre_metni="123456", onay_atla=False):
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")

    if not onay_atla:
        print("=" * 60)
        print("⚠️  DİKKAT: TÜM KULLANICI ŞİFRELERİNİ SIFIRLAMA")
        print("=" * 60)
        print(f"Hedef sunucu     : {db_host}")
        print(f"Hedef veritabanı : {db_name}")
        print(f"Yeni şifre uzunluğu: {len(yeni_sifre_metni)} karakter")
        print()
        print("Bu işlem, yukarıdaki veritabanındaki TÜM kullanıcıların")
        print("şifresini bu TEK şifreyle değiştirecek. GERİ ALINAMAZ.")
        print()
        print(f"Devam etmek için hedef veritabanının adını AYNEN yazın (\"{db_name}\"):")
        girilen = input("> ").strip()
        if girilen != db_name:
            print("❌ İptal edildi: veritabanı adı eşleşmedi, hiçbir şey değiştirilmedi.")
            return False
        print()

    db = None
    try:
        db = mysql.connector.connect(
            host=db_host,
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=db_name,
            # NOT (madde 8): bkz. stok_takip.py'deki aynı not.
            charset='utf8mb4',
        )
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT Username FROM Users")
        kullanicilar = cursor.fetchall()

        if not kullanicilar:
            print("Users tablosunda hiç kullanıcı bulunamadı, yapılacak bir şey yok.")
            return True

        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(yeni_sifre_metni.encode("utf-8"), salt)

        for k in kullanicilar:
            cursor.execute(
                "UPDATE Users SET PasswordHash = %s WHERE Username = %s",
                (hashed_password.decode("utf-8"), k["Username"]),
            )
            print(f"✅ {k['Username']} adlı kullanıcının şifresi bcrypt ile güncellendi.")

        db.commit()
        print(f"\n{len(kullanicilar)} kullanıcının şifresi başarıyla güncellendi.")
        return True

    except Exception as e:
        print(f"Hata oluştu: {e}")
        return False
    finally:
        if db is not None and db.is_connected():
            db.close()


def _cli():
    parser = argparse.ArgumentParser(
        description=(
            "TÜM kullanıcıların şifresini tek bir bcrypt hash'iyle günceller. "
            "DİKKAT: geri alınamaz bir işlemdir, varsayılan olarak önce onay ister."
        )
    )
    parser.add_argument(
        "--sifre",
        default="123456",
        help="Tüm kullanıcılara atanacak yeni şifre (varsayılan: 123456 — "
             "production'da MUTLAKA farklı, güçlü bir şifre kullanın)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Onay adımını atla (SADECE otomatik test/CI ortamları için; production'da KULLANMAYIN)",
    )
    args = parser.parse_args()
    sifreleri_bcrypt_yap(yeni_sifre_metni=args.sifre, onay_atla=args.force)


if __name__ == "__main__":
    _cli()
