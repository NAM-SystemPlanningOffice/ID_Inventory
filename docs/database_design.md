# データベース設計

## 1. システムユーザー情報定義テーブル (NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS)

### テーブル概要
各システムのユーザー情報の定義を管理するマスタテーブル。
システムごとの項目定義、マッピング情報、出力設定を保持する。

### テーブル構造

```sql
CREATE TABLE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS (
    -- 基本情報
    system_id VARCHAR2(50) PRIMARY KEY,              -- システムID（一意識別子）
    system_name VARCHAR2(200) NOT NULL,              -- システム名
    description VARCHAR2(500),                       -- システム説明
    
    -- 取り込み設定
    import_method VARCHAR2(20),                      -- 取り込み方法（CSV, XLSX, DIRECT）
    import_table_name CLOB,                          -- 取り込み先テーブル名 または 参照SQL（DIRECTの場合）
    import_mapping_json CLOB,                        -- マッピング情報（JSON形式、CSV/XLSX時のみ）
    last_import_datetime TIMESTAMP,                  -- 最終取り込み日時
    last_import_user VARCHAR2(50),                   -- 最終取り込みユーザー
    last_import_record_count NUMBER(10),             -- 最終取り込みレコード数
    
    -- 共通出力設定
    output_required NUMBER(1) DEFAULT 1,             -- 出力要否（0:不要、1:必要）
    output_order NUMBER(3),                          -- 出力順（シート順序）
    output_sheet_name VARCHAR2(100),                 -- 出力シート名

    -- ユーザー棚卸リスト設定
    tanaoroshi_output_columns_json CLOB,             -- 棚卸リスト出力項目定義（JSON形式）
    tanaoroshi_output_mode VARCHAR2(20) DEFAULT 'MISMATCH_ONLY', -- 出力モード（ALL, MISMATCH_ONLY, CUSTOM）
    tanaoroshi_filter_sql CLOB,                      -- カスタムフィルタSQL（CUSTOM時のみ）
    tanaoroshi_sort_sql CLOB,                        -- 棚卸リスト出力ソート順

    -- 組織転出者リスト設定
    tenshutu_output_columns_json CLOB,               -- 転出者リスト出力項目定義（JSON形式）
    tenshutu_filter_sql CLOB,                        -- 転出者リストフィルタSQL（WHERE句）
    tenshutu_sort_sql CLOB,                          -- 転出者リスト出力ソート順

    -- 退職者ID削除依頼書出力設定
    taishoku_output_required NUMBER(1) DEFAULT 1,    -- 退職時出力要否（0:不要、1:必要）
    taishoku_output_order NUMBER(3),                 -- 退職時出力順
    taishoku_display_sql CLOB,                       -- 退職者リスト表示SQL（SELECT句の1列分）
    taishoku_disabled_expression VARCHAR2(500),      -- 無効化済み判定の条件式

    -- 確認情報
    check_frequency VARCHAR2(20) DEFAULT 'MONTHLY',  -- 確認頻度（MONTHLY: 月次, ANNUAL: 年次5月）
    check_responsible VARCHAR2(50),                  -- 確認担当者のユーザーID
    output_scope VARCHAR2(500),                      -- 出力範囲（自由入力）
    check_points VARCHAR2(500),                      -- 確認ポイント（自由入力）
    check_remarks VARCHAR2(500),                     -- 確認に関する備考（自由入力）

    -- 状態管理
    is_active NUMBER(1) DEFAULT 1,                   -- 有効フラグ（0:無効、1:有効）
    remarks VARCHAR2(1000),                          -- 備考
    
    -- システム項目
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,       -- 作成日時
    created_by VARCHAR2(50),                         -- 作成者
    updated_at TIMESTAMP DEFAULT SYSTIMESTAMP,       -- 更新日時
    updated_by VARCHAR2(50)                          -- 更新者
);
```

### 取り込み方法による違い

#### 重要：ロジックの統一

**データ取り込み後の処理は、取り込み方法（DIRECT, CSV, XLSX）に依存せず、`IMPORT_TABLE_NAME` の内容のみで決定されます。**

すべての処理（リスト出力、カラム取得、USER_CDマッチング等）は以下のロジックで動作：

