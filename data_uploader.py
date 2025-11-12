# 第三方庫
import pandas as pd


class BigQueryUploader:
    """
    BigQuery 資料上傳器，負責將 DataFrame 上傳到 BigQuery。
    
    Examples:
        >>> uploader = BigQueryUploader()
        >>> uploader.upload_dataframe(df, "dataset.table", "project-id")
    
    Raises:
        ValueError: 當參數無效時
    """
    
    def upload_dataframe(
        self,
        dataframe: pd.DataFrame,
        table_id: str,
        project_id: str,
        if_exists: str = 'append'
    ) -> None:
        """
        上傳 DataFrame 到 BigQuery。
        
        Args:
            dataframe (pd.DataFrame): 要上傳的資料。
            table_id (str): BigQuery 表格 ID，格式為 'dataset.table'。
            project_id (str): Google Cloud 專案 ID。
            if_exists (str): 當表格已存在時的行為，預設為 'append'。可選值：'fail', 'replace', 'append'。
        
        Examples:
            >>> uploader = BigQueryUploader()
            >>> df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
            >>> uploader.upload_dataframe(df, "dataset.table", "my-project")
        
        Raises:
            ValueError: 當 dataframe 為空或參數無效時
            RuntimeError: 當上傳失敗時
        """
        if dataframe is None or dataframe.empty:
            raise ValueError("dataframe 不可為空")
        if not table_id:
            raise ValueError("table_id 不可為空")
        if not project_id:
            raise ValueError("project_id 不可為空")
        if if_exists not in ['fail', 'replace', 'append']:
            raise ValueError("if_exists 必須是 'fail', 'replace' 或 'append'")
        
        try:
            dataframe.to_gbq(
                table_id,
                if_exists=if_exists,
                project_id=project_id
            )
            print(f"成功上傳 {len(dataframe)} 筆資料到 {table_id}")
        except Exception as e:
            raise RuntimeError(f"上傳資料到 BigQuery 失敗: {e}")
