# DB Schema Crawler — Danh sách Task Triển khai

> Thực hiện  **tuần tự từ trên xuống** . Mỗi task có checkbox để tracking tiến độ.
>
> Ước tính thời gian dành cho developer Python có kinh nghiệm trung bình.

---

## Phase 0 — Khởi tạo dự án

> Mục tiêu: Có skeleton project chạy được, môi trường sạch.

* [ ] **0.1** Tạo thư mục theo đúng cấu trúc trong DESIGN.md
* [ ] **0.2** Khởi tạo virtual environment (`python -m venv .venv`)
* [ ] **0.3** Tạo `requirements.txt` với các dependency: `mysql-connector-python`, `pydantic`, `openpyxl`, `PyYAML`, `click`
* [ ] **0.4** Tạo `requirements-dev.txt` với: `pytest`, `pytest-mock`, `pytest-cov`
* [ ] **0.5** Tạo `pyproject.toml` với metadata dự án và cấu hình pytest
* [ ] **0.6** Tạo tất cả file `__init__.py` cho các package: `config/`, `connector/`, `crawler/`, `models/`, `exporter/`
* [ ] **0.7** Tạo file `.gitignore` (loại trừ `.venv/`, `output/`, `*.pyc`, `config/connections.yaml`)
* [ ] **0.8** Cài đặt dependencies: `pip install -r requirements.txt -r requirements-dev.txt`
* [ ] **0.9** Verify môi trường: `python -c "import mysql.connector, pydantic, openpyxl, yaml, click; print('OK')`

**Checkpoint:** `pytest tests/` chạy không có lỗi import (dù chưa có test nào).

---

## Phase 1 — Module 1: Config Loader

> Mục tiêu: Đọc và validate file YAML cấu hình kết nối.

* [ ] **1.1** Viết Pydantic model `DBConfig` trong `src/db_schema_crawler/config/schema.py`
  * Các field: `alias`, `host`, `port` (default 3306), `user`, `password`, `database`, `charset` (default utf8mb4)
* [ ] **1.2** Viết Pydantic model `AppConfig` trong cùng file
  * Các field: `output_dir` (default `"./output"`), `databases: List[DBConfig]`
* [ ] **1.3** Viết class `ConfigLoader` trong `src/db_schema_crawler/config/loader.py`
  * Method `load(path: str) -> AppConfig`
  * Raise `FileNotFoundError` nếu file không tồn tại
  * Raise `pydantic.ValidationError` nếu YAML thiếu field bắt buộc
* [ ] **1.4** Tạo file mẫu `config/connections.example.yaml` với 2 DB giả để làm template
* [ ] **1.5** Viết unit test `tests/test_config_loader.py` — 5 test cases theo DESIGN.md
* [ ] **1.6** Chạy `pytest tests/test_config_loader.py -v` → tất cả PASS

**Checkpoint:** `ConfigLoader.load("config/connections.example.yaml")` trả về `AppConfig` hợp lệ.

---

## Phase 2 — Module 2: MySQL Connector

> Mục tiêu: Kết nối MySQL an toàn, execute query, context manager.

* [ ] **2.1** Viết abstract base class `BaseConnector` trong `src/db_schema_crawler/connector/base.py`
  * Abstract methods: `connect()`, `disconnect()`, `execute_query()`
* [ ] **2.2** Viết class `MySQLConnector` trong `src/db_schema_crawler/connector/mysql.py`
  * Method `connect()`: dùng `mysql.connector.connect()`, raise `ConnectionError` nếu thất bại
  * Method `disconnect()`: đóng cursor và connection an toàn (check None trước)
  * Method `execute_query(sql, params) -> List[Dict]`: dùng `cursor(dictionary=True)`
  * Implement `__enter__` / `__exit__` (gọi `connect` / `disconnect`)
* [ ] **2.3** Viết custom exception `QueryError` trong `src/db_schema_crawler/connector/mysql.py`
* [ ] **2.4** Viết `tests/fixtures/mock_mysql_data.py`
  * Fixture `mock_db_config()` trả về `DBConfig` với thông tin giả
  * Fixture `mock_cursor_rows()` trả về list of dicts giả lập kết quả query
* [ ] **2.5** Viết unit test `tests/test_connector.py` — 5 test cases theo DESIGN.md
  * Dùng `unittest.mock.patch("mysql.connector.connect")` — không cần DB thật
* [ ] **2.6** Chạy `pytest tests/test_connector.py -v` → tất cả PASS

