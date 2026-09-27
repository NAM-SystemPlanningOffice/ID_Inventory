from app.repositories.base_repository import BaseRepository
from typing import List, Dict, Any

class UserRepository(BaseRepository):
    def _is_sql(self, table_or_query: str) -> bool:
        """テーブル名/SQLがSQLかどうかを判定"""
        if not table_or_query:
            return False
        sql_upper = table_or_query.strip().upper()
        return sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')

    def _build_system_join(self, system, alias: str, default_schema: str = 'NAM_IAM_ADMIN') -> str:
        """システムとのJOIN句を構築（取り込み方法に依存しない共通ロジック）

        Args:
            system: システム定義
            alias: テーブルエイリアス
            default_schema: デフォルトスキーマ名

        Returns:
            JOIN句の文字列、エラーの場合はNone
        """
        from app.utils.logger import logger
        system_id = system.system_id.upper()

        # IMPORT_TABLE_NAMEの取得
        if system.import_table_name and system.import_table_name.strip():
            table_or_query = system.import_table_name.strip()
        elif system.import_method in ('CSV', 'XLSX'):
            # CSV/XLSXでIMPORT_TABLE_NAME未指定の場合はデフォルトテーブル
            table_or_query = f"IDINV_W_SYSTEM_USERS_{system_id}"
        else:
            logger.warning(f"System {system_id} has no import_table_name")
            return None

        # SQLかテーブル名かで分岐
        if self._is_sql(table_or_query):
            # SQLの場合：サブクエリとして使用
            return f"""
    LEFT JOIN ({table_or_query}) {alias}
        ON t.USER_CD = {alias}.USER_CD"""
        else:
            # テーブル名の場合：存在チェック後にJOIN
            # スキーマ付きかチェック
            if '.' in table_or_query:
                full_table_name = table_or_query
            else:
                full_table_name = f"{default_schema}.{table_or_query}"

            # テーブル存在チェック
            try:
                check_sql = f"SELECT 1 FROM {full_table_name} WHERE ROWNUM = 1"
                self.execute_one(check_sql)

                return f"""
    LEFT JOIN {full_table_name} {alias}
        ON t.USER_CD = {alias}.USER_CD"""
            except:
                logger.warning(f"Table not found, skipping: {full_table_name}")
                return None
    def get_zaiseki_users(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT USER_CD, USER_NAME, SHOZOKU, POST_NAME, HONMU, KENMU
            FROM NAM_USER_ADMIN.E_IMDB_HONMU_KENMU
            UNION
            SELECT USER_CD, USER_NAME, SHOZOKU, '産育休' AS POST_NAME,
                   NVL(SHOZOKU_NAME, BUMON_NAME) AS HONMU, NULL AS KENMU
            FROM NAM_USER_ADMIN.E_IMDB_SANKYU
            WHERE DEPARTMENT_MAIN = '1'
        """
        return self.execute_query(sql)

    def get_taishoku_users_with_systems(self, target_date, systems) -> List[Dict[str, Any]]:
        """退職者情報を各システムの表示SQLと共に取得（横持ち形式）

        Args:
            target_date: 対象日（YYYY-MM-DD形式）
            systems: システム定義リスト（taishoku_output_order順）

        Returns:
            退職者情報リスト（各システムの列を含む）
        """
        if not systems:
            return []

        # 固定列
        select_columns = [
            "t.USER_CD AS USER_CD",
            "t.USER_NAME AS USER_NAME",
            "t.DEPARTMENT_NAME AS DEPARTMENT_NAME"
        ]

        # LEFT JOIN句リスト
        joins = []

        # 各システムの列を追加（共通ロジック使用）
        from app.utils.logger import logger
        valid_systems = []

        for system in systems:
            alias = f"s{len(valid_systems)}"
            join_clause = self._build_system_join(system, alias)

            if join_clause:
                joins.append(join_clause)
                valid_systems.append(system)

        # 有効なシステムの列を追加
        # 各システムのマッピング定義から必要なカラムを動的に取得
        for idx, system in enumerate(valid_systems):
            alias = f"s{idx}"
            system_id = system.system_id.upper()

            # 表示SQL取得（1行目に表示する値）
            display_sql = system.taishoku_display_sql

            if not display_sql or display_sql.strip() == '':
                # 未設定の場合はデフォルトでUSER_CDを使用
                display_sql = f"{alias}.USER_CD"
            else:
                # エイリアス's'を実際のエイリアスに置換
                display_sql = display_sql.strip()
                display_sql = display_sql.replace("s.", f"{alias}.")
                display_sql = display_sql.replace("S.", f"{alias}.")

            # 表示値（1行目用）
            select_columns.append(
                f"NVL(TO_CHAR({display_sql}), '') AS SYS_{system_id}_DISPLAY_VALUE"
            )

            # 無効化済み判定SQL（2行目用）
            disabled_expression = system.taishoku_disabled_expression

            if disabled_expression and disabled_expression.strip() != '':
                # エイリアス's'を実際のエイリアスに置換
                disabled_expression = disabled_expression.strip()
                disabled_expression = disabled_expression.replace("s.", f"{alias}.")
                disabled_expression = disabled_expression.replace("S.", f"{alias}.")

                # CASE文でラップして無効化判定値を生成（2行目用）
                disabled_sql = f"CASE WHEN {disabled_expression} THEN '－' ELSE NULL END"
                select_columns.append(
                    f"{disabled_sql} AS SYS_{system_id}_DISABLED_VALUE"
                )
            else:
                # 未設定の場合はNULL（作業必要）
                select_columns.append(
                    f"NULL AS SYS_{system_id}_DISABLED_VALUE"
                )

        # SQL組み立て
        columns_str = ',\n    '.join(select_columns)
        joins_str = ''.join(joins)

        sql = f"""SELECT
    {columns_str}
FROM NAM_USER_ADMIN.E_IMDB_USERS_END t{joins_str}
WHERE TRUNC(t.TAISHA_DATE) = TO_DATE(:TARGET_DATE, 'YYYY-MM-DD')
  AND t.TAISHA = 1
  AND t.DEPARTMENT_MAIN = 1
ORDER BY t.USER_CD"""

        # デバッグ用：生成されたSQLをログ出力
        from app.utils.logger import logger
        logger.debug(f"Generated taishoku SQL: {sql}")

        try:
            return self.execute_query(sql, {'TARGET_DATE': target_date})
        except Exception as e:
            logger.error(f"Failed to execute taishoku query: {str(e)}")
            logger.error(f"SQL: {sql}")
            raise

    def get_taishoku_users(self, target_date) -> List[Dict[str, Any]]:
        sql = """
            SELECT USER_CD, USER_NAME, DEPARTMENT_CD, DEPARTMENT_NAME,
                   POST_CD, POST_NAME, TAISHA_DATE
            FROM NAM_USER_ADMIN.E_IMDB_USERS_END
            WHERE TAISHA = 1
              AND DEPARTMENT_MAIN = 1
              AND TRUNC(TAISHA_DATE) = TO_DATE(:TARGET_DATE, 'YYYY-MM-DD')
        """
        return self.execute_query(sql, {'TARGET_DATE': target_date})

    def get_tenshutu_users_for_system(self, target_date, system, sort_sql=None, filter_sql=None) -> List[Dict[str, Any]]:
        """転出者情報を一時テーブルから取得し、1システムのみとJOIN

        複数システムを1本のSQLで横JOINするとシステム間でデカルト積が発生し、
        1システムが1ユーザーにつき複数行（例: im_role）を持つ場合に他システムの
        レコードまで増幅される。これを避けるため、システムごとに個別クエリを実行する。

        Args:
            target_date: 異動日（YYYY-MM-DD形式）
            system: システム定義（1件）
            sort_sql: ソート順SQL（例: t.BEFORE_ORG ASC, s.USER_CD ASC）
            filter_sql: 追加のWHERE句条件（例: s.STATUS = 'ACTIVE'）

        Returns:
            転出者情報リスト（当該システムの列を含む）。JOIN先が存在しない場合は空リスト。
        """
        from app.utils.logger import logger

        alias = "s0"
        join_clause = self._build_system_join(system, alias)
        if not join_clause:
            return []

        system_id = system.system_id.upper()

        # 固定列（転出者情報）
        select_columns = [
            "t.USER_CD AS USER_CD",
            "t.USER_NAME AS USER_NAME",
            "t.BEFORE_ORG AS BEFORE_ORG",
            "t.AFTER_ORG AS AFTER_ORG"
        ]

        # システム側の列を追加（tenshutu_output_columnsに基づく）
        if system.tenshutu_output_columns:
            for col_def in system.tenshutu_output_columns.get('columns', []):
                # sourceがtenshutuの場合はスキップ（一時テーブルから取得）
                if col_def.get('source') == 'tenshutu':
                    continue
                col_name = col_def['column_name']
                select_columns.append(
                    f"NVL(TO_CHAR({alias}.{col_name}), '－') AS SYS_{system_id}_{col_name}"
                )
        else:
            select_columns.append(f"NVL({alias}.USER_CD, '－') AS SYS_{system_id}_USER_CD")

        columns_str = ',\n    '.join(select_columns)

        # WHERE句の構築
        where_clauses = ["TRUNC(t.IDO_DATE) = TO_DATE(:TARGET_DATE, 'YYYY-MM-DD')"]

        if filter_sql and filter_sql.strip():
            adjusted_filter = filter_sql.strip().replace('s.', f'{alias}.')
            where_clauses.append(f"({adjusted_filter})")
            logger.info(f"Tenshutu filter SQL applied ({system_id}): {adjusted_filter}")

        where_clause = "WHERE " + " AND ".join(where_clauses)

        # ORDER BY句の構築
        if sort_sql and sort_sql.strip():
            order_by_clause = sort_sql.strip().replace('s.', f'{alias}.')
            order_by = f"ORDER BY {order_by_clause}"
        else:
            order_by = "ORDER BY t.USER_CD"

        sql = f"""SELECT
    {columns_str}
FROM NAM_IAM_ADMIN.IDINV_W_TENSHUTU_TEMP t{join_clause}
{where_clause}
{order_by}"""

        logger.debug(f"Generated tenshutu SQL ({system_id}): {sql}")

        try:
            return self.execute_query(sql, {'TARGET_DATE': target_date})
        except Exception as e:
            logger.error(f"Failed to execute tenshutu query ({system_id}): {str(e)}")
            logger.error(f"SQL: {sql}")
            raise

    def validate_tenshutu_sql(self, system, filter_sql=None, sort_sql=None) -> None:
        """転出者リストのフィルタSQL・ソート順SQLをドライラン検証する

        転出者リスト出力時と同じJOIN構造（IDINV_W_TENSHUTU_TEMP t + 対象システム s0）を組み立て、
        WHERE ROWNUM = 0 を付けて実行することで、データを取得せずに
        構文・エイリアス・カラムの妥当性をOracleに検証させる。

        転出者クエリには在籍情報（z.）はJOINされないため、z. 参照はここでエラーになる。
        （転出者リストで使用可能なエイリアスは t.=転出者情報、s.=システム情報 のみ）

        Args:
            system: システム定義（1件）
            filter_sql: 転出者フィルタSQL（WHERE句条件、s. エイリアス使用）
            sort_sql: 転出者ソート順SQL（ORDER BY句、t. / s. エイリアス使用）

        Raises:
            ValueError: SQLに不備がある場合（存在しないエイリアス/カラム、構文誤り等）
        """
        from app.utils.logger import logger

        # フィルタ・ソートともに未設定なら検証不要
        has_filter = bool(filter_sql and filter_sql.strip())
        has_sort = bool(sort_sql and sort_sql.strip())
        if not has_filter and not has_sort:
            return

        alias = "s0"
        join_clause = self._build_system_join(system, alias)
        if not join_clause:
            # JOIN先テーブルが存在しない/未設定の場合は出力時もスキップされるため検証不可
            logger.info(f"[{system.system_id}] Skip tenshutu SQL validation: no join target")
            return

        # 出力時と同じWHERE/ORDER BYの組み立て（s. → s0. 置換も同一）
        where_clauses = ["ROWNUM = 0"]
        if has_filter:
            where_clauses.append(f"({filter_sql.strip().replace('s.', f'{alias}.')})")

        sql = f"""SELECT t.USER_CD
FROM NAM_IAM_ADMIN.IDINV_W_TENSHUTU_TEMP t{join_clause}
WHERE {' AND '.join(where_clauses)}"""

        if has_sort:
            sql += "\nORDER BY " + sort_sql.strip().replace('s.', f'{alias}.')

        try:
            self.execute_query(sql)
            logger.info(f"[{system.system_id}] Tenshutu SQL validation passed")
        except Exception as e:
            logger.warning(f"[{system.system_id}] Tenshutu filter/sort SQL validation failed: {str(e)}")
            raise ValueError(
                f"転出者リストのフィルタSQL・ソート順SQLに誤りがあります: {str(e)}\n"
                f"（転出者情報は t.、システム側カラムは s. のエイリアスを使用してください。"
                f"在籍情報の z. は転出者リストでは使用できません。"
                f"末尾の余分なカンマや、存在しないカラム名にもご注意ください）"
            )

    def validate_taishoku_sql(self, system, display_sql=None, disabled_expression=None) -> None:
        """退職者リストの表示SQL・無効化済み判定SQLをドライラン検証する

        退職者リスト出力時と同じ構造（E_IMDB_USERS_END t + 対象システム s0 のJOIN）で、
        表示SQL（NVL(TO_CHAR(...)))・無効化判定SQL（CASE WHEN ... THEN ... END）を組み込み、
        WHERE ROWNUM = 0 を付けて実行することで、データを取得せずに
        構文・エイリアス・カラムの妥当性をOracleに検証させる。

        get_taishoku_users_with_systems と同じエイリアス置換（s./S. → s0.）を行うため、
        出力時と同じ式で検証できる。

        Args:
            system: システム定義（1件）
            display_sql: 退職者表示SQL（1行目に表示する値、s. エイリアス使用）
            disabled_expression: 無効化済み判定SQL（真偽を返す式、s. エイリアス使用）

        Raises:
            ValueError: SQLに不備がある場合（存在しないエイリアス/カラム、構文誤り等）
        """
        from app.utils.logger import logger

        has_display = bool(display_sql and display_sql.strip())
        has_disabled = bool(disabled_expression and disabled_expression.strip())
        if not has_display and not has_disabled:
            return

        alias = "s0"
        join_clause = self._build_system_join(system, alias)
        if not join_clause:
            # JOIN先テーブルが存在しない/未設定の場合は出力時もスキップされるため検証不可
            logger.info(f"[{system.system_id}] Skip taishoku SQL validation: no join target")
            return

        # 出力時（get_taishoku_users_with_systems）と同一の式を組み立て
        select_exprs = ["t.USER_CD"]

        if has_display:
            expr = display_sql.strip().replace("s.", f"{alias}.").replace("S.", f"{alias}.")
            select_exprs.append(f"NVL(TO_CHAR({expr}), '') AS DISPLAY_VALUE")

        if has_disabled:
            expr = disabled_expression.strip().replace("s.", f"{alias}.").replace("S.", f"{alias}.")
            select_exprs.append(f"CASE WHEN {expr} THEN '－' ELSE NULL END AS DISABLED_VALUE")

        columns_str = ',\n    '.join(select_exprs)

        sql = f"""SELECT
    {columns_str}
