import pytest
import json
import urllib.request
from unittest.mock import MagicMock, patch
from db_schema_crawler.config.schema import LLMConfig
from db_schema_crawler.ai.llm_client import LLMClient, LLMClientError

def test_llm_client_mock():
    config = LLMConfig(mode="mock")
    client = LLMClient(config)
    
    assert client.request("classify glossary: gender") == "Giới tính"
    assert client.request("allowed values: [0, 1]") == "0: Nam, 1: Nữ"
    assert client.request("some unknown prompt") == ""

@patch("urllib.request.urlopen")
def test_llm_client_local_ollama(mock_urlopen):
    # Mock successful Ollama response
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"response": "Giới tính"}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    config = LLMConfig(mode="local", local_url="http://127.0.0.1:11434", local_model="qwen3:8B")
    client = LLMClient(config)

    res = client.request("Determine mapping for gender")
    assert res == "Giới tính"
    
    # Assert Ollama URL was called
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    assert req.full_url == "http://127.0.0.1:11434/api/generate"

@patch("urllib.request.urlopen")
def test_llm_client_local_openai_fallback(mock_urlopen):
    # Mock Ollama failure and OpenAI success
    mock_ollama_err = urllib.error.URLError("Ollama connection refused")
    
    mock_openai_response = MagicMock()
    mock_openai_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "Họ và tên"}}]
    }).encode("utf-8")
    mock_openai_response.__enter__.return_value = mock_openai_response
    
    # First call fails, second call succeeds
    mock_urlopen.side_effect = [mock_ollama_err, mock_openai_response]

    config = LLMConfig(mode="local", local_url="http://127.0.0.1:11434", local_model="qwen3:8B")
    client = LLMClient(config)

    res = client.request("Determine mapping for fullname")
    assert res == "Họ và tên"
    assert mock_urlopen.call_count == 2

@patch("urllib.request.urlopen")
def test_llm_client_api_openai(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "Email Address"}}]
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    config = LLMConfig(
        mode="api",
        api_provider="openai",
        api_key="test-key",
        api_model="gpt-4o-mini"
    )
    client = LLMClient(config)

    res = client.request("test prompt")
    assert res == "Email Address"
    
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    assert req.full_url == "https://api.openai.com/v1/chat/completions"
    assert req.headers["Authorization"] == "Bearer test-key"

@patch("urllib.request.urlopen")
def test_llm_client_api_gemini(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "candidates": [{"content": {"parts": [{"text": "Giới tính"}]}}]
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    config = LLMConfig(
        mode="api",
        api_provider="gemini",
        api_key="gemini-key",
        api_model="gemini-1.5-pro"
    )
    client = LLMClient(config)

    res = client.request("test prompt")
    assert res == "Giới tính"
    
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    assert "gemini-1.5-pro:generateContent?key=gemini-key" in req.full_url

def test_llm_client_api_missing_key():
    config = LLMConfig(mode="api", api_key=None)
    client = LLMClient(config)
    with pytest.raises(LLMClientError, match="API Key is missing"):
        client.request("test")
