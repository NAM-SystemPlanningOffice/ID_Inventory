# 組織転出者アクセス権限確認リスト SQL設計

## 概要

指定日に組織を転出したユーザーの権限確認リストを出力します。
組織コード変更のみの異動は除外し、複数の転出元・転出先組織がある場合はLISTAGGで連結します。

## 要件

1. **異動日を指定して実行**
2. **組織コード変更のみは除外**: `IDINV_ORGANIZATION_CHANGES` でマッチしたものは対象外
3. **複数組織対応**: 
   - 転出元（IDO_TYPE='END'）が複数ある場合は改行区切りで連結
   - 転出先（IDO_TYPE='AFTER'）が複数ある場合は改行区切りで連結
4. **本務・兼務**: それぞれ「組織名＋役職名」形式で表示

## データ構造

### e_imdb_ido（異動情報）

```
異動日: 2026-06-30
ユーザーCD: U00123

レコード1: IDO_TYPE='END', DEPARTMENT_CD='1000', DEPARTMENT_NAME='営業部', POST_NAME='課長', DEPARTMENT_MAIN=1
レコード2: IDO_TYPE='END', DEPARTMENT_CD='2000', DEPARTMENT_NAME='開発部', POST_NAME='担当', DEPARTMENT_MAIN=0
レコード3: IDO_TYPE='AFTER', DEPARTMENT_CD='3000', DEPARTMENT_NAME='総務部', POST_NAME='部長', DEPARTMENT_MAIN=1
```

### IDINV_ORGANIZATION_CHANGES（組織変更マスタ）

```
change_date: 2026-06-30
before_org_cd: '1000'
after_org_cd: '1001'
→ 組織コード変更のみ（名称は同じ）なので転出リスト対象外
```

## SQL設計

### 基本クエリ構造

```sql
WITH 
-- 1. 組織コード変更のみを除外したユーザー抽出
filtered_ido AS (
    SELECT DISTINCT
        i.user_cd,
        i.user_name,
        i.ido_date
    FROM nam_user_admin.e_imdb_ido i
    WHERE i.ido_date = :target_date
      AND i.ido_type = 'END'
      AND NOT EXISTS (
          -- 組織コード変更マスタに一致する場合は除外
          SELECT 1
          FROM NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES oc
          WHERE oc.change_date = i.ido_date
            AND oc.before_org_cd = i.department_cd
      )
),
-- 2. 転出元組織を集約（複数組織を改行区切り）
ido_end AS (
    SELECT
        i.user_cd,
        LISTAGG(
            i.department_name || 
            CASE WHEN i.department_main = 1 THEN '(本務)' ELSE '(兼務)' END ||
            ' ' || i.post_name,
            CHR(10)  -- 改行文字
        ) WITHIN GROUP (ORDER BY i.department_main DESC, i.department_cd) AS end_departments
    FROM nam_user_admin.e_imdb_ido i
    INNER JOIN filtered_ido f ON i.user_cd = f.user_cd AND i.ido_date = f.ido_date
    WHERE i.ido_type = 'END'
    GROUP BY i.user_cd
),
-- 3. 転出先組織を集約（複数組織を改行区切り）
ido_after AS (
    SELECT
        i.user_cd,
        LISTAGG(
            i.department_name || 
            CASE WHEN i.department_main = 1 THEN '(本務)' ELSE '(兼務)' END ||
            ' ' || i.post_name,
            CHR(10)  -- 改行文字
        ) WITHIN GROUP (ORDER BY i.department_main DESC, i.department_cd) AS after_departments
    FROM nam_user_admin.e_imdb_ido i
    INNER JOIN filtered_ido f ON i.user_cd = f.user_cd AND i.ido_date = f.ido_date
    WHERE i.ido_type = 'AFTER'
    GROUP BY i.user_cd
)
-- 4. 各システムのユーザー情報とJOIN
SELECT
    f.user_cd,
    f.user_name,
    e.end_departments AS before_org,
    a.after_departments AS after_org,
    s.user_cd AS system_user_cd,
    s.department_cd AS system_dept_cd,
    s.department_name AS system_dept_name
    -- システム固有の項目...
FROM filtered_ido f
LEFT JOIN ido_end e ON f.user_cd = e.user_cd
LEFT JOIN ido_after a ON f.user_cd = a.user_cd
LEFT JOIN IDINV_W_SYSTEM_USERS_{system_id} s
    ON f.user_cd = s.user_cd
    AND s.import_batch_id = (
        SELECT MAX(import_batch_id) 
        FROM IDINV_W_SYSTEM_USERS_{system_id}
    )
ORDER BY f.user_cd
```

## 出力例

### 単一組織の場合

```
┌────────┬──────┬────────────┬────────────┬─────────┐
│ユーザーID│氏名   │転出元      │転出先      │システムA │
├────────┼──────┼────────────┼────────────┼─────────┤
│U00123  │山田太郎│営業部(本務)│総務部(本務)│enabled  │
│        │      │課長        │部長        │         │
└────────┴──────┴────────────┴────────────┴─────────┘
```

