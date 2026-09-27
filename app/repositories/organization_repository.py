from app.repositories.base_repository import BaseRepository
from app.models.organization import OrganizationChange
from typing import List, Optional
from datetime import date

class OrganizationRepository(BaseRepository):
    def find_all(self) -> List[OrganizationChange]:
        sql = """
            SELECT CHANGE_DATE, BEFORE_ORG_CD, BEFORE_ORG_NAME,
                   AFTER_ORG_CD, AFTER_ORG_NAME, REMARKS
            FROM NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES
            ORDER BY CHANGE_DATE DESC
        """
        rows = self.execute_query_for_model(sql)
        return [OrganizationChange(**row) for row in rows]

    def find_by_date(self, change_date: date) -> List[OrganizationChange]:
        sql = """
            SELECT CHANGE_DATE, BEFORE_ORG_CD, BEFORE_ORG_NAME,
                   AFTER_ORG_CD, AFTER_ORG_NAME, REMARKS
            FROM NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES
            WHERE CHANGE_DATE = :CHANGE_DATE
        """
        rows = self.execute_query_for_model(sql, {'CHANGE_DATE': change_date})
        return [OrganizationChange(**row) for row in rows]

    def insert(self, org_change: OrganizationChange) -> int:
        sql = """
            INSERT INTO NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES (
                CHANGE_DATE, BEFORE_ORG_CD, BEFORE_ORG_NAME,
                AFTER_ORG_CD, AFTER_ORG_NAME, REMARKS
            ) VALUES (
                :CHANGE_DATE, :BEFORE_ORG_CD, :BEFORE_ORG_NAME,
                :AFTER_ORG_CD, :AFTER_ORG_NAME, :REMARKS
            )
        """
        params = {
            'CHANGE_DATE': org_change.change_date,
            'BEFORE_ORG_CD': org_change.before_org_cd,
            'BEFORE_ORG_NAME': org_change.before_org_name,
            'AFTER_ORG_CD': org_change.after_org_cd,
            'AFTER_ORG_NAME': org_change.after_org_name,
            'REMARKS': org_change.remarks
        }
        return self.execute_insert(sql, params)

    def delete(self, change_date: date, before_org_cd: str, after_org_cd: str) -> int:
        sql = """
            DELETE FROM NAM_IAM_ADMIN.IDINV_ORGANIZATION_CHANGES
            WHERE CHANGE_DATE = :CHANGE_DATE
              AND BEFORE_ORG_CD = :BEFORE_ORG_CD
              AND AFTER_ORG_CD = :AFTER_ORG_CD
        """
        return self.execute_delete(sql, {
            'CHANGE_DATE': change_date,
            'BEFORE_ORG_CD': before_org_cd,
            'AFTER_ORG_CD': after_org_cd
        })
