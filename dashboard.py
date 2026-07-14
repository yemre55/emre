import streamlit as st
import pandas as pd
import plotly.express as px
import time
import warnings
import io
import logging
from database import DashboardVeriErisim
from services import kritik_stok_eposta_tetikle
from tedarikci_yonetimi import TedarikciYonetimi
from config import KRITIK_STOK_ESIGI, OTOMATIK_SIPARIS_MIKTARI, TAHMIN_GUN_ESIGI

warnings.filterwarnings("ignore")

# Loglama ayarları
logging.basicConfig(
    filename='erp_sistem.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# .env dosyasındaki veritabanı şifrelerini sisteme yüklüyoruz


# --- ÖNBELLEKLEME (CACHE) KATMANI ---
# NOT: database.py bilinçli olarak Streamlit'ten habersiz tutuluyor (Faz 3
# ayrımı: database.py = veri katmanı, dashboard.py = UI). Bu yüzden
# @st.cache_data'yı sınıf metodlarına değil, burada tanımlı ince
# "sarmalayıcı" fonksiyonlara uyguluyoruz.
#
# Parametre adının "_veri" olması bilinçli: Streamlit, alt çizgiyle
# başlayan parametreleri hash'lemeye ÇALIŞMAZ. Aksi halde DashboardVeriErisim
# nesnesinin içindeki MySQL bağlantı havuzunu hash'lemeye çalışıp hataya düşerdi.
#
# ttl=30: veri en fazla 30 saniye "bayat" kalabilir. Yazma işlemlerinden sonra
# ayrıca st.cache_data.clear() ile anında da temizleniyor (bkz. aşağıdaki
# ilgili form/buton blokları).
@st.cache_resource
def veri_erisimi_al() -> DashboardVeriErisim:
    """
    DashboardVeriErisim (ve içindeki MySQL connection pool) yalnızca BİR KEZ
    oluşturulur ve tüm oturumlar arasında paylaşılır. @st.cache_data'nın
    aksine @st.cache_resource, DB bağlantısı/pool gibi "paylaşılan, yeniden
    kullanılabilir kaynaklar" içindir — her rerun'da yeniden oluşturulmaz.
    """
    return DashboardVeriErisim()
@st.cache_data(ttl=30)
def stok_listesi_cache(_veri):
    return _veri.stok_listesini_getir()

@st.cache_data(ttl=30)
def satis_verileri_cache(_veri):
    return _veri.satis_verilerini_getir()

@st.cache_data(ttl=30)
def stok_analizi_cache(_veri):
    return _veri.stok_analizi_getir()

@st.cache_data(ttl=30)
def onay_bekleyenler_cache(_veri):
    return _veri.onay_bekleyenleri_getir()

@st.cache_data(ttl=30)
def log_verileri_cache(_veri):
    return _veri.log_verilerini_getir()

@st.cache_data(ttl=60)
def tedarikci_bilgisi_cache(urun_adi):
    """
    tedarikci_yonetimi.py, dashboard.py'nin bağlantı havuzundan bağımsız
    kendi kısa ömürlü bağlantısını açar (main.py'deki CLI kullanımıyla
    aynı modül). Sonuç 60 saniye önbelleğe alınır; tedarikçi bilgisi sık
    değişen bir veri olmadığı için bu makul bir süre.
    """
    tedarikci = TedarikciYonetimi()
    if tedarikci.baglan():
        try:
            return tedarikci.tedarikci_bilgisi_getir(urun_adi)
        finally:
            tedarikci.baglantiyi_kapat()
    return {"firma": "Bağlantı Yok", "teslimat_gunu": 0, "eposta": None, "telefon": None}


# --- AKILLI BİLDİRİM MOTORU (E-POSTA SİMÜLASYONU) ---

# --- CSS (Minimalist Kurumsal) ---
def css_ayarlarini_yukle():
    st.markdown("""
    <style>
        .stApp { background-color: #f4f7f6; }
        div[data-testid="stVerticalBlock"] > div {
            background-color: #ffffff; padding: 20px; border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- ANA ARAYÜZ ---
def arayuzu_ciz():
    # set_page_config, Streamlit kuralı gereği bir sayfada çağrılan İLK
    # Streamlit komutu olmak zorunda; bu yüzden fonksiyonun en başında.
    st.set_page_config(page_title="ERP Profesyonel", layout="wide")
    css_ayarlarini_yukle()

    # Sistem Sağlığı Paneli
    with st.expander("📊 Sistem Sağlığı ve Günlükler (Loglar)"):
        try:
            with open("erp_sistem.log", "r") as f:
                log_icerigi = f.read()
                # Logları son 20 satır olarak gösterelim ki ekranı boğmasın
                log_satirlari = log_icerigi.splitlines()
                st.text("\n".join(log_satirlari[-20:]))

            if st.button("Log Dosyasını İndir"):
                with open("erp_sistem.log", "r") as f:
                    st.download_button("Dosyayı Kaydet", f, file_name="erp_sistem.log")
        except FileNotFoundError:
            st.warning("Henüz hiç log kaydı bulunamadı.")

    if 'giris_yapildi' not in st.session_state:
        st.session_state.update({'giris_yapildi': False, 'rol': None, 'kullanici_adi': None, 'eposta_gonderildi': set()})

    veri = veri_erisimi_al()

    if not st.session_state['giris_yapildi']:
        st.title("🔒 ERP Giriş")
        with st.form("login"):
            u = st.text_input("Kullanıcı"); p = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş"):
                basarili, rol = veri.kullanici_dogrula(u, p)
                if basarili:
                    st.session_state.update({'giris_yapildi': True, 'rol': rol, 'kullanici_adi': u})
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı.")
    else:
        st.title("📊 ERP Kontrol Paneli")
        if st.button("Çıkış"): st.session_state.clear(); st.rerun()

        stok_df = stok_listesi_cache(veri)

        if st.session_state['rol'] == 'Yonetici':
            # --- FİNANSAL KPI KARTLARI ---
            st.subheader("📊 Finansal Özet")

            # Toplam depo maliyetini hesaplıyoruz: (Stok Miktarı * Birim Fiyat)
            if 'UnitPrice' in stok_df.columns:
                toplam_sermaye = (stok_df['StockQuantity'] * stok_df['UnitPrice']).sum()
            else:
                toplam_sermaye = 0

            toplam_urun_cesidi = len(stok_df)
            toplam_stok_adedi = stok_df['StockQuantity'].sum()

            kpi1, kpi2, kpi3 = st.columns(3)

            kpi1.metric(label="💰 Depodaki Toplam Sermaye", value=f"₺{toplam_sermaye:,.2f}")
            kpi2.metric(label="📦 Toplam Ürün Çeşidi", value=f"{toplam_urun_cesidi} Adet")
            kpi3.metric(label="📈 Toplam Stok Hacmi", value=f"{toplam_stok_adedi} Birim")

            st.divider()
            # -----------------------------
            # Üst Sütunlar: Grafikler ve Tahminleme
            satis = satis_verileri_cache(veri)

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📈 Satış Analizi")
                st.plotly_chart(px.bar(satis, x='ProductName', y='Toplam_Satis', color_discrete_sequence=['#00c2cb']), use_container_width=True)

            bildirim_listesi = []

            with c2:
                st.subheader("🔮 Stok Bitme Tahmini")
                analiz_df = stok_analizi_cache(veri)

                if analiz_df is not None and not analiz_df.empty:
                    gosterilecek_df = analiz_df[['ProductName', 'StockQuantity', 'Kalan_Gun_Tahmini']].copy()
                    gosterilecek_df['Kalan_Gun_Tahmini'] = gosterilecek_df['Kalan_Gun_Tahmini'].astype(int)

                    gosterilecek_df['Tahmin'] = gosterilecek_df['Kalan_Gun_Tahmini'].apply(
                        lambda x: "Veri Yok" if x == 999 else f"{x} Gün"
                    )

                    for idx, row in gosterilecek_df.iterrows():
                        if row['Kalan_Gun_Tahmini'] < TAHMIN_GUN_ESIGI:
                            bildirim_listesi.append(row['ProductName'])

                    gosterilecek_df = gosterilecek_df[['ProductName', 'StockQuantity', 'Tahmin']]

                    def renk_ata(val):
                        if val == "Veri Yok": return 'color: #888888; font-style: italic;'
                        gun = int(val.split(' ')[0])
                        color = '#ff4b4b' if gun < TAHMIN_GUN_ESIGI else '#28a745'
                        return f'color: {color}; font-weight: bold;'

                    st.dataframe(gosterilecek_df.style.map(renk_ata, subset=['Tahmin']), use_container_width=True, hide_index=True)

                    # --- EXCEL RAPORLAMA BUTONU ---
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        gosterilecek_df.to_excel(writer, index=False, sheet_name='Kritik Stoklar')

                    st.download_button(
                        label="📥 Raporu Excel Olarak İndir",
                        data=buffer.getvalue(),
                        file_name="kritik_stok_raporu.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            # --- TEDARİKÇİ SİPARİŞ MODÜLÜ ---
            if bildirim_listesi:
                st.divider()
                st.subheader("🛒 Akıllı Satın Alma (Tedarikçi Modülü)")

                po_col1, po_col2 = st.columns([2, 3])

                with po_col1:
                    st.markdown("**Kritik Ürün Siparişi Oluştur**")
                    secilen_urun = st.selectbox("Tedarik Edilecek Ürün", bildirim_listesi)
                    siparis_adedi = st.number_input("Sipariş Adedi", min_value=10, step=10)

                    # Gerçek tedarikçi bilgisini SQL'den çekip seçim yapılırken gösteriyoruz
                    tedarikci_bilgisi = tedarikci_bilgisi_cache(secilen_urun)
                    st.caption(
                        f"📦 Tedarikçi: **{tedarikci_bilgisi['firma']}**  |  "
                        f"Tahmini Teslimat: **{tedarikci_bilgisi['teslimat_gunu']} gün**"
                    )
                    if tedarikci_bilgisi.get('eposta') or tedarikci_bilgisi.get('telefon'):
                        st.caption(
                            f"✉️ {tedarikci_bilgisi.get('eposta') or '—'}  |  "
                            f"📞 {tedarikci_bilgisi.get('telefon') or '—'}"
                        )

                    siparis_ver = st.button("Tedarikçiye Sipariş Geç", type="primary", use_container_width=True)

                with po_col2:
                    if siparis_ver:
                        # Sipariş, Purchase_Orders tablosuna gerçekten yazılıyor (mükerrer
                        # kontrolüyle birlikte); "Onay Bekleyen Siparişler" listesinde görünür.
                        olusturuldu = veri.otomatik_siparis_taslagi_olustur(secilen_urun, int(siparis_adedi))

                        if olusturuldu:
                            st.cache_data.clear()
                            tarih = pd.Timestamp.now().strftime("%d.%m.%Y %H:%M")
                            st.success("✅ Satın Alma Talebi (PO) veritabanına kaydedildi.")
                            st.info(f"""
                            **📄 SATIN ALMA SİPARİŞ FİŞİ**

                            * **Tarih/Saat:** {tarih}
                            * **Talep Eden:** {st.session_state['kullanici_adi']} (Yönetici)
                            * **Tedarik Edilecek Ürün:** {secilen_urun}
                            * **Talep Edilen Miktar:** {siparis_adedi} Adet
                            * **Tedarikçi:** {tedarikci_bilgisi['firma']}
                            * **Tahmini Teslimat:** {tedarikci_bilgisi['teslimat_gunu']} gün
                            * **Durum:** Beklemede / Yönetici Onayı Bekliyor

                            Sipariş, aşağıdaki "Onay Bekleyen Satın Alma Siparişleri" listesinde görünecektir.
                            """)
                        else:
                            st.warning(f"ℹ️ {secilen_urun} için zaten bekleyen bir sipariş var, yenisi açılmadı.")

            st.subheader("📦 Onay Bekleyen Satın Alma Siparişleri")

            siparisler = onay_bekleyenler_cache(veri)

            if siparisler:
                for siparis in siparisler:
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    col1.write(f"**{siparis['ProductName']}**")
                    col2.write(f"Miktar: {siparis['OrderQuantity']}")
                    col3.write(f"Tarih: {siparis['OrderDate']}")

                    if col4.button("Onayla", key=f"btn_{siparis['OrderID']}"):
                        if veri.siparis_onayla(siparis['OrderID']):
                            st.cache_data.clear()
                            st.success("✅ Sipariş onaylandı!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Onaylama başarısız.")
            else:
                st.info("Şu an onay bekleyen sipariş bulunmuyor.")

            # Denetim İzi & Raporlama
            st.subheader("🕵️ Denetim İzi & Raporlama")
            st.dataframe(log_verileri_cache(veri), use_container_width=True)
            st.download_button("📊 Stok Raporunu İndir", stok_df.to_csv(index=False), 'stok.csv', 'text/csv')

            # Ürün Yönetimi
            st.subheader("🛠️ Ürün Yönetimi")
            t1, t2 = st.tabs(["Ekle", "Sil"])
            with t1:
                with st.form("ekle"):
                    a = st.text_input("Ad")
                    f = st.number_input("Fiyat", min_value=0.0, step=0.01)
                    s = st.number_input("Stok", min_value=0, step=1)
                    if st.form_submit_button("Ekle"):
                        # Widget seviyesindeki min_value=0 kontrolüne güvenmek yerine
                        # burada da açıkça doğruluyoruz (defense-in-depth): örn. ileride
                        # bu fonksiyon başka bir yerden (API, script vb.) çağrılırsa
                        # negatif/sıfır değerler yine de yakalanmış olur.
                        hatalar = []
                        if not a.strip():
                            hatalar.append("Ürün adı boş olamaz.")
                        if f <= 0:
                            hatalar.append("Fiyat sıfırdan büyük olmalıdır.")
                        if s < 0:
                            hatalar.append("Stok negatif olamaz.")

                        if hatalar:
                            for hata in hatalar:
                                st.error(hata)
                        else:
                            veri.urun_islemleri(a, f, s, "ekle")
                            st.cache_data.clear()
                            st.rerun()
            with t2:
                sil = st.selectbox("Ürün Seç", stok_df['ProductName'].tolist())
                if st.button("Sil"):
                    veri.urun_islemleri(sil, 0, 0, "sil")
                    st.cache_data.clear()
                    st.rerun()

        elif st.session_state['rol'] == 'Depo_Calisani':
            st.info(f"Hoş geldiniz, {st.session_state['kullanici_adi'].capitalize()} | Aktif Yetki: Depo Operasyonları")

            st.subheader("📦 Mevcut Stok Durumu")
            st.dataframe(stok_df, use_container_width=True)

            st.divider()

            st.subheader("📝 Stok Güncelleme Formu")
            with st.form("guncelle"):
                u = st.selectbox("Ürün", stok_df['ProductName'].tolist())
                m = st.number_input("Yeni Miktar", min_value=0, step=1)

                if st.form_submit_button("Güncelle"):
                    # Widget seviyesindeki min_value=0'a ek olarak kod tarafında da
                    # açıkça doğruluyoruz (defense-in-depth).
                    if m < 0:
                        st.error("Stok miktarı negatif olamaz.")
                        st.stop()

                    # 1. Önce veritabanında stoğu güncelliyoruz
                    veri.stok_guncelle(u, m, st.session_state['kullanici_adi'])
                    st.cache_data.clear()
                    st.success(f"✅ {u} stoğu {m} olarak güncellendi.")

                    # 2. EĞER YENİ STOK KRİTİK EŞİĞİN ALTINDAYSA:
                    #    a) e-posta bildirimi gönder, b) tedarik siparişi taslağı aç
                    if int(m) < KRITIK_STOK_ESIGI:
                        # a) E-posta bildirimi (her ürün için oturum başına yalnızca bir kez)
                        gonderilenler = st.session_state.setdefault('eposta_gonderildi', set())
                        if u not in gonderilenler:
                            eposta_basarili = kritik_stok_eposta_tetikle(u, m)
                            if eposta_basarili:
                                gonderilenler.add(u)
                                st.info(f"📧 {u} için kritik stok bildirim e-postası gönderildi.")
                            else:
                                st.warning("E-posta gönderilemedi, loglara bakın.")

                        # b) Otomatik satın alma taslağı
                        try:
                            yeni_siparis_acildi_mi = veri.otomatik_siparis_taslagi_olustur(u, OTOMATIK_SIPARIS_MIKTARI)
                            if yeni_siparis_acildi_mi:
                                st.cache_data.clear()
                                st.success(f"✅ Otomatik sipariş başarıyla veritabanına işlendi: {u}")
                            else:
                                st.info(f"ℹ️ {u} için zaten bekleyen bir sipariş var, yenisi açılmadı.")
                        except Exception as e:
                            st.error(f"❌ Sipariş hatası: {e}")

if __name__ == "__main__":
    arayuzu_ciz()
