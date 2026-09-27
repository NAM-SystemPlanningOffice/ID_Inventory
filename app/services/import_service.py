import os
import time
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any
from werkzeug.utils import secure_filename

from app.repositories.system_repository import SystemRepository
from app.repositories.user_repository import UserRepository
from app.repositories.history_repository import HistoryRepository
from app.models.history import ImportHistory
from app.utils.file_parser import FileParser
from app.utils.validators import validate_file_extension, validate_import_data
from app.utils.date_utils import generate_batch_id
from app.utils.logger import logger
from app.utils.db import get_db_connection
from app.config import Config
import json

class ImportService:
    def __init__(self):
        self.upload_folder = Config.UPLOAD_FOLDER
        os.makedirs(self.upload_folder, exist_ok=True)

    def import_user_data(self, system_id: str, uploaded_file, user: str) -> Dict[str, Any]:
        temp_file_path = None
        start_time = datetime.now()

        try:
            self.cleanup_old_temp_files()

            logger.info(f"File upload started: system_id={system_id}, filename={uploaded_file.filename}")

            if not validate_file_extension(uploaded_file.filename, Config.ALLOWED_EXTENSIONS):
                raise ValueError(f"許可されていないファイル形式です。CSV または XLSX ファイルのみアップロード可能です。")

            temp_file_path = self._save_temp_file(uploaded_file)
            file_size = os.path.getsize(temp_file_path)
            file_hash = self._calculate_file_hash(temp_file_path)

            with get_db_connection() as conn:
                system_repo = SystemRepository(conn)
                system_info = system_repo.find_by_id(system_id)

                if not system_info:
                    raise ValueError(f"システムID '{system_id}' が見つかりません")

                if system_info.import_method not in ('CSV', 'XLSX'):
                    raise ValueError(f"システム '{system_info.system_name}' はファイル取り込み対象外です")

                self._ensure_system_table_exists(conn, system_id)

                mapping = system_info.import_mapping
                if not mapping:
                    raise ValueError(f"システム '{system_info.system_name}' のマッピング定義が設定されていません")

                file_type = uploaded_file.filename.rsplit('.', 1)[1].lower()
                raw_data = FileParser.parse_file(
                    temp_file_path,
                    file_type,
                    encoding=mapping.get('file_encoding', 'utf-8-sig'),  # BOM付き・BOMなしUTF-8両対応
                    has_header=mapping.get('has_header', True),
                    skip_rows=mapping.get('skip_rows', 0),
                    delimiter=mapping.get('delimiter', ','),
                    quotechar=mapping.get('quotechar', '"'),
                    sheet_name=mapping.get('sheet_name')
                )

                logger.info(f"File parsing completed: records={len(raw_data)}")

                transformed_data = FileParser.transform_data(raw_data, mapping)

                # 検証を実行（必須チェックでエラーのある行はスキップ）
                validation_result = validate_import_data(transformed_data, mapping)
                valid_data = validation_result['valid_data']
                validation_errors = validation_result['errors']

                batch_id = generate_batch_id(system_id)

                user_repo = UserRepository(conn)
                user_repo.delete_system_users(system_id)
                inserted_count = user_repo.insert_system_users(system_id, valid_data, batch_id)

                system_repo.update_import_info(
                    system_id,
                    datetime.now(),
                    user,
                    inserted_count
                )

                end_time = datetime.now()
                status = 'SUCCESS' if not validation_errors else 'WARNING'
                history = ImportHistory(
                    batch_id=batch_id,
                    system_id=system_id,
                    import_user=user,
                    file_name=uploaded_file.filename,
                    file_size=file_size,
                    file_hash=file_hash,
                    status=status,
                    total_records=len(transformed_data),
                    success_records=inserted_count,
                    error_records=len(validation_errors),
                    start_time=start_time,
                    end_time=end_time,
                    error_message=self._format_validation_errors(validation_errors) if validation_errors else None
                )

                history_repo = HistoryRepository(conn)
                history_repo.insert_import_history(history)

                logger.info(f"Import completed: system_id={system_id}, records={inserted_count}, skipped={len(validation_errors)}")

                result = {
                    'status': 'success',
                    'batch_id': batch_id,
                    'records': inserted_count,
                    'system_name': system_info.system_name
                }

                # 警告がある場合は追加情報を返す
                if validation_errors:
                    result['warnings'] = {
                        'skipped_rows': len(validation_errors),
                        'errors': validation_errors[:10]  # 最初の10件のみ
                    }

                return result

        except Exception as e:
            logger.error(f"Import failed: system_id={system_id}, error={str(e)}")

            try:
                with get_db_connection() as conn:
                    end_time = datetime.now()
                    batch_id = generate_batch_id(system_id)
                    history = ImportHistory(
                        batch_id=batch_id,
                        system_id=system_id,
                        import_user=user,
                        file_name=uploaded_file.filename if uploaded_file else None,
                        file_size=os.path.getsize(temp_file_path) if temp_file_path else None,
                        status='ERROR',
                        total_records=0,
                        success_records=0,
                        error_records=0,
                        error_message=str(e),
                        start_time=start_time,
                        end_time=end_time
                    )
                    history_repo = HistoryRepository(conn)
                    history_repo.insert_import_history(history)
            except Exception as history_error:
                logger.error(f"Failed to record import history: {str(history_error)}")

            raise

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    logger.info(f"Temp file deleted: {os.path.basename(temp_file_path)}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {temp_file_path}, {e}")

    def _save_temp_file(self, uploaded_file) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = os.path.splitext(uploaded_file.filename)[1]
        unique_id = str(uuid.uuid4())[:8]
        temp_filename = f"{timestamp}_{unique_id}{ext}"
        temp_path = os.path.join(self.upload_folder, temp_filename)

        uploaded_file.save(temp_path)

        file_size = os.path.getsize(temp_path)
        if file_size > Config.MAX_UPLOAD_SIZE:
            os.remove(temp_path)
            raise ValueError(f"ファイルサイズが上限を超えています: {file_size} bytes (上限: {Config.MAX_UPLOAD_SIZE})")

        logger.info(f"Temp file saved: {temp_filename}, size: {file_size} bytes")
        return temp_path

    def _calculate_file_hash(self, file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _format_validation_errors(self, errors: list) -> str:
        """バリデーションエラーをフォーマット"""
        if not errors:
            return None

        # 最大10件までエラーメッセージを作成
        messages = []
        for i, error in enumerate(errors[:10]):
            messages.append(f"行{error['row']}: {error['message']}")

        result = '\n'.join(messages)

        # 10件以上ある場合は省略メッセージを追加
        if len(errors) > 10:
            result += f"\n...他 {len(errors) - 10} 件のエラー"

        return result

    def cleanup_old_temp_files(self, max_age_hours: int = 24):
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder, exist_ok=True)
            return

        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 60 * 60)
        deleted_count = 0

        for filename in os.listdir(self.upload_folder):
            filepath = os.path.join(self.upload_folder, filename)

            try:
                file_mtime = os.path.getmtime(filepath)

                if file_mtime < cutoff_time:
                    os.remove(filepath)
                    deleted_count += 1
                    logger.info(f"Deleted old temp file: {filename}")

            except Exception as e:
                logger.warning(f"Failed to delete old temp file: {filename}, {e}")

        if deleted_count > 0:
            logger.info(f"Cleanup: deleted {deleted_count} old temp files")

    def get_import_status(self):
        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            systems = system_repo.find_all(active_only=True)

            oldest_datetime = system_repo.get_oldest_import_datetime()

            systems_status = []
            for system in systems:
                if system.import_method:
                    systems_status.append({
                        'system_id': system.system_id,
                        'system_name': system.system_name,
                        'import_method': system.import_method,
                        'last_import_datetime': system.last_import_datetime,
                        'last_import_record_count': system.last_import_record_count
                    })

            return {
                'oldest_import_datetime': oldest_datetime,
                'systems': systems_status
            }

    def _ensure_system_table_exists(self, conn, system_id: str) -> bool:
        system_repo = SystemRepository(conn)
        system = system_repo.find_by_id(system_id)

        if not system or system.import_method not in ('CSV', 'XLSX'):
            return False

        if not system.import_mapping_json:
            raise ValueError(f"システム '{system.system_name}' のマッピング定義が設定されていません")

        user_repo = UserRepository(conn)
        table_name = f"IDINV_W_SYSTEM_USERS_{system_id.upper()}"

        try:
            test_sql = f"SELECT COUNT(*) AS CNT FROM NAM_IAM_ADMIN.{table_name} WHERE ROWNUM = 1"
            user_repo.execute_one(test_sql)
            logger.debug(f"System user table exists: {table_name}")
            return True
        except Exception as e:
            logger.info(f"Creating system user table: {table_name}")
            mapping = json.loads(system.import_mapping_json)
            user_repo.create_system_user_table(system_id, mapping['columns'])
            logger.info(f"System user table created: {table_name}")
            return True
