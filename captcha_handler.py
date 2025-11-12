# 標準庫
import base64
import os

# 第三方庫
import numpy as np
from PIL import Image
from selenium import webdriver
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array

# 本地模組
from screenshot_handler import ScreenshotHandler


class ImageProcessor:
    """
    處理圖像的類別，包括獲取 Base64 圖像、保存圖像到文件以及處理圖像裁剪的功能。

    屬性:
        WHITE_PIXEL_VALUE (int): 白色像素的值，預設為 255。
        CHAR_TO_INT (dict): 字元到整數的映射，用於字元處理。
    
    Examples:
        >>> processor = ImageProcessor()
        >>> base64_data = processor.get_base64_image(driver, element)
        >>> processor.save_base64_image(base64_data, "image.png")
    
    Raises:
        FileNotFoundError: 當圖像文件不存在時
        ValueError: 當圖像處理參數無效時
    """

    WHITE_PIXEL_VALUE = 255
    CHAR_TO_INT = {chr(i+48): i for i in range(10)}
    CHAR_TO_INT.update({chr(i+55): i for i in range(10, 36)})

    def get_base64_image(self, driver: webdriver.Chrome, element: webdriver.remote.webelement.WebElement) -> str:
        """
        從 Selenium WebDriver 元素中獲取 Base64 格式的圖像數據。
        
        此方法會自動檢查圖片是否已載入完成，並等待最多 5 秒。如果圖片載入失敗或超時，
        會拋出 JavaScript 錯誤，並由 Selenium 轉換為相應的異常。

        Args:
            driver (webdriver.Chrome): Selenium WebDriver 物件。
            element (webdriver.remote.webelement.WebElement): 要獲取圖片的 WebElement。

        Returns:
            str: 圖像的 Base64 編碼數據。
        
        Examples:
            >>> processor = ImageProcessor()
            >>> base64_data = processor.get_base64_image(driver, image_element)
            >>> isinstance(base64_data, str)
            True
        
        Raises:
            ValueError: 當 driver 或 element 為 None 時
            selenium.common.exceptions.JavascriptException: 當圖片載入失敗或超時時
        """
        if driver is None or element is None:
            raise ValueError("driver 和 element 不可為 None")
        
        script = """
        var img = arguments[0];
        
        // 檢查圖片是否已載入的函數
        function checkImageLoaded(img) {
            // 檢查圖片是否已完成載入且尺寸有效
            return img.complete && img.naturalWidth > 0 && img.naturalHeight > 0;
        }
        
        // 使用輪詢方式等待圖片載入（最多等待 5 秒）
        var maxAttempts = 50; // 50 次 × 100ms = 5 秒
        var attempt = 0;
        
        while (attempt < maxAttempts) {
            // 檢查圖片是否已載入
            if (checkImageLoaded(img)) {
                // 圖片已載入，開始轉換為 Base64
                var canvas = document.createElement('canvas');
                canvas.width = img.naturalWidth || img.width;
                canvas.height = img.naturalHeight || img.height;
                var ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                return canvas.toDataURL('image/png').substring(22);
            }
            
            // 如果圖片標記為已完成但尺寸無效，可能是載入失敗
            if (img.complete && (img.naturalWidth === 0 || img.naturalHeight === 0)) {
                throw new Error('圖片載入失敗：圖片處於 broken 狀態');
            }
            
            // 等待 100ms 後重試
            var start = Date.now();
            while (Date.now() - start < 100) {
                // 空循環等待
            }
            attempt++;
        }
        
        // 超時仍未載入
        throw new Error('圖片載入超時：在 5 秒內無法完成載入');
        """
        try:
            return driver.execute_script(script, element)
        except Exception as e:
            # 錯誤發生時進行截圖
            try:
                screenshot_handler = ScreenshotHandler("testing-cola-rd-vector-storage")
                screenshot_handler.capture_and_upload(driver, "get_base64_image_error")
            except Exception as screenshot_error:
                print(f"截圖失敗: {screenshot_error}")
            raise

    def save_base64_image(self, base64_data: str, file_path: str) -> None:
        """
        將 Base64 數據保存為圖像文件。

        Args:
            base64_data (str): Base64 編碼的圖像數據。
            file_path (str): 保存圖像文件的路徑。

        Returns:
            None
        
        Examples:
            >>> processor = ImageProcessor()
            >>> processor.save_base64_image("iVBORw0KGgoAAAA...", "test.png")
        
        Raises:
            ValueError: 當 base64_data 為空或 file_path 無效時
            IOError: 當文件寫入失敗時
        """
        if not base64_data:
            raise ValueError("base64_data 不可為空")
        if not file_path:
            raise ValueError("file_path 不可為空")
        
        try:
            image_data = base64.b64decode(base64_data)
            with open(file_path, "wb") as f:
                f.write(image_data)
        except IOError as e:
            raise IOError(f"文件寫入失敗: {e}")

    def process_image(self, image_path: str, target_height: int, target_width: int) -> list:
        """
        處理圖像並返回裁剪後的圖像數組。

        Args:
            image_path (str): 圖像文件的路徑。
            target_height (int): 目標圖像的高度。
            target_width (int): 目標圖像的寬度。

        Returns:
            list: 裁剪後的圖像數組，以數字數組的形式表示。
        
        Examples:
            >>> processor = ImageProcessor()
            >>> images = processor.process_image("captcha.png", 30, 100)
            >>> len(images)
            4
        
        Raises:
            FileNotFoundError: 當圖像文件不存在時
            ValueError: 當 target_height 或 target_width 小於等於 0 時
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"圖像文件不存在: {image_path}")
        if target_height <= 0 or target_width <= 0:
            raise ValueError("target_height 和 target_width 必須大於 0")
        
        # 開啟圖像並轉換為灰階
        image = Image.open(image_path)
        gray_image = image.convert('L')
        image_array = np.array(gray_image)
        
        # 計算每列非白色像素的數量
        non_white_pixels_per_column = np.sum(image_array != self.WHITE_PIXEL_VALUE, axis=0)
        
        # 計算非白色像素的平均值（減去標準差的 25% 作為閾值調整）
        average_non_white_pixels = np.mean(non_white_pixels_per_column) - 0.25 * (np.std(non_white_pixels_per_column))
        
        # 找出超過平均值的列索引
        columns_above_average = np.where(non_white_pixels_per_column > average_non_white_pixels)[0]
        
        # 將連續的列索引分組為範圍
        continuous_ranges = []
        start = columns_above_average[0]
        for i in range(1, len(columns_above_average)):
            if columns_above_average[i] != columns_above_average[i-1] + 1:
                continuous_ranges.append((start, columns_above_average[i-1]))
                start = columns_above_average[i]
        continuous_ranges.append((start, columns_above_average[-1]))
        
        # 依範圍大小排序，取前 4 個最大的範圍
        sorted_data = sorted(continuous_ranges, key=lambda x: abs(x[1] - x[0]), reverse=True)
        continuous_ranges = sorted(sorted_data[:4])
        
        # 計算 4 個範圍之間的中點，重新定義邊界
        updated_ranges = [
            (0, self.calculate_midpoint(continuous_ranges[0], continuous_ranges[1])),
            (self.calculate_midpoint(continuous_ranges[0], continuous_ranges[1]), self.calculate_midpoint(continuous_ranges[1], continuous_ranges[2])),
            (self.calculate_midpoint(continuous_ranges[1], continuous_ranges[2]), self.calculate_midpoint(continuous_ranges[2], continuous_ranges[3])),
            (self.calculate_midpoint(continuous_ranges[2], continuous_ranges[3]), image.width)
        ]
        continuous_ranges = updated_ranges
        
        # 轉換為 RGB 格式並裁剪圖像
        rgb_image = image.convert('RGB')
        cropped_images = []
        for start, end in continuous_ranges:
            # 裁剪出單個字符區域
            cropped_image = rgb_image.crop((start, 0, end, rgb_image.height))
            
            # 創建白色背景並將裁剪的圖像貼上
            new_width = 100
            background = Image.new('RGB', (new_width, target_height), (255, 255, 255))
            paste_position = (new_width - target_width, 0)
            background.paste(cropped_image, paste_position)
            
            # 將處理後的圖像轉換為數組並加入列表
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
        
        Examples:
            >>> processor = ImageProcessor()
            >>> processor.calculate_midpoint((0, 10), (20, 30))
            15
        
        Raises:
            ValueError: 當 range1 或 range2 不是長度為 2 的 tuple 時
        """
        if not isinstance(range1, tuple) or len(range1) != 2:
            raise ValueError("range1 必須是長度為 2 的 tuple")
        if not isinstance(range2, tuple) or len(range2) != 2:
            raise ValueError("range2 必須是長度為 2 的 tuple")
        
        return int((range1[1] + range2[0]) / 2)


