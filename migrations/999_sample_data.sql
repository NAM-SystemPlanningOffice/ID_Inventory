-- サンプルシステム定義データ

-- システム1: SAP人事システム
INSERT INTO NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS (
    SYSTEM_ID, SYSTEM_NAME, DESCRIPTION,
    IMPORT_REQUIRED, IMPORT_METHOD,
    IMPORT_MAPPING_JSON,
    OUTPUT_REQUIRED, OUTPUT_ORDER, OUTPUT_SHEET_NAME,
    OUTPUT_COLUMNS_JSON,
    TANAOROSHI_OUTPUT_MODE,
    TAISHOKU_OUTPUT_REQUIRED, TAISHOKU_OUTPUT_ORDER,
    TAISHOKU_DISPLAY_SQL,
    IS_ACTIVE, CREATED_BY, UPDATED_BY
) VALUES (
    'sap_hr',
    'SAP人事システム',
    'SAP HRのユーザー情報',
    1,
    'CSV',
    '{
        "file_encoding": "shift-jis",
        "has_header": true,
        "skip_rows": 0,
        "columns": [
            {"source_column": "ユーザーID", "target_column": "USER_CD", "data_type": "string", "required": true, "trim": true},
            {"source_column": "氏名", "target_column": "USER_NAME", "data_type": "string", "required": true, "trim": true},
            {"source_column": "所属コード", "target_column": "DEPARTMENT_CD", "data_type": "string", "trim": true},
            {"source_column": "所属名", "target_column": "DEPARTMENT_NAME", "data_type": "string", "trim": true},
            {"source_column": "メールアドレス", "target_column": "EMAIL", "data_type": "string", "trim": true, "transform": "lowercase"}
        ]
    }',
    1,
    1,
    'SAP人事',
    '{
        "columns": [
            {"column_name": "USER_CD", "display_name": "ユーザーID", "order": 1, "width": 15, "format": "text", "required": true},
            {"column_name": "USER_NAME", "display_name": "氏名", "order": 2, "width": 20, "format": "text", "required": true},
            {"column_name": "DEPARTMENT_CD", "display_name": "所属コード", "order": 3, "width": 12, "format": "text"},
            {"column_name": "DEPARTMENT_NAME", "display_name": "所属名", "order": 4, "width": 30, "format": "text"},
            {"column_name": "EMAIL", "display_name": "メールアドレス", "order": 5, "width": 30, "format": "text"}
        ]
    }',
    'MISMATCH_ONLY',
    1,
    1,
    'S.USER_CD',
    1,
    'SYSTEM',
    'SYSTEM'
);

-- システム2: Active Directory
INSERT INTO NAM_IAM_ADMIN.IDINV_SYSTEM_DEFINITIONS (
    SYSTEM_ID, SYSTEM_NAME, DESCRIPTION,
    IMPORT_REQUIRED, IMPORT_METHOD,
    IMPORT_MAPPING_JSON,
    OUTPUT_REQUIRED, OUTPUT_ORDER, OUTPUT_SHEET_NAME,
    OUTPUT_COLUMNS_JSON,
    TANAOROSHI_OUTPUT_MODE,
    TAISHOKU_OUTPUT_REQUIRED, TAISHOKU_OUTPUT_ORDER,
    TAISHOKU_DISPLAY_SQL,
    IS_ACTIVE, CREATED_BY, UPDATED_BY
) VALUES (
    'active_directory',
    'Active Directory',
    'ADのユーザーアカウント情報',
    1,
    'CSV',
    '{
        "file_encoding": "utf-8",
        "has_header": true,
        "skip_rows": 0,
        "columns": [
            {"source_column": "samAccountName", "target_column": "USER_CD", "data_type": "string", "required": true, "trim": true},
            {"source_column": "displayName", "target_column": "USER_NAME", "data_type": "string", "required": true, "trim": true},
            {"source_column": "department", "target_column": "DEPARTMENT_NAME", "data_type": "string", "trim": true},
            {"source_column": "mail", "target_column": "EMAIL", "data_type": "string", "trim": true, "transform": "lowercase"},
            {"source_column": "enabled", "target_column": "ACCOUNT_STATUS", "data_type": "string", "trim": true}
        ]
    }',
    1,
    2,
    'Active Directory',
    '{
        "columns": [
            {"column_name": "USER_CD", "display_name": "ユーザーID", "order": 1, "width": 15, "format": "text", "required": true},
            {"column_name": "USER_NAME", "display_name": "氏名", "order": 2, "width": 20, "format": "text", "required": true},
            {"column_name": "DEPARTMENT_NAME", "display_name": "所属名", "order": 3, "width": 30, "format": "text"},
            {"column_name": "EMAIL", "display_name": "メールアドレス", "order": 4, "width": 30, "format": "text"},
            {"column_name": "ACCOUNT_STATUS", "display_name": "状態", "order": 5, "width": 15, "format": "text"}
        ]
    }',
    'CUSTOM',
    1,
    2,
    'CASE WHEN S.ACCOUNT_STATUS = ''True'' THEN ''有効'' ELSE ''無効'' END',
    1,
    'SYSTEM',
    'SYSTEM'
);

-- システム用ユーザーテーブルの作成（サンプル）
CREATE TABLE NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_SAP_HR (
    IMPORT_BATCH_ID VARCHAR2(50),
    USER_CD VARCHAR2(50) NOT NULL,
    USER_NAME VARCHAR2(200),
    DEPARTMENT_CD VARCHAR2(50),
    DEPARTMENT_NAME VARCHAR2(200),
    EMAIL VARCHAR2(200)
);

CREATE TABLE NAM_IAM_ADMIN.IDINV_W_SYSTEM_USERS_ACTIVE_DIRECTORY (
    IMPORT_BATCH_ID VARCHAR2(50),
    USER_CD VARCHAR2(50) NOT NULL,
    USER_NAME VARCHAR2(200),
    DEPARTMENT_NAME VARCHAR2(200),
    EMAIL VARCHAR2(200),
    ACCOUNT_STATUS VARCHAR2(50)
);

COMMIT;
