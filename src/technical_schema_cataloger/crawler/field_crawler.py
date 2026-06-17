import re
import logging
import unicodedata
import difflib
from typing import List, Dict, Any, Optional
from ..connector.base import BaseConnector
from ..config.schema import DBConfig
from ..models.field_schema import FieldSchema
from ..ai.llm_client import LLMClient

logger = logging.getLogger(__name__)

class FieldCrawler:
    def __init__(
        self, 
        connector: BaseConnector, 
        db_config: DBConfig, 
        llm_client: Optional[LLMClient] = None,
        glossary: Optional[List[Dict[str, Any]]] = None
    ):
        self.connector = connector
        self.db_config = db_config
        self.llm_client = llm_client
        self.glossary = glossary or []

    def _resolve_check_constraint_for_column(self, col_name: str, check_clauses: List[str]) -> Optional[str]:
        for clause in check_clauses:
            clean_clause = clause.replace("`", "")
            if re.search(r'\b' + re.escape(col_name) + r'\b', clean_clause, re.IGNORECASE):
                in_match = re.search(r'in\s*\(([^)]+)\)', clean_clause, re.IGNORECASE)
                if in_match:
                    vals = [v.strip().strip("'\"") for v in in_match.group(1).split(",")]
                    return ", ".join(vals)
                
                between_match = re.search(r'between\s+(\S+)\s+and\s+(\S+)', clean_clause, re.IGNORECASE)
                if between_match:
                    g1 = between_match.group(1).strip().rstrip(")")
                    g2 = between_match.group(2).strip().rstrip(")")
                    return f"{g1} - {g2}"
                
                comp_match = re.search(re.escape(col_name) + r'\s*([><=!]+)\s*(\S+)', clean_clause, re.IGNORECASE)
                if comp_match:
                    op = comp_match.group(1).strip()
                    val = comp_match.group(2).strip().rstrip(")")
                    return f"{op} {val}"
                
                return clean_clause
        return None

    def _format_length(self, col: Dict[str, Any]) -> str:
        data_type = col["DATA_TYPE"].lower()
        if data_type in ("enum", "set"):
            column_type = col.get("COLUMN_TYPE") or ""
            match = re.match(r"^(?:enum|set)\((.*)\)$", column_type, re.IGNORECASE)
            if match:
                vals = re.findall(r"'([^']*)'", match.group(1))
                return f"{data_type.upper()}({len(vals)} giá trị)"
            return data_type.upper()
        if data_type in ("varchar", "char", "nvarchar", "nchar"):
            length = col["CHARACTER_MAXIMUM_LENGTH"]
            if length == -1 or (length is not None and length > 4000 and data_type.startswith('n')):
                 return "MAX"
            return f"{length} ký tự" if length is not None else ""
        elif data_type in ("varbinary", "binary", "image"):
            length = col["CHARACTER_MAXIMUM_LENGTH"]
            if length == -1: return "MAX"
            return f"{length} bytes" if length is not None else "Binary"
        elif data_type in ("int", "bigint", "tinyint", "mediumint", "smallint"):
            prec = col["NUMERIC_PRECISION"]
            return f"{prec} chữ số" if prec is not None else ""
        elif data_type in ("decimal", "float", "double", "numeric", "real"):
            prec = col["NUMERIC_PRECISION"]
            scale = col["NUMERIC_SCALE"]
            if prec is not None and scale is not None:
                return f"{prec},{scale}"
            return ""
        elif data_type in ("datetime", "timestamp", "datetime2", "smalldatetime"):
            return "YYYY-MM-DD HH:MM:SS"
        elif data_type == "date":
            return "YYYY-MM-DD"
        elif data_type in ("text", "longtext", "mediumtext", "tinytext", "ntext"):
            return "text"
        return data_type if data_type else "N/A"

    def _resolve_key_type(self, col_name: str, pks: List[str], fk_details: Dict[str, Dict[str, str]]) -> str:
        is_pk = (col_name in pks)
        is_fk = (col_name in fk_details)
        if is_pk and is_fk:
            return "PK,FK"
        elif is_pk:
            return "PK"
        elif is_fk:
            return "FK"
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

    def _to_pascal_case_fallback(self, col_name: str) -> str:
        parts = [p.capitalize() for p in col_name.split("_") if p]
        replacements = {
            "cb": "CanBo",
            "cd": "ChucDanh",
            "dv": "DonVi",
            "hs": "HoSo",
            "tthc": "TTHC",
            "cccd": "SoDinhDanh",
            "cmnd": "SoDinhDanh",
            "sdt": "SoDienThoai",
            "gt": "GioiTinh",
            "sts": "TrangThai",
            "lvl": "CapDo"
        }
        converted_parts = []
        for p in parts:
            p_lower = p.lower()
            if p_lower in replacements:
                converted_parts.append(replacements[p_lower])
            else:
                converted_parts.append(p)
        return "".join(converted_parts)

    def _resolve_glossary_mapping_term(self, col_name: str, comment: str, table_name: str) -> str:
        if not self.glossary:
            return ""

        norm_col = self._normalize(col_name)
        col_tokens = self._col_tokens(col_name)

        col_lower = col_name.lower()
        for entry in self.glossary:
            term = entry.get("term", "")
            mapping_id = entry.get("id", term)
            syns = entry.get("synonyms", [])
            if col_lower in [s.lower() for s in syns]:
                return mapping_id

        for entry in self.glossary:
            term = entry.get("term", "")
            mapping_id = entry.get("id", term)
            syns = entry.get("synonyms", [])
            for syn in syns:
                if self._normalize(syn) == norm_col:
                    return mapping_id
            syn_token_sets = [(s, set(self._col_tokens(s))) for s in syns]
            for syn_str, syn_tokens in syn_token_sets:
                if len(syn_tokens) >= 2 and syn_tokens.issubset(set(col_tokens)):
                    if len(syn_tokens) >= len(col_tokens) - 1:
                        return mapping_id
                elif len(syn_tokens) == 1:
                    single = next(iter(syn_tokens))
                    if len(single) >= 5 and single in col_tokens:
                        return mapping_id

        if len(norm_col) >= 4:
            best_ratio = 0.0
            best_id = ""
            for entry in self.glossary:
                term = entry.get("term", "")
                mapping_id = entry.get("id", term)
                syns = entry.get("synonyms", [])
                for syn in syns:
                    norm_syn = self._normalize(syn)
                    if len(norm_syn) < 4:
                        continue
                    ratio = difflib.SequenceMatcher(None, norm_col, norm_syn).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_id = mapping_id
            
            if best_ratio >= 0.85:
                return best_id

        return ""

    def resolve_glossary_mapping(self, col_name: str, comment: str, table_name: str) -> str:
        matched_id = self._resolve_glossary_mapping_term(col_name, comment, table_name)
        if matched_id:
            return matched_id

        if self.llm_client and self.llm_client.config.mode in ("local", "api"):
            terms_list = ", ".join([f"{entry.get('term')} ({entry.get('id')})" for entry in self.glossary])
            system_prompt = "Bạn là trợ lý chuẩn hóa từ điển dữ liệu chính phủ. Hãy phân loại thông tin cột vào khái niệm chuẩn tương ứng."
            prompt = f"""
Danh sách các khái niệm nghiệp vụ chuẩn:
[{terms_list}]

Thông tin cột dữ liệu cần phân loại:
- Tên bảng: {table_name}
- Tên cột kỹ thuật: {col_name}
- Bình luận/Mô tả cột: {comment}

Hãy chọn khái niệm nghiệp vụ chuẩn khớp nhất từ danh sách trên.
- Nếu khớp một khái niệm, chỉ trả về mã định danh PascalCase tương ứng của khái niệm đó (ví dụ: 'HoTen', 'GioiTinh', 'SoDinhDanh', 'NgaySinh', 'SoDienThoai', 'Email', 'MaCoQuan', 'MaThuTuc', 'MaHoSoTTHC', 'TrangThaiHoSo', 'DanhGiaHaiLong').
- Nếu không khớp khái niệm nào trong danh sách, hãy tự suy luận ra một từ khóa viết tắt PascalCase đại diện cho cột (ví dụ: 'chuyen_nganh' -> 'ChuyenNganh', 'luong_cb' -> 'LuongCoBan', 'het_hieu_luc' -> 'HetHieuLuc').
Chỉ trả về chuỗi từ khóa PascalCase ngắn gọn nhất, không thêm giải thích hay ký tự thừa.
"""
            try:
                res_llm = self.llm_client.request(prompt, system_prompt).strip().replace('"', '').replace("'", "")
                res_llm = re.sub(r"[^A-Za-z0-9]", "", res_llm)
                if res_llm:
                    return res_llm
            except Exception as e:
                logger.warning(f"LLM glossary mapping failed for {col_name}: {e}")

        return self._to_pascal_case_fallback(col_name)

    def _get_fallback_allowed_values(self, col_name: str, col_type: str, table_name: str) -> str:
        col_lower = col_name.lower()
        data_type_clean = col_type.split("(")[0].lower()

        if data_type_clean in ("date", "datetime", "timestamp", "time", "year"):
            return "YYYY-MM-DD" if data_type_clean == "date" else "N/A"

        if any(k in col_lower for k in ("so_giay_to", "so_cccd", "so_cmnd", "cccd", "cmnd", "citizen_id", "identity_card")):
            if "12" in col_type or "12" in col_lower:
                return "Chuỗi 12 chữ số"
            return "Chuỗi ký tự số"

        if any(k in col_lower for k in ("sdt", "so_dien_thoai", "phone", "tel")):
            return "Số điện thoại"

        if "email" in col_lower or "mail" in col_lower:
            return "Email"

        if "trang_thai_hs" in col_lower or "trang_thai_ho_so" in col_lower:
            return "1:Mới, 2:Đang XL, 3:Xong, 4:Từ chối"
        if "status" in col_lower or "trang_thai" in col_lower or "sts" in col_lower:
            if "land" in table_name or "transaction" in table_name:
                return "0: Hủy, 1: Chờ, 2: Hoàn thành"
            if "can_bo" in table_name or "nhan_vien" in table_name:
                return "0: Nghỉ, 1: Đang làm"
            return "0: Trong hạn, 1: Quá hạn"
        if "hai_long" in col_lower or "muc_do_hai_long" in col_lower:
            return "1:Rất hài lòng -> 5:Rất KHL"
        if "do_khan" in col_lower or "muc_do_khan" in col_lower:
            return "1: Thường, 2: Khẩn, 3: Thượng khẩn, 4: Hỏa tốc"
        if "so_ky_hieu" in col_lower or "ma_dinh_danh" in col_lower:
            return "Ký tự chữ và số"
        if "so_ngay" in col_lower:
            return "Số ngày"

        is_code_or_id = any(k in col_lower for k in ("ma", "code", "id", "lvl", "uid", "key"))
        if data_type_clean in ("varchar", "char", "nvarchar", "text", "longtext", "mediumtext", "tinytext"):
            if is_code_or_id:
                return "Ký tự chữ và số"
            return "Text"

        if data_type_clean in ("int", "bigint", "tinyint", "smallint", "mediumint", "decimal", "float", "double"):
            return "N/A"

        return "N/A"

    def resolve_allowed_values(
        self, 
        col_name: str, 
        col_type: str, 
        comment: str, 
        table_name: str, 
        fk_details: Dict[str, Dict[str, str]],
        extra: str = "",
        check_clauses: List[str] = None
    ) -> str:
        # Step 1: Check constraints from information_schema
        # A. Auto-increment check
        if extra.lower() == "auto_increment":
            return "Auto-Increment"

        # B. Foreign Key check
        if col_name in fk_details:
            ref_table = fk_details[col_name]["referenced_table"]
            return f"Map với {ref_table}"

        # C. ENUM / SET check
        enum_match = re.match(r"^(?:enum|set)\((.*)\)$", col_type, re.IGNORECASE)
        if enum_match:
            vals = re.findall(r"'([^']*)'", enum_match.group(1))
            return ", ".join(vals)

        # D. CHECK Constraint check
        if check_clauses:
            constraint_val = self._resolve_check_constraint_for_column(col_name, check_clauses)
            if constraint_val:
                return constraint_val

        # Step 2: Fallback to LLM (for local/api modes)
        if self.llm_client and self.llm_client.config.mode in ("local", "api"):
            key_type = "None"
            referenced_table = ""
            if col_name in fk_details:
                key_type = "FK"
                referenced_table = fk_details[col_name]["referenced_table"]

            system_prompt = "Bạn là chuyên gia thiết kế cơ sở dữ liệu và chuẩn hóa dữ liệu chính phủ."
            prompt = f"""
Hãy phân tích thông tin cột và sinh ra mô tả định dạng/giá trị cho phép nghiệp vụ tương ứng theo phong cách chuẩn nghiệp vụ Việt Nam.
Ví dụ:
- ma_ho_so (varchar(20)) -> Regex: ^[A-Z0-9.\\-]+$
- ma_tthc (varchar(50)) -> Map với tbl_danhmuc_tthc
- so_giay_to (varchar(12)) -> Chuỗi 12 chữ số
- ngay_tiep_nhan (datetime) -> N/A
- trang_thai_hs (int(1)) -> 1:Mới, 2:Đang XL, 3:Xong, 4:Từ chối
- do_khan (int) -> 1: Thường, 2: Khẩn, 3: Thượng khẩn, 4: Hỏa tốc
- ho_ten (varchar(100)) -> Text
- don_vi_id (int) -> Map với dm_don_vi
- ma_co_quan_xl -> Danh mục cơ quan nhà nước
- so_ky_hieu -> Ký tự chữ và số (VD: 123/UBND-TH)
- id tự tăng -> Auto-Increment

Hãy sinh giá trị cho phép ngắn gọn cho cột sau:
- Tên bảng: {table_name}
- Tên cột: {col_name}
- Kiểu dữ liệu: {col_type}
- Khóa (PK/FK/None): {key_type}
- Bảng tham chiếu (nếu là FK): {referenced_table}

Quy tắc:
1. Nếu là khóa ngoại (FK), hãy trả về 'Map với {referenced_table}'.
2. Nếu kiểu ngày tháng, trả về định dạng ngày tháng như 'YYYY-MM-DD' hoặc 'N/A' (nếu là ngày giờ nhận).
3. Nếu là khóa chính tự tăng (auto_increment), trả về 'Auto-Increment'.
4. Nếu là trường văn bản tự do thông thường (tên, mô tả, nội dung), trả về 'Text'.
5. Nếu là trường số lượng thông thường không phải mã (ví dụ: số ngày, diện tích, tiền lương), trả về mô tả đơn vị như 'Số ngày', 'Số tiền', 'N/A'.
6. Nếu là trường mã trạng thái/phân loại/số định danh, hãy suy luận danh sách giá trị nghiệp vụ chuẩn hoặc định dạng regex/mô tả chuỗi (ví dụ: '1:Mới, 2:Đang XL...', 'Chuỗi 12 chữ số').
Chỉ trả về chuỗi kết quả ngắn gọn nhất, không thêm giải thích hay ký tự thừa.
"""
            try:
                res_llm = self.llm_client.request(prompt, system_prompt).strip().replace('"', '').replace("'", "")
                if res_llm:
                    return res_llm
            except Exception as e:
                logger.warning(f"LLM allowed values resolution failed for {col_name}: {e}")

        # Step 3: Fallback to rule engine (mock mode / fallback)
        return self._get_fallback_allowed_values(col_name, col_type, table_name)

    def crawl_fields_for_table(self, table_name: str) -> List[FieldSchema]:
        cols = self.connector.get_columns(table_name)
        fk_details = self.connector.get_foreign_keys(table_name)
        check_clauses = self.connector.get_check_constraints(table_name)
        pks = self.connector.get_primary_keys(table_name)
        
        result = []
        for idx, col in enumerate(cols, 1):
            col_name = col["COLUMN_NAME"]
            data_type = col["DATA_TYPE"]
            column_type = col.get("COLUMN_TYPE") or ""
            comment = col.get("COLUMN_COMMENT") or ""
            extra = col.get("EXTRA") or ""
            
            length_format = self._format_length(col)
            bat_buoc = "Có" if col.get("IS_NULLABLE") == "NO" else "Không"
            key_type = self._resolve_key_type(col_name, pks, fk_details)
            
            # Resolve allowed values
            danh_sach_gia_tri = self.resolve_allowed_values(
                col_name=col_name,
                col_type=column_type,
                comment=comment,
                table_name=table_name,
                fk_details=fk_details,
                extra=extra,
                check_clauses=check_clauses
            )
            
            # Resolve glossary mapping
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
                ghi_chu=""
            ))
        return result
