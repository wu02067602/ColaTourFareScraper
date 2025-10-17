import os
import time
import base64
import re
from typing import ParamSpec

import numpy as np
import pandas as pd
import platform
from datetime import datetime, timedelta
from PIL import Image
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
import sentry_sdk

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List
import requests
import json

# Sentry
# sentry_sdk.init(
#     dsn="https://8ca523e67523891165330d546b830317@o4506557212721152.ingest.us.sentry.io/4508561921605632",
#     traces_sample_rate=0.1 # 追蹤率
# )

PROJECT_ID = os.getenv('PROJECT_ID')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')

class MLModelManager:
    """
    負責管理機器學習模型的加載、預測和相關操作。
    
    此類別遵循單一職責原則，專注於機器學習模型的管理，
    與圖像處理器協作來完成驗證碼識別任務。
    
    屬性:
        model: 已加載的 Keras 模型實例。
        image_processor (ImageProcessor): 圖像處理器實例。
    
    方法:
        load_model(model_path): 從檔案載入模型。
        predict(images): 對圖像進行預測。
        decode_prediction(pred): 解碼預測結果為字串。
    
    Examples:
        >>> manager = MLModelManager('captcha_model_1.keras')
        >>> images = manager.image_processor.process_image('captcha.png', 30, 100)
        >>> result = manager.predict(images)
        'A3B9'
    
    Raises:
        FileNotFoundError: 當模型檔案不存在時
        ValueError: 當模型格式不正確時
    """
    
    def __init__(self, model_path: str):
        """
        初始化 MLModelManager 並加載模型。
        
        Args:
            model_path (str): 模型檔案的路徑。
            
        Raises:
            FileNotFoundError: 當模型檔案不存在時
            OSError: 當模型無法加載時
        """
        try:
            self.model = load_model(model_path)
            self.image_processor = ImageProcessor()
        except FileNotFoundError as e:
            raise FileNotFoundError(f"模型檔案不存在: {model_path}") from e
        except OSError as e:
            raise OSError(f"無法加載模型: {e}") from e
    
    def load_and_process_image(self, image_path: str, target_height: int, target_width: int) -> np.ndarray:
        """
        加載並處理圖像資料，轉換為模型可接受的格式。
        
        Args:
            image_path (str): 圖像檔案的路徑。
            target_height (int): 目標高度。
            target_width (int): 目標寬度。
            
        Returns:
            np.ndarray: 處理後的圖像數據，範圍在 [0, 1] 之間。
            
        Examples:
            >>> manager = MLModelManager('model.keras')
            >>> images = manager.load_and_process_image('captcha.png', 30, 100)
            
        Raises:
            FileNotFoundError: 當圖像檔案不存在時
            ValueError: 當圖像格式不正確時
        """
        try:
            cropped_images = self.image_processor.process_image(image_path, target_height, target_width)
            images = np.array(cropped_images, dtype='float32') / 255.0
            return images
        except FileNotFoundError as e:
            raise FileNotFoundError(f"圖像檔案不存在: {image_path}") from e
        except ValueError as e:
            raise ValueError(f"圖像處理失敗: {e}") from e
    
    def decode_prediction(self, pred: np.ndarray) -> str:
        """
        將模型的預測結果解碼為可讀的字元串。
        
        Args:
            pred (np.ndarray): 模型的預測結果，為每個字符的概率分布。
            
        Returns:
            str: 解碼後的字串。
            
        Examples:
            >>> manager = MLModelManager('model.keras')
            >>> result = manager.decode_prediction(predictions)
            'A3B9'
            
        Raises:
            KeyError: 當字符映射不存在時
            ValueError: 當預測結果格式不正確時
        """
        try:
            int_to_char = {i: c for c, i in ImageProcessor.CHAR_TO_INT.items()}
            return ''.join([int_to_char[np.argmax(c)] for c in pred])
        except KeyError as e:
            raise KeyError(f"字符映射錯誤: {e}") from e
        except (IndexError, ValueError) as e:
            raise ValueError(f"預測結果格式不正確: {e}") from e
    
    def predict(self, images: np.ndarray) -> str:
        """
        使用模型對圖像進行預測並解碼。
        
        Args:
            images (np.ndarray): 預處理後的圖像數據。
            
        Returns:
            str: 完整的預測字串。
            
        Examples:
            >>> manager = MLModelManager('model.keras')
            >>> images = manager.load_and_process_image('captcha.png', 30, 100)
            >>> result = manager.predict(images)
            'A3B9'
            
        Raises:
            ValueError: 當預測失敗時
        """
        try:
            predictions = [self.decode_prediction(self.model.predict(np.expand_dims(img, axis=0))) 
                          for img in images]
            return ''.join(predictions)
        except ValueError as e:
            raise ValueError(f"模型預測失敗: {e}") from e


class ImageProcessor:
    """
    處理圖像的類別，包括獲取 Base64 圖像、保存圖像到文件以及處理圖像裁剪的功能。

    屬性:
        WHITE_PIXEL_VALUE (int): 白色像素的值，預設為 255。
        CHAR_TO_INT (dict): 字元到整數的映射，用於字元處理。

    方法:
        get_base64_image(driver, element):
            從 Selenium WebDriver 元素中獲取 Base64 格式的圖像數據。

        save_base64_image(base64_data, file_path):
            將 Base64 數據保存為圖像文件。

        process_image(image_path, target_height, target_width):
            處理圖像並返回裁剪後的圖像數組。

        calculate_midpoint(range1, range2):
            計算兩個範圍的中點。
    """

    WHITE_PIXEL_VALUE = 255
    CHAR_TO_INT = {chr(i+48): i for i in range(10)}
    CHAR_TO_INT.update({chr(i+55): i for i in range(10, 36)})

    def get_base64_image(self, driver: webdriver.Chrome, element: webdriver.remote.webelement.WebElement) -> str:
        """
        從 Selenium WebDriver 元素中獲取 Base64 格式的圖像數據。

        Args:
            driver (webdriver.Chrome): Selenium WebDriver 物件。
            element (webdriver.remote.webelement.WebElement): 要獲取圖片的 WebElement。

        Returns:
            str: 圖像的 Base64 編碼數據。
        """
        script = """
        var img = arguments[0];
        var canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        var ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, img.width, img.height);
        return canvas.toDataURL('image/png').substring(22);
        """
        return driver.execute_script(script, element)

    def save_base64_image(self, base64_data: str, file_path: str) -> None:
        """
        將 Base64 數據保存為圖像文件。

        Args:
            base64_data (str): Base64 編碼的圖像數據。
            file_path (str): 保存圖像文件的路徑。

        Returns:
            None
        """
        image_data = base64.b64decode(base64_data)
        with open(file_path, "wb") as f:
            f.write(image_data)

    def process_image(self, image_path: str, target_height: int, target_width: int) -> list:
        """
        處理圖像並返回裁剪後的圖像數組。

        Args:
            image_path (str): 圖像文件的路徑。
            target_height (int): 目標圖像的高度。
            target_width (int): 目標圖像的寬度。

        Returns:
            list: 裁剪後的圖像數組，以數字數組的形式表示。
        """
        image = Image.open(image_path)
        gray_image = image.convert('L')
        image_array = np.array(gray_image)
        non_white_pixels_per_column = np.sum(image_array != self.WHITE_PIXEL_VALUE, axis=0)
        average_non_white_pixels = np.mean(non_white_pixels_per_column) - 0.25 * (np.std(non_white_pixels_per_column))
        columns_above_average = np.where(non_white_pixels_per_column > average_non_white_pixels)[0]
        
        continuous_ranges = []
        start = columns_above_average[0]
        for i in range(1, len(columns_above_average)):
            if columns_above_average[i] != columns_above_average[i-1] + 1:
                continuous_ranges.append((start, columns_above_average[i-1]))
                start = columns_above_average[i]
        continuous_ranges.append((start, columns_above_average[-1]))
        
        sorted_data = sorted(continuous_ranges, key=lambda x: abs(x[1] - x[0]), reverse=True)
        continuous_ranges = sorted(sorted_data[:4])
        
        updated_ranges = [
            (0, self.calculate_midpoint(continuous_ranges[0], continuous_ranges[1])),
            (self.calculate_midpoint(continuous_ranges[0], continuous_ranges[1]), self.calculate_midpoint(continuous_ranges[1], continuous_ranges[2])),
            (self.calculate_midpoint(continuous_ranges[1], continuous_ranges[2]), self.calculate_midpoint(continuous_ranges[2], continuous_ranges[3])),
            (self.calculate_midpoint(continuous_ranges[2], continuous_ranges[3]), image.width)
        ]
        continuous_ranges = updated_ranges
        
        rgb_image = image.convert('RGB')
        cropped_images = []
        for start, end in continuous_ranges:
            cropped_image = rgb_image.crop((start, 0, end, rgb_image.height))
            new_width = 100
            background = Image.new('RGB', (new_width, target_height), (255, 255, 255))
            paste_position = (new_width - target_width, 0)
            background.paste(cropped_image, paste_position)
            cropped_images.append(img_to_array(background))
        
        return cropped_images

    def calculate_midpoint(self, range1: tuple, range2: tuple) -> int:
        """
        計算兩個範圍的中點。

        Args:
            range1 (tuple): 第一個範圍 (start, end)。
            range2 (tuple): 第二個範圍 (start, end)。

        Returns:
            int: 中點的值。
        """
        return int((range1[1] + range2[0]) / 2)