**Checkpoint:** Context manager `with MySQLConnector(config) as conn:` hoạt động đúng kể cả khi có exception bên trong.

---

## Phase 3 — Module 5: Data Models

> Mục tiêu: Định nghĩa cấu trúc dữ liệu chuẩn trước khi viết crawler.
>
> *(Làm trước crawler để crawler có type target rõ ràng)*

* [ ] **3.1** Viết Pydantic model `TableSchema` trong `src/db_schema_crawler/models/table_schema.py`
  * Đầy đủ 16 field theo DESIGN.md
  * Các field để trống: default `""`
  * Field `ngay_cap_nhat`: type `str | None = None`
* [ ] **3.2** Viết Pydantic model `FieldSchema` trong `src/db_schema_crawler/models/field_schema.py`
  * Đầy đủ 14 field theo DESIGN.md
  * Các field để trống: default `""`
* [ ] **3.3** Viết unit test `tests/test_models.py` — 3 test cases theo DESIGN.md
* [ ] **3.4** Chạy `pytest tests/test_models.py -v` → tất cả PASS

**Checkpoint:** `TableSchema(stt=1, ten_csdl="X", ten_bang="Y", so_truong=5, so_ban_ghi=100, khoa_dinh_danh="id")` khởi tạo không lỗi.

---

## Phase 4 — Module 3: Table Crawler

> Mục tiêu: Crawl metadata cấp bảng từ `information_schema`.

* [ ] **4.1** Viết class `TableCrawler` trong `src/db_schema_crawler/crawler/table_crawler.py`
* [ ] **4.2** Implement `_get_table_list()` — query `information_schema.TABLES`
* [ ] **4.3** Implement `_count_records(table_name)` — `COUNT(*)` thực tế
  * Wrap trong try/except, nếu lỗi trả về `-1` và log WARNING
* [ ] **4.4** Implement `_get_primary_keys(table_name)` — query `KEY_COLUMN_USAGE`
  * Join nhiều PK bằng `" + "` (ví dụ: `"MaThuaDat + MaDVHC"`)
* [ ] **4.5** Implement `_get_update_time(table_name)` — lấy `UPDATE_TIME` từ `information_schema.TABLES`
  * Nếu NULL: thử fallback `MAX(updated_at)` nếu bảng có cột tên `updated_at` / `update_time` / `modified_at`
  * Nếu vẫn không có: trả về `None`
* [ ] **4.6** Implement `crawl_all_tables()` — gọi các method trên, assemble `List[TableSchema]`
* [ ] **4.7** Bổ sung thêm mock data vào `tests/fixtures/mock_mysql_data.py` cho table crawler
* [ ] **4.8** Viết unit test `tests/test_table_crawler.py` — 6 test cases theo DESIGN.md
* [ ] **4.9** Chạy `pytest tests/test_table_crawler.py -v` → tất cả PASS

**Checkpoint:** Với mock data 3 bảng, `crawl_all_tables()` trả về list 3 `TableSchema` với đầy đủ field tự sinh.

---

## Phase 5 — Module 4: Field Crawler

> Mục tiêu: Crawl metadata từng cột, detect PK/FK, format độ dài.

* [ ] **5.1** Viết class `FieldCrawler` trong `src/db_schema_crawler/crawler/field_crawler.py`
* [ ] **5.2** Implement `_get_columns(table_name)` — query `information_schema.COLUMNS`
* [ ] **5.3** Implement `_get_fk_map(table_name)` — query `KEY_COLUMN_USAGE` lấy FK
  * Trả về `Dict[column_name, "FK"]`
* [ ] **5.4** Implement `_format_length(col: Dict) -> str` — theo bảng mapping trong DESIGN.md
  * varchar/char → `"{n} ký tự"`
  * int/bigint/tinyint → `"{n} chữ số"`
  * decimal/float/double → `"{precision},{scale}"`
  * datetime/timestamp → `"YYYY-MM-DD HH:MM:SS"`
  * date → `"YYYY-MM-DD"`
  * text/longtext/mediumtext → `"text"`
  * còn lại → type gốc
* [ ] **5.5** Implement `_resolve_key_type(col_key, col_name, fk_map) -> str`
  * `col_key == 'PRI'` và có trong fk_map → `"PK,FK"`
  * `col_key == 'PRI'` → `"PK"`
  * có trong fk_map → `"FK"`
  * còn lại → `""`
