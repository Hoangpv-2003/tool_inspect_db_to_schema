import click
import logging
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any
from .config.loader import ConfigLoader
from .connector.factory import ConnectorFactory
from .crawler.table_crawler import TableCrawler
from .crawler.field_crawler import FieldCrawler
from .exporter.excel_exporter import ExcelCatalogExporter
from .models.table_schema import TableSchema
from .models.field_schema import FieldSchema
from .ai.llm_client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("db_schema_crawler")

def load_glossary(glossary_path: str) -> List[Dict[str, Any]]:
    path = Path(glossary_path)
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
    llm_key: str | None = None
) -> None:
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
    output_path = Path(output_dir) / "data_catalog.xlsx"

    # Initialize LLM Client
    llm_client = LLMClient(config.llm)
    logger.info(f"Initialized LLM Client with mode: {config.llm.mode}")

    # Load Business Glossary dictionary
    glossary = load_glossary(glossary_path)
    logger.info(f"Loaded glossary file from {glossary_path} with {len(glossary)} terms.")

    all_tables: List[TableSchema] = []
    all_fields: List[FieldSchema] = []
    global_stt_table = 1
    global_stt_field = 1

    for db_config in config.databases:
        logger.info(f"[{db_config.alias}] Starting crawl on database {db_config.database}...")
        try:
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
                    table.stt = global_stt_table
                    global_stt_table += 1
                    
                    logger.info(f"[{db_config.alias}] Crawling fields for table {table.ten_bang}...")
                    fields = field_crawler.crawl_fields_for_table(table.ten_bang)
                    
                    for field in fields:
                        field.stt = global_stt_field
                        global_stt_field += 1
                    all_fields.extend(fields)
                    all_tables.extend([table])
        except Exception as e:
            logger.error(f"[{db_config.alias}] Failed to crawl database: {e}. Skipping database.")
            continue

    if not all_tables:
        logger.warning("No tables were successfully crawled. Exiting without writing catalog.")
        return

    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        exporter = ExcelCatalogExporter(str(output_path))
        exporter.export(all_tables, all_fields)
        logger.info(f"Data catalog successfully exported to {output_path}")
    except Exception as e:
        logger.error(f"Failed to export Excel file: {e}")
        sys.exit(1)

@click.command()
@click.option("--config", required=True, type=click.Path(exists=True), help="Path to connections.yaml configuration file.")
@click.option("--output-dir", type=click.Path(), default=None, help="Override output directory.")
@click.option("--glossary", default="config/glossary.yaml", type=click.Path(), help="Path to glossary.yaml configuration file.")
@click.option("--llm-mode", type=click.Choice(["mock", "local", "api"]), default=None, help="Override LLM mode (mock, local, api).")
@click.option("--llm-url", type=str, default=None, help="Override local LLM endpoint URL.")
@click.option("--llm-key", type=str, default=None, help="Override remote LLM API key.")
@click.option("--log-level", default="INFO", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), help="Logging level.")
def cli(
    config: str,
    output_dir: str | None,
    glossary: str,
    llm_mode: str | None,
    llm_url: str | None,
    llm_key: str | None,
    log_level: str
) -> None:
    logger.setLevel(getattr(logging, log_level))
    run(
        config_path=config,
        output_dir_override=output_dir,
        glossary_path=glossary,
        llm_mode=llm_mode,
        llm_url=llm_url,
        llm_key=llm_key
    )

if __name__ == "__main__":
    cli()
