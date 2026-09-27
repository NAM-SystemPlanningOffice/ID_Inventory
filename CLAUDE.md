各種システムのID棚卸のシステムです

必要な機能

 - 各システムのユーザー情報の取り込み（csv,xlsx→oracle、既にOracleに格納済のシステムも過半）
 - リスト出力（Google SpreadSheetに出力）
   1. ユーザー棚卸リスト（在籍ユーザーと照合、システム毎にシート出力）
   2. 退職者（育産休）ID削除依頼書（縦）
   3. 組織転出者アクセス権限確認リスト
 - 組織変更対応（組織体制変更で組織コードが変わった場合は組織転出者アクセス権限確認リストの対象外）

画面構成

 - リスト出力指示
   1. 日別の転出・退職情報（月を選択し、転職・退職がある日だけ表示、どの日のリストを出力するか選択して３つのリストを出力）
   2. ユーザー情報取り込み日時が最も古い日時を表示（クリックして各システムの状況も参照可）
 - 各システムのユーザー情報取り込み（ファイルアップロード、マッピングに従いOracleに取り込み）
 - 各システムのユーザー情報定義画面（Oracleテーブルの情報、出力項目、取り込みが必要な場合はマッピング情報、最終取り込み日時等、退職時出力要否、出力順）
 - 組織変更入力画面（ 入力内容をOracle に格納、変更前後の組織コード、組織名の対応）

データ

　- 在籍従業員情報 nam_user_admin.e_imdb_honmu_kenmu（USER_CD,USER_NAME,SHOZOKU,HONMU,KENMU）
  - 退職者情報
 ```
  select user_cd,user_name,department_cd,department_name,post_cd,post_name, taisha_date from e_imdb_users_end
  where taisha=1 and department_main =1
  ```
  - 組織転出者情報 　nam_user_admin.e_imdb_ido
```
IDO_DATE: 異動日
USER_CD: ユーザーCD
USER_NAME: ユーザー名
IDO_TYPE: 'END' 異動で転出した組織 　'AFTER'　異動後の組織（異動日・ユーザーCDでEND、AFTERは複数レコード有）
DEPARTMENT_CD: 所属コード
POST_CD: 役職コード
DEPARTMENT_NAME: 所属名
POST_NAME: 役職名
DEPARTMENT_MAIN: 1: 本務　0: 兼務
```
  - 各システムのユーザー情報定義　nam_user_admin.m_system_user_info（新規作成） に格納
  - 各システムのユーザー管理テーブル　nam_user_admin.m_system_user_info　に情報格納
  - 組織変更の情報 nam_user_admin.t_organization_change

システム
 - python/flask
 - bootstrap は使用しない（社内ネットワークで閉じた構成）
 - Azure App Service上で稼働

セキュリティ
 - .env でこのシステムを利用できる室のコードをカンマ区切りで定義
 - nam_user_admin.e_imdb2_users　のnaisetsu に上記コードが一致するユーザーのみログイン可


 その他
 - 現在Excelに出力しているレポートのテンプレートは、docs/templates_example を参照