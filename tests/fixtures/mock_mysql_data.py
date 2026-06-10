import pytest
from db_schema_crawler.config.schema import DBConfig

@pytest.fixture
def mock_db_config():
    return DBConfig(
        alias="MockDB",
        host="localhost",
        port=3306,
        user="test_user",
        password="test_password",
        database="test_db",
        charset="utf8mb4"
    )
