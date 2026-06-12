import logging
from typing import List, Dict, Any
from ..connector.base import BaseConnector
from ..config.schema import DBConfig
from ..models.table_schema import TableSchema

logger = logging.getLogger(__name__)

class TableCrawler:
    def __init__(self, connector: BaseConnector, db_config: DBConfig):
        self.connector = connector
        self.db_config = db_config

    def crawl_all_tables(self) -> List[TableSchema]:
        tables = self.connector.get_tables()
        result = []
        for idx, table in enumerate(tables, 1):
            table_name = table["TABLE_NAME"]
            mo_ta = ""
            
            # Count records
            so_ban_ghi = self.connector.count_records(table_name)
            
            # Get primary keys
            pks = self.connector.get_primary_keys(table_name)
            khoa_dinh_danh = " + ".join(pks) if pks else ""
            
            # Get number of fields
            columns = self.connector.get_columns(table_name)
            so_truong = len(columns)
            
            # Get update time
            ngay_cap_nhat = self.connector.get_update_time(table_name)
            
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
