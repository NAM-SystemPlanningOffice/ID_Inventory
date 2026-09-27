"""Azure App Service（Entra ID / Easy Auth）による認証・認可

App Service の組み込み認証（Easy Auth）を有効にすると、Entra ID で認証済みの
ユーザー情報が各リクエストのヘッダに付与される。本モジュールはそのヘッダから
ユーザーの UPN を取り出し、下記ロジックで認可する。

  1. UPN（例: abc123@nam.co.jp）から AUTH_EMAIL_DOMAIN を除いてユーザーCDを得る
  2. e_imdb2_users.USER_CD と照合し、NAISETSU（室コード）を取得
  3. NAISETSU が ALLOWED_NAISETSU_CODES に含まれればログインを許可する

ローカル開発（FLASK_ENV=development）では Easy Auth ヘッダが存在しないため、
認証・認可を完全にバイパスし、DEV_LOGIN_USER_CD をログインユーザーとして扱う。

【重要】ここで扱うログインユーザーの USER_CD（e_imdb2_users）は、在籍・異動
データ（e_imdb_honmu_kenmu 等）の USER_CD とは別体系であり、突き合わせは行わない。
"""
from functools import wraps
from flask import request, g, current_app, render_template, abort

from app.config import Config
from app.repositories.auth_repository import AuthRepository
from app.utils.db import get_db_connection
from app.utils.logger import logger

# Easy Auth が付与する認証済みユーザー情報ヘッダ
# X-MS-CLIENT-PRINCIPAL-NAME には Entra ID の UPN（サインイン名）が入る。
PRINCIPAL_NAME_HEADER = 'X-MS-CLIENT-PRINCIPAL-NAME'


def _extract_user_cd(upn: str) -> str:
    """UPN からユーザーCDを取り出す（ドメイン部を除去）

    例: 'abc123@nam.co.jp' -> 'abc123'
    設定ドメイン以外や '@' を含まない値でも、'@' 以前を採用して安全に処理する。
    """
    if not upn:
        return ''
    upn = upn.strip()
    domain = (Config.AUTH_EMAIL_DOMAIN or '').lower()
    lowered = upn.lower()
    if domain and lowered.endswith(domain):
        return upn[: -len(domain)]
    # ドメイン不一致でも '@' があれば手前を採用
    if '@' in upn:
        return upn.split('@', 1)[0]
    return upn


def _authorize_user_cd(user_cd: str):
    """USER_CD を e_imdb2_users と照合し、許可された室コードか確認する

    Returns:
        (allowed: bool, user_info: dict|None, reason: str)
    """
    if not user_cd:
        return False, None, 'ユーザーCDを特定できませんでした'

    try:
        with get_db_connection() as conn:
            auth_repo = AuthRepository(conn)
            user_info = auth_repo.get_user_naisetsu(user_cd)
    except Exception as e:
        logger.error(f"Authorization DB lookup failed for user_cd={user_cd}: {str(e)}")
        return False, None, '認可情報の取得に失敗しました'

    if not user_info:
        logger.warning(f"Login denied: user_cd={user_cd} not found in e_imdb2_users")
        return False, None, '利用者として登録されていません'

    naisetsu = user_info.get('NAISETSU')
    naisetsu_str = str(naisetsu).strip() if naisetsu is not None else ''
    allowed_codes = Config.ALLOWED_NAISETSU_CODES

    if naisetsu_str and naisetsu_str in allowed_codes:
        return True, user_info, ''

    logger.warning(
        f"Login denied: user_cd={user_cd} naisetsu={naisetsu_str} "
        f"not in allowed codes {allowed_codes}"
    )
    return False, user_info, 'この室のコードではログインが許可されていません'


def _current_principal():
    """現在のリクエストの認証済みユーザーCDを取得する

    Returns:
        (user_cd: str|None, is_dev_bypass: bool)
    """
    # 開発環境: 認証を完全バイパス
    if Config.IS_DEVELOPMENT:
        return Config.DEV_LOGIN_USER_CD, True

    upn = request.headers.get(PRINCIPAL_NAME_HEADER)
    if not upn:
        return None, False
    return _extract_user_cd(upn), False


def load_authenticated_user():
    """before_request フック: ログインユーザーを解決し g に格納、未認可なら遮断する

    - 開発環境ではバイパスし、DEV_LOGIN_USER_CD をログインユーザーとして扱う
    - 静的ファイル・ヘルスチェックは認証対象外
    """
    # 静的ファイルは認証不要
    if request.endpoint == 'static':
        return None

    # ヘルスチェック用エンドポイントは認証不要
    if request.path == '/healthz':
        return None

    user_cd, is_dev = _current_principal()

    # 開発環境: 認可チェックもスキップして通す
    if is_dev:
        g.user_cd = user_cd
        g.user_name = user_cd
        g.auth_bypassed = True
        return None

    # 本番: Easy Auth ヘッダが無い＝未認証（通常は App Service 側で弾かれる）
    if not user_cd:
        logger.warning("No Easy Auth principal header present; access denied")
        return render_template('403.html', reason='認証情報が確認できませんでした'), 401

    allowed, user_info, reason = _authorize_user_cd(user_cd)
    if not allowed:
        return render_template('403.html', reason=reason, user_cd=user_cd), 403

    g.user_cd = user_info.get('USER_CD', user_cd)
    g.user_name = user_info.get('USER_NAME') or user_cd
    g.auth_bypassed = False
    return None


def inject_current_user():
    """context_processor: テンプレートでログインユーザー情報を参照可能にする"""
    return {
        'current_user_cd': getattr(g, 'user_cd', None),
        'current_user_name': getattr(g, 'user_name', None),
        'auth_bypassed': getattr(g, 'auth_bypassed', False),
    }


def init_auth(app):
    """アプリに認証・認可フックを登録する"""
    app.before_request(load_authenticated_user)
    app.context_processor(inject_current_user)