class CaptchaSolver:
    """
    CaptchaSolver 類別負責處理驗證碼的預測與解碼。

    透過預先訓練的深度學習模型，這個類別可以加載圖像數據並進行驗證碼的解碼與預測。

    屬性:
        model: 預訓練的驗證碼識別模型。

    方法:
        load_data(data_dir, target_height, target_width):
            加載並處理圖像數據，將圖像裁剪並轉換為數組格式。

        decode_prediction(pred):
            將模型的預測結果解碼為可讀的字元串。

        predict_captcha(images):
            使用加載的模型對圖像數據進行預測，並解碼成驗證碼字串。
    """

    def __init__(self, model_path: str):
        """
        初始化 CaptchaSolver 類別並加載模型。

        Args:
            model_path (str): 預訓練模型的文件路徑。
        """
        self.model = load_model(model_path)

    def load_data(self, data_dir: str, target_height: int, target_width: int) -> np.ndarray:
        """
        加載並處理圖像數據，將圖像裁剪並轉換為數組格式。

        Args:
            data_dir (str): 圖像文件的路徑。
            target_height (int): 圖像裁剪後的目標高度。
            target_width (int): 圖像裁剪後的目標寬度。

        Returns:
            np.ndarray: 處理後的圖像數據數組，範圍在 [0, 1] 之間。
        """
        processor = ImageProcessor()
        img_path = os.path.join(data_dir)
        cropped_images = processor.process_image(img_path, target_height, target_width)
        images = np.array(cropped_images, dtype='float32') / 255.0
        return images

    def decode_prediction(self, pred: np.ndarray) -> str:
        """
        將模型的預測結果解碼為可讀的字元串。

        Args:
            pred (np.ndarray): 模型的預測結果，為每個字符的概率分布。

        Returns:
            str: 解碼後的驗證碼字串。
        """
        int_to_char = {i: c for c, i in ImageProcessor.CHAR_TO_INT.items()}
        return ''.join([int_to_char[np.argmax(c)] for c in pred])

    def predict_captcha(self, images: np.ndarray) -> str:
        """
        使用加載的模型對圖像數據進行預測，並解碼成驗證碼字串。

        Args:
            images (np.ndarray): 預處理後的圖像數據數組。

        Returns:
            str: 解碼後的驗證碼字串。
        """
        predictions = [self.decode_prediction(self.model.predict(np.expand_dims(img, axis=0))) for img in images]
        return ''.join(predictions)

class CaptchaLoginManager:
    """
    負責驗證碼識別和網站登入的管理類別。
    
    此類別遵循單一職責原則，專注於登入流程的管理，
    整合了圖像處理、模型預測和登入操作。
    
    屬性:
        driver (webdriver.Chrome): Selenium WebDriver 實例。
        image_processor (ImageProcessor): 圖像處理器。
        ml_manager (MLModelManager): 機器學習模型管理器。
    
    方法:
        login(username, password): 執行單次登入。
        login_with_retry(username, password, max_retries): 帶重試的登入。
    
    Examples:
        >>> manager = CaptchaLoginManager(driver, 'captcha_model_1.keras')
        >>> manager.login_with_retry('username', 'password')
    
    Raises:
        ValueError: 當登入參數不正確時
        TimeoutException: 當頁面元素載入超時時
    """
    
    def __init__(self, driver: webdriver.Chrome, captcha_model_path: str):
        """
        初始化 CaptchaLoginManager。
        
        Args:
            driver (webdriver.Chrome): Selenium WebDriver 實例。
            captcha_model_path (str): 驗證碼模型檔案路徑。
            
        Raises:
            FileNotFoundError: 當模型檔案不存在時
        """
        self.driver = driver
        self.image_processor = ImageProcessor()
        self.ml_manager = MLModelManager(captcha_model_path)
    
    def login(self, username: str, password: str) -> None:
        """
        執行單次登入操作，包含驗證碼識別。
        
        Args:
            username (str): 登入帳號。
            password (str): 登入密碼。
            
        Examples:
            >>> manager = CaptchaLoginManager(driver, 'model.keras')
            >>> manager.login('user123', 'pass456')
            
        Raises:
            ValueError: 當帳號或密碼為空時
            TimeoutException: 當頁面元素找不到時
        """
        if not username or not password:
            raise ValueError("帳號和密碼不可為空")
        
        try:
            self.driver.get('https://www.colatour.com.tw/C000_Portal/C000_MemberLogin.aspx')
            
            image_element = self.driver.find_element(By.ID, 'imgValidate')
            image_base64 = self.image_processor.get_base64_image(self.driver, image_element)
            self.image_processor.save_base64_image(image_base64, "image.png")
            
            target_height = 30
            target_width = 100
            images = self.ml_manager.load_and_process_image("image.png", target_height, target_width)
            predicted_label = self.ml_manager.predict(images)
            
            input_field = self.driver.find_element(By.ID, 'txtImageValidate')
            input_field.send_keys(predicted_label)
            
            account = self.driver.find_element(By.ID, 'txtMemberIdno')
            account.send_keys(username)
            
            password_field = self.driver.find_element(By.ID, 'txtMemberPW')
            password_field.send_keys(password)
            
            login_button = self.driver.find_element(By.ID, 'cmdLogin')
            login_button.click()
        except ValueError as e:
            raise ValueError(f"登入過程發生錯誤: {e}") from e
    
    def login_with_retry(self, username: str, password: str, max_retries: int = 10) -> None:
        """
        帶重試機制的登入，處理驗證碼識別失敗的情況。
        
        Args:
            username (str): 登入帳號。
            password (str): 登入密碼。
            max_retries (int): 最大重試次數，預設為 10。
            
        Examples:
            >>> manager = CaptchaLoginManager(driver, 'model.keras')
            >>> manager.login_with_retry('user123', 'pass456', max_retries=5)
            
        Raises:
            ValueError: 當達到最大重試次數仍失敗時
        """
        retries = 0
        self.login(username, password)
        alert_present = EC.alert_is_present()
        
        while retries < max_retries and alert_present(self.driver):
            try:
                WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                alert = Alert(self.driver)
                alert.accept()
                
                retries += 1
                print(f"出現彈出視窗，重試登入...（第 {retries} 次重試）")
                
                self.login(username, password)
            except TimeoutException:
                break
        
        if retries == max_retries:
            print("達到最大重試次數，登入失敗，關閉視窗")
            self.driver.quit()
            raise ValueError(f"登入失敗，已達最大重試次數 {max_retries}")
        else:
            print("登入成功")


class WebNavigator:
    """
    用於瀏覽網站和執行相關操作的導覽器類別。

    此類別負責滾動頁面、登入網站以及處理驗證碼與彈出視窗的功能。

    屬性:
        driver (webdriver.Chrome): Selenium WebDriver，用於瀏覽器自動化。
    """

    def __init__(self, driver: webdriver.Chrome):
        """
        初始化 WebNavigator 類別。

        參數:
            driver (webdriver.Chrome): Selenium WebDriver 的實例，用於與瀏覽器交互。
        """
        self.driver = driver

    def scroll_to_bottom(self) -> None:
        """
        滾動至網頁底部，以加載所有內容。

        此方法持續執行滾動操作，直到頁面無法再向下滾動為止。
        """
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def login_to_website(self, username: str, password: str, captcha_model_path: str) -> None:
        """
        登入指定的網站並處理驗證碼。

        此方法包括了加載驗證碼圖片、使用預訓練模型進行驗證碼識別，並將其填入表單中以完成登入。

        參數:
            username (str): 登入帳號。
            password (str): 登入密碼。
            captcha_model_path (str): 預訓練的驗證碼識別模型的路徑。
        """
        self.driver.get('https://www.colatour.com.tw/C000_Portal/C000_MemberLogin.aspx')

        image_element = self.driver.find_element(By.ID, 'imgValidate')
        image_processor = ImageProcessor()
        captcha_solver = CaptchaSolver(captcha_model_path)

        image_base64 = image_processor.get_base64_image(self.driver, image_element)
        image_processor.save_base64_image(image_base64, "image.png")

        target_height = 30
        target_width = 100
        images = captcha_solver.load_data("image.png", target_height, target_width)
        predicted_label = captcha_solver.predict_captcha(images)

        input_field = self.driver.find_element(By.ID, 'txtImageValidate')
        input_field.send_keys(predicted_label)

        account = self.driver.find_element(By.ID, 'txtMemberIdno')
        account.send_keys(username)

        password_field = self.driver.find_element(By.ID, 'txtMemberPW')
        password_field.send_keys(password)

        login_button = self.driver.find_element(By.ID, 'cmdLogin')
        login_button.click()

    def login_with_retry(self, username: str, password: str, captcha_model_path: str, max_retries: int = 10) -> None:
        """
        嘗試登入網站並處理可能出現的驗證碼與彈出視窗，直到登入成功或達到最大重試次數。

        此方法在登入失敗且出現彈出視窗時會自動重試登入，直到成功或達到設定的最大重試次數。

        參數:
            username (str): 登入帳號。
            password (str): 登入密碼。
            captcha_model_path (str): 預訓練的驗證碼識別模型的路徑。
            max_retries (int): 最大重試次數，預設為 10 次。
        """
        retries = 0
        self.login_to_website(username, password, captcha_model_path)
        alert_present = EC.alert_is_present()
        while retries < max_retries and alert_present(self.driver):
            WebDriverWait(self.driver, 5).until(EC.alert_is_present())
            alert = Alert(self.driver)
            alert.accept()

            retries += 1
            print(f"出現彈出視窗，重試登入...（第 {retries} 次重試）")

            self.login_to_website(username, password, captcha_model_path)

        if retries == max_retries:
            print("達到最大重試次數，登入失敗，關閉視窗")
            self.driver.quit()
        else:
            print("登入成功")

