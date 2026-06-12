import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any
from .base import BaseConnector
from ..config.schema import DBConfig

class QueryError(Exception):
    pass

class PostgreSQLConnector(BaseConnector):
    def __init__(self, config: DBConfig):
        self.config = config
        self.connection = None

    def connect(self) -> None:
        try:
            self.connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL database: {e}") from e

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
        self.connection = None

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        if not self.connection:
            raise QueryError("Not connected to database.")
        
        # PostgreSQL uses %s for placeholders, so we might need to convert ? or :name if used elsewhere.
        # But for now, we assume the caller provides compatible SQL.
        
        cursor = None
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(sql, params)
            if cursor.description:
                result = cursor.fetchall()
                return [dict(row) for row in result]
            return []
        except Exception as e:
            raise QueryError(f"Query execution failed: {e}") from e
        finally:
            if cursor is not None:
                cursor.close()

    def get_tables(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT 
                table_name AS "TABLE_NAME", 
                NULL AS "TABLE_COMMENT"
            FROM information_schema.tables
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        # Note: PostgreSQL does not store table comments in information_schema.tables in a standard way
        # across all versions easily without joining with pg_description.
        return self.execute_query(sql)

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT 
                column_name AS "COLUMN_NAME", 
                data_type AS "DATA_TYPE", 
                udt_name AS "COLUMN_TYPE",
                character_maximum_length AS "CHARACTER_MAXIMUM_LENGTH", 
                numeric_precision AS "NUMERIC_PRECISION", 
                numeric_scale AS "NUMERIC_SCALE", 
                NULL AS "DATETIME_PRECISION", 
                is_nullable AS "IS_NULLABLE", 
                NULL AS "COLUMN_KEY", 
                column_default AS "COLUMN_DEFAULT", 
                NULL AS "COLUMN_COMMENT", 
                '' AS "EXTRA",
                ordinal_position AS "ORDINAL_POSITION"
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """
        return self.execute_query(sql, (table_name,))

    def get_primary_keys(self, table_name: str) -> List[str]:
        sql = """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = %s
            ORDER BY kcu.ordinal_position
        """
        res = self.execute_query(sql, (table_name,))
        return [row["column_name"] for row in res]

    def get_foreign_keys(self, table_name: str) -> Dict[str, Dict[str, str]]:
        sql = """
            SELECT
                kcu.column_name,
                ccu.table_name AS referenced_table_name,
                ccu.column_name AS referenced_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
              AND tc.table_schema = 'public'
              AND tc.table_name = %s
        """
        res = self.execute_query(sql, (table_name,))
        return {
            row["column_name"]: {
                "referenced_table": row["referenced_table_name"],
                "referenced_column": row["referenced_column_name"]
            } for row in res
        }

    def get_check_constraints(self, table_name: str) -> List[str]:
        sql = """
            SELECT cc.check_clause
            FROM information_schema.table_constraints tc
            JOIN information_schema.check_constraints cc
              ON tc.constraint_name = cc.constraint_name
             AND tc.constraint_schema = cc.constraint_schema
            WHERE tc.constraint_type = 'CHECK'
              AND tc.table_schema = 'public'
              AND tc.table_name = %s
        """
        res = self.execute_query(sql, (table_name,))
        return [row["check_clause"] for row in res]
