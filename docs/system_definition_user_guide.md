# システム定義 登録・編集ガイド（利用者向け）

このドキュメントは、**システム定義画面**で各システムのID棚卸設定を登録・編集する担当者向けの手引きです。
「どの順番で設定すればよいか」「設定を修正したときの注意点」を中心に、各リストの元になるSQL（在籍・異動・退社データの取得ロジック）も理解のために掲載します。

---

## 0. 全体像

ID棚卸システムは、各システムのユーザー情報を Oracle に取り込み（または直接参照し）、以下の3つのリストを Google スプレッドシートに出力します。

| リスト | 目的 | 照合するマスタ |
|--------|------|----------------|
| ① ユーザー棚卸リスト | 在籍ユーザーとの照合（システム毎にシート出力） | 在籍マスタ（本務・兼務・産育休） |
| ② 組織転出者アクセス権限確認リスト | 組織を転出したユーザーの権限確認 | 異動マスタ |
| ③ 退職者（産育休）ID削除依頼書 | 退職者のID削除依頼（横持ち一覧） | 退職者マスタ |

システム定義では、この3つのリストに何を・どう出力するかを、システムごとに設定します。

---

## 1. 設定の手順（重要）

システム定義は **「取り込み設定」→「保存」→「出力設定」→「保存」** の順で行ってください。
理由は、出力設定のカラム選択肢が「取り込み設定で定義したカラム（取り込み先テーブル／参照SQLの出力カラム）」から作られるためです。取り込み設定を保存する前は、出力設定で正しいカラムを選べません。

### 手順フロー

```
┌─────────────────────────────────────────────┐
│ ① 基本情報を入力（システムID・システム名 など）              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ ② 「取り込み設定」を入力                                   │
│    ・取り込み方法（CSV / XLSX / Oracle直接参照）             │
│    ・マッピング定義（CSV/XLSX）または 参照元SQL（DIRECT）     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ ★ 一旦「保存」する                                        │
│    → 取り込み先テーブルが作成され、出力設定でカラムを         │
│      選べるようになる                                      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ ③ 編集画面を開き直して「出力設定」を入力                    │
│    ・棚卸リスト / 転出者リスト / 退職者リスト の出力項目       │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ ★ もう一度「保存」する                                    │
└─────────────────────────────────────────────┘
```

> **なぜ2回保存するのか**
> 出力項目の選択肢（カラム一覧）は、取り込み設定を保存した時点のテーブル／参照SQLの列構成から生成されます。取り込み設定を保存せずに出力設定を行うと、変更後の列が選択肢に反映されません。**必ず取り込み設定を保存してから、編集画面を開き直して出力設定を行ってください。**

---

## 2. 取り込み設定を修正した場合の注意（必読）

取り込み設定（**参照元テーブル/SQL**・**マッピング定義**）を後から変更した場合は、次を必ず守ってください。

1. **修正後は必ず一旦「保存」する。**
   保存しないと、変更後のカラム構成が出力設定の選択肢に反映されません。保存後に編集画面を開き直してください。

2. **取り込み設定から削除した項目（カラム）は、「出力設定」からも削除する。**
   取り込み設定から消したカラムが以下に残っていると、保存時のエラーチェックでエラーになる、またはリスト出力時に空欄になります。次の箇所を確認し、削除したカラムを取り除いてください。
   - 棚卸リスト出力カラム定義
   - 転出者リスト出力カラム定義
   - 棚卸フィルタSQL（`s.` で参照しているカラム）
   - 転出者リストフィルタSQL（`s.` で参照しているカラム）
   - 棚卸／転出者リストの出力ソート順（`s.` で参照しているカラム）
   - 退職者リスト表示SQL・無効化済み判定SQL（`s.` / `S.` で参照しているカラム）

3. **保存時にエラーチェックが走る。**
   修正後の内容（参照元SQL・出力カラム・フィルタSQL・ソート順）は、保存時に Oracle 上で実際に検証されます。存在しないカラム名や構文誤りがあると保存できません。エラーメッセージに従って修正してください。

