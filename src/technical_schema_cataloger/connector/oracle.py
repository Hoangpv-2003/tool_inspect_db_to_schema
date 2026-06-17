import oracledb
from typing import List, Dict, Any
from .base import BaseConnector
from ..config.schema import DBConfig

class QueryError(Exception):
    pass

class OracleConnector(BaseConnector):
    def __init__(self, config: DBConfig):
        self.config = config
        self.connection = None

    def connect(self) -> None:
        try:
            self.connection = oracledb.connect(
                user=self.config.user,
                password=self.config.password,
                host=self.config.host,
                port=self.config.port,
                service_name=self.config.database
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Oracle database: {e}") from e

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
                columns = [col[0] for col in cursor.description]
                cursor.rowfactory = lambda *args: dict(zip(columns, args))
                return cursor.fetchall()
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
            FROM ALL_TABLES
            WHERE OWNER = USER
            ORDER BY TABLE_NAME
        """
        return self.execute_query(sql)

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT 
                COLUMN_NAME, 
                DATA_TYPE, 
                DATA_TYPE AS COLUMN_TYPE,
                CHAR_LENGTH AS CHARACTER_MAXIMUM_LENGTH, 
                DATA_PRECISION AS NUMERIC_PRECISION, 
                DATA_SCALE AS NUMERIC_SCALE, 
                NULL AS DATETIME_PRECISION, 
                DECODE(NULLABLE, 'N', 'NO', 'YES') AS IS_NULLABLE, 
                NULL AS COLUMN_KEY, 
                DATA_DEFAULT AS COLUMN_DEFAULT, 
                NULL AS COLUMN_COMMENT, 
                CASE WHEN IDENTITY_COLUMN = 'YES' THEN 'auto_increment' ELSE '' END AS EXTRA,
                COLUMN_ID AS ORDINAL_POSITION
            FROM ALL_TAB_COLUMNS
            WHERE OWNER = USER AND TABLE_NAME = :1
            ORDER BY COLUMN_ID
        """
        # Convert IS_NULLABLE (Y/N) to (YES/NO) for consistency if needed, 
        return self.execute_query(sql, (table_name,))

    def get_update_time(self, table_name: str) -> str | None:
        """Strictly Metadata-only update time retrieval for Oracle with creation date fallback."""
        sql_meta = """
            SELECT COALESCE(t.LAST_ANALYZED, o.CREATED) AS MAX_TIME
            FROM ALL_TABLES t
            JOIN ALL_OBJECTS o ON t.OWNER = o.OWNER AND t.TABLE_NAME = o.OBJECT_NAME
            WHERE t.OWNER = USER AND t.TABLE_NAME = :1 AND o.OBJECT_TYPE = 'TABLE'
        """
        try:
            res = self.execute_query(sql_meta, (table_name,))
            if res and res[0]["MAX_TIME"]:
                return str(res[0]["MAX_TIME"])
        except Exception:
            pass
        return None

    def get_primary_keys(self, table_name: str) -> List[str]:
        sql = """
            SELECT cols.column_name
            FROM all_constraints cons, all_cons_columns cols
            WHERE cols.table_name = :1
              AND cons.constraint_type = 'P'
              AND cons.constraint_name = cols.constraint_name
              AND cons.owner = cols.owner
              AND cons.owner = USER
            ORDER BY cols.position
        """
        res = self.execute_query(sql, (table_name,))
        return [row["COLUMN_NAME"] for row in res]

    def get_foreign_keys(self, table_name: str) -> Dict[str, Dict[str, str]]:
        sql = """
            SELECT 
                a.column_name, 
                c_pk.table_name AS referenced_table_name, 
                b.column_name AS referenced_column_name
            FROM all_cons_columns a
            JOIN all_constraints c 
              ON a.owner = c.owner AND a.constraint_name = c.constraint_name
            JOIN all_constraints c_pk 
              ON c.r_owner = c_pk.owner AND c.r_constraint_name = c_pk.constraint_name
            JOIN all_cons_columns b 
              ON c_pk.owner = b.owner AND c_pk.constraint_name = b.constraint_name AND a.position = b.position
            WHERE c.constraint_type = 'R' 
              AND a.table_name = :1
              AND a.owner = USER
        """
        res = self.execute_query(sql, (table_name,))
        return {
            row["COLUMN_NAME"]: {
                "referenced_table": row["REFERENCED_TABLE_NAME"],
                "referenced_column": row["REFERENCED_COLUMN_NAME"]
            } for row in res
        }

    def get_check_constraints(self, table_name: str) -> List[str]:
        sql = """
            SELECT SEARCH_CONDITION AS CHECK_CLAUSE
            FROM ALL_CONSTRAINTS
            WHERE CONSTRAINT_TYPE = 'C'
              AND TABLE_NAME = :1
              AND OWNER = USER
        """
        res = self.execute_query(sql, (table_name,))
        # Oracle stores search_condition as a LONG, which might need special handling 
        # but modern oracledb often handles it.
        return [row["CHECK_CLAUSE"] for row in res]
