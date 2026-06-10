import mysql.connector
from mysql.connector import Error as MySQLError
from typing import List, Dict, Any
from .base import BaseConnector
from ..config.schema import DBConfig

class QueryError(Exception):
    pass

class MySQLConnector(BaseConnector):
    def __init__(self, config: DBConfig):
        self.config = config
        self.connection = None

    def connect(self) -> None:
        try:
            self.connection = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset
            )
        except MySQLError as e:
            raise ConnectionError(f"Failed to connect to MySQL database: {e}") from e

    def disconnect(self) -> None:
        if self.connection and self.connection.is_connected():
            self.connection.close()
        self.connection = None

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        if not self.connection or not self.connection.is_connected():
            raise QueryError("Not connected to database.")
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            result = cursor.fetchall()
            return result
        except MySQLError as e:
            raise QueryError(f"Query execution failed: {e}") from e
        finally:
            if cursor is not None:
                cursor.close()

    def __enter__(self) -> "MySQLConnector":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
