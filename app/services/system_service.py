from typing import Dict, Any, List
from app.repositories.system_repository import SystemRepository
from app.repositories.user_repository import UserRepository
from app.models.system import SystemUserInfo
from app.utils.db import get_db_connection
from app.utils.validators import validate_system_id, validate_taishoku_display_sql
from app.utils.logger import logger
import json

class SystemService:
    def get_all_systems(self, active_only: bool = True) -> List[SystemUserInfo]:
        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            return system_repo.find_all(active_only)

    def get_system_by_id(self, system_id: str) -> SystemUserInfo:
        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            system = system_repo.find_by_id(system_id)
            if not system:
                raise ValueError(f"システムID '{system_id}' が見つかりません")
            return system

    def create_system(self, system_data: Dict[str, Any], user: str) -> None:
        validate_system_id(system_data['system_id'])

        # 退職者表示SQLのバリデーション
        if 'taishoku_display_sql' in system_data:
            validate_taishoku_display_sql(system_data['taishoku_display_sql'])

        import_method = system_data.get('import_method')
        # CSV/XLSXでもIMPORT_TABLE_NAMEをユーザー指定可能に（デフォルトはテーブル名）
        if import_method == 'DIRECT':
            import_table_name = system_data.get('import_table_name', '')
        elif import_method in ('CSV', 'XLSX'):
            # ユーザー指定がない場合のみデフォルトテーブル名を設定
            import_table_name = system_data.get('import_table_name') or f"IDINV_W_SYSTEM_USERS_{system_data['system_id'].upper()}"
        else:
            import_table_name = system_data.get('import_table_name', '')

        system = SystemUserInfo(
            system_id=system_data['system_id'],
            system_name=system_data['system_name'],
            description=system_data.get('description'),
            import_method=import_method,
            import_table_name=import_table_name,
            import_mapping_json=system_data.get('import_mapping_json'),
            output_required=system_data.get('output_required', 1),
            output_order=system_data.get('output_order'),
            output_sheet_name=system_data.get('output_sheet_name'),
            tanaoroshi_output_columns_json=system_data.get('tanaoroshi_output_columns_json'),
            tanaoroshi_output_mode=system_data.get('tanaoroshi_output_mode', 'MISMATCH_ONLY'),
            tanaoroshi_filter_sql=system_data.get('tanaoroshi_filter_sql'),
            tanaoroshi_sort_sql=system_data.get('tanaoroshi_sort_sql'),
            tenshutu_output_columns_json=system_data.get('tenshutu_output_columns_json'),
            tenshutu_filter_sql=system_data.get('tenshutu_filter_sql'),
            tenshutu_sort_sql=system_data.get('tenshutu_sort_sql'),
            taishoku_output_required=system_data.get('taishoku_output_required', 1),
            taishoku_output_order=system_data.get('taishoku_output_order'),
            taishoku_display_sql=system_data.get('taishoku_display_sql'),
            taishoku_disabled_expression=system_data.get('taishoku_disabled_expression'),
            check_frequency=system_data.get('check_frequency', 'MONTHLY'),
            check_responsible=system_data.get('check_responsible'),
            output_scope=system_data.get('output_scope'),
            check_points=system_data.get('check_points'),
            check_remarks=system_data.get('check_remarks'),
            is_active=system_data.get('is_active', 1),
            remarks=system_data.get('remarks')
        )

        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            user_repo = UserRepository(conn)

            existing = system_repo.find_by_id(system_data['system_id'])
            if existing:
                raise ValueError(f"システムID '{system_data['system_id']}' は既に登録されています")

            # 1. CSV/XLSXの場合、参照元テーブル(IDINV_W_SYSTEM_USERS_XXXX)を先に作成
            #    （マッピング変更後の列構成で参照元チェックを行うため）
            if system.import_method in ('CSV', 'XLSX') and system.import_mapping_json:
                mapping = json.loads(system.import_mapping_json)
                user_repo.create_system_user_table(system.system_id, mapping['columns'])
                logger.info(f"System user table created: {system.import_table_name}")

            # 2. 棚卸の参照元テーブル/SQL・フィルタSQL・ソート順SQL・出力カラム定義のバリデーション
            #    （テーブル作成後の実際の列構成に対してドライラン検証）
            self._validate_tanaoroshi_sql(
                system_id=system.system_id,
                import_table_name=system.import_table_name,
                import_method=system.import_method,
                filter_sql=system.tanaoroshi_filter_sql,
                sort_sql=system.tanaoroshi_sort_sql,
                tanaoroshi_output_columns_json=system.tanaoroshi_output_columns_json,
                tenshutu_output_columns_json=system.tenshutu_output_columns_json,
                conn=conn
            )

            # 2b. 転出者リストのフィルタSQL・ソート順SQLのドライラン検証
            #     （転出者クエリ構造 IDINV_W_TENSHUTU_TEMP + システム に対して検証。
            #       棚卸と異なり在籍情報 z. はJOINされないため z. 参照はここで弾く）
            UserRepository(conn).validate_tenshutu_sql(
                system=system,
                filter_sql=system.tenshutu_filter_sql,
                sort_sql=system.tenshutu_sort_sql
            )

            # 2c. 退職者リストの表示SQL・無効化済み判定SQLのドライラン検証
            #     （退職者クエリ構造 E_IMDB_USERS_END + システム に対して検証）
            UserRepository(conn).validate_taishoku_sql(
                system=system,
                display_sql=system.taishoku_display_sql,
                disabled_expression=system.taishoku_disabled_expression
            )

            # 3. システム定義を登録
            system_repo.insert(system, user)

    def update_system(self, system_id: str, system_data: Dict[str, Any], user: str) -> None:
        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            system = system_repo.find_by_id(system_id)

            if not system:
                raise ValueError(f"システムID '{system_id}' が見つかりません")

            old_mapping = system.import_mapping_json

            if 'system_name' in system_data:
                system.system_name = system_data['system_name']
            if 'description' in system_data:
                system.description = system_data['description']
            if 'import_method' in system_data:
                system.import_method = system_data['import_method']
            if 'import_table_name' in system_data:
                system.import_table_name = system_data['import_table_name']
            if 'import_mapping_json' in system_data:
                system.import_mapping_json = system_data['import_mapping_json']
            if 'output_required' in system_data:
                system.output_required = system_data['output_required']
            if 'output_order' in system_data:
                system.output_order = system_data['output_order']
            if 'output_sheet_name' in system_data:
                system.output_sheet_name = system_data['output_sheet_name']
            if 'tanaoroshi_output_columns_json' in system_data:
                system.tanaoroshi_output_columns_json = system_data['tanaoroshi_output_columns_json']
            if 'tanaoroshi_output_mode' in system_data:
                system.tanaoroshi_output_mode = system_data['tanaoroshi_output_mode']
            if 'tanaoroshi_filter_sql' in system_data:
                system.tanaoroshi_filter_sql = system_data['tanaoroshi_filter_sql']
            if 'tanaoroshi_sort_sql' in system_data:
                system.tanaoroshi_sort_sql = system_data['tanaoroshi_sort_sql']
            if 'tenshutu_output_columns_json' in system_data:
                system.tenshutu_output_columns_json = system_data['tenshutu_output_columns_json']
            if 'tenshutu_filter_sql' in system_data:
                system.tenshutu_filter_sql = system_data['tenshutu_filter_sql']
            if 'tenshutu_sort_sql' in system_data:
                system.tenshutu_sort_sql = system_data['tenshutu_sort_sql']
            if 'taishoku_output_required' in system_data:
                system.taishoku_output_required = system_data['taishoku_output_required']
            if 'taishoku_output_order' in system_data:
                system.taishoku_output_order = system_data['taishoku_output_order']
            if 'taishoku_display_sql' in system_data:
                validate_taishoku_display_sql(system_data['taishoku_display_sql'])
                system.taishoku_display_sql = system_data['taishoku_display_sql']
            if 'taishoku_disabled_expression' in system_data:
                system.taishoku_disabled_expression = system_data['taishoku_disabled_expression']
            if 'check_frequency' in system_data:
                system.check_frequency = system_data['check_frequency']
            if 'check_responsible' in system_data:
                system.check_responsible = system_data['check_responsible']
            if 'output_scope' in system_data:
                system.output_scope = system_data['output_scope']
            if 'check_points' in system_data:
                system.check_points = system_data['check_points']
            if 'check_remarks' in system_data:
                system.check_remarks = system_data['check_remarks']
            if 'is_active' in system_data:
                system.is_active = system_data['is_active']
            if 'remarks' in system_data:
                system.remarks = system_data['remarks']

            # 1. CSV/XLSXでマッピングが変更された場合、参照元テーブル(IDINV_W_SYSTEM_USERS_XXXX)を先に再作成
            #    （マッピング変更後の列構成で参照元チェックを行うため）
            if system.import_method in ('CSV', 'XLSX') and old_mapping != system.import_mapping_json and system.import_mapping_json:
                user_repo = UserRepository(conn)
                mapping = json.loads(system.import_mapping_json)
                user_repo.create_system_user_table(system.system_id, mapping['columns'])
                logger.info(f"System user table recreated: {system.import_table_name}")

            # 2. 棚卸の参照元テーブル/SQL・フィルタSQL・ソート順SQL・出力カラム定義のバリデーション
            #    （参照元/取り込み方法/フィルタ/ソート/マッピング/出力カラム定義のいずれかが
            #      変更された場合、テーブル再作成後の実際の列構成に対してドライラン検証）
            if 'tanaoroshi_filter_sql' in system_data or 'tanaoroshi_sort_sql' in system_data \
                    or 'import_table_name' in system_data or 'import_method' in system_data \
                    or 'import_mapping_json' in system_data \
                    or 'tanaoroshi_output_columns_json' in system_data \
                    or 'tenshutu_output_columns_json' in system_data:
                self._validate_tanaoroshi_sql(
                    system_id=system_id,
                    import_table_name=system.import_table_name,
                    import_method=system.import_method,
                    filter_sql=system.tanaoroshi_filter_sql,
                    sort_sql=system.tanaoroshi_sort_sql,
                    tanaoroshi_output_columns_json=system.tanaoroshi_output_columns_json,
                    tenshutu_output_columns_json=system.tenshutu_output_columns_json,
                    conn=conn
                )

            # 2b. 転出者リストのフィルタSQL・ソート順SQLのドライラン検証
            #     （転出者SQLまたは参照元/取り込み方法/マッピングのいずれかが変更された場合）
            if 'tenshutu_filter_sql' in system_data or 'tenshutu_sort_sql' in system_data \
                    or 'import_table_name' in system_data or 'import_method' in system_data \
                    or 'import_mapping_json' in system_data:
                UserRepository(conn).validate_tenshutu_sql(
                    system=system,
                    filter_sql=system.tenshutu_filter_sql,
                    sort_sql=system.tenshutu_sort_sql
                )

            # 2c. 退職者リストの表示SQL・無効化済み判定SQLのドライラン検証
            #     （退職者SQLまたは参照元/取り込み方法/マッピングのいずれかが変更された場合）
            if 'taishoku_display_sql' in system_data or 'taishoku_disabled_expression' in system_data \
                    or 'import_table_name' in system_data or 'import_method' in system_data \
                    or 'import_mapping_json' in system_data:
                UserRepository(conn).validate_taishoku_sql(
                    system=system,
                    display_sql=system.taishoku_display_sql,
                    disabled_expression=system.taishoku_disabled_expression
                )

            # 3. システム定義を更新
            system_repo.update(system, user)

    def _validate_tanaoroshi_sql(self, system_id, import_table_name=None, import_method=None,
                                 filter_sql=None, sort_sql=None,
                                 tanaoroshi_output_columns_json=None,
                                 tenshutu_output_columns_json=None, conn=None) -> None:
        """棚卸の参照元テーブル/SQL・フィルタSQL・ソート順SQL・出力カラム定義をドライラン検証する

        CSV/XLSXでimport_table_name未指定の場合はデフォルトテーブル名を補完してから検証する。

        Args:
            system_id: システムID
            import_table_name: テーブル名またはSQL
            import_method: 取り込み方法（デフォルトテーブル名補完に使用）
            filter_sql: 棚卸フィルタSQL
            sort_sql: 棚卸ソート順SQL
            tanaoroshi_output_columns_json: 棚卸リストの出力カラム定義（JSON文字列）
            tenshutu_output_columns_json: 転出者リストの出力カラム定義（JSON文字列）
            conn: 既存のDB接続（指定時は再利用、未指定時は新規接続）

        Raises:
            ValueError: SQLまたは出力カラム定義に不備がある場合
        """
        # CSV/XLSXでテーブル名未指定ならデフォルトテーブル名を補完
        table_name = import_table_name
        if (not table_name or not table_name.strip()) and import_method in ('CSV', 'XLSX'):
            table_name = f"IDINV_W_SYSTEM_USERS_{system_id.upper()}"

        # 出力カラム定義（JSON文字列）をパースして検証対象リストを構築
        output_column_sets = []
        for label, columns_json in (
            ('ユーザー棚卸リスト 出力カラム定義', tanaoroshi_output_columns_json),
            ('組織転出者リスト 出力カラム定義', tenshutu_output_columns_json),
        ):
            if columns_json:
                try:
                    output_column_sets.append({'label': label, 'columns': json.loads(columns_json)})
                except (ValueError, TypeError):
                    # JSONパース失敗はここでは無視（別途JSON形式のバリデーションに委ねる）
                    pass

        def _run(c):
            UserRepository(c).validate_tanaoroshi_sql(
                system_id=system_id,
                import_table_name=table_name,
                filter_sql=filter_sql,
                sort_sql=sort_sql,
                output_column_sets=output_column_sets
            )

        if conn is not None:
            _run(conn)
        else:
            with get_db_connection() as new_conn:
                _run(new_conn)

    def delete_system(self, system_id: str) -> None:
        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            system = system_repo.find_by_id(system_id)

            if not system:
                raise ValueError(f"システムID '{system_id}' が見つかりません")

            system.is_active = 0
            system_repo.update(system, 'SYSTEM')

    def ensure_system_table_exists(self, system_id: str) -> bool:
        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            system = system_repo.find_by_id(system_id)

            if not system or system.import_method not in ('CSV', 'XLSX'):
                return False

            if not system.import_mapping_json:
                raise ValueError(f"システム '{system.system_name}' のマッピング定義が設定されていません")

            user_repo = UserRepository(conn)
            table_name = f"IDINV_W_SYSTEM_USERS_{system_id.upper()}"

            try:
                test_sql = f"SELECT COUNT(*) AS CNT FROM NAM_IAM_ADMIN.{table_name} WHERE ROWNUM = 1"
                user_repo.execute_one(test_sql)
                return True
            except:
                mapping = json.loads(system.import_mapping_json)
                user_repo.create_system_user_table(system_id, mapping['columns'])
                logger.info(f"System user table created: {table_name}")
                return True
