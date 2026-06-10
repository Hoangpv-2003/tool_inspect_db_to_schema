import pytest
from unittest.mock import MagicMock
from db_schema_crawler.crawler.field_crawler import FieldCrawler
from tests.fixtures.mock_mysql_data import mock_db_config

def test_crawl_fields(mock_db_config):
    mock_conn = MagicMock()
    
    # Mock _get_columns query results
    columns_data = [
        {
            "COLUMN_NAME": "id",
            "DATA_TYPE": "bigint",
            "CHARACTER_MAXIMUM_LENGTH": None,
            "NUMERIC_PRECISION": 20,
            "NUMERIC_SCALE": 0,
            "DATETIME_PRECISION": None,
            "IS_NULLABLE": "NO",
            "COLUMN_KEY": "PRI",
            "COLUMN_DEFAULT": None,
            "COLUMN_COMMENT": "Primary key",
            "ORDINAL_POSITION": 1
        },
        {
            "COLUMN_NAME": "name",
            "DATA_TYPE": "varchar",
            "CHARACTER_MAXIMUM_LENGTH": 50,
            "NUMERIC_PRECISION": None,
            "NUMERIC_SCALE": None,
            "DATETIME_PRECISION": None,
            "IS_NULLABLE": "YES",
            "COLUMN_KEY": "",
            "COLUMN_DEFAULT": None,
            "COLUMN_COMMENT": "User's full name",
            "ORDINAL_POSITION": 2
        },
        {
            "COLUMN_NAME": "balance",
            "DATA_TYPE": "decimal",
            "CHARACTER_MAXIMUM_LENGTH": None,
            "NUMERIC_PRECISION": 10,
            "NUMERIC_SCALE": 2,
            "DATETIME_PRECISION": None,
            "IS_NULLABLE": "NO",
            "COLUMN_KEY": "",
            "COLUMN_DEFAULT": "0.00",
            "COLUMN_COMMENT": "Account balance",
            "ORDINAL_POSITION": 3
        },
        {
            "COLUMN_NAME": "created_at",
            "DATA_TYPE": "datetime",
            "CHARACTER_MAXIMUM_LENGTH": None,
            "NUMERIC_PRECISION": None,
            "NUMERIC_SCALE": None,
            "DATETIME_PRECISION": 0,
            "IS_NULLABLE": "NO",
            "COLUMN_KEY": "",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP",
            "COLUMN_COMMENT": "",
            "ORDINAL_POSITION": 4
        },
        {
            "COLUMN_NAME": "group_id",
            "DATA_TYPE": "int",
            "CHARACTER_MAXIMUM_LENGTH": None,
            "NUMERIC_PRECISION": 10,
            "NUMERIC_SCALE": 0,
            "DATETIME_PRECISION": None,
            "IS_NULLABLE": "NO",
            "COLUMN_KEY": "MUL",
            "COLUMN_DEFAULT": None,
            "COLUMN_COMMENT": "Foreign key to groups",
            "ORDINAL_POSITION": 5
        }
    ]

    # Mock foreign key map query
    fk_data = [
        {
            "COLUMN_NAME": "group_id",
            "REFERENCED_TABLE_NAME": "groups",
            "REFERENCED_COLUMN_NAME": "id"
        }
    ]

    def side_effect(sql, params=()):
        sql_upper = sql.upper()
        if "INFORMATION_SCHEMA.COLUMNS" in sql_upper:
            return columns_data
        elif "KEY_COLUMN_USAGE" in sql_upper:
            return fk_data
        return []

    mock_conn.execute_query.side_effect = side_effect

    crawler = FieldCrawler(mock_conn, mock_db_config)
    res = crawler.crawl_fields_for_table("users")
    
    assert len(res) == 5
    
    # 1. ID column (bigint, PK)
    assert res[0].ten_truong_ky_thuat == "id"
    assert res[0].kieu_du_lieu == "bigint"
    assert res[0].do_dai_dinh_dang == "20 chữ số"
    assert res[0].bat_buoc == "Có"
    assert res[0].khoa == "PK"
    assert res[0].ghi_chu == ""

    # 2. Name column (varchar, nullable)
    assert res[1].ten_truong_ky_thuat == "name"
    assert res[1].kieu_du_lieu == "varchar"
    assert res[1].do_dai_dinh_dang == "50 ký tự"
    assert res[1].bat_buoc == "Không"
    assert res[1].khoa == ""
    assert res[1].ghi_chu == ""

    # 3. Balance column (decimal)
    assert res[2].ten_truong_ky_thuat == "balance"
    assert res[2].kieu_du_lieu == "decimal"
    assert res[2].do_dai_dinh_dang == "10,2"
    assert res[2].bat_buoc == "Có"
    assert res[2].khoa == ""

    # 4. Created_at column (datetime)
    assert res[3].ten_truong_ky_thuat == "created_at"
    assert res[3].kieu_du_lieu == "datetime"
    assert res[3].do_dai_dinh_dang == "YYYY-MM-DD HH:MM:SS"
    assert res[3].bat_buoc == "Có"
    assert res[3].khoa == ""

    # 5. Group_id column (int, FK)
    assert res[4].ten_truong_ky_thuat == "group_id"
    assert res[4].kieu_du_lieu == "int"
    assert res[4].do_dai_dinh_dang == "10 chữ số"
    assert res[4].bat_buoc == "Có"
    assert res[4].khoa == "FK"