> **補足（CSV/XLSXの場合）**
> マッピング定義を変更すると、取り込み先テーブル `IDINV_W_SYSTEM_USERS_（システムID）` が再作成されます。**既存の取り込み済みデータは削除される**ため、マッピング変更後は再度データを取り込んでください。

---

## 3. 取り込み設定の入力項目

### 取り込み方法

| 方法 | 説明 | 必要な設定 |
|------|------|-----------|
| **CSV** | CSVファイルをアップロードして取り込む | マッピング定義＋（必要であれば）参照元テーブル/SQL|
| **XLSX** | Excelファイルをアップロードして取り込む | マッピング定義（＋シート名）＋（必要であれば）参照元テーブル/SQL| |
| **Oracle直接参照（DIRECT）** | 既にOracleにあるテーブル/ビューを参照する | 参照元テーブル/SQL |

### マッピング定義（CSV / XLSX）

CSV/XLSXの列を Oracle のカラムに対応づけます。フォーム入力またはJSON直接入力で設定します。

- **元カラム名 / 列番号**: ヘッダー行ありなら元カラム名、なしなら列番号（0始まり）
- **DBカラム名**: 取り込み先の Oracle カラム名（大文字）
- **USER_CD は必須**: 在籍・退職・異動マスタとの照合キーになります

### 参照元テーブル/SQL（Oracle直接参照）

- テーブル名のみ（例: `SCHEMA.USERS`）の場合は `SELECT *` が自動付与されます
- `SELECT` または `WITH` で始まる場合はSQL文としてそのまま使われます
- **出力カラムに `USER_CD` が必須**です。別名の列しかない場合は `AS USER_CD` を付けてください

---

## 4. 各リストの元データを取得するSQL

出力設定で選べるカラムや、フィルタ・ソートで使えるエイリアスを理解するために、各リストが内部で使うSQLを掲載します。
実際にはシステムの取り込みテーブル／参照SQLとこれらのマスタを結合してリストを生成します。

### 4-1. 在籍ユーザー（棚卸リストの照合元）

棚卸リストは、システムのユーザーと**在籍マスタ**を `USER_CD` で突き合わせます。在籍マスタは「本務・兼務マスタ」と「産育休マスタ」の和集合です。

```sql
-- 在籍ユーザー（通常 + 産育休）
SELECT USER_CD, USER_NAME, SHOZOKU, POST_NAME, HONMU, KENMU
FROM NAM_USER_ADMIN.E_IMDB_HONMU_KENMU
UNION
SELECT USER_CD, USER_NAME, SHOZOKU, '産育休' AS POST_NAME,
       NVL(SHOZOKU_NAME, BUMON_NAME) AS HONMU, NULL AS KENMU
FROM NAM_USER_ADMIN.E_IMDB_SANKYU
WHERE DEPARTMENT_MAIN = '1'
```

この在籍情報は、棚卸リストのカラムでは **エイリアス `z`**（在籍側）で参照できます。
利用できる在籍カラム: `z.USER_CD` / `z.USER_NAME` / `z.SHOZOKU` / `z.POST_NAME` / `z.HONMU` / `z.KENMU`

**棚卸リストの実際の照合クエリ（イメージ）**:

```sql
SELECT s.*,
       CASE WHEN z.USER_CD IS NOT NULL THEN 1 ELSE 0 END AS IS_ZAISEKI_MATCH,
       z.USER_NAME AS ZAISEKI_USER_NAME,
       z.SHOZOKU  AS ZAISEKI_SHOZOKU,
       z.POST_NAME AS ZAISEKI_POST_NAME,
       z.HONMU    AS ZAISEKI_HONMU,
       z.KENMU    AS ZAISEKI_KENMU
FROM ( 取り込みテーブル または 参照SQL ) s
LEFT JOIN ( 上記の在籍SQL ) z ON s.USER_CD = z.USER_CD
-- 出力モードに応じたフィルタ:
--   ALL          : フィルタなし
--   MISMATCH_ONLY: WHERE z.USER_CD IS NULL      （在籍にいない=棚卸対象）
--   CUSTOM       : WHERE ( 棚卸フィルタSQL )
ORDER BY ( 棚卸ソート順SQL )
```

