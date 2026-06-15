-- DUMP CSDL MẪU - HỆ THỐNG QUẢN LÝ NHÀ THUỐC
-- Phiên bản: 1.0 (Dùng để kiểm tra khả năng trích xuất cấu trúc)

-- 1. Bảng quản lý danh mục thuốc (PostgreSQL/Oracle Style)
CREATE TABLE dm_thuoc (
    ma_thuoc VARCHAR(20) PRIMARY KEY,
    ten_thuoc VARCHAR(255) NOT NULL,
    don_vi_tinh VARCHAR(50) CHECK (don_vi_tinh IN ('Vien', 'Vi', 'Hop', 'Chai')),
    gia_ban DECIMAL(18, 2),
    trang_thai VARCHAR(1) DEFAULT 'A'
);

COMMENT ON TABLE dm_thuoc IS 'Danh mục các loại thuốc trong hệ thống';
COMMENT ON COLUMN dm_thuoc.ma_thuoc IS 'Mã định danh duy nhất của thuốc';

-- 2. Bảng quản lý kho (MySQL style - COMMENT inline)
CREATE TABLE kho_du_tru (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ma_thuoc VARCHAR(20),
    so_luong INT DEFAULT 0,
    vi_tri_kho VARCHAR(100),
    CONSTRAINT fk_thuoc FOREIGN KEY (ma_thuoc) REFERENCES dm_thuoc(ma_thuoc)
) COMMENT='Bảng lưu trữ số lượng tồn kho thực tế';

-- 3. Bảng log hệ thống
CREATE TABLE sys_log (
    log_id BIGINT PRIMARY KEY,
    thoi_gian TIMESTAMP,
    noi_dung TEXT,
    nguoi_thuc_hien VARCHAR(50)
);

-- 4. Dữ liệu thử nghiệm (Để kiểm tra tính năng đếm số bản ghi)
INSERT INTO dm_thuoc (ma_thuoc, ten_thuoc, don_vi_tinh, gia_ban) VALUES ('PANA01', 'Panadol Extra', 'Vi', 15000);
INSERT INTO dm_thuoc (ma_thuoc, ten_thuoc, don_vi_tinh, gia_ban) VALUES ('DECO02', 'Decolgen', 'Vien', 2000);
INSERT INTO dm_thuoc (ma_thuoc, ten_thuoc, don_vi_tinh, gia_ban) VALUES ('STRE03', 'Strepsils', 'Hop', 35000);

INSERT INTO kho_du_tru (ma_thuoc, so_luong, vi_tri_kho) VALUES ('PANA01', 100, 'Ke A-01');
INSERT INTO kho_du_tru (ma_thuoc, so_luong, vi_tri_kho) VALUES ('DECO02', 500, 'Ke B-05');
