# 使用官方的 Python 基礎映像
FROM python:3.10-slim-buster

# 設定環境變數，避免輸出緩衝，讓日誌即時顯示
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 設定工作目錄
WORKDIR /app

# 將本地的 requirements.txt 複製到容器中
COPY requirements.txt /app/

# 安裝所有 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 將整個專案複製到容器中
COPY . /app/

# 運行 collectstatic 來收集靜態檔案（如果你的靜態檔案也由Django應用伺服）
# 如果你完全透過GCS服務靜態檔案，這一步可以省略或簡化
# RUN python manage.py collectstatic --noinput

# 運行資料庫遷移 (注意：這會在每次容器啟動時運行，生產環境下考慮單獨執行)
# 更好的做法是在部署前手動執行一次 migrate，或作為 Cloud Run 部署步驟的一部分
# CMD python manage.py migrate --noinput && gunicorn your_project_name.wsgi:application --bind :$PORT
# 因為是CMD，所以每次啟動容器都會執行。你也可以考慮在部署後單獨執行 migrate。

# 定義容器啟動時執行的命令
# Cloud Run 會將請求發送到你的應用程式監聽的 $PORT
CMD gunicorn FinalProject.wsgi:application --bind :$PORT