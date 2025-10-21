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
2. 執行以下命令以開始數據抓取：
   ```bash
   python colatour_fetch_data.py
   ```
3. 輸入所需的出發地、目的地、出發日期和返回日期，系統將自動導航並抓取相關數據。

### API 取得節日日期功能

本專案整合了節日日期查詢 API，可自動取得未來月份的節日日期資訊。

#### 使用範例

**取得 2 個月後的節日日期：**
```python
from colatour_fetch_data import get_holiday_dates

# 取得 2 個月後的節日日期
holidays = get_holiday_dates(month_offset=2)
for holiday in holidays:
    print(f"節日名稱: {holiday['holiday_name']}")
    print(f"出發日期: {holiday['departure_date']}")
    print(f"返回日期: {holiday['return_date']}")
```

**取得 6 個月後的節日日期：**
```python
# 取得 6 個月後的節日日期
holidays = get_holiday_dates(month_offset=6)
for holiday in holidays:
    print(f"節日名稱: {holiday['holiday_name']}")
    print(f"出發日期: {holiday['departure_date']}")
    print(f"返回日期: {holiday['return_date']}")
```

#### API 回應格式

API 回應包含以下欄位：
- `holiday_name`: 節日名稱
- `holiday_date`: 節日日期（格式：YYYY-MM-DD）
- `departure_date`: 建議出發日期（格式：YYYY-MM-DD）
- `return_date`: 建議返回日期（格式：YYYY-MM-DD）
- `weekday`: 星期幾

### API 取得固定月份日期功能

本專案整合了固定月份日期查詢 API，可自動取得未來指定月份的固定日期資訊。

#### 使用範例

**取得 2 個月後（5 號去 10 號回）的日期：**
```python
from colatour_fetch_data import get_fixed_dates

# 取得 2 個月後，5 號去 10 號回的日期
dates = get_fixed_dates(month_offset=2, dep_day=5, return_day=10)
print(f"出發日期: {dates['departure_date']}")
print(f"返回日期: {dates['return_date']}")
```

**取得 6 個月後（5 號去 10 號回）的日期：**
```python
# 取得 6 個月後，5 號去 10 號回的日期
dates = get_fixed_dates(month_offset=6, dep_day=5, return_day=10)
print(f"出發日期: {dates['departure_date']}")
print(f"返回日期: {dates['return_date']}")
```

#### API 回應格式

API 回應包含以下欄位：
- `departure_date`: 出發日期（格式：YYYY-MM-DD）
- `return_date`: 返回日期（格式：YYYY-MM-DD）
- `target_year`: 目標年份
- `target_month`: 目標月份

## 常見問題
1. **為什麼我的爬蟲無法正常運行？**
   - 請確認 ChromeDriver 的版本與 Chrome 瀏覽器版本匹配。
   - 確保網絡連接正常，並且網站可訪問。

2. **如何處理驗證碼問題？**
   - 本專案使用預訓練的模型來自動識別驗證碼，請確保 `captcha_model_1.keras` 文件存在於指定路徑。

3. **數據抓取後如何查看結果？**
   - 抓取的數據將自動寫入 BigQuery，您可以通過 BigQuery 控制台查看和分析數據。

