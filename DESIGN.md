# DB Schema Crawler — Tài liệu Thiết kế Kiến trúc

> **Phiên bản:** 1.0.0
>
> **Ngày:** 2026-06-09
>
> **Mục đích:** Công cụ tự động crawl metadata từ nhiều MySQL database, sinh schema/đặc tả, xuất 1 file Excel (`data_catalog.xlsx`) với 2 sheet chuẩn Data Catalog.

---

## 1. Tổng quan hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                        DB Schema Crawler                        │
│                                                                 │
│  [config.yaml / CLI args]                                       │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  Config     │───▶│  Connector   │───▶│  Schema Crawler  │   │
│  │  Loader     │    │  (MySQL)     │    │  (per DB/Table)  │   │
│  └─────────────┘    └──────────────┘    └────────┬─────────┘   │
│                                                  │             │
│                                                  ▼             │
│                                        ┌──────────────────┐    │
│                                        │  Schema Model    │    │
│                                        │  (Pydantic)      │    │
│                                        └────────┬─────────┘    │
│                                                 │              │
│                                                 ▼              │
│                                        ┌──────────────────┐    │
│                                        │  Excel Exporter  │    │
│                                        │  (data_catalog   │    │
│                                        │   .xlsx, 2sheet) │    │
│                                        └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Cấu trúc thư mục

```
db_schema_crawler/
│
├── README.md                        # Hướng dẫn sử dụng
├── DESIGN.md                        # File này
├── pyproject.toml                   # Dependency & build config
├── requirements.txt                 # Pin versions
│
├── config/
│   └── connections.example.yaml     # Template cấu hình kết nối
│
├── src/
│   └── db_schema_crawler/
│       ├── __init__.py
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── loader.py            # Module 1: Config Loader
│       │   └── schema.py            # Pydantic model cho config
│       │
│       ├── connector/
│       │   ├── __init__.py
│       │   ├── base.py              # Abstract base connector
│       │   └── mysql.py             # Module 2: MySQL Connector
│       │
│       ├── crawler/
│       │   ├── __init__.py
│       │   ├── table_crawler.py     # Module 3: Table Metadata Crawler
│       │   └── field_crawler.py     # Module 4: Field Metadata Crawler
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── table_schema.py      # Module 5: Data Model – Table
│       │   └── field_schema.py      # Module 5: Data Model – Field
│       │
│       ├── exporter/
│       │   ├── __init__.py
│       │   ├── base.py              # Abstract exporter
│       │   └── excel_exporter.py   # Module 6: Excel Exporter – 2 sheet trong 1 file
│       │
│       └── main.py                  # Entrypoint / Orchestrator
│
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   └── mock_mysql_data.py       # Dữ liệu giả cho unit test
    ├── test_config_loader.py
    ├── test_connector.py
    ├── test_table_crawler.py
    ├── test_field_crawler.py
    ├── test_models.py
    └── test_exporter.py             # Test cả 2 sheet trong 1 file
```

---

## 3. Mô tả chi tiết từng Module

---

### Module 1 — Config Loader (`config/loader.py`)

**Mục đích:** Đọc và validate file cấu hình kết nối (YAML hoặc CLI args).

#### Input

```yaml
# config/connections.yaml
output_dir: "./output"
databases:
  - alias: "CSDL_GiaDat_HaTinh"
    host: "192.168.1.10"
    port: 3306
    user: "readonly_user"
    password: "secret"
    database: "gia_dat_ha_tinh"
    charset: "utf8mb4"

  - alias: "CSDL_DanSo"
    host: "192.168.1.20"
    port: 3306
    user: "readonly_user"
    password: "secret"
    database: "dan_so"
```

#### Output

```python
AppConfig(
    output_dir="./output",
    databases=[
        DBConfig(alias="CSDL_GiaDat_HaTinh", host=..., port=3306, ...),
        DBConfig(alias="CSDL_DanSo", ...),
    ]
)
```

#### Pydantic Schema (`config/schema.py`)

```python
class DBConfig(BaseModel):
    alias: str           # Tên hiển thị trong Excel (Tên CSDL)
    host: str
    port: int = 3306
    user: str
    password: str
    database: str
    charset: str = "utf8mb4"

class AppConfig(BaseModel):
    output_dir: str = "./output"
    databases: List[DBConfig]
```

