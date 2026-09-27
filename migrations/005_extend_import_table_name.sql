-- IMPORT_TABLE_NAMEの桁拡張（テーブル名またはSQLを格納）

-- 既存データを保持しながら型を変更
ALTER TABLE NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS
MODIFY IMPORT_TABLE_NAME CLOB;

-- コメント更新
COMMENT ON COLUMN NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS.IMPORT_TABLE_NAME
IS '取り込み先テーブル名 または 参照SQL
- CSV/XLSX取り込みの場合:
  デフォルト: IDINV_W_SYSTEM_USERS_システムID 形式
  カスタム: SQLを指定（取り込み後の追加処理が必要な場合）
    例: SELECT * FROM IDINV_W_SYSTEM_USERS_XXX WHERE STATUS = ''ACTIVE''
- DIRECT参照の場合:
  シンプル: SCHEMA.TABLE_NAME
  複雑: SELECT USER_CD, USER_NAME FROM SCHEMA.TABLE WHERE ...
  WITH句: WITH temp AS (...) SELECT ... FROM temp
※ SELECT または WITH で始まる場合はSQL、それ以外はテーブル名として判定';

-- import_methodのコメントを更新
COMMENT ON COLUMN NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS.IMPORT_METHOD
IS '取り込み方法
- CSV: CSVファイルから取り込み
- XLSX: Excelファイルから取り込み
- DIRECT: 既存Oracleテーブルから直接参照（IMPORT_TABLE_NAMEにテーブル名またはSQLを指定）';

-- 既存データは影響なし（VARCHAR2 → CLOBは互換性あり）
COMMIT;
