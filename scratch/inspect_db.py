import mysql.connector
import yaml
import sys

# Reconfigure stdout to use utf-8
sys.stdout.reconfigure(encoding='utf-8')

with open("config/connections.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

for db_conf in config["databases"]:
    print(f"=== Database: {db_conf['database']} ===")
    conn = mysql.connector.connect(
        host=db_conf["host"],
        port=db_conf["port"],
        user=db_conf["user"],
        password=db_conf["password"],
        database=db_conf["database"],
        charset=db_conf.get("charset", "utf8mb4")
    )
    try:
        cursor = conn.cursor(dictionary=True)
        # Get tables
        cursor.execute("SHOW TABLES")
        tables = [list(row.values())[0] for row in cursor.fetchall()]
        for table in tables:
            print(f"  Table: {table}")
            # Get columns & comments
            cursor.execute(f"SHOW FULL COLUMNS FROM `{table}`")
            cols = cursor.fetchall()
            for col in cols:
                field = col["Field"]
                ctype = col["Type"]
                comment = col["Comment"]
                key = col["Key"]
                print(f"    Column: {field} | Type: {ctype} | Key: {key} | Comment: {comment}")
            
            # Check constraints (MySQL 8.0+)
            try:
                cursor.execute("""
                    SELECT tc.CONSTRAINT_NAME, cc.CHECK_CLAUSE 
                    FROM information_schema.TABLE_CONSTRAINTS tc
                    JOIN information_schema.CHECK_CONSTRAINTS cc 
                      ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA 
                     AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
                    WHERE tc.CONSTRAINT_SCHEMA = %s AND tc.TABLE_NAME = %s AND tc.CONSTRAINT_TYPE = 'CHECK'
                """, (db_conf["database"], table))
                constraints = cursor.fetchall()
                if constraints:
                    print(f"    Check constraints for {table}:")
                    for const in constraints:
                        print(f"      {const['CONSTRAINT_NAME']}: {const['CHECK_CLAUSE']}")
            except Exception as e:
                print(f"    No check constraints or error: {e}")
            print()
    finally:
        conn.close()