FROM NAM_USER_ADMIN.E_IMDB_USERS_END t{join_clause}
WHERE ROWNUM = 0"""

        try:
            self.execute_query(sql)
            logger.info(f"[{system.system_id}] Taishoku SQL validation passed")
        except Exception as e:
            logger.warning(f"[{system.system_id}] Taishoku display/disabled SQL validation failed: {str(e)}")
            raise ValueError(
                f"退職者リストの表示SQL・無効化済み判定SQLに誤りがあります: {str(e)}\n"
                f"（システム側カラムは s. のエイリアスを使用してください。"
                f"無効化済み判定SQLは真偽を返す条件式（例: s.STATUS = 'DISABLED'）で記述し、"
                f"存在しないカラム名や構文の誤りにご注意ください）"
            )

    def get_ido_users(self, target_date) -> List[Dict[str, Any]]:
        sql = """
            SELECT IDO_DATE, USER_CD, USER_NAME, IDO_TYPE,
                   DEPARTMENT_CD, POST_CD, DEPARTMENT_NAME, POST_NAME, DEPARTMENT_MAIN
            FROM NAM_USER_ADMIN.E_IMDB_IDO
            WHERE TRUNC(IDO_DATE) = TO_DATE(:TARGET_DATE, 'YYYY-MM-DD')
            ORDER BY USER_CD, IDO_TYPE, DEPARTMENT_MAIN DESC, DEPARTMENT_CD
        """
        return self.execute_query(sql, {'TARGET_DATE': target_date})

    def get_after_org_from_imart(self, kijun_date, user_cds: List[str] = None) -> Dict[str, str]:
        """基準日時点の異動後の所属・役職を imart（@imdb2）から取得し、ユーザー単位で改行連結して返す

        転出者リストの「転出後」列に使用する。E_IMDB_IDO の IDO_TYPE='AFTER' レコードではなく、
        基準日時点で有効な当該ユーザーの全所属（本務・兼務）・役職を対象とする。

        Args:
            kijun_date: 基準日（YYYY-MM-DD形式）。imart各マスタの有効期間判定に使用
            user_cds: 対象ユーザーCDのリスト（省略時は全ユーザー）

        Returns:
            {USER_CD: DEV_AFTER_LIST} の辞書。本務→兼務の順で改行(CRLF)連結
        """
        params = {'KIJUN_DATE': kijun_date}

        # 対象ユーザーが指定されていればIN句で絞り込む（バッチ処理の負荷軽減）
        user_filter = ""
        if user_cds:
            bind_names = []
            for i, uc in enumerate(user_cds):
                key = f"U{i}"
                params[key] = uc
                bind_names.append(f":{key}")
            user_filter = f"AND user_cd IN ({', '.join(bind_names)})"

        sql = f"""
        WITH
        -- 1. ユーザー所属情報の抽出
        dep_base AS (
            SELECT
                user_cd,
                department_cd,
                department_main
            FROM imart.imm_department_ath@imdb2
            WHERE start_date <= TO_DATE(:KIJUN_DATE, 'YYYY-MM-DD')
              AND end_date > TO_DATE(:KIJUN_DATE, 'YYYY-MM-DD')
              AND delete_flag = '0'
              {user_filter}
        ),
        -- 2. ユーザー役職情報の抽出
        post_base AS (
            SELECT
                user_cd,
                department_cd,
                post_cd
            FROM imart.imm_department_post_ath@imdb2
            WHERE start_date <= TO_DATE(:KIJUN_DATE, 'YYYY-MM-DD')
              AND end_date > TO_DATE(:KIJUN_DATE, 'YYYY-MM-DD')
              AND delete_flag = '0'
              AND post_cd NOT IN (951)
              {user_filter}
        ),
        -- 3. 所属と役職を結合したベース情報の作成 (BASE1)
        base_member AS (
            SELECT
                dep.user_cd,
                dep.department_cd,
                post.post_cd,
                dep.department_main
            FROM dep_base dep
            INNER JOIN post_base post
                    ON dep.user_cd = post.user_cd
                   AND dep.department_cd = post.department_cd
        ),
        -- 4. 組織マスタの抽出 (DN1)
        department_master AS (
            SELECT
                department_cd,
                department_name
            FROM imart.imm_department@imdb2
            WHERE start_date <= TO_DATE(:KIJUN_DATE, 'YYYY-MM-DD')
              AND end_date > TO_DATE(:KIJUN_DATE, 'YYYY-MM-DD')
              AND delete_flag = '0'
        ),
        -- 6. 役職マスタの抽出 (PN)
        post_master AS (
            SELECT
                post_cd,
                post_name
            FROM imart.imm_company_post@imdb2
            WHERE start_date <= TO_DATE(:KIJUN_DATE, 'YYYY-MM-DD')
              AND end_date > TO_DATE(:KIJUN_DATE, 'YYYY-MM-DD')
              AND delete_flag = '0'
        ),
        -- 7. 結合・フィルタリングを行い、1行ずつのリスト基礎データを作成
        detail_list AS (
            SELECT
                bm.user_cd,
                bm.department_main,
                DECODE(bm.department_main, '0', '（兼務）', '') || d.department_name || ' ' || p.post_name AS dev_after
            FROM base_member bm
            INNER JOIN department_master d ON bm.department_cd = d.department_cd
            INNER JOIN post_master p       ON bm.post_cd = p.post_cd
            WHERE NOT (bm.department_cd = '2310000' AND bm.department_main = '0')
        )
        -- メイン処理：user_cdでグループ化し、dev_afterを改行コードで合体（本務→兼務の順）
        SELECT
            user_cd AS "USER_CD",
            LISTAGG(dev_after, chr(13) || chr(10)) WITHIN GROUP (ORDER BY department_main DESC) AS "DEV_AFTER_LIST"
        FROM detail_list
        GROUP BY user_cd
        """

        rows = self.execute_query(sql, params)
        return {row['USER_CD']: row['DEV_AFTER_LIST'] for row in rows}

    def get_taishoku_ido_dates(self) -> List[Dict[str, Any]]:
        """過去200日間の退職・異動日のリストを取得"""
        sql = """
            SELECT ido_date AS "IDO_DATE",
                   SUM(taisha) AS "TAISHA_COUNT",
                   SUM(ido) AS "IDO_COUNT"
            FROM (
                SELECT TAISHA_DATE AS ido_date, USER_CD AS user_cd, 1 AS taisha, 0 AS ido
                FROM NAM_USER_ADMIN.E_IMDB_USERS_END
                WHERE DEPARTMENT_MAIN = 1
                  AND TAISHA_DATE > SYSDATE - 200
                  AND TAISHA = 1
                UNION
                SELECT DISTINCT IDO_DATE AS ido_date, USER_CD AS user_cd, 0 AS taisha, 1 AS ido
                FROM NAM_USER_ADMIN.E_IMDB_IDO
                WHERE IDO_DATE > SYSDATE - 200
            )
            GROUP BY ido_date
            ORDER BY ido_date DESC
        """
        return self.execute_query(sql)

    def get_system_users_with_zaiseki_flag(self, system_id: str, import_table_name: str = None, import_method: str = None, filter_sql: str = None, output_mode: str = None, sort_sql: str = None) -> List[Dict[str, Any]]:
        """システムユーザーデータを在籍情報とJOINして取得（棚卸リスト用）

        Args:
            system_id: システムID
            import_table_name: テーブル名またはSQL
            import_method: 取り込み方法（参照用）
            filter_sql: 追加のWHERE句条件（CUSTOM時）
            output_mode: 出力モード（ALL/MISMATCH_ONLY/CUSTOM）
            sort_sql: ソート順SQL（ORDER BY句、例: z.SHOZOKU ASC, s.USER_CD ASC）
                      システム側はエイリアス s、在籍側はエイリアス z を使用

        Returns:
            システムユーザー情報リスト（IS_ZAISEKI_MATCH列を含む）
        """
        from app.utils.logger import logger

        logger.info(f"get_system_users_with_zaiseki_flag called: system_id={system_id}, output_mode={output_mode}")

        # IMPORT_TABLE_NAMEが指定されている場合はそれを使用、未指定ならデフォルトテーブル
        if import_table_name and import_table_name.strip():
            table_or_query = import_table_name.strip()
        else:
            table_or_query = f"IDINV_W_SYSTEM_USERS_{system_id.upper()}"

        # SQLかテーブルかで分岐
        is_sql = self._is_sql(table_or_query)

        if is_sql:
            base_sql = table_or_query
        else:
            # テーブルの場合
            if '.' in table_or_query:
                full_table_name = table_or_query
            else:
                full_table_name = f"NAM_IAM_ADMIN.{table_or_query}"

            # テーブルの存在確認
            check_sql = f"""
                SELECT COUNT(*) as cnt
                FROM ALL_TABLES
                WHERE OWNER = '{full_table_name.split('.')[0]}'
                AND TABLE_NAME = '{full_table_name.split('.')[1]}'
            """

            try:
                result = self.execute_query(check_sql)
                if not result or result[0]['CNT'] == 0:
                    logger.warning(f"Table {full_table_name} does not exist, returning empty list")
                    return []
            except Exception as e:
                logger.error(f"Failed to check table existence: {full_table_name}, error={str(e)}")
                return []

            base_sql = f"SELECT * FROM {full_table_name}"

        # 在籍ユーザー情報とのLEFT JOIN（詳細情報も含む）
        # 在籍情報（E_IMDB_HONMU_KENMU + E_IMDB_SANKYU）
        zaiseki_sql = """
            SELECT USER_CD, USER_NAME, SHOZOKU, POST_NAME, HONMU, KENMU
            FROM NAM_USER_ADMIN.E_IMDB_HONMU_KENMU
            UNION
            SELECT USER_CD, USER_NAME, SHOZOKU, '産育休' AS POST_NAME,
                   NVL(SHOZOKU_NAME, BUMON_NAME) AS HONMU, NULL AS KENMU
            FROM NAM_USER_ADMIN.E_IMDB_SANKYU
            WHERE DEPARTMENT_MAIN = '1'
        """

        # システムユーザーに在籍情報を付与（プレフィックス: ZAISEKI_）
        sql = f"""
