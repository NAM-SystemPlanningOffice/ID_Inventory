# ファイル処理設計

## 一時ファイル管理方針

### 基本方針
- **専用バッチ処理は不要**
- データ取り込み処理の開始時に古いファイルをクリーンアップ
- 処理完了後（成功・失敗問わず）、一時ファイルを確実に削除

## ディレクトリ構成

```
/tmp/uploads/
├── {uuid}.csv      # 一時アップロードファイル
├── {uuid}.xlsx
└── ...
```

## ファイル命名規則

```python
import uuid
from datetime import datetime

def generate_temp_filename(original_filename):
    """
    一時ファイル名を生成
    
    Args:
        original_filename: 元のファイル名（例: "users.csv"）
    
    Returns:
        str: UUID付きファイル名（例: "20260625_143025_a1b2c3d4.csv"）
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = os.path.splitext(original_filename)[1]
    unique_id = str(uuid.uuid4())[:8]
    return f"{timestamp}_{unique_id}{ext}"
```

**例**: `20260625_143025_a1b2c3d4.csv`

## ファイル処理フロー

### 擬似コード

```python
def import_user_data(system_id, uploaded_file):
    """
    ユーザーデータ取り込み処理
    
    Args:
        system_id: システムID
        uploaded_file: アップロードされたファイルオブジェクト
    
    Returns:
        dict: 処理結果
    """
    temp_file_path = None
    
    try:
        # ステップ1: 古い一時ファイルのクリーンアップ
        cleanup_old_temp_files()
        
        # ステップ2: 一時ファイルとして保存
        temp_file_path = save_temp_file(uploaded_file)
        
        # ステップ3: ファイル検証
        validate_file(temp_file_path)
        
        # ステップ4: マッピング定義取得
        mapping = get_mapping_definition(system_id)
        
        # ステップ5: データ読み込み・変換
        data = parse_file(temp_file_path, mapping)
        
        # ステップ6: バリデーション
        validate_data(data, mapping)
        
        # ステップ7: DB取り込み
        import_to_database(system_id, data)
        
        # ステップ8: 履歴記録
        record_import_history(system_id, success=True)
        
        return {"status": "success", "records": len(data)}
        
    except Exception as e:
        # エラー時も履歴記録
        record_import_history(system_id, success=False, error=str(e))
        raise
        
    finally:
        # ステップ9: 一時ファイルを確実に削除
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                # 削除失敗はログに記録するが、エラーにはしない
                logger.warning(f"Failed to delete temp file: {temp_file_path}, {e}")


def cleanup_old_temp_files(max_age_hours=24):
    """
    24時間以上経過した一時ファイルを削除
    
    Args:
        max_age_hours: ファイルの最大保持時間（デフォルト24時間）
    """
    upload_dir = '/tmp/uploads/'
    
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
        return
    
    current_time = time.time()
    cutoff_time = current_time - (max_age_hours * 60 * 60)
    
    for filename in os.listdir(upload_dir):
        filepath = os.path.join(upload_dir, filename)
        
        try:
            # ファイルの最終更新時刻を取得
            file_mtime = os.path.getmtime(filepath)
            
            # 24時間以上経過していれば削除
            if file_mtime < cutoff_time:
                os.remove(filepath)
                logger.info(f"Deleted old temp file: {filename}")
                
        except Exception as e:
            # 削除失敗してもスキップ（次回削除試行）
            logger.warning(f"Failed to delete old temp file: {filename}, {e}")


def save_temp_file(uploaded_file):
    """
    アップロードファイルを一時保存
    
    Args:
        uploaded_file: Flaskのファイルオブジェクト
    
    Returns:
        str: 保存したファイルのパス
    """
    upload_dir = '/tmp/uploads/'
    os.makedirs(upload_dir, exist_ok=True)
    
    # UUIDでランダムなファイル名を生成
    temp_filename = generate_temp_filename(uploaded_file.filename)
    temp_path = os.path.join(upload_dir, temp_filename)
    
    # ファイル保存
    uploaded_file.save(temp_path)
    
    # ファイルサイズチェック（100MB上限）
    file_size = os.path.getsize(temp_path)
    max_size = 100 * 1024 * 1024  # 100MB
    
    if file_size > max_size:
        os.remove(temp_path)
        raise ValueError(f"File size exceeds limit: {file_size} bytes (max: {max_size})")
    
    logger.info(f"Temp file saved: {temp_filename}, size: {file_size} bytes")
    
    return temp_path
```

