# 退職者ID削除依頼書：無効化済み判定SQL

## 概要

退職者ID削除依頼書を2行形式で出力する際に、各システムのユーザーが既に無効化されているかをSQL式で判定します。

無効化済みの場合は「－」を返し、作業不要であることを示します。

## 仕様

### TAISHOKU_DISABLED_EXPRESSION（無効化済み判定SQL）

- **SQL条件式を記述**（CASE文は不要、条件部分のみ）
- システムが自動的に `CASE WHEN [条件式] THEN '－' ELSE NULL END` に展開
- **テーブルエイリアス**: 退職者リスト表示SQLと同じ `S.` を使用可能

#### 入力形式

```sql
-- 入力（条件式のみ）
S.STATUS IS NULL OR S.STATUS != 'active'

-- 自動生成されるSQL
CASE WHEN S.STATUS IS NULL OR S.STATUS != 'active' THEN '－' ELSE NULL END
```

### データの流れ

1. 退職者データ取得時に、`TAISHOKU_DISPLAY_SQL`と展開後の`TAISHOKU_DISABLED_EXPRESSION`を**同じSELECT句で取得**
2. `TAISHOKU_DISPLAY_SQL`の結果を1行目に表示
3. 展開後の`TAISHOKU_DISABLED_EXPRESSION`の結果が`'－'`なら2行目に「－」、`NULL`なら空欄を表示

---

## 設定例

### 例1: シンプルな判定

#### 退職者リスト表示SQL
```sql
S.STATUS
```

#### 無効化済み判定SQL（入力）
```sql
S.STATUS IS NULL OR S.STATUS != 'active'
```

#### 自動生成されるSQL
```sql
CASE WHEN S.STATUS IS NULL OR S.STATUS != 'active' THEN '－' ELSE NULL END
```

**説明**: 
- `STATUS`が`NULL`または`'active'`以外の場合、無効化済みと判定

---

### 例2: 複数条件の判定

#### 退職者リスト表示SQL
```sql
S.ACCOUNT_STATUS
```

#### 無効化済み判定SQL（入力）
```sql
S.ACCOUNT_STATUS IN ('Disabled', 'Suspended', 'Deleted')
```

#### 自動生成されるSQL
```sql
CASE WHEN S.ACCOUNT_STATUS IN ('Disabled', 'Suspended', 'Deleted') THEN '－' ELSE NULL END
```

**説明**: 
- `ACCOUNT_STATUS`が`'Disabled'`, `'Suspended'`, `'Deleted'`のいずれかの場合、無効化済みと判定

---

### 例3: CASE文を使った変換と判定

#### 退職者リスト表示SQL
```sql
CASE WHEN S.ENABLED = 'True' THEN '有効' ELSE '無効' END
```

#### 無効化済み判定SQL（入力）
```sql
S.ENABLED != 'True'
```

#### 自動生成されるSQL
```sql
CASE WHEN S.ENABLED != 'True' THEN '－' ELSE NULL END
```

**説明**: 
- 表示SQLでは「有効」「無効」の日本語表示
- 判定SQLでは元の`ENABLED`の値で判定

---

### 例4: NULL判定のみ

#### 退職者リスト表示SQL
```sql
S.USER_CD
```

#### 無効化済み判定SQL（入力）
```sql
S.USER_CD IS NULL
```

#### 自動生成されるSQL
```sql
CASE WHEN S.USER_CD IS NULL THEN '－' ELSE NULL END
```

**説明**: 
- データが存在しない（NULL）場合は無効化済みと判定

---

### 例5: 複雑な条件（AND/OR）

#### 退職者リスト表示SQL
```sql
S.STATUS
```

#### 無効化済み判定SQL（入力）
```sql
S.STATUS IS NULL OR (S.STATUS = 'inactive' AND S.LAST_LOGIN IS NULL)
```

#### 自動生成されるSQL
```sql
CASE WHEN S.STATUS IS NULL OR (S.STATUS = 'inactive' AND S.LAST_LOGIN IS NULL) THEN '－' ELSE NULL END
```