* [ ] **5.6** Implement `crawl_fields_for_table(table_name)` → `List[FieldSchema]`
* [ ] **5.7** Bổ sung mock data cho field crawler vào `tests/fixtures/mock_mysql_data.py`
* [ ] **5.8** Viết unit test `tests/test_field_crawler.py` — 8 test cases theo DESIGN.md
* [ ] **5.9** Chạy `pytest tests/test_field_crawler.py -v` → tất cả PASS

**Checkpoint:** Với mock 1 bảng có 5 cột (varchar, int, decimal, datetime, FK), `crawl_fields_for_table()` trả về đúng 5 `FieldSchema` với format chính xác.

---

## Phase 6 — Module 6: Excel Exporter

> Mục tiêu: Xuất 1 file `data_catalog.xlsx` với 2 sheet đúng format.

* [ ] **6.1** Viết abstract `BaseExporter` trong `src/db_schema_crawler/exporter/base.py`
* [ ] **6.2** Viết class `ExcelCatalogExporter` trong `src/db_schema_crawler/exporter/excel_exporter.py`
* [ ] **6.3** Implement `_apply_header_style(ws, n_cols)`:
  * Background `#1F4E79`, chữ trắng, bold, căn giữa
  * Áp dụng cho toàn bộ row 1
* [ ] **6.4** Implement `_apply_column_colors(ws, auto_cols, manual_cols, n_rows)`:
  * `auto_cols`: background `#E2EFDA`
  * `manual_cols`: background `#FFF2CC`
* [ ] **6.5** Implement `_autofit_columns(ws)`:
  * Duyệt từng cột, lấy max length của tất cả cell, set `column_dimensions[col].width`
  * Min width 10, max width 50
* [ ] **6.6** Implement `_write_tables_sheet(ws, tables)`:
  * Ghi header 16 cột
  * Ghi dữ liệu từ `List[TableSchema]`
  * Gọi `_apply_header_style`, `_apply_column_colors`, `_autofit_columns`
  * Set `freeze_panes = "A2"`
* [ ] **6.7** Implement `_write_fields_sheet(ws, fields)`:
  * Ghi header 14 cột
  * Ghi dữ liệu từ `List[FieldSchema]`
  * Áp dụng style tương tự
  * Set `freeze_panes = "A2"`
* [ ] **6.8** Implement `export(tables, fields)`:
  * Tạo `Workbook()`
  * Tạo sheet "Danh mục bảng" (tab color `#1F4E79`)
  * Tạo sheet "Danh mục trường" (tab color `#375623`)
  * Gọi `_write_tables_sheet` và `_write_fields_sheet`
  * `wb.save(output_path)`
* [ ] **6.9** Viết unit test `tests/test_exporter.py` — 11 test cases theo DESIGN.md
  * Dùng `openpyxl.load_workbook()` để đọc lại file và assert
  * Dùng `tmp_path` fixture của pytest để tạo file tạm
* [ ] **6.10** Chạy `pytest tests/test_exporter.py -v` → tất cả PASS

**Checkpoint:** Mở file `data_catalog.xlsx` bằng Excel/LibreOffice, thấy đúng 2 sheet, màu header đúng, freeze panes hoạt động.

---

## Phase 7 — Module 7: Orchestrator & CLI

> Mục tiêu: Kết nối toàn bộ pipeline, expose CLI.

* [ ] **7.1** Viết function `run(config_path: str, output_dir: str | None)` trong `src/db_schema_crawler/main.py`
  * Load config
  * Loop từng DB: connect → crawl tables → crawl fields → disconnect
  * Xử lý lỗi từng DB độc lập (try/except, log ERROR, continue)
  * Gán STT liên tục xuyên suốt các DB
  * Gọi `ExcelCatalogExporter.export()`
* [ ] **7.2** Viết CLI entry point dùng `click` trong cùng file `main.py`
  * Option `--config` (required)
  * Option `--output-dir` (optional, override config)
  * Option `--log-level` (default INFO)
* [ ] **7.3** Cấu hình `logging` với format: `%(asctime)s [%(levelname)s] %(message)s`
* [ ] **7.4** Thêm entry point vào `pyproject.toml`:
  ```toml
  [project.scripts]db-schema-crawler = "db_schema_crawler.main:cli"
  ```
* [ ] **7.5** Test thủ công với DB thật (hoặc Docker MySQL):
  ```bash
  python -m db_schema_crawler --config config/connections.yaml --log-level DEBUG
  ```
* [ ] **7.6** Verify output: mở `data_catalog.xlsx`, kiểm tra dữ liệu đúng

**Checkpoint:** Chạy CLI với 2 DB thật, file Excel sinh ra đúng, log hiển thị progress từng DB/bảng.

