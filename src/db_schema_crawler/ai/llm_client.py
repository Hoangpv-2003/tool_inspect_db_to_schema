import json
import urllib.request
import urllib.error
import logging
from typing import Optional
from ..config.schema import LLMConfig

logger = logging.getLogger(__name__)

class LLMClientError(Exception):
    pass

class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config

    def request(self, prompt: str, system_prompt: str = "") -> str:
        if self.config.mode == "mock":
            return self._mock_request(prompt)
        elif self.config.mode == "local":
            return self._local_request(prompt, system_prompt)
        elif self.config.mode == "api":
            return self._api_request(prompt, system_prompt)
        return ""

    def _mock_request(self, prompt: str) -> str:
        p_lower = prompt.lower()
        if "classify" in p_lower or "từ điển" in p_lower or "glossary" in p_lower:
            if "gender" in p_lower or "gioi" in p_lower or "gt" in p_lower:
                return "Giới tính"
            if "name" in p_lower or "ho" in p_lower:
                return "Họ và tên"
            if "loai_dat" in p_lower or "dat" in p_lower:
                return "Loại đất"
            if "status" in p_lower or "trang_thai" in p_lower:
                return "Trạng thái"
        if "giá trị" in p_lower or "values" in p_lower or "allowed" in p_lower:
            if "0" in p_lower and "1" in p_lower:
                return "0: Nam, 1: Nữ"
            if "gd" in p_lower and "tp" in p_lower:
                return "GD: Giám đốc, TP: Trưởng phòng"
        return ""

    def _local_request(self, prompt: str, system_prompt: str) -> str:
        url = f"{self.config.local_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.config.local_model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": self.config.temperature}
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res = json.loads(response.read().decode("utf-8"))
                return res.get("response", "").strip()
        except Exception as e:
            logger.debug(f"Local Ollama endpoint failed, trying OpenAI compatible endpoint: {e}")
            # Fallback to OpenAI compatible endpoint `/v1/chat/completions`
            fallback_url = f"{self.config.local_url.rstrip('/')}/v1/chat/completions"
            fallback_payload = {
                "model": self.config.local_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.config.temperature
            }
            req_fb = urllib.request.Request(
                fallback_url,
                data=json.dumps(fallback_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                with urllib.request.urlopen(req_fb, timeout=10) as response_fb:
                    res_fb = json.loads(response_fb.read().decode("utf-8"))
                    return res_fb["choices"][0]["message"]["content"].strip()
            except Exception as e_fb:
                raise LLMClientError(
                    f"Local LLM request failed on both Ollama (/api/generate) and OpenAI-compatible (/v1/chat/completions) endpoints. "
                    f"Errors: [{e}], [{e_fb}]"
                ) from e_fb

    def _api_request(self, prompt: str, system_prompt: str) -> str:
        if not self.config.api_key:
            raise LLMClientError("API Key is missing for API mode.")
            
        if self.config.api_provider == "openai":
            url = self.config.api_url or "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": self.config.api_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.config.temperature
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}"
            }
        elif self.config.api_provider == "gemini":
            # Direct Gemini REST API endpoint
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.api_model}:generateContent?key={self.config.api_key}"
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
                "generationConfig": {"temperature": self.config.temperature}
            }
            headers = {"Content-Type": "application/json"}
        else:
            raise LLMClientError(f"Unsupported API provider: {self.config.api_provider}")

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res = json.loads(response.read().decode("utf-8"))
                if self.config.api_provider == "openai":
                    return res["choices"][0]["message"]["content"].strip()
                elif self.config.api_provider == "gemini":
                    return res["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            raise LLMClientError(f"API request failed: {e}") from e