> **棚卸出力モード**
> - `ALL`: 全ユーザー出力
> - `MISMATCH_ONLY`（標準）: 在籍マスタに存在しないユーザーのみ出力
> - `CUSTOM`: 棚卸フィルタSQL の条件で出力

### 4-2. 組織転出者（転出者リスト）

転出者リストは、**異動マスタ**から指定した異動日のレコードを取得し、「組織コード変更のみ」「同一組織内の昇格」などを除外してから、転出元・転出先組織を組み立てます。

**異動マスタ取得**:

```sql
SELECT IDO_DATE, USER_CD, USER_NAME, IDO_TYPE,
       DEPARTMENT_CD, POST_CD, DEPARTMENT_NAME, POST_NAME, DEPARTMENT_MAIN
FROM NAM_USER_ADMIN.E_IMDB_IDO
WHERE TRUNC(IDO_DATE) = TO_DATE(:TARGET_DATE, 'YYYY-MM-DD')
ORDER BY USER_CD, IDO_TYPE
```

- `IDO_TYPE = 'END'`: 転出した組織、`IDO_TYPE = 'AFTER'`: 転出後の組織（1ユーザーに複数レコードあり）
- `DEPARTMENT_MAIN = 1`: 本務 / `0`: 兼務

**除外・整形ロジック（システム内部で処理）**:
- 組織変更マスタ `IDINV_ORGANIZATION_CHANGES` に登録された「組織コード変更のみ」の異動は対象外
- 同一組織内で役職が同じ、または昇格（`POST_CD` が小さくなる）の場合は対象外
- 残った転出元／転出先を「(本務/兼務) 組織名 役職名」形式で改行連結

整形結果は一時テーブル `IDINV_W_TENSHUTU_TEMP`（列: `USER_CD, USER_NAME, IDO_DATE, BEFORE_ORG, AFTER_ORG`）に保存され、各システムと結合されます。

**転出者リストの実際の結合クエリ（イメージ）**:

```sql
SELECT t.USER_CD, t.USER_NAME, t.BEFORE_ORG, t.AFTER_ORG,
       NVL(TO_CHAR(s0.（システムカラム）), '－') AS ...
FROM NAM_IAM_ADMIN.IDINV_W_TENSHUTU_TEMP t
LEFT JOIN ( システム0の取り込みテーブル/参照SQL ) s0 ON t.USER_CD = s0.USER_CD
-- 他システムも同様に LEFT JOIN
WHERE TRUNC(t.IDO_DATE) = TO_DATE(:TARGET_DATE, 'YYYY-MM-DD')
  AND ( 転出者フィルタSQL )        -- 任意
ORDER BY ( 転出者ソート順SQL )      -- 既定は t.USER_CD
```

転出者リストのフィルタ・ソートで使えるエイリアス:
- システム側: `s.`（システムの取り込みカラム）
- 転出者情報側: `t.USER_CD` / `t.USER_NAME` / `t.IDO_DATE` / `t.BEFORE_ORG` / `t.AFTER_ORG`

> **組織コード変更のみの登録**
> 組織名は変わらずコードだけ変わった場合は、組織変更画面から `IDINV_ORGANIZATION_CHANGES` に登録しておくと、その異動は転出者リストの対象外になります。

### 4-3. 退職者（退職者ID削除依頼書）

退職者リストは、**退職者マスタ**から指定日の退職者を取得し、全システムを横に並べた一覧（横持ち）にします。

**退職者マスタ取得**:

```sql
SELECT USER_CD, USER_NAME, DEPARTMENT_CD, DEPARTMENT_NAME,
       POST_CD, POST_NAME, TAISHA_DATE
FROM NAM_USER_ADMIN.E_IMDB_USERS_END
WHERE TAISHA = 1
  AND DEPARTMENT_MAIN = 1
  AND TRUNC(TAISHA_DATE) = TO_DATE(:TARGET_DATE, 'YYYY-MM-DD')
```

- `TAISHA = 1`: 退職 / `DEPARTMENT_MAIN = 1`: 本務のみ

**退職者リストの実際の結合クエリ（イメージ）**:

