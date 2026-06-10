import pytest
from unittest.mock import MagicMock
from db_schema_crawler.config.schema import DBConfig, LLMConfig
from db_schema_crawler.ai.llm_client import LLMClient
from db_schema_crawler.crawler.field_crawler import FieldCrawler

@pytest.fixture
def mock_db_config():
    return DBConfig(
        alias="test_db",
        host="localhost",
        port=3306,
        user="test_user",
        password="password",
        database="test_db"
    )

@pytest.fixture
def sample_glossary():
    return [
        {
            "term": "Giới tính",
            "synonyms": ["gioi_tinh", "gender", "sex", "sex_code", "ma_gt", "gt"]
        },
        {
            "term": "Họ và tên",
            "synonyms": ["ho_ten", "fullname", "full_name", "customer_name"]
        },
        {
            "term": "Trạng thái",
            "synonyms": ["trang_thai", "status", "state"]
        }
    ]

def test_resolve_glossary_mapping_rules(mock_db_config, sample_glossary):
    mock_conn = MagicMock()
    # Mock LLM Client
    llm_config = LLMConfig(mode="mock")
    llm_client = LLMClient(llm_config)
    
    crawler = FieldCrawler(mock_conn, mock_db_config, llm_client=llm_client, glossary=sample_glossary)
    
    # 1. Exact Synonym match
    assert crawler.resolve_glossary_mapping("gioi_tinh", "", "users") == "Giới tính"
    
    # 2. Normalized Synonym match
    assert crawler.resolve_glossary_mapping("HO_TEN", "", "users") == "Họ và tên"
    assert crawler.resolve_glossary_mapping("full-name", "", "users") == "Họ và tên"
    
    # 3. Substring match
    assert crawler.resolve_glossary_mapping("user_status", "", "users") == "Trạng thái"
    
    # 4. Fuzzy match (similarity >= 0.8)
    assert crawler.resolve_glossary_mapping("statuss", "", "users") == "Trạng thái"

def test_resolve_allowed_values_enum(mock_db_config):
    mock_conn = MagicMock()
    llm_client = MagicMock()
    crawler = FieldCrawler(mock_conn, mock_db_config, llm_client=llm_client)
    
    # Level 1: ENUM/SET parse
    res = crawler.resolve_allowed_values("gender", "enum('Nam','Nữ','Khác')", "", "users", {})
    assert res == "Nam, Nữ, Khác"

def test_resolve_allowed_values_fk(mock_db_config):
    mock_conn = MagicMock()
    fk_details = {
        "ma_don_vi": {
            "referenced_table": "don_vi",
            "referenced_column": "ma_don_vi"
        }
    }
    
    crawler = FieldCrawler(mock_conn, mock_db_config)
    res = crawler.resolve_allowed_values("ma_don_vi", "varchar(20)", "", "can_bo", fk_details)
    
    # Should map to the referenced table directly
    assert res == "Map với don_vi"

def test_resolve_allowed_values_constraints_and_auto_inc(mock_db_config):
    mock_conn = MagicMock()
    crawler = FieldCrawler(mock_conn, mock_db_config)
    
    # Auto-increment
    res = crawler.resolve_allowed_values("id", "int(11)", "", "can_bo", {}, extra="auto_increment")
    assert res == "Auto-Increment"

    # CHECK constraint status IN (0, 1, 2)
    check_clauses = ["(`status` in (0,1,2))"]
    res = crawler.resolve_allowed_values("status", "tinyint(4)", "", "land_transaction", {}, check_clauses=check_clauses)
    assert res == "0, 1, 2"

    # CHECK constraint between 0.50 and 3.00
    check_clauses = ["(`he_so` between 0.50 and 3.00)"]
    res = crawler.resolve_allowed_values("he_so", "decimal(4,2)", "", "bang_gia", {}, check_clauses=check_clauses)
    assert res == "0.50 - 3.00"

    # CHECK constraint comparison > 0
    check_clauses = ["(`gia_min` > 0)"]
    res = crawler.resolve_allowed_values("gia_min", "bigint(20)", "", "bang_gia", {}, check_clauses=check_clauses)
    assert res == "> 0"

def test_resolve_glossary_mapping_fallback(mock_db_config):
    mock_conn = MagicMock()
    crawler = FieldCrawler(mock_conn, mock_db_config)
    
    # test snake to Pascal conversion fallback
    assert crawler.resolve_glossary_mapping("ma_cb", "", "can_bo") == "MaCanBo"
    assert crawler.resolve_glossary_mapping("luong_cb", "", "can_bo") == "LuongCanBo"
    assert crawler.resolve_glossary_mapping("het_hieu_luc", "", "bang_gia") == "HetHieuLuc"
