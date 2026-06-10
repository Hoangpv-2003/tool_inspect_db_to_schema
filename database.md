-- ============================================================
-- DB Schema Crawler — Test Database v2
-- Mô phỏng THỰC TẾ: không có COMMENT đầy đủ, tên cột viết tắt,
-- mix tiếng Anh/Việt, có FK khai báo và FK ngầm định
-- Mục đích: kiểm tra 4 mức trích xuất "Danh sách giá trị"
-- ============================================================

-- ============================================================
-- SCHEMA 1: ql_nhan_su  (Quản lý nhân sự)
-- Đặc trưng thực tế:
--   - Tên cột viết tắt: ma_cb, gt, trinh_do
--   - Một số cột COMMENT, nhiều cột không có
--   - FK khai báo chính thức và FK ngầm (không khai báo constraint)
--   - ENUM, TINYINT(1), VARCHAR làm flag
-- ============================================================
DROP DATABASE IF EXISTS ql_nhan_su;
CREATE DATABASE ql_nhan_su CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ql_nhan_su;

-- Bảng danh mục: có tiền tố dm_ → heuristic detect
CREATE TABLE dm_don_vi (
    id       SMALLINT    NOT NULL AUTO_INCREMENT,
    ma       VARCHAR(20) NOT NULL,
    ten      VARCHAR(200)NOT NULL,
    cap      TINYINT     NOT NULL,
    ma_cha   VARCHAR(20),
    PRIMARY KEY (id),
    UNIQUE KEY (ma)
) ENGINE=InnoDB;

INSERT INTO dm_don_vi (ma, ten, cap, ma_cha) VALUES
('UBND'   ,'UBND Tỉnh'                   ,1, NULL),
('STNMT'  ,'Sở Tài nguyên Môi trường'    ,1, NULL),
('STC'    ,'Sở Tài chính'                ,1, NULL),
('SYT'    ,'Sở Y tế'                     ,1, NULL),
('STNMT-P1','Phòng Đất đai'              ,2,'STNMT'),
('STNMT-P2','Phòng Khoáng sản'           ,2,'STNMT'),
('STC-P1' ,'Phòng Ngân sách'             ,2,'STC');

-- Bảng danh mục: dm_ prefix, dùng làm FK target ngầm
CREATE TABLE dm_chuc_danh (
    id    TINYINT     NOT NULL AUTO_INCREMENT,
    ma    VARCHAR(10) NOT NULL,
    ten   VARCHAR(100)NOT NULL,
    bac   TINYINT,
    PRIMARY KEY (id),
    UNIQUE KEY (ma)
) ENGINE=InnoDB;

INSERT INTO dm_chuc_danh (ma, ten, bac) VALUES
('GD'  ,'Giám đốc'           ,8),
('PGD' ,'Phó Giám đốc'       ,7),
('TP'  ,'Trưởng phòng'       ,6),
('PP'  ,'Phó phòng'          ,5),
('CV'  ,'Chuyên viên'        ,4),
('NV'  ,'Nhân viên'          ,3);

-- Bảng chính: can_bo
-- - Mức 1: ENUM → gt, trinh_do  (trích xuất 100%)
-- - Mức 2: FK khai báo → don_vi_id (trích xuất từ dm_don_vi)
-- - FK ngầm không khai báo → ma_cd (không detect được bằng constraint)
-- - Mức 4: trang_thai TINYINT(1) → DISTINCT chỉ thấy 0,1 (không đủ ngữ nghĩa)
CREATE TABLE can_bo (
    id           INT         NOT NULL AUTO_INCREMENT,
    ma_cb        VARCHAR(20) NOT NULL,
    ho_ten       VARCHAR(100)NOT NULL,
    ngay_sinh    DATE,
    gt           ENUM('Nam','Nữ','Khác') NOT NULL,
    so_cccd      VARCHAR(12),
    sdt          VARCHAR(15),
    email        VARCHAR(100),
    don_vi_id    SMALLINT    NOT NULL,
    ma_cd        VARCHAR(10),              -- FK ngầm → dm_chuc_danh.ma (KHÔNG khai báo constraint)
    trinh_do     ENUM('TC','CD','DH','ThS','TS') NOT NULL COMMENT 'TC=Trung cấp CD=Cao đẳng DH=Đại học ThS=Thạc sĩ TS=Tiến sĩ',
    chuyen_nganh VARCHAR(200),
    ngay_vao     DATE,
    trang_thai   TINYINT(1)  NOT NULL DEFAULT 1,  -- 0=Nghỉ 1=Đang làm (không comment)
    luong_cb     DECIMAL(12,2),
    updated_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY (ma_cb),
    CONSTRAINT fk_cb_dv FOREIGN KEY (don_vi_id) REFERENCES dm_don_vi(id)
    -- KHÔNG khai báo FK cho ma_cd dù thực tế nó ref dm_chuc_danh.ma
) ENGINE=InnoDB;

