"""
組織転出者判定サービス
"""
from typing import List, Dict, Any
from app.repositories.user_repository import UserRepository
from app.repositories.organization_repository import OrganizationRepository
from app.utils.logger import logger


class TenshutuService:
    """組織転出者の判定ロジック"""

    def __init__(self, conn):
        self.user_repo = UserRepository(conn)
        self.org_repo = OrganizationRepository(conn)

    def filter_tenshutu_users(self, target_date: str) -> List[Dict[str, Any]]:
        """
        転出者を判定し、出力対象ユーザーのリストを生成

        Args:
            target_date: 異動日（YYYY-MM-DD形式）

        Returns:
            出力対象ユーザーのリスト
            [
                {
                    'USER_CD': 'U00123',
                    'USER_NAME': '山田太郎',
                    'IDO_DATE': '2026-06-30',
                    'BEFORE_ORG': '営業部(本務) 課長\n開発部(兼務) 担当',
                    'AFTER_ORG': '総務部(本務) 部長\n企画部(兼務) 課長'
                },
                ...
            ]
        """
        from datetime import datetime

        # 異動情報取得
        ido_records = self.user_repo.get_ido_users(target_date)

        if not ido_records:
            return []

        # 組織変更情報取得（target_dateをdatetimeに変換）
        target_date_obj = datetime.strptime(target_date, '%Y-%m-%d')
        org_changes_list = self.org_repo.find_by_date(target_date_obj)
        org_changes = {
            (oc.before_org_cd, oc.after_org_cd): oc
            for oc in org_changes_list
        }

        # ユーザーごとにグループ化
        users_dict = {}
        for ido in ido_records:
            user_cd = ido.get('USER_CD')
            if user_cd not in users_dict:
                users_dict[user_cd] = {
                    'USER_CD': user_cd,
                    'USER_NAME': ido.get('USER_NAME'),
                    'IDO_DATE': ido.get('IDO_DATE'),
                    'END': [],
                    'AFTER': []
                }

            ido_type = ido.get('IDO_TYPE')
            dept_info = {
                'DEPARTMENT_CD': ido.get('DEPARTMENT_CD'),
                'DEPARTMENT_NAME': ido.get('DEPARTMENT_NAME'),
                'POST_CD': ido.get('POST_CD'),
                'POST_NAME': ido.get('POST_NAME'),
                'DEPARTMENT_MAIN': ido.get('DEPARTMENT_MAIN')
            }

            if ido_type == 'END':
                users_dict[user_cd]['END'].append(dept_info)
            elif ido_type == 'AFTER':
                users_dict[user_cd]['AFTER'].append(dept_info)

        # 各ユーザーの判定
        # 「転出前(BEFORE_ORG)」は従来通りE_IMDB_IDOのEND側フィルタ結果を使用する。
        # 「転出後(AFTER_ORG)」はE_IMDB_IDOのAFTERではなく、基準日時点で有効な
        # 当該ユーザーの全所属・役職（imart @imdb2）を後段でまとめて設定する。
        result = []
        for user_cd, user_data in users_dict.items():
            filtered_end, _filtered_after = self._filter_user_ido(
                user_data['END'],
                user_data['AFTER'],
                org_changes
            )

            # 転出元（END）が残っている場合のみ出力対象
            # 組織CD変更等を考慮した結果、転出元の組織が無くなった場合は対象外
            if filtered_end:
                before_org_str = self._format_org_list(filtered_end)

                result.append({
                    'USER_CD': user_cd,
                    'USER_NAME': user_data['USER_NAME'],
                    'IDO_DATE': user_data['IDO_DATE'],
                    'BEFORE_ORG': before_org_str,
                    'AFTER_ORG': ''  # 後段でimartの異動後所属・役職を設定
                })

        # 「転出後」を基準日時点の所属・役職（imart）で設定
        # 対象ユーザー分のみをまとめて1クエリで取得する
        if result:
            target_user_cds = [u['USER_CD'] for u in result]
            after_org_map = self.user_repo.get_after_org_from_imart(target_date, target_user_cds)
            for u in result:
                u['AFTER_ORG'] = after_org_map.get(u['USER_CD'], '')

        logger.info(f"Filtered tenshutu users: {len(result)} users from {len(users_dict)} total")
        return result

    def _filter_user_ido(
        self,
        end_list: List[Dict],
        after_list: List[Dict],
        org_changes: Dict
    ) -> tuple:
        """
        1ユーザーの異動情報をフィルタリング

        ロジック:
        - 組織体制変更（組織コード変更）による転出は除外
          （END側=旧コード, AFTER側=新コード が IDINV_ORGANIZATION_CHANGES に登録されている場合）
        - ENDとAFTERで組織コードが一致する組織のうち、昇格・役職変更なしは除外
        - 上記以外は出力対象（組織転出・着任）

        Returns:
            tuple: (filtered_end, filtered_after)
        """
        # 組織コード→組織情報の索引
        end_by_code = {d['DEPARTMENT_CD']: d for d in end_list}
        after_by_code = {d['DEPARTMENT_CD']: d for d in after_list}

        # 除外する組織コードのセット（ENDとAFTERで別コードになり得るため分離）
        excluded_end_codes = set()
        excluded_after_codes = set()

        # 組織体制変更（組織コード変更）による除外
        # 登録された (旧コード, 新コード) が END(旧) と AFTER(新) の両方に存在すれば
        # 実質的な転出ではないため除外対象
        for (before_cd, after_cd) in org_changes.keys():
            if before_cd in end_by_code and after_cd in after_by_code:
                excluded_end_codes.add(before_cd)
                excluded_after_codes.add(after_cd)

        # 同一組織コードで残っているものについて、昇格・役職変更なしを除外
        common_org_codes = set(end_by_code) & set(after_by_code)

        for org_cd in common_org_codes:
            # 既に組織変更で除外済みならスキップ
            if org_cd in excluded_end_codes:
                continue

            end_dept = end_by_code[org_cd]
            after_dept = after_by_code[org_cd]

            # 役職の昇格判定（post_cdが小さい方が上位）
            is_promotion = False
            if end_dept['POST_CD'] and after_dept['POST_CD']:
                try:
                    end_post = int(end_dept['POST_CD'])
                    after_post = int(after_dept['POST_CD'])
                    is_promotion = after_post < end_post
                except:
                    pass

            if is_promotion:
                # ケース1-2: 同一組織内の昇格 → 除外
                excluded_end_codes.add(org_cd)
                excluded_after_codes.add(org_cd)
                continue

            # 役職変更なし（または降格）の場合
            if end_dept['POST_CD'] == after_dept['POST_CD']:
                # 役職も同じ → 除外（異動なし）
                excluded_end_codes.add(org_cd)
                excluded_after_codes.add(org_cd)

        # 除外されない組織のみを抽出
        # 並び順（本務→兼務）は get_ido_users のORDER BY（DEPARTMENT_MAIN DESC）で担保済み
        filtered_end = [d for d in end_list if d['DEPARTMENT_CD'] not in excluded_end_codes]
        filtered_after = [d for d in after_list if d['DEPARTMENT_CD'] not in excluded_after_codes]

        return filtered_end, filtered_after

    def _format_org_list(self, org_list: List[Dict]) -> str:
        """
        組織リストを文字列にフォーマット

        例: "(本務) 営業部 課長\n(兼務) 開発部 担当"
        """
        lines = []
        for org in org_list:
            dept_name = org['DEPARTMENT_NAME'] or ''
            post_name = org['POST_NAME'] or ''
            is_main = org['DEPARTMENT_MAIN'] == '1'

            line = f"({'本務' if is_main else '兼務'}) {dept_name} {post_name}"
            lines.append(line.strip())

        return '\n'.join(lines)

    def save_to_temp_table(self, target_date: str, users: List[Dict[str, Any]]):
        """
        一時テーブルに保存

        Args:
            target_date: 異動日（YYYY-MM-DD形式）
            users: フィルタリング済みユーザーリスト
        """
        from datetime import datetime

        # 既存データを削除
        delete_sql = """
            DELETE FROM NAM_IAM_ADMIN.IDINV_W_TENSHUTU_TEMP
            WHERE TRUNC(IDO_DATE) = TO_DATE(:TARGET_DATE, 'YYYY-MM-DD')
        """
        try:
            logger.debug(f"Deleting temp data for date: {target_date}")
            self.user_repo.execute_delete(delete_sql, {'TARGET_DATE': target_date})
            logger.info(f"Deleted existing temp data for date: {target_date}")
        except Exception as e:
            logger.error(f"Failed to delete temp data: {str(e)}, target_date={target_date}")
            raise

        if not users:
            return

        # 新規データを挿入
        insert_sql = """
            INSERT INTO NAM_IAM_ADMIN.IDINV_W_TENSHUTU_TEMP (
                USER_CD, USER_NAME, IDO_DATE, BEFORE_ORG, AFTER_ORG
            ) VALUES (
                :USER_CD, :USER_NAME, :IDO_DATE, :BEFORE_ORG, :AFTER_ORG
            )
        """

        for user in users:
            # IDO_DATEをdatetimeオブジェクトに変換（DB DATE型へのバインド用）
            ido_date = user['IDO_DATE']
            if isinstance(ido_date, str):
                # ISO形式の場合は日付部分のみを抽出してdatetimeに変換
                date_part = ido_date.split('T')[0] if 'T' in ido_date else ido_date[:10]
                user['IDO_DATE'] = datetime.strptime(date_part, '%Y-%m-%d')
            # 既にdatetimeオブジェクトの場合はそのまま使用

            try:
                logger.debug(f"Inserting user: {user['USER_CD']}, ido_date={user['IDO_DATE']}")
                self.user_repo.execute_insert(insert_sql, user)
            except Exception as e:
                logger.error(f"Failed to insert user: {str(e)}, user={user}")
                raise

        logger.info(f"Inserted {len(users)} users to temp table")
