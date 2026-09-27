from flask import Blueprint, render_template, request, jsonify
from app.services.system_service import SystemService
from app.utils.db import get_db_connection
from app.repositories.system_repository import SystemRepository

system_bp = Blueprint('system', __name__)

@system_bp.route('/')
def index():
    try:
        system_service = SystemService()
        systems = system_service.get_all_systems(active_only=False)

        return render_template('system.html', systems=systems)
    except Exception as e:
        return render_template('system.html', systems=[], error=str(e))

@system_bp.route('/<system_id>')
def get_system(system_id):
    try:
        system_service = SystemService()
        system = system_service.get_system_by_id(system_id)

        return jsonify({
            'status': 'success',
            'system': system.to_dict()
        })

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@system_bp.route('/create', methods=['POST'])
def create_system():
    try:
        data = request.json
        user = data.get('user', 'system')

        system_service = SystemService()
        system_service.create_system(data, user)

        return jsonify({'status': 'success', 'message': 'システムを登録しました'})

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@system_bp.route('/update/<system_id>', methods=['PUT'])
def update_system(system_id):
    try:
        data = request.json
        user = data.get('user', 'system')

        system_service = SystemService()
        system_service.update_system(system_id, data, user)

        return jsonify({'status': 'success', 'message': 'システムを更新しました'})

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@system_bp.route('/<system_id>/available-columns', methods=['GET'])
def get_available_columns(system_id):
    """システムで利用可能なカラム一覧を取得"""
    try:
        with get_db_connection() as conn:
            system_repo = SystemRepository(conn)
            system = system_repo.find_by_id(system_id)

            if not system:
                return jsonify({'status': 'error', 'message': 'システムが見つかりません'}), 404

            # システムのカラム取得（取り込み方法に依存しない統一ロジック）
            system_columns = []

            # IMPORT_TABLE_NAMEの取得
            if system.import_table_name and system.import_table_name.strip():
                table_or_query = system.import_table_name.strip()
            elif system.import_method in ('CSV', 'XLSX'):
                # CSV/XLSXでIMPORT_TABLE_NAME未指定の場合はデフォルトテーブル
                table_or_query = f"IDINV_W_SYSTEM_USERS_{system_id.upper()}"
            else:
                table_or_query = None

            from app.utils.logger import logger
            logger.info(f"get_available_columns: system_id={system_id}, import_method={system.import_method}, table_or_query={table_or_query[:100] if table_or_query else None}...")

            # SQLまたはテーブルからカラムを取得
            if table_or_query:
                sql_upper = table_or_query.upper()
                is_sql = sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')

                logger.info(f"get_available_columns: system_id={system_id}, is_sql={is_sql}")

                try:
                    from app.utils.db import get_cursor

                    if is_sql:
                        # SQLの場合：WHERE ROWNUM = 0を追加してカラムのみ取得
                        sql = f"SELECT * FROM ({table_or_query}) WHERE ROWNUM = 0"
                    else:
                        # テーブルの場合
                        # スキーマ付きかチェック
                        if '.' in table_or_query:
                            sql = f"SELECT * FROM {table_or_query} WHERE ROWNUM = 0"
                        else:
                            # デフォルトスキーマを付与
                            sql = f"SELECT * FROM NAM_IAM_ADMIN.{table_or_query} WHERE ROWNUM = 0"

                    # カラム名を取得（結果が空でもカラム名は取得できる）
                    with get_cursor(conn) as cursor:
                        cursor.execute(sql)
                        if cursor.description:
                            for col_desc in cursor.description:
                                col_name = col_desc[0]
                                system_columns.append({
                                    'value': col_name,
                                    'label': col_name
                                })
                except Exception as e:
                    # エラーの場合：CSV/XLSXならマッピング定義から取得
                    from app.utils.logger import logger
                    logger.error(f"Failed to get columns from table/SQL for system {system_id}: {str(e)}")

                    if system.import_method in ('CSV', 'XLSX') and system.import_mapping:
                        # フォールバック：マッピング定義から取得
                        for col in system.import_mapping.get('columns', []):
                            system_columns.append({
                                'value': col['target_column'],
                                'label': col['target_column']
                            })

            # 在籍情報のカラム
            zaiseki_columns = [
                {'value': 'USER_CD', 'label': 'ユーザーCD'},
                {'value': 'USER_NAME', 'label': 'ユーザー名'},
                {'value': 'SHOZOKU', 'label': '所属'},
                {'value': 'POST_NAME', 'label': '役職名'},
                {'value': 'HONMU', 'label': '本務'},
                {'value': 'KENMU', 'label': '兼務'}
            ]

            # 異動情報のカラム
            ido_columns = [
                {'value': 'USER_CD', 'label': 'ユーザーCD'},
                {'value': 'USER_NAME', 'label': 'ユーザー名'},
                {'value': 'IDO_DATE', 'label': '異動日'},
                {'value': 'BEFORE_ORG', 'label': '転出元'},
                {'value': 'AFTER_ORG', 'label': '異動後'}
            ]

            return jsonify({
                'status': 'success',
                'system_columns': system_columns,
                'zaiseki_columns': zaiseki_columns,
                'ido_columns': ido_columns
            })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
