"""
Thin wrapper around the Ollama Python client.
All AI modules import from here — never directly from ollama.
"""

import json
import logging
import re
from typing import Any, Optional

import ollama

from config.settings import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Wrapper around Ollama that adds JSON extraction and error handling."""

    def __init__(self, base_url: str = None, timeout: int = 120):
        self.base_url = base_url or settings.ollama_base_url
        self.timeout = timeout
        self._client = ollama.Client(host=self.base_url)

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> str:
        try:
            response = self._client.generate(
                model=model,
                prompt=prompt,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )
            return response.response.strip()
        except Exception as e:
            logger.error(f"Ollama generate failed [{model}]: {e}")
            raise

    def generate_json(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> Optional[dict | list]:
        raw = self.generate(model, prompt, temperature, max_tokens)
        return self._extract_json(raw)

    def embed(self, model: str, text: str) -> list[float]:
        try:
            response = self._client.embeddings(model=model, prompt=text)
            return response.embedding
        except Exception as e:
            logger.error(f"Ollama embed failed [{model}]: {e}")
            raise

    def is_available(self) -> bool:
        try:
            self._client.list()
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            models = self._client.list()
            return [m.model for m in models.models]
        except Exception:
            return []

    @staticmethod
    def _extract_json(text: str) -> Optional[dict | list]:
        """
        Extract JSON from a model response that may contain:
        - markdown fences: ```json ... ```
        - // comments (invalid JSON but some models add these)
        - extra explanation text before or after the JSON
        """
        if not text:
            return None

        # Strip markdown fences
        text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

        # Strip // comments — these are invalid JSON but phi3:mini adds them
        text = re.sub(r"//[^\n]*", "", text).strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find a JSON object or array within the text
        for pattern in [r"\{.*\}", r"\[.*\]"]:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue

        logger.warning(f"Could not extract JSON from model response: {text[:200]}")
        return None


# Shared instance — import this everywhere
ollama_client = OllamaClient()