class FlightDataCleaner:
    """
    負責航班資料的解析、清理和轉換。
    
    此類別遵循單一職責原則，專注於資料清理和格式轉換的功能，
    不包含任何網頁抓取或業務邏輯。
    
    方法:
        parse_date_time(text, year): 解析日期時間字串。
        parse_duration_to_timedelta(text): 解析時長字串為 timedelta。
        format_datetime_to_string(dt): 將 datetime 轉換為字串。
        format_timedelta_to_hhmm(td): 將 timedelta 轉換為 HH:MM 格式。
        extract_iata(text): 從文字中提取 IATA 機場代碼。
        parse_flight_and_cabin(text): 解析航班和艙等資訊。
        clean_flight_data(card, start_date, return_date): 清理航班資料。
        clean_price_data(card): 清理票價資料。
        clean_baggage_data(card, driver, flight_details): 清理行李資料。
    
    Examples:
        >>> cleaner = FlightDataCleaner()
        >>> dt = cleaner.parse_date_time("10/15(三) 14:30", 2025)
        >>> cleaner.extract_iata("SFO 舊金山 舊金山國際機場")
        'SFO'
    
    Raises:
        ValueError: 當資料格式不正確時
        KeyError: 當缺少必要欄位時
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
            >>> FlightDataCleaner.parse_date_time("10/15(三) 14:30", 2025)
            datetime(2025, 10, 15, 14, 30)

        Raises:
            ValueError: 當日期字串為空或無法解析時
        """
        if text is None:
            raise ValueError("日期字串不可為空")
        cleaned = re.sub(r"\([^)]*\)", "", text).strip()
        try:
            dt = datetime.strptime(f"{year}/" + cleaned, "%Y/%m/%d %H:%M")
            return dt
        except ValueError as exc:
            raise ValueError(f"無法解析日期時間: {text}") from exc
    
    @staticmethod
    def parse_duration_to_timedelta(text: str) -> timedelta:
        """
        將中文時長字串 (如 "03小時25分鐘"、"2小時15分鐘") 解析為 timedelta。

        Args:
            text (str): 表示時長的字串；若為空或無法解析則視為 0。

        Returns:
            timedelta: 由時與分組成的時間段；無法解析時為 0。
            
        Examples:
            >>> FlightDataCleaner.parse_duration_to_timedelta("3小時25分鐘")
            timedelta(hours=3, minutes=25)

        Raises:
            無明確錯誤，無法解析時回傳 timedelta(0)
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
            dt (datetime): 要轉換的日期時間物件。
            
        Returns:
            str: 格式化後的日期時間字串，失敗時回傳空字串。
            
        Examples:
            >>> from datetime import datetime
            >>> FlightDataCleaner.format_datetime_to_string(datetime(2025, 10, 15, 14, 30))
            '2025-10-15 14:30'
            
        Raises:
            無明確錯誤，轉換失敗時回傳空字串
        """
        try:
            return dt.strftime("%Y-%m-%d %H:%M")
        except (AttributeError, ValueError):
            return ""
    
    @staticmethod
    def format_timedelta_to_hhmm(td) -> str:
        """
        將 timedelta 轉成 "HH:MM"，若為 0 或無效則回傳空字串。
        
        Args:
            td (timedelta): 要轉換的時間段。
            
        Returns:
            str: 格式化後的時間字串，失敗或為 0 時回傳空字串。
            
        Examples:
            >>> from datetime import timedelta
            >>> FlightDataCleaner.format_timedelta_to_hhmm(timedelta(hours=3, minutes=25))
            '03:25'
            
        Raises:
            無明確錯誤，轉換失敗時回傳空字串
        """
        try:
            total_minutes = int(td.total_seconds() // 60)
            if total_minutes <= 0:
                return ""
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"{hours:02d}:{minutes:02d}"
        except (AttributeError, ValueError):
            return ""
    
    @staticmethod
    def extract_iata(text: str) -> str:
        """
        自機場描述文字中擷取 IATA 三字碼。

        Args:
            text (str): 例如 "SFO 舊金山 舊金山國際機場" 的字串。

        Returns:
            str: 擷取到的三字碼 (例如 "SFO")；若無則回傳空字串。
            
        Examples:
            >>> FlightDataCleaner.extract_iata("SFO 舊金山 舊金山國際機場")
            'SFO'
            
        Raises:
            無明確錯誤，找不到時回傳空字串
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
            >>> FlightDataCleaner.parse_flight_and_cabin("UA852 經濟艙 K")
            ('UA852', '經濟艙K')
            
        Raises:
            無明確錯誤，無法解析時回傳 (原字串或空, 空)
        """
        if not text:
            return "", ""
        m = re.match(r"\s*([A-Z0-9]{2,3})\s?(\d+)\s+(\S*?)\s*([A-Z])\s*$", text)
        if m:
            flight_no = m.group(1) + m.group(2)
            cabin = m.group(3)
            booking = m.group(4)
            return flight_no, f"{cabin}{booking}"
        m2 = re.search(r"([A-Z0-9]{2,3})\s?(\d+)", text)
        if m2:
            flight_no = m2.group(1) + m2.group(2)
            m3 = re.search(r"([\u4e00-\u9fa5A-Za-z]+)\s*([A-Z])\s*$", text)
            if m3:
                return flight_no, f"{m3.group(1)}{m3.group(2)}"
            return flight_no, ""
        parts = text.split()
        if len(parts) >= 3:
            return parts[0], f"{parts[1]}{parts[2]}"
        return text.strip(), ""
    
    def clean_flight_data(self, card: webdriver.remote.webelement.WebElement,
                         start_date: str, return_date: str) -> list:
        """
        自單張航班卡片的「航班明細」區塊抽取並清洗資料。
        
        會解析去程與回程、各最多三段航段，過濾轉機灰條列，並整理為欄位化結構。

        Args:
            card (webdriver.remote.webelement.WebElement): 航班卡片根元素。
            start_date (str): 去程日期，格式 'YYYY/MM/DD'，僅用於推斷年份。
            return_date (str): 回程日期，格式 'YYYY/MM/DD'，僅用於推斷年份。

        Returns:
            list[dict]: 只包含一筆紀錄的列表。包含去/回程各航段 1~3 的詳細資訊。
            
        Examples:
            >>> cleaner = FlightDataCleaner()
            >>> data = cleaner.clean_flight_data(card, "2025/10/15", "2025/10/20")
            >>> data[0]['去程航班編號1']
            'BR123'

        Raises:
            ValueError: 當日期格式不正確時
            AttributeError: 當網頁元素找不到時
        """
        return extract_and_clean_flight_data(card, start_date, return_date)
    
    def clean_price_data(self, card: webdriver.remote.webelement.WebElement) -> list:
        """
        自單張航班卡片的「票價」區塊抽取並清洗資料。

        Args:
            card (webdriver.remote.webelement.WebElement): 航班卡片根元素。

        Returns:
            list[dict]: 只包含一筆紀錄的列表。包含票價相關欄位。
            
        Examples:
            >>> cleaner = FlightDataCleaner()
            >>> data = cleaner.clean_price_data(card)
            >>> data[0]['總售價']
            8346

        Raises:
            ValueError: 當資料格式不正確時
        """
        return extract_and_clean_price_data(card)
    
    def clean_baggage_data(self, card: webdriver.remote.webelement.WebElement,
                          driver: webdriver.Chrome,
                          flight_details: dict) -> dict:
        """
        從航班卡片中提取並清理行李資訊。

        Args:
            card (webdriver.remote.webelement.WebElement): 當前的航班卡片元素。
            driver (webdriver.Chrome): 用於操作的 WebDriver。
            flight_details (dict): 當前航班的詳細資訊，用於判斷行李去回程。

        Returns:
            dict: 包含結構化行李數據的字典。
            
        Examples:
            >>> cleaner = FlightDataCleaner()
            >>> data = cleaner.clean_baggage_data(card, driver, flight_info)
            >>> data['去程行李1']
            '30公斤'

        Raises:
            ValueError: 當資料格式不正確時
            AttributeError: 當網頁元素找不到時
        """
        return extract_and_clean_baggage_data(card, driver, flight_details)


def parse_date_time(text: str, year: int) -> datetime:
    """
    將如 "10/15(三) 14:30" 或 "10/15 14:30" 的字串轉換為 datetime；年份由參數補齊。

    參數說明
    - text (str): 原始日期時間字串，格式 "MM/DD(週) HH:MM" 或 "MM/DD HH:MM"。
    - year (int): 年份 (西元)，用於組合完整日期時間。

    返回值說明
    - datetime: 解析成功的日期時間物件；若解析失敗會拋出 ValueError。
    """
    if text is None:
        raise ValueError("日期字串不可為空")
    # 去除括號中的星期
    cleaned = re.sub(r"\([^)]*\)", "", text).strip()
    # 期望格式: MM/DD HH:MM
    try:
        dt = datetime.strptime(f"{year}/" + cleaned, "%Y/%m/%d %H:%M")
        return dt
    except Exception as exc:
        raise ValueError(f"無法解析日期時間: {text}") from exc

def parse_duration_to_timedelta(text: str) -> timedelta:
    """
    將中文時長字串 (如 "03小時25分鐘"、"2小時15分鐘") 解析為 timedelta。

    參數說明
    - text (str): 表示時長的字串；若為空或無法解析則視為 0。

    返回值說明
    - timedelta: 由時與分組成的時間段；無法解析時為 0。
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

def format_datetime_to_string(dt) -> str:
    """
    將 datetime 轉成字串 "YYYY-MM-DD HH:MM"，無效則回傳空字串。
    """
    try:
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""

def format_timedelta_to_hhmm(td) -> str:
    """
    將 timedelta 轉成 "HH:MM"，若為 0 或無效則回傳空字串。
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

def extract_iata(text: str) -> str:
    """
    自機場描述文字中擷取 IATA 三字碼。

    參數說明
    - text (str): 例如 "SFO 舊金山 舊金山國際機場" 的字串。

    返回值說明
    - str: 擷取到的三字碼 (例如 "SFO")；若無則回傳空字串。
    """
    if not text:
        return ""
    m = re.match(r"\s*([A-Z]{3})\b", text.strip())
    return m.group(1) if m else ""

def parse_flight_and_cabin(text: str) -> tuple:
    """
    解析航班與艙等資訊字串，取得航班號與「艙等+訂位代碼」。

    參數說明
    - text (str): 例如 "UA852 經濟艙 K" 的字串。

    返回值說明
    - tuple[str, str]: (航班號, 艙等與艙等編碼)。
      若無法解析：回傳 (原字串或空, 空)。
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

def extract_and_clean_flight_data(
                card: webdriver.remote.webelement.WebElement,
                start_date: str,
                return_date: str) -> list:
    """
    自單張航班卡片的「航班明細」區塊抽取並清洗資料。會解析去程與回程、各最多三段航段，
    過濾轉機灰條列，並整理為欄位化結構。

    參數說明
    - card (selenium.webdriver.remote.webelement.WebElement): 航班卡片根元素。
    - start_date (str): 去程日期，格式 'YYYY/MM/DD'，僅用於推斷年份。
    - return_date (str): 回程日期，格式 'YYYY/MM/DD'，僅用於推斷年份。

    返回值說明
    - list[dict]: 只包含一筆紀錄的列表。鍵包含去/回程各航段 1~3 的以下欄位：
      - "{去程|回程}航班編號{i}"
      - "{去程|回程}艙等與艙等編碼{i}"
      - "{去程|回程}起飛機場{i}"
      - "{去程|回程}降落機場{i}"
      - "{去程|回程}起飛時間{i}" (str，格式 YYYY-MM-DD HH:MM，無值為空字串)
      - "{去程|回程}降落時間{i}" (str，格式 YYYY-MM-DD HH:MM，無值為空字串)
      - "{去程|回程}飛機公司及型號{i}"
      - "{去程|回程}飛行時間{i}" (str，格式 HH:MM，無值為空字串)
    """
    # 彙整單張卡片，將去/回程最多三段航段填入對應欄位
    results = []
    year_outbound = int(start_date.split("/")[0])
    year_inbound = int(return_date.split("/")[0])

    # 初始化欄位
    record = {}
    for d in ["去程", "回程"]:
        for i in range(1, 4):
            record[f"{d}航班編號{i}"] = ""
            record[f"{d}艙等與艙等編碼{i}"] = ""
            record[f"{d}起飛機場{i}"] = ""
            record[f"{d}降落機場{i}"] = ""
            record[f"{d}起飛時間{i}"] = ""
            record[f"{d}降落時間{i}"] = ""
            record[f"{d}飛機公司及型號{i}"] = ""
            record[f"{d}飛行時間{i}"] = ""

    segment_index = {"去程": 1, "回程": 1}

    # 取得去程/回程外層表格
    outer_tables = card.find_elements(By.CSS_SELECTOR, "table.flightDetails_table")
    for idx, outer in enumerate(outer_tables):
        outer_class = outer.get_attribute("class") or ""
        # 標題優先，其次 class，最後索引後備
        has_return_title = len(outer.find_elements(By.XPATH, ".//p[contains(@class,'detail_title') and contains(.,'回程')] | .//p[contains(@class,'desktop_detail_title') and contains(.,'回程')]")) > 0
        if has_return_title or "return_line" in outer_class:
            direction = "回程"
        else:
            direction = "回程" if idx == 1 else "去程"
        assumed_year = year_inbound if direction == "回程" else year_outbound

        # 只抓取真正的航段資料列（排除轉機灰條）
        rows = outer.find_elements(
            By.XPATH,
            ".//tr[not(contains(concat(' ', normalize-space(@class), ' '), ' flightDetails_gray ')) and "
            "not(contains(concat(' ', normalize-space(@class), ' '), ' middleStay ')) and "
            "td[contains(concat(' ', normalize-space(@class), ' '), ' cell_2 ') and "
            "contains(concat(' ', normalize-space(@class), ' '), ' b-box ')]]"
        )
        if not rows:
            rows = outer.find_elements(
                By.XPATH,
                ".//tr[not(contains(@class,'flightDetails_gray')) and (td[contains(@class,'cell_2')] or td[contains(@class,'cell_3')] or td[contains(@class,'cell_5')])]"
            )
        for tr in rows:
            if segment_index[direction] > 3:
                continue

            # cell_2: 航空與航班資訊（第2個 <p> 為 航班編號 + 艙等資訊）
            cell2 = tr.find_element(By.CSS_SELECTOR, "td.cell_2")
            flight_and_cabin_text = ""
            for _ in range(3):
                p_texts = [p.text.strip() for p in cell2.find_elements(By.TAG_NAME, "p") if p.text.strip()]
                candidates = [t for t in p_texts if re.search(r"[A-Z0-9]{2,3}\s?\d+", t)]
                if candidates:
                    flight_and_cabin_text = candidates[-1]
                    break
                time.sleep(0.2)
            flight_no, cabin_and_code = parse_flight_and_cabin(flight_and_cabin_text)

            # cell_3: 出發資訊
            dep_airport = ""
            dep_dt = None
            cell3 = tr.find_element(By.CSS_SELECTOR, "td.cell_3")
            cell3_ps = [p.text.strip() for p in cell3.find_elements(By.TAG_NAME, "p")]
            if cell3_ps:
                dep_airport = extract_iata(cell3_ps[0]) or dep_airport
                time_line = None
                for t in cell3_ps:
                    if re.search(r"\d{1,2}/\d{1,2}.*\d{1,2}:\d{2}", t):
                        time_line = t
                        break
                if time_line:
                    dep_dt = parse_date_time(time_line, assumed_year)

            # cell_5: 抵達資訊
            arr_airport = ""
            arr_dt = None
            cell5 = tr.find_element(By.CSS_SELECTOR, "td.cell_5")
            cell5_ps = [p.text.strip() for p in cell5.find_elements(By.TAG_NAME, "p")]
            if cell5_ps:
                arr_airport = extract_iata(cell5_ps[0]) or arr_airport
                time_line = None
                for t in cell5_ps:
                    if re.search(r"\d{1,2}/\d{1,2}.*\d{1,2}:\d{2}", t):
                        time_line = t
                        break
                if time_line:
                    arr_dt = parse_date_time(time_line, assumed_year)

            # cell_6: 機型與飛行時間
            equipment_text = ""
            duration_td = timedelta(0)
            cell6 = tr.find_element(By.CSS_SELECTOR, "td.cell_6")
            cell6_ps = [p.text.strip() for p in cell6.find_elements(By.TAG_NAME, "p") if p.text.strip()]
            if cell6_ps:
                dur_line = next((t for t in cell6_ps if re.search(r"\d+\s*小時|\d+\s*分", t)), "")
                if dur_line:
                    duration_td = parse_duration_to_timedelta(dur_line)
                    equipment_text = next((t for t in cell6_ps if t != dur_line), equipment_text)
                else:
                    equipment_text = cell6_ps[0]

            idx = segment_index[direction]
            record[f"{direction}航班編號{idx}"] = flight_no
            record[f"{direction}艙等與艙等編碼{idx}"] = cabin_and_code
            record[f"{direction}起飛機場{idx}"] = dep_airport
            record[f"{direction}降落機場{idx}"] = arr_airport
            # 轉為字串（時間: YYYY-MM-DD HH:MM；時長: HH:MM）
            dep_str = format_datetime_to_string(dep_dt)
            arr_str = format_datetime_to_string(arr_dt)
            dur_str = format_timedelta_to_hhmm(duration_td)
            record[f"{direction}起飛時間{idx}"] = dep_str
            record[f"{direction}降落時間{idx}"] = arr_str
            record[f"{direction}飛機公司及型號{idx}"] = equipment_text
            record[f"{direction}飛行時間{idx}"] = dur_str

            segment_index[direction] += 1

    results.append(record)
    return results

def extract_and_clean_price_data(card):
    """
    自單張航班卡片的「票價」區塊抽取並清洗資料。
    
    參數說明
    - card (selenium.webdriver.remote.webelement.WebElement): 航班卡片根元素。
    
    返回值說明
    - list[dict]: 只包含一筆紀錄的列表。鍵包含以下欄位：
        - gds_type
        ...(其他欄位)
    """
    # 1) 透過 card 取得對應的 driver，等待票價明細彈出視窗出現
    driver = getattr(card, "parent", None) or getattr(card, "_parent", None)
    results = []

    def parse_int(text: str) -> int:
        if text is None:
            return 0
        cleaned = re.sub(r"[ ,，]", "", text)
        try:
            return int(cleaned)
        except Exception:
            # 若帶有小數點，取整數部分
            try:
                return int(float(cleaned))
            except Exception:
                return 0

    def parse_float(text: str) -> float:
        if text is None:
            return 0.0
        cleaned = text.replace("，", ",")  # 容忍中文逗號
        cleaned = cleaned.replace(",", "")  # 去除千分位
        try:
            return float(cleaned)
        except Exception:
            return 0.0

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

    # 等待含有 id=DBGModal 的內容載入
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "DBGModal"))
        )
    except Exception:
        # 若沒有彈窗，回傳預設欄位
        results.append(record)
        return results

    try:
        modal = driver.find_element(By.ID, "DBGModal")
    except Exception:
        results.append(record)
        return results

    modal_text = modal.text or ""

    # 2) 解析 GDS Type
    m = re.search(r"GDS\s*Type[:：]\s*([^\s\r\n]+)", modal_text)
    if m:
        record["GDS Type"] = m.group(1).strip()

    # 3) 優先從「大人公式」解析各欄位
    #    範例：( 票面 4,468 * [KP3] - 折扣 0 ) * 1.021 + TAX 3,840 * 1.021 + 固定金額 0 = 8,346
    formula_line = ""
    fm = re.search(r"大人公式[:：]\s*(.*)", modal_text)
    if fm:
        formula_line = fm.group(1).strip()

    if formula_line:
        # 公式型態 1：
        # ( 票面|淨價 <num> * [KP#] - 折扣 <num> ) * <num> + TAX <num> * <num> + 固定金額 <num> = <num>
        type1_pattern = re.compile(
            r"^\(\s*(票面|淨價)\s*[\d,，]+\s*\*\s*\[\s*KP\s*\d+\s*\]\s*-\s*折扣\s*[\d,，]+\s*\)\s*\*\s*[0-9]+(?:\.[0-9]+)?\s*\+\s*TAX\s*[\d,，]+\s*\*\s*[0-9]+(?:\.[0-9]+)?\s*\+\s*固定金額\s*[-]?[\d,，]+\s*=\s*[\d,，]+\s*$",
            re.IGNORECASE
        )
        # 公式型態 2（參考資料C）：
        # ( (票面|淨價 <num> - 折扣 <num>) * [KP#] ) * <num> + TAX <num> * <num> + 固定金額 <num> = <num>
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
                breakpoint()  # 未知公式：中斷以供人工確認
            except Exception:
                pass

        # 票型 + 基礎票價
        # 型態1："( 票面 11,800 * [KP3] - 折扣 0 ) ..."
        # 型態2："( (票面 11,800 - 折扣 0) * [KP5] ) ..."
        m_type_price = re.search(r"\(\s*([\u4e00-\u9fa5A-Za-z]+)\s*([\d,，]+)", formula_line)
        if not m_type_price:
            m_type_price = re.search(r"\(\s*\(\s*([\u4e00-\u9fa5A-Za-z]+)\s*([\d,，]+)", formula_line)
        if m_type_price:
            record["票型"] = m_type_price.group(1).strip()
            record["基礎票價"] = parse_int(m_type_price.group(2))

        # 折讓百分比 (由 [KPx] 取得 x)
        m_kp = re.search(r"\[\s*KP\s*(\d+)\s*\]", formula_line, re.IGNORECASE)
        if m_kp:
            record["折讓百分比"] = int(m_kp.group(1))

        # 折扣
        m_disc = re.search(r"折扣\s*([\d,，]+)", formula_line)
        if m_disc:
            record["折扣"] = parse_int(m_disc.group(1))

        # 票價加價成數：在第一個右括號之後的 "* number"
        m_price_factor = re.search(r"\)\s*\*\s*([0-9]+(?:\.[0-9]+)?)", formula_line)
        if m_price_factor:
            record["票價加價成數"] = parse_float(m_price_factor.group(1))

        # 稅金與稅金加價成數：TAX <num> * <num>
        m_tax = re.search(r"TAX\s*([\d,，]+)\s*\*\s*([0-9]+(?:\.[0-9]+)?)", formula_line, re.IGNORECASE)
        if m_tax:
            record["稅金"] = parse_int(m_tax.group(1))
            record["稅金加價成數"] = parse_float(m_tax.group(2))

        # 固定金額（允許負數）
        m_fixed = re.search(r"固定金額\s*([-]?[\d,，]+)", formula_line)
        if m_fixed:
            record["固定金額"] = parse_int(m_fixed.group(1))

        # 總售價：等號右側
        m_total = re.search(r"=\s*([\d,，]+)\s*$", formula_line)
        if m_total:
            record["總售價"] = parse_int(m_total.group(1))

    # 4) 後備：若稅金/總售價未抓到，嘗試由其他段落補齊
    if not record["稅金"]:
        # 例如：MP： 票面 4468 稅金 3840 或 NEGO 8446 稅金 2534
        m_tax2 = re.search(r"稅金\s*([\d,，]+)", modal_text)
        if m_tax2:
            record["稅金"] = parse_int(m_tax2.group(1))

    if not record["總售價"]:
        # 有時候頁面會在其他區段顯示售價（保守：若找不到，維持 0）
        m_total2 = re.search(r"總售價[:：]\s*([\d,，]+)", modal_text)
        if m_total2:
            record["總售價"] = parse_int(m_total2.group(1))

    results.append(record)
    return results

class CrawlerOrchestrator:
    """
    爬蟲系統的流程控制器，負責協調所有組件完成整體爬取任務。
    
    此類別遵循依賴反轉原則，依賴於抽象接口而非具體實現，
    並且負責整合所有功能類別來完成完整的爬取流程。
    
    屬性:
        driver (webdriver.Chrome): Selenium WebDriver 實例。
        data_cleaner (FlightDataCleaner): 資料清理器。
        website_navigator (WebsiteNavigator): 網站導航器。
        login_manager (CaptchaLoginManager): 登入管理器。
        data_uploader (DataUploader): 資料上傳器。
        
    方法:
        crawl_flights(origin, destination, start_date, return_date): 爬取單個航線的資料。
        run_tasks(date_combinations): 執行多個爬取任務。
    
    Examples:
        >>> orchestrator = CrawlerOrchestrator(
        ...     username='user',
        ...     password='pass',
        ...     captcha_model_path='model.keras',
        ...     project_id='my-project',
        ...     dataset_table='dataset.table'
        ... )
        >>> df = orchestrator.crawl_flights('TPE', 'TYO', '2025/10/15', '2025/10/20')
    
    Raises:
        ValueError: 當參數不正確時
        Exception: 當爬取過程發生錯誤時
    """
    
    def __init__(self, username: str, password: str, captcha_model_path: str,
                 project_id: str, dataset_table: str):
        """
        初始化 CrawlerOrchestrator 及所有相依組件。
        
        Args:
            username (str): 登入帳號。
            password (str): 登入密碼。
            captcha_model_path (str): 驗證碼模型路徑。
            project_id (str): Google Cloud 專案 ID。
            dataset_table (str): BigQuery 資料集和表格名稱。
            
        Raises:
            ValueError: 當必要參數為空時
        """
        if not all([username, password, captcha_model_path, project_id, dataset_table]):
            raise ValueError("所有參數都不可為空")
        
        # 初始化 WebDriver
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--window-size=1920x1080")
        
        if platform.machine() == 'aarch64':
            service = ChromeService(executable_path='/usr/bin/chromedriver')
            chrome_options.binary_location = '/usr/bin/chromium'
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            self.driver = webdriver.Chrome(options=chrome_options)
        
        # 初始化所有組件
        self.data_cleaner = FlightDataCleaner()
        self.website_navigator = WebsiteNavigator(self.driver)
        self.login_manager = CaptchaLoginManager(self.driver, captcha_model_path)
        self.data_uploader = DataUploader(project_id, dataset_table)
        
        # 儲存登入資訊
        self.username = username
        self.password = password
    
    def crawl_flights(self, origin_code: str, destination_code: str,
                     start_date: str, return_date: str) -> pd.DataFrame:
        """
        爬取單個航線的機票資料。
        
        Args:
            origin_code (str): 出發地代碼 (例如 'TPE')。
            destination_code (str): 目的地代碼 (例如 'TYO')。
            start_date (str): 出發日期，格式為 'YYYY/MM/DD'。
            return_date (str): 返回日期，格式為 'YYYY/MM/DD'。
            
        Returns:
            pd.DataFrame: 爬取並清理後的航班資料。
            
        Examples:
            >>> orchestrator = CrawlerOrchestrator(...)
            >>> df = orchestrator.crawl_flights('TPE', 'TYO', '2025/10/15', '2025/10/20')
            
        Raises:
            ValueError: 當參數不正確時
            Exception: 當爬取過程發生錯誤時
        """
        return main(origin_code, destination_code, start_date, return_date)
    
    def run_tasks(self, origin_code: str, destination_code: str,
                 date_info_list: List[Dict[str, str]]) -> None:
        """
        執行多個爬取任務並上傳資料。
        
        Args:
            origin_code (str): 出發地代碼。
            destination_code (str): 目的地代碼。
            date_info_list (List[Dict[str, str]]): 日期資訊列表，每個元素包含 departure_date 和 return_date。
            
        Examples:
            >>> orchestrator = CrawlerOrchestrator(...)
            >>> dates = [
            ...     {'departure_date': '2025-10-15', 'return_date': '2025-10-20'},
            ...     {'departure_date': '2025-11-15', 'return_date': '2025-11-20'}
            ... ]
            >>> orchestrator.run_tasks('TPE', 'TYO', dates)
            
        Raises:
            ValueError: 當資料格式不正確時
        """
        for date_info in date_info_list:
            start_date = date_info['departure_date'].replace('-', '/')
            return_date = date_info['return_date'].replace('-', '/')
            
            print(f"處理航線: {origin_code} -> {destination_code}, "
                  f"出發日期: {start_date}, 回程日期: {return_date}")
            
            try:
                final_df = self.crawl_flights(origin_code, destination_code,
                                             start_date, return_date)
                self.data_uploader.upload_to_bigquery(final_df)
            except Exception as e:
                print(f"處理日期 {start_date} - {return_date} 時發生錯誤: {e}")
                continue
    
    def cleanup(self) -> None:
        """
        清理資源，關閉 WebDriver。
        
        Examples:
            >>> orchestrator = CrawlerOrchestrator(...)
            >>> orchestrator.cleanup()
            
        Raises:
            無明確錯誤
        """
        if self.driver:
            self.driver.quit()


def main(origin_code: str, 
         destination_code: str, 
         start_date: str, 
         return_date: str):
    """
    主程式。
    
    參數:
        origin_code (str): 出發地代碼 (例如 'TPE')。
        destination_code (str): 目的地代碼 (例如 'TYO')。
        start_date (str): 出發日期，格式為 'YYYY/MM/DD'。
        return_date (str): 返回日期，格式為 'YYYY/MM/DD'。
    """
    # 初始化 WebDriver
    chrome_options = Options()
    # 無頭模式(無UI)
    chrome_options.add_argument("--headless") # 無頭模式
    chrome_options.add_argument("--no-sandbox") # 禁用沙盒
    chrome_options.add_argument("--disable-dev-shm-usage") # 禁用 DevTools
    chrome_options.add_argument("--disable-gpu")  # 禁用 GPU
    chrome_options.add_argument("--remote-debugging-port=9222")  # 設置遠程調試端口
    chrome_options.add_argument("--window-size=1920x1080")  # 設置窗口大小

    # 根據系統架構設定不同的瀏覽器路徑
    if platform.machine() == 'aarch64':
        service = ChromeService(executable_path='/usr/bin/chromedriver')
        chrome_options.binary_location = '/usr/bin/chromium'
        driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )
    else:
        driver = webdriver.Chrome(options=chrome_options)

    navigator = WebNavigator(driver)

    # 登入網站並處理驗證碼
    login_to_site(navigator, '0920262685', 'B8722000', 'captcha_model_1.keras')

    # 導航至機票查詢頁面
    navigate_to_flight_page(driver=driver, 
                            origin_code=origin_code, 
                            destination_code=destination_code, 
                            start_date=start_date, 
                            return_date=return_date)

    # 等待頁面加載並滾動至底部以加載所有內容
    WebDriverWait(driver, 45).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'tab01')))
    navigator.scroll_to_bottom()

    # 展開所有可用的航班選項
    expand_flight_options(driver)

    # 等待展開操作完成
    time.sleep(2)

    # 獲取所有航班卡片
    flight_cards = driver.find_elements(By.CLASS_NAME, 'airPrice_box')
    print(f"找到 {len(flight_cards)} 張航班卡片")

    # 迴圈處理每一張卡片
    extracted_rows = []
    for card_index, card in enumerate(flight_cards):
        # 驗證每一張卡片是否只有兩組 MultiSegment div
        multi_segment_divs = card.find_elements(By.XPATH, ".//div[@ng-repeat='MultiSegment in cjSegment[$index]' and @ng-init='MultiSegmentIndex=$index' and @class='ng-scope']")
        
        if len(multi_segment_divs) != 2:
            print(f"警告：第 {card_index + 1} 張卡片包含 {len(multi_segment_divs)} 組 MultiSegment div（預期為 2 組）")
            continue
        else:
            print(f"第 {card_index + 1} 張卡片驗證通過：包含 {len(multi_segment_divs)} 組 MultiSegment div")

        # 去程航班以及按鈕
        departure_flights_buttons = multi_segment_divs[0].find_elements(By.XPATH, ".//input[@type='radio' and @name]")
        
        # 回程航班以及按鈕
        return_flights_buttons = multi_segment_divs[1].find_elements(By.XPATH, ".//input[@type='radio' and @name]")
        
        # 將所有去程與回程的組合逐一點擊（先點去程，再點回程）
        # 1. 先取得去程和回程各有幾個選項
        dep_count = len(departure_flights_buttons)
        ret_count = len(return_flights_buttons)

        # 2. 用索引迴圈處理去程選項
        for d_idx in range(dep_count):
            # 3. 每次都重新抓取去程按鈕列表，避免 DOM 更新造成元素失效
            # 4. 確保索引不超過按鈕列表長度，避免索引錯誤
            dep_list = multi_segment_divs[0].find_elements(By.XPATH, ".//input[@type='radio' and @name]")
            if d_idx >= len(dep_list):
                break
            dep_btn = dep_list[d_idx]
            # 5. 確保按鈕可見並可點擊
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", dep_btn)
            driver.execute_script("arguments[0].click();", dep_btn)
            time.sleep(0.1)

            # 6. 內層迴圈：對每個去程選項，都要配對所有回程選項
            for r_idx in range(ret_count):
                ret_list = multi_segment_divs[1].find_elements(By.XPATH, ".//input[@type='radio' and @name]")
                if r_idx >= len(ret_list):
                    break
                ret_btn = ret_list[r_idx]
                # 7. 滾動並點擊回程按鈕
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ret_btn)
                driver.execute_script("arguments[0].click();", ret_btn)
                time.sleep(0.1)

                # 8. 航班資訊取得
                # 點擊航班資訊
                flight_tab = card.find_element(By.CSS_SELECTOR, "a.tab01")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", flight_tab)
                driver.execute_script("arguments[0].click();", flight_tab)
                WebDriverWait(driver, 5).until(lambda d: len(card.find_elements(By.CSS_SELECTOR, ".flightDetails_table")) >= 2)
                # 於每次組合選取後，抽取航班明細資料
                flight_extracted = extract_and_clean_flight_data(card, start_date, return_date)

                # 9. 行李資訊取得
                # 點擊行李資訊 Tab
                baggage_tab = card.find_element(By.CSS_SELECTOR, "a.tab03")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", baggage_tab)
                driver.execute_script("arguments[0].click();", baggage_tab)
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".bagInformation_tab")))
                # 獲取當前卡片的航班詳細資訊，用於判斷行李是去程還是回程
                current_flight_details = flight_extracted[0] if flight_extracted else {}
                # 將當前卡片的行李資訊合併到航班詳細資訊中
                card_baggage_info = extract_and_clean_baggage_data(card, driver, current_flight_details)

                # 10. 票價資訊取得
                # 點擊票價資訊
                price_strong = card.find_element(By.CSS_SELECTOR, "strong[bo-text='SaleGroup.Display_Price | number']")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", price_strong)
                driver.execute_script("arguments[0].click();", price_strong)
                # 於每次組合選取後，抽取票價資料
                price_extracted = extract_and_clean_price_data(card)

                # 11. 點擊背景遮罩復原彈出視窗
                # 由於每次組合選取後，都會彈出視窗，因此需要點擊背景遮罩復原彈出視窗
                overlay = driver.find_element(By.CSS_SELECTOR, ".ui-widget-overlay.ui-front")
                driver.execute_script("arguments[0].click();", overlay)

                # 12. 爬取時間戳記
                created_at = time.time()

                # 12. 合併資料
                row = {**flight_extracted[0], **price_extracted[0], **card_baggage_info, "建立時間": created_at}
                extracted_rows.append(row)


    # 彙總成 DataFrame（符合新資料結構：去/回程 + 航段 1~3）並去重
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
        # 只保留我們關心的欄位，並依序排序
        final_df = final_df.reindex(columns=column_order)
        final_df = final_df.drop_duplicates()
    else:
        final_df = pd.DataFrame(columns=column_order)

    return final_df

class WebsiteNavigator:
    """
    負責網站操作和導航的類別。
    
    此類別遵循單一職責原則，專注於網站的導航、頁面操作等功能，
    不包含登入或資料處理邏輯。
    
    屬性:
        driver (webdriver.Chrome): Selenium WebDriver 實例。
    
    方法:
        navigate_to_flight_page(origin, destination, start_date, return_date): 導航到航班查詢頁。
        scroll_to_bottom(): 滾動到頁面底部。
        expand_flight_options(): 展開所有航班選項。
    
    Examples:
        >>> navigator = WebsiteNavigator(driver)
        >>> navigator.navigate_to_flight_page('TPE', 'TYO', '2025/10/15', '2025/10/20')
        >>> navigator.expand_flight_options()
    
    Raises:
        ValueError: 當參數不正確時
        TimeoutException: 當頁面載入超時時
    """
    
    def __init__(self, driver: webdriver.Chrome):
        """
        初始化 WebsiteNavigator。
        
        Args:
            driver (webdriver.Chrome): Selenium WebDriver 實例。
        """
        self.driver = driver
    
    def navigate_to_flight_page(self, origin_code: str, destination_code: str,
                                start_date: str, return_date: str) -> None:
        """
        導航至指定的機票查詢頁面。
        
        Args:
            origin_code (str): 出發地代碼 (例如 'TPE')。
            destination_code (str): 目的地代碼 (例如 'TYO')。
            start_date (str): 出發日期，格式為 'YYYY/MM/DD'。
            return_date (str): 返回日期，格式為 'YYYY/MM/DD'。
            
        Examples:
            >>> navigator = WebsiteNavigator(driver)
            >>> navigator.navigate_to_flight_page('TPE', 'TYO', '2025/10/15', '2025/10/20')
            
        Raises:
            ValueError: 當日期格式不正確時
        """
        if not all([origin_code, destination_code, start_date, return_date]):
            raise ValueError("所有參數都不可為空")
        
        url = (f'https://www.colatour.com.tw/C10C_MPAirTicket/C10C_20_ChooseLowFare.aspx?'
               f'DirectFlightMark=False&JourneyType=Round&OriginCode={origin_code}&'
               f'DestinationCode={destination_code}&ReturnCode={destination_code}&'
               f'StartDate={start_date}&ReturnDate={return_date}&AdtCnt=1&ChdCnt=0&'
               f'InfantCnt=0&ServiceClass=ALL&SegmentStartDate={start_date.replace("/", "_")},'
               f'{return_date.replace("/", "_")}&SegmentLocCode={origin_code}.{destination_code},'
               f'{destination_code}.{origin_code}&SegmentLocType=City.City,City.City')
        self.driver.get(url)
        self.driver.set_window_size(945, 1012)
    
    def scroll_to_bottom(self) -> None:
        """
        滾動至網頁底部，以加載所有內容。
        
        此方法持續執行滾動操作，直到頁面無法再向下滾動為止。
        
        Examples:
            >>> navigator = WebsiteNavigator(driver)
            >>> navigator.scroll_to_bottom()
            
        Raises:
            無明確錯誤
        """
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    
    def expand_flight_options(self) -> None:
        """
        展開所有可用的航班選項，點擊所有"更多航班"按鈕。
        
        Examples:
            >>> navigator = WebsiteNavigator(driver)
            >>> navigator.expand_flight_options()
            
        Raises:
            TimeoutException: 當頁面元素載入超時時
        """
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'airPrice_box'))
        )
        
        expand_buttons = self.driver.find_elements(
            By.XPATH, "//a[contains(@class, 'plusBtn') and contains(text(), '更多航班')]"
        )
        
        print(f"找到 {len(expand_buttons)} 個更多航班按鈕")
        
        for i, button in enumerate(expand_buttons):
            try:
                self.driver.execute_script("arguments[0].scrollIntoView();", button)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", button)
                print(f"已展開第 {i+1} 個航班選項")
            except Exception as e:
                print(f"點擊第 {i+1} 個展開按鈕時發生錯誤: {e}")
                continue
        
        print("所有航班選項已展開完成")


class DataUploader:
    """
    負責資料上傳到 BigQuery 的類別。
    
    此類別遵循單一職責原則，專注於資料上傳功能，
    與資料處理和爬取邏輯分離。
    
    屬性:
        project_id (str): Google Cloud 專案 ID。
        dataset_table (str): BigQuery 資料集和表格名稱。
    
    方法:
        upload_to_bigquery(dataframe): 上傳 DataFrame 到 BigQuery。
    
    Examples:
        >>> uploader = DataUploader('my-project', 'dataset.table')
        >>> uploader.upload_to_bigquery(df)
    
    Raises:
        ValueError: 當專案 ID 或表格名稱為空時
        Exception: 當上傳失敗時
    """
    
    def __init__(self, project_id: str, dataset_table: str):
        """
        初始化 DataUploader。
        
        Args:
            project_id (str): Google Cloud 專案 ID。
            dataset_table (str): BigQuery 資料集和表格名稱 (格式: 'dataset.table')。
            
        Raises:
            ValueError: 當參數為空時
        """
        if not project_id or not dataset_table:
            raise ValueError("project_id 和 dataset_table 不可為空")
        
        self.project_id = project_id
        self.dataset_table = dataset_table
    
    def upload_to_bigquery(self, dataframe: pd.DataFrame) -> None:
        """
        上傳 DataFrame 到 BigQuery。
        
        Args:
            dataframe (pd.DataFrame): 要上傳的資料。
            
        Examples:
            >>> uploader = DataUploader('my-project', 'economy.table')
            >>> uploader.upload_to_bigquery(df)
            
        Raises:
            ValueError: 當 DataFrame 為空時
            Exception: 當上傳失敗時
        """
        if dataframe.empty:
            print("警告: DataFrame 為空，跳過上傳")
            return
        
        try:
            dataframe.to_gbq(
                self.dataset_table,
                if_exists='append',
                project_id=self.project_id
            )
            print(f"成功寫入 {len(dataframe)} 筆資料到 BigQuery")
        except Exception as e:
            raise Exception(f"上傳到 BigQuery 失敗: {e}") from e


def login_to_site(navigator, username: str, password: str, captcha_model_path: str):
    """
    使用指定的用戶名和密碼登入網站，並處理驗證碼。
    
    參數:
        navigator (WebNavigator): 網站導航工具。
        username (str): 登入帳號。
        password (str): 登入密碼。
        captcha_model_path (str): 預訓練的驗證碼識別模型路徑。
    """
    navigator.login_with_retry(username=username, password=password, captcha_model_path=captcha_model_path)

def expand_flight_options(driver: webdriver.Chrome) -> None:
    """
    展開所有可用的航班選項，點擊所有"更多航班"按鈕。

    參數:
        driver (webdriver.Chrome): 用於操作的 WebDriver。
    """
    # 等待頁面加載完成
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, 'airPrice_box'))
    )

    # 找到所有"更多航班"按鈕
    # 這些按鈕包含文字"更多航班"且有plusBtn類別
    expand_buttons = driver.find_elements(By.XPATH, "//a[contains(@class, 'plusBtn') and contains(text(), '更多航班')]")

    print(f"找到 {len(expand_buttons)} 個更多航班按鈕")

    # 點擊每個展開按鈕
    for i, button in enumerate(expand_buttons):
        try:
            # 確保按鈕可見並可點擊
            driver.execute_script("arguments[0].scrollIntoView();", button)
            time.sleep(0.5)  # 等待滾動完成

            # 使用JavaScript點擊按鈕，避免某些點擊事件無法觸發的問題
            driver.execute_script("arguments[0].click();", button)
            print(f"已展開第 {i+1} 個航班選項")

        except Exception as e:
            print(f"點擊第 {i+1} 個展開按鈕時發生錯誤: {e}")
            continue

    print("所有航班選項已展開完成")

def extract_and_clean_baggage_data(
    card: webdriver.remote.webelement.WebElement,
    driver: webdriver.Chrome,
    current_flight_details: dict
) -> dict:
    """
    從航班卡片中提取並清理行李資訊。

    參數:
        card (webdriver.remote.webelement.WebElement): 當前的航班卡片元素。
        driver (webdriver.Chrome): 用於操作的 WebDriver。
        current_flight_details (dict): 當前航班的詳細資訊，用於判斷行李去回程。

    返回值:
        dict: 包含結構化行李數據的字典。
    """
    card_baggage_info = {}  # 儲存當前卡片的所有行李資訊
    outbound_baggage_counter = 0  # 去程行李計數器
    return_baggage_counter = 0    # 回程行李計數器

    baggage_rows = card.find_elements(By.CSS_SELECTOR, ".bagInformation_tab table.bagInformation tbody tr.bagInformation_item")

    for row_idx, row in enumerate(baggage_rows):
        segment_element = row.find_element(By.CSS_SELECTOR, "td.segment")
        segment_text = segment_element.text.strip()

        flight_num_element = row.find_element(By.CSS_SELECTOR, "td.flight_num")
        flight_num_text = flight_num_element.text.strip()

        adult_baggage_element = row.find_element(By.CSS_SELECTOR, "td[data-title='成人']")
        adult_baggage_text = adult_baggage_element.text.strip()

        # 使用正規表達式提取數字和單位
        match = re.search(r'(\d+)\s*(公斤|件)?', adult_baggage_text)
        if match:
            value = int(match.group(1))
            unit = match.group(2) if match.group(2) else ""
            cleaned_baggage_info = f"{value}{unit}"
        else:
            cleaned_baggage_info = None

        # 從行李航段文本中提取機場代碼
        airport_match = re.search(r'(\w+)\s+.*?－\s*(\w+)', segment_text)
        dep_airport_code = airport_match.group(1) if airport_match else None
        arr_airport_code = airport_match.group(2) if airport_match else None

        # 判斷是去程還是回程
        current_journey_type = None
        for i in range(1, 4):  # 假設最多有3個航段
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
            # 可以考慮將無法判斷的航班也加入，例如作為「未知行李X」
    return card_baggage_info
    
def navigate_to_flight_page(driver: webdriver.Chrome,
                            origin_code: str,
                            destination_code: str,
                            start_date: str,
                            return_date: str):
    """
    導航至指定的機票查詢頁面。

    參數:
        driver (webdriver.Chrome): 用於導航的 WebDriver。
        origin_code (str): 出發地代碼 (例如 'TPE')。
        destination_code (str): 目的地代碼 (例如 'TYO')。
        start_date (str): 出發日期，格式為 'YYYY/MM/DD'。
        return_date (str): 返回日期，格式為 'YYYY/MM/DD'。
    """
    url = (f'https://www.colatour.com.tw/C10C_MPAirTicket/C10C_20_ChooseLowFare.aspx?'
           f'DirectFlightMark=False&JourneyType=Round&OriginCode={origin_code}&'
           f'DestinationCode={destination_code}&ReturnCode={destination_code}&'
           f'StartDate={start_date}&ReturnDate={return_date}&AdtCnt=1&ChdCnt=0&'
           f'InfantCnt=0&ServiceClass=ALL&SegmentStartDate={start_date.replace("/", "_")},'
           f'{return_date.replace("/", "_")}&SegmentLocCode={origin_code}.{destination_code},'
           f'{destination_code}.{origin_code}&SegmentLocType=City.City,City.City')
    driver.get(url)
    driver.set_window_size(945, 1012)

def fetch_dates_from_api(month_offset: int, dep_day: int, return_day: int) -> Dict[str, str]:
    """
    從 API 取得指定月份偏移量和日期的航班日期資訊。
    
    Args:
        month_offset (int): 月份偏移量，表示從當前月份往後推幾個月（必須 >= 0）
        dep_day (int): 出發日期的天數（1-31）
        return_day (int): 回程日期的天數（1-31）
    
    Returns:
        Dict[str, str]: 包含 departure_date 和 return_date 的字典
    
    Examples:
        >>> date_info = fetch_dates_from_api(2, 5, 10)
        >>> date_info['departure_date']
        '2025-12-05'
        >>> date_info['return_date']
        '2025-12-10'
    
    Raises:
        requests.exceptions.RequestException: 當 API 請求失敗時
        ValueError: 當參數值不符合要求時
        KeyError: 當 API 回應格式不符合預期時
    """
    if month_offset < 0:
        raise ValueError(f"month_offset 必須大於等於 0，目前值為 {month_offset}")
    if not (1 <= dep_day <= 31):
        raise ValueError(f"dep_day 必須介於 1-31，目前值為 {dep_day}")
    if not (1 <= return_day <= 31):
        raise ValueError(f"return_day 必須介於 1-31，目前值為 {return_day}")
    
    api_url = f"{API_BASE_URL}/calculate_dates"
    payload = {
        "month_offset": month_offset,
        "dep_day": dep_day,
        "return_day": return_day
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"API 請求失敗: {e}") from e
    
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise ValueError(f"API 回應格式錯誤，無法解析 JSON: {e}") from e
    
    if not data.get("success"):
        error_msg = data.get("error", "未知錯誤")
        raise ValueError(f"API 回應錯誤: {error_msg}")
    
    try:
        result = {
            "departure_date": data["data"]["departure_date"],
            "return_date": data["data"]["return_date"]
        }
    except KeyError as e:
        raise KeyError(f"API 回應缺少必要欄位: {e}") from e
    
    return result

 

if __name__ == "__main__":
    IATA_ID = os.getenv('IATA_ID')
    
    # 定義要查詢的日期組合（出發日, 回程日）
    date_combinations = [
        (5, 10),   # 每月 5 日出發，10 日回程
        (24, 28),  # 每月 24 日出發，28 日回程
    ]
    
    # 從 API 取得 2 個月後和 6 個月後的日期
    month_offsets = [2, 6]
    all_dates = []
    
    for offset in month_offsets:
        for dep_day, return_day in date_combinations:
            try:
                date_info = fetch_dates_from_api(offset, dep_day, return_day)
                all_dates.append(date_info)
                print(f"成功取得 {offset} 個月後的日期: {date_info['departure_date']} - {date_info['return_date']}")
            except (requests.exceptions.RequestException, ValueError, KeyError) as e:
                print(f"取得 {offset} 個月後 {dep_day}-{return_day} 日的日期時發生錯誤: {e}")
                continue
    
    if not all_dates:
        print("警告: 未能取得任何日期資料，程式終止")
    else:
        for iata in [['TPE', IATA_ID]]:
            for date_info in all_dates:
                # 將 API 回傳的日期格式 'YYYY-MM-DD' 轉換為 'YYYY/MM/DD'
                start_date = date_info['departure_date'].replace('-', '/')
                return_date = date_info['return_date'].replace('-', '/')
                
                print(f"處理航線: {iata[0]} -> {iata[1]}, 出發日期: {start_date}, 回程日期: {return_date}")
                
                try:
                    final_df = main(origin_code=iata[0],
                                    destination_code=iata[1],
                                    start_date=start_date,
                                    return_date=return_date)
                    final_df.to_gbq('economy.New_cola_air_tickets_price', if_exists='append', project_id="testing-cola-rd")
                    print(f"成功寫入 {len(final_df)} 筆資料到 BigQuery")
                except Exception as e:
                    print(f"處理日期 {start_date} - {return_date} 時發生錯誤: {e}")
                    continue
