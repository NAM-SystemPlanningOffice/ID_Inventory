-- ============================================================
-- 既存環境向け：旧名テーブル → 新スキーマ・新名への移行スクリプト
-- ============================================================
-- 旧: nam_user_admin.{m_,t_}*        （M_/T_ 接頭辞、旧スキーマ）
-- 新: NAM_IAM_ADMIN.IDINV_*          （IDINV_ 接頭辞、新スキーマ）
--
-- 【重要】Oracle の ALTER TABLE ... RENAME TO はスキーマをまたげない。
--   スキーマ移動を伴うため、下記いずれかの方法で実施すること。
--
--   方法A（推奨・データ移送）:
--     新スキーマに CREATE（001〜 のCREATE系マイグレーションを実行）した上で、
--     INSERT ... SELECT で旧テーブルからデータを移送し、旧テーブルを DROP する。
--
--   方法B（同一スキーマで運用継続する場合）:
--     スキーマ移動をせず nam_user_admin 内で名前だけ変える場合は、
--     本ファイル末尾の「同一スキーマ・リネームのみ」節を使用する。
--
-- 実行前に必ずバックアップを取得すること。
-- ============================================================


-- ------------------------------------------------------------
-- 方法A：新スキーマへデータ移送（CREATE系マイグレーション実行後に実施）
-- ------------------------------------------------------------
-- ※ 事前に 001〜004 / create_idinv_tenshutu_temp_table.sql を NAM_IAM_ADMIN で実行済みであること。

-- 1. システム定義マスタ
INSERT INTO NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
SELECT * FROM nam_user_admin.m_system_user_info;

-- 2. 組織変更情報
INSERT INTO NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES
SELECT * FROM nam_user_admin.t_organization_change;

-- 3. 取り込み履歴
INSERT INTO NAM_IAM_ADMIN.IDINV_IMPORT_HISTORY
SELECT * FROM nam_user_admin.t_import_history;

-- 4. リスト出力履歴（OUTPUT_ID は IDENTITY のため列を明示して除外）
INSERT INTO NAM_IAM_ADMIN.IDINV_OUTPUT_HISTORY
    (OUTPUT_TYPE, OUTPUT_DATETIME, OUTPUT_USER, TARGET_DATE, TARGET_MONTH,
     SPREADSHEET_URL, STATUS, TOTAL_SYSTEMS, TOTAL_USERS, ERROR_MESSAGE, CREATED_AT)
SELECT
     OUTPUT_TYPE, OUTPUT_DATETIME, OUTPUT_USER, TARGET_DATE, TARGET_MONTH,
     SPREADSHEET_URL, STATUS, TOTAL_SYSTEMS, TOTAL_USERS, ERROR_MESSAGE, CREATED_AT
FROM nam_user_admin.t_output_history;

-- 5. 各システムのユーザーデータテーブル（t_system_users_*）
--    動的テーブルのため、存在するぶんだけ個別に移送する。
--    例（sap_hr / active_directory）:
--
--    CREATE TABLE NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_SAP_HR
--        AS SELECT * FROM nam_user_admin.t_system_users_sap_hr;
--    CREATE TABLE NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_ACTIVE_DIRECTORY
--        AS SELECT * FROM nam_user_admin.t_system_users_active_directory;
--
--    ※ USER_CD の NOT NULL 制約は CREATE ... AS SELECT では引き継がれないため、
--      必要に応じて ALTER TABLE ... MODIFY (USER_CD NOT NULL) を追記すること。

-- 6. 組織転出者一時テーブル（都度洗い替えのためデータ移送不要。CREATE のみでよい）

-- 7. システム定義の IMPORT_TABLE_NAME 内に埋め込まれた参照の補正
--    IMPORT_TABLE_NAME にはテーブル名だけでなく SQL 文が格納されている場合があり、
--    その中に旧テーブル名やスキーマ省略参照が含まれるため、移送後に置換する。

-- 7-1. CSV/XLSX 取り込みテーブル名の改名（T_SYSTEM_USERS_XXXX → IDINV_W_SYSTEM_USERS_XXXX）
--      テーブル名指定・SQL埋め込みの双方をカバー。
UPDATE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
SET IMPORT_TABLE_NAME =
        REPLACE(REPLACE(IMPORT_TABLE_NAME,
            'T_SYSTEM_USERS_', 'IDINV_W_SYSTEM_USERS_'),
            't_system_users_', 'IDINV_W_SYSTEM_USERS_')
WHERE IMPORT_TABLE_NAME IS NOT NULL
  AND (IMPORT_TABLE_NAME LIKE '%T_SYSTEM_USERS_%'
    OR IMPORT_TABLE_NAME LIKE '%t_system_users_%');

