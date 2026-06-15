"""
Script chẩn đoán: Kiểm tra bộ trích xuất SQL một cách độc lập (không qua Excel writer).
Chạy từ thư mục gốc: python test_parser.py
"""
import sys
import re

# === Nhúng logic parser vào đây để test độc lập ===

def clean_identifier(ident: str) -> str:
    if not ident:
        return ""
    return ident.strip().strip('"`[]').strip()


def split_columns(body: str):
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


def parse_column(col_def, table_pk_set):
    col_def = col_def.strip()
    if not col_def:
        return None

    first_word = col_def.split()[0].upper() if col_def.split() else ""
    if first_word in ["CONSTRAINT", "PRIMARY", "INDEX", "KEY", "UNIQUE", "FOREIGN", "CHECK"]:
        pk_match = re.search(r"PRIMARY\s+KEY\s*\(\s*(.*?)\s*\)", col_def, re.IGNORECASE)
        if pk_match:
            for k in pk_match.group(1).split(','):
                table_pk_set.add(clean_identifier(k))
        return None

    col_name_match = re.match(r"^([`\"\[\]a-zA-Z0-9_]+)", col_def)
    if not col_name_match:
        print(f"  ⚠️  CẢNH BÁO: Không nhận diện được tên cột từ: '{col_def[:50]}'")
        return None

    col_name = clean_identifier(col_name_match.group(1))
    if col_name.upper() in ["PRIMARY", "FOREIGN", "CHECK", "UNIQUE", "INDEX", "KEY", "CONSTRAINT"]:
        return None

    rest = col_def[len(col_name_match.group(0)):].strip()
    type_match = re.match(r"([a-zA-Z_]+(?:\s*\([^)]*\))?)", rest, re.IGNORECASE)
    raw_type = type_match.group(1).strip() if type_match else "UNKNOWN"

    type_param_match = re.match(r"([a-zA-Z_]+)\s*\(([^)]*)\)", raw_type, re.IGNORECASE)
    if type_param_match:
        col_type = type_param_match.group(1).upper()
        length = type_param_match.group(2).strip()
    else:
        col_type = raw_type.upper()
        length = ""

    col_def_upper = col_def.upper()
    is_required = "Có" if "NOT NULL" in col_def_upper else "Không"
    is_pk = "PK" if "PRIMARY KEY" in col_def_upper else ""
    if is_pk:
        table_pk_set.add(col_name)

    allowed_values = ""
    check_match = re.search(r"CHECK\s*\((.*?)\)", col_def, re.IGNORECASE)
    if check_match:
        allowed_values = check_match.group(1).replace("'", "").strip()

    default_val = ""
    default_match = re.search(r"\bDEFAULT\b\s+([^\s,]+)", col_def, re.IGNORECASE)
    if default_match:
        default_val = f"Mặc định: {default_match.group(1).strip()}"

    ref_note = ""
    ref_match = re.search(r"REFERENCES\s+([^\s\(]+)\s*\(\s*([^)]+)\s*\)", col_def, re.IGNORECASE)
    if ref_match:
        ref_table = clean_identifier(ref_match.group(1))
        ref_col = clean_identifier(ref_match.group(2))
        ref_note = f"FK→{ref_table}({ref_col})"

    return {
        "col_name": col_name,
        "col_type": col_type,
        "length": length,
        "is_required": is_required,
        "is_pk": is_pk,
        "allowed_values": allowed_values,
        "ghi_chu": "; ".join(p for p in [default_val, ref_note] if p)
    }


def parse_sql_file(filepath):
    print(f"\n{'='*60}")
    print(f"ĐANG PHÂN TÍCH FILE: {filepath}")
    print('='*60)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    statements = content.split(';')
    print(f"→ Tổng số câu lệnh sau khi tách bằng ';': {len(statements)}")

    tables_found = 0
    for idx, stmt in enumerate(statements):
        stmt = stmt.strip()
        if not stmt:
            continue

        match = re.search(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"\[\]a-zA-Z0-9_.]+)\s*\((.*)\)",
            stmt,
            re.IGNORECASE | re.DOTALL
        )
        if not match:
            continue

        tables_found += 1
        table_name_raw = match.group(1)
        table_name = clean_identifier(table_name_raw)
        body = match.group(2)

        print(f"\n▶ BẢNG [{tables_found}]: {table_name}")
        print(f"  Raw name: '{table_name_raw}'")

        col_definitions = split_columns(body)
        print(f"  Tổng mệnh đề cột (trước lọc): {len(col_definitions)}")

        table_pk_set = set()
        valid_cols = []

        for i, col_def in enumerate(col_definitions):
            col_def_stripped = col_def.strip()
            print(f"\n  --- Mệnh đề [{i+1}] ---")
            print(f"  Raw: '{col_def_stripped[:80]}'")

            field = parse_column(col_def_stripped, table_pk_set)
            if field:
                valid_cols.append(field)
                pk_marker = " ★PK" if field["is_pk"] else ""
                print(f"  ✅ Cột: {field['col_name']}{pk_marker} | Type: {field['col_type']}({field['length']}) | Bắt buộc: {field['is_required']} | Ghi chú: {field['ghi_chu'] or '[trống]'}")
            else:
                print(f"  ⏭️  Bỏ qua (ràng buộc bảng hoặc không hợp lệ)")

        # INSERT count
        insert_pattern = (
            rf"INSERT\s+INTO\s+[`\"\[]?{re.escape(table_name_raw)}[`\"\]]?"
            rf"\s*(?:\([^)]*\))?\s*VALUES"
        )
        row_count = len(re.findall(insert_pattern, content, re.IGNORECASE))

        print(f"\n  📊 TỔNG KẾT bảng {table_name}:")
        print(f"     Cột hợp lệ: {len(valid_cols)}")
        print(f"     Khóa chính: {', '.join(table_pk_set) or 'N/A'}")
        print(f"     Số bản ghi (ước tính): {row_count}")

    print(f"\n{'='*60}")
    print(f"KẾT QUẢ: Phát hiện {tables_found} bảng trong file.")
    print('='*60)


if __name__ == "__main__":
    filepath = r"d:\Technical_Schema_Cataloger\sample_database.sql"
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    parse_sql_file(filepath)
