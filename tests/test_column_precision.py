import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.append(os.getcwd())

from src.technical_schema_cataloger.connector.sqlserver import SQLServerConnector
from src.technical_schema_cataloger.connector.mysql import MySQLConnector
from src.technical_schema_cataloger.connector.postgresql import PostgreSQLConnector
from src.technical_schema_cataloger.connector.oracle import OracleConnector
from src.technical_schema_cataloger.config.schema import DBConfig

class TestColumnPrecision(unittest.TestCase):
    def setUp(self):
        self.config = DBConfig(
            alias="precision_test", db_type="sqlserver", host="localhost", 
            port=1433, user="test", password="test", database="test_db"
        )

    def test_sqlserver_column_precision(self):
        print("\n--- Testing SQL Server Column Logic ---")
        connector = SQLServerConnector(self.config)
        mock_data = [
            # Scenario 1: Auto-increment PK
            {"COLUMN_NAME": "id", "DATA_TYPE": "int", "IS_NULLABLE": "NO", "COLUMN_DEFAULT": None, "EXTRA": "auto_increment"},
            # Scenario 2: String with default value
            {"COLUMN_NAME": "status", "DATA_TYPE": "nvarchar", "IS_NULLABLE": "YES", "COLUMN_DEFAULT": "('active')", "EXTRA": ""},
        ]
        with patch.object(connector, 'execute_query', return_value=mock_data):
            cols = connector.get_columns("test_table")
            # Verify ID info
            self.assertEqual(cols[0]["EXTRA"], "auto_increment", "Fail: ID should be auto_increment")
            self.assertEqual(cols[0]["IS_NULLABLE"], "NO", "Fail: ID should be NOT NULL")
            # Verify Status info
            self.assertEqual(cols[1]["COLUMN_DEFAULT"], "('active')", "Fail: Status should have default value")
        print("[OK] SQL Server: All column scenarios passed.")

    def test_mysql_column_precision(self):
        print("\n--- Testing MySQL Column Logic ---")
        connector = MySQLConnector(self.config)
        mock_data = [
            # Scenario: Auto-increment and mandatory
            {"COLUMN_NAME": "id", "DATA_TYPE": "int", "IS_NULLABLE": "NO", "COLUMN_DEFAULT": None, "EXTRA": "auto_increment"},
        ]
        with patch.object(connector, 'execute_query', return_value=mock_data):
            cols = connector.get_columns("test_table")
            self.assertEqual(cols[0]["EXTRA"], "auto_increment")
            self.assertEqual(cols[0]["IS_NULLABLE"], "NO")
        print("[OK] MySQL: All column scenarios passed.")

    def test_postgresql_column_precision(self):
        print("\n--- Testing PostgreSQL Column Logic ---")
        connector = PostgreSQLConnector(self.config)
        mock_data = [
            # Scenario: SERIAL column detected via EXTRA logic in SQL
            {"column_name": "id", "data_type": "integer", "is_nullable": "NO", "EXTRA": "auto_increment"},
        ]
        with patch.object(connector, 'execute_query', return_value=mock_data):
            cols = connector.get_columns("test_table")
            self.assertEqual(cols[0]["EXTRA"], "auto_increment")
        print("[OK] PostgreSQL: All column scenarios passed.")

    def test_oracle_column_precision(self):
        print("\n--- Testing Oracle Column Logic ---")
        connector = OracleConnector(self.config)
        mock_data = [
            # Scenario: IDENTITY column
            {"COLUMN_NAME": "ID", "DATA_TYPE": "NUMBER", "IS_NULLABLE": "NO", "EXTRA": "auto_increment"},
        ]
        with patch.object(connector, 'execute_query', return_value=mock_data):
            cols = connector.get_columns("test_table")
            self.assertEqual(cols[0]["EXTRA"], "auto_increment")
        print("[OK] Oracle: All column scenarios passed.")

if __name__ == "__main__":
    unittest.main()
