# 出力項目定義 - 利用可能なカラム

## 1. 棚卸リスト

### システムソース
システムのユーザーテーブルのカラム（取り込みマッピングで定義したカラム）

例: USER_CD, USER_NAME, DEPARTMENT_CD, EMAIL, ACCOUNT_STATUS 等

### 在籍ソース
在籍ユーザー情報（NAM_USER_ADMIN.E_IMDB_HONMU_KENMU + E_IMDB_SANKYU）

| カラム名 | 表示名 | 説明 |
|---------|--------|------|
| USER_CD | ユーザーCD | ユーザーコード |
| USER_NAME | ユーザー名 | 氏名 |
| SHOZOKU | 所属 | 所属名 |
| POST_NAME | 役職名 | 役職名（産育休の場合は「産育休」） |
| HONMU | 本務 | 本務所属 |
| KENMU | 兼務 | 兼務所属 |

## 2. 転出者リスト

### システムソース
システムのユーザーテーブルのカラム（取り込みマッピングで定義したカラム）

例: USER_CD, USER_NAME, DEPARTMENT_CD, EMAIL, ACCOUNT_STATUS 等

### 異動ソース
異動情報（NAM_IAM_ADMIN.IDINV_W_TENSHUTU_TEMP）

| カラム名 | 表示名 | 説明 |
|---------|--------|------|
| USER_CD | ユーザーCD | ユーザーコード |
| USER_NAME | ユーザー名 | 氏名 |
| IDO_DATE | 異動日 | 異動日 |
| BEFORE_ORG | 転出元 | 転出元組織 |
| AFTER_ORG | 異動後 | 異動後の所属・役職（基準日時点、imart） |

## JSON形式

### 棚卸リスト用 (tanaoroshi_output_columns_json)

```json
{
  "columns": [
    {
      "column_name": "USER_CD",
      "display_name": "ユーザーCD",
      "order": 1,
      "source": "system"
    },
    {
      "column_name": "USER_NAME",
      "display_name": "ユーザー名",
      "order": 2,
      "source": "zaiseki"
    },
    {
      "column_name": "SHOZOKU",
      "display_name": "所属",
      "order": 3,
      "source": "zaiseki"
    },
    {
      "column_name": "DEPARTMENT_CD",
      "display_name": "部署コード",
      "order": 4,
      "source": "system"
    }
  ]
}
```

### 転出者リスト用 (tenshutu_output_columns_json)

```json
{
  "columns": [
    {
      "column_name": "USER_CD",
      "display_name": "ユーザーCD",
      "order": 1,
      "source": "tenshutu"
    },
    {
      "column_name": "USER_NAME",
      "display_name": "ユーザー名",
      "order": 2,
      "source": "tenshutu"
    },
    {
      "column_name": "BEFORE_ORG",
      "display_name": "転出元",
      "order": 3,
      "source": "tenshutu"
    },
    {
      "column_name": "AFTER_ORG",
      "display_name": "異動後",
      "order": 4,
      "source": "tenshutu"
    },
    {
      "column_name": "EMAIL",
      "display_name": "メールアドレス",
      "order": 5,
      "source": "system"
    }
  ]
}
```

## フィールド説明

- **column_name**: カラム名（データベースのカラム名）
- **display_name**: 表示名（スプレッドシートのヘッダー）
- **order**: 表示順序（昇順）
- **source**: データソース
  - `system`: システムのユーザーテーブル
  - `zaiseki`: 在籍ユーザー情報（棚卸リストのみ）
  - `tenshutu`: 異動情報（転出者リストのみ）
