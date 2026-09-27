"""
Google OAuth2認証スクリプト

初回実行時にブラウザが開き、Googleアカウントでログインして認証を行います。
認証後、token.jsonファイルが作成されます。
"""

import os
import sys
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import Config

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def authenticate():
    """OAuth2認証を実行"""

    # プロキシ設定
    if Config.HTTP_PROXY:
        os.environ['HTTP_PROXY'] = Config.HTTP_PROXY
        print(f"HTTP_PROXY: {Config.HTTP_PROXY}")
    if Config.HTTPS_PROXY:
        os.environ['HTTPS_PROXY'] = Config.HTTPS_PROXY
        print(f"HTTPS_PROXY: {Config.HTTPS_PROXY}")

    credentials = None
    token_file = Config.GOOGLE_OAUTH2_TOKEN_FILE

    # 既存のトークンを確認
    if os.path.exists(token_file):
        print(f"既存のトークンファイルが見つかりました: {token_file}")
        try:
            with open(token_file, 'rb') as token:
                credentials = pickle.load(token)
            print("トークンを読み込みました")
        except Exception as e:
            print(f"トークンの読み込みに失敗: {str(e)}")

    # 認証情報の確認・更新
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("トークンをリフレッシュしています...")
            credentials.refresh(Request())
            print("トークンをリフレッシュしました")
        else:
            print("OAuth2認証フローを開始します...")
            print(f"クライアントシークレットファイル: {Config.GOOGLE_CREDENTIALS_JSON}")

            if not os.path.exists(Config.GOOGLE_CREDENTIALS_JSON):
                print(f"エラー: クライアントシークレットファイルが見つかりません: {Config.GOOGLE_CREDENTIALS_JSON}")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                Config.GOOGLE_CREDENTIALS_JSON,
                SCOPES
            )

            print("ブラウザが開きます。Googleアカウントでログインしてください...")
            credentials = flow.run_local_server(port=0)
            print("認証が完了しました")

        # トークンを保存
        with open(token_file, 'wb') as token:
            pickle.dump(credentials, token)
        print(f"トークンを保存しました: {token_file}")
    else:
        print("有効なトークンが存在します")

    print("\n認証が完了しました。Flaskアプリケーションから Google Sheets API を使用できます。")

if __name__ == '__main__':
    authenticate()
