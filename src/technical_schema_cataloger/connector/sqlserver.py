import pyodbc
from typing import List, Dict, Any
from .base import BaseConnector
from ..config.schema import DBConfig

class QueryError(Exception):
    pass

class SQLServerConnector(BaseConnector):
    def __init__(self, config: DBConfig):
        self.config = config
        self.connection = None

    def connect(self) -> None:
        try:
            # Note: Driver name might need to be adjusted based on environment
            # Common drivers: {ODBC Driver 17 for SQL Server}, {SQL Server}
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.config.host},{self.config.port};"
                f"DATABASE={self.config.database};"
                f"UID={self.config.user};"
                f"PWD={self.config.password}"
            )
            self.connection = pyodbc.connect(conn_str)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to SQL Server database: {e}") from e

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
        self.connection = None

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        if not self.connection:
            raise QueryError("Not connected to database.")
        
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            if cursor.description:
                columns = [column[0] for column in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            return []
        except Exception as e:
            raise QueryError(f"Query execution failed: {e}") from e
        finally:
            if cursor is not None:
                cursor.close()

    def get_tables(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT 
                TABLE_NAME, 
                NULL AS TABLE_COMMENT
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
              AND TABLE_CATALOG = ?
            ORDER BY TABLE_NAME
        """
        return self.execute_query(sql, (self.config.database,))

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT 
                COLUMN_NAME, 
                DATA_TYPE, 
                DATA_TYPE AS COLUMN_TYPE,
                CHARACTER_MAXIMUM_LENGTH, 
                NUMERIC_PRECISION, 
                NUMERIC_SCALE, 
                DATETIME_PRECISION, 
                IS_NULLABLE, 
                NULL AS COLUMN_KEY, 
                COLUMN_DEFAULT, 
                NULL AS COLUMN_COMMENT, 
                '' AS EXTRA,
                ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_CATALOG = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """
        return self.execute_query(sql, (self.config.database, table_name))

    def get_primary_keys(self, table_name: str) -> List[str]:
        sql = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_CATALOG = ? 
              AND TABLE_NAME = ? 
              AND CONSTRAINT_NAME IN (
                  SELECT CONSTRAINT_NAME 
                  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
                  WHERE CONSTRAINT_TYPE = 'PRIMARY KEY' 
                    AND TABLE_CATALOG = ? 
                    AND TABLE_NAME = ?
              )
            ORDER BY ORDINAL_POSITION
        """
        res = self.execute_query(sql, (self.config.database, table_name, self.config.database, table_name))
        return [row["COLUMN_NAME"] for row in res]

    def get_foreign_keys(self, table_name: str) -> Dict[str, Dict[str, str]]:
        # SQL Server specific join for FKs
        sql = """
            SELECT 
                kcu.COLUMN_NAME, 
                rc.TABLE_NAME AS REFERENCED_TABLE_NAME, 
                kcu_ref.COLUMN_NAME AS REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc 
              ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu_ref 
              ON rc.UNIQUE_CONSTRAINT_NAME = kcu_ref.CONSTRAINT_NAME
            WHERE kcu.TABLE_CATALOG = ? AND kcu.TABLE_NAME = ?
        """
        res = self.execute_query(sql, (self.config.database, table_name))
        return {
            row["COLUMN_NAME"]: {
                "referenced_table": row["REFERENCED_TABLE_NAME"],
                "referenced_column": row["REFERENCED_COLUMN_NAME"]
            } for row in res
        }

    def get_check_constraints(self, table_name: str) -> List[str]:
        sql = """
            SELECT CHECK_CLAUSE
            FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
            JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc 
              ON cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
            WHERE tc.TABLE_CATALOG = ? 
              AND tc.TABLE_NAME = ?
        """
        res = self.execute_query(sql, (self.config.database, table_name))
        return [row["CHECK_CLAUSE"] for row in res]
