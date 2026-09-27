# 無効化済み判定式の設定方法

## 概要

退職者ID削除依頼書で、各システムのユーザーが既に無効化されているかを判定するPython式を設定します。

## カラム名の対応関係

### 1. **退職者リスト表示SQL** に記述するカラム名

- **`S.カラム名`** の形式で記述（`S`はシステムテーブルのエイリアス）
- 例: `S.ACCOUNT_STATUS`、`CASE WHEN S.ACCOUNT_STATUS = 'True' THEN '有効' ELSE '無効' END`

### 2. **無効化済み判定式（Python式）** に記述するカラム名

- **マッピング定義の`target_column`（Oracleテーブルのカラム名）** をそのまま使用
- プレフィックスなし、大文字で記述
- 例: `ACCOUNT_STATUS`、`USER_CD`、`EMAIL`

## 設定例

### 例1: Active Directory

#### マッピング定義
```json
{
  "columns": [
    {"source_column": "samAccountName", "target_column": "USER_CD"},
    {"source_column": "displayName", "target_column": "USER_NAME"},
    {"source_column": "enabled", "target_column": "ACCOUNT_STATUS"}
  ]
}
```

#### 退職者リスト表示SQL
```sql
CASE WHEN S.ACCOUNT_STATUS = 'True' THEN '有効' ELSE '無効' END
```

#### 無効化済み判定式
```python
ACCOUNT_STATUS == 'False' or ACCOUNT_STATUS is None
```

**説明**: 
- 表示SQLでは`S.ACCOUNT_STATUS`を使用
- 判定式では`ACCOUNT_STATUS`（プレフィックスなし）を使用
- `ACCOUNT_STATUS`が`False`またはNullの場合、無効化済みと判定

---

### 例2: Windows AD

#### マッピング定義
```json
{
  "columns": [
    {"source_column": "UserName", "target_column": "USER_CD"},
    {"source_column": "DisplayName", "target_column": "USER_NAME"},
    {"source_column": "Status", "target_column": "ACCOUNT_STATUS"}
  ]
}
```

#### 退職者リスト表示SQL
```sql
S.ACCOUNT_STATUS
```

#### 無効化済み判定式
```python
ACCOUNT_STATUS in ['Disabled', 'Suspended']
```

**説明**: 
- `ACCOUNT_STATUS`が`Disabled`または`Suspended`の場合、無効化済みと判定

---

### 例3: Zoom

#### マッピング定義
```json
{
  "columns": [
    {"source_column": "Email", "target_column": "USER_CD"},
    {"source_column": "FirstName", "target_column": "USER_NAME"},
    {"source_column": "Status", "target_column": "STATUS"}
  ]
}
```

#### 退職者リスト表示SQL
```sql
S.STATUS
```

#### 無効化済み判定式
```python
STATUS == 'inactive'
```

**説明**: 
- マッピング定義で`target_column`が`STATUS`なので、判定式でも`STATUS`を使用

---

### 例4: 複数カラムを使った判定

#### マッピング定義
```json
{
  "columns": [
    {"source_column": "UserID", "target_column": "USER_CD"},
    {"source_column": "UserName", "target_column": "USER_NAME"},
    {"source_column": "Status", "target_column": "ACCOUNT_STATUS"},
    {"source_column": "LastLogin", "target_column": "LAST_LOGIN_DATE"}
  ]
}
```

#### 退職者リスト表示SQL
```sql
S.ACCOUNT_STATUS
```

#### 無効化済み判定式
```python
ACCOUNT_STATUS != 'Active' and (LAST_LOGIN_DATE is None or LAST_LOGIN_DATE == '')
```

**説明**: 
- 複数のカラムを組み合わせて判定可能
- `ACCOUNT_STATUS`が`Active`でなく、かつ`LAST_LOGIN_DATE`が空の場合、無効化済みと判定

---

## 重要なポイント

### ✅ 正しい書き方

```python
# カラム名は大文字、プレフィックスなし
ACCOUNT_STATUS == 'Disabled'

# 複数の値をチェック
ACCOUNT_STATUS in ['Disabled', 'Suspended', 'inactive']

# Null判定
ACCOUNT_STATUS is None

# 複合条件
ACCOUNT_STATUS != 'Active' and USER_CD is not None
```

### ❌ 間違った書き方

```python
# ❌ プレフィックス付き（S.やs0.は不要）
S.ACCOUNT_STATUS == 'Disabled'
s0.ACCOUNT_STATUS == 'Disabled'

# ❌ 小文字（Oracleのカラム名は大文字）
account_status == 'Disabled'

# ❌ SYS_プレフィックス（内部処理用のプレフィックスは不要）
SYS_WINDOWS_ACCOUNT_STATUS == 'Disabled'
```

## データの流れ

1. **マッピング定義** で `target_column: "ACCOUNT_STATUS"` を定義
2. **Oracleテーブル** に `ACCOUNT_STATUS` カラムとして格納
3. **退職者データ取得SQL** で `s0.ACCOUNT_STATUS AS SYS_WINDOWS_ACCOUNT_STATUS` として取得
4. **Python評価時** に `SYS_WINDOWS_` プレフィックスを除去して `ACCOUNT_STATUS` として渡される
5. **判定式** で `ACCOUNT_STATUS` として参照

## トラブルシューティング

### エラー: "NameError: name 'XXXX' is not defined"

**原因**: 判定式で参照しているカラムがマッピング定義に存在しない

**解決策**:
1. システム定義のマッピング定義を確認
2. `target_column` に該当するカラムが定義されているか確認
3. 判定式のカラム名が `target_column` と完全一致しているか確認（大文字小文字含む）

### 判定結果が意図と異なる

**原因**: カラムの値が想定と異なる

**解決策**:
1. システムテーブル（`IDINV_W_SYSTEM_USERS_XXXX`）を直接確認
2. 実際のデータがどのような値になっているか確認
3. 判定式をデータに合わせて修正

```sql
-- システムテーブルのデータ確認例
SELECT USER_CD, USER_NAME, ACCOUNT_STATUS
FROM NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_WINDOWS
WHERE ROWNUM <= 10;
```

## まとめ

| 項目 | 記述方法 | 例 |
|------|----------|-----|
| **マッピング定義 target_column** | 大文字のカラム名 | `ACCOUNT_STATUS` |
| **退職者リスト表示SQL** | `S.カラム名` | `S.ACCOUNT_STATUS` |
| **無効化済み判定式** | プレフィックスなし大文字 | `ACCOUNT_STATUS` |

**判定式で使用するカラム名 = マッピング定義の target_column と完全一致**
