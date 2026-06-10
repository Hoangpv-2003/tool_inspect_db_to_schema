import pytest
import sys
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from db_schema_crawler.main import cli, run

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "--config" in result.output

@patch("db_schema_crawler.main.ConfigLoader.load")
@patch("db_schema_crawler.main.MySQLConnector")
@patch("db_schema_crawler.main.TableCrawler")
@patch("db_schema_crawler.main.FieldCrawler")
@patch("db_schema_crawler.main.ExcelCatalogExporter")
def test_run_success(mock_exporter_cls, mock_field_crawler_cls, mock_table_crawler_cls, mock_conn_cls, mock_load_config, tmp_path):
    # Setup mock configuration
    mock_db = MagicMock()
    mock_db.alias = "TestDB"
    mock_db.database = "test_db"
    
    mock_config = MagicMock()
    mock_config.output_dir = "./output"
    mock_config.databases = [mock_db]
    mock_load_config.return_value = mock_config
    
    # Setup mock connector
    mock_conn = MagicMock()
    mock_conn_cls.return_value = mock_conn
    mock_conn.__enter__.return_value = mock_conn
    
    # Setup mock table crawler
    mock_table = MagicMock()
    mock_table.stt = 0
    mock_table.ten_bang = "users"
    mock_table_crawler = MagicMock()
    mock_table_crawler.crawl_all_tables.return_value = [mock_table]
    mock_table_crawler_cls.return_value = mock_table_crawler
    
    # Setup mock field crawler
    mock_field = MagicMock()
    mock_field.stt = 0
    mock_field_crawler = MagicMock()
    mock_field_crawler.crawl_fields_for_table.return_value = [mock_field]
    mock_field_crawler_cls.return_value = mock_field_crawler
    
    # Setup mock exporter
    mock_exporter = MagicMock()
    mock_exporter_cls.return_value = mock_exporter
    
    config_file = tmp_path / "config.yaml"
    config_file.touch()
    
    # Run CLI
    runner = CliRunner()
    with patch("db_schema_crawler.main.Path.mkdir") as mock_mkdir:
        result = runner.invoke(cli, ["--config", str(config_file)])
        assert result.exit_code == 0
        
    # Verify mock interactions
    mock_load_config.assert_called_once_with(str(config_file))
    mock_table_crawler_cls.assert_called_once()
    mock_field_crawler_cls.assert_called_once()
    mock_exporter.export.assert_called_once()
    
    # Verify STT assignment
    assert mock_table.stt == 1
    assert mock_field.stt == 1

@patch("db_schema_crawler.main.ConfigLoader.load")
def test_run_config_load_failure(mock_load_config, tmp_path):
    mock_load_config.side_effect = Exception("Invalid YAML")
    config_file = tmp_path / "config.yaml"
    config_file.touch()
    
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_file)])
    assert result.exit_code == 1
