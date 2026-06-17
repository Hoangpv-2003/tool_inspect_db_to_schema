import yaml
import logging
import sys
import os

# Tu dong them thu muc goc vao sys.path
sys.path.append(os.getcwd())

from src.technical_schema_cataloger.connector.sqlserver import SQLServerConnector
from src.technical_schema_cataloger.config.schema import DBConfig

logging.basicConfig(level=logging.INFO)

def test_sqlserver_connection():
    # Load config to get credentials
    with open("config/connections.yaml", "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    # Target the sqlserver db
    db_config_raw = None
    for item in config_data.get("databases", []):
        if item.get("db_type") == "sqlserver":
            db_config_raw = item
            break
    
    if not db_config_raw:
        print("[FAIL] Khong tim thay cau hinh sqlserver trong config/connections.yaml")
        return

    db_config = DBConfig(**db_config_raw)
    connector = SQLServerConnector(db_config)

    print(f"\n--- DANG KIEM TRA KET NOI TOI: {db_config.database} ---")
    try:
        connector.connect()
        print("[OK] Ket noi thanh cong!")
        
        # 1. Test get_tables
        tables = connector.get_tables()
        if not tables:
            print("[WARNING] Khong tim thay bang nao trong database này.")
            return
        
        print(f"[OK] Tim thay {len(tables)} bang.")
        test_table = tables[0]["TABLE_NAME"]
        print(f"--- DANG KIEM TRA CHI TIET BANG: {test_table} ---")

        # 2. Test count_records
        count = connector.count_records(test_table)
        print(f"[OK] So luong ban ghi (uoc tinh): {count}")

        # 3. Test get_columns
        cols = connector.get_columns(test_table)
        print(f"[OK] Lay duoc {len(cols)} cot.")
        if cols:
            print(f"     Mau cot dau tien: {cols[0]['COLUMN_NAME']} ({cols[0]['DATA_TYPE']})")

        # 4. Test PK
        pks = connector.get_primary_keys(test_table)
        print(f"[OK] Primary Keys: {pks}")

        # 5. Test Update Time
        update_time = connector.get_update_time(test_table)
        print(f"[OK] Ngay cap nhat gan nhat: {update_time}")

        print("\n==> KET LUAN: LOGIC HOAT DONG CHUAN 100%!")

    except Exception as e:
        print(f"[FAIL] Co loi xay ra: {e}")
    finally:
        connector.disconnect()

if __name__ == "__main__":
    test_sqlserver_connection()
