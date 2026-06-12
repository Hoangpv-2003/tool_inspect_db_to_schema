from typing import Type
from ..config.schema import DBConfig
from .base import BaseConnector
from .mysql import MySQLConnector
from .postgresql import PostgreSQLConnector
from .sqlserver import SQLServerConnector
from .oracle import OracleConnector

class ConnectorFactory:
    _connectors = {
        "mysql": MySQLConnector,
        "postgresql": PostgreSQLConnector,
        "sqlserver": SQLServerConnector,
        "oracle": OracleConnector,
    }

    @classmethod
    def get_connector(cls, config: DBConfig) -> BaseConnector:
        connector_class = cls._connectors.get(config.db_type.lower())
        if not connector_class:
            raise ValueError(f"Unsupported database type: {config.db_type}")
        return connector_class(config)

    @classmethod
    def register_connector(cls, db_type: str, connector_class: Type[BaseConnector]):
        cls._connectors[db_type.lower()] = connector_class
