# ID棚卸システム

各種システムのID棚卸を支援するシステムです。

## 機能概要

- **データ取り込み**: 各システムのユーザー情報を取得
  - CSV/Excelファイルからの取り込み
  - 既存Oracleテーブルの直接参照（DIRECT参照）
- **リスト出力**: Google Spreadsheetへ以下のリストを出力
  1. ユーザー棚卸リスト（システム毎）
  2. 退職者ID削除依頼書
  3. 組織転出者アクセス権限確認リスト
- **システム定義管理**: 各システムのマッピング情報・出力設定を管理
- **組織変更管理**: 組織体制変更の情報を管理

## 技術スタック

- **バックエンド**: Python 3.13+ / Flask 3.x
- **データベース**: Oracle Database (python-oracledb Thin mode)
- **フロントエンド**: HTML5 / CSS3 / JavaScript (Vanilla JS)
- **外部連携**: Google Sheets API
- **ホスティング**: Azure App Service

## セットアップ

### 1. 環境構築

```bash
# 仮想環境作成
python -m venv .venv

# 仮想環境アクティベート (Windows)
.venv\Scripts\activate

# 仮想環境アクティベート (Linux/Mac)
source .venv/bin/activate

# 依存パッケージインストール
pip install -r requirements.txt
```

### 2. 環境変数設定

`.env.example` を `.env` にコピーして、環境に合わせて編集してください。

```bash
cp .env.example .env
```

必須の設定項目:
- `DB_USER`: Oracleユーザー名
- `DB_PASSWORD`: Oracleパスワード
- `DB_HOST`: Oracleホスト名
- `DB_SERVICE`: Oracleサービス名
- `ALLOWED_NAISETSU_CODES`: 利用を許可する室のコード（カンマ区切り）
- `GOOGLE_CREDENTIALS_JSON`: Google Sheets API認証情報のパス

### 3. データベース初期化

本システムのオブジェクトは `NAM_IAM_ADMIN` スキーマに作成します（全テーブルに `IDINV_` 接頭辞）。

#### 新規構築の場合

`001` の CREATE 文は後続 ALTER 系の追加カラムをすべて反映した最新の完全定義です。
そのため新規構築では以下の CREATE 系のみ実行すれば足ります（`005` 以降の ALTER 系は不要）。

```bash
# NAM_IAM_ADMIN で接続してテーブルを作成
sqlplus NAM_IAM_ADMIN/password@host:1521/service

@migrations/001_create_idinv_system_definitions.sql
@migrations/002_create_idinv_organization_changes.sql
@migrations/003_create_idinv_import_history.sql
@migrations/004_create_idinv_output_history.sql
@migrations/create_idinv_tenshutu_temp_table.sql
```

在籍系マスタ（`e_imdb_*`）や DIRECT 参照先（他スキーマの既存テーブル）への
SELECT 権限は、**各オブジェクトの所有者**（`nam_user_admin` 等）で付与します。

```bash
# オブジェクト所有者（例: nam_user_admin）で接続して権限付与
sqlplus nam_user_admin/password@host:1521/service
@migrations/000_grant_imdb_select.sql
```

#### 既存環境（旧 `nam_user_admin` の `M_`/`T_` テーブル）から移行する場合

1. 上記「新規構築」で `NAM_IAM_ADMIN` に空テーブルを作成
2. `migrations/rename_existing_to_idinv.sql` の手順でデータを移送
3. `000_grant_imdb_select.sql` で参照権限を付与

> **補足**: `migrations/005`〜`014` の ALTER 系および `999_sample_data.sql` は、
> `001` 統合前の旧環境向けの履歴です。新規構築では実行不要（`001` に反映済み）。
> 旧環境でこれらを未適用のまま移行する場合のみ、移送前に旧スキーマ側で適用してください。

### 4. アプリケーション起動

```bash
python run.py
```

ブラウザで `http://localhost:5000` にアクセスしてください。

## データ取り込み機能の使い方

### 1. システム定義の登録

データベースにサンプルシステムを登録してください（migrations/999_sample_data.sql を実行）。

または、画面から登録：
1. `http://localhost:5000/system` にアクセス
2. 「新規登録」ボタンをクリック
3. システム情報とマッピング定義を入力
   - システムID: 小文字英数字とアンダースコア（例: `sap_hr`）
   - マッピング定義: [docs/sample_mapping.json](docs/sample_mapping.json) を参考
   - 出力項目定義: [docs/sample_output_columns.json](docs/sample_output_columns.json) を参考

### システム定義の編集

1. システム定義画面で「編集」ボタンをクリック
2. 必要な項目を修正
   - **GUIフォーム**: 「フォーム入力」タブで簡単に設定（推奨）
   - **JSON直接入力**: 「JSON直接入力」タブで高度な設定
3. 「保存」ボタンをクリック

#### フォームビルダーの使い方

**マッピング定義**:
- 「+ 列を追加」ボタンで行を追加
- 元カラム名（CSVヘッダー）とDBカラム名を入力
- 必須、トリム、変換などのオプションを設定
- 「削除」ボタンで不要な行を削除

