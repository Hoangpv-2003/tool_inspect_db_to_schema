import pyodbc

conn_str = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.10.158,1433;"
    "DATABASE=CongThuongHNDbContext;"
    "UID=user_01;"
    "PWD=ltlt2026;"
    "Connect Timeout=10;"
)

def debug_final():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        table_name = "dbo.CCN_GiayPhepSanXuat"
        parts = table_name.split('.')
        pure_table = parts[-1]
        schema = parts[0]
        safe_full_name = f"[{schema}].[{pure_table}]"
        
        print(f"Testing for: {safe_full_name}")
        
        # Test 1: Only OBJECT_ID
        cursor.execute(f"SELECT OBJECT_ID('{safe_full_name}')")
        obj_id = cursor.fetchone()[0]
        print(f"  OBJECT_ID: {obj_id}")
        
        # Test 2: Only sys.dm_db_index_usage_stats
        if obj_id:
            cursor.execute("SELECT MAX(last_user_update) FROM sys.dm_db_index_usage_stats WHERE database_id = DB_ID() AND object_id = ?", (obj_id,))
            last_up = cursor.fetchone()[0]
            print(f"  Last user update: {last_up}")
        
        # Test 3: The Full COALESCE query
        sql = f"""
            SELECT 
                COALESCE(
                    (SELECT MAX(last_user_update) 
                     FROM sys.dm_db_index_usage_stats 
                     WHERE database_id = DB_ID() AND object_id = OBJECT_ID('{safe_full_name}')),
                    (SELECT modify_date FROM sys.tables WHERE name = ? AND schema_id = SCHEMA_ID(?)),
                    (SELECT create_date FROM sys.tables WHERE name = ? AND schema_id = SCHEMA_ID(?))
                ) as MAX_TIME
        """
        cursor.execute(sql, (pure_table, schema, pure_table, schema))
        res = cursor.fetchone()
        print(f"  Full Query Result: {res[0] if res else 'NONE'}")

        conn.close()
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    debug_final()
