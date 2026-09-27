import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database Configuration
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT', '1521')
    DB_SERVICE = os.getenv('DB_SERVICE')

    # Security Configuration
    ALLOWED_NAISETSU_CODES = [
        code.strip()
        for code in os.getenv('ALLOWED_NAISETSU_CODES', '').split(',')
        if code.strip()
    ]

    # 認証（Azure App Service / Entra ID Easy Auth）
    # Entra ID の UPN（例: abc123@nam.co.jp）から下記ドメインを除いた部分を
    # e_imdb2_users.USER_CD と照合し、NAISETSU が ALLOWED_NAISETSU_CODES に
    # 含まれるユーザーのみログインを許可する。
    AUTH_EMAIL_DOMAIN = os.getenv('AUTH_EMAIL_DOMAIN', '@nam.co.jp')

    # 開発環境（FLASK_ENV=development）では Easy Auth ヘッダが無いため認証をバイパスする。
    IS_DEVELOPMENT = os.getenv('FLASK_ENV', 'production').lower() == 'development'
    # バイパス時に「ログイン中」として扱うユーザーCD（表示・ログ用）
    DEV_LOGIN_USER_CD = os.getenv('DEV_LOGIN_USER_CD', 'devuser')

    # Upload Configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/tmp/uploads')
    MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', 104857600))
    ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

    # Google Sheets API (OAuth2)
    GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
    GOOGLE_OAUTH2_TOKEN_FILE = os.getenv('GOOGLE_OAUTH2_TOKEN_FILE', './token.json')
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

    # Proxy Configuration
    HTTP_PROXY = os.getenv('HTTP_PROXY')
    HTTPS_PROXY = os.getenv('HTTPS_PROXY')

    # Flask Configuration
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    @staticmethod
    def get_db_dsn():
        return f"{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_SERVICE}"
