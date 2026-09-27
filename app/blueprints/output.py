from flask import Blueprint, render_template, request, jsonify
from app.services.output_service import OutputService

output_bp = Blueprint('output', __name__)

def extract_date_only(date_str):
    """ISO形式の日付文字列から日付部分のみを抽出 (YYYY-MM-DD)"""
    if not date_str:
        return None
    # タイムスタンプ部分を削除
    if 'T' in date_str:
        return date_str.split('T')[0]
    # 最初の10文字を取得 (YYYY-MM-DD)
    return date_str[:10]

@output_bp.route('/')
def index():
    return render_template('output.html')

@output_bp.route('/dates', methods=['GET'])
def get_taishoku_ido_dates():
    """退職・異動日のリストを取得"""
    try:
        output_service = OutputService()
        dates = output_service.get_taishoku_ido_dates()
        return jsonify({
            'status': 'success',
            'dates': dates
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@output_bp.route('/tanaoroshi', methods=['POST'])
def generate_tanaoroshi():
    """棚卸リストを生成（現時点の状態）"""
    try:
        output_service = OutputService()
        result = output_service.generate_tanaoroshi_list()

        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@output_bp.route('/taishoku-tenshutu', methods=['POST'])
def generate_taishoku_tenshutu():
    """退職者・転出者リストを生成"""
    try:
        target_date = request.json.get('target_date')
        if not target_date:
            return jsonify({'status': 'error', 'message': '対象日を指定してください'}), 400

        # 日付部分のみを抽出
        target_date = extract_date_only(target_date)

        output_service = OutputService()
        taishoku_result = output_service.generate_taishoku_list(target_date)
        tenshutu_result = output_service.generate_tenshutu_list(target_date)

        # 各リストでエラーが発生した場合はエラー内容を収集して表示
        errors = []
        if taishoku_result.get('status') == 'error':
            errors.append(f"退職者ID削除依頼書: {taishoku_result.get('message')}")
        if tenshutu_result.get('status') == 'error':
            errors.append(f"組織転出者アクセス権限確認リスト: {tenshutu_result.get('message')}")

        if errors:
            return jsonify({
                'status': 'warning',
                'message': '一部のリスト生成でエラーが発生しました',
                'errors': errors,
                'taishoku_url': taishoku_result.get('url'),
                'tenshutu_url': tenshutu_result.get('url')
            })

        # 各リストの対象有無に応じてメッセージを組み立てる
        # URLが無い場合は対象なし（サービス側で対象0件と判定されたケース）
        if taishoku_result.get('url'):
            taishoku_msg = '退職者リストを生成しました'
        else:
            taishoku_msg = '退職者リストは対象なしです'

        if tenshutu_result.get('url'):
            tenshutu_msg = '転出者リストを生成しました'
        else:
            tenshutu_msg = '転出者リストは対象なしです'

        return jsonify({
            'status': 'success',
            'message': f'{taishoku_msg}／{tenshutu_msg}',
            'taishoku_url': taishoku_result.get('url'),
            'tenshutu_url': tenshutu_result.get('url')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
