-- ============================================================
-- 前提スキーマと外部データソースへの参照権限付与
-- ============================================================
-- 本システムのオブジェクトは NAM_IAM_ADMIN スキーマに作成する
-- （テーブルはすべて IDINV_ 接頭辞を付与）。
--
-- 本システムは以下の他スキーマのオブジェクトを参照(SELECT)のみ行う。
-- そのため各オブジェクト所有者側で NAM_IAM_ADMIN へ SELECT 権限を付与する。
--
--   (A) e_imdb_* : 在籍・退職・異動・認証情報（nam_user_admin 所有）
--   (B) DIRECT参照先 : 各システム定義の IMPORT_TABLE_NAME に指定された
--                      既存 Oracle テーブル／ビュー（nam_user_admin, NAM_OPE 等）
--
-- ============================================================


-- ------------------------------------------------------------
-- (A) 在籍系マスタ（nam_user_admin 所有）— nam_user_admin で実行
-- ------------------------------------------------------------
GRANT SELECT ON nam_user_admin.e_imdb_honmu_kenmu TO NAM_IAM_ADMIN;  -- 在籍ユーザー（本務・兼務）
GRANT SELECT ON nam_user_admin.e_imdb_sankyu      TO NAM_IAM_ADMIN;  -- 産育休ユーザー
GRANT SELECT ON nam_user_admin.e_imdb_users_end   TO NAM_IAM_ADMIN;  -- 退職者情報
GRANT SELECT ON nam_user_admin.e_imdb_ido         TO NAM_IAM_ADMIN;  -- 組織異動者情報
GRANT SELECT ON nam_user_admin.e_imdb2_users      TO NAM_IAM_ADMIN;  -- ログイン認証（内設コード照合）


-- ------------------------------------------------------------
-- (B) DIRECT参照先（IMPORT_TABLE_NAME に指定された既存オブジェクト）
-- ------------------------------------------------------------
-- import_method = 'DIRECT' のシステムは、IMPORT_TABLE_NAME に既存テーブル／
-- ビュー名または SQL を指定して直接参照する（例: NAM_USER_ADMIN.ZOOM_USERS）。
-- これらは他スキーマ所有のため、参照する分だけ SELECT 権限が必要。
--
-- 【重要・スキーマ省略への注意】
--   IMPORT_TABLE_NAME 内でスキーマを省略した参照（例: FROM ZOOM_USERS）は、
--   旧環境では実行ユーザー nam_user_admin の自スキーマに解決されていた。
--   新環境では実行ユーザーが NAM_IAM_ADMIN になるため、スキーマ省略のままだと
--   解決先が変わり ORA-00942 になる。省略参照は必ずスキーマを明示するよう
--   IMPORT_TABLE_NAME を更新すること（下記 migration 参照）。
--
-- IMPORT_TABLE_NAME 内 SQL の参照オブジェクトを洗い出した結果に基づく GRANT。
-- （FROM/JOIN 参照先。WITH句/インライン別名の code(svs)・role(zoom) は実オブジェクト
--   ではないため対象外。自スキーマの t_system_users_* / IDINV_W_SYSTEM_USERS_* も対象外。）
--
-- 参考・再洗い出しクエリ:
--   SELECT SYSTEM_ID, IMPORT_METHOD, IMPORT_TABLE_NAME
--   FROM   NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS   -- 旧環境では nam_user_admin.m_system_user_info
--   WHERE  IMPORT_METHOD = 'DIRECT'
--      OR  UPPER(IMPORT_TABLE_NAME) LIKE 'SELECT%'
--      OR  UPPER(IMPORT_TABLE_NAME) LIKE 'WITH%';

-- (B-1) nam_user_admin 所有 — nam_user_admin で実行
--       明示参照:
GRANT SELECT ON nam_user_admin.gmail_users      TO NAM_IAM_ADMIN;  -- gmail（明示参照）
GRANT SELECT ON nam_user_admin.mail_auth_detail TO NAM_IAM_ADMIN;  -- gmail（明示参照）
GRANT SELECT ON nam_user_admin.zoom_users       TO NAM_IAM_ADMIN;  -- zoom（明示参照）
--       スキーマ省略参照（実在は nam_user_admin。7-2 でスキーマ明示化する対象）:
GRANT SELECT ON nam_user_admin.adusers             TO NAM_IAM_ADMIN;  -- anrepo, bunsho_kanri, windows, windows_all
GRANT SELECT ON nam_user_admin.adgroup_asis        TO NAM_IAM_ADMIN;  -- anrepo, bunsho_kanri
GRANT SELECT ON nam_user_admin.group_google        TO NAM_IAM_ADMIN;  -- mobilemail
GRANT SELECT ON nam_user_admin.faims_id_convert    TO NAM_IAM_ADMIN;  -- faims
GRANT SELECT ON nam_user_admin.e_imdb_users_simple TO NAM_IAM_ADMIN;  -- sba
--       ※ gmail_users は mobilemail / windows / windows_all でも省略参照されるが、
--         上の nam_user_admin.gmail_users への GRANT で共通にカバーされる。

-- (B-2) NAM_OPE 所有 — nam_ope で実行
GRANT SELECT ON nam_ope.remote_auth         TO NAM_IAM_ADMIN;  -- remote_users
GRANT SELECT ON nam_ope.code                TO NAM_IAM_ADMIN;  -- remote_users
GRANT SELECT ON nam_ope.remote_outside_user TO NAM_IAM_ADMIN;  -- windows, windows_all

-- ------------------------------------------------------------
-- (C) DBリンク経由の参照（GRANT では付与できない）
-- ------------------------------------------------------------
-- 以下は他DBのオブジェクトを DB リンク経由で参照している。
-- これらは NAM_IAM_ADMIN への GRANT では解決できない。必要なのは:
--   1) DB リンク（@imdb / @imdb2 / @pma）が NAM_IAM_ADMIN から使用可能であること
--      （NAM_IAM_ADMIN 所有の private link を作成するか、public link を用意する）
--   2) リンクの接続ユーザーが、リンク先DBで対象オブジェクトへの SELECT 権限を持つこと
--
--   @imdb  : imart.b_m_account_role_b      （im_role）
--            imart.b_m_role_i              （im_role）
--            imart.imfr_ut_sp_mail_apply   （mobilemail）
--            imart.imw_t_cpl_matter        （mobilemail）
--            imart.m_emp_term              （faims）
--   @imdb2 : imart.imm_user                （gmail）
--   @pma   : pma.v_svs_user_attr           （svs）
