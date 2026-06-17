from typing import Type
from ..config.schema import DBConfig
from .base import BaseConnector

class ConnectorFactory:
    @classmethod
    def get_connector(cls, config: DBConfig) -> BaseConnector:
        db_type = config.db_type.lower()
        
        if db_type == "mysql":
            from .mysql import MySQLConnector
            return MySQLConnector(config)
        elif db_type == "postgresql":
            from .postgresql import PostgreSQLConnector
            return PostgreSQLConnector(config)
        elif db_type == "sqlserver":
            from .sqlserver import SQLServerConnector
            return SQLServerConnector(config)
        elif db_type == "oracle":
            from .oracle import OracleConnector
            return OracleConnector(config)
        else:
            raise ValueError(f"Unsupported database type: {config.db_type}")

    @classmethod
    def register_connector(cls, db_type: str, connector_class: Type[BaseConnector]):
        # This method is less used now with lazy loading but kept for compatibility
        pass
