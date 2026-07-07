# --- ERP Streamlit Uygulaması ---
# NOT: main.py bilinçli olarak burada KULLANILMIYOR. main.py, bu sohbette
# paylaşılmamış olan stok_takip.py ve tedarikci_yonetimi.py modüllerine
# bağımlı; konteyner doğrudan dashboard.py'yi (Streamlit uygulamasının
# kendisi) çalıştırıyor. main.py'yi de dahil etmek isterseniz o iki
# dosyayı da projeye eklemeniz ve CMD'yi güncellemeniz gerekir.

FROM python:3.11-slim

# MySQL client kütüphanesinin derlenmesi için gerekli sistem paketleri
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Önce sadece requirements.txt kopyalanıyor ki bağımlılıklar değişmediği
# sürece Docker layer cache'i korunsun (kod her değiştiğinde pip install
# yeniden tetiklenmesin).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunun tamamı
COPY dashboard.py database.py services.py config.py ./
COPY .streamlit ./.streamlit

EXPOSE 8501

# Streamlit'in konteyner dışından erişilebilir olması için 0.0.0.0'a bağlanıyoruz
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
