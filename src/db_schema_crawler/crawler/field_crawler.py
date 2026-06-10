import re
import logging
import unicodedata
import difflib
from typing import List, Dict, Any, Optional
from ..connector.mysql import MySQLConnector
from ..config.schema import DBConfig
from ..models.field_schema import FieldSchema
from ..ai.llm_client import LLMClient

logger = logging.getLogger(__name__)

class FieldCrawler:
    def __init__(
        self, 
        connector: MySQLConnector, 
        db_config: DBConfig, 
        llm_client: Optional[LLMClient] = None,
        glossary: Optional[List[Dict[str, Any]]] = None
    ):
        self.connector = connector
        self.db_config = db_config
        self.llm_client = llm_client
        self.glossary = glossary or []

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

    def _get_fk_details(self, table_name: str) -> Dict[str, Dict[str, str]]:
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
        try:
            res = self.connector.execute_query(sql, (self.db_config.database, table_name))
            return {
                row["COLUMN_NAME"]: {
                    "referenced_table": row["REFERENCED_TABLE_NAME"],
                    "referenced_column": row["REFERENCED_COLUMN_NAME"]
                } for row in res
            }
        except Exception as e:
            logger.warning(f"Could not retrieve FK details for table {table_name}: {e}")
            return {}

    def _format_length(self, col: Dict[str, Any]) -> str:
        data_type = col["DATA_TYPE"].lower()
        # BUG FIX #4: ENUM/SET must return "" not "enum"/"set"
        if data_type in ("enum", "set"):
            return ""
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

    def _resolve_key_type(self, col_key: str, col_name: str, fk_details: Dict[str, Dict[str, str]]) -> str:
        # BUG FIX #5: Detect UNIQUE KEY (UNI) from COLUMN_KEY
        is_pk = (col_key == "PRI")
        is_fk = (col_name in fk_details)
        is_uk = (col_key == "UNI")
        if is_pk and is_fk:
            return "PK,FK"
        elif is_pk:
            return "PK"
        elif is_fk:
            return "FK"
        elif is_uk:
            return "UK"
        return ""

    def _normalize(self, s: str) -> str:
        """Lowercase, strip accents and punctuation — used for character-level comparison."""
        s = s.lower().strip()
        s = re.sub(r"[_\-\s]+", "", s)
        s = "".join(
            c for c in unicodedata.normalize("NFD", s)
            if unicodedata.category(c) != "Mn"
        )
        return s

    def _col_tokens(self, col_name: str) -> List[str]:
        """Split column name into meaningful word tokens by underscore."""
        return [t.lower() for t in col_name.split("_") if t]

    def resolve_glossary_mapping(self, col_name: str, comment: str, table_name: str) -> str:
        if not self.glossary:
            return ""

        norm_col = self._normalize(col_name)
        col_tokens = self._col_tokens(col_name)

        # Level 1: Exact Synonym Match (case-insensitive)
        col_lower = col_name.lower()
        for entry in self.glossary:
            term = entry.get("term", "")
            syns = entry.get("synonyms", [])
            if col_lower in [s.lower() for s in syns]:
                return term

        # Level 2: Normalized Match — exact equality only (no substring)
        for entry in self.glossary:
            term = entry.get("term", "")
            syns = entry.get("synonyms", [])
            # Check if any synonym normalizes to the exact same string as the column
            for syn in syns:
                if self._normalize(syn) == norm_col:
                    return term
            # Check synonym tokens against column tokens
            syn_token_sets = [(s, set(self._col_tokens(s))) for s in syns]
            for syn_str, syn_tokens in syn_token_sets:
                # Rule A — Multi-token synonyms: ALL tokens must appear in column tokens
                # AND the synonym covers most of the column (prevents "ho_ten" matching "ten_don_vi")
                if len(syn_tokens) >= 2 and syn_tokens.issubset(set(col_tokens)):
                    if len(syn_tokens) >= len(col_tokens) - 1:
                        return term
                # Rule B — Single-token synonyms with length >= 5:
                # The synonym token must exactly match one of the column tokens.
                # Length guard prevents short tokens like "ten" (3), "dat" (3), "id" (2)
                # from causing false positives (e.g. "ten_don_vi" → "Họ và tên")
                elif len(syn_tokens) == 1:
                    single = next(iter(syn_tokens))
                    if len(single) >= 5 and single in col_tokens:
                        return term

        # Level 3: Fuzzy Match (difflib SequenceMatcher, threshold >= 0.85)
        # Only consider columns with at least 4 characters to avoid false positives on short names
        if len(norm_col) >= 4:
            best_ratio = 0.0
            best_term = ""
            for entry in self.glossary:
                term = entry.get("term", "")
                syns = entry.get("synonyms", [])
                for syn in syns:
                    norm_syn = self._normalize(syn)
                    if len(norm_syn) < 4:  # Skip very short synonyms in fuzzy matching
                        continue
                    ratio = difflib.SequenceMatcher(None, norm_col, norm_syn).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_term = term
            
            if best_ratio >= 0.85:
                return best_term

        # Level 4: LLM Classification — only for non-mock modes (real network call)
        if self.llm_client and self.llm_client.config.mode in ("local", "api"):
            terms_list = ", ".join([entry.get("term", "") for entry in self.glossary])
            system_prompt = "Bạn là trợ lý chuẩn hóa từ điển dữ liệu. Hãy phân loại thông tin cột vào khái niệm chuẩn tương ứng."
            prompt = f"""
Danh sách các khái niệm nghiệp vụ chuẩn:
[{terms_list}]

Thông tin cột dữ liệu cần phân loại:
- Tên bảng: {table_name}
- Tên cột kỹ thuật: {col_name}
- Bình luận/Mô tả cột: {comment}

Hãy phân loại và chọn chính xác MỘT khái niệm nghiệp vụ chuẩn từ danh sách trên khớp nhất.
Chỉ trả về tên khái niệm chuẩn (ví dụ: 'Giới tính'), nếu không khớp thì trả về chuỗi rỗng.
"""
            try:
                res = self.llm_client.request(prompt, system_prompt).strip().replace('"', '').replace("'", "")
                for entry in self.glossary:
                    if res.lower() == entry.get("term", "").lower():
                        return entry.get("term", "")
            except Exception as e:
                logger.warning(f"LLM glossary mapping failed for {col_name}: {e}")

        return ""

    def _get_table_row_count(self, table_name: str) -> int:
        # Count up to 50001 only for performance safety
        count_sql = f"SELECT COUNT(*) AS row_count FROM (SELECT 1 FROM `{self.db_config.database}`.`{table_name}` LIMIT 50001) AS t"
        try:
            res = self.connector.execute_query(count_sql)
            return res[0]["row_count"] if res else 0
        except Exception:
            return 0

    def resolve_allowed_values(
        self, 
        col_name: str, 
        col_type: str, 
        comment: str, 
        table_name: str, 
        fk_details: Dict[str, Dict[str, str]]
    ) -> str:
        # Level 1: ENUM / SET — read directly from schema, 100% accurate
        enum_match = re.match(r"^(?:enum|set)\((.*)\)$", col_type, re.IGNORECASE)
        if enum_match:
            vals = re.findall(r"'([^']*)'", enum_match.group(1))
            return ", ".join(vals)

        # Level 2: Foreign Key Lookup — follow FK to referenced table
        if col_name in fk_details:
            ref_table = fk_details[col_name]["referenced_table"]
            ref_column = fk_details[col_name]["referenced_column"]
            sql = f"SELECT DISTINCT `{ref_column}` FROM `{self.db_config.database}`.`{ref_table}` LIMIT 11"
            try:
                res = self.connector.execute_query(sql)
                vals = [str(row[ref_column]) for row in res if row[ref_column] is not None]
                if len(vals) > 10:
                    return ", ".join(vals[:10]) + "..."
                return ", ".join(vals)
            except Exception as e:
                logger.warning(f"Failed to fetch FK values from {ref_table}.{ref_column}: {e}")

        # Level 3: Distinct scan for small tables on candidate types
        data_type_clean = col_type.split("(")[0].lower()
        candidate_types = ("tinyint", "smallint", "mediumint", "int", "integer", "varchar", "char")
        
        if data_type_clean in candidate_types:
            row_count = self._get_table_row_count(table_name)
            if 0 < row_count <= 50000:
                sql = f"SELECT DISTINCT `{col_name}` FROM `{self.db_config.database}`.`{table_name}` LIMIT 11"
                try:
                    res = self.connector.execute_query(sql)
                    vals = [str(row[col_name]) for row in res if row[col_name] is not None]
                    # Only treat as categorical domain if ≤ 10 distinct values
                    if 0 < len(vals) <= 10:
                        raw_list = ", ".join(vals)

                        # Level 4: LLM value translation — only for real LLM modes (local/api)
                        # BUG FIX #1: Never call mock LLM here (mock always returns "0: Nam, 1: Nữ")
                        if self.llm_client and self.llm_client.config.mode in ("local", "api"):
                            system_prompt = "Bạn là trợ lý phân tích dữ liệu. Hãy chuyển đổi danh sách giá trị mã hoá sang mô tả thân thiện."
                            prompt = f"""
Thông tin cột:
- Tên bảng: {table_name}
- Tên cột: {col_name}
- Kiểu dữ liệu: {col_type}
- Mô tả: {comment}
- Danh sách giá trị thô: [{raw_list}]

Nếu các giá trị này là mã (code) cần dịch nghĩa, hãy trả về dạng 'mã: nghĩa' (ví dụ: '0: Nam, 1: Nữ').
Nếu không phải mã cần dịch, trả về nguyên bản danh sách thô.
Chỉ trả về kết quả ngắn gọn.
"""
                            try:
                                res_llm = self.llm_client.request(prompt, system_prompt).strip().replace('"', '').replace("'", "")
                                if res_llm:
                                    return res_llm
                            except Exception as e:
                                logger.warning(f"LLM allowed values resolution failed for {col_name}: {e}")

                        return raw_list
                except Exception as e:
                    logger.warning(f"Failed to scan distinct values for {table_name}.{col_name}: {e}")

        return ""

    def crawl_fields_for_table(self, table_name: str) -> List[FieldSchema]:
        cols = self._get_columns(table_name)
        fk_details = self._get_fk_details(table_name)
        result = []
        for idx, col in enumerate(cols, 1):
            col_name = col["COLUMN_NAME"]
            data_type = col["DATA_TYPE"]
            column_type = col.get("COLUMN_TYPE") or ""
            comment = col["COLUMN_COMMENT"] or ""
            
            length_format = self._format_length(col)
            bat_buoc = "Có" if col["IS_NULLABLE"] == "NO" else "Không"
            key_type = self._resolve_key_type(col["COLUMN_KEY"], col_name, fk_details)
            
            # Resolve allowed values (Level 1 to 4)
            danh_sach_gia_tri = self.resolve_allowed_values(
                col_name=col_name,
                col_type=column_type,
                comment=comment,
                table_name=table_name,
                fk_details=fk_details
            )
            
            # Resolve glossary mapping (Level 1 to 4)
            anh_xa = self.resolve_glossary_mapping(
                col_name=col_name,
                comment=comment,
                table_name=table_name
            )

            dinh_nghia_nghiep_vu = "" # Kept empty per user request
            du_lieu_ca_nhan = ""      # Kept empty per user request
            ghi_chu = ""              # Kept empty per user request

            result.append(FieldSchema(
                stt=idx,
                ten_csdl=self.db_config.alias,
                ten_bang=table_name,
                ten_truong_nghiep_vu="",
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
