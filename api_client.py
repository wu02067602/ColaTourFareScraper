# 標準庫
import json
from typing import Dict, List

# 第三方庫
import requests
import google.auth.transport.requests
import google.oauth2.id_token
from google.auth.exceptions import DefaultCredentialsError

class DateAPIClient:
    """
    日期 API 客戶端，負責從 API 取得節日日期和固定日期資訊。
    
    Examples:
        >>> client = DateAPIClient()
        >>> holidays = client.get_holiday_dates(2)
    
    Raises:
        ValueError: 當參數無效時
        requests.exceptions.RequestException: 當 API 請求失敗時
    """
    
    HOLIDAY_API_URL = "https://domanda-get-date-data-934329676269.asia-east1.run.app/calculate_holiday_dates"
    FIXED_DATE_API_URL = "https://domanda-get-date-data-934329676269.asia-east1.run.app/calculate_dates"
    
    def get_holiday_dates(self, month_offset: int) -> List[Dict]:
        """
        透過 API 取得指定月份偏移量的節日日期資訊。
        
        Args:
            month_offset (int): 月份偏移量，表示從當前月份往後推幾個月（必須 > 0）
        
        Returns:
            List[Dict]: 節日資訊列表，每個字典包含以下欄位：
                - holiday_name (str): 節日名稱
                - holiday_date (str): 節日日期，格式 YYYY-MM-DD
                - departure_date (str): 建議出發日期，格式 YYYY-MM-DD
                - return_date (str): 建議返回日期，格式 YYYY-MM-DD
                - weekday (str): 星期幾
        
        Examples:
            >>> client = DateAPIClient()
            >>> holidays = client.get_holiday_dates(2)
            >>> print(holidays[0]['holiday_name'])
            '行憲紀念日'
        
        Raises:
            ValueError: 當 month_offset 小於 0 時
            requests.exceptions.RequestException: 當 API 請求失敗時
            KeyError: 當 API 回應格式不符合預期時
        """
        if month_offset <= 0:
            raise ValueError(f"month_offset 必須 > 0，目前值為 {month_offset}")
        
        try:
            # 獲取 ID Token
            auth_req = google.auth.transport.requests.Request()
            id_token = google.oauth2.id_token.fetch_id_token(auth_req, self.HOLIDAY_API_URL)

            # 加入 Authorization header
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json"
            }
        except DefaultCredentialsError as e:
            headers = {
                "Authorization": "",
            }
        
        try:
            response = requests.post(
                self.HOLIDAY_API_URL,
                json={"month_offset": month_offset},
                timeout=10,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get("success", False):
                raise ValueError(f"API 回應失敗: {result.get('error', '未知錯誤')}")
            
            holidays = result.get("data", {}).get("holidays", [])
            return holidays
        
        except requests.exceptions.Timeout as e:
            raise requests.exceptions.RequestException(f"API 請求超時: {e}")
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(f"API 請求失敗: {e}")
        except json.JSONDecodeError as e:
            import pickle
            with open('error_result.pkl', 'wb') as f:
                pickle.dump(result, f)
            raise json.JSONDecodeError(f"API 回應格式錯誤: {e}", e.doc, e.pos)
        except KeyError as e:
            raise KeyError(f"API 回應格式錯誤，缺少必要欄位: {e}")

    def get_fixed_dates(self, month_offset: int, dep_day: int, return_day: int) -> Dict:
        """
        透過 API 取得指定月份偏移量與固定日期的日期資訊。
        
        Args:
            month_offset (int): 月份偏移量，表示從當前月份往後推幾個月（必須 >= 0）
            dep_day (int): 出發日期的天數（1-31）
            return_day (int): 回程日期的天數（1-31）
        
        Returns:
            Dict: 日期資訊字典，包含以下欄位：
                - departure_date (str): 出發日期，格式 YYYY-MM-DD
                - return_date (str): 回程日期，格式 YYYY-MM-DD
                - target_year (int): 目標年份
                - target_month (int): 目標月份
        
        Examples:
            >>> client = DateAPIClient()
            >>> dates = client.get_fixed_dates(2, 5, 10)
            >>> print(dates['departure_date'])
            '2025-12-05'
        
        Raises:
            ValueError: 當 month_offset 小於 0 時
            ValueError: 當 dep_day 或 return_day 不在 1-31 範圍內時
            requests.exceptions.RequestException: 當 API 請求失敗時
            KeyError: 當 API 回應格式不符合預期時
        """
        if month_offset <= 0:
            raise ValueError(f"month_offset 必須 >= 0，目前值為 {month_offset}")
        
        if not (1 <= dep_day <= 31):
            raise ValueError(f"dep_day 必須在 1-31 之間，目前值為 {dep_day}")
        
        if not (1 <= return_day <= 31):
            raise ValueError(f"return_day 必須在 1-31 之間，目前值為 {return_day}")
        
        try:

            # 獲取 ID Token
            auth_req = google.auth.transport.requests.Request()
            id_token = google.oauth2.id_token.fetch_id_token(auth_req, self.FIXED_DATE_API_URL)

            # 加入 Authorization header
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json"
            }
        except DefaultCredentialsError as e:
            headers = {
                "Content-Type": "application/json",
                "Authorization": "",
            }
        
        try:
            response = requests.post(
                self.FIXED_DATE_API_URL,
                json={
                    "month_offset": month_offset,
                    "dep_day": dep_day,
                    "return_day": return_day
                },
                timeout=10,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get("success", False):
                raise ValueError(f"API 回應失敗: {result.get('error', '未知錯誤')}")
            
            dates = result.get("data", {})
            return dates
        
        except requests.exceptions.Timeout as e:
            raise requests.exceptions.RequestException(f"API 請求超時: {e}")
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(f"API 請求失敗: {e}")
        except json.JSONDecodeError as e:
            import pickle
            with open('error_result.pkl', 'wb') as f:
                pickle.dump(result, f)
            raise json.JSONDecodeError(f"API 回應格式錯誤: {e}", e.doc, e.pos)
        except KeyError as e:
            raise KeyError(f"API 回應格式錯誤，缺少必要欄位: {e}")


class DatePairGenerator:
    """
    日期對生成器，負責從 API 生成日期對列表。
    
    Examples:
        >>> generator = DatePairGenerator()
        >>> date_pairs = generator.generate_from_api()
    
    Raises:
        ValueError: 當生成失敗時
    """
    
    def __init__(self):
        """
        初始化日期對生成器。
        
        Examples:
            >>> generator = DatePairGenerator()
        
        Raises:
            無特定錯誤
        """
        self.api_client = DateAPIClient()
    
    def generate_from_api(self) -> List[List[List[int]]]:
        """
        透過 API 動態生成爬取日期列表。
        
        Returns:
            List[List[List[int]]]: 日期對列表，格式為 [[[year, month, day], [year, month, day]], ...]
        
        Examples:
            >>> generator = DatePairGenerator()
            >>> date_pairs = generator.generate_from_api()
            >>> print(date_pairs[0])
            [[2025, 12, 5], [2025, 12, 10]]
        
        Raises:
            ValueError: 當 API 回應格式錯誤時
            requests.exceptions.RequestException: 當 API 請求失敗時
        """
        date_pairs = []
        
        month_offsets = [2, 6]
        
        # 1. 從 API 取得節日日期
        print("=== 從 API 取得節日日期 ===")
        for month_offset in month_offsets:
            try:
                holidays = self.api_client.get_holiday_dates(month_offset=month_offset)
                for holiday in holidays:
                    departure_str = holiday['departure_date']
                    return_str = holiday['return_date']
                    
                    dep_parts = departure_str.split('-')
                    ret_parts = return_str.split('-')
                    
                    date_pair = [
                        [int(dep_parts[0]), int(dep_parts[1]), int(dep_parts[2])],
                        [int(ret_parts[0]), int(ret_parts[1]), int(ret_parts[2])]
                    ]
                    date_pairs.append(date_pair)
                    
                    print(f"新增節日日期: {holiday['holiday_name']} - {departure_str} 到 {return_str}")
            except (ValueError, requests.exceptions.RequestException, KeyError) as e:
                print(f"取得 {month_offset} 個月後節日日期時發生錯誤: {e}")
        
        # 2. 從 API 取得固定日期
        print("\n=== 從 API 取得固定日期 ===")
        fixed_date_configs = [
            {'dep_day': 5, 'return_day': 10},
            {'dep_day': 24, 'return_day': 28},
        ]
        
        for month_offset in month_offsets:
            for config in fixed_date_configs:
                try:
                    dates = self.api_client.get_fixed_dates(
                        month_offset=month_offset,
                        dep_day=config['dep_day'],
                        return_day=config['return_day']
                    )
                    
                    departure_str = dates['departure_date']
                    return_str = dates['return_date']
                    
                    dep_parts = departure_str.split('-')
                    ret_parts = return_str.split('-')
                    
                    date_pair = [
                        [int(dep_parts[0]), int(dep_parts[1]), int(dep_parts[2])],
                        [int(ret_parts[0]), int(ret_parts[1]), int(ret_parts[2])]
                    ]
                    date_pairs.append(date_pair)
                    
                    print(f"新增固定日期: {departure_str} 到 {return_str}")
                except (ValueError, requests.exceptions.RequestException, KeyError) as e:
                    print(f"取得 {month_offset} 個月後固定日期（{config['dep_day']}號-{config['return_day']}號）時發生錯誤: {e}")
        
        print(f"\n=== 共生成 {len(date_pairs)} 組日期 ===\n")
        return date_pairs