---

## Phase 8 — Kiểm thử tích hợp

> Mục tiêu: Đảm bảo toàn bộ pipeline hoạt động end-to-end.

* [ ] **8.1** Dựng MySQL test bằng Docker:
  ```bash
  docker run -d --name mysql-test \  -e MYSQL_ROOT_PASSWORD=test \  -e MYSQL_DATABASE=test_db \  -p 3306:3306 mysql:8.0
  ```
* [ ] **8.2** Tạo schema test: 3 bảng, mỗi bảng 5–10 cột, có PK, có FK giữa các bảng
* [ ] **8.3** Insert ~100 row dữ liệu mẫu vào mỗi bảng
* [ ] **8.4** Chạy tool với config trỏ vào DB test
* [ ] **8.5** Verify sheet "Danh mục bảng": đúng số bảng, đúng `so_ban_ghi`, đúng PK
* [ ] **8.6** Verify sheet "Danh mục trường": đúng số cột, đúng kiểu dữ liệu, đúng PK/FK
* [ ] **8.7** Test edge case: DB không có bảng nào → tool không crash, sheet trống
* [ ] **8.8** Test edge case: 1 DB lỗi credential → log ERROR, DB kia vẫn chạy bình thường
* [ ] **8.9** Test edge case: bảng có composite PK (2+ cột) → hiển thị `"col1 + col2"`
* [ ] **8.10** Chạy full test suite: `pytest --cov=src --cov-report=term-missing`
  * Target: coverage ≥ 80%

**Checkpoint:** Toàn bộ test PASS, coverage ≥ 80%, file Excel mở được và dữ liệu khớp với DB thật.

---

## Phase 9 — Hoàn thiện & Đóng gói

> Mục tiêu: Tool sẵn sàng bàn giao và sử dụng thực tế.

* [ ] **9.1** Viết `README.md` với các mục:
  * Giới thiệu tool
  * Yêu cầu hệ thống (Python 3.10+, MySQL 5.7+)
  * Hướng dẫn cài đặt (3 bước)
  * Cách cấu hình `connections.yaml`
  * Cách chạy CLI
  * Mô tả output Excel (2 sheet, màu sắc)
  * Grant quyền MySQL tối thiểu
  * FAQ (xử lý lỗi thường gặp)
* [ ] **9.2** Kiểm tra lại tất cả error message — phải rõ ràng, actionable (không phải stack trace thuần)
* [ ] **9.3** Thêm progress bar khi crawl nhiều bảng (dùng `tqdm` hoặc log đơn giản `[3/15] Đang crawl bảng users...`)
* [ ] **9.4** Test trên DB thật của dự án với nhiều bảng (>20 bảng)
* [ ] **9.5** Đo thời gian chạy — nếu >5 phút với 100 bảng thì xem xét parallel `COUNT(*)`
* [ ] **9.6** Peer review code (hoặc tự review lại toàn bộ): type hints, docstring, exception handling
* [ ] **9.7** Tạo tag `v1.0.0` trên git

**Checkpoint cuối:** Bàn giao tool cho người dùng, họ chạy được với `README.md` mà không cần hỗ trợ thêm.

---

## Tổng quan tiến độ

| Phase           | Mô tả                    | Số task           | Ước tính            |
| --------------- | -------------------------- | ------------------ | ---------------------- |
| Phase 0         | Khởi tạo dự án         | 9                  | 1–2 giờ              |
| Phase 1         | Config Loader              | 6                  | 1–2 giờ              |
| Phase 2         | MySQL Connector            | 6                  | 2–3 giờ              |
| Phase 3         | Data Models                | 4                  | 1 giờ                 |
| Phase 4         | Table Crawler              | 9                  | 3–4 giờ              |
| Phase 5         | Field Crawler              | 9                  | 3–4 giờ              |
| Phase 6         | Excel Exporter             | 10                 | 3–4 giờ              |
| Phase 7         | Orchestrator & CLI         | 6                  | 2–3 giờ              |
| Phase 8         | Kiểm thử tích hợp      | 10                 | 2–3 giờ              |
| Phase 9         | Hoàn thiện & Đóng gói | 7                  | 2–3 giờ              |
| **Tổng** |                            | **76 tasks** | **~20–29 giờ** |

---

> **Lưu ý:** Không bỏ qua Phase 8. Nhiều lỗi thực tế chỉ lộ ra khi chạy với DB thật (quyền thiếu, encoding tiếng Việt, bảng không có PK...).
>
