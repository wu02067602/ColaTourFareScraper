# 標準庫
import re
import time
from datetime import datetime, timedelta

# 第三方庫
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class DateTimeParser:
    """
    日期時間解析器，負責解析各種日期時間格式。
    
    Examples:
        >>> parser = DateTimeParser()
        >>> dt = parser.parse_date_time("10/15(三) 14:30", 2025)
        >>> dt.year
        2025
    
    Raises:
        ValueError: 當日期時間格式無效時
    """
    
    @staticmethod
    def parse_date_time(text: str, year: int) -> datetime:
        """
        將如 "10/15(三) 14:30" 或 "10/15 14:30" 的字串轉換為 datetime；年份由參數補齊。

        Args:
            text (str): 原始日期時間字串，格式 "MM/DD(週) HH:MM" 或 "MM/DD HH:MM"。
            year (int): 年份 (西元)，用於組合完整日期時間。

        Returns:
            datetime: 解析成功的日期時間物件。
        
        Examples:
            >>> parser = DateTimeParser()
            >>> dt = parser.parse_date_time("10/15(三) 14:30", 2025)
            >>> dt.month
            10
        
        Raises:
            ValueError: 當日期字串為空或格式無效時
        """
        if text is None:
            raise ValueError("日期字串不可為空")
        # 去除括號中的星期
        cleaned = re.sub(r"\([^)]*\)", "", text).strip()
        # 期望格式: MM/DD HH:MM
        dt = datetime.strptime(f"{year}/" + cleaned, "%Y/%m/%d %H:%M")
        return dt

    @staticmethod
    def parse_duration_to_timedelta(text: str) -> timedelta:
        """
        將中文時長字串 (如 "03小時25分鐘"、"2小時15分鐘") 解析為 timedelta。

        Args:
            text (str): 表示時長的字串；若為空或無法解析則視為 0。

        Returns:
            timedelta: 由時與分組成的時間段；無法解析時為 0。
        
        Examples:
            >>> parser = DateTimeParser()
            >>> td = parser.parse_duration_to_timedelta("03小時25分鐘")
            >>> td.total_seconds()
            12300.0
        
        Raises:
            ValueError: 當時長字串格式嚴重錯誤時（注意：空字串不會拋出錯誤，而是返回 0）
        """
        if not text:
            return timedelta(0)
        hours = 0
        minutes = 0
        m = re.search(r"(\d+)\s*小時", text)
        if m:
            hours = int(m.group(1))
        m = re.search(r"(\d+)\s*分", text)
        if m:
            minutes = int(m.group(1))
        return timedelta(hours=hours, minutes=minutes)

    @staticmethod
    def format_datetime_to_string(dt) -> str:
        """
        將 datetime 轉成字串 "YYYY-MM-DD HH:MM"，無效則回傳空字串。
        
        Args:
            dt: datetime 物件。
        
        Returns:
            str: 格式化後的日期時間字串，格式 "YYYY-MM-DD HH:MM"。
        
        Examples:
            >>> parser = DateTimeParser()
            >>> dt = datetime(2025, 10, 15, 14, 30)
            >>> parser.format_datetime_to_string(dt)
            '2025-10-15 14:30'
        
        Raises:
            ValueError: 當 dt 為 None 或無效時（注意：函數內部會捕捉並返回空字串）
        """
        try:
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return ""

    @staticmethod
    def format_timedelta_to_hhmm(td) -> str:
        """
        將 timedelta 轉成 "HH:MM"，若為 0 或無效則回傳空字串。
        
        Args:
            td: timedelta 物件。
        
        Returns:
            str: 格式化後的時長字串，格式 "HH:MM"。
        
        Examples:
            >>> parser = DateTimeParser()
            >>> td = timedelta(hours=3, minutes=25)
            >>> parser.format_timedelta_to_hhmm(td)
            '03:25'
        
        Raises:
            ValueError: 當 td 為 None 或無效時（注意：函數內部會捕捉並返回空字串）
        """
        try:
            total_minutes = int(td.total_seconds() // 60)
            if total_minutes <= 0:
                return ""
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"{hours:02d}:{minutes:02d}"
        except Exception:
            return ""


class FlightDataParser:
    """
    航班資料解析器，負責解析機場代碼、航班號、艙等等資訊。
    
    Examples:
        >>> parser = FlightDataParser()
        >>> iata = parser.extract_iata("SFO 舊金山 舊金山國際機場")
        >>> iata
        'SFO'
    
    Raises:
        ValueError: 當資料格式無效時
    """
    
    @staticmethod
    def extract_iata(text: str) -> str:
        """
        自機場描述文字中擷取 IATA 三字碼。

        Args:
            text (str): 例如 "SFO 舊金山 舊金山國際機場" 的字串。

        Returns:
            str: 擷取到的三字碼 (例如 "SFO")；若無則回傳空字串。
        
        Examples:
            >>> parser = FlightDataParser()
            >>> parser.extract_iata("SFO 舊金山 舊金山國際機場")
            'SFO'
            >>> parser.extract_iata("無效文字")
            ''
        
        Raises:
            ValueError: 當 text 為 None 時（注意：空字串不會拋出錯誤）
        """
        if not text:
            return ""
        m = re.match(r"\s*([A-Z]{3})\b", text.strip())
        return m.group(1) if m else ""

    @staticmethod
    def parse_flight_and_cabin(text: str) -> tuple:
        """
        解析航班與艙等資訊字串，取得航班號與「艙等+訂位代碼」。

        Args:
            text (str): 例如 "UA852 經濟艙 K" 的字串。

        Returns:
            tuple[str, str]: (航班號, 艙等與艙等編碼)。若無法解析：回傳 (原字串或空, 空)。
        
        Examples:
            >>> parser = FlightDataParser()
            >>> parser.parse_flight_and_cabin("UA852 經濟艙 K")
            ('UA852', '經濟艙K')
        
        Raises:
            ValueError: 當 text 為 None 時（注意：空字串不會拋出錯誤）
        """
        if not text:
            return "", ""
        # 放寬格式：允許航班號中間有空白、艙等與訂位碼可能連在一起
        m = re.match(r"\s*([A-Z0-9]{2,3})\s?(\d+)\s+(\S*?)\s*([A-Z])\s*$", text)
        if m:
            flight_no = m.group(1) + m.group(2)
            cabin = m.group(3)
            booking = m.group(4)
            return flight_no, f"{cabin}{booking}"
        # 備援：先抓航班號，再嘗試艙等/訂位碼
        m2 = re.search(r"([A-Z0-9]{2,3})\s?(\d+)", text)
        if m2:
            flight_no = m2.group(1) + m2.group(2)
            m3 = re.search(r"([\u4e00-\u9fa5A-Za-z]+)\s*([A-Z])\s*$", text)
            if m3:
                return flight_no, f"{m3.group(1)}{m3.group(2)}"
            return flight_no, ""
        # 最後備援：以空白切割
        parts = text.split()
        if len(parts) >= 3:
            return parts[0], f"{parts[1]}{parts[2]}"
        return text.strip(), ""


class FlightDataExtractor:
    """
    航班資料擷取器，負責從網頁元素中擷取並清洗航班資料。
    
    Examples:
        >>> extractor = FlightDataExtractor()
        >>> data = extractor.extract_and_clean_flight_data(card, "2025/10/15", "2025/10/20")
    
    Raises:
        ValueError: 當資料擷取失敗時
    """
    
    def _validate_extract_parameters(
        self,
        card: webdriver.remote.webelement.WebElement,
        start_date: str,
        return_date: str
    ) -> tuple[int, int]:
        """
        驗證 extract_and_clean_flight_data 的輸入參數，並解析年份。
        
        Args:
            card: 航班卡片根元素
            start_date: 去程日期，格式 'YYYY/MM/DD'
            return_date: 回程日期，格式 'YYYY/MM/DD'
        
        Returns:
            tuple[int, int]: (去程年份, 回程年份)
        
        Examples:
            >>> extractor = FlightDataExtractor()
            >>> year_out, year_in = extractor._validate_extract_parameters(card, "2025/10/15", "2025/10/20")
            >>> year_out
            2025
        
        Raises:
            ValueError: 當 card 為 None 時
            ValueError: 當日期格式無效時
            IndexError: 當日期字串無法正確分割時
        """
        if card is None:
            raise ValueError("card 不可為 None")
        
        if not start_date or not isinstance(start_date, str):
            raise ValueError("start_date 必須為非空字串")
        
        if not return_date or not isinstance(return_date, str):
            raise ValueError("return_date 必須為非空字串")
        
        try:
            year_outbound = int(start_date.split("/")[0])
        except (IndexError, ValueError) as e:
            raise ValueError(f"start_date 格式無效，期望 'YYYY/MM/DD'，實際為 '{start_date}'") from e
        
        try:
            year_inbound = int(return_date.split("/")[0])
        except (IndexError, ValueError) as e:
            raise ValueError(f"return_date 格式無效，期望 'YYYY/MM/DD'，實際為 '{return_date}'") from e
        
        return year_outbound, year_inbound
    
    def _initialize_flight_record(self) -> dict:
        """
        初始化航班記錄的所有欄位。
        
        Returns:
            dict: 包含所有航班欄位的空字典，每個方向（去程/回程）各有3個航段的欄位
        
        Examples:
            >>> extractor = FlightDataExtractor()
            >>> record = extractor._initialize_flight_record()
            >>> record["去程航班編號1"]
            ''
            >>> len([k for k in record.keys() if k.startswith("去程")])
            24
        
        Raises:
            無特定錯誤
        """
        record = {}
        for direction in ["去程", "回程"]:
            for i in range(1, 4):
                record[f"{direction}航班編號{i}"] = ""
                record[f"{direction}艙等與艙等編碼{i}"] = ""
                record[f"{direction}起飛機場{i}"] = ""
                record[f"{direction}降落機場{i}"] = ""
                record[f"{direction}起飛時間{i}"] = ""
                record[f"{direction}降落時間{i}"] = ""
                record[f"{direction}飛機公司及型號{i}"] = ""
                record[f"{direction}飛行時間{i}"] = ""
        return record
    
    def _determine_flight_direction(
        self,
        outer_table: webdriver.remote.webelement.WebElement,
        table_index: int
    ) -> str:
        """
        判斷航班表格是去程還是回程。
        
        優先順序：
        1. 標題中包含「回程」字樣
        2. class 屬性中包含 "return_line"
        3. 根據表格索引判斷（索引 1 為回程，索引 0 為去程）
        
        Args:
            outer_table: 航班表格元素
            table_index: 表格在列表中的索引（0 或 1）
        
        Returns:
            str: "去程" 或 "回程"
        
        Examples:
            >>> extractor = FlightDataExtractor()
            >>> direction = extractor._determine_flight_direction(table, 0)
            >>> direction in ["去程", "回程"]
            True
        
        Raises:
            ValueError: 當 outer_table 為 None 時
        """
        if outer_table is None:
            raise ValueError("outer_table 不可為 None")
        
        outer_class = outer_table.get_attribute("class") or ""
        
        # 優先檢查標題是否包含「回程」
        has_return_title = len(outer_table.find_elements(
            By.XPATH,
            ".//p[contains(@class,'detail_title') and contains(.,'回程')] | "
            ".//p[contains(@class,'desktop_detail_title') and contains(.,'回程')]"
        )) > 0
        
        if has_return_title or "return_line" in outer_class:
            return "回程"
        
        # 後備方案：根據索引判斷
        return "回程" if table_index == 1 else "去程"
    
    def _find_segment_rows(
        self,
        outer_table: webdriver.remote.webelement.WebElement
    ) -> list:
        """
        從航班表格中找出所有有效的航段資料列（排除轉機灰條）。
        
        使用兩階段策略：
        1. 首先嘗試精確的 XPath 篩選
        2. 如果沒有結果，使用較寬鬆的後備 XPath
        
        Args:
            outer_table: 航班外層表格元素
        
        Returns:
            list: 包含航段資料的 WebElement 列表
        
        Examples:
            >>> extractor = FlightDataExtractor()
            >>> rows = extractor._find_segment_rows(table)
            >>> len(rows) >= 0
            True
        
        Raises:
            ValueError: 當 outer_table 為 None 時
        """
        if outer_table is None:
            raise ValueError("outer_table 不可為 None")
        
        # 嘗試精確的 XPath（排除灰條和轉機停留行）
        rows = outer_table.find_elements(
            By.XPATH,
            ".//tr[not(contains(concat(' ', normalize-space(@class), ' '), ' flightDetails_gray ')) and "
            "not(contains(concat(' ', normalize-space(@class), ' '), ' middleStay ')) and "
            "td[contains(concat(' ', normalize-space(@class), ' '), ' cell_2 ') and "
            "contains(concat(' ', normalize-space(@class), ' '), ' b-box ')]]"
        )
        
        # 後備方案：使用較寬鬆的篩選條件
        if not rows:
            rows = outer_table.find_elements(
                By.XPATH,
                ".//tr[not(contains(@class,'flightDetails_gray')) and "
                "(td[contains(@class,'cell_2')] or td[contains(@class,'cell_3')] or td[contains(@class,'cell_5')])]"
            )
        
        return rows
    
    def _extract_flight_and_cabin_info(
        self,
        row: webdriver.remote.webelement.WebElement
    ) -> tuple[str, str]:
        """
        從航段行的 cell_2 提取航班編號和艙等資訊。
        
        包含重試機制，最多嘗試 3 次，每次間隔 0.2 秒。
        
        Args:
            row: 航段資料行元素
        
        Returns:
            tuple[str, str]: (航班編號, 艙等與艙等編碼)
        
        Examples:
            >>> extractor = FlightDataExtractor()
            >>> flight_no, cabin = extractor._extract_flight_and_cabin_info(row)
            >>> isinstance(flight_no, str) and isinstance(cabin, str)
            True
        
        Raises:
            ValueError: 當 row 為 None 時
            NoSuchElementException: 當找不到 cell_2 元素時
        """
        if row is None:
            raise ValueError("row 不可為 None")
        
        cell2 = row.find_element(By.CSS_SELECTOR, "td.cell_2")
        flight_and_cabin_text = ""
        
        # 重試機制：嘗試三次提取航班資訊
        for _ in range(3):
            p_texts = [p.text.strip() for p in cell2.find_elements(By.TAG_NAME, "p") if p.text.strip()]
            candidates = [t for t in p_texts if re.search(r"[A-Z0-9]{2,3}\s?\d+", t)]
            if candidates:
                flight_and_cabin_text = candidates[-1]
                break
            time.sleep(0.2)
        
        return FlightDataParser.parse_flight_and_cabin(flight_and_cabin_text)
    
    def _extract_airport_and_time(
        self,
        row: webdriver.remote.webelement.WebElement,
        cell_class: str,
        assumed_year: int
    ) -> tuple[str, datetime | None]:
        """
        從航段行的指定 cell 提取機場代碼和時間。
        
        通用函數，可用於提取出發資訊（cell_3）或抵達資訊（cell_5）。
        
        Args:
            row: 航段資料行元素
            cell_class: CSS class 名稱（如 "cell_3" 或 "cell_5"）
            assumed_year: 假定的年份用於日期解析
        
        Returns:
            tuple[str, datetime | None]: (機場 IATA 代碼, 日期時間物件)
        
        Examples:
            >>> extractor = FlightDataExtractor()
            >>> airport, dt = extractor._extract_airport_and_time(row, "cell_3", 2025)
            >>> isinstance(airport, str)
            True
        
        Raises:
            ValueError: 當 row 為 None 或 cell_class 為空時
            NoSuchElementException: 當找不到指定 cell 時
        """
        if row is None:
            raise ValueError("row 不可為 None")
        if not cell_class:
            raise ValueError("cell_class 不可為空")
        
        airport = ""
        dt = None
        
        cell = row.find_element(By.CSS_SELECTOR, f"td.{cell_class}")
        cell_ps = [p.text.strip() for p in cell.find_elements(By.TAG_NAME, "p")]
        
        if cell_ps:
            # 從第一行提取機場代碼
            airport = FlightDataParser.extract_iata(cell_ps[0]) or airport
            
            # 尋找包含日期時間的行
            time_line = None
            for t in cell_ps:
                if re.search(r"\d{1,2}/\d{1,2}.*\d{1,2}:\d{2}", t):
                    time_line = t
                    break
            
            if time_line:
                dt = DateTimeParser.parse_date_time(time_line, assumed_year)
        
        return airport, dt
    
    def _extract_equipment_and_duration(
        self,
        row: webdriver.remote.webelement.WebElement
    ) -> tuple[str, timedelta]:
        """
        從航段行的 cell_6 提取機型和飛行時間。
        
        策略：
        1. 尋找包含「小時」或「分」的文字作為飛行時間
        2. 其他文字視為機型資訊
        3. 如果沒有飛行時間，第一行文字視為機型
        
        Args:
            row: 航段資料行元素
        
        Returns:
            tuple[str, timedelta]: (機型文字, 飛行時間)
        
        Examples:
            >>> extractor = FlightDataExtractor()
            >>> equipment, duration = extractor._extract_equipment_and_duration(row)
            >>> isinstance(equipment, str) and isinstance(duration, timedelta)
            True
        
        Raises:
            ValueError: 當 row 為 None 時
            NoSuchElementException: 當找不到 cell_6 元素時
        """
        if row is None:
            raise ValueError("row 不可為 None")
        
        equipment_text = ""
        duration_td = timedelta(0)
        
        cell6 = row.find_element(By.CSS_SELECTOR, "td.cell_6")
        cell6_ps = [p.text.strip() for p in cell6.find_elements(By.TAG_NAME, "p") if p.text.strip()]
        
        if cell6_ps:
            # 尋找飛行時間（包含「小時」或「分」的文字）
            dur_line = next((t for t in cell6_ps if re.search(r"\d+\s*小時|\d+\s*分", t)), "")
            
            if dur_line:
                duration_td = DateTimeParser.parse_duration_to_timedelta(dur_line)
                # 機型是非飛行時間的那一行
                equipment_text = next((t for t in cell6_ps if t != dur_line), equipment_text)
            else:
                # 沒有飛行時間，第一行當作機型
                equipment_text = cell6_ps[0]
        
        return equipment_text, duration_td
    
    def _extract_segment_data(
        self,
        row: webdriver.remote.webelement.WebElement,
        assumed_year: int
    ) -> dict:
        """
        從單個航段行提取完整的航段資訊。
        
        整合所有提取函數，從航段行中提取：
        - 航班編號和艙等（cell_2）
        - 出發機場和時間（cell_3）
        - 抵達機場和時間（cell_5）
        - 機型和飛行時間（cell_6）
        
        Args:
            row: 航段資料行元素
            assumed_year: 假定的年份用於日期解析
        
        Returns:
            dict: 包含航段所有資訊的字典
                - flight_no: 航班編號
                - cabin_and_code: 艙等與艙等編碼
                - dep_airport: 出發機場
                - arr_airport: 抵達機場
                - dep_time: 出發時間（字串格式）
                - arr_time: 抵達時間（字串格式）
                - equipment: 機型
                - duration: 飛行時間（字串格式）
        
        Examples:
            >>> extractor = FlightDataExtractor()
            >>> segment = extractor._extract_segment_data(row, 2025)
            >>> "flight_no" in segment and "dep_airport" in segment
            True
        
        Raises:
            ValueError: 當 row 為 None 時
            NoSuchElementException: 當找不到必要的 cell 元素時
        """
        if row is None:
            raise ValueError("row 不可為 None")
        
        # 提取航班和艙等
        flight_no, cabin_and_code = self._extract_flight_and_cabin_info(row)
        
        # 提取出發資訊
        dep_airport, dep_dt = self._extract_airport_and_time(row, "cell_3", assumed_year)
        
        # 提取抵達資訊
        arr_airport, arr_dt = self._extract_airport_and_time(row, "cell_5", assumed_year)
        
        # 提取機型和飛行時間
        equipment_text, duration_td = self._extract_equipment_and_duration(row)
        
        # 格式化日期時間
        dep_str = DateTimeParser.format_datetime_to_string(dep_dt)
        arr_str = DateTimeParser.format_datetime_to_string(arr_dt)
        dur_str = DateTimeParser.format_timedelta_to_hhmm(duration_td)
        
        return {
            "flight_no": flight_no,
            "cabin_and_code": cabin_and_code,
            "dep_airport": dep_airport,
            "arr_airport": arr_airport,
            "dep_time": dep_str,
            "arr_time": arr_str,
            "equipment": equipment_text,
            "duration": dur_str
        }
    
    def _write_segment_to_record(
        self,
        record: dict,
        segment_data: dict,
        direction: str,
        segment_index: int
    ) -> None:
        """
        將航段資料寫入記錄字典。
        
        根據方向（去程/回程）和航段索引（1-3），將航段資料寫入對應的欄位。
        
        Args:
            record: 要寫入的記錄字典
            segment_data: 航段資料字典（由 _extract_segment_data 產生）
            direction: 航班方向（"去程" 或 "回程"）
            segment_index: 航段索引（1、2 或 3）
        
        Returns:
            None（直接修改 record 字典）
        
        Examples:
            >>> extractor = FlightDataExtractor()
            >>> record = extractor._initialize_flight_record()
            >>> segment_data = {"flight_no": "UA852", "cabin_and_code": "經濟艙K", ...}
            >>> extractor._write_segment_to_record(record, segment_data, "去程", 1)
            >>> record["去程航班編號1"]
            'UA852'
        
        Raises:
            ValueError: 當 record 為 None 或 segment_data 為 None 時
            ValueError: 當 direction 不是 "去程" 或 "回程" 時
            ValueError: 當 segment_index 不在 1-3 範圍內時
        """
        if record is None:
            raise ValueError("record 不可為 None")
        if segment_data is None:
            raise ValueError("segment_data 不可為 None")
        if direction not in ["去程", "回程"]:
            raise ValueError(f"direction 必須為 '去程' 或 '回程'，實際為 '{direction}'")
        if not 1 <= segment_index <= 3:
            raise ValueError(f"segment_index 必須在 1-3 範圍內，實際為 {segment_index}")
        
        record[f"{direction}航班編號{segment_index}"] = segment_data["flight_no"]
        record[f"{direction}艙等與艙等編碼{segment_index}"] = segment_data["cabin_and_code"]
        record[f"{direction}起飛機場{segment_index}"] = segment_data["dep_airport"]
        record[f"{direction}降落機場{segment_index}"] = segment_data["arr_airport"]
        record[f"{direction}起飛時間{segment_index}"] = segment_data["dep_time"]
        record[f"{direction}降落時間{segment_index}"] = segment_data["arr_time"]
        record[f"{direction}飛機公司及型號{segment_index}"] = segment_data["equipment"]
        record[f"{direction}飛行時間{segment_index}"] = segment_data["duration"]
    
    def extract_and_clean_flight_data(
        self,
        card: webdriver.remote.webelement.WebElement,
        start_date: str,
        return_date: str
    ) -> list:
        """
        自單張航班卡片的「航班明細」區塊抽取並清洗資料。
        
        此函數作為流程控制器，協調各個輔助函數完成資料提取任務。

        Args:
            card (webdriver.remote.webelement.WebElement): 航班卡片根元素。
            start_date (str): 去程日期，格式 'YYYY/MM/DD'，僅用於推斷年份。
            return_date (str): 回程日期，格式 'YYYY/MM/DD'，僅用於推斷年份。

        Returns:
            list[dict]: 只包含一筆紀錄的列表。
        
        Examples:
            >>> extractor = FlightDataExtractor()
            >>> data = extractor.extract_and_clean_flight_data(card, "2025/10/15", "2025/10/20")
            >>> len(data)
            1
        
        Raises:
            ValueError: 當 card 為 None 或日期格式無效時
        """
        # 步驟 1: 驗證參數並解析年份
        year_outbound, year_inbound = self._validate_extract_parameters(
            card, start_date, return_date
        )
        
        # 步驟 2: 初始化記錄結構
        record = self._initialize_flight_record()
        segment_index = {"去程": 1, "回程": 1}
        
        # 步驟 3: 取得去程/回程外層表格
        outer_tables = card.find_elements(By.CSS_SELECTOR, "table.flightDetails_table")
        
        # 步驟 4: 遍歷每個表格（去程/回程）
        for idx, outer_table in enumerate(outer_tables):
            # 步驟 4.1: 判斷航班方向
            direction = self._determine_flight_direction(outer_table, idx)
            assumed_year = year_inbound if direction == "回程" else year_outbound
            
            # 步驟 4.2: 抓取航段資料列
            rows = self._find_segment_rows(outer_table)
            
            # 步驟 4.3: 處理每個航段
            for row in rows:
                # 限制每個方向最多 3 個航段
                if segment_index[direction] > 3:
                    continue
                
                # 步驟 4.3.1: 提取航段資料
                segment_data = self._extract_segment_data(row, assumed_year)
                
                # 步驟 4.3.2: 將航段資料寫入記錄
                self._write_segment_to_record(
                    record,
                    segment_data,
                    direction,
                    segment_index[direction]
                )
                
                # 步驟 4.3.3: 遞增航段索引
                segment_index[direction] += 1
        
        # 步驟 5: 返回結果
        return [record]


class PriceDataExtractor:
    """
    票價資料擷取器，負責從網頁元素中擷取並清洗票價資料。
    
    Examples:
        >>> extractor = PriceDataExtractor()
        >>> data = extractor.extract_and_clean_price_data(card)
    
    Raises:
        ValueError: 當資料擷取失敗時
    """
    
    @staticmethod
    def parse_int(text: str) -> int:
        """
        解析整數字串，去除千分位逗號。
        
        Args:
            text (str): 整數字串。
        
        Returns:
            int: 解析後的整數。
        
        Examples:
            >>> PriceDataExtractor.parse_int("1,234")
            1234
        
        Raises:
            ValueError: 當 text 無法解析為整數時（注意：函數內部會捕捉並返回 0）
        """
        if text is None:
            return 0
        cleaned = re.sub(r"[ ,，]", "", text)
        try:
            return int(cleaned)
        except Exception:
            try:
                return int(float(cleaned))
            except Exception:
                return 0

    @staticmethod
    def parse_float(text: str) -> float:
        """
        解析浮點數字串，去除千分位逗號。
        
        Args:
            text (str): 浮點數字串。
        
        Returns:
            float: 解析後的浮點數。
        
        Examples:
            >>> PriceDataExtractor.parse_float("1,234.56")
            1234.56
        
        Raises:
            ValueError: 當 text 無法解析為浮點數時（注意：函數內部會捕捉並返回 0.0）
        """
        if text is None:
            return 0.0
        cleaned = text.replace("，", ",")
        cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except Exception:
            return 0.0
    
    def extract_and_clean_price_data(self, card: webdriver.remote.webelement.WebElement) -> list:
        """
        自單張航班卡片的「票價」區塊抽取並清洗資料。
        
        Args:
            card (webdriver.remote.webelement.WebElement): 航班卡片根元素。
        
        Returns:
            list[dict]: 只包含一筆紀錄的列表。
        
        Examples:
            >>> extractor = PriceDataExtractor()
            >>> data = extractor.extract_and_clean_price_data(card)
            >>> len(data)
            1
        
        Raises:
            ValueError: 當 card 為 None 時
        """
        if card is None:
            raise ValueError("card 不可為 None")
        
        driver = getattr(card, "parent", None) or getattr(card, "_parent", None)
        results = []

        record = {
            "GDS Type": "",
            "稅金": 0,
            "總售價": 0,
            "票型": "",
            "基礎票價": 0,
            "折讓百分比": 0,
            "折扣": 0,
            "票價加價成數": 0.0,
            "稅金加價成數": 0.0,
            "固定金額": 0,
            "公式類型": -1,
        }

        if driver is None:
            results.append(record)
            return results

        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "DBGModal"))
            )
        except Exception:
            results.append(record)
            return results

        try:
            modal = driver.find_element(By.ID, "DBGModal")
        except Exception:
            results.append(record)
            return results

        modal_text = modal.text or ""

        # 解析 GDS Type
        m = re.search(r"GDS\s*Type[:：]\s*([^\s\r\n]+)", modal_text)
        if m:
            record["GDS Type"] = m.group(1).strip()

        # 從「大人公式」解析各欄位
        formula_line = ""
        fm = re.search(r"大人公式[:：]\s*(.*)", modal_text)
        if fm:
            formula_line = fm.group(1).strip()

        if formula_line:
            type1_pattern = re.compile(
                r"^\(\s*(票面|淨價)\s*[\d,，]+\s*\*\s*\[\s*KP\s*\d+\s*\]\s*-\s*折扣\s*[\d,，]+\s*\)\s*\*\s*[0-9]+(?:\.[0-9]+)?\s*\+\s*TAX\s*[\d,，]+\s*\*\s*[0-9]+(?:\.[0-9]+)?\s*\+\s*固定金額\s*[-]?[\d,，]+\s*=\s*[\d,，]+\s*$",
                re.IGNORECASE
            )
            type2_pattern = re.compile(
                r"^\(\s*\(\s*(票面|淨價)\s*[\d,，]+\s*-\s*折扣\s*[\d,，]+\s*\)\s*\*\s*\[\s*KP\s*\d+\s*\]\s*\)\s*\*\s*[0-9]+(?:\.[0-9]+)?\s*\+\s*TAX\s*[\d,，]+\s*\*\s*[0-9]+(?:\.[0-9]+)?\s*\+\s*固定金額\s*[-]?[\d,，]+\s*=\s*[\d,，]+\s*$",
                re.IGNORECASE
            )

            if type1_pattern.search(formula_line):
                record["公式類型"] = 1
            elif type2_pattern.search(formula_line):
                record["公式類型"] = 2
            else:
                record["公式類型"] = -1
                try:
                    breakpoint()
                except Exception:
                    pass

            # 票型 + 基礎票價
            m_type_price = re.search(r"\(\s*([\u4e00-\u9fa5A-Za-z]+)\s*([\d,，]+)", formula_line)
            if not m_type_price:
                m_type_price = re.search(r"\(\s*\(\s*([\u4e00-\u9fa5A-Za-z]+)\s*([\d,，]+)", formula_line)
            if m_type_price:
                record["票型"] = m_type_price.group(1).strip()
                record["基礎票價"] = self.parse_int(m_type_price.group(2))

            # 折讓百分比
            m_kp = re.search(r"\[\s*KP\s*(\d+)\s*\]", formula_line, re.IGNORECASE)
            if m_kp:
                record["折讓百分比"] = int(m_kp.group(1))

            # 折扣
            m_disc = re.search(r"折扣\s*([\d,，]+)", formula_line)
            if m_disc:
                record["折扣"] = self.parse_int(m_disc.group(1))

            # 票價加價成數
            m_price_factor = re.search(r"\)\s*\*\s*([0-9]+(?:\.[0-9]+)?)", formula_line)
            if m_price_factor:
                record["票價加價成數"] = self.parse_float(m_price_factor.group(1))

            # 稅金與稅金加價成數
            m_tax = re.search(r"TAX\s*([\d,，]+)\s*\*\s*([0-9]+(?:\.[0-9]+)?)", formula_line, re.IGNORECASE)
            if m_tax:
                record["稅金"] = self.parse_int(m_tax.group(1))
                record["稅金加價成數"] = self.parse_float(m_tax.group(2))

            # 固定金額
            m_fixed = re.search(r"固定金額\s*([-]?[\d,，]+)", formula_line)
            if m_fixed:
                record["固定金額"] = self.parse_int(m_fixed.group(1))

            # 總售價
            m_total = re.search(r"=\s*([\d,，]+)\s*$", formula_line)
            if m_total:
                record["總售價"] = self.parse_int(m_total.group(1))

        # 後備：補齊稅金/總售價
        if not record["稅金"]:
            m_tax2 = re.search(r"稅金\s*([\d,，]+)", modal_text)
            if m_tax2:
                record["稅金"] = self.parse_int(m_tax2.group(1))

        if not record["總售價"]:
            m_total2 = re.search(r"總售價[:：]\s*([\d,，]+)", modal_text)
            if m_total2:
                record["總售價"] = self.parse_int(m_total2.group(1))

        results.append(record)
        return results


