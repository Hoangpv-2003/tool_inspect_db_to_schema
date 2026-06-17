import click
import logging
import sys
import traceback
import yaml
from pathlib import Path
from typing import List, Dict, Any
from .config.loader import ConfigLoader
from .connector.factory import ConnectorFactory
from .crawler.table_crawler import TableCrawler
from .crawler.field_crawler import FieldCrawler
from .crawler.sql_file_crawler import SQLFileCrawler
from .exporter.excel_exporter import ExcelCatalogExporter
from .models.table_schema import TableSchema
from .models.field_schema import FieldSchema
from .ai.llm_client import LLMClient

# Force UTF-8 for Windows console to avoid UnicodeEncodeError (charmap/cp1252)
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("db_schema_crawler")

def load_glossary(glossary_path: str) -> List[Dict[str, Any]]:
    path = Path(glossary_path)
    # Nếu không thấy tại đường dẫn tương đối, thử tìm tại thư mục gốc (parent của src/technical_schema_cataloger)
    if not path.exists():
        fallback_path = Path(__file__).parent.parent.parent / glossary_path
        if fallback_path.exists():
            path = fallback_path
            
    if not path.exists():
        logger.warning(f"Glossary file not found at {glossary_path}. Synonym matching will be skipped.")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data.get("glossary", [])
    except Exception as e:
        logger.error(f"Failed to load glossary from {glossary_path}: {e}")
        return []

def run(
    config_path: str,
    output_dir_override: str | None = None,
    glossary_path: str = "config/glossary.yaml",
    llm_mode: str | None = None,
    llm_url: str | None = None,
    llm_key: str | None = None,
    sql_file_path: str | None = None
) -> None:
    if sql_file_path:
        # SQL file mode: không cần file config
        class _FakeConfig:
            output_dir = './output'
        config = _FakeConfig()
    else:
        if not config_path:
            logger.error("Bạn phải cung cấp --config khi không dùng --sql-file.")
            sys.exit(1)
        try:
            config = ConfigLoader.load(config_path)
        except Exception as e:
            logger.error(f"Failed to load configuration file: {e}")
            sys.exit(1)

    # Overwrite LLM configurations if specified by CLI options
    if llm_mode:
        config.llm.mode = llm_mode
    if llm_url:
        config.llm.local_url = llm_url
    if llm_key:
        config.llm.api_key = llm_key

    output_dir = output_dir_override or config.output_dir
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Load Business Glossary dictionary
    glossary = load_glossary(glossary_path)
    logger.info(f"Loaded glossary file from {glossary_path} with {len(glossary)} terms.")

    if sql_file_path:
        # SQL file mode: export based on SQL filename
        sql_name = Path(sql_file_path).stem
        output_path = Path(output_dir) / f"data_catalog_{sql_name}.xlsx"
        
        logger.info(f"Starting extraction from SQL file: {sql_file_path}")
        try:
            crawler = SQLFileCrawler(sql_file_path, glossary=glossary)
            tables, fields = crawler.parse()
            
            for idx, table in enumerate(tables, 1):
                table.stt = idx
            for idx, field in enumerate(fields, 1):
                field.stt = idx
                
            exporter = ExcelCatalogExporter(str(output_path))
            exporter.export(tables, fields)
            logger.info(f"Data catalog successfully exported to {output_path}")
        except Exception as e:
            logger.error(f"Failed to parse SQL file: {e}")
            logger.error(traceback.format_exc())
    else:
        # DB connection mode: khởi tạo LLMClient
        llm_client = LLMClient(config.llm)
        logger.info(f"Initialized LLM Client with mode: {config.llm.mode}")
        
        for db_config in config.databases:
            logger.info(f"[{db_config.alias}] Starting crawl on database {db_config.database}...")
            db_tables: List[TableSchema] = []
            db_fields: List[FieldSchema] = []
            stt_table = 1
            stt_field = 1
            
            try:
                output_path = Path(output_dir) / f"data_catalog_{db_config.alias}.xlsx"
                
                with ConnectorFactory.get_connector(db_config) as conn:
                    table_crawler = TableCrawler(conn, db_config)
                    field_crawler = FieldCrawler(
                        connector=conn,
                        db_config=db_config,
                        llm_client=llm_client,
                        glossary=glossary
                    )

                    tables = table_crawler.crawl_all_tables()
                    logger.info(f"[{db_config.alias}] Found {len(tables)} tables.")
                    
                    for table in tables:
                        table.stt = stt_table
                        stt_table += 1
                        
                        logger.info(f"[{db_config.alias}] Crawling fields for table {table.ten_bang}...")
                        fields = field_crawler.crawl_fields_for_table(table.ten_bang)
                        
                        for field in fields:
                            field.stt = stt_field
                            stt_field += 1
                        db_fields.extend(fields)
                        db_tables.extend([table])
                
                if db_tables:
                    exporter = ExcelCatalogExporter(str(output_path))
                    exporter.export(db_tables, db_fields)
                    logger.info(f"[{db_config.alias}] Data catalog successfully exported to {output_path}")
                else:
                    logger.warning(f"[{db_config.alias}] No tables found, skipping export.")
                    
            except Exception as e:
                logger.error(f"[{db_config.alias}] Failed to crawl database: {e}. Skipping database.")
                logger.error(traceback.format_exc())
                continue

@click.command()
@click.option("--config", required=False, default=None, type=click.Path(), help="Path to connections.yaml configuration file (không cần khi dùng --sql-file).")
@click.option("--output-dir", type=click.Path(), default=None, help="Override output directory.")
@click.option("--glossary", default="config/glossary.yaml", type=click.Path(), help="Path to glossary.yaml configuration file.")
@click.option("--llm-mode", type=click.Choice(["mock", "local", "api"]), default=None, help="Override LLM mode (mock, local, api).")
@click.option("--llm-url", type=str, default=None, help="Override local LLM endpoint URL.")
@click.option("--llm-key", type=str, default=None, help="Override remote LLM API key.")
@click.option("--sql-file", type=click.Path(exists=True), help="Path to a SQL file to extract metadata from directly.")
@click.option("--log-level", default="INFO", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), help="Logging level.")
def cli(
    config: str,
    output_dir: str | None,
    glossary: str,
    llm_mode: str | None,
    llm_url: str | None,
    llm_key: str | None,
    sql_file: str | None,
    log_level: str
) -> None:
    logger.setLevel(getattr(logging, log_level))
    run(
        config_path=config,
        output_dir_override=output_dir,
        glossary_path=glossary,
        llm_mode=llm_mode,
        llm_url=llm_url,
        llm_key=llm_key,
        sql_file_path=sql_file
    )

if __name__ == "__main__":
    cli()
