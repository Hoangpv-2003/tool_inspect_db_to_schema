# 🚀 Hệ thống Tự động Lập Danh mục Đặc tả Kỹ thuật CSDL

**Giải pháp chuyên dụng cho công tác Quản lý và Quy hoạch Kiến trúc Dữ liệu số.**

Hệ thống được thiết kế để hỗ trợ các cơ quan, tổ chức trong việc tự động hóa công tác lập danh mục thông tin kỹ thuật, phục vụ báo cáo cấu trúc dữ liệu và xây dựng kho đặc tả nghiệp vụ mà **không tiếp cận nội dung dữ liệu nhạy cảm**.

---

## 🛡️ Cam kết An toàn và Bảo mật Dữ liệu

Đây là ưu tiên số 1 của hệ thống khi làm việc với các cơ quan nhà nước:

- **CHỈ THU THẬP CẤU TRÚC (Metadata Only)**: Hệ thống chỉ đọc tên bảng, tên trường, kiểu dữ liệu, độ dài và các ràng buộc kỹ thuật.
- **KHÔNG TRÍCH XUẤT NỘI DUNG**: Hệ thống tuyệt đối không thực hiện các lệnh đọc dữ liệu (`SELECT *`) từ các bảng nghiệp vụ. Toàn bộ thông tin thu thập đều nằm trong các bảng quản lý hệ thống của CSDL (như `information_schema`, `ALL_TABLES`).
- **KHÔNG LƯU TRỮ TRUNG GIAN**: Toàn bộ dữ liệu trích xuất được ghi trực tiếp ra file Excel trên máy tính của người dùng, không gửi qua internet hay lưu trữ trên bất kỳ máy chủ bên thứ ba nào.

---

## ✨ Chức năng chính

- **Kiểm kê đa nền tảng**: Tương thích hoàn toàn với MySQL, PostgreSQL, SQL Server và Oracle.
- **Tự động hóa báo cáo**: Xuất đặc tả kỹ thuật ra định dạng Excel theo chuẩn tài liệu nghiệp vụ.
- **Xác định logic kỹ thuật**: Tự động nhận diện cấu trúc Khóa chính, Khóa ngoại và các quy tắc kiểm soát dữ liệu.
- **Giao diện thuần Việt**: Thao tác đơn giản, phù hợp với cán bộ nghiệp vụ và quản lý.

---

## 📖 Hướng dẫn sử dụng nhanh

### Bước 1: Khởi tạo hệ thống

Tìm và chạy file: **`Lap_Danh_Muc_Dac_Ta.bat`** (Click đúp chuột).
*Lưu ý: Hệ thống sẽ tự động kiểm tra và cấu hình môi trường trong lần đầu sử dụng.*

### Bước 2: Thiết lập kết nối

1. Tại menu, chọn **[1] Cài đặt kết nối**.
2. Nhập các thông số kỹ thuật của CSDL (Host, Port, User, Password, DB Name) do bộ phận kỹ thuật cung cấp.
3. Nhấn **[0]** để xác nhận và quay lại.

### Bước 3: Lập danh mục đặc tả

1. Chọn **[2] Chạy hệ thống**.
2. Hệ thống sẽ thực hiện quét cấu trúc kỹ thuật (Cam kết không chạm vào dữ liệu nghiệp vụ).
3. Kết thúc, chọn **[1]** để mở thư mục kết quả. File báo cáo: **`data_catalog.xlsx`**.

---

## ⚠️ Lưu ý sử dụng

- **Quyền truy cập**: Chỉ cần quyền `READ-ONLY` trên các bảng hệ thống (Metadata queries).
- **Trạng thái file**: Vui lòng **ĐÓNG FILE EXCEL** báo cáo trước khi ra lệnh trích xuất mới.
- **Bảo mật mật khẩu**: Mật khẩu được lưu cục bộ dưới dạng mã hóa cơ bản để phục vụ kết nối, vui lòng không chia sẻ thư mục công cụ cho người không có thẩm quyền.

---

*Được phát triển phục vụ công tác Chuyển đổi số và Quản trị dữ liệu.*