-- 7-2. DIRECT参照の SQL 内でスキーマ省略している参照へスキーマ名を明示する。
--      新環境では実行ユーザーが NAM_IAM_ADMIN になり、無修飾参照が自スキーマ
--      （NAM_IAM_ADMIN）を指してしまい ORA-00942 となるため、実在スキーマを付与する。
--
--      スキーマ省略参照のオブジェクトと使用システム（洗い出し済み）:
--        adusers             … anrepo, bunsho_kanri, windows, windows_all
--        adgroup_asis        … anrepo, bunsho_kanri
--        gmail_users         … mobilemail, windows, windows_all
--        group_google        … mobilemail
--        faims_id_convert    … faims
--        e_imdb_users_simple … sba
--      いずれも実在スキーマは nam_user_admin。
--
--      置換方針（二重修飾・部分一致の防止）:
--        - 直前が識別子文字/ドットでなく（＝既に nam_user_admin. 等で修飾済みは対象外）、
--          直後も識別子文字でない出現のみを対象に、先頭へ nam_user_admin. を付与する。
--        - 大文字小文字を無視（'i'）、全出現（occurrence=0）を置換。
--        - キャプチャ \2 で元の綴り（大小）を保持する。
UPDATE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
SET IMPORT_TABLE_NAME =
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
    REGEXP_REPLACE(
        IMPORT_TABLE_NAME,
        '(^|[^[:alnum:]_.])(adusers)([^[:alnum:]_]|$)',            '\1nam_user_admin.\2\3', 1, 0, 'i'),
        '(^|[^[:alnum:]_.])(adgroup_asis)([^[:alnum:]_]|$)',       '\1nam_user_admin.\2\3', 1, 0, 'i'),
        '(^|[^[:alnum:]_.])(gmail_users)([^[:alnum:]_]|$)',        '\1nam_user_admin.\2\3', 1, 0, 'i'),
        '(^|[^[:alnum:]_.])(group_google)([^[:alnum:]_]|$)',       '\1nam_user_admin.\2\3', 1, 0, 'i'),
        '(^|[^[:alnum:]_.])(faims_id_convert)([^[:alnum:]_]|$)',   '\1nam_user_admin.\2\3', 1, 0, 'i'),
        '(^|[^[:alnum:]_.])(e_imdb_users_simple)([^[:alnum:]_]|$)','\1nam_user_admin.\2\3', 1, 0, 'i')
WHERE IMPORT_TABLE_NAME IS NOT NULL
  AND REGEXP_LIKE(IMPORT_TABLE_NAME,
        '(^|[^[:alnum:]_.])(adusers|adgroup_asis|gmail_users|group_google|faims_id_convert|e_imdb_users_simple)([^[:alnum:]_]|$)',
        'i');

--      ※ 上記正規表現は「同一オブジェクトが1つのSQL内に複数回出現」する場合、
--        区切り文字を1文字消費する都合で2つ目以降を取りこぼす可能性がある。
--        自己結合等で同名参照が複数ある場合は、置換後に下記で残存を確認すること。
--          SELECT SYSTEM_ID, IMPORT_TABLE_NAME
--          FROM   NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
--          WHERE  REGEXP_LIKE(IMPORT_TABLE_NAME,
--                   '(^|[^[:alnum:]_.])(adusers|adgroup_asis|gmail_users|group_google|faims_id_convert|e_imdb_users_simple)([^[:alnum:]_]|$)', 'i');
--      ※ 既に明示済みの参照（nam_user_admin.gmail_users / mail_auth_detail / zoom_users、
--        nam_ope.*、imart.*@imdb 等、DBリンク参照）は対象外（修飾済みのため置換されない）。
--      ※ (B) の GRANT（000_grant_imdb_select.sql）とセットで実施すること。

COMMIT;

-- 移送・検証が完了したら旧テーブルを削除する（要確認後に実行）:
--   DROP TABLE nam_user_admin.m_system_user_info CASCADE CONSTRAINTS;
--   DROP TABLE nam_user_admin.t_organization_change;
--   DROP TABLE nam_user_admin.t_import_history;
--   DROP TABLE nam_user_admin.t_output_history;
--   DROP TABLE nam_user_admin.t_tenshutu_temp;
--   DROP TABLE nam_user_admin.t_system_users_xxx;  -- システムごと


-- ------------------------------------------------------------
-- 方法B：同一スキーマ（nam_user_admin）内でリネームのみ行う場合
-- ------------------------------------------------------------
-- スキーマ移動をせず名前だけ変更するなら以下を使用する。
-- （この場合、コード側のスキーマ名は nam_user_admin のままにする必要がある）
--
--   ALTER TABLE nam_user_admin.m_system_user_info   RENAME TO IDINV_SYSTEM_DEFINITIONS;
--   ALTER TABLE nam_user_admin.t_organization_change RENAME TO IDINV_ORGANIZATION_CHANGES;
--   ALTER TABLE nam_user_admin.t_import_history      RENAME TO IDINV_IMPORT_HISTORY;
--   ALTER TABLE nam_user_admin.t_output_history      RENAME TO IDINV_OUTPUT_HISTORY;
--   ALTER TABLE nam_user_admin.t_tenshutu_temp       RENAME TO IDINV_W_TENSHUTU_TEMP;
--   -- 動的テーブルはシステムごと:
--   -- ALTER TABLE nam_user_admin.t_system_users_sap_hr RENAME TO IDINV_W_SYSTEM_USERS_SAP_HR;