class CaptchaSolver:
    """
    CaptchaSolver 類別負責處理驗證碼的預測與解碼。

    透過預先訓練的深度學習模型，這個類別可以加載圖像數據並進行驗證碼的解碼與預測。

    屬性:
        model: 預訓練的驗證碼識別模型。
    
    Examples:
        >>> solver = CaptchaSolver("captcha_model_1.keras")
        >>> images = solver.load_data("captcha.png", 30, 100)
        >>> result = solver.predict_captcha(images)
    
    Raises:
        FileNotFoundError: 當模型文件不存在時
        ValueError: 當模型載入失敗時
    """

    def __init__(self, model_path: str):
        """
        初始化 CaptchaSolver 類別並加載模型。

        Args:
            model_path (str): 預訓練模型的文件路徑。
        
        Examples:
            >>> solver = CaptchaSolver("captcha_model_1.keras")
        
        Raises:
            FileNotFoundError: 當模型文件不存在時
            ValueError: 當模型載入失敗時
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        try:
            self.model = load_model(model_path)
        except Exception as e:
            raise ValueError(f"模型載入失敗: {e}")

    def load_data(self, data_dir: str, target_height: int, target_width: int) -> np.ndarray:
        """
        加載並處理圖像數據，將圖像裁剪並轉換為數組格式。

        Args:
            data_dir (str): 圖像文件的路徑。
            target_height (int): 圖像裁剪後的目標高度。
            target_width (int): 圖像裁剪後的目標寬度。

        Returns:
            np.ndarray: 處理後的圖像數據數組，範圍在 [0, 1] 之間。
        
        Examples:
            >>> solver = CaptchaSolver("captcha_model_1.keras")
            >>> images = solver.load_data("captcha.png", 30, 100)
            >>> images.shape
            (4, 30, 100, 3)
        
        Raises:
            FileNotFoundError: 當圖像文件不存在時
            ValueError: 當 target_height 或 target_width 無效時
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
        
        Examples:
            >>> solver = CaptchaSolver("captcha_model_1.keras")
            >>> pred = np.array([[0.1, 0.9], [0.8, 0.2]])
            >>> solver.decode_prediction(pred)
            'AB'
        
        Raises:
            ValueError: 當 pred 格式無效時
        """
        if not isinstance(pred, np.ndarray):
            raise ValueError("pred 必須是 numpy ndarray")
        
        int_to_char = {i: c for c, i in ImageProcessor.CHAR_TO_INT.items()}
        return ''.join([int_to_char[np.argmax(c)] for c in pred])

    def predict_captcha(self, images: np.ndarray) -> str:
        """
        使用加載的模型對圖像數據進行預測，並解碼成驗證碼字串。

        Args:
            images (np.ndarray): 預處理後的圖像數據數組。

        Returns:
            str: 解碼後的驗證碼字串。
        
        Examples:
            >>> solver = CaptchaSolver("captcha_model_1.keras")
            >>> images = solver.load_data("captcha.png", 30, 100)
            >>> result = solver.predict_captcha(images)
            >>> len(result)
            4
        
        Raises:
            ValueError: 當 images 格式無效時
        """
        if not isinstance(images, np.ndarray):
            raise ValueError("images 必須是 numpy ndarray")
        
        predictions = [self.decode_prediction(self.model.predict(np.expand_dims(img, axis=0))) for img in images]
        return ''.join(predictions)
