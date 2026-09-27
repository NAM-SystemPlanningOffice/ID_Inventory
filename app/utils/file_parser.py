import csv
import openpyxl
from typing import List, Dict, Any

class FileParser:
    @staticmethod
    def parse_csv(file_path: str, encoding: str = 'utf-8-sig', has_header: bool = True, skip_rows: int = 0,
                  delimiter: str = ',', quotechar: str = '"') -> List[Dict[str, Any]]:
        """CSVファイルをパース

        Args:
            file_path: ファイルパス
            encoding: エンコーディング（デフォルト: utf-8-sig、複数のエンコーディングを自動試行）
            has_header: ヘッダー行の有無
            skip_rows: スキップする行数
            delimiter: 区切り文字
            quotechar: 引用符文字

        Returns:
            パース結果のリスト
        """
        from app.utils.logger import logger

        # 試行するエンコーディングのリスト（優先順位順）
        encodings_to_try = [
            encoding,           # 指定されたエンコーディング
            'utf-8-sig',       # BOM付きUTF-8
            'utf-8',           # UTF-8
            'cp932',           # Windows日本語（Shift-JIS拡張）
            'shift_jis',       # Shift-JIS
            'iso-2022-jp',     # ISO-2022-JP（日本語メール等）
            'euc-jp',          # EUC-JP
            'latin-1',         # Latin-1（フォールバック）
        ]

        # 重複を削除
        encodings_to_try = list(dict.fromkeys(encodings_to_try))

        last_error = None

        for try_encoding in encodings_to_try:
            try:
                logger.info(f"Trying to parse CSV with encoding: {try_encoding}")
                data = []

                with open(file_path, 'r', encoding=try_encoding, errors='strict') as f:
                    for _ in range(skip_rows):
                        next(f)

                    # delimiterとquotecharを指定してreaderを作成
                    reader = csv.reader(f, delimiter=delimiter, quotechar=quotechar if quotechar else None)
                    headers = None

                    if has_header:
                        headers = next(reader)

                    for row_idx, row in enumerate(reader):
                        if has_header and headers:
                            row_data = {headers[i]: row[i] if i < len(row) else None for i in range(len(headers))}
                        else:
                            row_data = {i: row[i] if i < len(row) else None for i in range(len(row))}
                        data.append(row_data)

                logger.info(f"Successfully parsed CSV with encoding: {try_encoding}, records: {len(data)}")
                return data

            except (UnicodeDecodeError, UnicodeError) as e:
                last_error = e
                logger.debug(f"Failed to parse with encoding {try_encoding}: {str(e)}")
                continue
            except Exception as e:
                # その他のエラーは即座に上げる
                logger.error(f"Unexpected error while parsing CSV with encoding {try_encoding}: {str(e)}")
                raise

        # 全てのエンコーディングで失敗した場合
        error_msg = f"Failed to parse CSV file with any encoding. Last error: {str(last_error)}"
        logger.error(error_msg)
        raise UnicodeDecodeError(
            'multiple_encodings_failed',
            b'',
            0,
            1,
            error_msg
        )

    @staticmethod
    def parse_xlsx(file_path: str, has_header: bool = True, skip_rows: int = 0, sheet_name: str = None) -> List[Dict[str, Any]]:
        wb = openpyxl.load_workbook(file_path, data_only=True)

        if sheet_name:
            ws = wb[sheet_name]
        else:
            ws = wb.active

        rows = list(ws.iter_rows(values_only=True))

        for _ in range(skip_rows):
            if rows:
                rows.pop(0)

        if not rows:
            return []

        data = []
        headers = None

        if has_header:
            headers = rows.pop(0)

        for row_idx, row in enumerate(rows):
            if has_header and headers:
                row_data = {headers[i]: row[i] if i < len(row) else None for i in range(len(headers))}
            else:
                row_data = {i: row[i] if i < len(row) else None for i in range(len(row))}
            data.append(row_data)

        wb.close()
        return data

    @staticmethod
    def parse_file(file_path: str, file_type: str, encoding: str = 'utf-8-sig', has_header: bool = True,
                   skip_rows: int = 0, delimiter: str = ',', quotechar: str = '"', sheet_name: str = None) -> List[Dict[str, Any]]:
        """ファイルをパース

        Args:
            file_path: ファイルパス
            file_type: ファイル種類（csv, xlsx, xls）
            encoding: エンコーディング（CSVの場合、デフォルト: utf-8-sig）
            has_header: ヘッダー行の有無
            skip_rows: スキップする行数
            delimiter: 区切り文字（CSVの場合）
            quotechar: 引用符文字（CSVの場合）
            sheet_name: シート名（Excelの場合）

        Returns:
            パース結果のリスト
        """
        if file_type.lower() == 'csv':
            return FileParser.parse_csv(file_path, encoding, has_header, skip_rows, delimiter, quotechar)
        elif file_type.lower() in ['xlsx', 'xls']:
            return FileParser.parse_xlsx(file_path, has_header, skip_rows, sheet_name)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def transform_data(raw_data: List[Dict[str, Any]], mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
        from datetime import datetime
        from app.utils.logger import logger

        transformed = []

        for row in raw_data:
            transformed_row = {}

            for col_def in mapping['columns']:
                source_col = col_def.get('source_column')
                source_idx = col_def.get('source_index')
                target_col = col_def['target_column']
                data_type = col_def.get('data_type', 'string')
                trim = col_def.get('trim', False)
                transform = col_def.get('transform')

                if source_col is not None:
                    value = row.get(source_col)
                elif source_idx is not None:
                    value = row.get(source_idx)
                else:
                    value = None

                # 必須チェックはvalidators.pyで行うため、ここではチェックしない
                # 値の変換処理のみ実行

                if value is not None:
                    if isinstance(value, str) and trim:
                        value = value.strip()

                    if transform == 'lowercase' and isinstance(value, str):
                        value = value.lower()
                    elif transform == 'uppercase' and isinstance(value, str):
                        value = value.upper()

                    # date型の変換処理
                    if data_type == 'date' and isinstance(value, str) and value.strip():
                        try:
                            # 複数のフォーマットを試行
                            date_formats = [
                                '%Y-%m-%dT%H:%M:%S.%fZ',     # "2026-04-14T03:21:24.000Z" (ISO 8601 with milliseconds and Z)
                                '%Y-%m-%dT%H:%M:%SZ',        # "2026-04-14T03:21:24Z" (ISO 8601 with Z)
                                '%Y-%m-%dT%H:%M:%S.%f',      # "2026-04-14T03:21:24.000" (ISO 8601 with milliseconds)
                                '%Y-%m-%dT%H:%M:%S',         # "2026-04-14T03:21:24" (ISO 8601)
                                '%Y-%m-%d %H:%M:%S.%f',      # "2025-05-15 20:44:55.000"
                                '%Y-%m-%d %H:%M:%S %z',      # "2025-05-15 20:44:55 +0900"
                                '%Y-%m-%d %H:%M:%S',         # "2025-05-15 20:44:55"
                                '%Y-%m-%d',                  # "2025-05-15"
                                '%Y/%m/%d %H:%M:%S',         # "2025/05/15 20:44:55"
                                '%Y/%m/%d',                  # "2025/05/15"
                            ]

                            parsed_date = None
                            for fmt in date_formats:
                                try:
                                    parsed_date = datetime.strptime(value.strip(), fmt)
                                    break
                                except ValueError:
                                    continue

                            if parsed_date:
                                value = parsed_date
                            else:
                                logger.warning(f"Failed to parse date: {value} for column {target_col}")
                                value = None
                        except Exception as e:
                            logger.error(f"Date conversion error for column {target_col}: {value}, error={str(e)}")
                            value = None

                transformed_row[target_col] = value

            transformed.append(transformed_row)

        return transformed
