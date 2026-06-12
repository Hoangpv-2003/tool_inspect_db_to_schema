import mysql.connector
from mysql.connector import Error as MySQLError
from typing import List, Dict, Any
from .base import BaseConnector
from ..config.schema import DBConfig

class QueryError(Exception):
    pass

class MySQLConnector(BaseConnector):
    def __init__(self, config: DBConfig):
        self.config = config
        self.connection = None

    def connect(self) -> None:
        try:
            self.connection = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset
            )
        except MySQLError as e:
            raise ConnectionError(f"Failed to connect to MySQL database: {e}") from e

    def disconnect(self) -> None:
        if self.connection and self.connection.is_connected():
            self.connection.close()
        self.connection = None

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        if not self.connection or not self.connection.is_connected():
            raise QueryError("Not connected to database.")
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            if cursor.description:
                result = cursor.fetchall()
                return result
            return []
        except MySQLError as e:
            raise QueryError(f"Query execution failed: {e}") from e
        finally:
            if cursor is not None:
                cursor.close()

    def get_tables(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT 
                TABLE_NAME, 
                TABLE_COMMENT
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s 
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """
        return self.execute_query(sql, (self.config.database,))

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT 
                COLUMN_NAME, 
                DATA_TYPE, 
                COLUMN_TYPE,
                CHARACTER_MAXIMUM_LENGTH, 
                NUMERIC_PRECISION, 
                NUMERIC_SCALE, 
                DATETIME_PRECISION, 
                IS_NULLABLE, 
                COLUMN_KEY, 
                COLUMN_DEFAULT, 
                COLUMN_COMMENT, 
                EXTRA,
                ORDINAL_POSITION
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        return self.execute_query(sql, (self.config.database, table_name))

    def get_primary_keys(self, table_name: str) -> List[str]:
        sql = """
            SELECT COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s 
              AND TABLE_NAME = %s 
              AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
        """
        res = self.execute_query(sql, (self.config.database, table_name))
        return [row["COLUMN_NAME"] for row in res]

    def get_foreign_keys(self, table_name: str) -> Dict[str, Dict[str, str]]:
        sql = """
            SELECT 
                COLUMN_NAME, 
                REFERENCED_TABLE_NAME, 
                REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s 
              AND TABLE_NAME = %s 
              AND REFERENCED_TABLE_NAME IS NOT NULL
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
            SELECT cc.CHECK_CLAUSE
            FROM information_schema.TABLE_CONSTRAINTS tc
            JOIN information_schema.CHECK_CONSTRAINTS cc 
              ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA 
             AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
            WHERE tc.CONSTRAINT_SCHEMA = %s 
              AND tc.TABLE_NAME = %s 
              AND tc.CONSTRAINT_TYPE = 'CHECK'
        """
        res = self.execute_query(sql, (self.config.database, table_name))
        return [row["CHECK_CLAUSE"] for row in res]

    def count_records(self, table_name: str) -> int:
        """Get approximate row count for MySQL to avoid hanging on large tables."""
        sql = """
            SELECT TABLE_ROWS as row_count 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """
        try:
            res = self.execute_query(sql, (self.config.database, table_name))
            return res[0]["row_count"] if res else 0
        except Exception:
            # Fallback to a fast count if possible or just return -1
            return -1

    def get_update_time(self, table_name: str) -> str | None:
        """MySQL specific update time retrieval."""
        # Try MAX(updated_at) etc as approximation
        fallback_cols = ["updated_at", "update_time", "modified_at"]
        sql_cols = f"""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            AND COLUMN_NAME IN ('{"', '".join(fallback_cols)}')
        """
        try:
            existing_cols = self.execute_query(sql_cols, (self.config.database, table_name))
            for row in existing_cols:
                col = row["COLUMN_NAME"]
                sql_max = f"SELECT MAX(`{col}`) AS max_time FROM `{self.config.database}`.`{table_name}`"
                res_max = self.execute_query(sql_max)
                if res_max and res_max[0]["max_time"]:
                    return str(res_max[0]["max_time"])
        except Exception:
            pass

        # Fallback to information_schema
        sql_tables = "SELECT UPDATE_TIME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s"
        try:
            res = self.execute_query(sql_tables, (self.config.database, table_name))
            if res and res[0]["UPDATE_TIME"]:
                return str(res[0]["UPDATE_TIME"])
        except Exception:
            pass
        return None
