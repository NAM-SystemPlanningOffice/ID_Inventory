# リスト出力機能の実装

## 概要

ID棚卸システムのリスト出力機能を実装しました。

## 実装した機能

### 1. ユーザー棚卸リスト
- 現時点の状態を出力（対象月の指定は不要）
- 在籍ユーザーとの照合を行い、システムごとにGoogle Spreadsheetに出力
- 不一致のあるユーザーを抽出

### 2. 退職者ID削除依頼書・組織転出者アクセス権限確認リスト
- 過去60日間の退職・異動日のリストを表示
- 日付を選択してリストを出力
- 退職者リストと転出者リストを同時に生成

## 実装ファイル

### バックエンド

1. **app/repositories/user_repository.py**
   - `get_taishoku_ido_dates()`: 過去60日間の退職・異動日リストを取得
   - SQLで退職者と異動者の件数を集計

2. **app/services/output_service.py**
   - `get_taishoku_ido_dates()`: 日付リストを取得するサービスメソッド
   - `generate_tanaoroshi_list()`: 対象月パラメータを削除（現時点の状態を出力）

3. **app/blueprints/output.py**
   - `GET /output/dates`: 退職・異動日リストを取得するエンドポイント
   - `POST /output/tanaoroshi`: 棚卸リスト生成（対象月パラメータ削除）
   - `POST /output/taishoku-tenshutu`: 退職者・転出者リスト生成

4. **app/repositories/base_repository.py**
   - 日付データをISO形式文字列に変換
   - 大文字・小文字両方のキーをサポート

### フロントエンド

1. **app/templates/output.html**
   - 棚卸リスト: 対象月入力フィールドを削除
   - 退職者・転出者リスト: 日付セレクトボックスを追加
   - ローディング表示、エラーメッセージ表示を追加

2. **app/static/js/output.js**
   - ページ読み込み時に日付リストを取得
   - 日付データを日本語形式でセレクトボックスに表示
   - 棚卸リスト生成処理を対象月なしに変更

3. **app/static/css/styles.css**
   - ローディング表示、エラーメッセージ、フォームコントロールのスタイルを追加

## SQL仕様

### 退職・異動日リスト取得

```sql
SELECT ido_date AS "IDO_DATE",
       SUM(taisha) AS "TAISHA_COUNT",
       SUM(ido) AS "IDO_COUNT"
FROM (
    SELECT TAISHA_DATE AS ido_date, USER_CD AS user_cd, 1 AS taisha, 0 AS ido
    FROM NAM_USER_ADMIN.E_IMDB_USERS_END
    WHERE DEPARTMENT_MAIN = 1
      AND TAISHA_DATE > SYSDATE - 60
      AND TAISHA = 1
    UNION
    SELECT DISTINCT IDO_DATE AS ido_date, USER_CD AS user_cd, 0 AS taisha, 1 AS ido
    FROM NAM_USER_ADMIN.E_IMDB_IDO
    WHERE IDO_DATE > SYSDATE - 60
)
GROUP BY ido_date
ORDER BY ido_date DESC
```

## Google Spreadsheet出力機能

### 実装済み

**認証方式:**
- サービスアカウント認証 + 代理ユーザー（Domain-wide Delegation）
- `.env`で以下を設定:
  - `GOOGLE_CREDENTIALS_JSON`: サービスアカウントの認証情報JSONファイルパス
  - `DELEGATED_USER_EMAIL`: 代理ユーザーのメールアドレス
  - `GOOGLE_DRIVE_FOLDER_ID`: スプレッドシート作成先のGoogle DriveフォルダID

**出力形式:**
- ファイル名にタイムスタンプを付与して毎回新規作成
  - 例: `ユーザー棚卸リスト_20260702_143025`
- 指定したGoogle Driveフォルダに作成
- システムごとに別シートで出力
- ヘッダー行は太字・背景色でフォーマット

**実装ファイル:**
- [app/utils/google_sheets.py](../app/utils/google_sheets.py) - Google Sheets API操作クラス
- [app/services/output_service.py](../app/services/output_service.py) - 各リスト生成処理
- [app/config.py](../app/config.py) - Google API設定

### 出力リスト詳細

1. **ユーザー棚卸リスト**
   - 在籍ユーザーと不一致のユーザーのみ出力
   - 各システムを別シートで出力
   - 列: ユーザーCD、ユーザー名、所属、本務、兼務

2. **退職者ID削除依頼書**
   - 指定日の退職者でシステムに存在するユーザーを出力
   - 各システムを別シートで出力
   - 列: ユーザーCD、ユーザー名、所属コード、所属名、役職コード、役職名、退職日

3. **組織転出者アクセス権限確認リスト**
   - 指定日の異動者でシステムに存在するユーザーを出力
   - 異動前/異動後の情報を並べて表示
   - 各システムを別シートで出力
   - 列: ユーザーCD、ユーザー名、異動前所属コード、異動前所属名、異動前役職コード、異動前役職名、異動後所属コード、異動後所属名、異動後役職コード、異動後役職名、異動日

## 今後の実装予定

### 組織変更対応
- 組織変更情報との照合
- 組織コード変更による対象外判定ロジック
- `IDINV_ORGANIZATION_CHANGES`テーブルとの照合処理実装