INSERT INTO can_bo (ma_cb,ho_ten,ngay_sinh,gt,so_cccd,sdt,email,don_vi_id,ma_cd,trinh_do,chuyen_nganh,ngay_vao,trang_thai,luong_cb) VALUES
('CB001','Nguyễn Văn An' ,'1975-03-12','Nam','038075003124','0912345678','an@gmail.com'  ,2,'GD' ,'ThS','Quản lý đất đai','2000-08-01',1,15000000),
('CB002','Trần Thị Bình' ,'1980-07-25','Nữ' ,'038080007256','0923456789','binh@gmail.com',2,'PGD','TS' ,'Môi trường'     ,'2005-06-15',1,14000000),
('CB003','Lê Văn Cường'  ,'1985-11-08','Nam','038085011342','0934567890','cuong@gmail.com',5,'TP' ,'DH' ,'Địa chính'      ,'2008-09-01',1,12000000),
('CB004','Phạm Thị Dung' ,'1990-02-14','Nữ' ,'038090002198','0945678901','dung@gmail.com' ,5,'CV' ,'DH' ,'Luật đất đai'   ,'2012-07-01',1,9000000),
('CB005','Hoàng Văn Em'  ,'1988-09-30','Nam','038088009276','0956789012','em@gmail.com'   ,6,'CV' ,'ThS','Khoáng sản'     ,'2010-01-15',0,9500000);

