# ユーザー棚卸リスト設計詳細

## 概要

月次で各システムのユーザーIDを確認し、在籍ユーザー属性（本務所属・兼務所属・役職）とシステム固有項目を出力します。

## 出力イメージ

```
【システムA - ユーザー棚卸リスト】

┌────────┬──────┬────────────┬────────────┬─────────┬─────────────┐
│ユーザーID│氏名   │本務所属     │兼務所属     │役職      │システム      │
│        │      │            │            │         │ユーザーID    │
├────────┼──────┼────────────┼────────────┼─────────┼─────────────┤
│U00123  │山田太郎│営業部       │開発部       │課長      │yamada_sys   │
├────────┼──────┼────────────┼────────────┼─────────┼─────────────┤
│U00456  │佐藤花子│総務部       │－          │部長      │sato_sys     │
├────────┼──────┼────────────┼────────────┼─────────┼─────────────┤
│U00789  │鈴木一郎│            │            │         │suzuki_sys   │
├────────┼──────┼────────────┼────────────┼─────────┼─────────────┤
│U00999  │田中次郎│人事部       │            │産育休    │             │
└────────┴──────┴────────────┴────────────┴─────────┴─────────────┘
```

## 出力項目の構成

### 1. 在籍ユーザー属性（自動付与）

| 項目 | 内容 | データソース |
|-----|------|------------|
| 本務所属 | 本務の所属名 | `honmu` 列の値 |
| 兼務所属 | 兼務の所属名（複数ある場合は改行区切り） | `kenmu` 列の値 |
| 役職 | 役職名 | `post_name` 列の値 |

**在籍していない場合**: 空白（何も表示しない）

**データソース**: 
```sql
-- 在籍ユーザー（通常 + 産育休）
SELECT user_cd, user_name, shozoku, post_name, honmu, kenmu 
FROM nam_user_admin.e_imdb_honmu_kenmu
UNION
SELECT user_cd, user_name, shozoku, '産育休' AS post_name, 
       NVL(shozoku_name, bumon_name) AS honmu, NULL AS kenmu 
FROM nam_user_admin.e_imdb_sankyu
WHERE department_main = '1'
```

### 2. システム固有項目

`output_columns_json` で定義された項目（システムごとに設定可能）

## SQL設計

### 基本クエリ

```sql
WITH 
-- 在籍ユーザー情報（通常 + 産育休）
zaiseki AS (
    SELECT user_cd, user_name, shozoku, post_name, honmu, kenmu 
    FROM nam_user_admin.e_imdb_honmu_kenmu
    UNION
    SELECT user_cd, user_name, shozoku, '産育休' AS post_name, 
           NVL(shozoku_name, bumon_name) AS honmu, NULL AS kenmu 
    FROM nam_user_admin.e_imdb_sankyu
    WHERE department_main = '1'
)
SELECT
    s.user_cd,
    s.user_name,
    z.honmu AS honmu_shozoku,
    z.kenmu AS kenmu_shozoku,
    z.post_name AS yakushoku,
    -- システム固有項目（output_columns_jsonで定義）
    s.system_user_id
    -- ... その他のシステム固有項目
FROM IDINV_W_SYSTEM_USERS_{system_id} s
LEFT JOIN zaiseki z ON s.user_cd = z.user_cd
WHERE s.import_batch_id = (
    SELECT MAX(import_batch_id)
    FROM IDINV_W_SYSTEM_USERS_{system_id}
)
-- 出力モードに応じたフィルタ
-- ALL: フィルタなし
-- MISMATCH_ONLY: AND z.user_cd IS NULL
-- CUSTOM: AND (tanaoroshi_filter_sql)
ORDER BY s.user_cd
```

## 出力モード

### 1. ALL（全ユーザー出力）

```sql
-- フィルタ条件なし
WHERE s.import_batch_id = (SELECT MAX(import_batch_id) FROM IDINV_W_SYSTEM_USERS_{system_id})
```

**用途**: 小規模システム、全数確認が必要なシステム

### 2. MISMATCH_ONLY（在籍マッチング不可のみ）

```sql
-- 在籍マスタにないユーザーのみ
WHERE s.import_batch_id = (SELECT MAX(import_batch_id) FROM IDINV_W_SYSTEM_USERS_{system_id})
  AND z.user_cd IS NULL
```

**用途**: 標準（最も多い）

### 3. CUSTOM（カスタムフィルタ）

```sql
-- tanaoroshi_filter_sql を適用
WHERE s.import_batch_id = (SELECT MAX(import_batch_id) FROM IDINV_W_SYSTEM_USERS_{system_id})
  AND (tanaoroshi_filter_sql)
```

**設定例**:
- `s.account_status != 'Disabled'` （Disableユーザー除外）
- `s.permission_level NOT IN ('User', 'Guest')` （一般権限除外）
- `z.user_cd IS NULL OR s.account_status = 'Disabled'` （在籍なし または Disable）

## Python実装

### SQL生成関数

