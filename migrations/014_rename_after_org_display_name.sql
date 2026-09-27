-- 転出者リスト出力カラム定義の AFTER_ORG の表示名を「転出先」→「異動後」に変更
-- 既存システムに保存済みの TENSHUTU_OUTPUT_COLUMNS_JSON 内の display_name を置換する。
-- （JSONは画面のtextarea入力がそのまま生の日本語文字列で格納されているため、文字列置換で対応）

UPDATE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
SET TENSHUTU_OUTPUT_COLUMNS_JSON =
        REPLACE(
            TENSHUTU_OUTPUT_COLUMNS_JSON,
            '"display_name": "転出先"',
            '"display_name": "異動後"'
        )
WHERE TENSHUTU_OUTPUT_COLUMNS_JSON LIKE '%"display_name": "転出先"%';

COMMIT;