1. **`IMPORT_TABLE_NAME` にSQLが含まれているか判定**
   - `SELECT` または `WITH` で始まる → SQL
   - それ以外 → テーブル名

2. **SQLの場合:**
   - 指定したSQLを実行してデータ取得
   - USER_CDマッチングはSQLの結果の `USER_CD` カラムで実行
   - 出力項目定義の「システム」カラムは、SQLの実行結果カラムから取得
   - 棚卸フィルタSQL（`tanaoroshi_filter_sql`）で、SQLの結果カラムを `s.カラム名` で参照可能

3. **テーブル名の場合:**
   - テーブルから直接データ取得
   - USER_CDマッチングはテーブルの `USER_CD` カラムで実行
   - 出力項目定義の「システム」カラムは、テーブルのカラムから取得
   - 棚卸フィルタSQL（`tanaoroshi_filter_sql`）で、テーブルのカラムを `s.カラム名` で参照可能

#### DIRECT（Oracle直接参照）
- **用途**: 既にOracle上にあるユーザーデータを参照
- **データ鮮度**: リスト出力時に毎回最新データを参照
- **import_table_name**: テーブル名 または SQL文を指定（必須）
  - シンプル: `SCHEMA.TABLE_NAME` → 自動で`SELECT *`付与
  - JOIN: `SELECT U.USER_CD, D.DEPT_NAME FROM SCHEMA.USERS U LEFT JOIN SCHEMA.DEPT D ON ...`
  - WITH句: `WITH temp AS (...) SELECT ... FROM temp`
- **import_mapping_json**: 不要（NULL）
- **IDINV_W_SYSTEM_USERS_XXXテーブル**: 作成されない
- **同期処理**: 不要（リスト出力時に毎回直接参照）

#### CSV / XLSX（ファイル取り込み）
- **用途**: 外部システムからエクスポートしたファイルを取り込み
- **データ鮮度**: 最終取り込み時点の情報
- **import_table_name**: 
  - デフォルト: `IDINV_W_SYSTEM_USERS_システムID` 形式（未指定時）
  - カスタム: SQLを指定可能（取り込み後の追加処理が必要な場合）
    - テーブル: `IDINV_W_SYSTEM_USERS_システムID` のみ参照
    - SQL: `SELECT * FROM IDINV_W_SYSTEM_USERS_XXX WHERE STATUS = 'ACTIVE'` 等の加工処理
- **import_mapping_json**: 必須（カラムマッピング定義）
- **IDINV_W_SYSTEM_USERS_XXXテーブル**: 自動作成される
- **同期処理**: データ取り込み画面からファイルアップロード → テーブルに格納
- **注意**: IMPORT_TABLE_NAMEにSQLを指定した場合、出力項目定義で選択できるカラムはSQLの実行結果カラムになります

### JSON形式の項目定義例

#### import_mapping_json（マッピング情報）
```json
{
  "file_encoding": "shift-jis",
  "has_header": true,
  "skip_rows": 0,
  "columns": [
    {
      "source_column": "ユーザーID",
      "source_index": 0,
      "target_column": "USER_CD",
      "data_type": "string",
      "required": true,
      "trim": true,
      "comment": "必須：在籍マスタとの紐付けキー"
    },
    {
      "source_column": "氏名",
      "source_index": 1,
      "target_column": "USER_NAME",
      "data_type": "string",
      "required": true,
      "trim": true
    },
    {
      "source_column": "所属コード",
      "source_index": 2,
      "target_column": "DEPARTMENT_CD",
      "data_type": "string",
      "required": false,
      "trim": true
    },
    {
      "source_column": "所属名",
      "source_index": 3,
      "target_column": "DEPARTMENT_NAME",
      "data_type": "string",
      "required": false,
      "trim": true
    },
    {
      "source_column": "メールアドレス",
      "source_index": 4,
      "target_column": "EMAIL",
      "data_type": "string",
      "required": false,
      "trim": true,
      "transform": "lowercase"
    }
  ]
}
```

#### output_columns_json（共通出力項目定義：棚卸リスト・組織転出者リスト）

棚卸リストと組織転出者リストは、各システム固有の出力項目（ユーザー情報）が同じです。
在籍ユーザー属性（本務/兼務、転出元/転出先）は異なりますが、システム側のカラムは共通で定義します。

