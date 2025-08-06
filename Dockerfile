# # 選擇一個適合編譯的基礎映像，例如一個標準的 Debian 或 Ubuntu 映像
# FROM python:3.10-slim-buster as builder

# # 安裝編譯所需的工具和依賴
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     libsqlite3-dev \
#     wget \
#     xz-utils \
#     --no-install-recommends && \
#     rm -rf /var/lib/apt/lists/*

# # 下載並解壓所需版本的 SQLite3 源碼
# ENV SQLITE_VERSION 3350000 # 這是 3.35.0 的數字表示 (major*1000000 + minor*1000 + patch)
# RUN wget https://www.sqlite.org/2021/sqlite-autoconf-${SQLITE_VERSION}.tar.gz && \
#     tar xzf sqlite-autoconf-${SQLITE_VERSION}.tar.gz && \
#     cd sqlite-autoconf-${SQLITE_VERSION} && \
#     ./configure --prefix=/usr/local && \
#     make && \
#     make install && \
#     cd / && \
#     rm -rf sqlite-autoconf-${SQLITE_VERSION} sqlite-autoconf-${SQLITE_VERSION}.tar.gz
# 切換到運行時映像 (通常是一個更小的 slim 映像)
FROM python:3.10-slim-bookworm

# 設定環境變數，避免輸出緩衝，讓日誌即時顯示
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# 確保運行時使用新編譯的 SQLite3 庫
# ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# 設定工作目錄
WORKDIR /app

# 將本地的 requirements.txt 複製到容器中
COPY requirements.txt /app/

# 安裝所有 Python 依賴
RUN pip install -r requirements.txt

RUN pip install sentence-transformers
ENV MODEL_DIR=/app/models/sentence-transformers/
RUN mkdir -p ${MODEL_DIR}
RUN python -c "from sentence_transformers.util import snapshot_download; snapshot_download(repo_id='sentence-transformers/all-MiniLM-L6-v2', cache_dir='${MODEL_DIR}')"

# 將整個專案複製到容器中
COPY . /app/

# 運行 collectstatic 來收集靜態檔案（如果你的靜態檔案也由Django應用伺服）
# 如果你完全透過GCS服務靜態檔案，這一步可以省略或簡化
# RUN python manage.py collectstatic --noinput

# 運行資料庫遷移 (注意：這會在每次容器啟動時運行，生產環境下考慮單獨執行)
# 更好的做法是在部署前手動執行一次 migrate，或作為 Cloud Run 部署步驟的一部分
# RUN python manage.py collectstatic --noinput

# 定義容器啟動時執行的命令
# Cloud Run 會將請求發送到你的應用程式監聽的 $PORT
CMD gunicorn FinalProject.wsgi:application --bind :$PORT