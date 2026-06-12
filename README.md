# 📘 Hướng dẫn sử dụng Máy quét Dữ liệu tự động (DB Insight Harvester)

Chào bạn! Đây là công cụ giúp các bạn **BA** và **Nghiệp vụ** tự động lập danh sách các bảng và trường dữ liệu từ hệ thống vào file Excel chỉ trong vài phút. Bạn không cần phải biết lập trình hay viết câu lệnh SQL phức tạp.

---

## 🌟 Công cụ này giúp gì cho bạn?

1.  **Lập danh mục dữ liệu cực nhanh**: Thay vì ngồi copy từng tên bảng, tên cột từ kỹ thuật, máy sẽ tự quét và điền vào Excel cho bạn.
2.  **Chính xác 100%**: Thông tin được lấy trực tiếp từ hệ thống nên không lo bị sai sót, nhầm lẫn.
3.  **Đầy đủ thông tin**: Máy tự biết cột nào là Khóa chính, cột nào bắt buộc nhập, độ dài bao nhiêu... giúp bạn làm tài liệu thiết kế nghiệp vụ cực nhàn.

---

## 🚀 3 Bước để có ngay file Excel Danh mục dữ liệu

### Bước 1: Khởi động công cụ
Bạn tìm đến thư mục của công cụ này và nhấp đúp chuột vào file:
👉 **`chay_tool.bat`** (File có biểu tượng bánh răng)

*Cửa sổ hiện lên sẽ có màu sắc và hướng dẫn bằng Tiếng Việt.*

### Bước 2: Cài đặt thông tin kết nối (Chỉ làm lần đầu)
1.  Trên màn hình, nhấn phím số **[1]** trên bàn phím.
2.  Chọn tiếp phím **[1]** để thêm database mới.
3.  Hãy nhờ các bạn kỹ thuật (Dev) cung cấp cho các thông số sau và nhập vào:
    - **Máy chủ (Host)**: Địa chỉ server.
    - **Tên đăng nhập & Mật khẩu**.
    - **Tên Database**: Tên kho dữ liệu bạn muốn quy hoạch.
4.  Sau khi báo "Lưu thành công", nhấn phím **[0]** để quay lại màn hình chính.

### Bước 3: Xuất dữ liệu ra Excel
1.  Tại màn hình chính, nhấn phím số **[2]**.
2.  Ngồi chờ máy quét (bạn sẽ thấy các dòng chữ chạy liên tục, đó là lúc máy đang làm việc).
3.  Khi máy báo **"HOÀN THÀNH XUẤT SẮC"**, bạn nhấn phím bất kỳ.
4.  Lúc này, hãy nhấn phím **[1]** để máy tự động mở thư mục chứa kết quả.
    - File bạn cần tìm là: **`data_catalog.xlsx`**.

---

## ⚠️ Những lưu ý "sống còn" để không bị lỗi

- **ĐÓNG FILE EXCEL**: Nếu bạn đang mở file `data_catalog.xlsx` để xem, hãy **ĐÓNG NÓ LẠI** trước khi bấm chạy công cụ. Nếu không, máy sẽ không thể ghi đè dữ liệu mới vào được.
- **Mật khẩu**: Khi nhập mật khẩu trên màn hình đen, có thể bạn sẽ không thấy ký tự hiện ra (để bảo mật), bạn cứ gõ đúng và nhấn Enter là được.
- **Nhờ hỗ trợ**: Nếu máy báo "Không thể kết nối", hãy kiểm tra xem bạn đã bật VPN chưa hoặc nhờ IT kiểm tra lại địa chỉ Host/Port.

---
*Chúc bạn làm việc thảnh thơi hơn với DB Insight Harvester!*
