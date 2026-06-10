import re
from typing import List, Dict, Any
from ..connector.mysql import MySQLConnector
from ..config.schema import DBConfig
from ..models.field_schema import FieldSchema

class FieldCrawler:
    def __init__(self, connector: MySQLConnector, db_config: DBConfig):
        self.connector = connector
        self.db_config = db_config

    def _get_columns(self, table_name: str) -> List[Dict[str, Any]]:
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
                ORDINAL_POSITION
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        return self.connector.execute_query(sql, (self.db_config.database, table_name))

    def _get_fk_map(self, table_name: str) -> Dict[str, str]:
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
        res = self.connector.execute_query(sql, (self.db_config.database, table_name))
        return {row["COLUMN_NAME"]: "FK" for row in res}

    def _format_length(self, col: Dict[str, Any]) -> str:
        data_type = col["DATA_TYPE"].lower()
        if data_type in ("varchar", "char"):
            length = col["CHARACTER_MAXIMUM_LENGTH"]
            return f"{length} ký tự" if length is not None else ""
        elif data_type in ("int", "bigint", "tinyint", "mediumint", "smallint"):
            prec = col["NUMERIC_PRECISION"]
            return f"{prec} chữ số" if prec is not None else ""
        elif data_type in ("decimal", "float", "double"):
            prec = col["NUMERIC_PRECISION"]
            scale = col["NUMERIC_SCALE"]
            if prec is not None and scale is not None:
                return f"{prec},{scale}"
            return ""
        elif data_type in ("datetime", "timestamp"):
            return "YYYY-MM-DD HH:MM:SS"
        elif data_type == "date":
            return "YYYY-MM-DD"
        elif data_type in ("text", "longtext", "mediumtext", "tinytext"):
            return "text"
        return data_type

    def _resolve_key_type(self, col_key: str, col_name: str, fk_map: Dict[str, str]) -> str:
        is_pk = (col_key == "PRI")
        is_fk = (col_name in fk_map)
        if is_pk and is_fk:
            return "PK,FK"
        elif is_pk:
            return "PK"
        elif is_fk:
            return "FK"
        return ""

    def crawl_fields_for_table(self, table_name: str) -> List[FieldSchema]:
        cols = self._get_columns(table_name)
        fk_map = self._get_fk_map(table_name)
        result = []
        for idx, col in enumerate(cols, 1):
            col_name = col["COLUMN_NAME"]
            data_type = col["DATA_TYPE"]
            length_format = self._format_length(col)
            bat_buoc = "Có" if col["IS_NULLABLE"] == "NO" else "Không"
            key_type = self._resolve_key_type(col["COLUMN_KEY"], col_name, fk_map)
            
            # Extract allowed values for enum/set types from COLUMN_TYPE
            column_type = col.get("COLUMN_TYPE") or ""
            danh_sach_gia_tri = ""
            enum_match = re.match(r"^(?:enum|set)\((.*)\)$", column_type, re.IGNORECASE)
            if enum_match:
                vals = re.findall(r"'([^']*)'", enum_match.group(1))
                danh_sach_gia_tri = ", ".join(vals)
            
            # Extract dictionary mapping from COLUMN_COMMENT (phần sau ký tự |)
            comment = col["COLUMN_COMMENT"] or ""
            anh_xa = ""
            if "|" in comment:
                parts = comment.split("|", 1)
                anh_xa = parts[1].strip()

            dinh_nghia_nghiep_vu = "" # Left empty as per user request
            du_lieu_ca_nhan = ""      # Left empty as per user request
            ghi_chu = ""              # Left empty as per user request

            result.append(FieldSchema(
                stt=idx,
                ten_csdl=self.db_config.alias,
                ten_bang=table_name,
                ten_truong_nghiep_vu="", # Keep empty/manual
                ten_truong_ky_thuat=col_name,
                kieu_du_lieu=data_type,
                do_dai_dinh_dang=length_format,
                bat_buoc=bat_buoc,
                khoa=key_type,
                danh_sach_gia_tri=danh_sach_gia_tri,
                dinh_nghia_nghiep_vu=dinh_nghia_nghiep_vu,
                du_lieu_ca_nhan=du_lieu_ca_nhan,
                anh_xa=anh_xa,
                ghi_chu=ghi_chu
            ))
        return result
