from app.utils.db import get_cursor
from datetime import datetime, date

class BaseRepository:
    def __init__(self, connection=None):
        self.connection = connection

    def _normalize_value_for_json(self, v):
        """値を正規化（JSON出力用：日付を文字列に変換）

        - date型: yyyy-MM-dd
        - datetime型で時刻が00:00:00: yyyy-MM-dd（日付のみ）
        - datetime型で時刻を持つ（取り込み日時等）: yyyy-MM-ddTHH:mm:ss（ISO形式）
        """
        if isinstance(v, datetime):
            # 時刻部分が00:00:00なら日付のみ、そうでなければ従来通りISO形式
            if v.hour == 0 and v.minute == 0 and v.second == 0 and v.microsecond == 0:
                return v.strftime('%Y-%m-%d')
            return v.isoformat()
        if isinstance(v, date):
            # date型は時刻を持たないので日付のみ
            return v.strftime('%Y-%m-%d')
        return v

    def _normalize_keys(self, d):
        """Oracleのカラム名を正規化（大文字・小文字両方のキーを持つ、値はJSON用に変換）"""
        result = {}
        for k, v in d.items():
            normalized_value = self._normalize_value_for_json(v)
            result[k.upper()] = normalized_value
            result[k.lower()] = normalized_value
        return result

    def _lowercase_keys_only(self, d):
        """小文字のキーのみを持つ辞書を返す（dataclassへの変換用：日付オブジェクトはそのまま）"""
        return {k.lower(): v for k, v in d.items()}

    def execute_query(self, sql, params=None):
        with get_cursor(self.connection) as cursor:
            cursor.execute(sql, params or {})
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            return [self._normalize_keys(dict(zip(columns, row))) for row in rows]

    def execute_query_for_model(self, sql, params=None):
        """モデルクラス（dataclass）への変換用クエリ実行（小文字キーのみ）"""
        with get_cursor(self.connection) as cursor:
            cursor.execute(sql, params or {})
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            return [self._lowercase_keys_only(dict(zip(columns, row))) for row in rows]

    def execute_one(self, sql, params=None):
        with get_cursor(self.connection) as cursor:
            cursor.execute(sql, params or {})
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                return self._normalize_keys(dict(zip(columns, row))) if row else None
            return None

    def execute_one_for_model(self, sql, params=None):
        """モデルクラス（dataclass）への変換用クエリ実行（小文字キーのみ）"""
        with get_cursor(self.connection) as cursor:
            cursor.execute(sql, params or {})
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                return self._lowercase_keys_only(dict(zip(columns, row))) if row else None
            return None

    def execute_insert(self, sql, params=None):
        from app.utils.logger import logger
        try:
            with get_cursor(self.connection) as cursor:
                cursor.execute(sql, params or {})
                return cursor.rowcount
        except Exception as e:
            logger.error(f"SQL execution failed (INSERT)")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            if hasattr(e, 'args') and e.args:
                for i, arg in enumerate(e.args):
                    logger.error(f"Oracle error args[{i}]: {arg}")
            logger.error(f"SQL: {sql[:500]}...")
            raise

    def execute_update(self, sql, params=None):
        from app.utils.logger import logger
        try:
            with get_cursor(self.connection) as cursor:
                cursor.execute(sql, params or {})
                return cursor.rowcount
        except Exception as e:
            logger.error(f"SQL execution failed (UPDATE)")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            if hasattr(e, 'args') and e.args:
                for i, arg in enumerate(e.args):
                    logger.error(f"Oracle error args[{i}]: {arg}")
            logger.error(f"SQL: {sql[:500]}...")
            raise

    def execute_delete(self, sql, params=None):
        from app.utils.logger import logger
        try:
            with get_cursor(self.connection) as cursor:
                cursor.execute(sql, params or {})
                return cursor.rowcount
        except Exception as e:
            logger.error(f"SQL execution failed (DELETE)")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            if hasattr(e, 'args') and e.args:
                for i, arg in enumerate(e.args):
                    logger.error(f"Oracle error args[{i}]: {arg}")
            logger.error(f"SQL: {sql[:500]}...")
            raise