**説明**: 
- `STATUS`がNULL、または`STATUS`が`'inactive'`かつ`LAST_LOGIN`がNULLの場合、無効化済みと判定

---

## 重要なポイント

### ✅ 正しい書き方（条件式のみ）

```sql
-- 基本形
S.STATUS = 'Disabled'

-- 複数値チェック
S.STATUS IN ('Disabled', 'Suspended')

-- NULL判定
S.STATUS IS NULL

-- 複合条件
S.STATUS IS NULL OR S.STATUS != 'active'

-- 括弧を使った複雑な条件
S.STATUS IS NULL OR (S.STATUS = 'inactive' AND S.LAST_LOGIN IS NULL)
```

### ❌ 間違った書き方

```sql
-- ❌ CASE文を含めている（不要）
CASE WHEN S.STATUS = 'Disabled' THEN '－' ELSE NULL END

-- ❌ 文字列の比較が正しくない
S.STATUS = Disabled  -- Disabledはクォートで囲む必要

-- ❌ 真偽値を返そうとしている
S.STATUS = 'Disabled' THEN TRUE
```

---

## データベース設計

### IDINV_SYSTEM_DEFINITIONS テーブル

新規カラム（既存）:

```sql
TAISHOKU_DISABLED_EXPRESSION VARCHAR2(500)
```

このカラムには、無効化済み判定を行うためのSQL式（CASE文）を格納します。

---

## トラブルシューティング

### 判定が期待通りに動作しない

**原因**: SQL式の構文エラーまたはカラム名が存在しない

**解決策**:
1. システム定義のTAISHOKU_DISABLED_EXPRESSIONを確認
2. SQLを単独で実行してテストする

```sql
-- テスト用SQL
SELECT 
    S.USER_CD,
    S.STATUS,
    CASE WHEN S.STATUS IS NULL OR S.STATUS != 'active' THEN '－' ELSE NULL END AS DISABLED_VALUE
FROM NAM_USER_ADMIN.ZOOM_USERS S
WHERE ROWNUM <= 10;
```

### 全員が「作業必要」になる

**原因**: TAISHOKU_DISABLED_EXPRESSIONが未設定、またはNULLを返している

**解決策**:
- TAISHOKU_DISABLED_EXPRESSIONを確認
- 条件式が正しく`'－'`を返すか確認

---

## Python式からの移行

### 旧仕様（Python式）

```python
STATUS is None or STATUS != 'active'
```

### 新仕様（SQL条件式）

```sql
S.STATUS IS NULL OR S.STATUS != 'active'
```

**システムが自動的に以下に展開**:
```sql
CASE WHEN S.STATUS IS NULL OR S.STATUS != 'active' THEN '－' ELSE NULL END
```

### 移行方法

| Python式 | SQL条件式（入力） | 自動生成されるSQL |
|----------|------------------|------------------|
| `STATUS == 'Disabled'` | `S.STATUS = 'Disabled'` | `CASE WHEN S.STATUS = 'Disabled' THEN '－' ELSE NULL END` |
| `STATUS in ['A', 'B']` | `S.STATUS IN ('A', 'B')` | `CASE WHEN S.STATUS IN ('A', 'B') THEN '－' ELSE NULL END` |
| `STATUS is None` | `S.STATUS IS NULL` | `CASE WHEN S.STATUS IS NULL THEN '－' ELSE NULL END` |
| `STATUS != 'active'` | `S.STATUS != 'active'` | `CASE WHEN S.STATUS != 'active' THEN '－' ELSE NULL END` |

---

## まとめ

**TAISHOKU_DISABLED_EXPRESSION = SQL条件式（条件部分のみ）**

```sql
[無効化済みの条件]
```

**例**:
```sql
S.STATUS IS NULL OR S.STATUS != 'active'
```

**システムが自動的に以下の形式に展開**:
```sql
CASE WHEN [条件式] THEN '－' ELSE NULL END
```

### メリット
- **シンプル**: 条件部分のみ記述すればよい
- **安全**: CASE文の構文を意識しなくてよい
- **わかりやすい**: 「どういう時に無効化済みか」だけを記述
- **統一性**: すべて同じパターンで自動展開
