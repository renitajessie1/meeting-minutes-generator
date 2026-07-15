"""
Thin wrapper around the Gemini API with retry/backoff and clear exception types,
so the rest of the app never has to deal with the SDK directly.

Supports two auth modes, controlled by the USE_VERTEX_EXPRESS env var:
- Google AI Studio (default): standard Gemini API key from aistudio.google.com
- Vertex AI Express Mode (USE_VERTEX_EXPRESS=true): a key from Vertex AI Express
  Mode, which does NOT require linking a billing account / credit card for
  new users during the 90-day free trial. Use this if your AI Studio key
  keeps returning a "free_tier_requests limit: 0" error.
"""

import os
import time
import logging

logger = logging.getLogger("meeting_minutes.llm")


class LLMError(Exception):
    """Base class for all LLM-call failures."""


class LLMTimeoutError(LLMError):
    pass


class LLMRateLimitError(LLMError):
    pass


class LLMAPIError(LLMError):
    pass


class GeminiClient:
    """
    Wraps the google-genai SDK with:
    - exponential backoff retries on transient failures
    - normalized exceptions (LLMTimeoutError / LLMRateLimitError / LLMAPIError)
    - support for both AI Studio and Vertex AI Express Mode auth
    """

    def __init__(
        self,
        model_name: str = "gemini-flash-latest",
        api_key: str | None = None,
        use_vertex_express: bool | None = None,
        max_retries: int = 3,
        base_backoff_seconds: float = 1.5,
        timeout_seconds: float = 30.0,
    ):
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if use_vertex_express is None:
            use_vertex_express = os.environ.get("USE_VERTEX_EXPRESS", "false").lower() == "true"
        self.use_vertex_express = use_vertex_express
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.timeout_seconds = timeout_seconds
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise LLMAPIError(
                    "GEMINI_API_KEY is not set. Add it to your .env file "
                    "(see .env.example)."
                )
            from google import genai

            self._client = genai.Client(vertexai=self.use_vertex_express, api_key=self.api_key)
        return self._client

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Calls the model with retry/backoff. Returns the raw text response.
        Raises LLMTimeoutError / LLMRateLimitError / LLMAPIError on failure
        after exhausting retries.
        """
        client = self._get_client()
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=[system_prompt, user_prompt],
                )
                text = getattr(response, "text", None)
                if not text:
                    raise LLMAPIError("Empty response from Gemini API.")
                return text

            except Exception as e:  # normalize SDK-specific exceptions
                last_error = e
                err_str = str(e).lower()

                if "timeout" in err_str or "deadline" in err_str:
                    normalized = LLMTimeoutError(str(e))
                elif "rate limit" in err_str or "429" in err_str or "quota" in err_str:
                    normalized = LLMRateLimitError(str(e))
                else:
                    normalized = LLMAPIError(str(e))

                if attempt < self.max_retries:
                    backoff = self.base_backoff_seconds * (2 ** (attempt - 1))
                    logger.warning(
                        "Gemini call failed (attempt %s/%s): %s. Retrying in %.1fs.",
                        attempt,
                        self.max_retries,
                        normalized,
                        backoff,
                    )
                    time.sleep(backoff)
                else:
                    raise normalized from last_error

        # Unreachable, but keeps type-checkers happy
        raise LLMAPIError(str(last_error))
