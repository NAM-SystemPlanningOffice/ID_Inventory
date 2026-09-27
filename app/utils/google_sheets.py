import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from app.config import Config
from app.utils.logger import logger
from typing import List, Dict, Any, Callable
from datetime import datetime
import os
import pickle
import time
import unicodedata

class GoogleSheetsManager:
    """Google Spreadsheet操作クラス（OAuth2認証）"""

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def _call_with_retry(self, func: Callable, *args, max_retries: int = 5, **kwargs):
        """Google Sheets APIのレート制限(429)に対応した呼び出しラッパー

        書き込みリクエストは60回/分に制限されており、超過すると429エラーになる。
        429を検知したら待機してリトライする（指数バックオフ）。

        Args:
            func: 実行するAPI呼び出し関数
            max_retries: 最大リトライ回数
        """
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except gspread.exceptions.APIError as e:
                # 429（レート制限）以外は即座に送出
                status_code = None
                try:
                    status_code = e.response.status_code
                except Exception:
                    pass

                if status_code != 429 or attempt >= max_retries:
                    raise

                # レート制限に達した場合は待機してリトライ
                # クォータは1分単位で回復するため、余裕を持って待機
                wait_seconds = min(60, 20 * (attempt + 1))
                logger.warning(
                    f"Rate limit (429) hit, retrying in {wait_seconds}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_seconds)

    def _open_worksheet(self, spreadsheet_url: str, sheet_name: str):
        """スプレッドシートとワークシートを取得（レート制限リトライ付き）

        読み取りAPI（open_by_url / worksheet）もレート制限(60回/分)の対象のため、
        リトライラッパー経由で取得する。

        Returns:
            (spreadsheet, worksheet) のタプル
        """
        spreadsheet = self._call_with_retry(self.client.open_by_url, spreadsheet_url)
        worksheet = self._call_with_retry(spreadsheet.worksheet, sheet_name)
        return spreadsheet, worksheet

    def __init__(self):
        """OAuth2で認証"""
        try:
            # プロキシ設定を環境変数に設定
            if Config.HTTP_PROXY:
                os.environ['HTTP_PROXY'] = Config.HTTP_PROXY
                logger.info(f"HTTP_PROXY set: {Config.HTTP_PROXY}")
            if Config.HTTPS_PROXY:
                os.environ['HTTPS_PROXY'] = Config.HTTPS_PROXY
                logger.info(f"HTTPS_PROXY set: {Config.HTTPS_PROXY}")

            credentials = None
            token_file = Config.GOOGLE_OAUTH2_TOKEN_FILE

            # token.jsonが存在する場合は読み込む
            if os.path.exists(token_file):
                try:
                    with open(token_file, 'rb') as token:
                        credentials = pickle.load(token)
                    logger.info("Loaded credentials from token file")
                except Exception as e:
                    logger.warning(f"Failed to load token file: {str(e)}")

            # 認証情報が無効または存在しない場合は再認証
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    # トークンをリフレッシュ
                    credentials.refresh(Request())
                    logger.info("Refreshed OAuth2 token")
                else:
                    # 初回認証フロー
                    flow = InstalledAppFlow.from_client_secrets_file(
                        Config.GOOGLE_CREDENTIALS_JSON,
                        self.SCOPES
                    )
                    credentials = flow.run_local_server(port=0)
                    logger.info("Completed OAuth2 authentication flow")

                # トークンを保存
                with open(token_file, 'wb') as token:
                    pickle.dump(credentials, token)
                logger.info(f"Saved credentials to {token_file}")

            self.client = gspread.authorize(credentials)
            logger.info("Google Sheets API authenticated successfully")

        except Exception as e:
            logger.error(f"Failed to authenticate Google Sheets API: {str(e)}")
            raise

    def create_spreadsheet(self, title: str, folder_id: str = None) -> str:
        """新規スプレッドシートを作成

        Args:
            title: スプレッドシート名
            folder_id: 作成先のGoogle DriveフォルダID

        Returns:
            スプレッドシートのURL
        """
        try:
            # タイムスタンプ付きのファイル名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            full_title = f"{title}_{timestamp}"

            # フォルダIDが指定されている場合はそのフォルダに作成
            if folder_id:
                spreadsheet = self.client.create(full_title, folder_id=folder_id)
            else:
                spreadsheet = self.client.create(full_title)

            logger.info(f"Created spreadsheet: {full_title}, ID: {spreadsheet.id}")
            return spreadsheet.url

        except Exception as e:
            logger.error(f"Failed to create spreadsheet: {str(e)}")
            raise

    def write_to_sheet(self, spreadsheet_url: str, sheet_name: str,
                       data: List[List[Any]], start_cell: str = 'A1') -> None:
        """スプレッドシートにデータを書き込み

        Args:
            spreadsheet_url: スプレッドシートのURL
            sheet_name: シート名
            data: 書き込むデータ（2次元配列）
            start_cell: 書き込み開始セル
        """
        try:
            spreadsheet = self._call_with_retry(self.client.open_by_url, spreadsheet_url)

            # シートが存在しない場合は作成
            try:
                worksheet = self._call_with_retry(spreadsheet.worksheet, sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = self._call_with_retry(
                    spreadsheet.add_worksheet, title=sheet_name, rows=1000, cols=26
                )

            # データを書き込み
            self._call_with_retry(worksheet.update, start_cell, data)
            logger.info(f"Wrote {len(data)} rows to sheet: {sheet_name}")

        except Exception as e:
            logger.error(f"Failed to write to sheet: {str(e)}")
            raise

    def create_sheet_with_data(self, title: str, sheets_data: Dict[str, List[List[Any]]],
                               folder_id: str = None, format_header: bool = True) -> str:
        """データ付きスプレッドシートを作成

        Args:
            title: スプレッドシート名
            sheets_data: {シート名: データ}の辞書
            folder_id: 作成先のGoogle DriveフォルダID
            format_header: ヘッダー行をフォーマット（固定・列幅調整含む）するか

        Returns:
            スプレッドシートのURL
        """
        try:
            # スプレッドシート作成
            spreadsheet_url = self.create_spreadsheet(title, folder_id)
            spreadsheet = self._call_with_retry(self.client.open_by_url, spreadsheet_url)

            # デフォルトの"Sheet1"を取得
            default_sheet = self._call_with_retry(lambda: spreadsheet.sheet1)

            # 各シートにデータを書き込み
            for idx, (sheet_name, data) in enumerate(sheets_data.items()):
                # 必要な行数・列数を算出（データ書き込みで範囲不足による切り捨てを防ぐ）
                needed_rows = max(len(data), 100) if data else 100
                needed_cols = max((len(data[0]) if data and len(data) > 0 else 0), 26)

                if idx == 0:
                    # 最初のシートはデフォルトシートを利用
                    worksheet = default_sheet
                    self._call_with_retry(worksheet.update_title, sheet_name)
                    # デフォルトシートのグリッドサイズをデータに合わせて確保
                    # （デフォルトは1000行のため、大量データだと途中で切れるのを防ぐ）
                    if data:
                        self._call_with_retry(worksheet.resize, rows=needed_rows, cols=needed_cols)
                else:
                    # 2つ目以降は新規作成
                    worksheet = self._call_with_retry(
                        spreadsheet.add_worksheet,
                        title=sheet_name,
                        rows=needed_rows,
                        cols=needed_cols
                    )

                if data:
                    self._call_with_retry(worksheet.update, 'A1', data)
                    logger.info(f"Wrote {len(data)} rows to sheet: {sheet_name}")

                    # ヘッダー行のフォーマット（行固定・列幅調整含む）
                    if format_header and len(data) > 0:
                        # データの列数を取得
                        num_cols = len(data[0]) if data and len(data) > 0 else 0
                        self.format_sheet_header(spreadsheet_url, sheet_name,
                                               header_row=1, freeze_rows=1,
                                               auto_resize_columns=True,
                                               num_cols=num_cols)

            return spreadsheet_url

        except Exception as e:
            logger.error(f"Failed to create sheet with data: {str(e)}")
            raise

    @staticmethod
    def _display_width(text: str) -> int:
        """文字列の表示幅を算出（全角=2、半角=1）。改行区切りの場合は最長行の幅を返す"""
        if text is None:
            return 0
        max_width = 0
        for line in str(text).split('\n'):
            width = 0
            for ch in line:
                # 全角判定（East Asian Width: F=全角, W=幅広, A=曖昧は全角扱い）
                width += 2 if unicodedata.east_asian_width(ch) in ('F', 'W', 'A') else 1
            max_width = max(max_width, width)
        return max_width

    def _calc_column_pixel_sizes(self, data: List[List[Any]],
                                 min_px: int = 60, max_px: int = 250,
                                 padding_chars: int = 2) -> List[int]:
        """データ内容から列ごとの適切なピクセル幅を算出する

        各列の最大表示幅（全角=2/半角=1）を基準に、autoResizeより少し広めになるよう
        padding_chars 文字分の余白を加え、min_px～max_px の範囲にクランプする。

        Args:
            data: シートに書き込む2次元配列
            min_px: 最小列幅（px）
            max_px: 最大列幅（px）。これ以上は広げない（折り返しで対応）
            padding_chars: 追加する余白（半角文字数換算）

        Returns:
            列ごとのピクセル幅リスト
        """
        # 半角1文字あたりの目安ピクセル数（デフォルトフォント10ptで約7px）
        px_per_half_char = 7

        num_cols = max((len(row) for row in data), default=0)
        sizes = []
        for col_idx in range(num_cols):
            max_chars = 0
            for row in data:
                if col_idx < len(row):
                    max_chars = max(max_chars, self._display_width(row[col_idx]))
            # 内容幅 + 余白 をピクセルに換算し、上下限でクランプ
            px = (max_chars + padding_chars) * px_per_half_char
            sizes.append(max(min_px, min(max_px, px)))
        return sizes

    def format_sheet_header(self, spreadsheet_url: str, sheet_name: str,
                           header_row: int = 1, freeze_rows: int = 1,
                           auto_resize_columns: bool = True, num_cols: int = None,
                           data: List[List[Any]] = None) -> None:
        """ヘッダー行をフォーマット（太字、背景色、行固定、列幅調整）

        シート全体には上詰め・折り返し表示を設定する（改行区切りの組織情報等が
        セル内で折り返し表示されるようにするため）。

        Args:
            spreadsheet_url: スプレッドシートのURL
            sheet_name: シート名
            header_row: ヘッダー行番号（1-indexed）
            freeze_rows: 固定する行数（デフォルト: 1行目を固定）
            auto_resize_columns: 列幅を自動調整するか（デフォルト: True）
            num_cols: 列数（指定しない場合は自動検出）
            data: シートに書き込んだ2次元配列。指定時は内容の文字数から列幅を算出する
                  （autoResizeが折り返しセルを2文字分程度に潰す問題を避けるため）
        """
        try:
            spreadsheet, worksheet = self._open_worksheet(spreadsheet_url, sheet_name)
            sheet_id = worksheet.id

            # ヘッダー書式・行固定・列幅調整を1回のbatch_updateにまとめる
            # （APIの書き込みリクエスト数を削減し、レート制限(60回/分)超過を防ぐ）
            requests = []

            # シート全体を上詰め・折り返して表示
            # （後続のヘッダー書式が上書きする前提で先頭に配置）
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'verticalAlignment': 'TOP',
                            'wrapStrategy': 'WRAP'
                        }
                    },
                    'fields': 'userEnteredFormat(verticalAlignment,wrapStrategy)'
                }
            })

            # ヘッダー行を太字、背景色を設定（header_rowは1-indexed → 0-indexedに変換）
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': header_row - 1,
                        'endRowIndex': header_row
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.85, 'green': 0.85, 'blue': 0.85}
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                }
            })

            # 行固定
            if freeze_rows > 0:
                requests.append({
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'gridProperties': {'frozenRowCount': freeze_rows}
                        },
                        'fields': 'gridProperties.frozenRowCount'
                    }
                })

            # 列数が指定されていない場合は自動検出
            if num_cols is None:
                if data:
                    num_cols = max((len(row) for row in data), default=0)
                else:
                    first_row = self._call_with_retry(worksheet.row_values, 1)
                    num_cols = len(first_row) if first_row else 0

            # 【列幅】データ内容の文字数から列ごとに幅を算出して設定する
            # autoResize（API/GAS）は折り返しセルを2文字分程度まで潰してしまうため、
            # 内容の最大文字数（全角=2/半角=1）＋余白から幅を決め、上限250pxでクランプする。
            if auto_resize_columns and num_cols > 0 and data:
                col_sizes = self._calc_column_pixel_sizes(data)
                for col_idx, px in enumerate(col_sizes):
                    requests.append({
                        'updateDimensionProperties': {
                            'range': {
                                'sheetId': sheet_id,
                                'dimension': 'COLUMNS',
                                'startIndex': col_idx,
                                'endIndex': col_idx + 1
                            },
                            'properties': {'pixelSize': px},
                            'fields': 'pixelSize'
                        }
                    })
            elif auto_resize_columns and num_cols > 0:
                # dataが渡されない場合は従来通り全列250pxで統一（折り返し前提の安全側）
                requests.append({
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': num_cols
                        },
                        'properties': {'pixelSize': 250},
                        'fields': 'pixelSize'
                    }
                })

            # 【行高】行高のみ最適化する（列幅と同じbatch_updateにまとめてAPI呼び出しを削減）
            # 列幅は上でupdateDimensionPropertiesで固定値を設定しており、
            # 列のauto-resizeは行わないため、行高の最適化と同一batchでも列幅は保持される。
            if auto_resize_columns and num_cols > 0:
                requests.append({
                    'autoResizeDimensions': {
                        'dimensions': {
                            'sheetId': sheet_id,
                            'dimension': 'ROWS',
                            'startIndex': 0,
                            'endIndex': worksheet.row_count
                        }
                    }
                })

            # ヘッダー書式・行固定・列幅・行高を1回のbatch_updateで一括適用
            # （書き込みリクエスト数を減らし、レート制限(60回/分)超過を抑制する）
            if requests:
                self._call_with_retry(spreadsheet.batch_update, {'requests': requests})

            logger.info(f"Formatted header row in sheet: {sheet_name}")

        except Exception as e:
            logger.error(f"Failed to format sheet header: {str(e)}")
            # フォーマットエラーは致命的ではないので続行

    def format_confirmation_sheet(self, spreadsheet_url: str, sheet_name: str, num_systems: int) -> None:
        """確認シートをフォーマット（棚卸リスト用、PDFフォーマット準拠）

        Args:
            spreadsheet_url: スプレッドシートのURL
            sheet_name: シート名（通常「確認」）
            num_systems: システム数
        """
        try:
            spreadsheet, worksheet = self._open_worksheet(spreadsheet_url, sheet_name)
            sheet_id = worksheet.id

            # バッチリクエストを準備
            requests = []

            # 行1: タイトル行を太字・フォント14（B列から）
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 1,
                        'endColumnIndex': 8
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'fontSize': 14, 'bold': True}
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat'
                }
            })

            # 行3: ヘッダー行を太字・背景色・中央揃え
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 2,
                        'endRowIndex': 3,
                        'startColumnIndex': 0,
                        'endColumnIndex': 8
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.85, 'green': 0.85, 'blue': 0.85},
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'TOP',
                            'wrapStrategy': 'WRAP'
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy)'
                }
            })

            # 行4～(3+num_systems): メイン表のデータ行を上詰め・折り返し
            end_row = 3 + num_systems
            if num_systems > 0:
                requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 3,
                            'endRowIndex': end_row,
                            'startColumnIndex': 0,
                            'endColumnIndex': 8
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'verticalAlignment': 'TOP',
                                'wrapStrategy': 'WRAP'
                            }
                        },
                        'fields': 'userEnteredFormat(verticalAlignment,wrapStrategy)'
                    }
                })

            # 行3～(3+num_systems): メイン表に罫線を引く
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 2,
                        'endRowIndex': end_row,
                        'startColumnIndex': 0,
                        'endColumnIndex': 8
                    },
                    'top': {'style': 'SOLID', 'width': 1},
                    'bottom': {'style': 'SOLID', 'width': 1},
                    'left': {'style': 'SOLID', 'width': 1},
                    'right': {'style': 'SOLID', 'width': 1},
                    'innerHorizontal': {'style': 'SOLID', 'width': 1},
                    'innerVertical': {'style': 'SOLID', 'width': 1}
                }
            })

            # 下部の小さな表のヘッダー行（メイン表の後、2行空けた位置）
            bottom_table_header_row = end_row + 2
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': bottom_table_header_row,
                        'endRowIndex': bottom_table_header_row + 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': 5
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.85, 'green': 0.85, 'blue': 0.85},
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE'
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor,horizontalAlignment,verticalAlignment)'
                }
            })

            # 下部の小さな表に罫線を引く（ヘッダー + 5行のデータ）
            bottom_table_end_row = bottom_table_header_row + 6
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': bottom_table_header_row,
                        'endRowIndex': bottom_table_end_row,
                        'startColumnIndex': 0,
                        'endColumnIndex': 5
                    },
                    'top': {'style': 'SOLID', 'width': 1},
                    'bottom': {'style': 'SOLID', 'width': 1},
                    'left': {'style': 'SOLID', 'width': 1},
                    'right': {'style': 'SOLID', 'width': 1},
                    'innerHorizontal': {'style': 'SOLID', 'width': 1},
                    'innerVertical': {'style': 'SOLID', 'width': 1}
                }
            })

            # 下部の小さな表: A列のセル結合（システム: IM_ROLE）
            bottom_table_data_start = bottom_table_header_row + 1
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': bottom_table_data_start,
                        'endRowIndex': bottom_table_data_start + 5,
                        'startColumnIndex': 0,
                        'endColumnIndex': 1
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })

            # 下部の小さな表: B列のセル結合（確認頻度: 年次（5月））
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': bottom_table_data_start,
                        'endRowIndex': bottom_table_data_start + 5,
                        'startColumnIndex': 1,
                        'endColumnIndex': 2
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })

            # セル結合したセルを中央揃えに
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': bottom_table_data_start,
                        'endRowIndex': bottom_table_data_start + 5,
                        'startColumnIndex': 0,
                        'endColumnIndex': 2
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE'
                        }
                    },
                    'fields': 'userEnteredFormat(horizontalAlignment,verticalAlignment)'
                }
            })

            # 列幅を調整
            # A列（システム名）: 180px
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 1
                    },
                    'properties': {
                        'pixelSize': 180
                    },
                    'fields': 'pixelSize'
                }
            })

            # B～E列（確認頻度、確認担当、確認状況、対応）: 120px
            for col_idx in range(1, 5):
                requests.append({
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': col_idx,
                            'endIndex': col_idx + 1
                        },
                        'properties': {
                            'pixelSize': 120
                        },
                        'fields': 'pixelSize'
                    }
                })

            # F～H列（出力範囲、確認ポイント、備考）: 250px
            for col_idx in range(5, 8):
                requests.append({
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': col_idx,
                            'endIndex': col_idx + 1
                        },
                        'properties': {
                            'pixelSize': 250
                        },
                        'fields': 'pixelSize'
                    }
                })

            # 行3を固定（ヘッダー行まで）
            requests.append({
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'gridProperties': {
                            'frozenRowCount': 3
                        }
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            })

            # 一括実行
            self._call_with_retry(spreadsheet.batch_update, {'requests': requests})
            logger.info(f"Formatted confirmation sheet: {sheet_name}")

        except Exception as e:
            logger.error(f"Failed to format confirmation sheet: {str(e)}")
            # フォーマットエラーは致命的ではないので続行

    def format_tenshutu_confirmation_sheet(self, spreadsheet_url: str, sheet_name: str,
                                          target_date: str, num_systems: int) -> None:
        """組織転出者アクセス権限確認リストの確認シートをフォーマット

        Args:
            spreadsheet_url: スプレッドシートのURL
            sheet_name: シート名（通常「確認」）
            target_date: 転出日（YYYY-MM-DD形式）
            num_systems: システム数
        """
        try:
            spreadsheet, worksheet = self._open_worksheet(spreadsheet_url, sheet_name)
            sheet_id = worksheet.id

            # バッチリクエストを準備
            requests = []

            # A1:G1をセル結合して表題を中央寄せ・太字・フォント14
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': 7
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })

            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': 7
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'fontSize': 14, 'bold': True},
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE'
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment'
                }
            })

            # G3:G5（確認の枠と下の空白セル）を罫線で囲む
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 2,
                        'endRowIndex': 5,
                        'startColumnIndex': 6,
                        'endColumnIndex': 7
                    },
                    'top': {'style': 'SOLID', 'width': 1},
                    'bottom': {'style': 'SOLID', 'width': 1},
                    'left': {'style': 'SOLID', 'width': 1},
                    'right': {'style': 'SOLID', 'width': 1},
                    'innerHorizontal': {'style': 'SOLID', 'width': 1}
                }
            })

            # セル結合: G4:G5（確認の下の空白セル）
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 3,
                        'endRowIndex': 5,
                        'startColumnIndex': 6,
                        'endColumnIndex': 7
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })

            # 行7:行8（ヘッダー）を太字・中央寄せ・上詰め・折り返し
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 6,
                        'endRowIndex': 8,
                        'startColumnIndex': 0,
                        'endColumnIndex': 7
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'TOP',
                            'wrapStrategy': 'WRAP'
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)'
                }
            })

            # セル結合: A7:A8（システム列のヘッダー）
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 6,
                        'endRowIndex': 8,
                        'startColumnIndex': 0,
                        'endColumnIndex': 1
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })

            # セル結合: B7:C7（継続要否確認）
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 6,
                        'endRowIndex': 7,
                        'startColumnIndex': 1,
                        'endColumnIndex': 3
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })

            # セル結合: D7:G7（権限削除等作業欄）
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 6,
                        'endRowIndex': 7,
                        'startColumnIndex': 3,
                        'endColumnIndex': 7
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })

            # 行9以降（システム名の行）を上詰め・折り返し
            end_row = 8 + num_systems
            if num_systems > 0:
                requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 8,
                            'endRowIndex': end_row,
                            'startColumnIndex': 0,
                            'endColumnIndex': 7
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'verticalAlignment': 'TOP',
                                'wrapStrategy': 'WRAP'
                            }
                        },
                        'fields': 'userEnteredFormat(verticalAlignment,wrapStrategy)'
                    }
                })

            # 行7以降（システム名の行）に罫線を引く
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 6,
                        'endRowIndex': end_row,
                        'startColumnIndex': 0,
                        'endColumnIndex': 7
                    },
                    'top': {'style': 'SOLID', 'width': 1},
                    'bottom': {'style': 'SOLID', 'width': 1},
                    'left': {'style': 'SOLID', 'width': 1},
                    'right': {'style': 'SOLID', 'width': 1},
                    'innerHorizontal': {'style': 'SOLID', 'width': 1},
                    'innerVertical': {'style': 'SOLID', 'width': 1}
                }
            })

            # 列幅を調整（A列: 120px、B～G列: 100px）
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 1
                    },
                    'properties': {
                        'pixelSize': 120
                    },
                    'fields': 'pixelSize'
                }
            })

            # B～G列の幅を調整
            for col_index in range(1, 7):
                requests.append({
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': col_index,
                            'endIndex': col_index + 1
                        },
                        'properties': {
                            'pixelSize': 100
                        },
                        'fields': 'pixelSize'
                    }
                })

            # 一括実行
            self._call_with_retry(spreadsheet.batch_update, {'requests': requests})
            logger.info(f"Formatted tenshutu confirmation sheet: {sheet_name}")

        except Exception as e:
            logger.error(f"Failed to format tenshutu confirmation sheet: {str(e)}")
            # フォーマットエラーは致命的ではないので続行

    def format_taishoku_sheet(self, spreadsheet_url: str, sheet_name: str, num_systems: int, num_users: int, shaded_cells: list = None, status_rows: list = None) -> None:
        """退職者ID削除依頼書シートをフォーマット（PDFと同じ形式）

        Args:
            spreadsheet_url: スプレッドシートのURL
            sheet_name: シート名
            num_systems: システム数
            num_users: 退職者数
            shaded_cells: 網掛けするセルのリスト [(row_index, col_index), ...]
            status_rows: ステータス行のインデックスリスト [row_index, ...]
        """
        if shaded_cells is None:
            shaded_cells = []
        if status_rows is None:
            status_rows = []
        try:
            spreadsheet, worksheet = self._open_worksheet(spreadsheet_url, sheet_name)
            sheet_id = worksheet.id

            # バッチリクエストを準備
            requests = []

            # 表全体を左右・上下ともにセンタリング、折り返して表示
            # （後続の個別フォーマット（タイトル・ヘッダー・網掛け等）が上書きする前提で先頭に配置）
            # 総行数 = ヘッダー6行 + データ(num_users*2)行 + 空白1行 + 作業3行
            total_rows = 6 + num_users * 2 + 1 + 3
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': total_rows,
                        'startColumnIndex': 0,
                        'endColumnIndex': num_systems + 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE',
                            'wrapStrategy': 'WRAP'
                        }
                    },
                    'fields': 'userEnteredFormat(horizontalAlignment,verticalAlignment,wrapStrategy)'
                }
            })

            # 行1: タイトル行
            # A1から(num_systems)列目までを結合してタイトル「退職者（産休）ID削除依頼書」を表示
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': num_systems
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })

            # タイトル行を太字・大きく・中央揃え
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': num_systems
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True, 'fontSize': 14},
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE'
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment)'
                }
            })

            # L1（明細行右端）に「室長(課長)確認」を配置し、網掛け・中央揃え
            # A列=USER_CD (index 0), B列～L列=システム11個 (index 1～11)
            # L列 = index 11 = num_systems
            confirm_col = num_systems  # 0-indexed（L列）
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,  # 行1
                        'endRowIndex': 1,
                        'startColumnIndex': confirm_col,
                        'endColumnIndex': confirm_col + 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.8, 'green': 0.85, 'blue': 0.9},
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE',
                            'wrapStrategy': 'WRAP'
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy)'
                }
            })

            # L1に罫線
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,  # 行1
                        'endRowIndex': 1,
                        'startColumnIndex': confirm_col,
                        'endColumnIndex': confirm_col + 1
                    },
                    'top': {'style': 'SOLID', 'width': 1},
                    'bottom': {'style': 'SOLID', 'width': 1},
                    'left': {'style': 'SOLID', 'width': 1},
                    'right': {'style': 'SOLID', 'width': 1}
                }
            })

            # L2-L3（室長確認欄の下2つのセル）に外側だけの罫線
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 1,  # 行2
                        'endRowIndex': 3,    # 行3まで
                        'startColumnIndex': confirm_col,
                        'endColumnIndex': confirm_col + 1
                    },
                    'top': {'style': 'SOLID', 'width': 1},
                    'bottom': {'style': 'SOLID', 'width': 1},
                    'left': {'style': 'SOLID', 'width': 1},
                    'right': {'style': 'SOLID', 'width': 1}
                }
            })

            # 行5-6: メインテーブルヘッダーを太字、中央揃え、網掛け（青みがかった色）
            # 行5: USER_CD、システム名、室長(課長)確認
            # 行6: 名　前、対処不要は...（B列以降を結合）

            # 行5（USER_CD、各システム名）
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 4,  # 行5
                        'endRowIndex': 5,
                        'startColumnIndex': 0,
                        'endColumnIndex': num_systems + 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.8, 'green': 0.85, 'blue': 0.9},
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE',
                            'wrapStrategy': 'WRAP'
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy)'
                }
            })

            # 行6のA列（名　前）: 網掛けあり
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 5,  # 行6
                        'endRowIndex': 6,
                        'startColumnIndex': 0,  # A列
                        'endColumnIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.8, 'green': 0.85, 'blue': 0.9},
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE',
                            'wrapStrategy': 'WRAP'
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy)'
                }
            })

            # 行6のB列以降（対処不要は...）: 網掛けなし（白背景）
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 5,  # 行6
                        'endRowIndex': 6,
                        'startColumnIndex': 1,  # B列から
                        'endColumnIndex': num_systems + 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE',
                            'wrapStrategy': 'WRAP'
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy)'
                }
            })

            # 行6のB列以降をセル結合
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 5,  # 行6
                        'endRowIndex': 6,
                        'startColumnIndex': 1,  # B列から
                        'endColumnIndex': num_systems + 1
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })


            # A列を網掛け（データ行のみ、ヘッダーは既に網掛け済み）（青みがかった色）
            data_start_row = 6  # 0-indexed（7行目）
            if num_users > 0:
                requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': data_start_row,
                            'endRowIndex': data_start_row + num_users * 2,
                            'startColumnIndex': 0,  # A列
                            'endColumnIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.8, 'green': 0.85, 'blue': 0.9}
                            }
                        },
                        'fields': 'userEnteredFormat.backgroundColor'
                    }
                })

            # データ行（各ユーザー2行1セット）の各システム列に中央揃えを設定
            if num_users > 0:
                requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': data_start_row,
                            'endRowIndex': data_start_row + num_users * 2,
                            'startColumnIndex': 1,
                            'endColumnIndex': num_systems + 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'horizontalAlignment': 'CENTER'
                            }
                        },
                        'fields': 'userEnteredFormat.horizontalAlignment'
                    }
                })

            # ステータス行（各明細の1行目）を網掛け（青みがかった色）
            for row_idx in status_rows:
                requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': row_idx,
                            'endRowIndex': row_idx + 1,
                            'startColumnIndex': 1,  # B列から
                            'endColumnIndex': num_systems + 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.8, 'green': 0.85, 'blue': 0.9}
                            }
                        },
                        'fields': 'userEnteredFormat.backgroundColor'
                    }
                })

            # 網掛けセルに背景色を設定（青みがかった色、作業不要な列）
            # 中央揃えも同時に設定
            for row_idx, col_idx in shaded_cells:
                requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': row_idx,
                            'endRowIndex': row_idx + 1,
                            'startColumnIndex': col_idx,
                            'endColumnIndex': col_idx + 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.8, 'green': 0.85, 'blue': 0.9},
                                'horizontalAlignment': 'CENTER'
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,horizontalAlignment)'
                    }
                })

            # 6行目を固定（ヘッダー2行分）
            requests.append({
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'gridProperties': {
                            'frozenRowCount': 6
                        }
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            })

            # ヘッダー行（行5-6）に罫線を引く（2行1セット）
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 4,  # 行5
                        'endRowIndex': 6,    # 行6まで
                        'startColumnIndex': 0,
                        'endColumnIndex': num_systems + 1
                    },
                    'top': {'style': 'SOLID', 'width': 1},
                    'bottom': {'style': 'SOLID', 'width': 1},
                    'left': {'style': 'SOLID', 'width': 1},
                    'right': {'style': 'SOLID', 'width': 1},
                    'innerVertical': {'style': 'SOLID', 'width': 1}
                }
            })

            # データ行（各ユーザー2行1セット）に罫線を引く
            if num_users > 0:
                for user_idx in range(num_users):
                    row_start = data_start_row + user_idx * 2
                    row_end = row_start + 2  # 2行分

                    requests.append({
                        'updateBorders': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': row_start,
                                'endRowIndex': row_end,
                                'startColumnIndex': 0,
                                'endColumnIndex': num_systems + 1
                            },
                            'top': {'style': 'SOLID', 'width': 1},
                            'bottom': {'style': 'SOLID', 'width': 1},
                            'left': {'style': 'SOLID', 'width': 1},
                            'right': {'style': 'SOLID', 'width': 1},
                            'innerVertical': {'style': 'SOLID', 'width': 1}
                        }
                    })

            # 作業担当・再査担当・実施日の3行に罫線を引く
            # 明細行と作業担当行の間に1行空白行があるため、+1する
            work_rows_start = data_start_row + num_users * 2 + 1

            # 作業担当行（1行）
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': work_rows_start,
                        'endRowIndex': work_rows_start + 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': num_systems + 1
                    },
                    'top': {'style': 'SOLID', 'width': 1},
                    'bottom': {'style': 'SOLID', 'width': 1},
                    'left': {'style': 'SOLID', 'width': 1},
                    'right': {'style': 'SOLID', 'width': 1},
                    'innerVertical': {'style': 'SOLID', 'width': 1}
                }
            })

            # 再査担当・実施日（2行1セット）- 2行の間の横罫線は引かない
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': work_rows_start + 1,
                        'endRowIndex': work_rows_start + 3,  # 2行分
                        'startColumnIndex': 0,
                        'endColumnIndex': num_systems + 1
                    },
                    'top': {'style': 'SOLID', 'width': 1},
                    'bottom': {'style': 'SOLID', 'width': 1},
                    'left': {'style': 'SOLID', 'width': 1},
                    'right': {'style': 'SOLID', 'width': 1},
                    'innerVertical': {'style': 'SOLID', 'width': 1}
                }
            })

            # A列を若干広く（120ピクセル）
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 1
                    },
                    'properties': {
                        'pixelSize': 120
                    },
                    'fields': 'pixelSize'
                }
            })

            # B列以降（システム列）を100ピクセルに
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 1,
                        'endIndex': num_systems + 1
                    },
                    'properties': {
                        'pixelSize': 100
                    },
                    'fields': 'pixelSize'
                }
            })

            # 一括実行
            self._call_with_retry(spreadsheet.batch_update, {'requests': requests})
            logger.info(f"Formatted taishoku sheet: {sheet_name}, systems={num_systems}, users={num_users}")

        except Exception as e:
            logger.error(f"Failed to format taishoku sheet: {str(e)}")
            # フォーマットエラーは致命的ではないので続行
