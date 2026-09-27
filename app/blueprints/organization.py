from flask import Blueprint, render_template, request, jsonify
from app.repositories.organization_repository import OrganizationRepository
from app.utils.db import get_db_connection
from app.models.organization import OrganizationChange
from app.utils.date_utils import parse_date

organization_bp = Blueprint('organization', __name__)

@organization_bp.route('/')
def index():
    try:
        with get_db_connection() as conn:
            org_repo = OrganizationRepository(conn)
            changes = org_repo.find_all()

        return render_template('organization.html', changes=changes)
    except Exception as e:
        return render_template('organization.html', changes=[], error=str(e))

@organization_bp.route('/create', methods=['POST'])
def create_change():
    try:
        data = request.json

        change = OrganizationChange(
            change_date=parse_date(data['change_date']),
            before_org_cd=data['before_org_cd'],
            before_org_name=data.get('before_org_name'),
            after_org_cd=data['after_org_cd'],
            after_org_name=data.get('after_org_name'),
            remarks=data.get('remarks')
        )

        with get_db_connection() as conn:
            org_repo = OrganizationRepository(conn)
            org_repo.insert(change)

        return jsonify({'status': 'success', 'message': '組織変更を登録しました'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@organization_bp.route('/delete', methods=['DELETE'])
def delete_change():
    try:
        data = request.json

        change_date = parse_date(data['change_date'])
        before_org_cd = data['before_org_cd']
        after_org_cd = data['after_org_cd']

        with get_db_connection() as conn:
            org_repo = OrganizationRepository(conn)
            org_repo.delete(change_date, before_org_cd, after_org_cd)

        return jsonify({'status': 'success', 'message': '組織変更を削除しました'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@organization_bp.route('/list/<date_str>')
def get_changes_by_date(date_str):
    try:
        target_date = parse_date(date_str)

        with get_db_connection() as conn:
            org_repo = OrganizationRepository(conn)
            changes = org_repo.find_by_date(target_date)

        return jsonify({
            'status': 'success',
            'changes': [change.to_dict() for change in changes]
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
