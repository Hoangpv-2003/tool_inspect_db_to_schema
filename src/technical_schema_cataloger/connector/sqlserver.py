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
        drivers = [
            "{SQL Server}",
            "{ODBC Driver 17 for SQL Server}",
            "{ODBC Driver 18 for SQL Server}",
            "{ODBC Driver 13 for SQL Server}",
            "{ODBC Driver 11 for SQL Server}"
        ]
        
        last_error = None
        for driver in drivers:
            try:
                print(f"  -> Dang thu ket noi bang driver: {driver}...")
                conn_str = (
                    f"DRIVER={driver};"
                    f"SERVER={self.config.host},{self.config.port};"
                    f"DATABASE={self.config.database};"
                    f"UID={self.config.user};"
                    f"PWD={self.config.password};"
                    "Connect Timeout=5;"
                )
                self.connection = pyodbc.connect(conn_str)
                print(f"  [OK] Ket noi thanh cong bang {driver}")
                return  # Connection successful
            except pyodbc.Error as e:
                last_error = e
                continue
        
        raise ConnectionError(f"Failed to connect to SQL Server database. Tested drivers: {drivers}. Last error: {last_error}")

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
                TABLE_SCHEMA + '.' + TABLE_NAME AS TABLE_NAME, 
                NULL AS TABLE_COMMENT
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
              AND TABLE_CATALOG = ?
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        return self.execute_query(sql, (self.config.database,))

    def count_records(self, table_name: str) -> int:
        """Fast row count using metadata partitions (SSMS style)."""
        # table_name might be 'schema.table'
        parts = table_name.split('.')
        pure_table = parts[-1]
        schema = parts[0] if len(parts) > 1 else 'dbo'
        
        sql = """
            SELECT SUM(rows) as row_count
            FROM sys.partitions
            WHERE object_id = OBJECT_ID(?)
              AND index_id IN (0, 1)
        """
        try:
            res = self.execute_query(sql, (f"{schema}.{pure_table}",))
            return res[0]["row_count"] if res and res[0]["row_count"] is not None else 0
        except Exception:
            return super().count_records(table_name)

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        # Handle schema.table
        parts = table_name.split('.')
        pure_table = parts[-1]
        schema = parts[0] if len(parts) > 1 else None

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
                CASE WHEN COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA + '.' + TABLE_NAME), COLUMN_NAME, 'IsIdentity') = 1 
                     THEN 'auto_increment' ELSE '' END AS EXTRA,
                ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_CATALOG = ? AND TABLE_NAME = ?
        """
        params = [self.config.database, pure_table]
        if schema:
            sql += " AND TABLE_SCHEMA = ?"
            params.append(schema)
        sql += " ORDER BY ORDINAL_POSITION"
        
        return self.execute_query(sql, tuple(params))

    def get_primary_keys(self, table_name: str) -> List[str]:
        parts = table_name.split('.')
        pure_table = parts[-1]
        schema = parts[0] if len(parts) > 1 else None

        sql = """
            SELECT kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
              ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
             AND kcu.TABLE_CATALOG = tc.TABLE_CATALOG
             AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA
            WHERE kcu.TABLE_CATALOG = ? 
              AND kcu.TABLE_NAME = ? 
              AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        """
        params = [self.config.database, pure_table]
        if schema:
            sql += " AND kcu.TABLE_SCHEMA = ?"
            params.append(schema)
        sql += " ORDER BY kcu.ORDINAL_POSITION"

        res = self.execute_query(sql, tuple(params))
        return [row["COLUMN_NAME"] for row in res]

    def get_foreign_keys(self, table_name: str) -> Dict[str, Dict[str, str]]:
        parts = table_name.split('.')
        pure_table = parts[-1]
        schema = parts[0] if len(parts) > 1 else None

        sql = """
            SELECT 
                kcu.COLUMN_NAME, 
                kcu_ref.TABLE_NAME AS REFERENCED_TABLE_NAME, 
                kcu_ref.COLUMN_NAME AS REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc 
              ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu_ref 
              ON rc.UNIQUE_CONSTRAINT_NAME = kcu_ref.CONSTRAINT_NAME
            WHERE kcu.TABLE_CATALOG = ? AND kcu.TABLE_NAME = ?
        """
        params = [self.config.database, pure_table]
        if schema:
            sql += " AND kcu.TABLE_SCHEMA = ?"
            params.append(schema)

        res = self.execute_query(sql, tuple(params))
        return {
            row["COLUMN_NAME"]: {
                "referenced_table": row["REFERENCED_TABLE_NAME"],
                "referenced_column": row["REFERENCED_COLUMN_NAME"]
            } for row in res
        }

    def get_check_constraints(self, table_name: str) -> List[str]:
        parts = table_name.split('.')
        pure_table = parts[-1]
        schema = parts[0] if len(parts) > 1 else None

        sql = """
            SELECT CHECK_CLAUSE
            FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
            JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc 
              ON cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
            WHERE tc.TABLE_CATALOG = ? 
              AND tc.TABLE_NAME = ?
        """
        params = [self.config.database, pure_table]
        if schema:
            sql += " AND tc.TABLE_SCHEMA = ?"
            params.append(schema)

        res = self.execute_query(sql, tuple(params))
        return [row["CHECK_CLAUSE"] for row in res]

    def get_update_time(self, table_name: str) -> str | None:
        """Strictly Metadata-only update time retrieval for SQL Server with create_date fallback."""
        parts = table_name.split('.')
        pure_table = parts[-1]
        schema = parts[0] if len(parts) > 1 else 'dbo'
        
        sql = """
            SELECT 
                COALESCE(
                    (SELECT MAX(last_user_update) 
                     FROM sys.dm_db_index_usage_stats 
                     WHERE database_id = DB_ID() AND object_id = OBJECT_ID(?)),
                    (SELECT modify_date FROM sys.tables WHERE name = ? AND schema_id = SCHEMA_ID(?)),
                    (SELECT create_date FROM sys.tables WHERE name = ? AND schema_id = SCHEMA_ID(?))
                ) as MAX_TIME
        """
        try:
            # Try with fully qualified name and pure name
            res = self.execute_query(sql, (f"[{schema}].[{pure_table}]", pure_table, schema, pure_table, schema))
            if res and res[0]["MAX_TIME"]:
                return res[0]["MAX_TIME"].strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        return None
