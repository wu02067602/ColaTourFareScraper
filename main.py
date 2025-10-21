#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ColaTourFareScraper 主程式入口

此程式負責爬取可樂旅遊網站上的機票票價資訊，並將數據上傳至 BigQuery。
"""

# 標準庫
import os

# 本地模組
from api_client import DatePairGenerator
from data_uploader import BigQueryUploader
from task_controller import ScraperTaskController


def main():
    """
    主程式入口函數。
    
    此函數負責：
    1. 從 API 取得日期對列表
    2. 迴圈處理每個機場組合和日期
    3. 執行爬蟲任務
    4. 上傳資料到 BigQuery
    
    Examples:
        >>> main()
    
    Raises:
        ValueError: 當環境變數缺少時
        RuntimeError: 當程式執行失敗時
    """
    # 取得環境變數
    iata_id = os.getenv('IATA_ID')
    if not iata_id:
        raise ValueError("環境變數 IATA_ID 未設定")
    
    # 使用 API 動態生成日期列表
    generator = DatePairGenerator()
    date_pairs = generator.generate_from_api()
    
    # 初始化控制器和上傳器
    controller = ScraperTaskController()
    uploader = BigQueryUploader()
    
    # 迴圈處理每個機場組合
    for iata in [['TPE', iata_id]]:
        # 迴圈處理每組日期
        for date in date_pairs:
            print(f"正在爬取: {iata[0]} -> {iata[1]}, "
                  f"{date[0][0]}/{date[0][1]}/{date[0][2]} - {date[1][0]}/{date[1][1]}/{date[1][2]}")
            
            # 執行爬蟲任務
            final_df = controller.run_scraping_task(
                origin_code=iata[0],
                destination_code=iata[1],
                start_date=f"{date[0][0]}/{date[0][1]}/{date[0][2]}",
                return_date=f"{date[1][0]}/{date[1][1]}/{date[1][2]}"
            )
            
            # 上傳資料到 BigQuery
            uploader.upload_dataframe(
                dataframe=final_df,
                table_id='economy.New_cola_air_tickets_price',
                project_id='testing-cola-rd'
            )
            
            print(f"完成爬取並上傳 {len(final_df)} 筆資料")


if __name__ == "__main__":
    main()
