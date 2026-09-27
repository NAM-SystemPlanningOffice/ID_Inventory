from flask import Blueprint, render_template, request, jsonify, g
from app.services.import_service import ImportService
from app.services.system_service import SystemService

import_bp = Blueprint('import_bp', __name__)

@import_bp.route('/')
def index():
    try:
        system_service = SystemService()
        systems = system_service.get_all_systems(active_only=True)
        import_systems = [s for s in systems if s.import_method]

        return render_template('import.html', systems=import_systems)
    except Exception as e:
        return render_template('import.html', systems=[], error=str(e))

@import_bp.route('/upload', methods=['POST'])
def upload():
    try:
        system_id = request.form.get('system_id')
        if not system_id:
            return jsonify({'status': 'error', 'message': 'システムIDが指定されていません'}), 400

        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'ファイルが選択されていません'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'ファイルが選択されていません'}), 400

        # 取り込みユーザーはログインユーザー（Entra ID）を記録する。
        # フォーム値は信用せず、認証済みのユーザーCDを優先する。
        user = getattr(g, 'user_cd', None) or request.form.get('user') or 'system'

        import_service = ImportService()
        result = import_service.import_user_data(system_id, file, user)

        return jsonify(result)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@import_bp.route('/system/<system_id>')
def get_system_info(system_id):
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
