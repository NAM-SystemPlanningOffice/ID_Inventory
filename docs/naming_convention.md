# 命名規則・コーディング規約

## カラム名の命名規則

### 基本方針: **すべて大文字に統一**

Oracleはダブルクォートなしの識別子を内部的に大文字に変換するため、すべてのカラム名を大文字で統一します。

### 1. Oracleテーブル定義

```sql
-- 正しい例
CREATE TABLE NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_SYSTEM_A (
    IMPORT_BATCH_ID VARCHAR2(50),
    USER_CD VARCHAR2(50),
    USER_NAME VARCHAR2(200),
    DEPARTMENT_CD VARCHAR2(50),
    DEPARTMENT_NAME VARCHAR2(200),
    EMAIL VARCHAR2(200)
);
```

### 2. JSON定義（import_mapping_json, output_columns_json）

```json
{
  "columns": [
    {
      "source_column": "ユーザーID",
      "target_column": "USER_CD",
      "data_type": "string"
    }
  ]
}
```

- **target_column**: 必ず大文字（Oracleカラム名と一致）
- **source_column**: ファイルヘッダーの表記通り

### 3. SQL内での参照（大文字に統一）

```sql
-- 推奨: すべて大文字
SELECT USER_CD, USER_NAME 
FROM NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_SYSTEM_A
WHERE IMPORT_BATCH_ID = :BATCH_ID;
```

### 4. Pythonコード

```python
# oracledb / cx_Oracle の結果セットは大文字
cursor.execute("""
    SELECT USER_CD, USER_NAME 
    FROM NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_SYSTEM_A
""")
row = cursor.fetchone()

# 大文字で参照
user_cd = row['USER_CD']
user_name = row['USER_NAME']
```

## 必須カラム: USER_CD

### すべてのシステムユーザーテーブルに必須

| 項目 | 内容 |
|-----|------|
| **カラム名** | `USER_CD` （必ず大文字） |
| **型** | `VARCHAR2(50)` |
| **NULL可否** | NOT NULL |
| **用途** | 在籍ユーザー情報との紐付けキー |

### データソースとの紐付け

| データソース | カラム名 | 説明 |
|------------|---------|------|
| E_IMDB_HONMU_KENMU | USER_CD | 在籍ユーザー（通常） |
| E_IMDB_SANKYU | USER_CD | 産育休ユーザー |
| E_IMDB_USERS_END | USER_CD | 退職者 |
| E_IMDB_IDO | USER_CD | 組織異動者 |

### バリデーション

#### テーブル作成時
- `USER_CD` カラムが存在しない場合はエラー
- 型が `VARCHAR2` でない場合は警告

#### データ取り込み時
- `import_mapping_json` に `target_column: "USER_CD"` が存在しない場合はエラー
- データ内に `USER_CD` が NULL のレコードがある場合はエラー

```python
def validate_import_data(data, mapping):
    """
    取り込みデータのバリデーション
    """
    # USER_CD カラムが存在するか
    has_user_cd = any(
        col['target_column'] == 'USER_CD' 
        for col in mapping['columns']
    )
    if not has_user_cd:
        raise ValueError("マッピング定義に USER_CD が存在しません")
    
    # データ内に NULL がないか
    for idx, row in enumerate(data):
        if not row.get('USER_CD'):
            raise ValueError(f"行{idx + 1}: USER_CD が NULL です")
```

## テーブル命名規則

### スキーマとプレフィックス

- **スキーマ**: 本システムのオブジェクトはすべて `NAM_IAM_ADMIN` に作成する。
- **プレフィックス**: 他アプリと同居するため、全テーブルに `IDINV_` を付与する。
  - 旧命名の `M_`/`T_`（マスタ／トランザクションを表す接頭辞）は廃止。
  - CSV/XLSX取り込みや一時利用の作業テーブルには、`IDINV_W_`（W = Work）を付与する。
- 制約名・インデックス名にも `IDINV_` を付与し、共有スキーマ内での名前衝突を避ける。

### システムユーザーテーブル

```
NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_{SYSTEM_ID}
```

**ルール**:
- プレフィックス: `IDINV_W_SYSTEM_USERS_`
- サフィックス: `SYSTEM_ID` （コード内で `system_id.upper()` により大文字化して使用）

