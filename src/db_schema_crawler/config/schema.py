from pydantic import BaseModel, Field
from typing import List, Optional

class LLMConfig(BaseModel):
    mode: str = "mock"  # mock, local, api
    local_url: str = "http://192.168.0.118:11434"
    local_model: str = "qwen3:8B"
    api_provider: str = "openai"  # openai or gemini
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    api_model: str = "gpt-4o-mini"
    temperature: float = 0.0

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
    llm: LLMConfig = Field(default_factory=LLMConfig)

