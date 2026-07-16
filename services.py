import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from config import KRITIK_STOK_ESIGI

# Loglama ayarları
logging.basicConfig(
    filename='erp_sistem.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    # NOT (madde 8): encoding açıkça 'utf-8' olarak belirtildi. Aksi halde
    # Python, log dosyasını işletim sisteminin/ortamın varsayılan
    # yerelleştirme (locale) charset'iyle açar; bu değer platforma göre
    # değişebilir ve bazı ortamlarda (özellikle Windows'ta Türkçe olmayan
    # bir locale ile) Türkçe karakterler (ç, ğ, ı, ö, ş, ü) loga yazılırken
    # UnicodeEncodeError'a veya bozuk (mojibake) karakterlere yol açabilir.
    encoding='utf-8'
)

# Çevresel değişkenleri yüklüyoruz
load_dotenv()

# --- İŞ MANTIĞI VE BİLDİRİM SERVİSLERİ ---

def kritik_stok_eposta_tetikle(urun_adi, kalan_stok):
    """
    Kritik stok seviyesine inen ürünler için Mailtrap üzerinden 
    kurumsal HTML şablonlu uyarı e-postası gönderir.
    """
    # Gönderen/alıcı artık .env'den okunuyor (Faz 3: config/env merkezileştirme
    # ilkesiyle uyumlu). Brevo gibi servisler, sahibi kanıtlanmamış bir
    # adresten gönderime izin vermez; bu yüzden EPOSTA_GONDEREN mutlaka
    # Brevo panelinde "doğrulanmış gönderen" olarak eklenmiş bir adres olmalı.
    gonderen = os.getenv("EPOSTA_GONDEREN", "erp-sistem@kurum.com")
    alici = os.getenv("EPOSTA_ALICI", "satinalma@kurum.com")
    
    msg = MIMEMultipart('alternative')
    msg['From'] = gonderen
    msg['To'] = alici
    msg['Subject'] = f"🚨 [KRİTİK STOK UYARISI] - {urun_adi.upper()}"
    
    # HTML E-posta Gövdesi (Kurumsal Tasarım)
    html_icerik = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f8fafc;
                margin: 0;
                padding: 20px;
            }}
            .email-container {{
                max-width: 600px;
                background-color: #ffffff;
                margin: 0 auto;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background-color: #0f172a;
                padding: 25px;
                text-align: center;
                border-bottom: 4px solid #ef4444;
            }}
            .header h2 {{
                color: #ffffff;
                margin: 0;
                font-size: 20px;
                letter-spacing: 1px;
            }}
            .content {{
                padding: 30px;
                color: #334155;
                line-height: 1.6;
            }}
            .alert-badge {{
                display: inline-block;
                background-color: #fee2e2;
                color: #991b1b;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 20px;
            }}
            .info-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background-color: #f1f5f9;
                border-radius: 6px;
                overflow: hidden;
            }}
            .info-table th, .info-table td {{
                padding: 12px 15px;
                text-align: left;
            }}
            .info-table th {{
                background-color: #e2e8f0;
                color: #1e293b;
                font-weight: 600;
                width: 35%;
            }}
            .info-table td {{
                border-bottom: 1px solid #e2e8f0;
                color: #0f172a;
            }}
            .btn-container {{
                text-align: center;
                margin-top: 30px;
            }}
            .action-btn {{
                background-color: #2563eb;
                color: #ffffff !important;
                padding: 12px 24px;
                text-decoration: none;
                font-weight: 500;
                border-radius: 6px;
                display: inline-block;
            }}
            .footer {{
                background-color: #f8fafc;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #64748b;
                border-top: 1px solid #e2e8f0;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h2>MERKEZİ ERP STOK KONTROL SİSTEMİ</h2>
            </div>
            
            <div class="content">
                <div class="alert-badge">⚠️ OTOMATİK RİSK BİLDİRİMİ</div>
                
                <p>Sayın Yetkili,</p>
                <p>Sistemimiz tarafından yapılan anlık envanter taramasında, aşağıda detayları belirtilen ürünün stok miktarı tanımlanan <strong>kritik eşik seviyesinin altına</strong> düşmüş durumdadır.</p>
                
                <table class="info-table">
                    <tr>
                        <th>Ürün Adı:</th>
                        <td>{urun_adi}</td>
                    </tr>
                    <tr>
                        <th>Mevcut Stok:</th>
                        <td style="color: #b91c1c; font-weight: bold;">{kalan_stok} Adet</td>
                    </tr>
                    <tr>
                        <th>Kritik Eşik:</th>
                        <td>{KRITIK_STOK_ESIGI} Adet</td>
                    </tr>
                    <tr>
                        <th>Durum:</th>
                        <td><span style="color: #b91c1c; font-weight: bold;">⚠️ Acil Tedarik Gerekli</span></td>
                    </tr>
                </table>
                
                <p>Olası operasyonel aksaklıkların önüne geçilmesi adına satın alma sürecinin başlatılması veya tedarik departmanı ile iletişime geçilmesi önem arz etmektedir.</p>
                
                <div class="btn-container">
                    <a href="http://localhost:8501" class="action-btn">ERP Paneline Git</a>
                </div>
            </div>
            
            <div class="footer">
                <p>Bu e-posta Merkezi ERP Otomasyon Servisi tarafından otomatik olarak üretilmiştir.<br>
                Lütfen bu mesaja doğrudan yanıt vermeyiniz.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # MIME tipini 'html' olarak bağlıyoruz
    msg.attach(MIMEText(html_icerik, 'html', 'utf-8'))
    
    try:
        server = smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT")))
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        time.sleep(2)
        server.send_message(msg)
        server.quit()
        
        logging.info(f"HTML E-POSTA BAŞARIYLA GÖNDERİLDİ: {urun_adi} (Kalan: {kalan_stok})")
        return True
        
    except Exception as e:
        logging.error(f"HTML E-posta gönderim hatası ({urun_adi}): {e}")
        return False