def test_pk_and_fk_combined(mock_db_config):
    mock_conn = MagicMock()
    # Cột vừa PK vừa FK
    columns_data = [{
        "COLUMN_NAME": "id",
        "DATA_TYPE": "int",
        "CHARACTER_MAXIMUM_LENGTH": None,
        "NUMERIC_PRECISION": 10,
        "NUMERIC_SCALE": 0,
        "DATETIME_PRECISION": None,
        "IS_NULLABLE": "NO",
        "COLUMN_KEY": "PRI",
        "COLUMN_DEFAULT": None,
        "COLUMN_COMMENT": "",
        "ORDINAL_POSITION": 1
    }]
    fk_data = [{
        "COLUMN_NAME": "id",
        "REFERENCED_TABLE_NAME": "parent",
        "REFERENCED_COLUMN_NAME": "id"
    }]

    mock_conn.execute_query.side_effect = lambda sql, params=(): columns_data if "COLUMNS" in sql.upper() else fk_data

    crawler = FieldCrawler(mock_conn, mock_db_config)
    res = crawler.crawl_fields_for_table("child")
    assert len(res) == 1
    assert res[0].khoa == "PK,FK"

def test_format_length_other_types(mock_db_config):
    mock_conn = MagicMock()
    crawler = FieldCrawler(mock_conn, mock_db_config)
    
    # date
    assert crawler._format_length({"DATA_TYPE": "date"}) == "YYYY-MM-DD"
    # text
    assert crawler._format_length({"DATA_TYPE": "longtext"}) == "text"
    # enum
    assert crawler._format_length({"DATA_TYPE": "enum"}) == "ENUM"
    # set
    assert crawler._format_length({"DATA_TYPE": "set"}) == "SET"
    # enum with values
    assert crawler._format_length({"DATA_TYPE": "enum", "COLUMN_TYPE": "enum('A','B','C')" }) == "ENUM(3 giá trị)"
    # custom fallback
    assert crawler._format_length({"DATA_TYPE": "blob"}) == "blob"

def test_enum_and_comment_parsing(mock_db_config):
    mock_conn = MagicMock()
    columns_data = [
        {
            "COLUMN_NAME": "gender",
            "DATA_TYPE": "enum",
            "COLUMN_TYPE": "enum('Male','Female')",
            "CHARACTER_MAXIMUM_LENGTH": None,
            "NUMERIC_PRECISION": None,
            "NUMERIC_SCALE": None,
            "DATETIME_PRECISION": None,
            "IS_NULLABLE": "NO",
            "COLUMN_KEY": "",
            "COLUMN_DEFAULT": None,
            "COLUMN_COMMENT": "Gender of user|danh_muc_gender.gender",
            "ORDINAL_POSITION": 1
        },
        {
            "COLUMN_NAME": "ssn",
            "DATA_TYPE": "varchar",
            "COLUMN_TYPE": "varchar(12)",
            "CHARACTER_MAXIMUM_LENGTH": 12,
            "NUMERIC_PRECISION": None,
            "NUMERIC_SCALE": None,
            "DATETIME_PRECISION": None,
            "IS_NULLABLE": "YES",
            "COLUMN_KEY": "",
            "COLUMN_DEFAULT": None,
            "COLUMN_COMMENT": "[PII] Social security number",
            "ORDINAL_POSITION": 2
        }
    ]
    mock_conn.execute_query.side_effect = lambda sql, params=(): columns_data if "COLUMNS" in sql.upper() else []
    
    glossary = [{"term": "Giới tính", "synonyms": ["gender", "sex"]}]
    crawler = FieldCrawler(mock_conn, mock_db_config, glossary=glossary)
    res = crawler.crawl_fields_for_table("users")
    
    assert len(res) == 2
    
    # Check gender column
    assert res[0].danh_sach_gia_tri == "Male, Female"
    assert res[0].dinh_nghia_nghiep_vu == ""
    assert res[0].anh_xa == "Giới tính"
    assert res[0].du_lieu_ca_nhan == ""
    
    # Check ssn column
    assert res[1].du_lieu_ca_nhan == ""
    assert res[1].dinh_nghia_nghiep_vu == ""
    assert res[1].anh_xa == "Ssn"