## エラーハンドリング

### ケース1: ファイル保存失敗
```python
try:
    temp_path = save_temp_file(uploaded_file)
except IOError as e:
    return {"status": "error", "message": "ファイル保存に失敗しました"}
```

### ケース2: ファイル形式エラー
```python
try:
    validate_file(temp_path)
except ValueError as e:
    # finally句で一時ファイルは削除される
    return {"status": "error", "message": "ファイル形式が不正です"}
```

### ケース3: DB取り込みエラー
```python
try:
    import_to_database(system_id, data)
except DatabaseError as e:
    # トランザクションロールバック
    # finally句で一時ファイルは削除される
    return {"status": "error", "message": "データベース取り込みに失敗しました"}
```

## セキュリティ考慮事項

### 1. ファイル名の安全性
- 元のファイル名をそのまま使用しない（パストラバーサル対策）
- UUIDでランダムなファイル名を生成（推測不可）

### 2. ファイルサイズ制限
- 最大100MBに制限（DoS攻撃対策）
- アップロード時とサーバー保存後の2段階でチェック

### 3. ファイル形式検証
- 拡張子チェック（`.csv`, `.xlsx` のみ許可）
- MIMEタイプチェック
- ファイル内容の検証（マジックバイト確認）

### 4. ディレクトリアクセス制御
- `/tmp/uploads/` ディレクトリの権限を適切に設定
- Webサーバーから直接アクセスできないように設定

## パフォーマンス考慮事項

### ファイル数の想定
- 同時アップロード: 最大10ユーザー
- 1回の処理時間: 平均30秒
- 滞留ファイル数: 通常0〜10個

### クリーンアップの頻度
- 取り込み処理の開始時に毎回実行
- 処理オーバーヘッド: 数ミリ秒（ファイル数が少ないため）

### ディスク容量
- 1ファイルあたり: 平均1MB（数百レコード）
- 最大ファイルサイズ: 100MB
- 必要なディスク容量: 1GB程度（十分なマージン）

## 監視・ログ

### ログ出力項目
```python
logger.info(f"File upload started: system_id={system_id}, filename={original_filename}")
logger.info(f"Temp file saved: {temp_filename}, size={file_size}")
logger.info(f"File parsing completed: records={record_count}")
logger.info(f"Import completed: system_id={system_id}, records={record_count}")
logger.info(f"Temp file deleted: {temp_filename}")
logger.info(f"Cleanup: deleted {deleted_count} old temp files")
```

### エラーログ
```python
logger.error(f"File validation failed: {temp_filename}, error={str(e)}")
logger.error(f"Import failed: system_id={system_id}, error={str(e)}")
logger.warning(f"Failed to delete temp file: {temp_filename}, error={str(e)}")
```

## 運用時の注意事項

1. **App Service再起動時**
   - `/tmp/` ディレクトリの内容は保持されない可能性あり
   - 問題なし（次回取り込み時にディレクトリが自動作成される）

2. **複数インスタンス構成時**
   - 各インスタンスが独立した `/tmp/` を持つ
   - ファイルは他のインスタンスから見えない（問題なし）

3. **ディスク容量監視**
   - Azure App Serviceのディスク使用率を監視
   - 通常は数MB程度の使用量（問題になることはない）

4. **障害時の復旧**
   - 一時ファイルが残っていても次回取り込み時にクリーンアップされる
   - 手動での削除は不要
