from pydantic import BaseModel
from typing import List

class DBConfig(BaseModel):
    alias: str
    host: str
    port: int = 3306
    user: str
    password: str
    database: str
    charset: str = "utf8mb4"

class AppConfig(BaseModel):
    output_dir: str = "./output"
    databases: List[DBConfig]
