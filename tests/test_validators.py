import pytest
from app.utils.validators import validate_system_id, validate_file_extension, validate_import_data

def test_validate_system_id_valid():
    assert validate_system_id('sap_hr') == True
    assert validate_system_id('active_directory') == True
    assert validate_system_id('system123') == True

def test_validate_system_id_invalid():
    with pytest.raises(ValueError):
        validate_system_id('')

    with pytest.raises(ValueError):
        validate_system_id('SAP_HR')

    with pytest.raises(ValueError):
        validate_system_id('system-name')

    with pytest.raises(ValueError):
        validate_system_id('a' * 51)

def test_validate_file_extension():
    assert validate_file_extension('test.csv', {'csv', 'xlsx'}) == True
    assert validate_file_extension('test.xlsx', {'csv', 'xlsx'}) == True
    assert validate_file_extension('test.CSV', {'csv', 'xlsx'}) == True
    assert validate_file_extension('test.txt', {'csv', 'xlsx'}) == False
    assert validate_file_extension('test', {'csv', 'xlsx'}) == False

def test_validate_import_data():
    mapping = {
        'columns': [
            {'target_column': 'USER_CD', 'required': True},
            {'target_column': 'USER_NAME', 'required': True}
        ]
    }

    data = [
        {'USER_CD': '12345', 'USER_NAME': 'Test User'},
        {'USER_CD': '67890', 'USER_NAME': 'Another User'}
    ]

    assert validate_import_data(data, mapping) == True

def test_validate_import_data_no_user_cd():
    mapping = {
        'columns': [
            {'target_column': 'USER_NAME', 'required': True}
        ]
    }

    data = [
        {'USER_NAME': 'Test User'}
    ]

    with pytest.raises(ValueError, match='USER_CD が存在しません'):
        validate_import_data(data, mapping)

def test_validate_import_data_null_user_cd():
    mapping = {
        'columns': [
            {'target_column': 'USER_CD', 'required': True}
        ]
    }

    data = [
        {'USER_CD': None}
    ]

    with pytest.raises(ValueError, match='USER_CD が NULL です'):
        validate_import_data(data, mapping)
