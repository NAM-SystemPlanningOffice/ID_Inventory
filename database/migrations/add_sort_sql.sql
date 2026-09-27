-- 出力ソート順のカラムを追加

ALTER TABLE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
ADD (
    tanaoroshi_sort_sql CLOB,
    tenshutu_sort_sql CLOB
);

COMMIT;

-- 使用例のコメント
COMMENT ON COLUMN NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS.tanaoroshi_sort_sql IS '棚卸リスト出力ソート順（例: z.SHOZOKU ASC, s.USER_CD ASC）';
COMMENT ON COLUMN NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS.tenshutu_sort_sql IS '転出者リスト出力ソート順（例: t.BEFORE_ORG ASC, s.USER_CD ASC）';
