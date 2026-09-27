from typing import Dict, Any, List
from app.repositories.system_repository import SystemRepository
from app.repositories.user_repository import UserRepository
from app.utils.db import get_db_connection
from app.utils.logger import logger
from app.utils.google_sheets import GoogleSheetsManager
from app.config import Config
from app.services.tenshutu_service import TenshutuService
# safe_eval_disabled_condition は不要（SQL式に変更）
from datetime import datetime

class OutputService:
    """リスト出力サービス"""

    def get_taishoku_ido_dates(self) -> List[Dict[str, Any]]:
        """過去60日間の退職・異動日のリストを取得

        Returns:
            日付リスト（退職・異動件数含む）
        """
        with get_db_connection() as conn:
            user_repo = UserRepository(conn)
            return user_repo.get_taishoku_ido_dates()

    def generate_tanaoroshi_list(self) -> Dict[str, Any]:
        """棚卸リストを生成（現時点の状態）

        Returns:
            生成結果（Google SpreadsheetのURL等）
        """
        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            user_repo = UserRepository(conn)

            # 出力対象システム取得
            systems = system_repo.find_all(active_only=True)
            output_systems = [s for s in systems if s.output_required]
            output_systems.sort(key=lambda s: (s.output_order or 999, s.system_id))

            # 各システムのユーザーデータ取得
            system_data_list = []
            for system in output_systems:
                try:
                    # システムユーザーデータ取得（在籍情報とJOINして判定、ソートもSQLで実施）
                    output_users = user_repo.get_system_users_with_zaiseki_flag(
                        system.system_id,
                        import_table_name=system.import_table_name,
                        import_method=system.import_method,
                        filter_sql=system.tanaoroshi_filter_sql,
                        output_mode=system.tanaoroshi_output_mode,
                        sort_sql=system.tanaoroshi_sort_sql
                    )

                    # 統計情報をログ出力
                    total_users = len(output_users)
                    matched_count = sum(1 for u in output_users if u.get('IS_ZAISEKI_MATCH') == 1)
                    unmatched_count = total_users - matched_count

                    logger.info(f"[{system.system_id}] mode={system.tanaoroshi_output_mode}, total={total_users}, matched={matched_count}, unmatched={unmatched_count}")

                    system_data_list.append({
                        'system': system,
                        'total_users': total_users,
                        'mismatches': output_users
                    })

                except Exception as e:
                    logger.error(f"Failed to get system users: {system.system_id}, error={str(e)}")
                    system_data_list.append({
                        'system': system,
                        'total_users': 0,
                        'mismatches': [],
                        'error': str(e)
                    })

            # エラーが発生したシステムを収集（システム名 + エラー内容）
            error_systems = [
                {
                    'system_id': s['system'].system_id,
                    'system_name': s['system'].system_name or s['system'].system_id,
                    'error': s['error']
                }
                for s in system_data_list if s.get('error')
            ]

            # Google Spreadsheetに出力
            sheets_data = {}
            for system_data in system_data_list:
                system = system_data['system']
                mismatches = system_data['mismatches']

                if not mismatches:
                    continue

                # tanaoroshi_output_columnsから出力項目を取得
                output_columns = system.tanaoroshi_output_columns
                if not output_columns or 'columns' not in output_columns:
                    logger.warning(f"No tanaoroshi_output_columns defined for system: {system.system_id}, using default columns")
                    # デフォルトのヘッダー（後方互換性）
                    header = ['ユーザーCD', 'ユーザー名', '所属', '本務', '兼務']
                    column_defs = None
                else:
                    # 出力カラム定義を取得してソート
                    column_defs = sorted(
                        output_columns['columns'],
                        key=lambda x: x.get('order', 999)
                    )
                    header = []

                    # カラム定義に従ってヘッダーを生成
                    for col_def in column_defs:
                        header.append(col_def.get('display_name', col_def['column_name']))

                rows = [header]

                # ソートはSQL側（ORDER BY）で実施済み
                # データ行
                for user in mismatches:
                    user_cd = user.get('USER_CD', '')

                    row = []

                    # カラム定義に従ってデータを追加
                    if column_defs:
                        for col_def in column_defs:
                            col_name = col_def['column_name']
                            source = col_def.get('source', 'system')  # デフォルトはsystem

                            if source == 'zaiseki':
                                # 在籍ユーザー情報から取得（ZAISEKI_プレフィックス付き）
                                zaiseki_col_name = f'ZAISEKI_{col_name}'
                                row.append(user.get(zaiseki_col_name, ''))
                            else:
                                # システムユーザー情報から取得
                                row.append(user.get(col_name, ''))
                    else:
                        # デフォルト（後方互換性）
                        row = [
                            user_cd,
                            user.get('USER_NAME', ''),
                            user.get('ZAISEKI_SHOZOKU', ''),
                            user.get('ZAISEKI_HONMU', ''),
                            user.get('ZAISEKI_KENMU', '')
                        ]

                    rows.append(row)

                sheet_name = system.output_sheet_name or system.system_name
                # シート名の長さ制限（31文字）
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[:31]

                sheets_data[sheet_name] = rows

            # 確認シートを先頭に追加（システム情報を渡す）
            # 確認担当（CHECK_RESPONSIBLE=USER_CD）の氏名を解決
            responsible_names = system_repo.get_user_names_by_cds(
                [s.check_responsible for s in output_systems]
            )
            confirmation_sheet = self._create_confirmation_sheet(output_systems, responsible_names)

            # 確認シートに出力されるシステム数を計算（確認頻度が「不要」以外）
            confirmation_system_count = sum(1 for s in output_systems if s.check_frequency != 'NONE')

            # 確認シートを先頭に挿入
            ordered_sheets_data = {'確認': confirmation_sheet}
            ordered_sheets_data.update(sheets_data)

            # スプレッドシート作成
            try:
                gs_manager = GoogleSheetsManager()
                spreadsheet_url = gs_manager.create_sheet_with_data(
                    title='ユーザー棚卸リスト',
                    sheets_data=ordered_sheets_data,
                    folder_id=Config.GOOGLE_DRIVE_FOLDER_ID,
                    format_header=False
                )

                # 確認シートをフォーマット（確認シートに出力されるシステム数を渡す）
                gs_manager.format_confirmation_sheet(spreadsheet_url, '確認', confirmation_system_count)

                # 各システムシートのヘッダー行をフォーマット（内容から列幅を算出するためdataを渡す）
                for sheet_name, sheet_data in sheets_data.items():
                    gs_manager.format_sheet_header(spreadsheet_url, sheet_name, data=sheet_data)

                logger.info(f"Created tanaoroshi spreadsheet: {spreadsheet_url}")

                # エラーが発生したシステムがあれば、成功メッセージに警告を付加
                if error_systems:
                    message = (f'棚卸リストを生成しました（ただし{len(error_systems)}件のシステムで'
                               f'SQLエラーが発生し、シート出力されていません）')
                    status = 'warning'
                else:
                    message = '棚卸リストを生成しました'
                    status = 'success'

                return {
                    'status': status,
                    'message': message,
                    'url': spreadsheet_url,
                    'systems_count': len(system_data_list),
                    'total_mismatches': sum(len(s['mismatches']) for s in system_data_list),
                    'error_systems': error_systems
                }

            except Exception as e:
                logger.error(f"Failed to create spreadsheet: {str(e)}")
                return {
                    'status': 'error',
                    'message': f'スプレッドシート作成に失敗しました: {str(e)}'
                }

    def generate_taishoku_list(self, target_date: str) -> Dict[str, Any]:
        """退職者ID削除依頼書を生成（2行形式・動的SQL）

        Args:
            target_date: 対象日（YYYY-MM-DD形式）

        Returns:
            生成結果
        """
        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            user_repo = UserRepository(conn)

            # 退職時出力要のシステム取得（OUTPUT_ORDER順）
            systems = system_repo.find_all(active_only=True)
            output_systems = [s for s in systems if s.taishoku_output_required]
            output_systems.sort(key=lambda s: (s.output_order or 999, s.system_id))

            if not output_systems:
                return {
                    'status': 'error',
                    'message': '退職時出力対象のシステムが設定されていません'
                }

            # 退職者情報を各システムの表示SQLと共に取得（動的SQL）
            try:
                taishoku_data = user_repo.get_taishoku_users_with_systems(target_date, output_systems)
            except Exception as e:
                logger.error(f"Failed to get taishoku users with systems: {str(e)}")
                return {
                    'status': 'error',
                    'message': f'退職者データ取得でSQLエラーが発生しました（システム定義の退職者表示SQL・無効化判定式を確認してください）: {str(e)}',
                    'url': None
                }

            # 退職者が0件の場合はスプレッドシートを作成しない
            if not taishoku_data:
                logger.info(f"No taishoku users found for date: {target_date}")
                return {
                    'status': 'success',
                    'message': f'{target_date}に退職者がいないため、退職者ID削除依頼書は作成されませんでした',
                    'url': None,
                    'taishoku_count': 0
                }

            # PDFと同じヘッダー構造を生成
            from datetime import datetime

            # 退社日をフォーマット
            taisha_date_formatted = datetime.strptime(target_date, '%Y-%m-%d').strftime('%Y/%m/%d')
            output_date = datetime.now().strftime('%Y/%m/%d')

            rows = []

            # 行1: タイトル「退職者（産休）ID削除依頼書」を中央寄せ、出力日をもう2つ左に配置
            # L列（明細行右端）に「室長(課長)確認」を配置
            title_row = (['退職者（産休）ID削除依頼書'] + [''] * (len(output_systems) - 3) +
                        ['出力日', output_date, '室長(課長)確認'])
            rows.append(title_row)

            # 行2: 空行
            rows.append([''] * (len(output_systems) + 3))

            # 行3: 退社日情報
            row3 = ['退社(産休開始)日', taisha_date_formatted] + [''] * (len(output_systems) + 1)
            rows.append(row3)

            # 行4: 注意書き
            row4 = ['退社日は一日後ろにずれます', ''] + [''] * (len(output_systems) + 1)
            rows.append(row4)

            # 行5: メインテーブルヘッダー1行目（USER_CD、各システム名）
            header1 = ['USER_CD'] + [system.system_name for system in output_systems]
            rows.append(header1)

            # 行6: メインテーブルヘッダー2行目（名　前、対処不要は...）
            header2_text = '対処不要は　"ー"　　削除または無効化実施済の場合は実施日入力'
            header2 = ['名　前', header2_text] + [''] * (len(output_systems) - 1)
            rows.append(header2)

            # データ行（1ユーザーあたり2行）
            # 網掛け情報を記録（行番号とカラムインデックス）
            shaded_cells = []  # [(row_index, col_index), ...]
            status_rows = []  # ステータス行（1行目）のインデックス

            data_start_row = len(rows)  # データ開始行（0-indexed、6行目）

            for user_idx, record in enumerate(taishoku_data):
                user_cd = record.get('USER_CD', '')
                user_name = record.get('USER_NAME', '')

                # 1行目: USER_CD, 各システムのステータス
                row1 = [user_cd]

                # 2行目: USER_NAME, 各システムの作業状況（'ー' or 空欄）
                row2 = [user_name]

                # 各システムの列データを追加
                for col_idx, system in enumerate(output_systems):
                    system_id_upper = system.system_id.upper()

                    # DISPLAY_VALUEを1行目に表示
                    display_key = f"SYS_{system_id_upper}_DISPLAY_VALUE"
                    display_value = record.get(display_key, '')
                    row1.append(display_value)

                    # DISABLED_VALUEを2行目に表示
                    # SQLで'-'が返ってきた場合は無効化済み、NULLの場合は作業必要（空欄）
                    disabled_key = f"SYS_{system_id_upper}_DISABLED_VALUE"
                    disabled_value = record.get(disabled_key)

                    if disabled_value == '－' or disabled_value == '-':
                        row2.append('－')
                        # 網掛け対象として記録（2行目、列はB列=1から始まる）
                        row2_index = data_start_row + user_idx * 2 + 1  # 0-indexed
                        col_index = 1 + col_idx  # 0-indexed（A=0, B=1, ...）
                        shaded_cells.append((row2_index, col_index))
                    else:
                        row2.append('')  # NULL or その他 → 空欄（作業必要）

                # ステータス行のインデックスを記録（網掛け用）
                row1_index = data_start_row + user_idx * 2
                status_rows.append(row1_index)

                rows.append(row1)
                rows.append(row2)

            # 明細行と作業担当行の間に空白行を挿入
            rows.append([''] * (len(output_systems) + 1))

            # 各システムが作業不要かどうかを判定（全ユーザーの2行目が「－」かをチェック）
            work_required_by_system = []  # 各システムが作業必要かどうか
            for col_idx, system in enumerate(output_systems):
                system_id_upper = system.system_id.upper()
                disabled_key = f"SYS_{system_id_upper}_DISABLED_VALUE"

                # 全ユーザーについて、このシステムの作業状況を確認
                all_disabled = all(
                    record.get(disabled_key) in ['－', '-']
                    for record in taishoku_data
                )
                work_required_by_system.append(not all_disabled)  # 全員無効化済み → 作業不要

            # 表の下部に作業担当・再査担当・実施日の3行を追加
            work_row_labels = ['作業 担当', '再査 担当', '　　実施日']

            for label in work_row_labels:
                row = [label]
                for col_idx, system in enumerate(output_systems):
                    if work_required_by_system[col_idx]:
                        # 作業必要 → 空欄
                        row.append('')
                    else:
                        # 作業不要 → 「－」を表示し網掛け
                        row.append('－')
                        # 網掛け対象として記録
                        row_index = len(rows)
                        col_index = 1 + col_idx  # 0-indexed（A=0, B=1, ...）
                        shaded_cells.append((row_index, col_index))

                # A列（ラベル列）も網掛け対象として記録
                row_index = len(rows)
                shaded_cells.append((row_index, 0))  # A列

                rows.append(row)

            # Google Spreadsheetに出力（1シート）
            try:
                gs_manager = GoogleSheetsManager()
                sheets_data = {'退職者一覧': rows}

                spreadsheet_url = gs_manager.create_sheet_with_data(
                    title=f'退職者ID削除依頼書_{target_date}',
                    sheets_data=sheets_data,
                    folder_id=Config.GOOGLE_DRIVE_FOLDER_ID,
                    format_header=False
                )

                # 退職者ID削除依頼書専用フォーマット（2行固定、日付形式、網掛け）
                gs_manager.format_taishoku_sheet(
                    spreadsheet_url,
                    '退職者一覧',
                    num_systems=len(output_systems),
                    num_users=len(taishoku_data),
                    shaded_cells=shaded_cells,
                    status_rows=status_rows
                )

                logger.info(f"Created taishoku spreadsheet: {spreadsheet_url}")

                return {
                    'status': 'success',
                    'message': '退職者ID削除依頼書を生成しました',
                    'url': spreadsheet_url,
                    'taishoku_count': len(taishoku_data)
                }

            except Exception as e:
                logger.error(f"Failed to create taishoku spreadsheet: {str(e)}")
                return {
                    'status': 'error',
                    'message': f'退職者リスト作成に失敗しました: {str(e)}'
                }

    def generate_tenshutu_list(self, target_date: str) -> Dict[str, Any]:
        """組織転出者アクセス権限確認リストを生成（判定ロジック + 一時テーブル方式）

        Args:
            target_date: 対象日（YYYY-MM-DD形式）

        Returns:
            生成結果
        """
        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            user_repo = UserRepository(conn)

            # 1. 転出者判定ロジックを実行
            tenshutu_service = TenshutuService(conn)
            filtered_users = tenshutu_service.filter_tenshutu_users(target_date)

            # 異動者が0件の場合はスプレッドシートを作成しない
            if not filtered_users:
                logger.info(f"No tenshutu users found for date: {target_date}")
                return {
                    'status': 'success',
                    'message': f'{target_date}に組織転出者がいないため、組織転出者アクセス権限確認リストは作成されませんでした',
                    'url': None
                }

            # 2. 一時テーブルに保存
            tenshutu_service.save_to_temp_table(target_date, filtered_users)

            # 3. 出力対象システム取得
            systems = system_repo.find_all(active_only=True)
            output_systems = [s for s in systems if s.output_required]
            output_systems.sort(key=lambda s: (s.output_order or 999, s.system_id))

            if not output_systems:
                return {
                    'status': 'error',
                    'message': '出力対象のシステムが設定されていません'
                }

            # 4-5. システムごとに個別クエリを実行してシート作成
            # 複数システムを1本のSQLで横JOINするとシステム間でデカルト積が発生し、
            # 1システムが1ユーザーにつき複数行（例: im_role）を持つ場合に他システムの
            # レコードまで増幅される。そのためシステム単位で個別にクエリを実行する。
            sheets_data = {}

            for system in output_systems:
                system_id = system.system_id.upper()

                # tenshutu_output_columnsから出力項目を取得
                output_columns = system.tenshutu_output_columns
                if not output_columns or 'columns' not in output_columns:
                    logger.warning(f"No tenshutu_output_columns defined for system: {system_id}")
                    continue

                # このシステム自身のソート順・フィルタSQLで個別取得
                try:
                    system_records = user_repo.get_tenshutu_users_for_system(
                        target_date,
                        system,
                        system.tenshutu_sort_sql,
                        system.tenshutu_filter_sql
                    )
                except Exception as e:
                    logger.error(f"Failed to get tenshutu users for system {system_id}: {str(e)}")
                    return {
                        'status': 'error',
                        'message': f'転出者データ取得でSQLエラーが発生しました（システム「{system.system_name or system_id}」の定義SQLを確認してください）: {str(e)}',
                        'url': None
                    }

                # このシステムのカラムプレフィックス
                column_prefix = f"SYS_{system_id}_"

                # USER_CDカラムでフィルタ（システムにユーザーが存在するか確認）
                user_cd_column = f"{column_prefix}USER_CD"
                system_records = [
                    r for r in system_records
                    if r.get(user_cd_column) and r.get(user_cd_column) != '－'
                ]

                if not system_records:
                    continue

                # 出力カラム定義を取得してソート
                column_defs = sorted(
                    output_columns['columns'],
                    key=lambda x: x.get('order', 999)
                )

                # ヘッダー行
                header = []
                for col_def in column_defs:
                    header.append(col_def.get('display_name', col_def['column_name']))

                # 最終列の次に「継続要否」列を追加
                header.append('継続要否')

                rows = [header]

                # データ行
                for record in system_records:
                    row = []

                    # カラム定義に従ってデータを追加
                    for col_def in column_defs:
                        col_name = col_def['column_name']
                        source = col_def.get('source', 'system')  # デフォルトはsystem

                        if source == 'tenshutu':
                            # 一時テーブル（転出者情報）から取得
                            row.append(record.get(col_name, ''))
                        else:
                            # システムユーザー情報から取得
                            full_col_name = f"{column_prefix}{col_name}"
                            row.append(record.get(full_col_name, ''))

                    # 継続要否列（空欄）を追加
                    row.append('')

                    rows.append(row)

                sheet_name = system.output_sheet_name or system.system_name
                # シート名の長さ制限（31文字）
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[:31]

                sheets_data[sheet_name] = rows

            if not sheets_data:
                return {
                    'status': 'success',
                    'message': f'{target_date}にシステムに存在する転出者がいないため、リストは作成されませんでした',
                    'url': None
                }

            # 6. 確認シートを先頭に追加（異動者が存在するシステム名のみ）
            # システム名とシステムオブジェクトのマッピングを作成
            system_map = {(s.output_sheet_name or s.system_name)[:31]: s for s in output_systems}
            confirmation_systems = [system_map[name] for name in sheets_data.keys() if name in system_map]
            # 確認担当（CHECK_RESPONSIBLE=USER_CD）の氏名を解決
            responsible_names = system_repo.get_user_names_by_cds(
                [s.check_responsible for s in confirmation_systems]
            )
            confirmation_sheet = self._create_tenshutu_confirmation_sheet(target_date, confirmation_systems, responsible_names)

            # 転出者シートを作成（IDINV_W_TENSHUTU_TEMPの内容を表示）
            tenshutu_sheet = self._create_tenshutu_list_sheet(filtered_users)

            # 確認シートと転出者シートを先頭に挿入
            ordered_sheets_data = {'確認': confirmation_sheet, '転出者': tenshutu_sheet}
            ordered_sheets_data.update(sheets_data)

            # 7. スプレッドシート作成
            try:
                gs_manager = GoogleSheetsManager()
                spreadsheet_url = gs_manager.create_sheet_with_data(
                    title=f'組織転出者アクセス権限確認リスト_{target_date}',
                    sheets_data=ordered_sheets_data,
                    folder_id=Config.GOOGLE_DRIVE_FOLDER_ID,
                    format_header=False
                )

                # 確認シートをフォーマット
                gs_manager.format_tenshutu_confirmation_sheet(spreadsheet_url, '確認', target_date, len(confirmation_systems))

                # 転出者シートのヘッダー行をフォーマット（内容から列幅を算出するためdataを渡す）
                gs_manager.format_sheet_header(spreadsheet_url, '転出者', data=tenshutu_sheet)

                # 各システムシートのヘッダー行をフォーマット（内容から列幅を算出するためdataを渡す）
                for sheet_name, sheet_data in sheets_data.items():
                    gs_manager.format_sheet_header(spreadsheet_url, sheet_name, data=sheet_data)

                logger.info(f"Created tenshutu spreadsheet: {spreadsheet_url}")

                return {
                    'status': 'success',
                    'message': '組織転出者アクセス権限確認リストを生成しました',
                    'url': spreadsheet_url
                }

            except Exception as e:
                logger.error(f"Failed to create tenshutu spreadsheet: {str(e)}")
                return {
                    'status': 'error',
                    'message': f'転出者リスト作成に失敗しました: {str(e)}'
                }

    def _create_confirmation_sheet(self, output_systems: List['SystemUserInfo'], responsible_names: Dict[str, str] = None) -> List[List[Any]]:
        """確認シートのデータを作成（棚卸リスト用、PDFフォーマット準拠）

        Args:
            output_systems: システム情報のリスト
            responsible_names: 確認担当のUSER_CDからUSER_NAMEへの辞書

        Returns:
            確認シートのデータ（2次元配列）
        """
        from datetime import datetime

        responsible_names = responsible_names or {}

        rows = []

        # 行1: タイトル「ID棚卸リストチェックシート」（B列から）、右側に日付
        output_date = datetime.now().strftime('%Y年%m月')
        rows.append(['', 'ID棚卸リストチェックシート', '', '', '', '', '', output_date])

        # 行2: 空行
        rows.append([''] * 8)

        # 行3: ヘッダー行
        header = ['システム', '確認頻度', '確認担当', '確認状況', '対応（あれば）', '出力範囲', '確認ポイント', '備考']
        rows.append(header)

        # 行4以降: 各システムのデータ行（確認頻度が「不要」のシステムは除外）
        for system in output_systems:
            # 確認頻度が「不要」の場合はスキップ
            if system.check_frequency == 'NONE':
                continue

            # 確認頻度の表示
            freq_display = '月次' if system.check_frequency == 'MONTHLY' else '年次（5月）' if system.check_frequency == 'ANNUAL' else ''

            row = [
                system.system_name or system.system_id,
                freq_display,
                # 確認担当はUSER_CDをUSER_NAMEに変換して出力（未解決時はCDのまま）
                responsible_names.get(system.check_responsible, system.check_responsible or ''),
                '',  # 確認状況は空欄
                '',  # 対応（あれば）は空欄
                system.output_scope or '',
                system.check_points or '',
                system.check_remarks or ''
            ]
            rows.append(row)

        # 下部の小さな表（IM_ROLEなど用）
        rows.append([''] * 8)  # 空行
        rows.append([''] * 8)  # 空行

        # 下部表のヘッダー
        rows.append(['システム', '確認頻度', '確認担当', '確認状況', '対応（あれば）', '', '', ''])

        # 下部表の明細（5行、IM_ROLEと年次（5月）を固定）
        # 最初の行のみ値を入力（セル結合後に表示される）
        rows.append(['IM_ROLE', '年次（5月）', '', '', '', '', '', ''])

        # 残り4行は空欄（セル結合されるため）
        for _ in range(4):
            rows.append(['', '', '', '', '', '', '', ''])

        return rows

    def _create_tenshutu_list_sheet(self, filtered_users: List[Dict[str, Any]]) -> List[List[Any]]:
        """転出者シートのデータを作成（IDINV_W_TENSHUTU_TEMPの内容を表示）

        Args:
            filtered_users: フィルタリング済み転出者リスト

        Returns:
            転出者シートのデータ（2次元配列）
        """
        rows = []

        # ヘッダー行
        header = ['ユーザーCD', 'ユーザー名', '転出元', '異動後']
        rows.append(header)

        # データ行
        for user in filtered_users:
            row = [
                user.get('USER_CD', ''),
                user.get('USER_NAME', ''),
                user.get('BEFORE_ORG', ''),
                user.get('AFTER_ORG', '')
            ]
            rows.append(row)

        return rows

    def _create_tenshutu_confirmation_sheet(self, target_date: str, systems: List['SystemUserInfo'], responsible_names: Dict[str, str] = None) -> List[List[Any]]:
        """確認シートのデータを作成（組織転出者アクセス権限確認リスト用）

        Args:
            target_date: 転出日（YYYY-MM-DD形式）
            systems: システム情報のリスト
            responsible_names: 確認担当のUSER_CDからUSER_NAMEへの辞書

        Returns:
            確認シートのデータ（2次元配列）
        """
        responsible_names = responsible_names or {}
        from datetime import datetime

        # 転出日をフォーマット（YYYY/MM/DD形式）
        tenshutu_date = datetime.strptime(target_date, '%Y-%m-%d').strftime('%Y/%m/%d')

        rows = []

        # 行1: 表題「転出者　アクセス権限　確認リスト」
        rows.append(['転出者　アクセス権限　確認リスト', '', '', '', '', '', ''])

        # 行2: 空行
        rows.append([''] * 7)

        # 行3: A3に「転出日」、B3に転出日、G3に「確認」
        rows.append(['転出日', tenshutu_date, '', '', '', '', '確認'])

        # 行4: 空行（確認の下の枠の一部）
        rows.append([''] * 7)

        # 行5: 空行（確認の下の枠の一部）
        rows.append([''] * 7)

        # 行6: 空行
        rows.append([''] * 7)

        # 行7: ヘッダー行
        rows.append(['', '継続要否確認', '', '権限削除等作業欄', '', '', ''])

        # 行8: サブヘッダー行
        rows.append(['', '担当', '確認日', '担当', '実施日', '再査', '実施日'])

        # 行9以降: システム名とcheck_responsibleを列挙
        for system in systems:
            system_name = system.output_sheet_name or system.system_name
            if len(system_name) > 31:
                system_name = system_name[:31]
            # 確認担当はUSER_CDをUSER_NAMEに変換して出力（未解決時はCDのまま）
            check_responsible = responsible_names.get(system.check_responsible, system.check_responsible or '')
            rows.append([system_name, check_responsible, '', '', '', '', ''])

        return rows