#### Lỗi có thể throw

* `FileNotFoundError`: Không tìm thấy file config
* `ValidationError`: Thiếu trường bắt buộc (Pydantic)

#### Unit test: `tests/test_config_loader.py`

| Test case                            | Mô tả                                                    |
| ------------------------------------ | ---------------------------------------------------------- |
| `test_load_valid_yaml`             | Load file YAML hợp lệ, kiểm tra parse đúng alias/host |
| `test_load_missing_file`           | Raise `FileNotFoundError`khi file không tồn tại       |
| `test_load_missing_required_field` | Raise `ValidationError`khi thiếu `host`               |
| `test_load_default_port`           | `port`mặc định là 3306 khi không khai báo          |
| `test_load_multiple_dbs`           | Parse đúng danh sách nhiều database                    |

---

### Module 2 — MySQL Connector (`connector/mysql.py`)

**Mục đích:** Quản lý connection pool đến MySQL, cung cấp context manager an toàn.

#### Interface

```python
class MySQLConnector:
    def __init__(self, config: DBConfig): ...

    def connect(self) -> None:
        """Tạo connection. Raise ConnectionError nếu thất bại."""

    def disconnect(self) -> None:
        """Đóng connection."""

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Thực thi SELECT, trả về list of dicts."""

    def __enter__(self) -> "MySQLConnector": ...
    def __exit__(self, *args) -> None: ...
```

#### Input

* `config: DBConfig` — thông tin kết nối

#### Output

* `List[Dict[str, Any]]` — kết quả query

#### Lỗi có thể throw

* `ConnectionError`: Không kết nối được (sai host/port/credential)
* `QueryError` (custom): SQL lỗi hoặc timeout

#### Unit test: `tests/test_connector.py`

| Test case                               | Mô tả                                                  |
| --------------------------------------- | -------------------------------------------------------- |
| `test_connect_success`                | Mock `mysql.connector`, kiểm tra connect được gọi |
| `test_connect_failure`                | Raise `ConnectionError`khi MySQL trả lỗi             |
| `test_execute_query_returns_rows`     | Mock cursor, kiểm tra trả về list of dicts            |
| `test_execute_empty_result`           | Query trả về `[]`không raise lỗi                   |
| `test_context_manager_closes_on_exit` | `disconnect()`được gọi dù có exception           |

---

### Module 3 — Table Metadata Crawler (`crawler/table_crawler.py`)

**Mục đích:** Crawl thông tin cấp bảng từ `information_schema.TABLES` và đếm bản ghi.

#### SQL được dùng

```sql
-- Lấy danh sách bảng + metadata cơ bản
SELECT
    TABLE_NAME,
    TABLE_COMMENT,
    CREATE_TIME,
    UPDATE_TIME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = %s
  AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;

-- Đếm số trường (từ COLUMNS)
SELECT COUNT(*) AS col_count
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s;

-- Đếm bản ghi thực tế
SELECT COUNT(*) AS row_count FROM `{database}`.`{table}`;

-- Lấy PK
SELECT COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = %s
  AND TABLE_NAME = %s
  AND CONSTRAINT_NAME = 'PRIMARY'
ORDER BY ORDINAL_POSITION;

-- Ngày cập nhật gần nhất: UPDATE_TIME từ information_schema.TABLES
```

#### Interface

```python
class TableCrawler:
    def __init__(self, connector: MySQLConnector, db_config: DBConfig): ...

    def crawl_all_tables(self) -> List[TableSchema]:
        """Crawl tất cả bảng trong DB, trả về list TableSchema."""

    def _get_table_list(self) -> List[Dict]: ...
    def _count_records(self, table_name: str) -> int: ...
    def _get_primary_keys(self, table_name: str) -> List[str]: ...
```

#### Input

* `connector: MySQLConnector` — connection đang mở
* `db_config: DBConfig` — để lấy `database`, `alias`

#### Output

* `List[TableSchema]`

#### Unit test: `tests/test_table_crawler.py`