class BaggageDataExtractor:
    """
    行李資料擷取器，負責從網頁元素中擷取並清洗行李資料。
    
    Examples:
        >>> extractor = BaggageDataExtractor()
        >>> data = extractor.extract_and_clean_baggage_data(card, driver, flight_details)
    
    Raises:
        ValueError: 當資料擷取失敗時
    """
    
    def extract_and_clean_baggage_data(
        self,
        card: webdriver.remote.webelement.WebElement,
        driver: webdriver.Chrome,
        current_flight_details: dict
    ) -> dict:
        """
        從航班卡片中提取並清理行李資訊。

        Args:
            card (webdriver.remote.webelement.WebElement): 當前的航班卡片元素。
            driver (webdriver.Chrome): 用於操作的 WebDriver。
            current_flight_details (dict): 當前航班的詳細資訊，用於判斷行李去回程。

        Returns:
            dict: 包含結構化行李數據的字典。
        
        Examples:
            >>> extractor = BaggageDataExtractor()
            >>> data = extractor.extract_and_clean_baggage_data(card, driver, flight_details)
            >>> '去程行李1' in data
            True
        
        Raises:
            ValueError: 當 card 或 driver 為 None 時
        """
        if card is None:
            raise ValueError("card 不可為 None")
        if driver is None:
            raise ValueError("driver 不可為 None")
        
        card_baggage_info = {}
        outbound_baggage_counter = 0
        return_baggage_counter = 0

        baggage_rows = card.find_elements(By.CSS_SELECTOR, ".bagInformation_tab table.bagInformation tbody tr.bagInformation_item")

        for row_idx, row in enumerate(baggage_rows):
            segment_element = row.find_element(By.CSS_SELECTOR, "td.segment")
            segment_text = segment_element.text.strip()

            flight_num_element = row.find_element(By.CSS_SELECTOR, "td.flight_num")
            flight_num_text = flight_num_element.text.strip()

            adult_baggage_element = row.find_element(By.CSS_SELECTOR, "td[data-title='成人']")
            adult_baggage_text = adult_baggage_element.text.strip()

            match = re.search(r'(\d+)\s*(公斤|件)?', adult_baggage_text)
            if match:
                value = int(match.group(1))
                unit = match.group(2) if match.group(2) else ""
                cleaned_baggage_info = f"{value}{unit}"
            else:
                cleaned_baggage_info = None

            airport_match = re.search(r'(\w+)\s+.*?－\s*(\w+)', segment_text)
            dep_airport_code = airport_match.group(1) if airport_match else None
            arr_airport_code = airport_match.group(2) if airport_match else None

            current_journey_type = None
            for i in range(1, 4):
                out_dep_key = f'去程起飛機場{i}'
                out_arr_key = f'去程降落機場{i}'
                ret_dep_key = f'回程起飛機場{i}'
                ret_arr_key = f'回程降落機場{i}'

                if (
                    current_flight_details.get(out_dep_key) == dep_airport_code
                    and current_flight_details.get(out_arr_key) == arr_airport_code
                ):
                    current_journey_type = "去程"
                    break
                elif (
                    current_flight_details.get(ret_dep_key) == dep_airport_code
                    and current_flight_details.get(ret_arr_key) == arr_airport_code
                ):
                    current_journey_type = "回程"
                    break

            if current_journey_type == "去程":
                outbound_baggage_counter += 1
                card_baggage_info[f"去程行李{outbound_baggage_counter}"] = cleaned_baggage_info
            elif current_journey_type == "回程":
                return_baggage_counter += 1
                card_baggage_info[f"回程行李{return_baggage_counter}"] = cleaned_baggage_info
            else:
                breakpoint()
                print(f"警告：無法判斷航段類型 ({flight_num_text})")
                
        return card_baggage_info
