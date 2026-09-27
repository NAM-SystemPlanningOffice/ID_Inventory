from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

@dataclass
class ImportHistory:
    batch_id: str
    system_id: str
    import_datetime: Optional[datetime] = None
    import_user: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    status: Optional[str] = None
    total_records: Optional[int] = None
    success_records: Optional[int] = None
    error_records: Optional[int] = None
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self):
        return {
            'batch_id': self.batch_id,
            'system_id': self.system_id,
            'import_datetime': self.import_datetime.isoformat() if self.import_datetime else None,
            'import_user': self.import_user,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'status': self.status,
            'total_records': self.total_records,
            'success_records': self.success_records,
            'error_records': self.error_records,
            'error_message': self.error_message,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }

@dataclass
class OutputHistory:
    output_id: Optional[int] = None
    output_type: Optional[str] = None
    output_datetime: Optional[datetime] = None
    output_user: Optional[str] = None
    target_date: Optional[date] = None
    target_month: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    status: Optional[str] = None
    total_systems: Optional[int] = None
    total_users: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self):
        return {
            'output_id': self.output_id,
            'output_type': self.output_type,
            'output_datetime': self.output_datetime.isoformat() if self.output_datetime else None,
            'output_user': self.output_user,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'target_month': self.target_month,
            'spreadsheet_url': self.spreadsheet_url,
            'status': self.status,
            'total_systems': self.total_systems,
            'total_users': self.total_users,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
