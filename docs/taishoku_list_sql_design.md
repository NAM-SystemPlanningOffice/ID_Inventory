# 退職者ID削除依頼書 SQL設計詳細

## 概要

退職者ID削除依頼書は、指定日に退職したユーザーを横持ち表形式で出力します。
各システムの列に表示する内容を、SQLで柔軟に定義できる設計とします。

## 出力イメージ

```
退職者ID削除依頼書
対象日: 2026-06-30

┌────────┬──────┬──────┬─────────┬─────────┬─────────┬─────────┐
│ユーザーID│氏名   │所属   │システムA │システムB │システムC │システムD │
├────────┼──────┼──────┼─────────┼─────────┼─────────┼─────────┤
│U00123  │山田太郎│営業部 │enabled  │EMP12345 │－       │enabled  │
│        │      │      │         │         │         │(2026/12)│
├────────┼──────┼──────┼─────────┼─────────┼─────────┼─────────┤
│U00456  │佐藤花子│総務部 │suspended│－       │disabled │enabled  │
├────────┼──────┼──────┼─────────┼─────────┼─────────┼─────────┤
│U00789  │鈴木一郎│人事部 │disabled │EMP67890 │enabled  │－       │
└────────┴──────┴──────┴─────────┴─────────┴─────────┴─────────┘
```

## テーブル定義

### IDINV_SYSTEM_DEFINITIONS に追加

```sql
taishoku_display_sql CLOB  -- 退職者リスト表示SQL（SELECT句の1列分）
```

## 表示SQL設定例

### パターン1: 条件分岐で表示内容を変える

```sql
-- suspended=Trueの場合は'suspended'と表示
-- enabled+期限ありの場合は'enabled(YYYY/MM)'と表示
-- それ以外はaccount_statusをそのまま表示
CASE 
    WHEN s.suspended = 'True' THEN 'suspended'
    WHEN s.account_status = 'enabled' AND s.expiry_date IS NOT NULL 
        THEN s.account_status || '(' || TO_CHAR(s.expiry_date, 'YYYY/MM') || ')'
    ELSE s.account_status
END
```

**出力例**: `enabled(2026/12)`, `suspended`, `disabled`

### パターン2: システム固有IDを表示

```sql
-- 名寄せ用のuser_cdとは別の、システム固有のIDを表示
s.system_user_id
```

**出力例**: `EMP12345`, `USR_00789`

### パターン3: シンプルにカラム値

```sql
s.account_status
```

**出力例**: `enabled`, `disabled`, `suspended`

### パターン4: DECODE関数を使用

```sql
DECODE(s.is_active, 1, 'enabled', 0, 'disabled', 'unknown')
```

**出力例**: `enabled`, `disabled`, `unknown`

### パターン5: 複数カラムを結合

```sql
s.account_status || 
CASE 
    WHEN s.expiry_date IS NOT NULL 
        THEN '(期限:' || TO_CHAR(s.expiry_date, 'YYYY/MM/DD') || ')' 
    ELSE '' 
END
```

**出力例**: `enabled(期限:2026/12/31)`, `disabled`

### パターン6: 複雑な条件

```sql
CASE 
    WHEN s.account_locked = 'Y' THEN 'locked'
    WHEN s.account_expired = 'Y' THEN 'expired'
    WHEN s.password_expired = 'Y' THEN 'pwd_expired'
    WHEN s.account_status = 'OPEN' THEN 'enabled'
    ELSE 'disabled'
END
```

**出力例**: `locked`, `expired`, `pwd_expired`, `enabled`, `disabled`

## SQL生成ロジック

### Pythonコード