SELECT s.*,
       CASE WHEN z.USER_CD IS NOT NULL THEN 1 ELSE 0 END AS IS_ZAISEKI_MATCH,
       z.USER_NAME AS ZAISEKI_USER_NAME,
       z.SHOZOKU AS ZAISEKI_SHOZOKU,
       z.POST_NAME AS ZAISEKI_POST_NAME,
       z.HONMU AS ZAISEKI_HONMU,
       z.KENMU AS ZAISEKI_KENMU
FROM ({base_sql}) s
LEFT JOIN ({zaiseki_sql}) z ON s.USER_CD = z.USER_CD
"""

        # 出力モードに応じたフィルタ
        where_clauses = []

        if output_mode == 'MISMATCH_ONLY':
            # 在籍不一致のみ
            where_clauses.append("z.USER_CD IS NULL")
        elif output_mode == 'CUSTOM':
            # CUSTOM: filter_sqlのみ適用（在籍不一致条件は含めない）
            if filter_sql and filter_sql.strip():
                where_clauses.append(f"({filter_sql.strip()})")
                logger.info(f"[{system_id}] CUSTOM mode filter applied: ({filter_sql.strip()})")
            # filter_sql未指定の場合は全件出力
        # ALL の場合はフィルタなし

        if where_clauses:
            sql += "\nWHERE " + " AND ".join(where_clauses)

        # ソート順（ORDER BY句）を適用
        # filter_sqlと同様、SQLに直接組み込む（z=在籍側、s=システム側のエイリアスをそのまま使用）
        if sort_sql and sort_sql.strip():
            sql += "\nORDER BY " + sort_sql.strip()
            logger.info(f"[{system_id}] Sort applied: ORDER BY {sort_sql.strip()}")

        logger.info(f"[{system_id}] Final SQL with zaiseki flag:\n{sql}")

        return self.execute_query(sql)

    def validate_tanaoroshi_sql(self, system_id: str, import_table_name: str = None,
                                filter_sql: str = None, sort_sql: str = None,
                                output_column_sets: list = None) -> None:
        """棚卸リストの参照元テーブル/SQL・フィルタSQL・ソート順SQLをドライラン検証する

        実際のクエリ構造（参照元＋在籍情報とのJOIN）に filter_sql / sort_sql を組み込み、
        WHERE ROWNUM = 0 を付けて実行することで、データを取得せずに
        参照元SQL・構文・エイリアス・カラムの妥当性をOracleに検証させる。

        CSV/XLSXの場合、呼び出し側で参照元テーブル(IDINV_W_SYSTEM_USERS_XXXX)を
        先に作成/再作成してから本メソッドを呼ぶ前提（変更後の列構成で検証するため）。

        Args:
            system_id: システムID
            import_table_name: テーブル名またはSQL
            filter_sql: 棚卸フィルタSQL（CUSTOM時のWHERE句条件）
            sort_sql: 棚卸ソート順SQL（ORDER BY句）
            output_column_sets: 出力カラム定義のリスト。各要素は
                {'label': '棚卸リスト', 'columns': {'columns': [{'column_name', 'source', ...}]}}
                source='system' のカラムが参照元の実出力カラムに存在するか検証する
                （棚卸・転出者の両方の出力カラム定義を渡せる）

        Raises:
            ValueError: SQLに不備がある場合（参照元SQLの誤り、末尾カンマ、
                        存在しないエイリアス/カラム、出力カラム定義の不整合等）
        """
        from app.utils.logger import logger

        # ベースとなるシステムユーザーSQLを構築
        if import_table_name and import_table_name.strip():
            table_or_query = import_table_name.strip()
        else:
            table_or_query = f"IDINV_W_SYSTEM_USERS_{system_id.upper()}"

        if self._is_sql(table_or_query):
            base_sql = table_or_query
        else:
            if '.' in table_or_query:
                full_table_name = table_or_query
            else:
                full_table_name = f"NAM_IAM_ADMIN.{table_or_query}"

            base_sql = f"SELECT * FROM {full_table_name}"

        # 【第1段階】参照元テーブル/SQL自体を「入力した生の状態」のまま検証
        # （在籍JOINでラップする前に検証するため、s./z. のエイリアスが混じらず
        #   参照元自体の誤りが分かりやすいエラーになる）
        # 同時に出力カラム名を取得し、JOINキーに必須の USER_CD の有無を確認する
        from app.utils.db import get_cursor
        try:
            with get_cursor(self.connection) as cursor:
                cursor.execute(f"SELECT * FROM ({base_sql}) WHERE ROWNUM = 0")
                column_names = [col[0].upper() for col in cursor.description] if cursor.description else []
        except Exception as e:
            logger.warning(f"[{system_id}] Import table/SQL validation failed: {str(e)}")
            raise ValueError(
                f"参照元テーブル/SQL自体に誤りがあります: {str(e)}\n"
                f"（テーブル名・SQL構文・カラム名などをご確認ください）"
            )

        # 参照元の出力カラムに必須の USER_CD が含まれているか確認
        # （在籍情報・システム情報のJOINキーであり、無いと棚卸照合ができない）
        if 'USER_CD' not in column_names:
            logger.warning(f"[{system_id}] Import table/SQL has no USER_CD column: {column_names}")
            raise ValueError(
                "参照元テーブル/SQLの出力カラムに必須の「USER_CD」がありません。\n"
                "（在籍情報との照合キーになるため、USER_CD を出力するようにしてください。"
                "別名のカラムがある場合は AS USER_CD で別名を付けてください）"
            )

        # 出力カラム定義（source=system）のカラムが参照元の実出力カラムに存在するか確認
        # （参照元SQLを修正した結果、出力カラム定義が参照元とマッチしなくなると
        #   リスト出力時にサイレントで空欄になるため、登録・更新時点で検知する）
        # 棚卸リスト・転出者リストの両方の出力カラム定義をチェックする
        for column_set in (output_column_sets or []):
            columns_def = column_set.get('columns')
            if not columns_def or not isinstance(columns_def, dict) or not columns_def.get('columns'):
                continue

            label = column_set.get('label', '出力カラム定義')
            missing_columns = []
            for col_def in columns_def['columns']:
                # source='system' 以外（zaiseki=在籍情報、tenshutu=転出者一時テーブル）は
                # 参照元ではなく固定カラムなのでスキップ
                source = col_def.get('source', 'system')
                if source != 'system':
                    continue
                col_name = (col_def.get('column_name') or '').strip()
                if col_name and col_name.upper() not in column_names:
                    missing_columns.append(col_name)

            if missing_columns:
                logger.warning(f"[{system_id}] {label}: columns not found in import table/SQL: {missing_columns}")
                raise ValueError(
                    f"「{label}」に設定されたカラムが、参照元テーブル/SQLの出力カラムに存在しません: "
                    f"{', '.join(missing_columns)}\n"
                    f"（参照元テーブル/SQLの修正により不整合が生じています。"
                    f"参照元の出力カラム: {', '.join(column_names)}）"
                )

        zaiseki_sql = """
            SELECT USER_CD, USER_NAME, SHOZOKU, POST_NAME, HONMU, KENMU
            FROM NAM_USER_ADMIN.E_IMDB_HONMU_KENMU
            UNION
            SELECT USER_CD, USER_NAME, SHOZOKU, '産育休' AS POST_NAME,
                   NVL(SHOZOKU_NAME, BUMON_NAME) AS HONMU, NULL AS KENMU
            FROM NAM_USER_ADMIN.E_IMDB_SANKYU
            WHERE DEPARTMENT_MAIN = '1'
        """

        sql = f"""