| Test case                         | Mô tả                                                           |
| --------------------------------- | ----------------------------------------------------------------- |
| `test_crawl_returns_table_list` | Mock query, kiểm tra trả về đúng số lượng `TableSchema` |
| `test_count_records_correct`    | Mock COUNT(*), kiểm tra giá trị row_count                      |
| `test_primary_keys_joined`      | PK nhiều cột → join bằng `+`(VD:`id + code`)              |
| `test_empty_database`           | DB không có bảng → trả về `[]`không crash                |
| `test_table_without_pk`         | Bảng không có PK → trường `primary_keys`là `""`        |
| `test_update_time_none`         | `UPDATE_TIME`NULL → để trống                                |

---

### Module 4 — Field Metadata Crawler (`crawler/field_crawler.py`)

**Mục đích:** Crawl metadata từng cột từ `information_schema.COLUMNS` và `KEY_COLUMN_USAGE`.

#### SQL được dùng

```sql
-- Lấy tất cả cột của một bảng
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    NUMERIC_PRECISION,
    NUMERIC_SCALE,
    DATETIME_PRECISION,
    IS_NULLABLE,
    COLUMN_KEY,         -- 'PRI', 'MUL', 'UNI'
    COLUMN_DEFAULT,
    COLUMN_COMMENT,
    ORDINAL_POSITION
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
ORDER BY ORDINAL_POSITION;

-- Lấy FK relationships
SELECT
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = %s
  AND TABLE_NAME = %s
  AND REFERENCED_TABLE_NAME IS NOT NULL;
```

#### Logic sinh Độ dài/Định dạng

| DATA_TYPE                        | Định dạng output      |
| -------------------------------- | ------------------------ |
| `varchar`,`char`             | `{LENGTH} ký tự`     |
| `int`,`bigint`,`tinyint`   | `{PRECISION} chữ số` |
| `decimal`,`float`,`double` | `{PRECISION},{SCALE}`  |
| `datetime`,`timestamp`       | `YYYY-MM-DD HH:MM:SS`  |
| `date`                         | `YYYY-MM-DD`           |
| `text`,`longtext`            | `text`                 |
| Còn lại                        | type gốc                |

#### Interface

```python
class FieldCrawler:
    def __init__(self, connector: MySQLConnector, db_config: DBConfig): ...

    def crawl_fields_for_table(self, table_name: str) -> List[FieldSchema]:
        """Trả về danh sách FieldSchema cho 1 bảng."""

    def _get_columns(self, table_name: str) -> List[Dict]: ...
    def _get_fk_map(self, table_name: str) -> Dict[str, str]: ...
    def _format_length(self, col: Dict) -> str: ...
    def _resolve_key_type(self, col_key: str, col_name: str, fk_map: Dict) -> str: ...
```

#### Input

* `table_name: str`

#### Output

* `List[FieldSchema]`

#### Unit test: `tests/test_field_crawler.py`

| Test case                    | Mô tả                                                    |
| ---------------------------- | ---------------------------------------------------------- |
| `test_crawl_varchar_field` | VARCHAR(50) →`"50 ký tự"`, IS_NULLABLE=NO →`"Có"` |
| `test_crawl_decimal_field` | DECIMAL(10,2) →`"10,2"`                                 |
| `test_pk_detection`        | `COLUMN_KEY='PRI'`→`key_type="PK"`                    |
| `test_fk_detection`        | Có entry trong KEY_COLUMN_USAGE →`key_type="FK"`       |
| `test_pk_and_fk_combined`  | Cột vừa PK vừa FK →`"PK,FK"`                         |
| `test_nullable_mapping`    | `IS_NULLABLE='YES'`→`"Không"`,`'NO'`→`"Có"`    |
| `test_datetime_format`     | `datetime`type →`"YYYY-MM-DD HH:MM:SS"`               |
| `test_format_length_text`  | `longtext`→`"text"`                                   |

---

### Module 5 — Data Models (`models/`)

**Mục đích:** Pydantic models chuẩn hóa dữ liệu giữa các module.

#### `models/table_schema.py`

