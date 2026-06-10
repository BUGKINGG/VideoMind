from __future__ import annotations

from dataclasses import dataclass
import json
import urllib.error
import urllib.request

from app.core.config import LLMConfig, get_llm_config


class LLMClient:
    '''
    抽象方法，只是接口，在下面实现
    '''
    def generate(self, messages: list[dict[str, str]]) -> str:
        raise NotImplementedError


@dataclass
class AnthropicLLMClient(LLMClient):
    config: LLMConfig
    max_tokens: int = 80000

    @classmethod
    def from_env(cls) -> "AnthropicLLMClient":
        return cls(config=get_llm_config())

    def generate(self, messages: list[dict[str, str]]) -> str:
        if not self.config.auth_token or not self.config.base_url or not self.config.model:
            return (
                "LLM is not configured yet. Please set ANTHROPIC_AUTH_TOKEN, "
                "ANTHROPIC_BASE_URL and ANTHROPIC_MODEL in .env."
            )

        '''
        调用deepseek的flash接口，用的是openAi的格式
        '''
        url = self.config.base_url.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": self.config.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        body = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url=url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.auth_token}",
                "x-api-key": self.config.auth_token,
                "anthropic-version": "2023-06-01",
            },
        )

        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API returned HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                "Cannot connect to the LLM API. Check your network, API base URL, "
                "and whether a local proxy is required or broken."
            ) from error

        return self._extract_text(data)

    def _extract_text(self, data: dict) -> str:
        # OpenAI/DeepSeek 格式：choices[0].message.content
        choices = data.get("choices", [])
        if choices and isinstance(choices, list):
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if content:
                return content.strip()
        # 兜底：如果 content 为空（比如思考模型占满 token），返回原始 JSON 调试
        return json.dumps(data, ensure_ascii=False)
