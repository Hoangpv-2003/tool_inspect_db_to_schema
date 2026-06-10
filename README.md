# DB Schema Crawler

Công cụ tự động crawl metadata từ nhiều MySQL database và xuất ra 1 file Excel đặc tả dữ liệu (`data_catalog.xlsx`) với 2 sheet chuẩn phục vụ lưu trữ tài liệu CSDL và xây dựng Data Catalog.

## Tính năng chính

- **Crawl nhiều Database cùng lúc:** Định nghĩa nhiều kết nối CSDL trong một file cấu hình YAML duy nhất.
- **Phân tách Độc lập:** Lỗi kết nối/crawl ở một database sẽ được bỏ qua và tiếp tục thực hiện với các database khác.
- **Crawl Metadata Cấp Bảng:** Số lượng cột, số bản ghi thực tế (`COUNT(*)`), khóa định danh chính (hỗ trợ composite key), ngày cập nhật gần nhất (có fallback thông minh).
- **Crawl Metadata Cấp Trường:** Tên trường kỹ thuật, kiểu dữ liệu, định dạng/độ dài hiển thị thân thiện, khóa (PK/FK), bắt buộc (nullable).
- **Xuất Excel Chuẩn Hóa:**
  - Định dạng header xanh đậm, chữ trắng, bold.
  - Phân màu trực quan: Cột tự sinh bằng tool có màu **xanh lá nhạt**, cột cần điền thủ công bằng nghiệp vụ có màu **vàng nhạt**.
  - Freeze panes tại dòng 2 giúp cuộn dữ liệu dễ dàng.
  - Tự động thay đổi kích thước chiều rộng cột (auto-fit).

---

## Yêu cầu hệ thống

- Python `3.10` trở lên.
- MySQL `5.7` hoặc `8.0` trở lên.

---

## Hướng dẫn cài đặt

1. **Clone mã nguồn hoặc truy cập thư mục dự án:**
   ```bash
   cd Tool_inspect_db_to_schema
   ```

2. **Khởi tạo môi trường ảo (Virtual Environment):**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Cài đặt các thư viện phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Hướng dẫn cấu hình

Tạo file `config/connections.yaml` (dựa trên `config/connections.example.yaml`):

```yaml
# config/connections.yaml
output_dir: "./output"
databases:
  - alias: "CSDL_GiaDat"            # Tên hiển thị trong Excel (Tên CSDL)
    host: "localhost"
    port: 3306
    user: "readonly_user"
    password: "password123"
    database: "gia_dat_ha_tinh"
    charset: "utf8mb4"

  - alias: "CSDL_DanSo"
    host: "localhost"
    port: 3306
    user: "readonly_user"
    password: "password123"
    database: "dan_so"
```

### Phân quyền MySQL tối thiểu cho User Crawl

Để công cụ hoạt động chính xác, tài khoản MySQL cần được cấp quyền đọc `information_schema` và các bảng cần crawl:

```sql
GRANT SELECT ON information_schema.* TO 'readonly_user'@'%';
GRANT SELECT ON `gia_dat_ha_tinh`.* TO 'readonly_user'@'%';
GRANT SELECT ON `dan_so`.* TO 'readonly_user'@'%';
FLUSH PRIVILEGES;
```

---

## Hướng dẫn sử dụng CLI

Chạy tool bằng lệnh CLI sau:

```bash
python -m db_schema_crawler.main --config config/connections.yaml
```

Hoặc sau khi cài đặt package ở chế độ edit:
```bash
db-schema-crawler --config config/connections.yaml
```

### Các tham số tùy chọn:
- `--config PATH`: Đường dẫn tới file cấu hình connections.yaml (Bắt buộc).
- `--output-dir DIR`: Ghi đè thư mục chứa file Excel output (Tùy chọn).
- `--log-level LEVEL`: Cấp độ ghi nhận logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Mặc định: `INFO`.

---

## Cấu trúc file Excel Output

Thư mục output mặc định `./output` sẽ sinh ra file `data_catalog.xlsx` chứa 2 sheet:

1. **Danh mục bảng (Sheet 1 - Màu xanh lam `#1F4E79`):**
   - **Cột tự động sinh:** `STT`, `Tên CSDL`, `Tên bảng/dataset`, `Số trường`, `Số bản ghi ước tính`, `Khóa định danh chính`, `Ngày cập nhật gần nhất`.
   - **Cột điền tay (Màu vàng):** `Mô tả nội dung bảng`, `Nhóm dữ liệu/thực thể`, `Có dữ liệu cá nhân?`, `Tần suất cập nhật`, `Người quản lý DL`, `Lineage: nguồn -> đích`, `Thời hạn lưu trữ / hủy`, `Giấy phép sử dụng`, `Ghi chú`.

2. **Danh mục trường (Sheet 2 - Màu xanh lá `#375623`):**
   - **Cột tự động sinh:** `STT`, `Tên CSDL`, `Tên bảng/dataset`, `Tên trường kỹ thuật`, `Kiểu dữ liệu`, `Độ dài/Định dạng`, `Bắt buộc?`, `Khóa (PK/FK)`.
   - **Cột điền tay (Màu vàng):** `Tên trường (nghiệp vụ)`, `Danh sách giá trị cho phép`, `Định nghĩa nghiệp vụ`, `Dữ liệu cá nhân?`, `Ánh xạ Từ điển dùng chung`, `Ghi chú`.

---

## Câu hỏi thường gặp (FAQ)

### 1. Tại sao giá trị `Số bản ghi ước tính` hiển thị `-1`?
Khi tool gặp lỗi không thể thực thi lệnh `COUNT(*)` (do thiếu quyền hoặc bảng bị khóa/lỗi vật lý), tool sẽ ghi nhận log `WARNING` và gán giá trị mặc định `-1` (N/A) để tránh gián đoạn quá trình crawl.

### 2. Định dạng độ dài dữ liệu hiển thị như thế nào?
Định dạng độ dài được chuẩn hóa trực quan:
- `varchar(50)` -> `50 ký tự`
- `int(11)` -> `10 chữ số` (Numeric precision)
- `decimal(10,2)` -> `10,2`
- `datetime` -> `YYYY-MM-DD HH:MM:SS`
- `date` -> `YYYY-MM-DD`
- `text/longtext` -> `text`