**例**:
- `IDINV_W_SYSTEM_USERS_SAP_HR`
- `IDINV_W_SYSTEM_USERS_SALESFORCE`
- `IDINV_W_SYSTEM_USERS_AWS_IAM`

### 各テーブルの名称

| 用途 | テーブル名 |
|-----|-----------|
| システム定義マスタ | `IDINV_SYSTEM_DEFINITIONS` |
| 組織変更情報 | `IDINV_ORGANIZATION_CHANGES` |
| 取り込み履歴 | `IDINV_IMPORT_HISTORY` |
| リスト出力履歴 | `IDINV_OUTPUT_HISTORY` |
| 各システムのユーザーデータ（動的） | `IDINV_W_SYSTEM_USERS_{SYSTEM_ID}` |
| 組織転出者一時テーブル | `IDINV_W_TENSHUTU_TEMP` |

### 外部データソース（参照専用・据え置き）

在籍・退職・異動・認証情報（`e_imdb_*`）や DIRECT 参照先の既存テーブルは、
他システム管轄のため `nam_user_admin` 等のスキーマに残す。本システムは SELECT のみ行い、
所有者側で `NAM_IAM_ADMIN` へ SELECT 権限を付与する（`migrations/000_grant_imdb_select.sql`）。

## システムID命名規則

### ルール
- **小文字**
- **スネークケース** （単語区切りはアンダースコア）
- **英数字とアンダースコアのみ**
- **最大50文字**

### 例

| システム名 | system_id |
|-----------|-----------|
| SAP人事システム | `sap_hr` |
| Salesforce | `salesforce` |
| AWS IAM | `aws_iam` |
| Active Directory | `active_directory` |
| Google Workspace | `google_workspace` |

### バリデーション

```python
import re

def validate_system_id(system_id):
    """
    システムIDのバリデーション
    """
    if not system_id:
        raise ValueError("system_id が空です")
    
    if len(system_id) > 50:
        raise ValueError("system_id は50文字以内にしてください")
    
    if not re.match(r'^[a-z0-9_]+$', system_id):
        raise ValueError(
            "system_id は小文字英数字とアンダースコアのみ使用できます"
        )
    
    return True
```

## Pythonコード規約

### SQL組み立て（大文字に統一）

```python
# 推奨: カラム名・テーブル名はすべて大文字
sql = """
    SELECT 
        USER_CD,
        USER_NAME,
        DEPARTMENT_CD
    FROM NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_{system_id}
    WHERE IMPORT_BATCH_ID = :BATCH_ID
"""

# 結果セットも大文字で参照
cursor.execute(sql.format(system_id='SAP_HR'.upper()), {'BATCH_ID': batch_id})
for row in cursor:
    user_cd = row['USER_CD']
    user_name = row['USER_NAME']
```

### 動的SQL生成時

```python
def generate_select_columns(output_columns):
    """
    出力項目定義からSELECT句を生成
    """
    columns = []
    for col in output_columns['columns']:
        # column_name は大文字で格納されている前提
        columns.append(f"S.{col['column_name']}")
    
    return ', '.join(columns)

# 例
# output_columns = {
#     "columns": [
#         {"column_name": "USER_CD", ...},
#         {"column_name": "USER_NAME", ...}
#     ]
# }
# 結果: "S.USER_CD, S.USER_NAME"
```

## まとめ

| 項目 | 規則 | 例 |
|-----|------|-----|
| **Oracleカラム名** | 大文字 | `USER_CD`, `USER_NAME` |
| **Oracleテーブル名** | 大文字・`IDINV_` 接頭辞 | `IDINV_W_SYSTEM_USERS_SAP_HR` |
| **JSON target_column** | 大文字 | `"USER_CD"` |
| **SQL内カラム参照** | 大文字 | `SELECT USER_CD` |
| **SQL内テーブル参照** | 大文字でも小文字でも可 | `FROM IDINV_W_SYSTEM_USERS_SAP_HR` |
| **Python結果セット** | 大文字 | `row['USER_CD']` |
| **system_id** | 小文字スネークケース | `sap_hr` |
