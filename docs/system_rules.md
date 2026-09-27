# システム設計ルール

## 必須項目と命名規則

### 1. user_cd（ユーザーコード）の必須化

#### ルール
- **全システムで `user_cd` は必須項目**
- **カラム名は必ず `user_cd`**（他の名前は使用不可）
- **NOT NULL 制約を付与**

#### 理由
- 在籍マスタ（`e_imdb_honmu_kenmu`, `e_imdb_sankyu`）との紐付けに使用
- 退職者マスタ（`e_imdb_users_end`）との紐付けに使用
- 組織異動マスタ（`e_imdb_ido`）との紐付けに使用

#### 実装上の制約

**テーブル作成時**:
```sql
CREATE TABLE NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_{system_id} (
    import_batch_id VARCHAR2(50),
    user_cd VARCHAR2(50) NOT NULL,  -- 必須
    ...
);
```

**マッピング定義時**:
```json
{
  "columns": [
    {
      "source_column": "ユーザーID",
      "target_column": "USER_CD",
      "required": true  -- 必須指定
    }
  ]
}
```

**バリデーション**:
- データ取り込み時に `user_cd` が NULL のレコードはエラー
- マッピング定義に `USER_CD` が存在しない場合はエラー

### 2. import_batch_id（取り込みバッチID）

#### ルール
- **全システムで共通の固定項目**
- **フォーマット**: `YYYYMMDD_HHMMSS_{system_id}`

#### 例
```
20260625_143025_SAP_HR
20260625_150130_SALESFORCE
```

#### 用途
- 取り込み日時の特定
- 最新データの識別（MAX(import_batch_id)）

### 3. システム固有項目

#### ルール
- `user_cd`, `user_name` 以外はシステムごとに自由に定義可能
- `output_columns_json` で出力項目を定義

#### 一般的な項目例
- `department_cd` （所属コード）
- `department_name` （所属名）
- `email` （メールアドレス）
- `account_status` （アカウント状態）
- `system_user_id` （システム固有ID）

## データ取り込みルール

### 1. 全件リフレッシュ方式

```sql
BEGIN
    -- 1. 全件削除
    DELETE FROM IDINV_W_SYSTEM_USERS_{system_id};
    
    -- 2. 新規データ挿入
    INSERT INTO IDINV_W_SYSTEM_USERS_{system_id} VALUES (...);
    
    -- 3. コミット
    COMMIT;
END;
```

### 2. バリデーションルール

#### 必須チェック
- `user_cd` が NULL または空文字列 → エラー
- マッピング定義で `required: true` の項目が NULL → エラー

#### 重複チェック
- 同一ファイル内で `user_cd` が重複 → 警告（後勝ち）

#### データ型チェック
- マッピング定義の `data_type` に従って変換
- 変換失敗 → エラー

### 3. エラーハンドリング

```python
def validate_import_data(data, mapping):
    """
    取り込みデータのバリデーション
    """
    errors = []
    
    # user_cd の存在チェック
    user_cd_column = None
    for col in mapping['columns']:
        if col['target_column'].upper() == 'USER_CD':
            user_cd_column = col
            break
    
    if not user_cd_column:
        raise ValueError("マッピング定義に USER_CD が存在しません")
    
    if not user_cd_column.get('required'):
        raise ValueError("USER_CD は required: true を指定してください")
    
    # データのバリデーション
    for idx, row in enumerate(data):
        user_cd = row.get('user_cd')
        if not user_cd or str(user_cd).strip() == '':
            errors.append(f"行 {idx + 1}: user_cd が空です")
    
    if errors:
        raise ValueError('\n'.join(errors))
    
    return True
```

## 出力ルール

### 1. 棚卸リスト・組織転出者リスト

**在籍ユーザー属性の自動付与**:
```sql
LEFT JOIN zaiseki z ON s.user_cd = z.user_cd
```

- `user_cd` をキーに在籍マスタと結合
- 在籍していない場合は空白

### 2. 退職者リスト

**退職者の抽出**:
```sql
INNER JOIN e_imdb_users_end t 
    ON s.user_cd = t.user_cd 
    AND t.taisha_date = :target_date
```

- `user_cd` をキーに退職者マスタと結合

### 3. 組織転出者リスト

**転出者の抽出**:
```sql
INNER JOIN e_imdb_ido i 
    ON s.user_cd = i.user_cd 
    AND i.ido_date = :target_date
```

- `user_cd` をキーに異動マスタと結合

## テーブル管理ルール

### 1. テーブル作成

