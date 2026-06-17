import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Tu dong them thu muc goc vao sys.path
sys.path.append(os.getcwd())

from src.technical_schema_cataloger.connector.sqlserver import SQLServerConnector
from src.technical_schema_cataloger.connector.mysql import MySQLConnector
from src.technical_schema_cataloger.connector.postgresql import PostgreSQLConnector
from src.technical_schema_cataloger.connector.oracle import OracleConnector
from src.technical_schema_cataloger.config.schema import DBConfig

class TestConnectorsLogic(unittest.TestCase):
    def setUp(self):
        self.config = DBConfig(
            alias="test", db_type="sqlserver", host="localhost", 
            port=1433, user="sa", password="password", database="testdb"
        )

    def test_sqlserver_all_automated_logic(self):
        connector = SQLServerConnector(self.config)
        # Mock PK
        with patch.object(connector, 'execute_query', return_value=[{"COLUMN_NAME": "ID"}]):
            pks = connector.get_primary_keys("dbo.Users")
            self.assertIn("ID", pks)
        # Mock FK
        fk_res = [{"COLUMN_NAME": "RoleID", "REFERENCED_TABLE_NAME": "Roles", "REFERENCED_COLUMN_NAME": "ID"}]
        with patch.object(connector, 'execute_query', return_value=fk_res):
            fks = connector.get_foreign_keys("dbo.Users")
            self.assertEqual(fks["RoleID"]["referenced_table"], "Roles")
        print("[OK] SQL Server: PK/FK logic dat chuan.")

    def test_mysql_all_automated_logic(self):
        connector = MySQLConnector(self.config)
        # Mock sequential calls: 1st for finding column, 2nd for getting MAX value
        mock_find_col = [{"COLUMN_NAME": "updated_at"}]
        mock_get_val = [{"MAX_TIME": "2023-10-12 09:13:53"}]
        
        with patch.object(connector, 'execute_query', side_effect=[mock_find_col, mock_get_val]):
            ut = connector.get_update_time("Users")
            self.assertEqual(ut, "2023-10-12 09:13:53")
        print("[OK] MySQL: Update Time logic dat chuan.")

    def test_postgresql_all_automated_logic(self):
        connector = PostgreSQLConnector(self.config)
        # Mock PK
        with patch.object(connector, 'execute_query', return_value=[{"column_name": "id"}]):
            pks = connector.get_primary_keys("Users")
            self.assertIn("id", pks)
        print("[OK] PostgreSQL: PK logic dat chuan.")

    def test_oracle_all_automated_logic(self):
        connector = OracleConnector(self.config)
        # Mock FK - Match OracleConnector.get_foreign_keys logic (uses REFERENCED_TABLE_NAME)
        fk_res = [{"COLUMN_NAME": "DEPT_ID", "REFERENCED_TABLE_NAME": "DEPARTMENTS", "REFERENCED_COLUMN_NAME": "ID"}]
        with patch.object(connector, 'execute_query', return_value=fk_res):
            fks = connector.get_foreign_keys("EMPLOYEES")
            self.assertEqual(fks["DEPT_ID"]["referenced_table"], "DEPARTMENTS")
        print("[OK] Oracle: FK logic dat chuan.")

if __name__ == "__main__":
    unittest.main()