```json
{
  "columns": [
    {
      "column_name": "USER_CD",
      "display_name": "ユーザーID",
      "order": 1,
      "width": 15,
      "format": "text",
      "required": true
    },
    {
      "column_name": "USER_NAME",
      "display_name": "氏名",
      "order": 2,
      "width": 20,
      "format": "text",
      "required": true
    },
    {
      "column_name": "DEPARTMENT_CD",
      "display_name": "所属コード",
      "order": 3,
      "width": 12,
      "format": "text",
      "required": false
    },
    {
      "column_name": "DEPARTMENT_NAME",
      "display_name": "所属名",
      "order": 4,
      "width": 30,
      "format": "text",
      "required": false
    },
    {
      "column_name": "EMAIL",
      "display_name": "メールアドレス",
      "order": 5,
      "width": 30,
      "format": "text",
      "required": false
    }
  ]
}
```

**補足**:
- 棚卸リストでは、在籍ユーザー属性（本務所属・兼務所属・役職）がシステム固有項目の前に自動付与される
- 組織転出者リストでは、在籍ユーザー属性（転出元組織・転出先組織）がシステム固有項目の前に自動付与される
- システム固有項目（上記定義）は両リストで共通
- システムによって項目が存在しない場合は、該当カラムを定義から除外する

#### taishoku_display_sql（退職者リスト表示SQL）

退職者ID削除依頼書は、1行に1ユーザー、横にシステムを並べる表形式で出力します。
各システムの列に表示する内容を、SQL（SELECT句の1列分）として定義します。

**設定例**

**例1: 条件分岐で表示を変える**
```sql
-- suspended=Trueの場合は'suspended'、それ以外はaccount_statusを表示
-- さらに、enabledでexpiry_dateがある場合は期限付きで表示
CASE 
    WHEN s.suspended = 'True' THEN 'suspended'
    WHEN s.account_status = 'enabled' AND s.expiry_date IS NOT NULL 
        THEN s.account_status || '(' || TO_CHAR(s.expiry_date, 'YYYY/MM') || ')'
    ELSE s.account_status
END
```

**例2: システム固有IDを表示**
```sql
-- 名寄せ用のuser_cdとは別の、システム固有のIDを表示
s.system_user_id
```

**例3: シンプルにアカウント状態**
```sql
s.account_status
```

**例4: DECODE関数を使用**
```sql
DECODE(s.is_active, 1, 'enabled', 0, 'disabled', 'unknown')
```

**例5: 複数項目を組み合わせ**
```sql
s.account_status || CASE WHEN s.expiry_date IS NOT NULL 
    THEN '(期限:' || TO_CHAR(s.expiry_date, 'YYYY/MM/DD') || ')' 
    ELSE '' 
END
```

**補足**:
- テーブルエイリアスは必ず `s` を使用（SQL生成時に動的に置換）
- NULLの場合は自動的に '－' に置換される
- 未設定（NULL）の場合は、デフォルトで `s.account_status` を使用


### 棚卸リスト出力モードと設定例

#### 出力モード（tanaoroshi_output_mode）

| モード | 説明 | filter_sql |
|-------|------|-----------|
| `ALL` | 全ユーザー出力 | NULL |
| `MISMATCH_ONLY` | 在籍マッチング不可のみ出力（デフォルト） | NULL |
| `CUSTOM` | カスタムフィルタ適用 | WHERE句を設定 |

#### 設定例

**例1: 全ユーザー出力**
```sql
tanaoroshi_output_mode = 'ALL'
tanaoroshi_filter_sql = NULL
```

**例2: 在籍マッチング不可のみ出力（標準）**
```sql
tanaoroshi_output_mode = 'MISMATCH_ONLY'
tanaoroshi_filter_sql = NULL
```

**例3: Disableユーザーを除外**
```sql
tanaoroshi_output_mode = 'CUSTOM'
tanaoroshi_filter_sql = 'ACCOUNT_STATUS != ''Disabled'''
```

**例4: 一般権限ユーザーを除外**
```sql
tanaoroshi_output_mode = 'CUSTOM'
tanaoroshi_filter_sql = 'PERMISSION_LEVEL NOT IN (''User'', ''Guest'')'
```

