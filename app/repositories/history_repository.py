from app.repositories.base_repository import BaseRepository
from app.models.history import ImportHistory, OutputHistory
from typing import List, Optional

class HistoryRepository(BaseRepository):
    def insert_import_history(self, history: ImportHistory) -> int:
        sql = """
            INSERT INTO NAM_IAM_ADMIN.IDINV_IMPORT_HISTORY (
                BATCH_ID, SYSTEM_ID, IMPORT_USER, FILE_NAME, FILE_SIZE,
                FILE_HASH, STATUS, TOTAL_RECORDS, SUCCESS_RECORDS,
                ERROR_RECORDS, ERROR_MESSAGE, START_TIME, END_TIME
            ) VALUES (
                :BATCH_ID, :SYSTEM_ID, :IMPORT_USER, :FILE_NAME, :FILE_SIZE,
                :FILE_HASH, :STATUS, :TOTAL_RECORDS, :SUCCESS_RECORDS,
                :ERROR_RECORDS, :ERROR_MESSAGE, :START_TIME, :END_TIME
            )
        """
        params = {
            'BATCH_ID': history.batch_id,
            'SYSTEM_ID': history.system_id,
            'IMPORT_USER': history.import_user,
            'FILE_NAME': history.file_name,
            'FILE_SIZE': history.file_size,
            'FILE_HASH': history.file_hash,
            'STATUS': history.status,
            'TOTAL_RECORDS': history.total_records,
            'SUCCESS_RECORDS': history.success_records,
            'ERROR_RECORDS': history.error_records,
            'ERROR_MESSAGE': history.error_message,
            'START_TIME': history.start_time,
            'END_TIME': history.end_time
        }
        return self.execute_insert(sql, params)

    def find_import_history_by_system(self, system_id: str, limit: int = 10) -> List[ImportHistory]:
        sql = """
            SELECT BATCH_ID, SYSTEM_ID, IMPORT_DATETIME, IMPORT_USER,
                   FILE_NAME, FILE_SIZE, FILE_HASH, STATUS,
                   TOTAL_RECORDS, SUCCESS_RECORDS, ERROR_RECORDS,
                   ERROR_MESSAGE, START_TIME, END_TIME
            FROM NAM_IAM_ADMIN.IDINV_IMPORT_HISTORY
            WHERE SYSTEM_ID = :SYSTEM_ID
            ORDER BY IMPORT_DATETIME DESC
            FETCH FIRST :LIMIT ROWS ONLY
        """
        rows = self.execute_query_for_model(sql, {'SYSTEM_ID': system_id, 'LIMIT': limit})
        return [ImportHistory(**row) for row in rows]

    def insert_output_history(self, history: OutputHistory) -> int:
        sql = """
            INSERT INTO NAM_IAM_ADMIN.IDINV_OUTPUT_HISTORY (
                OUTPUT_TYPE, OUTPUT_USER, TARGET_DATE, TARGET_MONTH,
                SPREADSHEET_URL, STATUS, TOTAL_SYSTEMS, TOTAL_USERS,
                ERROR_MESSAGE
            ) VALUES (
                :OUTPUT_TYPE, :OUTPUT_USER, :TARGET_DATE, :TARGET_MONTH,
                :SPREADSHEET_URL, :STATUS, :TOTAL_SYSTEMS, :TOTAL_USERS,
                :ERROR_MESSAGE
            )
        """
        params = {
            'OUTPUT_TYPE': history.output_type,
            'OUTPUT_USER': history.output_user,
            'TARGET_DATE': history.target_date,
            'TARGET_MONTH': history.target_month,
            'SPREADSHEET_URL': history.spreadsheet_url,
            'STATUS': history.status,
            'TOTAL_SYSTEMS': history.total_systems,
            'TOTAL_USERS': history.total_users,
            'ERROR_MESSAGE': history.error_message
        }
        return self.execute_insert(sql, params)

    def find_output_history(self, output_type: str = None, limit: int = 10) -> List[OutputHistory]:
        sql = """
            SELECT OUTPUT_ID, OUTPUT_TYPE, OUTPUT_DATETIME, OUTPUT_USER,
                   TARGET_DATE, TARGET_MONTH, SPREADSHEET_URL, STATUS,
                   TOTAL_SYSTEMS, TOTAL_USERS, ERROR_MESSAGE, CREATED_AT
            FROM NAM_IAM_ADMIN.IDINV_OUTPUT_HISTORY
        """
        params = {}
        if output_type:
            sql += " WHERE OUTPUT_TYPE = :OUTPUT_TYPE"
            params['OUTPUT_TYPE'] = output_type

        sql += " ORDER BY OUTPUT_DATETIME DESC FETCH FIRST :LIMIT ROWS ONLY"
        params['LIMIT'] = limit

        rows = self.execute_query_for_model(sql, params)
        return [OutputHistory(**row) for row in rows]
