import os

def proje_agacini_cikar(baslangic_yolu='.'):
    # Çıktıyı kirletmemesi için yoksayılacak klasörler
    yoksayilacak_klasorler = ['.git', '__pycache__', 'venv', 'env', '.vscode']
    
    print(f"📂 Proje Dizini: {os.path.abspath(baslangic_yolu)}\n")
    
    for root, dirs, files in os.walk(baslangic_yolu):
        # Yoksayılacak klasörleri listeden çıkarıyoruz
        dirs[:] = [d for d in dirs if d not in yoksayilacak_klasorler]
        
        seviye = root.replace(baslangic_yolu, '').count(os.sep)
        girinti = ' ' * 4 * seviye
        klasor_adi = os.path.basename(root)
        
        if seviye == 0:
            klasor_adi = "Ana Klasör"
            
        print(f"{girinti}📁 {klasor_adi}/")
        
        alt_girinti = ' ' * 4 * (seviye + 1)
        for dosya in sorted(files):
            # macOS gizli dosyalarını atla ama kritik .env dosyasını göster
            if not dosya.startswith('.') or dosya == '.env':
                print(f"{alt_girinti}📄 {dosya}")

if __name__ == "__main__":
    proje_agacini_cikar()