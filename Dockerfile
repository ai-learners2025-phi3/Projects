# 切換到運行時映像 (通常是一個更小的 slim 映像)
FROM python:3.10-slim-buster

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

# 將整個專案複製到容器中
COPY . /app/

# 執行 collectstatic 收集靜態檔案
RUN python manage.py collectstatic --noinput
# 定義容器啟動時執行的命令
# Cloud Run 會將請求發送到你的應用程式監聽的 $PORT
CMD gunicorn FinalProject.wsgi:application --bind :$PORT