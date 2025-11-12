# 標準庫
import os
import tempfile
import time
from datetime import datetime
from typing import Optional

# 第三方庫
from google.cloud import storage
from selenium import webdriver


class ScreenshotHandler:
    """
    截圖處理器，負責截取網頁截圖並上傳到 Cloud Storage。
    
    Examples:
        >>> handler = ScreenshotHandler("testing-cola-rd-vector-storage")
        >>> handler.capture_and_upload(driver, "error_001")
    
    Raises:
        ValueError: 當參數無效時
        RuntimeError: 當上傳失敗時
    """
    
    def __init__(self, bucket_name: str):
        """
        初始化截圖處理器。
        
        Args:
            bucket_name (str): Cloud Storage bucket 名稱。
        
        Examples:
            >>> handler = ScreenshotHandler("testing-cola-rd-vector-storage")
        
        Raises:
            ValueError: 當 bucket_name 為空時
        """
        if not bucket_name:
            raise ValueError("bucket_name 不可為空")
        
        self.bucket_name = bucket_name
        self.storage_client = storage.Client()
    
    def capture_and_upload(
        self,
        driver: webdriver.Chrome,
        error_context: str,
        filename_prefix: Optional[str] = None,
        delay: float = 5.0,
    ) -> str:
        """
        截取網頁截圖並上傳到 Cloud Storage。
        
        Args:
            driver (webdriver.Chrome): Selenium WebDriver 實例。
            error_context (str): 錯誤上下文描述，用於命名檔案。
            filename_prefix (Optional[str]): 檔案名稱前綴，預設為 None。
            delay (float): 延遲截圖的時間（秒），預設為 5.0 秒。
        
        Returns:
            str: 上傳到 Cloud Storage 的檔案路徑。
        
        Examples:
            >>> handler = ScreenshotHandler("testing-cola-rd-vector-storage")
            >>> path = handler.capture_and_upload(driver, "get_base64_image_error")
            >>> isinstance(path, str)
            True
        
        Raises:
            ValueError: 當 driver 或 error_context 為空時
            RuntimeError: 當截圖或上傳失敗時
        """
        if driver is None:
            raise ValueError("driver 不可為 None")
        if not error_context:
            raise ValueError("error_context 不可為空")
        
        try:
            # 生成檔案名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            safe_context = error_context.replace(" ", "_").replace("/", "_")
            
            if filename_prefix:
                filename = f"{filename_prefix}_{safe_context}_{timestamp}.png"
            else:
                filename = f"{safe_context}_{timestamp}.png"
            
            # 延遲截圖
            if delay > 0:
                time.sleep(delay)
            
            # 截圖並保存到本地臨時檔案
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_path = temp_file.name
            
            driver.save_screenshot(temp_path)
            
            # 上傳到 Cloud Storage
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(filename)
            blob.upload_from_filename(temp_path)
            
            # 清理臨時檔案
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            print(f"截圖已上傳到 Cloud Storage: gs://{self.bucket_name}/{filename}")
            return f"gs://{self.bucket_name}/{filename}"
            
        except Exception as e:
            raise RuntimeError(f"截圖或上傳失敗: {e}")

