import click
import logging
import sys
from pathlib import Path
from typing import List
from .config.loader import ConfigLoader
from .connector.mysql import MySQLConnector
from .crawler.table_crawler import TableCrawler
from .crawler.field_crawler import FieldCrawler
from .exporter.excel_exporter import ExcelCatalogExporter
from .models.table_schema import TableSchema
from .models.field_schema import FieldSchema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("db_schema_crawler")

def run(config_path: str, output_dir_override: str | None = None) -> None:
    try:
        config = ConfigLoader.load(config_path)
    except Exception as e:
        logger.error(f"Failed to load configuration file: {e}")
        sys.exit(1)

    output_dir = output_dir_override or config.output_dir
    output_path = Path(output_dir) / "data_catalog.xlsx"

    all_tables: List[TableSchema] = []
    all_fields: List[FieldSchema] = []
    global_stt_table = 1
    global_stt_field = 1

    for db_config in config.databases:
        logger.info(f"[{db_config.alias}] Starting crawl on database {db_config.database}...")
        try:
            with MySQLConnector(db_config) as conn:
                table_crawler = TableCrawler(conn, db_config)
                field_crawler = FieldCrawler(conn, db_config)

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
@click.option("--log-level", default="INFO", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), help="Logging level.")
def cli(config: str, output_dir: str | None, log_level: str) -> None:
    logger.setLevel(getattr(logging, log_level))
    run(config, output_dir)

if __name__ == "__main__":
    cli()
