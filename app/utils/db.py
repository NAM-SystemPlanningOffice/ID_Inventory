import oracledb
from contextlib import contextmanager
from app.config import Config
from app.utils.logger import logger

# Thin モードを使用（Azure App Service対応、Cライブラリ不要）
# Thin モードは自動的に使用されるが、明示的に設定
oracledb.defaults.fetch_lobs = False

def get_connection():
    """
    Oracle Database接続を取得（Thin mode）

    Thin modeの利点:
    - Oracle Instant Clientのインストール不要
    - Azure App Serviceでそのまま動作
    - Pure Python実装で軽量
    """
    try:
        conn = oracledb.connect(
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            dsn=Config.get_db_dsn()
        )
        # セッションの日付書式をISO形式に固定
        # 書式指定なしのTO_CHAR(date型)がOracle既定のDD-MON-YYになるのを防ぐ
        # （転出者リスト等の日付カラム出力を YYYY-MM-DD に統一）
        with conn.cursor() as cursor:
            cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD'")
            cursor.execute("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS'")
        logger.debug(f"Database connected: {Config.DB_HOST} (Thin mode)")
        return conn
    except oracledb.DatabaseError as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise

@contextmanager
def get_db_connection():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

@contextmanager
def get_cursor(conn=None):
    if conn:
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    else:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