```python
def generate_taishoku_list_sql(target_date, systems):
    """
    退職者ID削除依頼書用のSQLを動的生成
    
    Args:
        target_date: 対象日（退職日）
        systems: システム定義リスト（taishoku_output_orderでソート済み）
    
    Returns:
        tuple: (SQL文字列, カラム名リスト)
    
    Raises:
        ValueError: システムリストが空の場合
    """
    if not systems:
        raise ValueError("出力対象システムが存在しません")
    
    # 固定列（退職者マスタから取得）
    select_columns = [
        "t.user_cd AS user_cd",
        "t.user_name AS user_name",
        "t.department_name AS department_name"
    ]
    column_names = ["ユーザーID", "氏名", "所属"]
    
    # LEFT JOIN句リスト
    joins = []
    
    # 各システムの列を追加
    for idx, system in enumerate(systems):
        # 出力不要なシステムはスキップ
        if not system.taishoku_output_required:
            continue
        
        alias = f"s{idx}"
        system_id = system.system_id
        
        # LEFT JOIN追加
        joins.append(f"""
    LEFT JOIN IDINV_W_SYSTEM_USERS_{system_id} {alias}
        ON t.user_cd = {alias}.user_cd
        AND {alias}.import_batch_id = (
            SELECT MAX(import_batch_id) 
            FROM IDINV_W_SYSTEM_USERS_{system_id}
        )""")
        
        # 表示SQL取得
        display_sql = system.taishoku_display_sql
        
        if not display_sql or display_sql.strip() == '':
            # 未設定の場合はデフォルトでaccount_statusを使用
            display_sql = f"{alias}.account_status"
        else:
            # エイリアス's'を実際のエイリアスに置換
            display_sql = display_sql.strip()
            display_sql = display_sql.replace("s.", f"{alias}.")
        
        # NVLで存在しない場合は'－'に置換
        select_columns.append(
            f"NVL(({display_sql}), '－') AS sys_{system_id}"
        )
        
        # カラム名（システム名）
        column_names.append(system.system_name)
    
    # SQL組み立て
    sql = f"""SELECT 
    {',\n    '.join(select_columns)}
FROM nam_user_admin.e_imdb_users_end t{''.join(joins)}
WHERE t.taisha_date = :target_date
  AND t.taisha = 1
  AND t.department_main = 1
ORDER BY t.user_cd"""
    
    return sql, column_names


def execute_taishoku_list_query(target_date):
    """
    退職者リストを取得
    
    Args:
        target_date: 対象日
    
    Returns:
        tuple: (データ, カラム名リスト)
    """
    # システム定義を取得（出力順にソート）
    systems = get_active_systems_for_taishoku(order_by='taishoku_output_order')
    
    if not systems:
        return [], []
    
    # SQL生成
    sql, column_names = generate_taishoku_list_sql(target_date, systems)
    
    # 実行
    result = db.execute(sql, {'target_date': target_date})
    
    return result.fetchall(), column_names
```

### 生成されるSQLの例

**前提条件**:
- 対象日: 2026-06-30
- システムA: `taishoku_display_sql = "CASE WHEN s.suspended = 'True' THEN 'suspended' ELSE s.account_status END"`
- システムB: `taishoku_display_sql = "s.system_user_id"`
- システムC: `taishoku_display_sql = NULL`（デフォルト）

**生成されるSQL**:
```sql
SELECT 
    t.user_cd AS user_cd,
    t.user_name AS user_name,
    t.department_name AS department_name,
    NVL((CASE WHEN s0.suspended = 'True' THEN 'suspended' ELSE s0.account_status END), '－') AS sys_system_a,
    NVL((s1.system_user_id), '－') AS sys_system_b,
    NVL((s2.account_status), '－') AS sys_system_c
FROM nam_user_admin.e_imdb_users_end t
    LEFT JOIN IDINV_W_SYSTEM_USERS_system_a s0
        ON t.user_cd = s0.user_cd
        AND s0.import_batch_id = (
            SELECT MAX(import_batch_id) 
            FROM IDINV_W_SYSTEM_USERS_system_a
        )
    LEFT JOIN IDINV_W_SYSTEM_USERS_system_b s1
        ON t.user_cd = s1.user_cd
        AND s1.import_batch_id = (
            SELECT MAX(import_batch_id) 
            FROM IDINV_W_SYSTEM_USERS_system_b
        )
    LEFT JOIN IDINV_W_SYSTEM_USERS_system_c s2
        ON t.user_cd = s2.user_cd
        AND s2.import_batch_id = (
            SELECT MAX(import_batch_id) 
            FROM IDINV_W_SYSTEM_USERS_system_c
        )
WHERE t.taisha_date = :target_date
  AND t.taisha = 1
  AND t.department_main = 1
ORDER BY t.user_cd
```

## バリデーション

### 登録時のバリデーション

システム定義登録・更新時に、`taishoku_display_sql` の妥当性をチェック:

```python
def validate_taishoku_display_sql(system_id, display_sql):
    """
    表示SQLの妥当性チェック
    
    Args:
        system_id: システムID
        display_sql: 表示SQL
    
    Raises:
        ValueError: バリデーションエラー
    """
    # NULLまたは空文字列はOK（デフォルト使用）
    if not display_sql or display_sql.strip() == '':
        return True
    
    display_sql = display_sql.strip()
    
    # 1. 's.'エイリアスを使用しているかチェック
    if 's.' not in display_sql.lower():
        raise ValueError("表示SQLには 's.' エイリアスを使用してください（例: s.account_status）")
    
    # 2. 危険なSQLキーワードを含まないかチェック
    dangerous_keywords = [
        'DELETE', 'UPDATE', 'INSERT', 'DROP', 'TRUNCATE', 
        'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK'
    ]
    display_sql_upper = display_sql.upper()
    for keyword in dangerous_keywords:
        if keyword in display_sql_upper:
            raise ValueError(f"危険なキーワード '{keyword}' は使用できません")
    
    # 3. セミコロンを含まないかチェック（複数SQL実行防止）
    if ';' in display_sql:
        raise ValueError("セミコロン(;)は使用できません")
    
    # 4. 実際に実行してみる（構文チェック）
    test_sql = f"""
        SELECT {display_sql.replace('s.', 'test.')} AS test_column
        FROM IDINV_W_SYSTEM_USERS_{system_id} test
        WHERE ROWNUM = 1
    """
    
    try:
        # DRY RUN（実行計画のみチェック）
        db.execute(f"EXPLAIN PLAN FOR {test_sql}")
    except Exception as e:
        raise ValueError(f"SQLエラー: {str(e)}")
    
    return True
```

