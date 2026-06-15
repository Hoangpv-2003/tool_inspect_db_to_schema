import os
import sys
import yaml
import time
import subprocess
from pathlib import Path
from colorama import init, Fore, Style

# Khởi tạo màu sắc cho terminal
init(autoreset=True)

CONFIG_PATH = "config/connections.yaml"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}{title.center(60)}")
    print(f"{Fore.CYAN}{'='*60}\n")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"databases": [], "output_dir": "./output", "llm": {"mode": "mock"}}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if data else {"databases": [], "output_dir": "./output", "llm": {"mode": "mock"}}
    except:
        return {"databases": [], "output_dir": "./output", "llm": {"mode": "mock"}}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

def setup_menu():
    while True:
        clear_screen()
        print_header("CẤU HÌNH KẾT NỐI DATABASE")
        config = load_config()
        
        print(f"{Fore.YELLOW}Danh sách kết nối với database hiện có:")
        dbs = config.get("databases", [])
        if not dbs:
            print("  (Trống)")
        else:
            for i, db in enumerate(dbs, 1):
                print(f"  {i}. {db.get('alias')} ({db.get('db_type')} @ {db.get('host')})")
        
        print(f"\n{Fore.GREEN}[1] Thêm kết nối mới")
        print(f"{Fore.RED}[2] Xóa kết nối với với database cũ")
        print(f"{Fore.WHITE}[0] Trở lại menu chính")
        
        choice = input(f"\nChọn chức năng: ").strip()
        
        if choice == '1':
            print(f"\n{Fore.CYAN}--- Nhập thông tin kết nối ---")
            alias = input("Tên gợi nhớ (VD: db_nhan_su): ").strip()
            print(f"\nChọn loại Database:")
            print(f"  [1] MySQL / MariaDB")
            print(f"  [2] PostgreSQL")
            print(f"  [3] Microsoft SQL Server")
            print(f"  [4] Oracle")
            
            db_choice = input("Nhập số (1-4): ").strip()
            db_map = {"1": "mysql", "2": "postgresql", "3": "sqlserver", "4": "oracle"}
            db_type = db_map.get(db_choice, "mysql") # Mặc định là mysql nếu nhập sai
            
            print(f"-> Đã chọn: {Fore.YELLOW}{db_type.upper()}")
            host = input("Địa chỉ máy chủ (Host): ").strip()
            port = input("Cổng (Port - mặc định tùy loại DB): ").strip()
            user = input("Tên đăng nhập: ").strip()
            pw = input("Mật khẩu: ").strip()
            db_name = input("Tên Database / Service Name: ").strip()
            
            # Default ports
            if not port:
                if db_type == "mysql": port = 3306
                elif db_type == "postgresql": port = 5432
                elif db_type == "sqlserver": port = 1433
                elif db_type == "oracle": port = 1521
                else: port = 0
            
            new_db = {
                "alias": alias,
                "db_type": db_type,
                "host": host,
                "port": int(port),
                "user": user,
                "password": pw,
                "database": db_name,
                "charset": "utf8mb4"
            }
            if "databases" not in config: config["databases"] = []
            config["databases"].append(new_db)
            save_config(config)
            print(f"\n{Fore.GREEN}Lưu thành công!")
            time.sleep(1)
            
        elif choice == '2':
            confirm = input("Bạn có chắc chắn muốn xóa hết? (y/n): ")
            if confirm.lower() == 'y':
                config["databases"] = []
                save_config(config)
                print(f"{Fore.GREEN}Đã xóa sạch!")
                time.sleep(1)
        elif choice == '0':
            break

