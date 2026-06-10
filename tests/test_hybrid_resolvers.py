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
    crawler = FieldCrawler(mock_conn, mock_db_config)
    
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
    
    # Level 2: Foreign Key Lookup
    # Mock returning values: STNMT, STC, SYT
    mock_conn.execute_query.return_value = [
        {"ma_don_vi": "STNMT"},
        {"ma_don_vi": "STC"},
        {"ma_don_vi": "SYT"}
    ]
    
    crawler = FieldCrawler(mock_conn, mock_db_config)
    res = crawler.resolve_allowed_values("ma_don_vi", "varchar(20)", "", "can_bo", fk_details)
    
    assert res == "STNMT, STC, SYT"
    assert mock_conn.execute_query.call_count == 1

def test_resolve_allowed_values_distinct_scan(mock_db_config):
    mock_conn = MagicMock()
    
    # Mock row count query (Level 3 row count checks)
    # First query count (Level 3 count is <= 50,000, e.g. 5)
    # Second query distinct: returning 0, 1
    mock_conn.execute_query.side_effect = [
        [{"row_count": 5}],
        [{"trang_thai": 0}, {"trang_thai": 1}]
    ]
    
    llm_config = LLMConfig(mode="mock")
    llm_client = LLMClient(llm_config)
    
    crawler = FieldCrawler(mock_conn, mock_db_config, llm_client=llm_client)
    res = crawler.resolve_allowed_values("trang_thai", "tinyint(1)", "", "can_bo", {})
    
    # BUG FIX: mock mode does NOT call LLM for allowed values to prevent
    # "0: Nam, 1: Nữ" from being erroneously applied to every 0/1 column.
    # Raw distinct values are returned as-is when LLM mode is "mock".
    assert res == "0, 1"
    assert mock_conn.execute_query.call_count == 2
