-- output_columns_jsonを削除し、tanaoroshi_output_columns_jsonとtenshutu_output_columns_jsonを追加

-- 1. 新しいカラムを追加
ALTER TABLE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
ADD (
    tanaoroshi_output_columns_json CLOB,
    tenshutu_output_columns_json CLOB
);

-- 2. 既存のoutput_columns_jsonのデータをtanaoroshi_output_columns_jsonとtenshutu_output_columns_jsonにコピー
UPDATE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
SET tanaoroshi_output_columns_json = output_columns_json,
    tenshutu_output_columns_json = output_columns_json
WHERE output_columns_json IS NOT NULL;

COMMIT;

-- 3. 古いカラムを削除
ALTER TABLE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
DROP COLUMN output_columns_json;

COMMIT;
