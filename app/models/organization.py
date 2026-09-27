from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class OrganizationChange:
    change_date: date
    before_org_cd: str
    before_org_name: Optional[str]
    after_org_cd: str
    after_org_name: Optional[str]
    remarks: Optional[str] = None

    def to_dict(self):
        return {
            'change_date': self.change_date.isoformat() if self.change_date else None,
            'before_org_cd': self.before_org_cd,
            'before_org_name': self.before_org_name,
            'after_org_cd': self.after_org_cd,
            'after_org_name': self.after_org_name,
            'remarks': self.remarks
        }
