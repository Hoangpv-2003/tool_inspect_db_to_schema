import logging
from typing import List, Dict, Any
from ..connector.mysql import MySQLConnector
from ..config.schema import DBConfig
from ..models.table_schema import TableSchema

logger = logging.getLogger(__name__)

class TableCrawler:
    def __init__(self, connector: MySQLConnector, db_config: DBConfig):
        self.connector = connector
        self.db_config = db_config

    def _get_table_list(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT 
                TABLE_NAME, 
                TABLE_COMMENT, 
                CREATE_TIME, 
                UPDATE_TIME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s 
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """
        return self.connector.execute_query(sql, (self.db_config.database,))

    def _count_records(self, table_name: str) -> int:
        sql = f"SELECT COUNT(*) AS row_count FROM `{self.db_config.database}`.`{table_name}`"
        try:
            res = self.connector.execute_query(sql)
            return res[0]["row_count"] if res else 0
        except Exception as e:
            logger.warning(f"Could not count records for table {table_name}: {e}")
            return -1

    def _get_primary_keys(self, table_name: str) -> List[str]:
        sql = """
            SELECT COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s 
              AND TABLE_NAME = %s 
              AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
        """
        res = self.connector.execute_query(sql, (self.db_config.database, table_name))
        return [row["COLUMN_NAME"] for row in res]

    def _get_update_time(self, table_name: str, fallback_cols: List[str] = None) -> str | None:
        # Step 1: Read UPDATE_TIME from TABLES schema
        sql_tables = """
            SELECT UPDATE_TIME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """
        res = self.connector.execute_query(sql_tables, (self.db_config.database, table_name))
        if res and res[0]["UPDATE_TIME"]:
            return str(res[0]["UPDATE_TIME"])

        # Step 2: Fallback querying columns if they exist
        if fallback_cols is None:
            fallback_cols = ["updated_at", "update_time", "modified_at"]
        
        # Check column existence first
        sql_cols = """
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
              AND COLUMN_NAME IN (%s, %s, %s)
        """
        existing_cols = self.connector.execute_query(sql_cols, (self.db_config.database, table_name, *fallback_cols))
        existing_names = {row["COLUMN_NAME"] for row in existing_cols}
        
        for col in fallback_cols:
            if col in existing_names:
                sql_max = f"SELECT MAX(`{col}`) AS max_time FROM `{self.db_config.database}`.`{table_name}`"
                try:
                    res_max = self.connector.execute_query(sql_max)
                    if res_max and res_max[0]["max_time"]:
                        return str(res_max[0]["max_time"])
                except Exception:
                    pass
        return None

    def crawl_all_tables(self) -> List[TableSchema]:
        tables = self._get_table_list()
        result = []
        for idx, table in enumerate(tables, 1):
            table_name = table["TABLE_NAME"]
            mo_ta = ""
            
            # Count records
            so_ban_ghi = self._count_records(table_name)
            
            # Get primary keys
            pks = self._get_primary_keys(table_name)
            khoa_dinh_danh = " + ".join(pks) if pks else ""
            
            # Get number of fields
            sql_fields_count = """
                SELECT COUNT(*) AS col_count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            """
            fields_res = self.connector.execute_query(sql_fields_count, (self.db_config.database, table_name))
            so_truong = fields_res[0]["col_count"] if fields_res else 0
            
            # Get update time
            ngay_cap_nhat = self._get_update_time(table_name)
            
            result.append(TableSchema(
                stt=idx,
                ten_csdl=self.db_config.alias,
                ten_bang=table_name,
                mo_ta=mo_ta,
                so_truong=so_truong,
                so_ban_ghi=so_ban_ghi,
                khoa_dinh_danh=khoa_dinh_danh,
                ngay_cap_nhat=ngay_cap_nhat
            ))
        return result