### 複数組織の場合

```
┌────────┬──────┬────────────┬────────────┬─────────┐
│ユーザーID│氏名   │転出元      │転出先      │システムA │
├────────┼──────┼────────────┼────────────┼─────────┤
│U00123  │山田太郎│営業部(本務)│総務部(本務)│enabled  │
│        │      │課長        │部長        │         │
│        │      │開発部(兼務)│企画部(兼務)│         │
│        │      │担当        │課長        │         │
└────────┴──────┴────────────┴────────────┴─────────┘
```

## Python実装

### SQL生成関数

```python
def generate_tenshutu_list_sql(target_date, system_id):
    """
    組織転出者リスト用SQLを生成
    
    Args:
        target_date: 対象日
        system_id: システムID
    
    Returns:
        str: SQL文字列
    """
    sql = f"""
WITH 
filtered_ido AS (
    SELECT DISTINCT
        i.user_cd,
        i.user_name,
        i.ido_date
    FROM nam_user_admin.e_imdb_ido i
    WHERE i.ido_date = :target_date
      AND i.ido_type = 'END'
      AND NOT EXISTS (
          SELECT 1
          FROM NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES oc
          WHERE oc.change_date = i.ido_date
            AND oc.before_org_cd = i.department_cd
      )
),
ido_end AS (
    SELECT
        i.user_cd,
        LISTAGG(
            i.department_name || 
            CASE WHEN i.department_main = 1 THEN '(本務)' ELSE '(兼務)' END ||
            ' ' || i.post_name,
            CHR(10)
        ) WITHIN GROUP (ORDER BY i.department_main DESC, i.department_cd) AS end_departments
    FROM nam_user_admin.e_imdb_ido i
    INNER JOIN filtered_ido f ON i.user_cd = f.user_cd AND i.ido_date = f.ido_date
    WHERE i.ido_type = 'END'
    GROUP BY i.user_cd
),
ido_after AS (
    SELECT
        i.user_cd,
        LISTAGG(
            i.department_name || 
            CASE WHEN i.department_main = 1 THEN '(本務)' ELSE '(兼務)' END ||
            ' ' || i.post_name,
            CHR(10)
        ) WITHIN GROUP (ORDER BY i.department_main DESC, i.department_cd) AS after_departments
    FROM nam_user_admin.e_imdb_ido i
    INNER JOIN filtered_ido f ON i.user_cd = f.user_cd AND i.ido_date = f.ido_date
    WHERE i.ido_type = 'AFTER'
    GROUP BY i.user_cd
)
SELECT
    f.user_cd,
    f.user_name,
    e.end_departments AS before_org,
    a.after_departments AS after_org,
    NVL(s.user_cd, '－') AS system_user_cd,
    NVL(s.department_cd, '－') AS system_dept_cd,
    NVL(s.department_name, '－') AS system_dept_name
FROM filtered_ido f
LEFT JOIN ido_end e ON f.user_cd = e.user_cd
LEFT JOIN ido_after a ON f.user_cd = a.user_cd
LEFT JOIN IDINV_W_SYSTEM_USERS_{system_id} s
    ON f.user_cd = s.user_cd
    AND s.import_batch_id = (
        SELECT MAX(import_batch_id) 
        FROM IDINV_W_SYSTEM_USERS_{system_id}
    )
ORDER BY f.user_cd
"""
    return sql


def get_tenshutu_list_for_system(target_date, system_id):
    """
    特定システムの組織転出者リストを取得
    
    Args:
        target_date: 対象日
        system_id: システムID
    
    Returns:
        list: 転出者リスト
    """
    sql = generate_tenshutu_list_sql(target_date, system_id)
    result = db.execute(sql, {'target_date': target_date})
    return result.fetchall()


def get_all_tenshutu_lists(target_date):
    """
    全システムの組織転出者リストを取得
    
    Args:
        target_date: 対象日
    
    Returns:
        dict: システムIDをキーとした転出者リストの辞書
    """
    # 出力対象システムを取得
    systems = get_active_systems_for_tenshutu(order_by='tenshutu_output_order')
    
    result = {}
    for system in systems:
        if not system.tenshutu_output_required:
            continue
        
        data = get_tenshutu_list_for_system(target_date, system.system_id)
        
        # データが存在するシステムのみ結果に含める
        if data:
            result[system.system_id] = {
                'system_name': system.system_name,
                'data': data
            }
    
    return result
```

## Google Sheets出力

### シート構成

各システムごとに別シートで出力します。