```python
class TableSchema(BaseModel):
    stt: int                          # Tự sinh (sequential)
    ten_csdl: str                     # Từ DBConfig.alias
    ten_bang: str                     # TABLE_NAME
    mo_ta: str = ""                   # Để trống (hỏi cán bộ)
    so_truong: int                    # COUNT từ COLUMNS
    so_ban_ghi: int                   # COUNT(*) thực tế
    nhom_du_lieu: str = ""            # Để trống
    co_du_lieu_ca_nhan: str = ""      # Để trống
    tan_suat_cap_nhat: str = ""       # Để trống
    khoa_dinh_danh: str               # PK columns joined
    nguoi_quan_ly: str = ""           # Để trống
    lineage: str = ""                 # Để trống
    ngay_cap_nhat: Optional[str]      # UPDATE_TIME từ information_schema
    thoi_han_luu_tru: str = ""        # Để trống
    giay_phep: str = ""               # Để trống
    ghi_chu: str = ""                 # Để trống
```

#### `models/field_schema.py`

```python
class FieldSchema(BaseModel):
    stt: int                          # Tự sinh
    ten_csdl: str                     # Từ DBConfig.alias
    ten_bang: str                     # TABLE_NAME
    ten_truong_nghiep_vu: str = ""    # Để trống (hỏi cán bộ)
    ten_truong_ky_thuat: str          # COLUMN_NAME
    kieu_du_lieu: str                 # DATA_TYPE
    do_dai_dinh_dang: str             # Tự sinh theo logic Module 4
    bat_buoc: str                     # "Có" / "Không" từ IS_NULLABLE
    khoa: str                         # "PK" / "FK" / "PK,FK" / ""
    danh_sach_gia_tri: str = ""       # Để trống
    dinh_nghia_nghiep_vu: str = ""    # Để trống
    du_lieu_ca_nhan: str = ""         # Để trống
    anh_xa: str = ""                  # Để trống
    ghi_chu: str = ""                 # Để trống
```

#### Unit test: `tests/test_models.py`

| Test case                             | Mô tả                                          |
| ------------------------------------- | ------------------------------------------------ |
| `test_table_schema_defaults`        | Các trường để trống mặc định là `""` |
| `test_field_schema_required_fields` | Thiếu `ten_truong_ky_thuat`→ ValidationError |
| `test_table_schema_serialization`   | `.model_dump()`trả đúng số key             |

---

### Module 6 — Excel Exporter (`exporter/excel_exporter.py`)

**Mục đích:** Xuất `List[TableSchema]` và `List[FieldSchema]` thành **1 file `data_catalog.xlsx`** gồm  **2 sheet** .

#### Cấu trúc file output

```
data_catalog.xlsx
├── Sheet 1: "Danh mục bảng"    ← TableSchema
└── Sheet 2: "Danh mục trường"  ← FieldSchema
```

#### Định dạng chung cho cả 2 sheet

* **Header row:** background `#1F4E79` (xanh đậm), chữ trắng, bold, căn giữa
* **Cột tự sinh:** background `#E2EFDA` (xanh lá nhạt)
* **Cột để trống** (hỏi cán bộ): background `#FFF2CC` (vàng nhạt) — gợi ý điền
* **Freeze panes** tại row 2 (header luôn hiện khi cuộn)
* **Auto-fit** column width theo nội dung
* **Tab màu:** Sheet 1 = `#1F4E79`, Sheet 2 = `#375623`

#### Sheet 1 — "Danh mục bảng"

| # | Tên cột                           | Nguồn      | Màu nền dữ liệu |
| - | ----------------------------------- | ----------- | ------------------- |
| A | STT                                 | để trống | Xanh nhạt          |
| B | Tên CSDL                           | để trống | Xanh nhạt          |
| C | Tên bảng/dataset                  | Tự sinh    | Xanh nhạt          |
| D | Mô tả nội dung bảng             | Để trống | Vàng nhạt         |
| E | Số trường                        | Tự sinh    | Xanh nhạt          |
| F | Số bản ghi ước tính            | Tự sinh    | Xanh nhạt          |
| G | Nhóm dữ liệu/thực thể          | Để trống | Vàng nhạt         |
| H | Có dữ liệu cá nhân?            | Để trống | Vàng nhạt         |
| I | Tần suất cập nhật               | Để trống | Vàng nhạt         |
| J | Khóa định danh chính            | Tự sinh    | Xanh nhạt          |
| K | Người quản lý DL (Data steward) | Để trống | Vàng nhạt         |
| L | Lineage: nguồn → đích           | Để trống | Vàng nhạt         |
| M | Ngày cập nhật gần nhất         | Tự sinh    | Xanh nhạt          |
| N | Thời hạn lưu trữ / hủy         | Để trống | Vàng nhạt         |
| O | Giấy phép sử dụng               | Để trống | Vàng nhạt         |
| P | Ghi chú                            | Để trống | Vàng nhạt         |

