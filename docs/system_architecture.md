# システム構成概要

## システム概要

ID棚卸システムは、複数の社内システムのユーザーIDを一元管理し、在籍状況の確認、退職者ID削除依頼、組織転出者の権限確認を自動化するシステムです。

## アーキテクチャ

### 技術スタック

- **バックエンド**: Python 3.10+ / Flask 3.x
- **データベース**: Oracle Database
- **フロントエンド**: HTML5 / CSS3 / JavaScript (Vanilla JS)
- **外部連携**: Google Sheets API
- **ホスティング**: Azure App Service (Linux)
- **認証**: Azure AD (統合認証想定)

### システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                      クライアント                             │
│                    (社内ネットワーク)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS
┌─────────────────────▼───────────────────────────────────────┐
│                  Azure App Service                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            Flask Application                          │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Web Layer (Blueprint)                          │  │  │
│  │  │  - index.py       (トップページ)                 │  │  │
│  │  │  - output.py      (リスト出力)                   │  │  │
│  │  │  - import.py      (データ取り込み)               │  │  │
│  │  │  - system.py      (システム定義)                 │  │  │
│  │  │  - organization.py (組織変更)                    │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Service Layer                                  │  │  │
│  │  │  - import_service.py                            │  │  │
│  │  │  - export_service.py                            │  │  │
│  │  │  - matching_service.py                          │  │  │
│  │  │  - organization_service.py                      │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Repository Layer                               │  │  │
│  │  │  - system_repository.py                         │  │  │
│  │  │  - user_repository.py                           │  │  │
│  │  │  - organization_repository.py                   │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  /tmp/uploads/  (一時ファイル保管)                   │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
┌───────────────▼───────┐  ┌──────────▼──────────┐
│  Oracle Database      │  │ Google Sheets API   │
│                       │  │                     │
│  - NAM_IAM_ADMIN      │  │                     │
│    schema (IDINV_*)   │  │                     │
│  - nam_user_admin     │  │                     │
│    schema (e_imdb_*   │  │                     │
│    参照のみ)          │  │                     │
└───────────────────────┘  └─────────────────────┘
```

## ディレクトリ構成

```
ID_Inventory/
├── app/
│   ├── __init__.py                    # Flaskアプリケーション初期化
│   ├── config.py                      # 設定管理
│   ├── models/                        # データモデル
│   │   ├── __init__.py
│   │   ├── system.py                  # システム定義モデル
│   │   ├── user.py                    # ユーザー情報モデル
│   │   ├── organization.py            # 組織変更モデル
│   │   └── history.py                 # 履歴モデル
│   ├── repositories/                  # データアクセス層
│   │   ├── __init__.py
│   │   ├── base_repository.py         # 共通リポジトリ基底
│   │   ├── system_repository.py       # システム定義リポジトリ
│   │   ├── user_repository.py         # ユーザー情報リポジトリ
│   │   ├── organization_repository.py # 組織変更リポジトリ
│   │   └── history_repository.py      # 履歴リポジトリ
│   ├── services/                      # ビジネスロジック層
│   │   ├── __init__.py
│   │   ├── import_service.py          # データ取り込みサービス
│   │   ├── export_service.py          # リスト出力サービス
│   │   ├── matching_service.py        # 在籍照合サービス
│   │   ├── organization_service.py    # 組織変更サービス
│   │   └── gsheet_service.py          # Google Sheets連携サービス
│   ├── utils/                         # ユーティリティ
│   │   ├── __init__.py
│   │   ├── file_parser.py             # ファイルパーサー (CSV/Excel)
│   │   ├── validators.py              # バリデーション
│   │   ├── date_utils.py              # 日付ユーティリティ
│   │   └── logger.py                  # ロガー設定
│   ├── blueprints/                    # Blueprintルーティング
│   │   ├── __init__.py
│   │   ├── index.py                   # トップページ
│   │   ├── output.py                  # リスト出力画面
│   │   ├── import_bp.py               # データ取り込み画面
│   │   ├── system.py                  # システム定義画面
│   │   └── organization.py            # 組織変更入力画面
│   ├── static/                        # 静的ファイル
│   │   ├── css/
│   │   │   └── styles.css
│   │   └── js/
│   │       ├── common.js
│   │       ├── output.js
│   │       ├── import.js
│   │       ├── system.js
│   │       └── organization.js
│   └── templates/                     # Jinjaテンプレート
│       ├── base.html                  # 共通レイアウト
│       ├── index.html                 # トップページ
│       ├── output.html                # リスト出力画面
│       ├── import.html                # データ取り込み画面
│       ├── system.html                # システム定義画面
│       └── organization.html          # 組織変更入力画面
├── tests/                             # テストコード
│   ├── __init__.py
│   ├── test_import_service.py
│   ├── test_export_service.py
│   ├── test_matching_service.py
│   └── test_repositories.py
├── docs/                              # ドキュメント
│   ├── database_design.md             # DB設計書
│   ├── system_architecture.md         # システム構成概要
│   ├── api_specification.md           # API仕様書
│   └── templates_example/             # 既存レポートテンプレート
│       ├── アクセス権限棚卸リスト.xltx
│       ├── 転出者アクセス権限確認リスト.xltx
│       └── 退職者（産休）ID削除依頼書V2.xltx
├── migrations/                        # DBマイグレーション
│   ├── 000_grant_imdb_select.sql
│   ├── 001_create_idinv_system_definitions.sql
│   ├── 002_create_idinv_organization_changes.sql
│   ├── 003_create_idinv_import_history.sql
│   └── 004_create_idinv_output_history.sql
├── requirements.txt                   # Python依存パッケージ
├── .env.example                       # 環境変数サンプル
├── .gitignore
├── CLAUDE.md                          # システム要件定義
└── run.py                             # アプリケーションエントリポイント
```

## 主要機能モジュール

### 1. データ取り込み機能 (import_service.py)

**責務**:
- CSV/Excelファイルのアップロード受付
- マッピング定義に基づくデータ変換
- Oracleへのデータ格納
- 取り込み履歴の記録

**処理フロー**:
1. 前回エラー時の古い一時ファイルをクリーンアップ（24時間以上経過したファイル）
2. ファイルアップロード（サーバーローカルディスク `/tmp/uploads/` に一時保存）
3. ファイル形式検証（CSV/XLSX、ファイルサイズ上限100MB）
4. マッピング定義取得（`IDINV_SYSTEM_DEFINITIONS.import_mapping_json`）
5. データ読み込み・変換
6. バリデーション実行
7. トランザクション開始
8. 既存データを全件DELETE（`DELETE FROM IDINV_W_SYSTEM_USERS_{system_id}`）
9. 新規データを全件INSERT（`import_batch_id`に`YYYYMMDD_HHMMSS_{system_id}`形式の値を設定）
10. `IDINV_SYSTEM_DEFINITIONS.last_import_datetime` 更新
11. 取り込み履歴を `IDINV_IMPORT_HISTORY` に記録
12. トランザクションコミット
13. 一時ファイル削除（finally句で確実に削除）

### 2. リスト出力機能 (export_service.py)

**責務**:
- ユーザー棚卸リストの生成
- 退職者ID削除依頼書の生成
- 組織転出者アクセス権限確認リストの生成
- Google Sheetsへの出力

**詳細**: [output_list_design.md](output_list_design.md) 参照

**処理概要**:

#### 2.1 ユーザー棚卸リスト（独立実行）
- 月次実行
- 取り込み状況確認後、実行
- 出力フォーマット: システムごとにシート分割
- 在籍ユーザー属性: 本務所属・兼務所属・役職

#### 2.2 退職者・組織転出者リスト（同時出力）
- **異動日を指定して同時に2つのリストを出力**
- 取り込み状況確認後、実行

**退職者ID削除依頼書**:
- 出力フォーマット: 1シート・横持ち表形式
- 対象: 指定日の退職者のみ
- 表示内容: SQLで定義（taishoku_display_sql）

**組織転出者アクセス権限確認リスト**:
- 出力フォーマット: システムごとにシート分割
- 対象: 指定日の組織転出者のみ（組織コード変更のみは除外）
- 在籍ユーザー属性: 転出元組織・転出先組織（LISTAGGで複数対応）

### 4. 組織変更管理機能 (organization_service.py)

**責務**:
- 組織変更情報の登録
- 組織コード変更の判定
- 転出リスト対象判定

**変更種別判定ロジック**:
- `CODE_ONLY`: 組織コード変更のみ（名称変更なし） → 転出リスト対象外
- `NAME_ONLY`: 組織名変更のみ（コード変更なし） → 転出リスト対象外
- `BOTH`: コード・名称ともに変更 → 転出リスト対象

### 5. Google Sheets連携機能 (gsheet_service.py)

**責務**:
- スプレッドシート作成
- シート作成・書き込み
- フォーマット設定
- 権限設定

**使用ライブラリ**:
- `gspread`
- `google-auth`

## データフロー

### 取り込みフロー
```
[ユーザー] → [Webアップロード] → [/tmp/uploads/] → [Flask App]
                                                        ↓
                                                [ファイルパース]
                                                        ↓
                                                [マッピング変換]
                                                        ↓
                                                [バリデーション]
                                                        ↓
                                                    [Oracle]
                                                        ↓
                                               [一時ファイル削除]
