import re
from werkzeug.utils import secure_filename

def validate_system_id(system_id):
    if not system_id:
        raise ValueError("system_id が空です")

    if len(system_id) > 50:
        raise ValueError("system_id は50文字以内にしてください")

    if not re.match(r'^[a-z0-9_]+$', system_id):
        raise ValueError(
            "system_id は小文字英数字とアンダースコアのみ使用できます"
        )

    return True

def validate_file_extension(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def validate_import_data(data, mapping):
    """
    取り込みデータの検証

    Args:
        data: 変換後のデータ（List[Dict]）
        mapping: マッピング定義

    Returns:
        dict: {
            'valid_data': 検証に通ったデータのリスト,
            'errors': エラー情報のリスト [{'row': 行番号, 'message': エラーメッセージ}, ...]
        }
    """
    valid_data = []
    errors = []

    # required=True のカラムを抽出
    required_columns = [
        col for col in mapping['columns']
        if col.get('required', False)
    ]

    for idx, row in enumerate(data, start=1):
        row_errors = []

        # 必須カラムのチェック
        for col in required_columns:
            target_col = col['target_column']
            value = row.get(target_col)

            # 値がNoneまたは空文字列の場合はエラー
            if value is None or (isinstance(value, str) and value.strip() == ''):
                source_info = ""
                if col.get('source_column'):
                    source_info = f"（元カラム: '{col['source_column']}'）"
                elif col.get('source_index') is not None:
                    source_info = f"（元列番号: {col['source_index']}）"

                row_errors.append(f"{target_col} が空です {source_info}")

        if row_errors:
            errors.append({
                'row': idx,
                'message': '、'.join(row_errors)
            })
        else:
            valid_data.append(row)

    return {
        'valid_data': valid_data,
        'errors': errors
    }

def validate_taishoku_display_sql(display_sql):
    """
    退職者表示SQLのバリデーション

    Args:
        display_sql: 表示SQL

    Returns:
        bool: True（バリデーション成功）

    Raises:
        ValueError: バリデーションエラー
    """
    # NULLまたは空文字列はOK（デフォルト使用）
    if not display_sql or display_sql.strip() == '':
        return True

    display_sql = display_sql.strip()

    # 1. 's.'エイリアスを使用しているかチェック
    if 's.' not in display_sql.lower():
        raise ValueError("表示SQLには 's.' エイリアスを使用してください（例: s.account_status, S.USER_ID）")

    # 2. 危険なSQLキーワードを含まないかチェック
    dangerous_keywords = [
        'DELETE', 'UPDATE', 'INSERT', 'DROP', 'TRUNCATE',
        'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK',
        'EXECUTE', 'EXEC', 'CALL'
    ]
    display_sql_upper = display_sql.upper()
    for keyword in dangerous_keywords:
        # 単語境界を考慮（例: DELETE_FLAG は許可）
        if f' {keyword} ' in f' {display_sql_upper} ' or \
           display_sql_upper.startswith(f'{keyword} ') or \
           display_sql_upper.endswith(f' {keyword}'):
            raise ValueError(f"危険なキーワード '{keyword}' は使用できません")

    # 3. セミコロンを含まないかチェック（複数SQL実行防止）
    if ';' in display_sql:
        raise ValueError("セミコロン(;)は使用できません")

    # 4. コメントを含まないかチェック（SQLインジェクション防止）
    if '--' in display_sql or '/*' in display_sql or '*/' in display_sql:
        raise ValueError("SQLコメント(--、/*)は使用できません")

    return True
