"""LLM client abstraction supporting OpenAI, Anthropic, and Gemini."""

import os
import re
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Type, TypeVar
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

T = TypeVar("T", bound=BaseModel)


# Errors that should NOT be retried (billing, auth, bad request)
_NON_RETRYABLE_KEYWORDS = ["credit balance", "billing", "quota", "authentication", "invalid api key", "unauthorized"]


def _is_retryable(exc: BaseException) -> bool:
    """Return True if the exception is worth retrying (transient errors only)."""
    msg = str(exc).lower()
    return not any(kw in msg for kw in _NON_RETRYABLE_KEYWORDS)


def repair_json(content: str) -> str:
    """Repair common JSON syntax errors produced by LLMs."""
    content = re.sub(r",(\s*[}\]])", r"\1", content)
    content = re.sub(r",(\s*,)+", ",", content)
    return content


def _extract_json_object(content: str) -> str:
    """Extract a JSON object from LLM response text using multiple strategies."""
    if not content or not content.strip():
        raise RuntimeError("Empty content, cannot extract JSON")

    # Strategy 1: Extract from markdown code blocks
    if "```" in content:
        code_blocks = re.findall(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if code_blocks:
            content = code_blocks[0].strip()

    # Strategy 2: Find JSON object in the text
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        content = json_match.group(0)

    # Strategy 3: If content doesn't start with {, find first {
    if not content.startswith("{"):
        start_idx = content.find("{")
        if start_idx != -1:
            content = content[start_idx:]

    # Strategy 4: Balance braces if extra data after }
    if content.count("}") > content.count("{"):
        brace_count = 0
        for i, char in enumerate(content):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    content = content[: i + 1]
                    break

    # Strategy 5: Repair common JSON syntax errors
    content = repair_json(content)

    if not content.startswith("{"):
        raise RuntimeError(f"Response doesn't contain JSON object. Content: {content[:200]}")

    return content


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        pass

    @abstractmethod
    def generate_json(self, prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, schema: Type[T], temperature: float = 0.7) -> T:
        """Generate a response guaranteed to match the given Pydantic schema."""
        pass


class OpenAIClient(LLMClient):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Install openai: pip install 'resume-tailor[openai]'")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Set OPENAI_API_KEY environment variable or pass api_key.")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception(_is_retryable))
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception(_is_retryable))
    def generate_json(self, prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        content = response.choices[0].message.content.strip()
        content = _extract_json_object(content)
        return json.loads(content)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception(_is_retryable))
    def generate_structured(self, prompt: str, schema: Type[T], temperature: float = 0.7) -> T:
        response = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
            temperature=temperature,
        )
        return response.choices[0].message.parsed


class AnthropicClient(LLMClient):
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("Install anthropic: pip install 'resume-tailor[claude]'")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Set ANTHROPIC_API_KEY environment variable or pass api_key.")
        self.model = model
        self.client = Anthropic(api_key=self.api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception(_is_retryable))
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception(_is_retryable))
    def generate_json(self, prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
        json_prompt = f"{prompt}\n\nRespond with valid JSON only, no other text."
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=temperature,
            messages=[{"role": "user", "content": json_prompt}],
        )
        content = response.content[0].text.strip()
        content = _extract_json_object(content)
        return json.loads(content)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception(_is_retryable))
    def generate_structured(self, prompt: str, schema: Type[T], temperature: float = 0.7) -> T:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=4000,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
        return response.parsed_output


class GeminiClient(LLMClient):
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        try:
            from google import genai
        except ImportError:
            raise ImportError("Install google-genai: pip install 'resume-tailor[gemini]'")

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Set GEMINI_API_KEY environment variable or pass api_key.")
        self.model = model
        self.client = genai.Client(api_key=self.api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception(_is_retryable))
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text.strip()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception(_is_retryable))
    def generate_json(self, prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        content = response.text.strip()
        content = _extract_json_object(content)
        return json.loads(content)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception(_is_retryable))
    def generate_structured(self, prompt: str, schema: Type[T], temperature: float = 0.7) -> T:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        return schema.model_validate_json(response.text)


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMClient:
    """Factory function to create an LLM client."""
    provider = provider or os.getenv("AI_PROVIDER", "gemini")

    default_models = {
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-20250514",
        "gemini": "gemini-2.0-flash",
    }

    if provider not in default_models:
        raise ValueError(f"Invalid provider: {provider}. Supported: {list(default_models.keys())}")

    model = model or os.getenv("AI_MODEL") or default_models[provider]

    clients = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "gemini": GeminiClient,
    }

    return clients[provider](api_key=api_key, model=model)
