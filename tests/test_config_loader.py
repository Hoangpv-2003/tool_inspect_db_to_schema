import pytest
from pydantic import ValidationError
from db_schema_crawler.config.loader import ConfigLoader

def test_load_valid_yaml(tmp_path):
    yaml_content = """
output_dir: "./output"
databases:
  - alias: "CSDL_GiaDat_HaTinh"
    host: "192.168.1.10"
    port: 3306
    user: "readonly_user"
    password: "secret"
    database: "gia_dat_ha_tinh"
    charset: "utf8mb4"
"""
    config_file = tmp_path / "connections.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")
    
    config = ConfigLoader.load(str(config_file))
    assert config.output_dir == "./output"
    assert len(config.databases) == 1
    db = config.databases[0]
    assert db.alias == "CSDL_GiaDat_HaTinh"
    assert db.host == "192.168.1.10"
    assert db.port == 3306
    assert db.user == "readonly_user"
    assert db.password == "secret"
    assert db.database == "gia_dat_ha_tinh"
    assert db.charset == "utf8mb4"

def test_load_missing_file():
    with pytest.raises(FileNotFoundError):
        ConfigLoader.load("non_existent_file.yaml")

def test_load_missing_required_field(tmp_path):
    # Missing required field 'host'
    yaml_content = """
databases:
  - alias: "CSDL_GiaDat_HaTinh"
    user: "readonly_user"
    password: "secret"
    database: "gia_dat_ha_tinh"
"""
    config_file = tmp_path / "connections.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")
    
    with pytest.raises(ValidationError):
        ConfigLoader.load(str(config_file))

def test_load_default_port(tmp_path):
    yaml_content = """
databases:
  - alias: "CSDL_DanSo"
    host: "192.168.1.20"
    user: "readonly_user"
    password: "secret"
    database: "dan_so"
"""
    config_file = tmp_path / "connections.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")
    
    config = ConfigLoader.load(str(config_file))
    assert len(config.databases) == 1
    assert config.databases[0].port == 3306
    assert config.databases[0].charset == "utf8mb4"

def test_load_multiple_dbs(tmp_path):
    yaml_content = """
output_dir: "./output"
databases:
  - alias: "DB1"
    host: "host1"
    user: "user1"
    password: "pwd"
    database: "db1"
  - alias: "DB2"
    host: "host2"
    user: "user2"
    password: "pwd"
    database: "db2"
"""
    config_file = tmp_path / "connections.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")
    
    config = ConfigLoader.load(str(config_file))
    assert len(config.databases) == 2
    assert config.databases[0].alias == "DB1"
    assert config.databases[1].alias == "DB2"