```

### 出力フロー
```
[ユーザー] → [出力指示] → [Flask App]
                              ↓
                        [対象日の転出・退職取得]
                              ↓
                        [各システムユーザー取得]
                              ↓
                        [在籍マスタ照合]
                              ↓
                        [Google Sheets出力]
                              ↓
                        [URL返却]
```

## セキュリティ考慮事項

1. **認証・認可**
   - Azure ADによるSSO認証
   - 社内ネットワーク限定アクセス
   - ロールベースのアクセス制御（管理者/一般ユーザー）

2. **データ保護**
   - HTTPS通信（TLS 1.2以上）
   - 個人情報の暗号化（DBレベル）
   - アップロードファイルの一時保管（処理完了後即削除、エラー時も次回取り込み時にクリーンアップ）
   - ファイル保存時のランダムファイル名生成（UUID、推測不可）

3. **監査ログ**
   - 全操作の履歴記録
   - データ取り込み履歴の保持
   - リスト出力履歴の保持

4. **入力検証**
   - ファイル形式検証
   - ファイルサイズ制限（100MB）
   - SQLインジェクション対策（パラメータ化クエリ）
   - XSS対策（入力サニタイゼーション）

## パフォーマンス要件

- **同時接続**: 10ユーザー
- **ファイル取り込み**: 10,000レコード/分
- **リスト出力**: 100システム × 10,000ユーザー を 5分以内
- **画面応答**: 3秒以内

## 運用要件

### バックアップ
- Oracle: 日次バックアップ
- アプリケーション: Azureスナップショット（週次）

### モニタリング
- Azure Application Insights
- エラーログ監視
- パフォーマンスメトリクス

### メンテナンス
- 取り込み履歴: 2年保持後削除
- 出力履歴: 2年保持後削除
- 一時ファイル: 取り込み処理時に自動クリーンアップ（24時間以上経過したファイルを削除）

