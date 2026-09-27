from flask import Blueprint, render_template, jsonify
from app.services.import_service import ImportService
from app.repositories.user_repository import UserRepository
from app.utils.db import get_db_connection

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    try:
        import_service = ImportService()
        import_status = import_service.get_import_status()

        return render_template('index.html', import_status=import_status)
    except Exception as e:
        return render_template('index.html', error=str(e))

@index_bp.route('/api/ido-taishoku-dates/<year_month>')
def get_ido_taishoku_dates(year_month):
    try:
        with get_db_connection() as conn:
            user_repo = UserRepository(conn)

            ido_dates = user_repo.get_ido_dates_by_month(year_month)
            taishoku_dates = user_repo.get_taishoku_dates_by_month(year_month)

            # 日付が既に文字列の場合はそのまま、datetimeオブジェクトの場合は変換
            ido_date_list = []
            for row in ido_dates:
                date_val = row['ido_date']
                if isinstance(date_val, str):
                    ido_date_list.append(date_val)
                else:
                    ido_date_list.append(date_val.isoformat())

            taishoku_date_list = []
            for row in taishoku_dates:
                date_val = row['taisha_date']
                if isinstance(date_val, str):
                    taishoku_date_list.append(date_val)
                else:
                    taishoku_date_list.append(date_val.isoformat())

            all_dates = sorted(set(ido_date_list + taishoku_date_list))

            result = []
            for date_str in all_dates:
                result.append({
                    'date': date_str,
                    'has_ido': date_str in ido_date_list,
                    'has_taishoku': date_str in taishoku_date_list
                })

            return jsonify({'status': 'success', 'dates': result})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
