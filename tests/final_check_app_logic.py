from technical_schema_cataloger.connector.sqlserver import SQLServerConnector
from technical_schema_cataloger.config.schema import DBConfig

config = DBConfig(
    alias="CongThuongHNDb",
    db_type="sqlserver",
    host="192.168.10.158",
    port=1433,
    user="user_01",
    password="ltlt2026",
    database="CongThuongHNDbContext"
)

def check_20_random_tables():
    conn = SQLServerConnector(config)
    try:
        conn.connect()
        # Danh sach 20 bang ngau nhien tu danh sach cua ban
        tables = [
            "dbo.CCN_CumCongNghiep", "dbo.CCN_GiayPhepSanXuat", "dbo.dn_DoanhNghiep", 
            "dbo.dm_Unit", "dbo.xnk_VanBanXNK", "dbo.api_APIChiaSeDuLieu",
            "dbo.base_LogsEdit", "dbo.chht_LogAPI", "dbo.dm_Goods",
            "dbo.dn_SanPham", "dbo.nl_CuaHangXangDau", "dbo.tm_Cho",
            "dbo.tm_SieuThi", "dbo.xnk_SoLieuXNK", "dbo.dm_Xa",
            "dbo.dn_Factory", "dbo.hdsd_HuongDanSuDung", "dbo.tm_DoanhNghiepATTP",
            "dbo.tm_HopTacXaTM", "dbo.ie_ImportExport"
        ]
        
        print(f"{'TEN BANG':<40} | {'NGAY TAO (CONG)':<20} | {'NGAY SUA (SCHEMA)':<20}")
        print("-" * 85)
        
        for table in tables:
            parts = table.split('.')
            pure_table = parts[-1]
            schema = parts[0]
            
            sql = """
                SELECT create_date, modify_date 
                FROM sys.tables 
                WHERE name = ? AND schema_id = SCHEMA_ID(?)
            """
            res = conn.execute_query(sql, (pure_table, schema))
            if res:
                create = res[0]["create_date"].strftime("%Y-%m-%d")
                modify = res[0]["modify_date"].strftime("%Y-%m-%d %H:%M")
                print(f"{table:<40} | {create:<20} | {modify:<20}")
            else:
                print(f"{table:<40} | NOT FOUND")
                
        conn.disconnect()
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    check_20_random_tables()
