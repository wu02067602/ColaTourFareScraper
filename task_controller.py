# 標準庫
import time
from typing import List

# 第三方庫
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# 本地模組
from data_cleaner import BaggageDataExtractor, FlightDataExtractor, PriceDataExtractor
from web_operator import FlightOptionExpander, WebDriverFactory, WebNavigator


class FlightDataCollector:
    """
    航班資料收集器，負責從網頁收集航班、票價、行李資料。
    
    Examples:
        >>> collector = FlightDataCollector(driver)
        >>> data = collector.collect_all_flight_data("2025/10/15", "2025/10/20")
    
    Raises:
        ValueError: 當參數無效時
    """
    
    def __init__(self, driver: webdriver.Chrome):
        """
        初始化航班資料收集器。
        
        Args:
            driver (webdriver.Chrome): Selenium WebDriver 實例。
        
        Examples:
            >>> collector = FlightDataCollector(driver)
        
        Raises:
            ValueError: 當 driver 為 None 時
        """
        if driver is None:
            raise ValueError("driver 不可為 None")
        
        self.driver = driver
        self.flight_extractor = FlightDataExtractor()
        self.price_extractor = PriceDataExtractor()
        self.baggage_extractor = BaggageDataExtractor()
    
    def collect_all_flight_data(self, start_date: str, return_date: str) -> List[dict]:
        """
        收集所有航班資料。
        
        Args:
            start_date (str): 出發日期，格式 'YYYY/MM/DD'。
            return_date (str): 回程日期，格式 'YYYY/MM/DD'。
        
        Returns:
            List[dict]: 收集到的所有航班資料列表。
        
        Examples:
            >>> collector = FlightDataCollector(driver)
            >>> data = collector.collect_all_flight_data("2025/10/15", "2025/10/20")
            >>> len(data) > 0
            True
        
        Raises:
            ValueError: 當 start_date 或 return_date 為空時
        """
        if not start_date:
            raise ValueError("start_date 不可為空")
        if not return_date:
            raise ValueError("return_date 不可為空")
        
        flight_cards = self.driver.find_elements(By.CLASS_NAME, 'airPrice_box')
        print(f"找到 {len(flight_cards)} 張航班卡片")

        extracted_rows = []
        for card_index, card in enumerate(flight_cards):
            # 驗證每一張卡片是否只有兩組 MultiSegment div
            multi_segment_divs = card.find_elements(
                By.XPATH, 
                ".//div[@ng-repeat='MultiSegment in cjSegment[$index]' and @ng-init='MultiSegmentIndex=$index' and @class='ng-scope']"
            )
            
            if len(multi_segment_divs) != 2:
                print(f"警告：第 {card_index + 1} 張卡片包含 {len(multi_segment_divs)} 組 MultiSegment div（預期為 2 組）")
                continue
            else:
                print(f"第 {card_index + 1} 張卡片驗證通過：包含 {len(multi_segment_divs)} 組 MultiSegment div")

            # 去程航班以及按鈕
            departure_flights_buttons = multi_segment_divs[0].find_elements(
                By.XPATH, 
                ".//input[@type='radio' and @name]"
            )
            
            # 回程航班以及按鈕
            return_flights_buttons = multi_segment_divs[1].find_elements(
                By.XPATH, 
                ".//input[@type='radio' and @name]"
            )
            
            dep_count = len(departure_flights_buttons)
            ret_count = len(return_flights_buttons)

            for d_idx in range(dep_count):
                dep_list = multi_segment_divs[0].find_elements(
                    By.XPATH, 
                    ".//input[@type='radio' and @name]"
                )
                if d_idx >= len(dep_list):
                    break
                dep_btn = dep_list[d_idx]
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", dep_btn)
                self.driver.execute_script("arguments[0].click();", dep_btn)
                time.sleep(0.1)

                for r_idx in range(ret_count):
                    ret_list = multi_segment_divs[1].find_elements(
                        By.XPATH, 
                        ".//input[@type='radio' and @name]"
                    )
                    if r_idx >= len(ret_list):
                        break
                    ret_btn = ret_list[r_idx]
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ret_btn)
                    self.driver.execute_script("arguments[0].click();", ret_btn)
                    time.sleep(0.1)

                    # 航班資訊取得
                    flight_tab = card.find_element(By.CSS_SELECTOR, "a.tab01")
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", flight_tab)
                    self.driver.execute_script("arguments[0].click();", flight_tab)
                    WebDriverWait(self.driver, 5).until(
                        lambda d: len(card.find_elements(By.CSS_SELECTOR, ".flightDetails_table")) >= 2
                    )
                    flight_extracted = self.flight_extractor.extract_and_clean_flight_data(
                        card, start_date, return_date
                    )

                    # 行李資訊取得
                    baggage_tab = card.find_element(By.CSS_SELECTOR, "a.tab03")
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", baggage_tab)
                    self.driver.execute_script("arguments[0].click();", baggage_tab)
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".bagInformation_tab"))
                    )
                    current_flight_details = flight_extracted[0] if flight_extracted else {}
                    card_baggage_info = self.baggage_extractor.extract_and_clean_baggage_data(
                        card, self.driver, current_flight_details
                    )

                    # 票價資訊取得
                    price_strong = card.find_element(
                        By.CSS_SELECTOR, 
                        "strong[bo-text='SaleGroup.Display_Price | number']"
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", price_strong)
                    self.driver.execute_script("arguments[0].click();", price_strong)
                    price_extracted = self.price_extractor.extract_and_clean_price_data(card)

                    # 點擊背景遮罩復原彈出視窗
                    overlay = self.driver.find_element(By.CSS_SELECTOR, ".ui-widget-overlay.ui-front")
                    self.driver.execute_script("arguments[0].click();", overlay)

                    # 爬取時間戳記
                    created_at = time.time()

                    # 合併資料
                    row = {**flight_extracted[0], **price_extracted[0], **card_baggage_info, "建立時間": created_at}
                    extracted_rows.append(row)

        return extracted_rows


class DataFrameBuilder:
    """
    DataFrame 建構器，負責將收集到的資料建構成 DataFrame。
    
    Examples:
        >>> builder = DataFrameBuilder()
        >>> df = builder.build_dataframe(extracted_rows)
    
    Raises:
        ValueError: 當參數無效時
    """
    
    @staticmethod
    def build_dataframe(extracted_rows: List[dict]) -> pd.DataFrame:
        """
        建構 DataFrame。
        
        Args:
            extracted_rows (List[dict]): 收集到的資料列表。
        
        Returns:
            pd.DataFrame: 建構好的 DataFrame。
        
        Examples:
            >>> builder = DataFrameBuilder()
            >>> df = builder.build_dataframe([{'col1': 1, 'col2': 2}])
            >>> len(df)
            1
        
        Raises:
            ValueError: 當 extracted_rows 為 None 時
        """
        if extracted_rows is None:
            raise ValueError("extracted_rows 不可為 None")
        
        column_order = []
        for d in ["去程", "回程"]:
            for i in range(1, 4):
                column_order.extend([
                    f"{d}航班編號{i}",
                    f"{d}艙等與艙等編碼{i}",
                    f"{d}起飛機場{i}",
                    f"{d}降落機場{i}",
                    f"{d}起飛時間{i}",
                    f"{d}降落時間{i}",
                    f"{d}飛機公司及型號{i}",
                    f"{d}飛行時間{i}",
                    f"{d}行李{i}",
                ])
        column_order.extend([
            "GDS Type",
            "票型",
            "基礎票價",
            "折讓百分比",
            "票價加價成數",
            "稅金",
            "稅金加價成數",
            "固定金額",
            "總售價",
            "公式類型",
            "折扣",
            "建立時間",
        ])

        if extracted_rows:
            final_df = pd.DataFrame(extracted_rows)
            final_df = final_df.reindex(columns=column_order)
            final_df = final_df.drop_duplicates()
        else:
            final_df = pd.DataFrame(columns=column_order)

        return final_df


class ScraperTaskController:
    """
    爬蟲任務控制器，負責協調整個爬蟲流程。
    
    Examples:
        >>> controller = ScraperTaskController()
        >>> df = controller.run_scraping_task("TPE", "TYO", "2025/10/15", "2025/10/20")
    
    Raises:
        ValueError: 當參數無效時
    """
    
    def __init__(self):
        """
        初始化爬蟲任務控制器。
        
        Examples:
            >>> controller = ScraperTaskController()
        
        Raises:
            無特定錯誤
        """
        self.driver = None
    
    def run_scraping_task(
        self,
        origin_code: str,
        destination_code: str,
        start_date: str,
        return_date: str,
        username: str = '0920262685',
        password: str = 'B8722000',
        captcha_model_path: str = 'captcha_model_1.keras'
    ) -> pd.DataFrame:
        """
        執行爬蟲任務。
        
        Args:
            origin_code (str): 出發地代碼 (例如 'TPE')。
            destination_code (str): 目的地代碼 (例如 'TYO')。
            start_date (str): 出發日期，格式為 'YYYY/MM/DD'。
            return_date (str): 返回日期，格式為 'YYYY/MM/DD'。
            username (str): 登入帳號，預設為 '0920262685'。
            password (str): 登入密碼，預設為 'B8722000'。
            captcha_model_path (str): 驗證碼模型路徑，預設為 'captcha_model_1.keras'。
        
        Returns:
            pd.DataFrame: 收集到的航班資料 DataFrame。
        
        Examples:
            >>> controller = ScraperTaskController()
            >>> df = controller.run_scraping_task("TPE", "TYO", "2025/10/15", "2025/10/20")
            >>> isinstance(df, pd.DataFrame)
            True
        
        Raises:
            ValueError: 當任何參數為空時
            RuntimeError: 當爬蟲任務失敗時
        """
        if not origin_code:
            raise ValueError("origin_code 不可為空")
        if not destination_code:
            raise ValueError("destination_code 不可為空")
        if not start_date:
            raise ValueError("start_date 不可為空")
        if not return_date:
            raise ValueError("return_date 不可為空")
        
        try:
            # 初始化 WebDriver
            factory = WebDriverFactory()
            self.driver = factory.create_driver()
            
            navigator = WebNavigator(self.driver)
            
            # 登入網站
            navigator.login_with_retry(username, password, captcha_model_path)
            
            # 導航至機票查詢頁面
            navigator.navigate_to_flight_page(
                origin_code=origin_code,
                destination_code=destination_code,
                start_date=start_date,
                return_date=return_date
            )
            
            # 等待頁面加載並滾動至底部
            WebDriverWait(self.driver, 45).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'tab01'))
            )
            navigator.scroll_to_bottom()
            
            # 展開所有航班選項
            expander = FlightOptionExpander(self.driver)
            expander.expand_all_options()
            
            # 等待展開操作完成
            time.sleep(2)
            
            # 收集資料
            collector = FlightDataCollector(self.driver)
            extracted_rows = collector.collect_all_flight_data(start_date, return_date)
            
            # 建構 DataFrame
            builder = DataFrameBuilder()
            final_df = builder.build_dataframe(extracted_rows)
            
            return final_df
            
        except Exception as e:
            raise RuntimeError(f"爬蟲任務失敗: {e}")
        finally:
            if self.driver:
                self.driver.quit()
