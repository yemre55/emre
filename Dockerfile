# --- ERP Streamlit Uygulaması (multi-stage build) ---
# NOT: main.py bilinçli olarak burada KULLANILMIYOR. main.py, ayrı bir CLI
# akışı (stok_takip.py bağımlılığıyla) için tasarlanmış; konteyner doğrudan
# dashboard.py'yi (Streamlit uygulamasının kendisi) çalıştırıyor.
# tedarikci_yonetimi.py artık dashboard.py tarafından da kullanıldığı için
# (gerçek tedarikçi/teslimat bilgisi çekmek üzere) imaja dahil edilmiştir.
#
# NEDEN MULTI-STAGE?
# gcc / libmysqlclient-dev / pkg-config gibi paketler SADECE bazı Python
# paketlerini derlemek (build) için gerekiyor; uygulama ÇALIŞIRKEN bunlara
# ihtiyaç yok. Tek aşamalı bir Dockerfile'da bu derleyici araçları son
# image'da da kalır ve gereksiz yere yüz MB'larca yer kaplar. Burada iki
# aşama kullanıyoruz:
#   1) "builder": derleyicilerin kurulu olduğu geçici bir aşama, sadece
#      bağımlılıkları /root/.local altına kurmak için var.
#   2) son aşama: derleyicisiz, temiz bir image; builder'dan sadece kurulu
#      Python paketlerini (derleyicileri değil) kopyalar.
# Sonuç: aynı uygulama, önemli ölçüde daha küçük ve daha güvenli (gereksiz
# derleyici araçları saldırı yüzeyini de azaltır) bir image.

# ---------- 1) BUILDER AŞAMASI ----------
FROM python:3.11-slim AS builder

# MySQL connector'ın (ve varsa diğer C-uzantılı paketlerin) derlenmesi
# için gerekli sistem paketleri — SADECE bu aşamada kalıyor.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Önce sadece requirements.txt kopyalanıyor ki bağımlılıklar değişmediği
# sürece Docker layer cache'i korunsun (kod her değiştiğinde pip install
# yeniden tetiklenmesin).
COPY requirements.txt .
# --user: paketleri /root/.local altına kurar, böylece final aşamada
# tek bir COPY ile (site-packages'ın tamamını didiklemeden) taşınabilir.
RUN pip install --no-cache-dir --user -r requirements.txt

# ---------- 2) FİNAL (ÇALIŞMA ZAMANI) AŞAMASI ----------
FROM python:3.11-slim

# Çalışma zamanında SADECE healthcheck için curl gerekiyor — derleyici yok.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# builder aşamasında kurulan Python paketlerini (derleyicileri DEĞİL)
# olduğu gibi kopyalıyoruz.
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Uygulama kodunun tamamı
COPY dashboard.py database.py services.py config.py tedarikci_yonetimi.py ./
COPY .streamlit ./.streamlit

EXPOSE 8501

# Streamlit'in konteyner dışından erişilebilir olması için 0.0.0.0'a bağlanıyoruz
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