```python
def export_tenshutu_list_to_sheets(target_date, systems_data):
    """
    組織転出者リストをGoogle Sheetsに出力
    
    Args:
        target_date: 対象日
        systems_data: システムごとのデータ辞書
    
    Returns:
        str: スプレッドシートURL
    """
    # スプレッドシート作成
    title = f"組織転出者アクセス権限確認リスト_{target_date.strftime('%Y%m%d')}"
    spreadsheet = gsheet_client.create_spreadsheet(title)
    
    # 最初のシートは削除（後で追加するため）
    first_sheet = True
    
    for system_id, system_info in systems_data.items():
        system_name = system_info['system_name']
        data = system_info['data']
        
        # シート作成
        if first_sheet:
            sheet = spreadsheet.sheet1
            sheet.update_title(system_name)
            first_sheet = False
        else:
            sheet = spreadsheet.add_worksheet(
                title=system_name,
                rows=len(data) + 10,
                cols=10
            )
        
        # タイトル行
        sheet.update('A1', f"{system_name} - 組織転出者リスト")
        sheet.update('A2', f"対象日: {target_date.strftime('%Y年%m月%d日')}")
        
        # ヘッダー行（4行目）
        headers = [
            'ユーザーID', '氏名', '転出元組織', '転出先組織',
            'システムユーザーID', 'システム所属コード', 'システム所属名'
        ]
        sheet.append_row(headers)
        
        # データ行
        for row in data:
            sheet.append_row(list(row))
        
        # フォーマット設定
        sheet.format('A4:G4', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        
        # 列幅調整
        sheet.columns_auto_resize(0, len(headers))
        
        # 改行を有効化（転出元・転出先列）
        sheet.format('C5:D1000', {
            'wrapStrategy': 'WRAP'
        })
    
    # 出力履歴記録
    total_users = sum(len(s['data']) for s in systems_data.values())
    record_output_history(
        output_type='TENSHUTU',
        target_date=target_date,
        spreadsheet_url=spreadsheet.url,
        total_systems=len(systems_data),
        total_users=total_users
    )
    
    return spreadsheet.url
```

## IDINV_ORGANIZATION_CHANGES の使い方

### 組織コード変更のみを登録

組織の名称は変わらず、コードだけが変更された場合に登録します。

```sql
-- 例: 営業部のコードが '1000' → '1001' に変更
INSERT INTO NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES (
    change_date,
    before_org_cd,
    after_org_cd,
    before_org_name,
    after_org_name,
    remarks,
    created_by
) VALUES (
    DATE '2026-06-30',
    '1000',
    '1001',
    '営業部',
    '営業部',  -- 名称は同じ
    '組織コード体系変更',
    'SYSTEM'
);
```

### 除外ロジック

```sql
-- この条件に一致する異動は「組織コード変更のみ」と判定され、転出リストから除外
WHERE NOT EXISTS (
    SELECT 1
    FROM NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES oc
    WHERE oc.change_date = i.ido_date
      AND oc.before_org_cd = i.department_cd
)
```

## 注意事項

1. **LISTAGG制限**: Oracle 11gまでは最大4000バイト。12c以降は ON OVERFLOW TRUNCATE オプションで対応可能
2. **改行文字**: Google Sheetsで改行を表示するには、セルの折り返し設定（wrapStrategy: 'WRAP'）が必要
3. **本務優先**: ORDER BY で `department_main DESC` を指定し、本務を先に表示
4. **組織コード変更マスタ**: 変更前のコードのみをチェック（複数転出元がある場合、1つでも該当すれば全体が除外される訳ではない）

## テストケース

### ケース1-1: 単一組織の転出（対象）
```
U00123: (本務)営業部 → (本務)総務部
→ 出力対象
```

### ケース1-2: 単一組織内の昇格（対象外）
```
U00123: (本務)営業部 課長 → (本務)営業部 部長
役職コード(post_cd)が小さくなっていたら昇格
→ 出力対象外
```
### ケース1-3: 単一組織内の降格（対象）
```
U00123: (本務)営業部 課長 → (本務)営業部 課長補佐
役職コード(post_cd)が大きくなっていたら降格
→ 出力対象
```

### ケース２-1: 複数組織の転出（対象）
```
U00789:
  転出元: (本務)営業部 課長、(兼務)開発部 担当
  転出先: (本務)総務部 部長、(兼務)企画部 課長
→ 出力対象、LISTAGGで改行区切り
```
### ケース２-2: 複数組織の転出（対象）
```
U00789:
  転出元: (本務)営業部 課長、(兼務)開発部 担当
  転出先: (本務)営業部 課長、(兼務)企画部 課長
→ 転出元、転出先で同じ部署、同じまたは昇格した役職のものは出力対象外、
U00789:
  転出元: (兼務)開発部 担当
  転出先: (兼務)企画部 課長
のみ出力（複数の場合は改行区切り）
```

### ケース３: 組織コード変更のみ（除外）
```
U00456: 営業部(コード:1000) → 営業部(コード:1001)
IDINV_ORGANIZATION_CHANGESに登録あり
→ 出力対象外
```

### ケース4: 一部が組織コード変更（対象）
```
U00999:
  転出元A: 営業部(コード:1000) → 営業部(コード:1001)　IDINV_ORGANIZATION_CHANGESに登録あり
  転出元B: 開発部(コード:2000) → 登録なし
→ 開発部からの転出は対象（営業部は除外されるが、ユーザー全体は対象）
```
