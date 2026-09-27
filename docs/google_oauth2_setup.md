# Google OAuth2認証セットアップ手順

## 概要

このシステムはGoogle Sheets APIとGoogle Drive APIを使用してスプレッドシートを作成します。
OAuth2認証を使用するため、初回実行時に認証が必要です。

## 前提条件

1. Google Cloud Consoleでプロジェクトを作成済み
2. Google Sheets API と Google Drive API を有効化済み
3. OAuth 2.0 クライアントIDを作成し、JSONファイルをダウンロード済み

## セットアップ手順

### 1. クライアントシークレットファイルの配置

ダウンロードしたOAuth 2.0クライアントIDのJSONファイルをプロジェクトルートに配置します。

```bash
# ファイル名の例
client_secret_Oauth2.apps.googleusercontent.com.json
```

### 2. .envファイルの設定

`.env`ファイルに以下を設定します：

```bash
# Google Sheets API (OAuth2)
GOOGLE_CREDENTIALS_JSON=./client_secret_Oauth2.apps.googleusercontent.com.json
GOOGLE_OAUTH2_TOKEN_FILE=./token.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here

# Proxy Configuration (企業プロキシがある場合)
HTTP_PROXY=http://proxy-lb.namc.local:8088
HTTPS_PROXY=http://proxy-lb.namc.local:8088
```

### 3. 初回認証

#### 方法1: 認証スクリプトを使用（推奨）

```bash
python scripts/authenticate_google.py
```

このスクリプトを実行すると：
1. ブラウザが自動的に開きます
2. Googleアカウントでログインします
3. アプリケーションへのアクセス許可を確認します
4. 認証が完了すると、`token.json`ファイルが作成されます

#### 方法2: Flaskアプリケーション起動時に自動認証

Flaskアプリケーションを起動し、リスト出力機能を初めて使用すると、自動的に認証フローが開始されます。

```bash
python run.py
```

ブラウザで http://localhost:5000/output にアクセスし、リスト出力を実行すると認証フローが開始されます。

### 4. トークンの確認

認証が成功すると、プロジェクトルートに`token.json`ファイルが作成されます。

```bash
ls -la token.json
```

このファイルにはアクセストークンとリフレッシュトークンが保存されています。

## トラブルシューティング

### ブラウザが開かない場合

企業プロキシの設定が必要な場合があります。`.env`にプロキシ設定を追加してください。

### 認証エラーが発生する場合

1. クライアントシークレットファイルのパスが正しいか確認
2. Google Cloud Consoleで以下のAPIが有効化されているか確認：
   - Google Sheets API
   - Google Drive API
3. OAuth 2.0クライアントIDの設定を確認：
   - アプリケーションの種類: デスクトップアプリ
   - リダイレクトURI: `http://localhost`

### トークンが期限切れの場合

トークンは自動的にリフレッシュされます。リフレッシュに失敗した場合は、`token.json`を削除して再認証してください。

```bash
rm token.json
python scripts/authenticate_google.py
```

## セキュリティ

- `client_secret_*.json` と `token.json` は `.gitignore` に含まれています
- これらのファイルを Git リポジトリにコミットしないでください
- 本番環境では適切なアクセス制御を設定してください

## 参考リンク

- [Google Sheets API Python Quickstart](https://developers.google.com/sheets/api/quickstart/python)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
