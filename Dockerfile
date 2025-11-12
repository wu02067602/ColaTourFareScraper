# 使用官方 Python 運行時作為父鏡像
FROM python:3.10-slim

# 設置工作目錄
WORKDIR /app

# 複製目前目錄的內容到 /app 中的容器裡
COPY . /app

# 更新並安裝必要的軟體包，包括 wget、unzip、curl 和 Xvfb
RUN apt-get update && \
    apt-get install -y wget unzip curl gnupg ca-certificates xvfb && \
    rm -rf /var/lib/apt/lists/*

# 根據系統架構（ARM64/AMD64）安裝對應的瀏覽器和驅動程式
RUN if [ "$(uname -m)" = "aarch64" ]; then \
    # === ARM64 架構的處理流程 ===
    apt-get update && \
    apt-get install -y \
        chromium \
        chromium-driver \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/chromium /usr/bin/google-chrome \
    && ln -s /usr/bin/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver; \
else \
    # === AMD64 架構的處理流程 ===
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg && \
    chmod 644 /etc/apt/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y \
        google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* \
    && CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | awk -F. '{print $1 "." $2 "." $3}') \
    && LATEST_DRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION}") \
    && wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${LATEST_DRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/ \
    && rm -rf chromedriver-linux64.zip chromedriver-linux64 \
    && chmod +x /usr/local/bin/chromedriver; \
fi

# 安裝 Python 依賴
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# 安裝 chromedriver_autoinstaller
RUN pip install chromedriver-autoinstaller

# 讓連接埠 80 可供此容器外的環境使用
EXPOSE 80

# 在容器啟動時啟動 Xvfb 和執行 main.py
CMD ["sh", "-c", "Xvfb :99 -ac & python main.py"]
