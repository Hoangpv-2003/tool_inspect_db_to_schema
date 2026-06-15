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
        return ident.strip().strip('"`[]').strip()

    def _split_columns(self, body: str) -> List[str]:
        """Tách các cột dựa trên dấu phẩy, bỏ qua dấu phẩy nằm trong ngoặc."""
        col_definitions = []
        bracket_level = 0
        current = ""
        for char in body:
            if char == '(':
                bracket_level += 1
            elif char == ')':
                bracket_level -= 1
            if char == ',' and bracket_level == 0:
                col_definitions.append(current.strip())
                current = ""
            else:
                current += char
        if current.strip():
            col_definitions.append(current.strip())
        return col_definitions

    def _parse_column(self, col_def: str, table_pk_set: set) -> Optional[FieldSchema]:
        """
        Trích xuất hoàn toàn từ cú pháp SQL, không phụ thuộc comment.
        Trả về FieldSchema hoặc None nếu không phải khai báo cột hợp lệ.
        """
        col_def = col_def.strip()
        if not col_def:
            return None

        # Bỏ qua các ràng buộc bảng (không phải khai báo cột)
        first_word = col_def.split()[0].upper() if col_def.split() else ""
        if first_word in ["CONSTRAINT", "PRIMARY", "INDEX", "KEY", "UNIQUE", "FOREIGN", "CHECK"]:
            # Nhưng vẫn xử lý để lấy thông tin khóa
            pk_match = re.search(r"PRIMARY\s+KEY\s*\(\s*(.*?)\s*\)", col_def, re.IGNORECASE)
            if pk_match:
                for k in pk_match.group(1).split(','):
                    table_pk_set.add(self.clean_identifier(k))
            return None

        # ---------- Tên cột ----------
        col_name_match = re.match(r"^([`\"\[\]a-zA-Z0-9_]+)", col_def)
        if not col_name_match:
            return None
        col_name = self.clean_identifier(col_name_match.group(1))

        # Loại khỏi những từ khóa SQL nếu bị nhận nhầm
        if col_name.upper() in ["PRIMARY", "FOREIGN", "CHECK", "UNIQUE", "INDEX", "KEY", "CONSTRAINT"]:
            return None

        # ---------- Kiểu dữ liệu ----------
        rest = col_def[len(col_name_match.group(0)):].strip()
        type_match = re.match(r"([a-zA-Z_]+(?:\s*\([^)]*\))?)", rest, re.IGNORECASE)
        raw_type = type_match.group(1) if type_match else "UNKNOWN"

        # Tách kiểu và tham số (độ dài / precision)
        type_param_match = re.match(r"([a-zA-Z_]+)\s*\(([^)]*)\)", raw_type, re.IGNORECASE)
        if type_param_match:
            col_type = type_param_match.group(1).upper()
            length = type_param_match.group(2).strip()
        else:
            # Không có tham số (INT, TEXT, DATE, BIGINT...) – bỏ trống length
            col_type = re.match(r"([a-zA-Z_]+)", raw_type, re.IGNORECASE).group(1).upper() if re.match(r"([a-zA-Z_]+)", raw_type) else raw_type.upper()
            length = ""

        col_def_upper = col_def.upper()

        # ---------- Ràng buộc ----------
        is_required = "Có" if "NOT NULL" in col_def_upper else "Không"
        is_pk = ""
        if "PRIMARY KEY" in col_def_upper:
            is_pk = "PK"
            table_pk_set.add(col_name)
        
        # UNIQUE → ghi chú vào cột khóa
        is_unique = "UQ" if "UNIQUE" in col_def_upper and not is_pk else ""

        khoa_val = is_pk or is_unique

        # ---------- CHECK → Danh sách giá trị ----------
        allowed_values = ""
        # Tìm nội dung bên trong CHECK (...). Dùng đếm ngoặc hoặc regex tham lam
        check_search = re.search(r"CHECK\s*\((.*)\)", col_def, re.IGNORECASE)
        if check_search:
            content = check_search.group(1).strip()
            # Nếu ngoặc bị dư do tham lam, chúng ta lấy đến dấu ngoặc đóng cuối cùng tương ứng
            # (Ở đây dùng regex tham lam (.*) sẽ lấy đến dấu ngoặc đóng cuối cùng của mệnh đề)
            allowed_values = content.replace("'", "").strip()

        # ---------- DEFAULT → Ghi chú ----------
        default_val = ""
        default_match = re.search(r"\bDEFAULT\b\s+([^\s,]+)", col_def, re.IGNORECASE)
        if default_match:
            default_val = f"Mặc định: {default_match.group(1).strip()}"

        # ---------- FOREIGN KEY (REFERENCES) → Ghi chú ----------
        ref_note = ""
        ref_match = re.search(r"REFERENCES\s+([^\s\(]+)\s*\(\s*([^)]+)\s*\)", col_def, re.IGNORECASE)
        if ref_match:
            ref_table = self.clean_identifier(ref_match.group(1))
            ref_col = self.clean_identifier(ref_match.group(2))
            ref_note = f"FK→{ref_table}({ref_col})"

        ghi_chu_parts = [p for p in [default_val, ref_note] if p]
        ghi_chu = "; ".join(ghi_chu_parts)

        # ---------- Ánh xạ từ điển ----------
        mapping = ""
        if self.glossary:
            col_name_lower = col_name.lower()
            for item in self.glossary:
                synonyms = [s.lower() for s in item.get("synonyms", [])]
                term_id = str(item.get("id", "")).lower()
                # Nếu tên cột khớp với id hoặc nằm trong danh sách synonyms
                if col_name_lower == term_id or col_name_lower in synonyms:
                    mapping = item.get("term", "")
                    break

        return FieldSchema(
            stt=0,
            ten_csdl="SQL_FILE",
            ten_bang="",  # sẽ được gán sau
            ten_truong_nghiep_vu="",  # Làm trống – người dùng tự điền
            ten_truong_ky_thuat=col_name,
            kieu_du_lieu=col_type,
            do_dai_dinh_dang=length,
            bat_buoc=is_required,
            khoa=khoa_val,
            danh_sach_gia_tri=allowed_values,
            dinh_nghia_nghiep_vu="",  # Làm trống – người dùng tự điền
            anh_xa=mapping,
            ghi_chu="" # Làm trống - người dùng tự điền 
        )

    def parse(self) -> Tuple[List[TableSchema], List[FieldSchema]]:
        self.load_file()

        tables: List[TableSchema] = []
        fields_all: List[FieldSchema] = []

        # Chia file thành các câu lệnh theo dấu chấm phẩy
        statements = self.sql_content.split(';')

        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue

            # Chỉ xử lý câu lệnh CREATE TABLE
            match = re.search(
                r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"\[\]a-zA-Z0-9_.]+)\s*\((.*)\)",
                stmt,
                re.IGNORECASE | re.DOTALL
            )
            if not match:
                continue

            table_name_raw = match.group(1)
            table_name = self.clean_identifier(table_name_raw)
            body = match.group(2)

            # Tách danh sách cột
            col_definitions = self._split_columns(body)

            table_pk_set: set = set()
            current_fields: List[FieldSchema] = []

            for col_def in col_definitions:
                field = self._parse_column(col_def, table_pk_set)
                if field:
                    field.ten_bang = table_name
                    # Cập nhật PK từ bảng (dòng CONSTRAINT PRIMARY KEY)
                    if field.ten_truong_ky_thuat in table_pk_set:
                        field.khoa = "PK"
                    current_fields.append(field)
                    fields_all.append(field)

            # Cập nhật PK cho các cột sau khi quét xong tất cả (vì PK có thể ở cuối)
            for f in current_fields:
                if f.ten_truong_ky_thuat in table_pk_set and not f.khoa:
                    f.khoa = "PK"

            # Ghép danh sách các khóa chính
            khoa_chinh = ", ".join(sorted(table_pk_set)) if table_pk_set else "N/A"

            # Đếm số bản ghi từ INSERT (linh hoạt: có / không có danh sách cột)
            insert_pattern = (
                rf"INSERT\s+INTO\s+[`\"\[]?{re.escape(table_name_raw)}[`\"\]]?"
                rf"\s*(?:\([^)]*\))?\s*VALUES"
            )
            row_count = len(re.findall(insert_pattern, self.sql_content, re.IGNORECASE))

            table_schema = TableSchema(
                stt=0,
                ten_csdl="SQL_FILE",
                ten_bang=table_name,
                mo_ta="",  # Làm trống – người dùng tự điền
                so_truong=len(current_fields),
                so_ban_ghi=row_count,
                khoa_dinh_danh=khoa_chinh,
                ngay_cap_nhat=datetime.now().strftime("%d/%m/%Y")
            )
            tables.append(table_schema)

        return tables, fields_all