**例5: 複数条件（Disable除外 AND 在籍マッチング不可）**
```sql
tanaoroshi_output_mode = 'CUSTOM'
tanaoroshi_filter_sql = 'ACCOUNT_STATUS != ''Disabled'' AND matching_status != ''MATCH'''
```

### 補足
- ユーザー棚卸リストは `tanaoroshi_output_columns_json` を使用
- 退職者リストは `taishoku_output_columns_json` を使用（アカウント状態と有効期限のみ）
- 組織転出者リストは `tenshutu_output_columns_json` を使用
- システムによって項目が存在しない場合は、該当カラムを定義から除外する
- `tanaoroshi_filter_sql` は WHERE句の条件部分のみを記載（WHERE キーワードは不要）

## 2. 各システムのユーザーデータテーブル（動的テーブル）

### テーブル命名規則
`NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_{system_id}`

### 運用方針
- **取り込み時の処理**: 毎回全件DELETE→INSERTで更新
- **項目変更対応**: テーブル構造変更が必要な場合はDROP→CREATE
- **データ量**: 1システムあたり数百件程度を想定
- **インデックス**: データ量が少ないため不要

### 共通カラム構造
```sql
CREATE TABLE NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_{system_id} (
    import_batch_id VARCHAR2(50),                        -- 取り込みバッチID (YYYYMMDD_HHMMSS_{system_id}形式)
    
    -- 必須項目（在籍情報との紐付けに使用）
    user_cd VARCHAR2(50) NOT NULL,                       -- ユーザーコード（必須、在籍マスタとのキー項目）
    user_name VARCHAR2(200),                             -- ユーザー名（共通）
    
    -- システム固有項目（動的に作成）
    -- ... その他システム固有項目（マッピング定義に基づき動的に追加）
);
```

**重要な制約**:
- **`user_cd` は必須項目**: 在籍マスタ（e_imdb_honmu_kenmu、e_imdb_sankyu）との紐付けに使用
- **カラム名は必ず `user_cd`**: 他の名前は使用不可
- **マッピング定義で `USER_CD` を必須指定**: `required: true`

### テーブル作成・更新の運用フロー

#### 初回作成時
1. `IDINV_SYSTEM_DEFINITIONS` にシステム定義を登録
2. マッピング定義に基づき `IDINV_W_SYSTEM_USERS_{system_id}` を CREATE
3. データ取り込み実行

#### データ取り込み時
1. トランザクション開始
2. `DELETE FROM NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_{system_id}` で全件削除
3. 新規データを INSERT
4. `IDINV_SYSTEM_DEFINITIONS.last_import_datetime` 更新
5. トランザクションコミット

#### 項目定義変更時
1. `IDINV_SYSTEM_DEFINITIONS.import_mapping_json` を更新
2. 既存テーブルを DROP
3. 新しい構造で CREATE
4. データ再取り込み

### テーブル作成DDL例
```sql
-- 例: system_id = "SAP_HR" の場合
CREATE TABLE NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_SAP_HR (
    import_batch_id VARCHAR2(50),
    user_cd VARCHAR2(50) NOT NULL,          -- 必須：在籍マスタとの紐付けキー
    user_name VARCHAR2(200),
    department_cd VARCHAR2(50),
    department_name VARCHAR2(200),
    email VARCHAR2(200)
);
```

## 3. 組織変更テーブル (NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES)