```python
def generate_tanaoroshi_sql(system_id, system_info):
    """
    棚卸リスト用SQLを生成
    
    Args:
        system_id: システムID
        system_info: システム定義情報
    
    Returns:
        str: SQL文字列
    """
    # output_columns_json から出力項目を取得
    output_columns = json.loads(system_info.output_columns_json)
    
    # システム固有項目のSELECT句を生成
    system_columns = []
    for col in output_columns['columns']:
        system_columns.append(f"s.{col['column_name'].lower()}")
    
    # 出力モードに応じたフィルタ条件
    if system_info.tanaoroshi_output_mode == 'ALL':
        filter_condition = "1=1"
    elif system_info.tanaoroshi_output_mode == 'MISMATCH_ONLY':
        filter_condition = "h.user_cd IS NULL"
    elif system_info.tanaoroshi_output_mode == 'CUSTOM':
        filter_condition = system_info.tanaoroshi_filter_sql or "1=1"
    else:
        filter_condition = "1=1"
    
    sql = f"""
WITH 
zaiseki AS (
    SELECT user_cd, user_name, shozoku, post_name, honmu, kenmu 
    FROM nam_user_admin.e_imdb_honmu_kenmu
    UNION
    SELECT user_cd, user_name, shozoku, '産育休' AS post_name, 
           NVL(shozoku_name, bumon_name) AS honmu, NULL AS kenmu 
    FROM nam_user_admin.e_imdb_sankyu
    WHERE department_main = '1'
)
SELECT
    s.user_cd,
    s.user_name,
    z.honmu AS honmu_shozoku,
    z.kenmu AS kenmu_shozoku,
    z.post_name AS yakushoku,
    {', '.join(system_columns)}
FROM IDINV_W_SYSTEM_USERS_{system_id} s
LEFT JOIN zaiseki z ON s.user_cd = z.user_cd
WHERE s.import_batch_id = (
    SELECT MAX(import_batch_id)
    FROM IDINV_W_SYSTEM_USERS_{system_id}
)
  AND ({filter_condition})
ORDER BY s.user_cd
"""
    
    return sql


def get_tanaoroshi_column_names(system_info):
    """
    棚卸リストのカラム名リストを取得
    
    Args:
        system_info: システム定義情報
    
    Returns:
        list: カラム名リスト
    """
    # 固定列（在籍ユーザー属性）
    column_names = [
        "ユーザーID",
        "氏名",
        "本務所属",
        "兼務所属",
        "役職"
    ]
    
    # システム固有項目
    output_columns = json.loads(system_info.output_columns_json)
    for col in output_columns['columns']:
        column_names.append(col['display_name'])
    
    return column_names
```

## Google Sheets出力

### シート構成

システムごとに別シートで出力（`output_order` 順）

```python
def export_tanaoroshi_to_sheets(systems_data):
    """
    棚卸リストをGoogle Sheetsに出力
    
    Args:
        systems_data: システムごとのデータ辞書
    
    Returns:
        str: スプレッドシートURL
    """
    # スプレッドシート作成
    title = f"ユーザー棚卸リスト_{datetime.now().strftime('%Y%m%d')}"
    spreadsheet = gsheet_client.create_spreadsheet(title)
    
    first_sheet = True
    
    for system_id, system_info in systems_data.items():
        system_name = system_info['system_name']
        data = system_info['data']
        columns = system_info['columns']
        
        # シート作成
        if first_sheet:
            sheet = spreadsheet.sheet1
            sheet.update_title(system_name)
            first_sheet = False
        else:
            sheet = spreadsheet.add_worksheet(
                title=system_name,
                rows=len(data) + 10,
                cols=len(columns)
            )
        
        # タイトル行
        sheet.update('A1', f"{system_name} - ユーザー棚卸リスト")
        sheet.update('A2', f"出力日: {datetime.now().strftime('%Y年%m月%d日')}")
        
        # ヘッダー行（4行目）
        sheet.append_row(columns)
        
        # データ行
        for row in data:
            sheet.append_row(list(row))
        
        # フォーマット設定
        sheet.format('A4:Z4', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        
        # 本務所属・兼務所属の列を折り返し設定
        sheet.format('C5:D1000', {
            'wrapStrategy': 'WRAP'
        })
        
        # 列幅調整
        sheet.columns_auto_resize(0, len(columns))
    
    return spreadsheet.url
```

## 取り込み状況確認画面

### 画面イメージ

```
【ユーザー棚卸リスト出力】

■ 各システムの取り込み状況
┌──────────────────┬─────────────────┬────────┬────────┐
│ システム名        │ 最終取り込み日時  │ 状態    │ 出力    │
├──────────────────┼─────────────────┼────────┼────────┤
│ SAP人事システム   │ 2026-06-24 10:30│ OK     │ ☑      │
│ 営業支援システム   │ 2026-06-20 15:00│ 古い⚠  │ ☑      │
│ 経費精算システム   │ 未取り込み        │ 未実施❌│ □      │
└──────────────────┴─────────────────┴────────┴────────┘

[選択システムの棚卸リスト出力実行] ボタン
```

### 取り込み状況判定

```python
def check_import_status(system_info):
    """
    取り込み状況を判定
    
    Returns:
        str: 'OK', 'OLD', 'NONE'
    """
    if not system_info.last_import_datetime:
        return 'NONE'  # 未取り込み
    
    # 7日以上前の場合は「古い」
    days_old = (datetime.now() - system_info.last_import_datetime).days
    if days_old > 7:
        return 'OLD'
    
    return 'OK'
```

## 注意事項

1. **兼務所属の表示**: 複数ある場合はLISTAGGで改行区切り
2. **在籍なしの表示**: `(在籍なし)` と表示（空白ではない）
3. **Google Sheetsの改行**: セルの折り返し設定（wrapStrategy: 'WRAP'）が必要
4. **出力モード**: システムごとに設定可能（デフォルトはMISMATCH_ONLY）
