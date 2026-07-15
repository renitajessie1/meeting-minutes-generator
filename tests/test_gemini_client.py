import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock
import pytest

from llm.gemini_client import GeminiClient, LLMTimeoutError, LLMRateLimitError, LLMAPIError


def _client_with_mocked_sdk(mock_client):
    client = GeminiClient(api_key="fake-key", max_retries=2, base_backoff_seconds=0.01)
    client._client = mock_client
    return client


def test_successful_generate_returns_text():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"summary": "ok"}'
    mock_client.models.generate_content.return_value = mock_response

    client = _client_with_mocked_sdk(mock_client)
    result = client.generate("system", "user")

    assert result == '{"summary": "ok"}'


def test_retries_then_succeeds():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"summary": "ok"}'
    mock_client.models.generate_content.side_effect = [Exception("500 internal error"), mock_response]

    client = _client_with_mocked_sdk(mock_client)
    result = client.generate("system", "user")

    assert result == '{"summary": "ok"}'
    assert mock_client.models.generate_content.call_count == 2


def test_timeout_error_normalized():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("Deadline exceeded: timeout")

    client = _client_with_mocked_sdk(mock_client)
    with pytest.raises(LLMTimeoutError):
        client.generate("system", "user")


def test_rate_limit_error_normalized():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 quota exceeded: rate limit hit")

    client = _client_with_mocked_sdk(mock_client)
    with pytest.raises(LLMRateLimitError):
        client.generate("system", "user")


def test_generic_error_normalized_to_api_error():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("something weird happened")

    client = _client_with_mocked_sdk(mock_client)
    with pytest.raises(LLMAPIError):
        client.generate("system", "user")


def test_empty_response_raises_api_error():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = ""
    mock_client.models.generate_content.return_value = mock_response

    client = _client_with_mocked_sdk(mock_client)
    with pytest.raises(LLMAPIError):
        client.generate("system", "user")


def test_missing_api_key_raises_before_calling_sdk():
    client = GeminiClient(api_key=None)
    client._client = None  # force it to try to build a client
    with pytest.raises(LLMAPIError):
        client._get_client()


def test_vertex_express_flag_from_env(monkeypatch):
    monkeypatch.setenv("USE_VERTEX_EXPRESS", "true")
    client = GeminiClient(api_key="fake-key")
    assert client.use_vertex_express is True


def test_ai_studio_is_default_when_env_not_set(monkeypatch):
    monkeypatch.delenv("USE_VERTEX_EXPRESS", raising=False)
    client = GeminiClient(api_key="fake-key")
    assert client.use_vertex_express is False