#### Sheet 2 — "Danh mục trường"

| # | Tên cột                       | Nguồn      | Màu nền dữ liệu |
| - | ------------------------------- | ----------- | ------------------- |
| A | STT                             | để trống | Xanh nhạt          |
| B | Tên CSDL                       | để trống | Xanh nhạt          |
| C | Tên bảng/dataset              | Tự sinh    | Xanh nhạt          |
| D | Tên trường (nghiệp vụ)     | Để trống | Vàng nhạt         |
| E | Tên trường kỹ thuật        | Tự sinh    | Xanh nhạt          |
| F | Kiểu dữ liệu                 | Tự sinh    | Xanh nhạt          |
| G | Độ dài/Định dạng          | Tự sinh    | Xanh nhạt          |
| H | Bắt buộc?                     | Tự sinh    | Xanh nhạt          |
| I | Khóa (PK/FK)                   | Tự sinh    | Xanh nhạt          |
| J | Danh sách giá trị cho phép  | tự sinh    | Vàng nhạt         |
| K | Định nghĩa nghiệp vụ       | Để trống | Vàng nhạt         |
| L | Dữ liệu cá nhân?            | Để trống | Vàng nhạt         |
| M | Ánh xạ Từ điển dùng chung | tự sinh    | Vàng nhạt         |
| N | Ghi chú                        | Để trống | Vàng nhạt         |

#### Interface

```python
class ExcelCatalogExporter:
    def __init__(self, output_path: str): ...

    def export(
        self,
        tables: List[TableSchema],
        fields: List[FieldSchema],
    ) -> None:
        """Tạo data_catalog.xlsx với 2 sheet trong 1 lần gọi."""

    def _write_tables_sheet(self, ws, tables: List[TableSchema]) -> None: ...
    def _write_fields_sheet(self, ws, fields: List[FieldSchema]) -> None: ...
    def _apply_header_style(self, ws, n_cols: int) -> None: ...
    def _apply_column_colors(self, ws, auto_cols: List[int], manual_cols: List[int], n_rows: int) -> None: ...
    def _autofit_columns(self, ws) -> None: ...
```

#### Unit test: `tests/test_exporter.py`

| Test case                            | Mô tả                                                                            |
| ------------------------------------ | ---------------------------------------------------------------------------------- |
| `test_export_creates_single_file`  | Chỉ tạo 1 file `data_catalog.xlsx`, không tạo file nào khác                |
| `test_export_has_two_sheets`       | Workbook có đúng 2 sheet tên `"Danh mục bảng"`và `"Danh mục trường"` |
| `test_tables_sheet_header_16_cols` | Sheet 1 header có đúng 16 cột, đúng tên theo thứ tự                       |
| `test_fields_sheet_header_14_cols` | Sheet 2 header có đúng 14 cột, đúng tên theo thứ tự                       |
| `test_tables_sheet_row_count`      | Số dòng dữ liệu sheet 1 = số `TableSchema`truyền vào                      |
| `test_fields_sheet_row_count`      | Số dòng dữ liệu sheet 2 = tổng số `FieldSchema`                            |
| `test_tables_auto_columns_filled`  | Cột tự sinh  không trống                                                      |
| `test_tables_manual_columns_empty` | Cột hỏi cán bộ là `""`                                                      |
| `test_fields_pk_fk_correct`        | Cột I (Khóa) đúng giá trị `"PK"`/`"FK"`/`"PK,FK"`/`""`               |
| `test_header_background_color`     | Header row =`#1F4E79`, chữ trắng                                               |
| `test_freeze_panes_row2`           | `freeze_panes`được đặt tại `A2`cho cả 2 sheet                           |

---

### Module 7 — Orchestrator / Entrypoint (`main.py`)

