import pytest
from app.utils.file_parser import FileParser

def test_transform_data():
    raw_data = [
        {'ユーザーID': '12345', '氏名': '  テストユーザー  ', 'メールアドレス': 'TEST@EXAMPLE.COM'},
        {'ユーザーID': '67890', '氏名': '別のユーザー', 'メールアドレス': 'USER@EXAMPLE.COM'}
    ]

    mapping = {
        'columns': [
            {
                'source_column': 'ユーザーID',
                'target_column': 'USER_CD',
                'data_type': 'string',
                'required': True,
                'trim': True
            },
            {
                'source_column': '氏名',
                'target_column': 'USER_NAME',
                'data_type': 'string',
                'required': True,
                'trim': True
            },
            {
                'source_column': 'メールアドレス',
                'target_column': 'EMAIL',
                'data_type': 'string',
                'trim': True,
                'transform': 'lowercase'
            }
        ]
    }

    result = FileParser.transform_data(raw_data, mapping)

    assert len(result) == 2
    assert result[0]['USER_CD'] == '12345'
    assert result[0]['USER_NAME'] == 'テストユーザー'
    assert result[0]['EMAIL'] == 'test@example.com'
    assert result[1]['USER_CD'] == '67890'
    assert result[1]['EMAIL'] == 'user@example.com'

def test_transform_data_missing_required():
    raw_data = [
        {'ユーザーID': None, '氏名': 'テストユーザー'}
    ]

    mapping = {
        'columns': [
            {
                'source_column': 'ユーザーID',
                'target_column': 'USER_CD',
                'required': True
            }
        ]
    }

    with pytest.raises(ValueError, match='Required field missing'):
        FileParser.transform_data(raw_data, mapping)