**出力項目定義**:
- 「+ 列を追加」ボタンで行を追加
- DBカラム名、表示名、順序、幅を入力
- 「削除」ボタンで不要な行を削除

詳細は以下を参照してください:
- [フォームビルダー使い方ガイド](docs/form_builder_guide.md)
- [区切り文字とクォート文字の使用例](docs/delimiter_examples.md)

**注意**: マッピング定義を変更すると、システムユーザーテーブルが再作成されます（既存データは削除されます）

### 2. データの取り込み方法

#### パターンA: CSV/Excelファイルから取り込み

サンプルCSVファイルが用意されています：
- `tests/sample_data/sample_sap_hr.csv` - SAP人事システム用
- `tests/sample_data/sample_ad.csv` - Active Directory用

取り込み手順：
1. `http://localhost:5000/import` にアクセス
2. システムを選択
3. CSVファイルをアップロード
4. 「アップロード」ボタンをクリック

#### パターンB: Oracle直接参照（DIRECT参照）

既にOracle上にユーザーデータがある場合は、ファイル取り込み不要で直接参照できます。

システム定義での設定：
1. システム定義画面で「取り込み方法」に「Oracle直接参照」を選択
2. 「参照元テーブル/SQL」に以下のいずれかを入力:

**シンプルなテーブル参照:**
```
EXISTING_SCHEMA.USERS
```

**JOIN でコードを名称に変換:**
```sql
SELECT 
    U.USER_CD,
    U.USER_NAME,
    U.DEPT_CD,
    D.DEPT_NAME,
    U.EMAIL
FROM EXISTING_SCHEMA.USERS U
LEFT JOIN EXISTING_SCHEMA.DEPARTMENTS D ON U.DEPT_CD = D.DEPT_CD
WHERE U.IS_ACTIVE = 1
```

**WITH句 でマスターを定義:**
```sql
WITH dept_master AS (
    SELECT '1000' AS DEPT_CD, '総務部' AS DEPT_NAME FROM DUAL UNION ALL
    SELECT '2000', '営業部' FROM DUAL
)
SELECT 
    U.USER_CD,
    U.USER_NAME,
    D.DEPT_NAME
FROM EXISTING_SCHEMA.USERS U
LEFT JOIN dept_master D ON U.DEPT_CD = D.DEPT_CD
```

**特徴:**
- リスト出力時に毎回最新データを参照（データ鮮度が高い）
- ファイル取り込み不要
- マッピング定義不要

#### パターンC: CSV/XLSX取り込み + 追加SQL処理

CSV/XLSXで取り込んだデータに対して、追加のフィルタ処理やJOIN処理が必要な場合の設定です。

システム定義での設定：
1. システム定義画面で「取り込み方法」に「CSV」または「XLSX」を選択
2. マッピング定義を設定（通常のファイル取り込みと同様）
3. 「参照元テーブル/SQL」に追加処理用のSQLを入力（任意）:

**取り込み後のフィルタ処理:**
```sql
SELECT * FROM IDINV_W_SYSTEM_USERS_システムID
WHERE STATUS = 'ACTIVE'
AND DEPT_CD IN ('1000', '2000', '3000')
```

**取り込みデータと既存テーブルのJOIN:**
```sql
SELECT 
    S.USER_CD,
    S.USER_NAME,
    S.STATUS,
    D.DEPT_NAME
FROM IDINV_W_SYSTEM_USERS_システムID S
LEFT JOIN EXISTING_SCHEMA.DEPARTMENTS D ON S.DEPT_CD = D.DEPT_CD
WHERE S.STATUS = 'ACTIVE'
```

**特徴:**
- ファイル取り込み → IDINV_W_SYSTEM_USERS_XXX に格納
- リスト出力時に指定したSQLで追加処理を実行
- 未指定の場合は IDINV_W_SYSTEM_USERS_XXX を直接参照（従来通り）

**重要:** IMPORT_TABLE_NAMEにSQLを指定した場合、出力項目定義やフィルタSQLで参照できるカラムは、SQLの実行結果カラムになります。

### 3. 取り込み状況の確認

トップページ（`http://localhost:5000/`）で以下を確認できます：
- 各システムの最終取り込み日時
- 取り込みレコード数
- 最も古い取り込み日時

## ディレクトリ構成

```
ID_Inventory/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/              # データモデル
│   ├── repositories/        # データアクセス層
│   ├── services/            # ビジネスロジック層
│   ├── utils/               # ユーティリティ
│   ├── blueprints/          # ルーティング
│   ├── static/              # 静的ファイル (CSS/JS)
│   └── templates/           # HTMLテンプレート
├── migrations/              # DBマイグレーション
├── docs/                    # ドキュメント
├── tests/                   # テストコード
├── requirements.txt
├── .env.example
└── run.py
```

## 主要ファイル

- [CLAUDE.md](CLAUDE.md): システム要件定義
- [docs/system_architecture.md](docs/system_architecture.md): システム構成概要
- [docs/database_design.md](docs/database_design.md): データベース設計
- [docs/naming_convention.md](docs/naming_convention.md): 命名規則

