import pytest
from unittest.mock import MagicMock, patch
from mysql.connector import Error as MySQLError
from db_schema_crawler.connector.mysql import MySQLConnector, QueryError
from tests.fixtures.mock_mysql_data import mock_db_config

def test_connect_success(mock_db_config):
    with patch("mysql.connector.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        connector = MySQLConnector(mock_db_config)
        connector.connect()
        
        mock_connect.assert_called_once_with(
            host=mock_db_config.host,
            port=mock_db_config.port,
            user=mock_db_config.user,
            password=mock_db_config.password,
            database=mock_db_config.database,
            charset=mock_db_config.charset
        )
        assert connector.connection == mock_conn

def test_connect_failure(mock_db_config):
    with patch("mysql.connector.connect") as mock_connect:
        mock_connect.side_effect = MySQLError("Access denied")
        
        connector = MySQLConnector(mock_db_config)
        with pytest.raises(ConnectionError) as exc_info:
            connector.connect()
        assert "Failed to connect to MySQL database" in str(exc_info.value)

def test_execute_query_returns_rows(mock_db_config):
    with patch("mysql.connector.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "test"}]
        
        connector = MySQLConnector(mock_db_config)
        connector.connect()
        res = connector.execute_query("SELECT * FROM users")
        
        assert res == [{"id": 1, "name": "test"}]
        mock_conn.cursor.assert_called_once_with(dictionary=True)
        mock_cursor.execute.assert_called_once_with("SELECT * FROM users", ())
        mock_cursor.close.assert_called_once()

def test_execute_empty_result(mock_db_config):
    with patch("mysql.connector.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        connector = MySQLConnector(mock_db_config)
        connector.connect()
        res = connector.execute_query("SELECT * FROM empty_table")
        assert res == []

def test_context_manager_closes_on_exit(mock_db_config):
    with patch("mysql.connector.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.is_connected.return_value = True
        
        with MySQLConnector(mock_db_config) as connector:
            assert connector.connection == mock_conn
            
        mock_conn.close.assert_called_once()
        assert connector.connection is None

def test_execute_query_not_connected(mock_db_config):
    connector = MySQLConnector(mock_db_config)
    with pytest.raises(QueryError) as exc_info:
        connector.execute_query("SELECT 1")
    assert "Not connected to database" in str(exc_info.value)

def test_execute_query_mysql_error(mock_db_config):
    with patch("mysql.connector.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = MySQLError("Syntax error")
        
        connector = MySQLConnector(mock_db_config)
        connector.connect()
        with pytest.raises(QueryError) as exc_info:
            connector.execute_query("SELECT 1")
        assert "Query execution failed" in str(exc_info.value)
        mock_cursor.close.assert_called_once()
