# 標準庫
import platform
import time

# 第三方庫
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# 本地模組
from captcha_handler import CaptchaSolver, ImageProcessor


class WebDriverFactory:
    """
    WebDriver 工廠類別，負責建立和配置 Chrome WebDriver。
    
    Examples:
        >>> factory = WebDriverFactory()
        >>> driver = factory.create_driver()
    
    Raises:
        RuntimeError: 當 WebDriver 建立失敗時
    """
    
    @staticmethod
    def create_driver() -> webdriver.Chrome:
        """
        建立並配置 Chrome WebDriver。
        
        Returns:
            webdriver.Chrome: 配置好的 Chrome WebDriver 實例。
        
        Examples:
            >>> factory = WebDriverFactory()
            >>> driver = factory.create_driver()
            >>> driver.quit()
        
        Raises:
            RuntimeError: 當 WebDriver 建立失敗時
        """
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--window-size=1920x1080")

        try:
            if platform.machine() == 'aarch64':
                service = ChromeService(executable_path='/usr/bin/chromedriver')
                chrome_options.binary_location = '/usr/bin/chromium'
                driver = webdriver.Chrome(
                    service=service,
                    options=chrome_options
                )
            else:
                driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            raise RuntimeError(f"WebDriver 建立失敗: {e}")


class WebNavigator:
    """
    用於瀏覽網站和執行相關操作的導覽器類別。

    此類別負責滾動頁面、登入網站以及處理驗證碼與彈出視窗的功能。

    屬性:
        driver (webdriver.Chrome): Selenium WebDriver，用於瀏覽器自動化。
    
    Examples:
        >>> driver = WebDriverFactory.create_driver()
        >>> navigator = WebNavigator(driver)
        >>> navigator.scroll_to_bottom()
    
    Raises:
        ValueError: 當 driver 為 None 時
    """

    def __init__(self, driver: webdriver.Chrome):
        """
        初始化 WebNavigator 類別。

        Args:
            driver (webdriver.Chrome): Selenium WebDriver 的實例，用於與瀏覽器交互。
        
        Examples:
            >>> driver = WebDriverFactory.create_driver()
            >>> navigator = WebNavigator(driver)
        
        Raises:
            ValueError: 當 driver 為 None 時
        """
        if driver is None:
            raise ValueError("driver 不可為 None")
        self.driver = driver

    def scroll_to_bottom(self) -> None:
        """
        滾動至網頁底部，以加載所有內容。

        此方法持續執行滾動操作，直到頁面無法再向下滾動為止。
        
        Examples:
            >>> navigator = WebNavigator(driver)
            >>> navigator.scroll_to_bottom()
        
        Raises:
            無特定錯誤
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

        Args:
            username (str): 登入帳號。
            password (str): 登入密碼。
            captcha_model_path (str): 預訓練的驗證碼識別模型的路徑。
        
        Examples:
            >>> navigator = WebNavigator(driver)
            >>> navigator.login_to_website("user", "pass", "model.keras")
        
        Raises:
            ValueError: 當 username、password 或 captcha_model_path 為空時
            FileNotFoundError: 當模型文件不存在時
        """
        if not username:
            raise ValueError("username 不可為空")
        if not password:
            raise ValueError("password 不可為空")
        if not captcha_model_path:
            raise ValueError("captcha_model_path 不可為空")
        
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

        Args:
            username (str): 登入帳號。
            password (str): 登入密碼。
            captcha_model_path (str): 預訓練的驗證碼識別模型的路徑。
            max_retries (int): 最大重試次數，預設為 10 次。
        
        Examples:
            >>> navigator = WebNavigator(driver)
            >>> navigator.login_with_retry("user", "pass", "model.keras", max_retries=5)
        
        Raises:
            ValueError: 當 username、password 或 captcha_model_path 為空時
            ValueError: 當 max_retries 小於等於 0 時
        """
        if max_retries <= 0:
            raise ValueError("max_retries 必須大於 0")
        
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

    def navigate_to_flight_page(
        self,
        origin_code: str,
        destination_code: str,
        start_date: str,
        return_date: str
    ) -> None:
        """
        導航至指定的機票查詢頁面。

        Args:
            origin_code (str): 出發地代碼 (例如 'TPE')。
            destination_code (str): 目的地代碼 (例如 'TYO')。
            start_date (str): 出發日期，格式為 'YYYY/MM/DD'。
            return_date (str): 返回日期，格式為 'YYYY/MM/DD'。
        
        Examples:
            >>> navigator = WebNavigator(driver)
            >>> navigator.navigate_to_flight_page("TPE", "TYO", "2025/10/15", "2025/10/20")
        
        Raises:
            ValueError: 當任何參數為空時
        """
        if not origin_code:
            raise ValueError("origin_code 不可為空")
        if not destination_code:
            raise ValueError("destination_code 不可為空")
        if not start_date:
            raise ValueError("start_date 不可為空")
        if not return_date:
            raise ValueError("return_date 不可為空")
        
        url = (f'https://www.colatour.com.tw/C10C_MPAirTicket/C10C_20_ChooseLowFare.aspx?'
               f'DirectFlightMark=False&JourneyType=Round&OriginCode={origin_code}&'
               f'DestinationCode={destination_code}&ReturnCode={destination_code}&'
               f'StartDate={start_date}&ReturnDate={return_date}&AdtCnt=1&ChdCnt=0&'
               f'InfantCnt=0&ServiceClass=ALL&SegmentStartDate={start_date.replace("/", "_")},'
               f'{return_date.replace("/", "_")}&SegmentLocCode={origin_code}.{destination_code},'
               f'{destination_code}.{origin_code}&SegmentLocType=City.City,City.City')
        self.driver.get(url)
        self.driver.set_window_size(945, 1012)


class FlightOptionExpander:
    """
    航班選項展開器，負責展開網頁上的所有航班選項。
    
    Examples:
        >>> expander = FlightOptionExpander(driver)
        >>> expander.expand_all_options()
    
    Raises:
        ValueError: 當 driver 為 None 時
    """
    
    def __init__(self, driver: webdriver.Chrome):
        """
        初始化航班選項展開器。
        
        Args:
            driver (webdriver.Chrome): Selenium WebDriver 實例。
        
        Examples:
            >>> expander = FlightOptionExpander(driver)
        
        Raises:
            ValueError: 當 driver 為 None 時
        """
        if driver is None:
            raise ValueError("driver 不可為 None")
        self.driver = driver
    
    def expand_all_options(self) -> None:
        """
        展開所有可用的航班選項，點擊所有"更多航班"按鈕。
        
        Examples:
            >>> expander = FlightOptionExpander(driver)
            >>> expander.expand_all_options()
        
        Raises:
            無特定錯誤
        """
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'airPrice_box'))
        )

        expand_buttons = self.driver.find_elements(
            By.XPATH, 
            "//a[contains(@class, 'plusBtn') and contains(text(), '更多航班')]"
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