## 開発

### コーディング規約

- Pythonコードは PEP 8 に準拠
- Oracleカラム名は大文字統一
- システムIDは小文字スネークケース
- 詳細は [docs/naming_convention.md](docs/naming_convention.md) 参照

### テスト実行

```bash
pytest tests/
```

## デプロイ (Azure App Service)

### 前提条件

- Azure CLIがインストールされていること
- Oracleデータベースへのネットワーク疎通が確保されていること

### デプロイ手順

1. **Azure CLIでログイン**
```bash
az login
```

2. **App Serviceの作成（初回のみ）**
```bash
az webapp up --name id-inventory-app --resource-group your-rg --runtime "PYTHON:3.13" --sku B1
```

3. **起動コマンドの設定**
```bash
az webapp config set --name id-inventory-app --resource-group your-rg --startup-file "startup.txt"
```

4. **環境変数の設定**
```bash
az webapp config appsettings set --name id-inventory-app --resource-group your-rg \
  --settings \
    DB_USER="NAM_IAM_ADMIN" \
    DB_PASSWORD="your_password" \
    DB_HOST="your_oracle_host" \
    DB_PORT="1521" \
    DB_SERVICE="your_service" \
    ALLOWED_NAISETSU_CODES="1234,5678" \
    SECRET_KEY="your_secret_key" \
    UPLOAD_FOLDER="/tmp/uploads" \
    MAX_UPLOAD_SIZE="104857600"
```

5. **デプロイ**
```bash
az webapp up --name id-inventory-app
```

### 認証（Entra ID / App Service Easy Auth）

本システムは Azure App Service の組み込み認証（Easy Auth）による Entra ID 認証を前提とします。
アプリ側では Easy Auth が付与するヘッダ（`X-MS-CLIENT-PRINCIPAL-NAME` = UPN）から
ユーザーを特定し、独自の認可（室コード照合）を行います。

**認可ロジック**:

1. Entra ID の UPN（例: `abc123@nam.co.jp`）から `AUTH_EMAIL_DOMAIN` を除いてユーザーCDを得る（→ `abc123`）
2. `nam_user_admin.e_imdb2_users.USER_CD` と照合し、`NAISETSU`（室コード）を取得
3. `NAISETSU` が `ALLOWED_NAISETSU_CODES` に含まれるユーザーのみログイン可（それ以外は 403）

> ⚠️ ここで扱うログインユーザーの `USER_CD`（e_imdb2_users）は、在籍・異動データ
> （e_imdb_honmu_kenmu 等）の `USER_CD` とは**別体系**であり突き合わせは行いません。

**Easy Auth の有効化**:

```bash
# Entra ID (Microsoft) プロバイダで認証を有効化し、未認証はログインへリダイレクト
az webapp auth update --name id-inventory-app --resource-group your-rg \
  --enabled true \
  --action RedirectToLoginPage \
  --redirect-provider AzureActiveDirectory
```

App Service ポータルの「認証」からも設定可能です。認証済みユーザー情報は App Service が
検証したうえでヘッダに付与するため、アプリ側でトークン検証は行いません。

**認証関連の環境変数**:

```bash
az webapp config appsettings set --name id-inventory-app --resource-group your-rg \
  --settings \
    AUTH_EMAIL_DOMAIN="@nam.co.jp" \
    ALLOWED_NAISETSU_CODES="1234,5678" \
    FLASK_ENV="production"
```

- 本番では `FLASK_ENV=production`（既定）。`development` の場合のみ認証をバイパスします
- `/healthz`（ヘルスチェック）と静的ファイルは認証対象外です

**ローカル開発**:

`FLASK_ENV=development` のとき Easy Auth ヘッダが無くても認証・認可を完全にバイパスし、
`DEV_LOGIN_USER_CD`（既定 `devuser`）をログインユーザーとして扱います。

### Thin モードの利点

このシステムは **python-oracledb の Thin モード**を使用しています：

- ✅ **Oracle Instant Client不要**: 追加のライブラリインストール不要
- ✅ **Pure Python実装**: どの環境でも動作
- ✅ **Azure App Service対応**: 追加設定なしでデプロイ可能
- ✅ **軽量**: メモリ使用量が少ない

### 注意事項

- `/tmp/` ディレクトリはApp Service再起動時にクリアされます
- 一時ファイルは自動クリーンアップされるため問題ありません
- スケールアウト時は各インスタンスが独立した `/tmp/` を持ちます

## トラブルシューティング

### データベース接続エラー

- `.env` ファイルの DB 接続情報を確認
- Oracle Instant Client がインストールされているか確認
- ネットワークの疎通確認

### ファイルアップロードエラー

- ファイルサイズが 100MB 以下か確認
- ファイル形式が CSV または XLSX か確認
- `/tmp/uploads` ディレクトリの書き込み権限を確認

## ライセンス

社内システムのため非公開

## 連絡先

システム管理者まで
