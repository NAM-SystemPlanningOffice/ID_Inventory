# 退職者ID削除依頼書：無効化済み判定機能

## 概要

退職者ID削除依頼書を2行形式で出力する際に、各システムのユーザーが既に無効化されているかを自動判定する機能です。

無効化済みの場合は「ー」を表示し、作業不要であることを示します。

## データベース設計

### IDINV_SYSTEM_DEFINITIONS テーブル

新規カラム:

```sql
TAISHOKU_DISABLED_EXPRESSION VARCHAR2(500)
```

このカラムには、無効化済み判定を行うためのPython式を文字列で格納します。

## Python式の記法

### 基本的な構文

- **等価比較**: `COLUMN_NAME == 'value'`
- **不等価比較**: `COLUMN_NAME != 'value'`
- **Null判定**: `COLUMN_NAME is None`
- **Not Null判定**: `COLUMN_NAME is not None`
- **IN演算子**: `COLUMN_NAME in ['value1', 'value2', 'value3']`
- **NOT IN演算子**: `COLUMN_NAME not in ['value1', 'value2']`
- **AND条件**: `CONDITION1 and CONDITION2`
- **OR条件**: `CONDITION1 or CONDITION2`
- **NOT条件**: `not CONDITION`

### 式の例

#### 1. 単純な等価比較

```python
"ACCOUNT_STATUS == 'Disabled'"
```

→ ACCOUNT_STATUSが'Disabled'の場合、無効化済みと判定

#### 2. Null または特定値

```python
"ACCOUNT_STATUS is None or ACCOUNT_STATUS == 'Inactive'"
```

→ ACCOUNT_STATUSがNullまたは'Inactive'の場合、無効化済みと判定

#### 3. リストによる判定

```python
"ACCOUNT_STATUS in ['Disabled', 'Suspended', 'inactive']"
```

→ ACCOUNT_STATUSが'Disabled', 'Suspended', 'inactive'のいずれかの場合、無効化済みと判定

#### 4. 不等価判定

```python
"ACCOUNT_STATUS != 'Active'"
```

→ ACCOUNT_STATUSが'Active'以外の場合、無効化済みと判定

#### 5. 複合条件

```python
"ACCOUNT_STATUS != 'Active' and USER_CD is not None"
```

→ ACCOUNT_STATUSが'Active'以外で、かつUSER_CDがNullでない場合、無効化済みと判定

#### 6. 空文字列判定

```python
"USER_CD is None or USER_CD == ''"
```

→ USER_CDがNullまたは空文字列の場合、無効化済みと判定（データなし）

## 実装の仕組み

### 1. 式の評価

`app/utils/expression_evaluator.py`の`safe_eval_disabled_condition`関数で式を評価します。

```python
from app.utils.expression_evaluator import safe_eval_disabled_condition

# ユーザーデータ（システムテーブルから取得したレコード）
user_data = {
    "ACCOUNT_STATUS": "Disabled",
    "USER_CD": "test001"
}

# 無効化済み判定式
expression = "ACCOUNT_STATUS == 'Disabled'"

# 評価
is_disabled = safe_eval_disabled_condition(expression, user_data)
# → True
```

### 2. 表示値の取得

`get_display_value`関数で、判定結果に応じた表示値を取得します。

```python
from app.utils.expression_evaluator import get_display_value

display_value = get_display_value(
    user_data={"ACCOUNT_STATUS": "Disabled", "USER_CD": "test001"},
    disabled_expression="ACCOUNT_STATUS == 'Disabled'",
    display_column="USER_CD"
)
# → '－' (無効化済みの場合)
```

### 3. セキュリティ対策

- `eval()`を使用しますが、スコープを制限しています
- `__builtins__`を空にして、危険な組み込み関数を無効化
- `len`, `str`, `int`, `float`, `bool`のみ許可
- ユーザーデータのキーのみをローカル変数として利用

## 退職者ID削除依頼書の出力形式

### 2行形式

| USER_CD | 名　前 | Windows | Gmail | Zoom | ... |
|---------|--------|---------|-------|------|-----|
| **1行目** | USER_CD | 名前 | Disabled | Suspended | inactive | ... |
| **2行目** | （空欄） | （説明） | ー | ー | ー | ... |

- **1行目**: ユーザーCDと各システムのステータス値（TAISHOKU_DISPLAY_SQLで取得）
- **2行目**: 各システムの無効化作業が不要な場合は「ー」、必要な場合は空欄

## サンプルデータ

`migrations/011_update_sample_disabled_expression.sql`に各システムのサンプル式が定義されています。

```sql
-- Windows
UPDATE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
SET TAISHOKU_DISABLED_EXPRESSION = 'ACCOUNT_STATUS in [''Disabled'', ''Suspended'']'
WHERE SYSTEM_ID = 'windows';

-- Gmail
UPDATE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
SET TAISHOKU_DISABLED_EXPRESSION = 'ACCOUNT_STATUS == ''Suspended'''
WHERE SYSTEM_ID = 'gmail';

-- Zoom
UPDATE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
SET TAISHOKU_DISABLED_EXPRESSION = 'ACCOUNT_STATUS == ''inactive'''
WHERE SYSTEM_ID = 'zoom';
```

## テスト

`test_expression_evaluator.py`で動作確認ができます。

```bash
python test_expression_evaluator.py
```

## システム定義画面での設定

システム定義画面で「退職者ID削除依頼書 無効化済み判定式」フィールドに上記の式を入力してください。

- 式が未設定の場合は、デフォルトでFalse（作業必要）と判定されます
- 式の評価でエラーが発生した場合も、False（作業必要）と判定されます

## 注意事項

1. **カラム名の大文字小文字**: Oracleから取得したカラム名は大文字になります
2. **文字列リテラル**: シングルクォート`'`で囲みます
3. **Null判定**: `is None` を使用します（`== None`は非推奨）
4. **データ型**: 文字列比較が基本ですが、数値比較も可能です

## トラブルシューティング

### 式の評価エラー

ログに警告が出力されます:

```
条件評価エラー: expression=..., error=..., user_data=...
```

この場合、式の構文を確認してください。

### カラムが存在しない

式で参照しているカラムが、IMPORT_MAPPING_JSONで定義されていない場合、エラーになります。

マッピング定義を確認してください。