```sql
SELECT
    t.USER_CD  AS USER_CD,
    t.USER_NAME AS USER_NAME,
    t.DEPARTMENT_NAME AS DEPARTMENT_NAME,
    -- 各システムごとに「表示SQL」と「無効化済み判定SQL」を展開
    NVL(TO_CHAR( 表示SQL(s0) ), '') AS SYS_（システムID）_DISPLAY_VALUE,
    CASE WHEN 無効化済み判定式(s0) THEN '－' ELSE NULL END AS SYS_（システムID）_DISABLED_VALUE
    -- 他システムも同様
FROM NAM_USER_ADMIN.E_IMDB_USERS_END t
LEFT JOIN ( システム0の取り込みテーブル/参照SQL ) s0 ON t.USER_CD = s0.USER_CD
-- 他システムも LEFT JOIN
WHERE TRUNC(t.TAISHA_DATE) = TO_DATE(:TARGET_DATE, 'YYYY-MM-DD')
  AND t.TAISHA = 1
  AND t.DEPARTMENT_MAIN = 1
ORDER BY t.USER_CD
```

退職者リストの設定項目:
- **退職者リスト表示SQL** (`taishoku_display_sql`): 各システム列に表示する値。エイリアスは `S.`（=そのシステム）を使用。
  - 例: `S.ACCOUNT_STATUS`
  - 例: `CASE WHEN S.SUSPENDED = 'True' THEN 'suspended' ELSE S.ACCOUNT_STATUS END`
  - 未設定時は `S.USER_CD` を表示
- **無効化済み判定SQL** (`taishoku_disabled_expression`): 無効化済みなら `－` を表示する条件式。エイリアスは `S.`。
  - 例: `S.ACCOUNT_STATUS = 'Disabled'` / `S.STATUS IN ('Disabled','Suspended')` / `S.USER_CD IS NULL`
  - システムが自動的に `CASE WHEN [条件式] THEN '－' ELSE NULL END` に展開します

---

## 5. 出力設定の入力項目

取り込み設定を保存した後、編集画面を開き直して設定します。

### 棚卸リスト
- **出力要**（チェック）
- **棚卸出力モード**: `ALL` / `MISMATCH_ONLY` / `CUSTOM`
- **棚卸リスト出力カラム定義**: ソース（`system`=システム / `zaiseki`=在籍）・カラム名・表示名・順序
- **棚卸フィルタSQL**（CUSTOM時）: `s.`（システム）・`z.`（在籍）で参照
- **棚卸リスト出力ソート順**: 例 `z.SHOZOKU ASC, s.USER_CD ASC`

### 転出者リスト
- **転出者リスト出力カラム定義**: ソース（`system` / `tenshutu`=転出者情報）・カラム名・表示名・順序
- **転出者リストフィルタSQL**: `s.`（システム）・`t.`（転出者情報）で参照
- **転出者リスト出力ソート順**: 例 `t.BEFORE_ORG ASC, s.USER_CD ASC`

### 退職者リスト
- **退職時出力要**（チェック）／**退職時出力順**
- **退職者リスト表示SQL** / **無効化済み判定SQL**（前章 4-3 参照。エイリアスは `S.`）

---

## 6. よくある質問

**Q. 出力設定でカラムが選択肢に出てこない**
A. 取り込み設定を保存していない、または保存後に編集画面を開き直していない可能性があります。取り込み設定を保存してから編集画面を開き直してください。

**Q. 保存時に「カラムが存在しません」エラーになる**
A. 取り込み設定から削除したカラムが、出力カラム定義・フィルタSQL・ソート順・退職者リストのSQLに残っています。該当箇所から削除してください（第2章参照）。

**Q. マッピングを変えたら取り込み済みデータが消えた**
A. CSV/XLSXでマッピングを変更すると取り込み先テーブルが再作成されます（仕様）。変更後は再度データを取り込んでください。

**Q. 組織コード変更だけの異動を転出者リストから外したい**
A. 組織変更画面から `IDINV_ORGANIZATION_CHANGES` に変更前後の組織コードを登録してください。
</content>
</invoke>
