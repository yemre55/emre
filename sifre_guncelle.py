import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

def sifreleri_bcrypt_yap(yeni_sifre_metni="123456"):
    try:
        db = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = db.cursor(dictionary=True)
        
        # Tüm kullanıcıları çek
        cursor.execute("SELECT Username FROM Users")
        kullanicilar = cursor.fetchall()
        
        # Yeni bcrypt şifresini oluştur (encode ile byte'a çevrilmesi şarttır)
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(yeni_sifre_metni.encode('utf-8'), salt)
        
        # Tüm kullanıcıların şifresini yeni hash ile güncelle
        for k in kullanicilar:
            cursor.execute("UPDATE Users SET PasswordHash = %s WHERE Username = %s", 
                           (hashed_password.decode('utf-8'), k['Username']))
            print(f"✅ {k['Username']} adlı kullanıcının şifresi bcrypt ile güncellendi.")
            
        db.commit()
        print("\nSistemdeki tüm şifreler başarıyla endüstri standardına yükseltildi!")
        
    except Exception as e:
        print(f"Hata oluştu: {e}")
    finally:
        if 'db' in locals() and db.is_connected():
            db.close()

if __name__ == "__main__":
    sifreleri_bcrypt_yap()
