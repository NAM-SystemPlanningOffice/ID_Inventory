from app.repositories.base_repository import BaseRepository
from app.models.system import SystemUserInfo
from typing import List, Optional

class SystemRepository(BaseRepository):
    def find_all(self, active_only=True) -> List[SystemUserInfo]:
        sql = """
            SELECT
                SYSTEM_ID, SYSTEM_NAME, DESCRIPTION,
                IMPORT_METHOD, IMPORT_TABLE_NAME,
                IMPORT_MAPPING_JSON, LAST_IMPORT_DATETIME, LAST_IMPORT_USER,
                LAST_IMPORT_RECORD_COUNT, OUTPUT_REQUIRED, OUTPUT_ORDER,
                OUTPUT_SHEET_NAME,
                TANAOROSHI_OUTPUT_COLUMNS_JSON, TANAOROSHI_OUTPUT_MODE, TANAOROSHI_FILTER_SQL, TANAOROSHI_SORT_SQL,
                TENSHUTU_OUTPUT_COLUMNS_JSON, TENSHUTU_FILTER_SQL, TENSHUTU_SORT_SQL,
                TAISHOKU_OUTPUT_REQUIRED, TAISHOKU_OUTPUT_ORDER, TAISHOKU_DISPLAY_SQL, TAISHOKU_DISABLED_EXPRESSION,
                CHECK_FREQUENCY, CHECK_RESPONSIBLE, OUTPUT_SCOPE, CHECK_POINTS, CHECK_REMARKS,
                IS_ACTIVE, REMARKS, CREATED_AT, CREATED_BY, UPDATED_AT, UPDATED_BY
            FROM NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
        """
        if active_only:
            sql += " WHERE IS_ACTIVE = 1"
        sql += " ORDER BY OUTPUT_ORDER, SYSTEM_ID"

        rows = self.execute_query_for_model(sql)
        return [SystemUserInfo(**row) for row in rows]

    def find_by_id(self, system_id: str) -> Optional[SystemUserInfo]:
        sql = """
            SELECT
                SYSTEM_ID, SYSTEM_NAME, DESCRIPTION,
                IMPORT_METHOD, IMPORT_TABLE_NAME,
                IMPORT_MAPPING_JSON, LAST_IMPORT_DATETIME, LAST_IMPORT_USER,
                LAST_IMPORT_RECORD_COUNT, OUTPUT_REQUIRED, OUTPUT_ORDER,
                OUTPUT_SHEET_NAME,
                TANAOROSHI_OUTPUT_COLUMNS_JSON, TANAOROSHI_OUTPUT_MODE, TANAOROSHI_FILTER_SQL, TANAOROSHI_SORT_SQL,
                TENSHUTU_OUTPUT_COLUMNS_JSON, TENSHUTU_FILTER_SQL, TENSHUTU_SORT_SQL,
                TAISHOKU_OUTPUT_REQUIRED, TAISHOKU_OUTPUT_ORDER, TAISHOKU_DISPLAY_SQL, TAISHOKU_DISABLED_EXPRESSION,
                CHECK_FREQUENCY, CHECK_RESPONSIBLE, OUTPUT_SCOPE, CHECK_POINTS, CHECK_REMARKS,
                IS_ACTIVE, REMARKS, CREATED_AT, CREATED_BY, UPDATED_AT, UPDATED_BY
            FROM NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
            WHERE SYSTEM_ID = :SYSTEM_ID
        """
        row = self.execute_one_for_model(sql, {'SYSTEM_ID': system_id})
        return SystemUserInfo(**row) if row else None

    def insert(self, system: SystemUserInfo, user: str) -> int:
        sql = """
            INSERT INTO NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS (
                SYSTEM_ID, SYSTEM_NAME, DESCRIPTION,
                IMPORT_METHOD, IMPORT_TABLE_NAME,
                IMPORT_MAPPING_JSON, OUTPUT_REQUIRED, OUTPUT_ORDER,
                OUTPUT_SHEET_NAME,
                TANAOROSHI_OUTPUT_COLUMNS_JSON, TANAOROSHI_OUTPUT_MODE, TANAOROSHI_FILTER_SQL, TANAOROSHI_SORT_SQL,
                TENSHUTU_OUTPUT_COLUMNS_JSON, TENSHUTU_FILTER_SQL, TENSHUTU_SORT_SQL,
                TAISHOKU_OUTPUT_REQUIRED, TAISHOKU_OUTPUT_ORDER, TAISHOKU_DISPLAY_SQL, TAISHOKU_DISABLED_EXPRESSION,
                CHECK_FREQUENCY, CHECK_RESPONSIBLE, OUTPUT_SCOPE, CHECK_POINTS, CHECK_REMARKS,
                IS_ACTIVE, REMARKS, CREATED_BY, UPDATED_BY
            ) VALUES (
                :SYSTEM_ID, :SYSTEM_NAME, :DESCRIPTION,
                :IMPORT_METHOD, :IMPORT_TABLE_NAME,
                :IMPORT_MAPPING_JSON, :OUTPUT_REQUIRED, :OUTPUT_ORDER,
                :OUTPUT_SHEET_NAME,
                :TANAOROSHI_OUTPUT_COLUMNS_JSON, :TANAOROSHI_OUTPUT_MODE, :TANAOROSHI_FILTER_SQL, :TANAOROSHI_SORT_SQL,
                :TENSHUTU_OUTPUT_COLUMNS_JSON, :TENSHUTU_FILTER_SQL, :TENSHUTU_SORT_SQL,
                :TAISHOKU_OUTPUT_REQUIRED, :TAISHOKU_OUTPUT_ORDER, :TAISHOKU_DISPLAY_SQL, :TAISHOKU_DISABLED_EXPRESSION,
                :CHECK_FREQUENCY, :CHECK_RESPONSIBLE, :OUTPUT_SCOPE, :CHECK_POINTS, :CHECK_REMARKS,
                :IS_ACTIVE, :REMARKS, :CREATED_BY, :UPDATED_BY
            )
        """
        params = {
            'SYSTEM_ID': system.system_id,
            'SYSTEM_NAME': system.system_name,
            'DESCRIPTION': system.description,
            'IMPORT_METHOD': system.import_method,
            'IMPORT_TABLE_NAME': system.import_table_name,
            'IMPORT_MAPPING_JSON': system.import_mapping_json,
            'OUTPUT_REQUIRED': system.output_required,
            'OUTPUT_ORDER': system.output_order,
            'OUTPUT_SHEET_NAME': system.output_sheet_name,
            'TANAOROSHI_OUTPUT_COLUMNS_JSON': system.tanaoroshi_output_columns_json,
            'TANAOROSHI_OUTPUT_MODE': system.tanaoroshi_output_mode,
            'TANAOROSHI_FILTER_SQL': system.tanaoroshi_filter_sql,
            'TANAOROSHI_SORT_SQL': system.tanaoroshi_sort_sql,
            'TENSHUTU_OUTPUT_COLUMNS_JSON': system.tenshutu_output_columns_json,
            'TENSHUTU_FILTER_SQL': system.tenshutu_filter_sql,
            'TENSHUTU_SORT_SQL': system.tenshutu_sort_sql,
            'TAISHOKU_OUTPUT_REQUIRED': system.taishoku_output_required,
            'TAISHOKU_OUTPUT_ORDER': system.taishoku_output_order,
            'TAISHOKU_DISPLAY_SQL': system.taishoku_display_sql,
            'TAISHOKU_DISABLED_EXPRESSION': system.taishoku_disabled_expression,
            'CHECK_FREQUENCY': system.check_frequency,
            'CHECK_RESPONSIBLE': system.check_responsible,
            'OUTPUT_SCOPE': system.output_scope,
            'CHECK_POINTS': system.check_points,
            'CHECK_REMARKS': system.check_remarks,
            'IS_ACTIVE': system.is_active,
            'REMARKS': system.remarks,
            'CREATED_BY': user,
            'UPDATED_BY': user
        }
        return self.execute_insert(sql, params)

    def update(self, system: SystemUserInfo, user: str) -> int:
        sql = """
            UPDATE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS SET
                SYSTEM_NAME = :SYSTEM_NAME,
                DESCRIPTION = :DESCRIPTION,
                IMPORT_METHOD = :IMPORT_METHOD,
                IMPORT_TABLE_NAME = :IMPORT_TABLE_NAME,
                IMPORT_MAPPING_JSON = :IMPORT_MAPPING_JSON,
                OUTPUT_REQUIRED = :OUTPUT_REQUIRED,
                OUTPUT_ORDER = :OUTPUT_ORDER,
                OUTPUT_SHEET_NAME = :OUTPUT_SHEET_NAME,
                TANAOROSHI_OUTPUT_COLUMNS_JSON = :TANAOROSHI_OUTPUT_COLUMNS_JSON,
                TANAOROSHI_OUTPUT_MODE = :TANAOROSHI_OUTPUT_MODE,
                TANAOROSHI_FILTER_SQL = :TANAOROSHI_FILTER_SQL,
                TANAOROSHI_SORT_SQL = :TANAOROSHI_SORT_SQL,
                TENSHUTU_OUTPUT_COLUMNS_JSON = :TENSHUTU_OUTPUT_COLUMNS_JSON,
                TENSHUTU_FILTER_SQL = :TENSHUTU_FILTER_SQL,
                TENSHUTU_SORT_SQL = :TENSHUTU_SORT_SQL,
                TAISHOKU_OUTPUT_REQUIRED = :TAISHOKU_OUTPUT_REQUIRED,
                TAISHOKU_OUTPUT_ORDER = :TAISHOKU_OUTPUT_ORDER,
                TAISHOKU_DISPLAY_SQL = :TAISHOKU_DISPLAY_SQL,
                TAISHOKU_DISABLED_EXPRESSION = :TAISHOKU_DISABLED_EXPRESSION,
                CHECK_FREQUENCY = :CHECK_FREQUENCY,
                CHECK_RESPONSIBLE = :CHECK_RESPONSIBLE,
                OUTPUT_SCOPE = :OUTPUT_SCOPE,
                CHECK_POINTS = :CHECK_POINTS,
                CHECK_REMARKS = :CHECK_REMARKS,
                IS_ACTIVE = :IS_ACTIVE,
                REMARKS = :REMARKS,
                UPDATED_BY = :UPDATED_BY,
                UPDATED_AT = SYSTIMESTAMP
            WHERE SYSTEM_ID = :SYSTEM_ID
        """
        params = {
            'SYSTEM_ID': system.system_id,
            'SYSTEM_NAME': system.system_name,
            'DESCRIPTION': system.description,
            'IMPORT_METHOD': system.import_method,
            'IMPORT_TABLE_NAME': system.import_table_name,
            'IMPORT_MAPPING_JSON': system.import_mapping_json,
            'OUTPUT_REQUIRED': system.output_required,
            'OUTPUT_ORDER': system.output_order,
            'OUTPUT_SHEET_NAME': system.output_sheet_name,
            'TANAOROSHI_OUTPUT_COLUMNS_JSON': system.tanaoroshi_output_columns_json,
            'TANAOROSHI_OUTPUT_MODE': system.tanaoroshi_output_mode,
            'TANAOROSHI_FILTER_SQL': system.tanaoroshi_filter_sql,
            'TANAOROSHI_SORT_SQL': system.tanaoroshi_sort_sql,
            'TENSHUTU_OUTPUT_COLUMNS_JSON': system.tenshutu_output_columns_json,
            'TENSHUTU_FILTER_SQL': system.tenshutu_filter_sql,
            'TENSHUTU_SORT_SQL': system.tenshutu_sort_sql,
            'TAISHOKU_OUTPUT_REQUIRED': system.taishoku_output_required,
            'TAISHOKU_OUTPUT_ORDER': system.taishoku_output_order,
            'TAISHOKU_DISPLAY_SQL': system.taishoku_display_sql,
            'TAISHOKU_DISABLED_EXPRESSION': system.taishoku_disabled_expression,
            'CHECK_FREQUENCY': system.check_frequency,
            'CHECK_RESPONSIBLE': system.check_responsible,
            'OUTPUT_SCOPE': system.output_scope,
            'CHECK_POINTS': system.check_points,
            'CHECK_REMARKS': system.check_remarks,
            'IS_ACTIVE': system.is_active,
            'REMARKS': system.remarks,
            'UPDATED_BY': user
        }
        return self.execute_update(sql, params)

    def update_import_info(self, system_id: str, datetime, user: str, record_count: int) -> int:
        sql = """
            UPDATE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS SET
                LAST_IMPORT_DATETIME = :LAST_IMPORT_DATETIME,
                LAST_IMPORT_USER = :LAST_IMPORT_USER,
                LAST_IMPORT_RECORD_COUNT = :LAST_IMPORT_RECORD_COUNT,
                UPDATED_AT = SYSTIMESTAMP
            WHERE SYSTEM_ID = :SYSTEM_ID
        """
        return self.execute_update(sql, {
            'SYSTEM_ID': system_id,
            'LAST_IMPORT_DATETIME': datetime,
            'LAST_IMPORT_USER': user,
            'LAST_IMPORT_RECORD_COUNT': record_count
        })

    def get_user_names_by_cds(self, user_cds: List[str]) -> dict:
        """USER_CD のリストから USER_NAME を引く（IMART.IMM_USER@IMDB2 参照）

        確認担当（CHECK_RESPONSIBLE=USER_CD）の氏名解決に使用。

        Args:
            user_cds: ユーザーCDのリスト

        Returns:
            {USER_CD: USER_NAME} の辞書（在籍していないCDは含まれない）
        """
        # 空・None を除いた一意なCDのみ対象
        unique_cds = list({cd for cd in user_cds if cd})
        if not unique_cds:
            return {}

        params = {}
        bind_names = []
        for i, cd in enumerate(unique_cds):
            key = f"U{i}"
            params[key] = cd
            bind_names.append(f":{key}")

        sql = f"""
            SELECT USER_CD, USER_NAME
            FROM IMART.IMM_USER@IMDB2
            WHERE START_DATE <= TRUNC(SYSDATE)
              AND END_DATE > TRUNC(SYSDATE)
              AND DELETE_FLAG = '0'
              AND USER_CD IN ({', '.join(bind_names)})
        """
        rows = self.execute_query(sql, params)
        return {row['USER_CD']: row['USER_NAME'] for row in rows}

    def get_oldest_import_datetime(self):
        sql = """
            SELECT MIN(LAST_IMPORT_DATETIME) AS OLDEST_DATETIME
            FROM NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
            WHERE IS_ACTIVE = 1
              AND IMPORT_METHOD IN ('CSV', 'XLSX')
        """
        row = self.execute_one(sql)
        return row['oldest_datetime'] if row else None