-- Bảng log: không có COMMENT, tên cột viết tắt
-- - Mức 1: ENUM → lvl
-- - Không có updated_at
CREATE TABLE sys_log (
    id          BIGINT      NOT NULL AUTO_INCREMENT,
    lvl         ENUM('DEBUG','INFO','WARN','ERROR','FATAL') NOT NULL,
    module_name VARCHAR(50) NOT NULL,
    msg         TEXT        NOT NULL,
    ip          VARCHAR(45),
    uid         INT,                    -- FK ngầm → can_bo.id (không khai báo)
    ts          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

INSERT INTO sys_log (lvl,module_name,msg,ip,uid) VALUES
('INFO' ,'AUTH' ,'Login OK'         ,'192.168.1.10',1),
('WARN' ,'EXPORT','Export >50k rows','192.168.1.15',2),
('ERROR','DB'   ,'Connection timeout','10.0.0.1'   ,NULL),
('INFO' ,'CRAWL','Schema crawl done','127.0.0.1'   ,1);

-- ============================================================
-- SCHEMA 2: ql_dat_dai  (Quản lý đất đai)
-- Đặc trưng thực tế:
--   - Mix tên tiếng Anh/Việt
--   - Có CHECK constraint (MySQL 8.0+) → Mức 3
--   - Bảng staging không có PK, không có FK
--   - Tên cột không rõ nghĩa: val1, cd, sts
-- ============================================================
DROP DATABASE IF EXISTS ql_dat_dai;
CREATE DATABASE ql_dat_dai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ql_dat_dai;

-- Bảng danh mục: KHÔNG có tiền tố dm_ → khó detect heuristic
CREATE TABLE loai_dat (
    code     VARCHAR(10) NOT NULL,
    name     VARCHAR(100)NOT NULL,
    group_id TINYINT     NOT NULL,  -- 1=Nông nghiệp 2=Phi NN 3=Chưa dùng (không khai báo)
    PRIMARY KEY (code)
) ENGINE=InnoDB;

INSERT INTO loai_dat (code, name, group_id) VALUES
('LUA','Đất trồng lúa'         ,1),
('CLN','Đất cây lâu năm'       ,1),
('ODT','Đất ở đô thị'          ,2),
('ONT','Đất ở nông thôn'       ,2),
('TMD','Đất thương mại DV'     ,2),
('SKK','Đất đồi núi chưa dùng' ,3);

-- Bảng chính: pha trộn tên Anh-Việt, có CHECK constraint
-- - Mức 1: không có ENUM
-- - Mức 3: CHECK constraint → status, transaction_type
-- - FK khai báo → land_code (từ loai_dat)
-- - Không có updated_at
CREATE TABLE land_transaction (
    id               BIGINT      NOT NULL AUTO_INCREMENT,
    area_code        CHAR(6)     NOT NULL,           -- mã DVHC, không có FK constraint
    land_code        VARCHAR(10) NOT NULL,
    dien_tich        FLOAT       NOT NULL,
    gia_gd           BIGINT      NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    status           TINYINT     NOT NULL DEFAULT 1
        CHECK (status IN (0, 1, 2)),                -- 0=Hủy 1=Chờ 2=Hoàn thành (CHECK constraint)
    ngay_gd          DATE        NOT NULL,
    ghi_chu          TEXT,
    created_by       VARCHAR(50),
    created_at       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_lt_land FOREIGN KEY (land_code) REFERENCES loai_dat(code)
) ENGINE=InnoDB;

INSERT INTO land_transaction (area_code,land_code,dien_tich,gia_gd,transaction_type,status,ngay_gd,created_by) VALUES
('420101','ODT',120.5,1800000000,'Mua bán'       ,2,'2024-03-15','admin'),
('420101','TMD',200.0,6000000000,'Mua bán'       ,2,'2024-05-10','admin'),
('420102','ODT',150.0,2100000000,'Chuyển nhượng' ,1,'2024-06-01','user1'),
('420301','ONT',300.0,1200000000,'Tặng cho'      ,0,'2024-06-15','user2'),
('420302','LUA',5000., 1500000000,'Chuyển nhượng',2,'2024-01-15','admin');

-- Bảng giá đất: CHECK constraint trên nhiều cột
CREATE TABLE bang_gia (
    ma_vung     CHAR(6)      NOT NULL,
    land_code   VARCHAR(10)  NOT NULL,
    nam         SMALLINT     NOT NULL,
    gia_min     BIGINT       NOT NULL CHECK (gia_min > 0),
    gia_max     BIGINT       NOT NULL CHECK (gia_max > 0),
    he_so       DECIMAL(4,2) NOT NULL DEFAULT 1.00
        CHECK (he_so BETWEEN 0.50 AND 3.00),
    hieu_luc    DATE         NOT NULL,
    het_hieu_luc DATE,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (ma_vung, land_code, nam),
    CONSTRAINT fk_bg_land FOREIGN KEY (land_code) REFERENCES loai_dat(code)
) ENGINE=InnoDB;

INSERT INTO bang_gia VALUES
('420101','ODT',2024, 5000000,25000000,1.00,'2024-01-01',NULL,NOW()),
('420101','TMD',2024, 8000000,40000000,1.20,'2024-01-01',NULL,NOW()),
('420302','LUA',2024,  600000, 2500000,0.80,'2024-01-01',NULL,NOW()),
('420301','ONT',2024, 1500000, 8000000,0.90,'2024-01-01',NULL,NOW());

-- Bảng staging: không PK, không FK, không COMMENT
-- tên cột hoàn toàn không rõ nghĩa → tool không thể tự sinh được gì nhiều
CREATE TABLE stg_import_raw (
    src      VARCHAR(50),
    sts      TINYINT,      -- status: 0=pending 1=ok 2=error (không comment, không constraint)
    val1     VARCHAR(500),
    val2     VARCHAR(500),
    val3     VARCHAR(500),
    cd       VARCHAR(20),  -- mã gì đó (không rõ)
    ts_in    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO stg_import_raw (src,sts,val1,val2,val3,cd) VALUES
('FILE_A',0,'420101','ODT','2024-03-15','TXN001'),
('FILE_A',1,'420102','LUA','2024-04-01','TXN002'),
('FILE_B',2,'ERR'   ,NULL ,NULL        ,NULL),
('FILE_B',0,'420301','ONT','2024-05-10','TXN003');

-- ============================================================
-- VERIFY
-- ============================================================
SELECT
    t.TABLE_SCHEMA  AS `Schema`,
    t.TABLE_NAME    AS `Bảng`,
    t.TABLE_COMMENT AS `Comment`,
    COUNT(c.COLUMN_NAME) AS `Số cột`
FROM information_schema.TABLES t
JOIN information_schema.COLUMNS c
    ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
    AND c.TABLE_NAME  = t.TABLE_NAME
WHERE t.TABLE_SCHEMA IN ('ql_nhan_su','ql_dat_dai')
  AND t.TABLE_TYPE = 'BASE TABLE'
GROUP BY t.TABLE_SCHEMA, t.TABLE_NAME, t.TABLE_COMMENT
ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME;