### 実行時のエラーハンドリング

```python
def generate_taishoku_list_with_error_handling(target_date):
    """
    退職者リスト生成（エラーハンドリング付き）
    
    Args:
        target_date: 対象日
    
    Returns:
        dict: 結果（成功/エラー情報）
    """
    try:
        data, columns = execute_taishoku_list_query(target_date)
        
        if not data:
            return {
                'status': 'warning',
                'message': f'{target_date}に退職したユーザーは存在しません',
                'data': [],
                'columns': []
            }
        
        return {
            'status': 'success',
            'data': data,
            'columns': columns,
            'record_count': len(data)
        }
        
    except ValueError as e:
        # バリデーションエラー
        return {
            'status': 'error',
            'message': f'設定エラー: {str(e)}',
            'data': [],
            'columns': []
        }
    
    except Exception as e:
        # その他のエラー
        logger.error(f"退職者リスト生成エラー: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': f'システムエラー: {str(e)}',
            'data': [],
            'columns': []
        }
```

## Google Sheets出力

### 出力処理

```python
def export_taishoku_list_to_sheets(target_date, data, columns):
    """
    退職者リストをGoogle Sheetsに出力
    
    Args:
        target_date: 対象日
        data: データ（list of tuples）
        columns: カラム名リスト
    
    Returns:
        str: スプレッドシートURL
    """
    # スプレッドシート作成
    title = f"退職者ID削除依頼書_{target_date.strftime('%Y%m%d')}"
    spreadsheet = gsheet_client.create_spreadsheet(title)
    
    # デフォルトシートを取得
    sheet = spreadsheet.sheet1
    sheet.update_title("退職者一覧")
    
    # タイトル行
    sheet.update('A1', f"退職者ID削除依頼書")
    sheet.update('A2', f"対象日: {target_date.strftime('%Y年%m月%d日')}")
    
    # ヘッダー行（4行目）
    sheet.append_row(columns)
    
    # データ行
    for row in data:
        sheet.append_row(list(row))
    
    # フォーマット設定
    # ヘッダー行を太字・背景色
    sheet.format('A4:Z4', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })
    
    # 列幅調整
    sheet.columns_auto_resize(0, len(columns))
    
    # 出力履歴記録
    record_output_history(
        output_type='TAISHOKU',
        target_date=target_date,
        spreadsheet_url=spreadsheet.url,
        total_users=len(data),
        total_systems=len(columns) - 3  # 固定列3つを除く
    )
    
    return spreadsheet.url
```

## 設定例のまとめ

| システム | 表示内容 | taishoku_display_sql |
|---------|---------|---------------------|
| Active Directory | enabled/disabled | `DECODE(s.is_active, 1, 'enabled', 0, 'disabled', 'unknown')` |
| Salesforce | システム固有ID | `s.user_id` |
| AWS IAM | 状態+期限 | `s.status || CASE WHEN s.expiry_date IS NOT NULL THEN '(' || TO_CHAR(s.expiry_date, 'YYYY/MM') || ')' ELSE '' END` |
| Google Workspace | suspended判定 | `CASE WHEN s.suspended = 'true' THEN 'suspended' ELSE 'enabled' END` |
| Oracle DB | locked判定 | `CASE WHEN s.account_status = 'LOCKED' THEN 'locked' WHEN s.account_status = 'OPEN' THEN 'enabled' ELSE 'disabled' END` |

## 注意事項

1. **エイリアスは必ず 's'**: 設定時は `s.column_name` と記述（実行時に `s0.`, `s1.` に置換される）
2. **NULL安全**: `NVL()` で自動的に '－' に置換されるため、NULL対策は不要
3. **SQL injection対策**: 危険なキーワード、セミコロンはバリデーションで除外
4. **パフォーマンス**: 全システムをLEFT JOINするため、システム数が多い場合は注意（10〜20システム程度なら問題なし）
5. **構文エラー**: 登録時に構文チェックを実施するが、実データでのエラーも考慮してエラーハンドリングを実装