SELECT s.*,
       CASE WHEN z.USER_CD IS NOT NULL THEN 1 ELSE 0 END AS IS_ZAISEKI_MATCH,
       z.USER_NAME AS ZAISEKI_USER_NAME,
       z.SHOZOKU AS ZAISEKI_SHOZOKU,
       z.POST_NAME AS ZAISEKI_POST_NAME,
       z.HONMU AS ZAISEKI_HONMU,
       z.KENMU AS ZAISEKI_KENMU
FROM ({base_sql}) s
LEFT JOIN ({zaiseki_sql}) z ON s.USER_CD = z.USER_CD
"""

        # フィルタSQLとROWNUM=0を組み合わせて、データを取得せずに構文検証
        where_clauses = ["ROWNUM = 0"]
        if filter_sql and filter_sql.strip():
            where_clauses.append(f"({filter_sql.strip()})")
        sql += "\nWHERE " + " AND ".join(where_clauses)

        if sort_sql and sort_sql.strip():
            sql += "\nORDER BY " + sort_sql.strip()

        # 【第2段階】在籍情報とのJOIN・フィルタSQL・ソート順SQLを検証
        # （参照元自体は第1段階で検証済みなので、ここでのエラーは
        #   フィルタSQL/ソート順SQLのエイリアス指定ミス等が主な原因）
        try:
            self.execute_query(sql)
            logger.info(f"[{system_id}] Tanaoroshi SQL validation passed")
        except Exception as e:
            logger.warning(f"[{system_id}] Tanaoroshi filter/sort SQL validation failed: {str(e)}")
            raise ValueError(
                f"棚卸のフィルタSQL・ソート順SQLに誤りがあります: {str(e)}\n"
                f"（システム側カラムは s.、在籍側カラムは z. のエイリアスを使用してください。"
                f"末尾の余分なカンマや、存在しないカラム名にご注意ください）"
            )

    def get_system_users(self, system_id: str, import_table_name: str = None, import_method: str = None, filter_sql: str = None) -> List[Dict[str, Any]]:
        """システムユーザーデータを取得（取り込み方法に依存しない共通ロジック）

        Args:
            system_id: システムID
            import_table_name: テーブル名またはSQL
            import_method: 取り込み方法（参照用、ロジックには影響しない）
            filter_sql: 追加のWHERE句条件（tanaoroshi_filter_sql）
        """
        from app.utils.logger import logger

        logger.info(f"get_system_users called: system_id={system_id}, import_method={import_method}, import_table_name={import_table_name}")

        # IMPORT_TABLE_NAMEが指定されている場合はそれを使用、未指定ならデフォルトテーブル
        if import_table_name and import_table_name.strip():
            table_or_query = import_table_name.strip()
        else:
            table_or_query = f"IDINV_W_SYSTEM_USERS_{system_id.upper()}"

        logger.info(f"get_system_users: system_id={system_id}, table_or_query={table_or_query[:100]}...")

        # SQLかテーブルかで分岐
        is_sql = self._is_sql(table_or_query)
        logger.info(f"get_system_users: system_id={system_id}, is_sql={is_sql}")

        if is_sql:
            # SQLの場合：そのまま使用
            base_sql = table_or_query
            logger.info(f"get_system_users: Using SQL for system_id={system_id}")
        else:
            # テーブルの場合：存在確認後にSELECT文を構築
            # スキーマ付きかチェック
            if '.' in table_or_query:
                full_table_name = table_or_query
            else:
                full_table_name = f"NAM_IAM_ADMIN.{table_or_query}"

            logger.info(f"get_system_users: Using table for system_id={system_id}, full_table_name={full_table_name}")

            # テーブルの存在確認
            check_sql = f"""
                SELECT COUNT(*) as cnt
                FROM ALL_TABLES
                WHERE OWNER = '{full_table_name.split('.')[0]}'
                AND TABLE_NAME = '{full_table_name.split('.')[1]}'
            """

            try:
                result = self.execute_query(check_sql)
                if not result or result[0]['CNT'] == 0:
                    logger.warning(f"Table {full_table_name} does not exist, returning empty list")
                    return []
            except Exception as e:
                logger.error(f"Failed to check table existence: {full_table_name}, error={str(e)}")
                return []

            base_sql = f"SELECT * FROM {full_table_name}"

        # filter_sqlが指定されている場合はWHERE句を追加
        if filter_sql and filter_sql.strip():
            adjusted_filter = filter_sql.strip()
            # base_sqlをサブクエリとしてラップし、エイリアスsを定義
            sql = f"SELECT s.* FROM ({base_sql}) s WHERE {adjusted_filter}"
            logger.info(f"[{system_id}] Filter SQL applied: {adjusted_filter}")
            logger.info(f"[{system_id}] Full SQL with filter:\n{sql}")
        else:
            sql = base_sql
            logger.info(f"[{system_id}] No filter SQL applied, using base SQL")

        logger.info(f"[{system_id}] Final SQL (first 500 chars): {sql[:500]}...")

        return self.execute_query(sql)

    def _build_source_sql(self, import_table_name: str, default_schema: str = 'NAM_IAM_ADMIN') -> str:
        """IMPORT_TABLE_NAMEからSQL文を構築

        Args:
            import_table_name: テーブル名またはSQL
            default_schema: デフォルトスキーマ名

        Returns:
            実行可能なSQL文
        """
        if not import_table_name:
            raise ValueError("参照元テーブル/SQLが設定されていません")

        table_or_query = import_table_name.strip()

        if self._is_sql(table_or_query):
            # SQLの場合：そのまま返す
            return table_or_query
        else:
            # テーブル名の場合：SELECT * を付与
            # スキーマ付きかチェック
            if '.' in table_or_query:
                return f"SELECT * FROM {table_or_query}"
            else:
                return f"SELECT * FROM {default_schema}.{table_or_query}"

    def delete_system_users(self, system_id: str) -> int:
        table_name = f"IDINV_W_SYSTEM_USERS_{system_id.upper()}"
        sql = f"""
            DELETE FROM NAM_IAM_ADMIN.{table_name}
        """
        return self.execute_delete(sql)

    def insert_system_users(self, system_id: str, users: List[Dict[str, Any]], batch_id: str) -> int:
        if not users:
            return 0

        table_name = f"IDINV_W_SYSTEM_USERS_{system_id.upper()}"
        columns = list(users[0].keys())

        if 'IMPORT_BATCH_ID' not in columns:
            columns.insert(0, 'IMPORT_BATCH_ID')

        placeholders = ', '.join([f':{col}' for col in columns])
        columns_str = ', '.join(columns)

        sql = f"""
            INSERT INTO NAM_IAM_ADMIN.{table_name} ({columns_str})
            VALUES ({placeholders})
        """

        count = 0
        with get_cursor(self.connection) as cursor:
            for user in users:
                params = user.copy()
                params['import_batch_id'] = batch_id
                cursor.execute(sql, params)
                count += cursor.rowcount

        return count

    def create_system_user_table(self, system_id: str, columns: List[Dict[str, Any]]) -> None:
        """システムユーザーテーブルを作成

        Args:
            system_id: システムID
            columns: カラム定義リスト

        Raises:
            Exception: テーブル作成に失敗した場合（Oracleエラー詳細を含む）
        """
        from app.utils.logger import logger

        table_name = f"IDINV_W_SYSTEM_USERS_{system_id.upper()}"

        try:
            # 既存テーブルを削除（存在する場合）
            drop_sql = f"DROP TABLE NAM_IAM_ADMIN.{table_name}"
            try:
                self.execute_delete(drop_sql)
                logger.info(f"Dropped existing table: {table_name}")
            except Exception as e:
                # テーブルが存在しない場合は無視
                logger.debug(f"Table does not exist (ignored): {table_name}")

            # カラム定義を構築
            column_defs = ["IMPORT_BATCH_ID VARCHAR2(50)"]

            for col in columns:
                col_name = col['target_column']
                data_type = col.get('data_type', 'string')

                if data_type == 'number':
                    oracle_type = 'NUMBER'
                elif data_type == 'date':
                    oracle_type = 'DATE'
                else:
                    oracle_type = 'VARCHAR2(500)'

                nullable = '' if col.get('required', False) and col_name == 'USER_CD' else ''
                column_defs.append(f"{col_name} {oracle_type} {nullable}".strip())

            columns_sql = ',\n    '.join(column_defs)

            create_sql = f"""
CREATE TABLE NAM_IAM_ADMIN.{table_name} (
    {columns_sql}
)
"""

            logger.info(f"Creating table: {table_name}")
            logger.debug(f"CREATE TABLE SQL:\n{create_sql}")

            self.execute_insert(create_sql)
            logger.info(f"Table created successfully: {table_name}")

        except Exception as e:
            logger.error(f"Failed to create table: {table_name}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")

            # Oracleエラーの詳細を取得
            if hasattr(e, 'args') and e.args:
                for i, arg in enumerate(e.args):
                    logger.error(f"Oracle error args[{i}]: {arg}")

            # 再スローして呼び出し側でトランザクションをロールバック
            raise Exception(f"テーブル作成エラー ({table_name}): {str(e)}") from e


from app.utils.db import get_cursor
