from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json

@dataclass
class SystemUserInfo:
    system_id: str
    system_name: str
    description: Optional[str] = None
    import_method: Optional[str] = None
    import_table_name: Optional[str] = None
    import_mapping_json: Optional[str] = None
    last_import_datetime: Optional[datetime] = None
    last_import_user: Optional[str] = None
    last_import_record_count: Optional[int] = None
    output_required: int = 1
    output_order: Optional[int] = None
    output_sheet_name: Optional[str] = None
    tanaoroshi_output_columns_json: Optional[str] = None
    tanaoroshi_output_mode: str = 'MISMATCH_ONLY'
    tanaoroshi_filter_sql: Optional[str] = None
    tanaoroshi_sort_sql: Optional[str] = None
    tenshutu_output_columns_json: Optional[str] = None
    tenshutu_filter_sql: Optional[str] = None
    tenshutu_sort_sql: Optional[str] = None
    taishoku_output_required: int = 1
    taishoku_output_order: Optional[int] = None
    taishoku_display_sql: Optional[str] = None
    taishoku_disabled_expression: Optional[str] = None
    check_frequency: str = 'MONTHLY'
    check_responsible: Optional[str] = None
    output_scope: Optional[str] = None
    check_points: Optional[str] = None
    check_remarks: Optional[str] = None
    is_active: int = 1
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    @property
    def import_mapping(self):
        if self.import_mapping_json:
            return json.loads(self.import_mapping_json)
        return None

    @property
    def tanaoroshi_output_columns(self):
        if self.tanaoroshi_output_columns_json:
            return json.loads(self.tanaoroshi_output_columns_json)
        return None

    @property
    def tenshutu_output_columns(self):
        if self.tenshutu_output_columns_json:
            return json.loads(self.tenshutu_output_columns_json)
        return None

    def to_dict(self):
        return {
            'system_id': self.system_id,
            'system_name': self.system_name,
            'description': self.description,
            'import_method': self.import_method,
            'import_table_name': self.import_table_name,
            'import_mapping_json': self.import_mapping_json,
            'last_import_datetime': self.last_import_datetime.isoformat() if self.last_import_datetime else None,
            'last_import_user': self.last_import_user,
            'last_import_record_count': self.last_import_record_count,
            'output_required': self.output_required,
            'output_order': self.output_order,
            'output_sheet_name': self.output_sheet_name,
            'tanaoroshi_output_columns_json': self.tanaoroshi_output_columns_json,
            'tanaoroshi_output_mode': self.tanaoroshi_output_mode,
            'tanaoroshi_filter_sql': self.tanaoroshi_filter_sql,
            'tanaoroshi_sort_sql': self.tanaoroshi_sort_sql,
            'tenshutu_output_columns_json': self.tenshutu_output_columns_json,
            'tenshutu_filter_sql': self.tenshutu_filter_sql,
            'tenshutu_sort_sql': self.tenshutu_sort_sql,
            'taishoku_output_required': self.taishoku_output_required,
            'taishoku_output_order': self.taishoku_output_order,
            'taishoku_display_sql': self.taishoku_display_sql,
            'taishoku_disabled_expression': self.taishoku_disabled_expression,
            'check_frequency': self.check_frequency,
            'check_responsible': self.check_responsible,
            'output_scope': self.output_scope,
            'check_points': self.check_points,
            'check_remarks': self.check_remarks,
            'is_active': self.is_active,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by
        }
