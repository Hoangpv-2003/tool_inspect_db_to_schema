from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseConnector(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_tables(self) -> List[Dict[str, Any]]:
        """Returns list of tables with columns: TABLE_NAME, TABLE_COMMENT."""
        pass

    @abstractmethod
    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Returns list of columns with standard keys (COLUMN_NAME, DATA_TYPE, etc)."""
        pass

    @abstractmethod
    def get_primary_keys(self, table_name: str) -> List[str]:
        """Returns list of primary key column names."""
        pass

    @abstractmethod
    def get_foreign_keys(self, table_name: str) -> Dict[str, Dict[str, str]]:
        """Returns map of local_col -> {referenced_table, referenced_column}."""
        pass

    @abstractmethod
    def get_check_constraints(self, table_name: str) -> List[str]:
        """Returns list of check constraint clauses."""
        pass

    def count_records(self, table_name: str) -> int:
        """Default implementation for counting records."""
        sql = f"SELECT COUNT(*) AS row_count FROM {table_name}"
        try:
            res = self.execute_query(sql)
            return res[0]["row_count"] if res else 0
        except Exception:
            return -1

    def get_update_time(self, table_name: str) -> str | None:
        """Returns the last update time of the table if available."""
        return None

    def __enter__(self) -> "BaseConnector":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