```sql
CREATE TABLE NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES (
    change_date DATE NOT NULL,                                  -- 変更日
   
    -- 変更前情報
    before_org_cd VARCHAR2(10) NOT NULL,                        -- 変更前組織コード
    before_org_name VARCHAR2(200),                              -- 変更前組織名
    
    -- 変更後情報
    after_org_cd VARCHAR2(10) NOT NULL,                         -- 変更後組織コード
    after_org_name VARCHAR2(200),                               -- 変更後組織名
    
    -- 備考
    remarks VARCHAR2(1000)                                     -- 備考
    );


## 4. 取り込み履歴テーブル (NAM_IAM_ADMIN.IDINV_IMPORT_HISTORY)

```sql
CREATE TABLE NAM_IAM_ADMIN.IDINV_IMPORT_HISTORY (
    batch_id VARCHAR2(50) PRIMARY KEY,                   -- バッチID
    system_id VARCHAR2(50) NOT NULL,                     -- システムID
    import_datetime TIMESTAMP DEFAULT SYSTIMESTAMP,      -- 取り込み日時
    import_user VARCHAR2(50),                            -- 取り込みユーザー
    
    -- ファイル情報
    file_name VARCHAR2(500),                             -- ファイル名
    file_size NUMBER(15),                                -- ファイルサイズ（バイト）
    file_hash VARCHAR2(64),                              -- ファイルハッシュ（SHA-256）
    
    -- 処理結果
    status VARCHAR2(20),                                 -- 処理状態（SUCCESS, ERROR, WARNING）
    total_records NUMBER(10),                            -- 総レコード数
    success_records NUMBER(10),                          -- 成功レコード数
    error_records NUMBER(10),                            -- エラーレコード数
    error_message CLOB,                                  -- エラーメッセージ
    
    -- 処理時間
    start_time TIMESTAMP,                                -- 開始時刻
    end_time TIMESTAMP,                                  -- 終了時刻
    
    CONSTRAINT fk_import_system FOREIGN KEY (system_id) 
        REFERENCES NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS(system_id)
);

-- インデックス
CREATE INDEX idx_import_history_system ON NAM_IAM_ADMIN.IDINV_IMPORT_HISTORY(system_id);
CREATE INDEX idx_import_history_datetime ON NAM_IAM_ADMIN.IDINV_IMPORT_HISTORY(import_datetime);
CREATE INDEX idx_import_history_status ON NAM_IAM_ADMIN.IDINV_IMPORT_HISTORY(status);
```

## 5. リスト出力履歴テーブル (NAM_IAM_ADMIN.IDINV_OUTPUT_HISTORY)

```sql
CREATE TABLE NAM_IAM_ADMIN.IDINV_OUTPUT_HISTORY (
    output_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- 出力ID
    output_type VARCHAR2(50) NOT NULL,                          -- 出力種別（TANAOROSHI, TAISHOKU, TENSHUTU）
    output_datetime TIMESTAMP DEFAULT SYSTIMESTAMP,             -- 出力日時
    output_user VARCHAR2(50),                                   -- 出力ユーザー
    
    -- 対象日
    target_date DATE,                                           -- 対象日
    target_month VARCHAR2(7),                                   -- 対象月（YYYY-MM）
    
    -- 出力結果
    spreadsheet_url VARCHAR2(500),                              -- スプレッドシートURL
    status VARCHAR2(20),                                        -- 処理状態（SUCCESS, ERROR）
    total_systems NUMBER(5),                                    -- 出力システム数
    total_users NUMBER(10),                                     -- 出力ユーザー数
    error_message CLOB,                                         -- エラーメッセージ
    
    -- システム項目
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- インデックス
CREATE INDEX idx_output_history_type ON NAM_IAM_ADMIN.IDINV_OUTPUT_HISTORY(output_type);
CREATE INDEX idx_output_history_date ON NAM_IAM_ADMIN.IDINV_OUTPUT_HISTORY(target_date);
CREATE INDEX idx_output_history_datetime ON NAM_IAM_ADMIN.IDINV_OUTPUT_HISTORY(output_datetime);
```

## データ整合性制約

- `IDINV_SYSTEM_DEFINITIONS.system_id` は各システムの一意識別子
- `IDINV_W_SYSTEM_USERS_{system_id}` テーブルは `system_id` ごとに動的に作成
- `IDINV_W_SYSTEM_USERS_{system_id}` は毎回全件DELETE→INSERTで更新（履歴は保持しない）
- `import_batch_id` は `YYYYMMDD_HHMMSS_{system_id}` 形式（この値から取り込み日時を特定可能）
- **`user_cd` は全システム必須**: 在籍マスタとの紐付けに使用、カラム名は必ず `user_cd`
- JSON項目は適切なバリデーションを実施してから格納
- 履歴データ（`IDINV_IMPORT_HISTORY`, `IDINV_OUTPUT_HISTORY`）は物理削除しない
