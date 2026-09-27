from app.repositories.base_repository import BaseRepository
from typing import Optional, Dict, Any


class AuthRepository(BaseRepository):
    """ログイン認可のための在籍者マスタ（e_imdb2_users）参照"""

    def get_user_naisetsu(self, user_cd: str) -> Optional[Dict[str, Any]]:
        """USER_CD に一致するユーザーの室コード（NAISETSU）等を取得

        Args:
            user_cd: Entra ID の UPN からドメインを除いたユーザーコード

        Returns:
            ユーザー情報（USER_CD, USER_NAME, NAISETSU）。存在しなければ None。
        """
        sql = """
            SELECT USER_CD, USER_NAME, NAISETSU
            FROM NAM_USER_ADMIN.E_IMDB2_USERS
            WHERE USER_CD = :USER_CD
        """
        return self.execute_one(sql, {'USER_CD': user_cd})