```python
def create_system_table(system_id, mapping):
    """
    システムユーザーテーブルを作成
    """
    columns = [
        "import_batch_id VARCHAR2(50)",
        "user_cd VARCHAR2(50) NOT NULL"  # 必須
    ]
    
    for col in mapping['columns']:
        if col['target_column'].upper() in ['IMPORT_BATCH_ID', 'USER_CD']:
            continue  # 既に定義済み
        
        col_name = col['target_column'].lower()
        col_type = get_oracle_type(col['data_type'])
        columns.append(f"{col_name} {col_type}")
    
    ddl = f"""
        CREATE TABLE NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_{system_id} (
            {',\n            '.join(columns)}
        )
    """
    
    return ddl
```

### 2. テーブル削除・再作成

**項目定義変更時**:
```python
def recreate_system_table(system_id, new_mapping):
    """
    項目定義変更時にテーブルを再作成
    """
    # 1. 既存テーブル削除
    db.execute(f"DROP TABLE NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_{system_id}")
    
    # 2. 新しいテーブル作成
    ddl = create_system_table(system_id, new_mapping)
    db.execute(ddl)
    
    # 3. マッピング定義更新
    update_mapping(system_id, new_mapping)
```

## 命名規則

### 1. テーブル名

| 種類 | 命名規則 | 例 |
|-----|---------|---|
| システム定義マスタ | `IDINV_SYSTEM_DEFINITIONS` | 固定 |
| システムユーザーテーブル | `IDINV_W_SYSTEM_USERS_{system_id}` | `IDINV_W_SYSTEM_USERS_SAP_HR` |
| 組織変更マスタ | `IDINV_ORGANIZATION_CHANGES` | 固定 |
| 取り込み履歴 | `IDINV_IMPORT_HISTORY` | 固定 |
| 出力履歴 | `IDINV_OUTPUT_HISTORY` | 固定 |

### 2. カラム名

| 種類 | 命名規則 | 必須 |
|-----|---------|-----|
| 取り込みバッチID | `import_batch_id` | ○ |
| ユーザーコード | `user_cd` | ○ |
| ユーザー名 | `user_name` | - |
| その他 | 任意（スネークケース推奨） | - |

### 3. system_id

**ルール**:
- 英数字とアンダースコアのみ
- 大文字推奨
- 50文字以内

**例**:
- `SAP_HR`
- `SALESFORCE`
- `AWS_IAM`
- `GOOGLE_WORKSPACE`

## セキュリティルール

### 1. SQLインジェクション対策

**禁止事項**:
- `system_id` をそのままSQL文字列に埋め込まない
- ユーザー入力を直接SQL文字列に結合しない

**推奨方法**:
```python
# NG: SQLインジェクションのリスク
sql = f"SELECT * FROM IDINV_W_SYSTEM_USERS_{system_id}"

# OK: system_id をバリデーション後に使用
if not re.match(r'^[A-Z0-9_]+$', system_id):
    raise ValueError("Invalid system_id")
sql = f"SELECT * FROM IDINV_W_SYSTEM_USERS_{system_id}"
```

### 2. アクセス制御

**ルール**:
- このシステムを利用できる室のコードを `.env` で定義
- `e_imdb2_users.naisetsu` と照合してログイン制御

```python
# .env
ALLOWED_DEPARTMENTS=1000,1001,1002

# ログインチェック
def check_access(user_cd):
    user = db.query("SELECT naisetsu FROM e_imdb2_users WHERE user_cd = :1", user_cd)
    allowed = os.getenv('ALLOWED_DEPARTMENTS').split(',')
    return user.naisetsu in allowed
```

## バックアップ・リカバリルール

### 1. データバックアップ

- Oracleデータベース: 日次フルバックアップ（DBA担当）
- システムユーザーテーブル: 論理バックアップ不要（ソースファイルから再取り込み可能）

### 2. 取り込みエラー時の復旧

```python
def import_with_rollback(system_id, data):
    """
    エラー時は全てロールバック
    """
    try:
        db.begin()
        db.execute(f"DELETE FROM IDINV_W_SYSTEM_USERS_{system_id}")
        db.bulk_insert(f"IDINV_W_SYSTEM_USERS_{system_id}", data)
        db.commit()
    except Exception as e:
        db.rollback()
        raise
```

### 3. 履歴の保持

- 取り込み履歴（`IDINV_IMPORT_HISTORY`）: 2年保持
- 出力履歴（`IDINV_OUTPUT_HISTORY`）: 1年保持
- 一時ファイル: 処理完了後削除（エラー時は次回取り込み時にクリーンアップ）