def run_extract_menu():
    clear_screen()
    print_header("ĐANG CHẠY TRÍCH XUẤT CẤU TRÚC DATABASE")
    
    config = load_config()
    if not config.get("databases"):
        print(f"{Fore.RED}Lỗi: Chưa có database nào được cấu hình. Hãy vào phần Setup trước.")
        input(f"\n{Fore.YELLOW}Bấm phím bất kỳ để quay lại...")
        return

    output_dir = config.get("output_dir", "./output")
    output_file = Path(output_dir) / "data_catalog.xlsx"

    # Kiểm tra xem file có đang mở không (đề phòng lỗi Permission Denied sớm)
    if output_file.exists():
        try:
            with open(output_file, 'a'):
                pass
        except IOError:
            print(f"{Fore.RED}LỖI NGHIÊM TRỌNG: File '{output_file}' đang bị mở bởi một chương trình khác (như Excel).")
            print(f"{Fore.YELLOW}Vui lòng ĐÓNG FILE EXCEL này trước khi chạy công cụ.")
            input(f"\n{Fore.YELLOW}Bấm phím bất kỳ để quay lại...")
            return

    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        
        # Thêm cờ bufsize=1 để đọc log dòng theo dòng ngay lập tức
        process = subprocess.Popen(
            [sys.executable, "-m", "technical_schema_cataloger.main", "--config", CONFIG_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            env=env,
            bufsize=1
        )
        
        # Đọc output liên tục để tránh nghẽn buffer và treo
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                clean_line = line.strip()
                if "[INFO]" in clean_line:
                    print(f"{Fore.WHITE}{clean_line}")
                elif "[WARNING]" in clean_line:
                    print(f"{Fore.YELLOW}{clean_line}")
                elif "[ERROR]" in clean_line:
                    print(f"{Fore.RED}{clean_line}")
                else:
                    print(clean_line)
            
        process.wait()
        
        if process.returncode == 0:
            print(f"\n{Fore.GREEN}{'='*60}")
            print(f"{Fore.GREEN}HOÀN THÀNH XUẤT SẮC!")
            print(f"{Fore.GREEN}{'='*60}")
        else:
            print(f"\n{Fore.RED}Quá trình chạy có lỗi xảy ra (Mã lỗi: {process.returncode}).")
        
    except Exception as e:
        print(f"{Fore.RED}Lỗi hệ thống khi chạy hệ thống: {e}")
    
    input(f"\n{Fore.YELLOW}Bấm phím bất kỳ để tiếp tục...")
    
    # Màn hình sau khi chạy xong
    clear_screen()
    print_header("KẾT QUẢ TRÍCH XUẤT")
    
    output_dir = os.path.abspath(config.get("output_dir", "./output"))
    
    print(f"{Fore.WHITE}Các file báo cáo Excel đã được tạo tại:")
    print(f"{Fore.CYAN}{Style.BRIGHT}{output_dir}")
    print(f"\n{Fore.YELLOW}Gợi ý: Mở thư mục này để xem file 'data_catalog.xlsx'")
    
    print(f"\n{Fore.GREEN}[1] Mở thư mục chứa file ngay bây giờ")
    print(f"{Fore.WHITE}[0] Trở về menu chính")
    
    while True:
        choice = input(f"\nChọn: ").strip()
        if choice == '1':
            try:
                if os.name == 'nt':
                    os.startfile(output_dir)
                else:
                    subprocess.run(['open', output_dir])
            except:
                print(f"{Fore.RED}Không thể tự động mở thư mục. Hãy vào manually: {output_dir}")
        elif choice == '0':
            break

def run_sql_file_menu():
    clear_screen()
    print_header("TRÍCH XUẤT TỪ FILE SQL (.sql)")
    
    print(f"{Fore.WHITE}Vui lòng nhập đường dẫn đầy đủ đến file .sql của bạn.")
    print(f"{Fore.YELLOW}Gợi ý: Bạn có thể kéo thả file vào cửa sổ này để lấy đường dẫn.")
    
    file_path = input(f"\nĐường dẫn file: ").strip().strip('"')
    
    if not os.path.exists(file_path):
        print(f"{Fore.RED}Lỗi: Không tìm thấy file tại đường dẫn đã nhập.")
        input(f"\n{Fore.YELLOW}Bấm phím bất kỳ để quay lại...")
        return

    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        
        process = subprocess.Popen(
            [sys.executable, "-m", "technical_schema_cataloger.main", "--config", CONFIG_PATH, "--sql-file", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            env=env,
            bufsize=1
        )
        
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line.strip())
            
        process.wait()
        
        if process.returncode == 0:
            print(f"\n{Fore.GREEN}HOÀN THÀNH!")
        else:
            print(f"\n{Fore.RED}Có lỗi khi xử lý file.")
        
    except Exception as e:
        print(f"{Fore.RED}Lỗi hệ thống: {e}")
    
    input(f"\n{Fore.YELLOW}Bấm phím bất kỳ để tiếp tục...")
    
    # Màn hình kết quả
    config = load_config()
    output_dir = os.path.abspath(config.get("output_dir", "./output"))
    clear_screen()
    print_header("KẾT QUẢ TRÍCH XUẤT")
    print(f"{Fore.WHITE}Báo cáo đã được tạo tại: {Fore.CYAN}{output_dir}")
    print(f"\n{Fore.GREEN}[1] Mở thư mục kết quả")
    print(f"{Fore.WHITE}[0] Trở về menu chính")
    
    while True:
        choice = input(f"\nChọn: ").strip()
        if choice == '1':
            try:
                if os.name == 'nt': os.startfile(output_dir)
                else: subprocess.run(['open', output_dir])
            except: pass
        elif choice == '0':
            break

def main_menu():
    while True:
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.WHITE}{Style.BRIGHT}    HỆ THỐNG TỰ ĐỘNG LẬP DANH MỤC ĐẶC TẢ KỸ THUẬT CSDL")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"\nChào bạn! Đây là giải pháp an toàn để trích xuất cấu trúc Database.")
        print(f"{Fore.YELLOW}Cam kết: Chỉ thu thập Schema kỹ thuật - KHÔNG lấy dữ liệu.")
        
        print(f"\n{Fore.WHITE}{'-'*60}")
        print(f"{Fore.GREEN}  [1] CÀI ĐẶT THÔNG TIN DATABASE (Setup)")
        print(f"      (Nhập địa chỉ, tên đăng nhập, mật khẩu...)")
        
        print(f"\n{Fore.CYAN}  [2] BẮT ĐẦU TRÍCH XUẤT TỪ DATABASE (Cần kết nối)")
        print(f"      (Quét trực tiếp qua VPN, Mạng chuyên dùng...)")
        
        print(f"\n{Fore.MAGENTA}  [3] TRÍCH XUẤT TỪ FILE SQL (.sql) (Không cần kết nối)")
        print(f"      (Dành cho file Dump, file Export cấu trúc)")
        
        print(f"\n{Fore.RED}  [E] THOÁT CHƯƠNG TRÌNH")
        print(f"{Fore.WHITE}{'-'*60}")
        
        choice = input(f"\nNhập lựa chọn của bạn (1, 2, 3 hoặc E): ").strip().upper()
        
        if choice == '1':
            setup_menu()
        elif choice == '2':
            run_extract_menu()
        elif choice == '3':
            run_sql_file_menu()
        elif choice == 'E':
            print(f"\n{Fore.YELLOW}Cảm ơn bạn đã sử dụng. Hẹn gặp lại!")
            time.sleep(1)
            break
        else:
            print(f"{Fore.RED}Lựa chọn không hợp lệ, vui lòng thử lại.")
            time.sleep(1)

if __name__ == "__main__":
    main_menu()
