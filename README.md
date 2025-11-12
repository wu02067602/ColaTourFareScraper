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

## 爬蟲速度優化方案

### 現況分析

在 `task_controller.py` 的 `collect_all_flight_data` 函數中，存在巢狀迴圈結構（第 109-131 行），是影響爬蟲速度的主要瓶頸：

```python
for d_idx in range(dep_count):          # 去程選項迴圈
    for r_idx in range(ret_count):      # 回程選項迴圈
        # 每次迴圈都進行：
        # 1. 重新查詢 DOM 元素
        # 2. 滾動到元素位置
        # 3. 點擊按鈕
        # 4. 等待 0.1 秒
        # 5. 取得航班、行李、票價資訊
```

**效能問題**：
- 若有 5 個去程選項 × 5 個回程選項 = 25 次組合
- 每次組合需要重複執行滾動、點擊、等待等操作
- 大量的 DOM 重新查詢造成效能損耗
- 固定的 `time.sleep(0.1)` 無法根據實際情況調整

### 優化方案

#### 方案一：元素快取與批量處理

**核心概念**：
1. 在迴圈開始前一次性抓取並快取所有元素
2. 使用智慧等待機制替代固定 sleep
3. 減少不必要的 DOM 重新查詢

**實作架構**（符合 SOLID 原則）：

```python
class ElementCache:
    """
    元素快取器，負責預先抓取並快取 DOM 元素。
    
    單一職責原則：僅負責元素的快取與檢索。
    """
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self._cache = {}
    
    def cache_flight_buttons(self, card_element, segment_divs):
        """預先快取所有航班選項按鈕"""
        pass

class SmartWaitHandler:
    """
    智慧等待處理器，根據元素狀態動態調整等待時間。
    
    單一職責原則：僅負責等待邏輯的處理。
    開放封閉原則：可擴展不同的等待策略。
    """
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
    
    def wait_for_clickable(self, element, timeout=5):
        """等待元素可點擊"""
        pass
    
    def wait_for_element_stable(self, element):
        """等待元素穩定（避免動畫造成的點擊失敗）"""
        pass

class BatchClickProcessor:
    """
    批量點擊處理器，優化點擊流程。
    
    單一職責原則：僅負責批量點擊的邏輯處理。
    """
    def __init__(self, driver: webdriver.Chrome, wait_handler: SmartWaitHandler):
        self.driver = driver
        self.wait_handler = wait_handler
    
    def process_flight_combinations(self, cached_elements):
        """批量處理航班組合的點擊與資料抓取"""
        pass
```

**優化效果預估**：
- 減少 60-70% 的 DOM 查詢次數
- 動態等待機制可節省 30-50% 的等待時間
- 整體速度提升約 2-3 倍

#### 方案二：JavaScript 注入優化

**核心概念**：
直接使用 JavaScript 操作 DOM，繞過 Selenium 的封裝層。

**實作重點**：
```python
class JavaScriptOptimizer:
    """
    JavaScript 優化器，使用原生 JS 提升操作速度。
    
    單一職責原則：僅負責 JavaScript 相關的優化操作。
    """
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
    
    def batch_click_via_js(self, elements):
        """使用 JavaScript 批量點擊元素"""
        js_script = """
        const elements = arguments[0];
        elements.forEach(el => {
            el.scrollIntoView({block: 'center'});
            el.click();
        });
        """
        self.driver.execute_script(js_script, elements)
    
    def check_element_states(self, elements):
        """批量檢查元素狀態"""
        pass
```

**優化效果預估**：
- 減少 Selenium 封裝層的開銷
- 批量操作可節省 40-60% 的執行時間

#### 方案三：並行資料抓取

**核心概念**：
將資料抓取分離為獨立任務，使用非同步方式處理。

**注意事項**：
- Selenium WebDriver 本身不支援多執行緒
- 需要使用多個 WebDriver 實例（資源消耗較大）
- 適合處理大量獨立的查詢任務

**實作架構**：
```python
class ParallelScraper:
    """
    並行爬蟲處理器。
    
    單一職責原則：僅負責並行任務的協調。
    依賴反轉原則：依賴抽象的 ScraperTask 而非具體實作。
    """
    def __init__(self, worker_count: int = 3):
        self.worker_count = worker_count
        self.task_queue = Queue()
    
    def distribute_tasks(self, flight_cards):
        """將航班卡片分配給不同的 worker"""
        pass
```

**優化效果預估**：
- 若使用 3 個 worker，理論速度提升 2-2.5 倍
- 資源消耗增加 3 倍（記憶體、CPU）

### 建議採用方案

**推薦：方案一 + 方案二 的混合應用**

**理由**：
1. **符合 SOLID 原則**：
   - 單一職責：每個類別專注於特定功能
   - 開放封閉：可輕鬆擴展新的等待策略或處理邏輯
   - 依賴反轉：高層模組依賴抽象介面

2. **效益最大化**：
   - 元素快取減少重複查詢
   - JavaScript 注入提升執行效率
   - 智慧等待機制優化時間控制

3. **風險最低**：
   - 不需要多個 WebDriver 實例
   - 避免資源消耗過大
   - 維持程式碼的可維護性

4. **易於實作與測試**：
   - 可逐步重構現有程式碼
   - 每個元件可獨立測試
   - 不影響現有功能的穩定性

### 實施步驟

1. **第一階段**：實作 `ElementCache` 類別
   - 測試快取機制的穩定性
   - 驗證效能提升幅度

2. **第二階段**：實作 `SmartWaitHandler` 類別
   - 替換固定的 `time.sleep(0.1)`
   - 使用 WebDriverWait 進行智慧等待

3. **第三階段**：實作 `JavaScriptOptimizer` 類別
   - 優化滾動與點擊操作
   - 批量處理元素狀態檢查

4. **第四階段**：整合與測試
   - 重構 `collect_all_flight_data` 函數
   - 進行完整的端到端測試
   - 效能基準測試與比較

## 常見問題
1. **為什麼我的爬蟲無法正常運行？**
   - 請確認 ChromeDriver 的版本與 Chrome 瀏覽器版本匹配。
   - 確保網絡連接正常，並且網站可訪問。

2. **如何處理驗證碼問題？**
   - 本專案使用預訓練的模型來自動識別驗證碼，請確保 `captcha_model_1.keras` 文件存在於指定路徑。

3. **數據抓取後如何查看結果？**
   - 抓取的數據將自動寫入 BigQuery，您可以通過 BigQuery 控制台查看和分析數據。

