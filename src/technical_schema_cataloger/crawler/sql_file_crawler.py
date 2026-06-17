import re
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from ..models.table_schema import TableSchema
from ..models.field_schema import FieldSchema

logger = logging.getLogger("db_schema_crawler")


class SQLFileCrawler:
    def __init__(self, file_path: str, glossary: List[Dict[str, Any]] = None):
        self.file_path = Path(file_path)
        self.sql_content = ""
        self.glossary = glossary or []

    def load_file(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.sql_content = f.read()

    def clean_identifier(self, ident: str) -> str:
        if not ident:
            return ""
        # Xử lý trường hợp có database.table -> chỉ lấy table
        if '.' in ident and not ident.startswith('`') and not ident.startswith('['):
            ident = ident.split('.')[-1]
        return ident.strip().strip('"`[]').strip()

    def _extract_bracket_content(self, text: str, start_index: int) -> Tuple[str, int]:
        bracket_level = 0
        content = ""
        found_start = False
        for i in range(start_index, len(text)):
            if text[i] == '(':
                if not found_start:
                    found_start = True
                bracket_level += 1
                if bracket_level > 1:
                    content += text[i]
            elif text[i] == ')':
                bracket_level -= 1
                if bracket_level == 0:
                    return content, i
                content += text[i]
            elif found_start:
                content += text[i]
        return content, len(text)

    def _split_columns(self, body: str) -> List[str]:
        col_definitions = []
        bracket_level = 0
        in_string = None
        current = ""
        for char in body:
            if char in ["'", '"'] and (not current or current[-1] != "\\"):
                if in_string == char: in_string = None
                elif in_string is None: in_string = char
            if in_string is None:
                if char == '(': bracket_level += 1
                elif char == ')': bracket_level -= 1
            if char == ',' and bracket_level == 0 and in_string is None:
                col_definitions.append(current.strip())
                current = ""
            else:
                current += char
        if current.strip(): col_definitions.append(current.strip())
        return col_definitions

    def _parse_column(self, col_def: str, table_pk_set: set, table_fk_map: dict) -> Optional[FieldSchema]:
        col_def = col_def.strip()
        if not col_def: return None
        upper_def = col_def.upper()
        
        # --- Ràng buộc cấp bảng ---
        if any(upper_def.startswith(w) for w in ["CONSTRAINT", "PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK", "KEY", "INDEX"]):
            pk_match = re.search(r"PRIMARY\s+KEY\s*\(\s*(.*?)\s*\)", col_def, re.IGNORECASE)
            if pk_match:
                for k in pk_match.group(1).split(','):
                    table_pk_set.add(self.clean_identifier(k))
            
            fk_match = re.search(r"FOREIGN\s+KEY\s*\(\s*(.*?)\s*\)\s*REFERENCES\s+([^\s\(]+)\s*\(\s*(.*?)\s*\)", col_def, re.IGNORECASE)
            if fk_match:
                cols = [self.clean_identifier(c) for c in fk_match.group(1).split(',')]
                ref_table = self.clean_identifier(fk_match.group(2))
                ref_cols = [self.clean_identifier(c) for c in fk_match.group(3).split(',')]
                for i, c in enumerate(cols):
                    ref_c = ref_cols[i] if i < len(ref_cols) else ref_cols[0]
                    table_fk_map[c] = f"FK→{ref_table}({ref_c})"
            return None

        # --- Khai báo cột ---
        col_name_match = re.match(r"^([`\"\[]?([a-zA-Z0-9_]+)[`\"\]]?)", col_def)
        if not col_name_match: return None
        
        raw_col_name = col_name_match.group(1)
        col_name = self.clean_identifier(col_name_match.group(2))

        rest = col_def[len(raw_col_name):].strip()
        type_search = re.match(r"^([a-zA-Z0-9_\s]+(?:\s*\([^)]*\))?)", rest, re.IGNORECASE)
        raw_type_full = type_search.group(1).strip() if type_search else "UNKNOWN"
        
        # Làm sạch kiểu: Loại bỏ CHARACTER SET, COLLATE và các từ khóa SQL
        raw_type_cleaned = re.sub(r"\b(CHARACTER SET|COLLATE)\b.*", "", raw_type_full, flags=re.IGNORECASE).strip()
        sql_keywords = ["PRIMARY", "KEY", "NOT", "NULL", "UNIQUE", "CHECK", "REFERENCES", "DEFAULT", "AUTO_INCREMENT", "UNSIGNED"]
        for kw in sql_keywords:
            raw_type_cleaned = re.split(rf"\b{kw}\b", raw_type_cleaned, flags=re.IGNORECASE)[0].strip()
        
        type_base_match = re.match(r"([a-zA-Z0-9_\s]+)", raw_type_cleaned.split('(')[0], re.IGNORECASE)
        col_type = type_base_match.group(1).strip().upper() if type_base_match else raw_type_cleaned.upper()
        # Bổ sung UNSIGNED lại vào kiểu nếu có (đặc thù MySQL)
        if "UNSIGNED" in raw_type_full.upper() and "UNSIGNED" not in col_type:
            col_type += " UNSIGNED"
        
        length_display = raw_type_cleaned if "(" in raw_type_cleaned else ""

        # Ràng buộc trên dòng
        is_required = "Có" if "NOT NULL" in upper_def else "Không"
        is_pk_on_line = "PK" if "PRIMARY KEY" in upper_def else ""
        if is_pk_on_line: table_pk_set.add(col_name)
        
        is_fk_on_line = ""
        ref_note = ""
        ref_match = re.search(r"REFERENCES\s+([^\s\(]+)\s*\((.*?)\)", col_def, re.IGNORECASE)
        if ref_match:
            ref_table = self.clean_identifier(ref_match.group(1))
            ref_col = self.clean_identifier(ref_match.group(2).split(',')[0])
            ref_note = f"FK→{ref_table}({ref_col})"
            is_fk_on_line = "FK"

        is_unique = "UQ" if "UNIQUE" in upper_def and not is_pk_on_line else ""
        
        default_val = ""
        default_match = re.search(r"\bDEFAULT\b\s+([^,;\s]+|'[^']*')", col_def, re.IGNORECASE)
        if default_match: default_val = f"Mặc định: {default_match.group(1).strip()}"

        ghi_chu = "; ".join([p for p in [default_val, ref_note] if p])

        allowed_values = ""
        check_pos = upper_def.find("CHECK")
        if check_pos != -1:
            content, _ = self._extract_bracket_content(col_def, check_pos)
            if content: allowed_values = content.replace("'", "").strip()

        mapping = ""
        if self.glossary:
            col_name_lower = col_name.lower()
            for item in self.glossary:
                synonyms = [s.lower() for s in item.get("synonyms", [])]
                if col_name_lower == str(item.get("id", "")).lower() or col_name_lower in synonyms:
                    mapping = item.get("term", "")
                    break

        return FieldSchema(
            stt=0, ten_csdl="SQL_FILE", ten_bang="", ten_truong_nghiep_vu="",
            ten_truong_ky_thuat=col_name, kieu_du_lieu=col_type, do_dai_dinh_dang=length_display,
            bat_buoc=is_required, khoa=is_pk_on_line or is_fk_on_line or is_unique, 
            danh_sach_gia_tri=allowed_values, dinh_nghia_nghiep_vu="", anh_xa=mapping, ghi_chu=ghi_chu
        )

    def parse(self) -> Tuple[List[TableSchema], List[FieldSchema]]:
        self.load_file()
        file_date = ""
        date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", self.sql_content)
        if date_match: file_date = date_match.group(1)

        logger.info("Đang tính toán chính xác số lượng bản ghi...")
        insert_counts = {}
        insert_iter = re.finditer(r"INSERT\s+INTO\s+[`\"\[]?([a-zA-Z0-9_.]+)[`\"\]]?.*?\bVALUES\b(.*?)(?:;|\n\s*INSERT|$)", self.sql_content, re.IGNORECASE | re.DOTALL)
        for match in insert_iter:
            table_name = self.clean_identifier(match.group(1))
            values_part = match.group(2)
            row_count, lvl = 0, 0
            for char in values_part:
                if char == '(':
                    if lvl == 0: row_count += 1
                    lvl += 1
                elif char == ')': lvl -= 1
            insert_counts[table_name] = insert_counts.get(table_name, 0) + row_count

        tables: List[TableSchema] = []
        fields_all: List[FieldSchema] = []
        clean_content = re.sub(r"--.*?\n|/\*.*?\*/", "", self.sql_content, flags=re.DOTALL)
        statements = clean_content.split(';')

        for stmt in statements:
            stmt = stmt.strip()
            if not stmt: continue
            match = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"\[\]a-zA-Z0-9_.]+)\s*\((.*)\)", stmt, re.IGNORECASE | re.DOTALL)
            if not match: continue
            table_name = self.clean_identifier(match.group(1))
            body = match.group(2)

            col_definitions = self._split_columns(body)
            table_pk_set, table_fk_map, current_fields = set(), {}, []

            for col_def in col_definitions:
                field = self._parse_column(col_def, table_pk_set, table_fk_map)
                if field:
                    field.ten_bang = table_name
                    current_fields.append(field)
                    fields_all.append(field)

            for f in current_fields:
                tags = []
                if f.ten_truong_ky_thuat in table_pk_set: tags.append("PK")
                if f.ten_truong_ky_thuat in table_fk_map: 
                    tags.append("FK")
                    f.ghi_chu = "; ".join(filter(None, [f.ghi_chu, table_fk_map[f.ten_truong_ky_thuat]]))
                if not tags and "UQ" in f.khoa.upper(): tags.append("UQ")
                if tags: f.khoa = ", ".join(tags)

            tables.append(TableSchema(
                stt=0, ten_csdl="SQL_FILE", ten_bang=table_name, mo_ta="", 
                so_truong=len(current_fields), so_ban_ghi=insert_counts.get(table_name, 0),
                khoa_dinh_danh=", ".join(sorted(table_pk_set)) if table_pk_set else "N/A",
                ngay_cap_nhat=file_date
            ))
        return tables, fields_all
