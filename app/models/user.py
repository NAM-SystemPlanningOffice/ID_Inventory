from dataclasses import dataclass
from typing import Optional

@dataclass
class ZaisekiUser:
    user_cd: str
    user_name: str
    shozoku: Optional[str] = None
    honmu: Optional[str] = None
    kenmu: Optional[str] = None

    def to_dict(self):
        return {
            'user_cd': self.user_cd,
            'user_name': self.user_name,
            'shozoku': self.shozoku,
            'honmu': self.honmu,
            'kenmu': self.kenmu
        }

@dataclass
class TaishokuUser:
    user_cd: str
    user_name: str
    department_cd: Optional[str] = None
    department_name: Optional[str] = None
    post_cd: Optional[str] = None
    post_name: Optional[str] = None
    taisha_date: Optional[str] = None

    def to_dict(self):
        return {
            'user_cd': self.user_cd,
            'user_name': self.user_name,
            'department_cd': self.department_cd,
            'department_name': self.department_name,
            'post_cd': self.post_cd,
            'post_name': self.post_name,
            'taisha_date': self.taisha_date
        }

@dataclass
class IdoUser:
    ido_date: str
    user_cd: str
    user_name: str
    ido_type: str
    department_cd: Optional[str] = None
    post_cd: Optional[str] = None
    department_name: Optional[str] = None
    post_name: Optional[str] = None
    department_main: Optional[int] = None

    def to_dict(self):
        return {
            'ido_date': self.ido_date,
            'user_cd': self.user_cd,
            'user_name': self.user_name,
            'ido_type': self.ido_type,
            'department_cd': self.department_cd,
            'post_cd': self.post_cd,
            'department_name': self.department_name,
            'post_name': self.post_name,
            'department_main': self.department_main
        }
