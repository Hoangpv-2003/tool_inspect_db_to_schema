from abc import ABC, abstractmethod
from typing import List
from ..models.table_schema import TableSchema
from ..models.field_schema import FieldSchema

class BaseExporter(ABC):
    @abstractmethod
    def export(self, tables: List[TableSchema], fields: List[FieldSchema]) -> None:
        pass
