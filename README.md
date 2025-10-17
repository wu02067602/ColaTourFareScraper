# ColaTourFareScraper

## 專案簡介
ColaTourFareScraper 是一個用於爬取可樂旅遊網站上機票票價的專案，並將數據寫入 BigQuery。此專案主要目的是自動化地獲取機票價格資訊，並進行數據清理和整合，以便於後續的數據分析。

## 目錄
- [專案簡介](#專案簡介)
- [目錄](#目錄)
- [安裝指南](#安裝指南)
- [使用說明](#使用說明)
- [常見問題](#常見問題)

## 安裝指南
1. 確保已安裝 Python 3.6 或以上版本。
2. 克隆此專案到本地：
   ```bash
   git clone <repository-url>
   ```
3. 進入專案目錄並安裝所需的依賴：
   ```bash
   cd ColaTourFareScraper
   pip install -r requirements.txt
   ```

## 使用說明
1. 確保已安裝 Chrome 瀏覽器和對應版本的 ChromeDriver。
2. 設定必要的環境變數：
   ```bash
   export IATA_ID=<目的地機場代碼>
   export API_BASE_URL=<API 伺服器網址>  # 預設為 http://localhost:8000
   ```
3. 執行以下命令以開始數據抓取：
   ```bash
   python colatour_fetch_data.py
   ```
4. 系統將自動從 API 取得 2 個月後和 6 個月後的節日日期，並針對這些日期進行機票價格爬取。

### 日期取得機制
程式會透過 API 自動取得未來的節日日期：
- **2 個月後的節日**：呼叫 `POST /calculate_holiday_dates` with `month_offset=2`
- **6 個月後的節日**：呼叫 `POST /calculate_holiday_dates` with `month_offset=6`

API 會回傳該月份的節日資訊，包含建議的出發日期 (`departure_date`) 和回程日期 (`return_date`)，系統將針對這些日期組合進行票價查詢。

## 常見問題
1. **為什麼我的爬蟲無法正常運行？**
   - 請確認 ChromeDriver 的版本與 Chrome 瀏覽器版本匹配。
   - 確保網絡連接正常，並且網站可訪問。

2. **如何處理驗證碼問題？**
   - 本專案使用預訓練的模型來自動識別驗證碼，請確保 `captcha_model_1.keras` 文件存在於指定路徑。

3. **數據抓取後如何查看結果？**
   - 抓取的數據將自動寫入 BigQuery，您可以通過 BigQuery 控制台查看和分析數據。