**Mục đích:** Điều phối toàn bộ pipeline, xử lý lỗi từng DB độc lập (1 DB lỗi không dừng toàn bộ).

#### Flow

```python
def run(config_path: str) -> None:
    config = ConfigLoader.load(config_path)

    all_tables: List[TableSchema] = []
    all_fields: List[FieldSchema] = []
    global_stt_table = 1
    global_stt_field = 1

    for db_config in config.databases:
        try:
            with MySQLConnector(db_config) as conn:
                table_crawler = TableCrawler(conn, db_config)
                field_crawler = FieldCrawler(conn, db_config)

                tables = table_crawler.crawl_all_tables()
                for table in tables:
                    table.stt = global_stt_table
                    global_stt_table += 1

                    fields = field_crawler.crawl_fields_for_table(table.ten_bang)
                    for field in fields:
                        field.stt = global_stt_field
                        global_stt_field += 1
                    all_fields.extend(fields)

                all_tables.extend(tables)

        except Exception as e:
            logger.error(f"[{db_config.alias}] Lỗi: {e}. Bỏ qua DB này.")
            continue

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ExcelCatalogExporter(output_dir / "data_catalog.xlsx").export(all_tables, all_fields)
```

#### CLI Interface

```bash
# Cách dùng
python -m db_schema_crawler --config config/connections.yaml

# Options
--config PATH     # Đường dẫn file YAML (bắt buộc)
--output-dir DIR  # Override output_dir trong YAML (tùy chọn)
--log-level LEVEL # DEBUG / INFO / WARNING (mặc định: INFO)
```

---

## 4. Dependencies

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.10"
mysql-connector-python = "^8.3"
pydantic = "^2.7"
openpyxl = "^3.1"
PyYAML = "^6.0"
click = "^8.1"           # CLI

[tool.poetry.dev-dependencies]
pytest = "^8.2"
pytest-mock = "^3.14"
pytest-cov = "^5.0"
```

---

## 5. Xử lý lỗi & Logging

| Tình huống                        | Xử lý                                           |
| ----------------------------------- | ------------------------------------------------- |
| DB không kết nối được         | Log ERROR + skip DB, tiếp tục DB khác          |
| Bảng không COUNT được          | Log WARNING,`so_ban_ghi = -1`(hiển thị "N/A") |
| `information_schema`thiếu quyền | Raise rõ ràng với hướng dẫn grant           |
| File YAML sai format                | Raise `ConfigError`ngay từ đầu               |
| Output dir không ghi được       | Raise `PermissionError`                         |

---

## 6. Phân quyền MySQL cần thiết

```sql
-- Grant tối thiểu cho readonly user
GRANT SELECT ON information_schema.* TO 'readonly_user'@'%';
GRANT SELECT ON `your_database`.* TO 'readonly_user'@'%';
FLUSH PRIVILEGES;
```

---

## 7. Output mẫu

```
output/
└── data_catalog.xlsx
    ├── Sheet "Danh mục bảng"    — N dòng (tổng tất cả bảng của tất cả DB)
    └── Sheet "Danh mục trường"  — M dòng (tổng tất cả cột của tất cả bảng)
```

---

## 8. Quy ước code

* **Python 3.10+** — dùng `match/case`, `X | Y` type hints
* **Type hints** toàn bộ, mypy strict
* **Pydantic v2** cho tất cả data models
* **`with` context manager** cho tất cả DB connection
* **Không** dùng ORM (SQLAlchemy) — chỉ raw SQL qua `mysql-connector-python`
* **Log** dùng `logging` stdlib, format: `[LEVEL] [alias] message`
* **Test** dùng `pytest` + `unittest.mock` (không cần DB thật khi test)

---

## 9. Checklist triển khai

* [ ] Tạo readonly MySQL user, grant quyền
* [ ] Sao chép `config/connections.example.yaml` thành `config/connections.yaml`
* [ ] Điền connection strings
* [ ] `pip install -r requirements.txt`
* [ ] `python -m db_schema_crawler --config config/connections.yaml`
* [ ] Mở `output/data_catalog.xlsx` — sheet "Danh mục bảng" và "Danh mục trường"
* [ ] Điền các cột màu vàng (hỏi cán bộ nghiệp vụ)
