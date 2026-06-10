import pytest
from unittest.mock import MagicMock, patch
from db_schema_crawler.crawler.table_crawler import TableCrawler
from tests.fixtures.mock_mysql_data import mock_db_config

def test_crawl_returns_table_list(mock_db_config):
    mock_conn = MagicMock()
    # Mock _get_table_list query: return 2 tables
    tables_data = [
        {"TABLE_NAME": "users", "TABLE_COMMENT": "User accounts", "CREATE_TIME": "2026-06-01", "UPDATE_TIME": "2026-06-02"},
        {"TABLE_NAME": "orders", "TABLE_COMMENT": None, "CREATE_TIME": "2026-06-01", "UPDATE_TIME": None}
    ]
    
    # We will mock execute_query
    def side_effect(sql, params=()):
        sql_upper = sql.upper()
        if "INFORMATION_SCHEMA.TABLES" in sql_upper:
            if "TABLE_NAME = %S" in sql_upper or "TABLE_NAME =" in sql_upper:
                table_name = params[1] if len(params) > 1 else ""
                if table_name == "users":
                    return [{"UPDATE_TIME": "2026-06-02"}]
                return [{"UPDATE_TIME": None}]
            return tables_data
        elif "COUNT(*)" in sql_upper:
            if "USERS" in sql_upper:
                return [{"row_count": 50}]
            elif "COLUMNS" in sql_upper:
                return [{"col_count": 4}]
            return [{"row_count": 100}]
        elif "KEY_COLUMN_USAGE" in sql_upper:
            if "users" in params:
                return [{"COLUMN_NAME": "id"}]
            return []
        elif "COLUMNS" in sql_upper:
            # for fallback cols check
            return []
        return []
        
    mock_conn.execute_query.side_effect = side_effect
    
    crawler = TableCrawler(mock_conn, mock_db_config)
    res = crawler.crawl_all_tables()
    
    assert len(res) == 2
    assert res[0].ten_bang == "users"
    assert res[0].mo_ta == ""
    assert res[0].so_ban_ghi == 50
    assert res[0].so_truong == 4
    assert res[0].khoa_dinh_danh == "id"
    assert res[0].ngay_cap_nhat == "2026-06-02"

    assert res[1].ten_bang == "orders"
    assert res[1].mo_ta == ""
    assert res[1].so_ban_ghi == 100
    assert res[1].khoa_dinh_danh == ""
    assert res[1].ngay_cap_nhat is None

def test_count_records_correct(mock_db_config):
    mock_conn = MagicMock()
    mock_conn.execute_query.return_value = [{"row_count": 42}]
    
    crawler = TableCrawler(mock_conn, mock_db_config)
    assert crawler._count_records("users") == 42
    mock_conn.execute_query.assert_called_once_with("SELECT COUNT(*) AS row_count FROM `test_db`.`users`")

def test_count_records_error(mock_db_config):
    mock_conn = MagicMock()
    mock_conn.execute_query.side_effect = Exception("Table does not exist")
    
    crawler = TableCrawler(mock_conn, mock_db_config)
    assert crawler._count_records("ghost_table") == -1

def test_primary_keys_joined(mock_db_config):
    mock_conn = MagicMock()
    mock_conn.execute_query.return_value = [
        {"COLUMN_NAME": "order_id"},
        {"COLUMN_NAME": "item_id"}
    ]
    
    crawler = TableCrawler(mock_conn, mock_db_config)
    pks = crawler._get_primary_keys("order_items")
    assert pks == ["order_id", "item_id"]
    assert " + ".join(pks) == "order_id + item_id"

def test_empty_database(mock_db_config):
    mock_conn = MagicMock()
    mock_conn.execute_query.return_value = []
    
    crawler = TableCrawler(mock_conn, mock_db_config)
    assert crawler.crawl_all_tables() == []

def test_get_update_time_fallback(mock_db_config):
    mock_conn = MagicMock()
    
    # 1st query: TABLES UPDATE_TIME -> return None
    # 2nd query: COLUMNS check -> return updated_at
    # 3rd query: MAX(updated_at) -> return max_time
    def side_effect(sql, params=()):
        sql_upper = sql.upper()
        if "INFORMATION_SCHEMA.TABLES" in sql_upper:
            return [{"UPDATE_TIME": None}]
        elif "INFORMATION_SCHEMA.COLUMNS" in sql_upper:
            return [{"COLUMN_NAME": "updated_at"}]
        elif "MAX(`UPDATED_AT`)" in sql_upper:
            return [{"max_time": "2026-06-03 12:00:00"}]
        return []
        
    mock_conn.execute_query.side_effect = side_effect
    crawler = TableCrawler(mock_conn, mock_db_config)
    t = crawler._get_update_time("users")
    assert t == "2026-06-03 12:00:00"
