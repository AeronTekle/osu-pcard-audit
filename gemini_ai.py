"""Google Gemini integration for natural-language SQL translation."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field, ValidationError


GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"


class SQLAnswer(BaseModel):
    """Structured answer returned by Gemini."""

    sql: str = Field(description="One read-only SQLite SELECT query")
    explanation: str = Field(description="A short plain-English explanation of the query")


class GeminiAIError(RuntimeError):
    """Safe, user-facing error raised by the Gemini integration."""


@dataclass(frozen=True)
class GeminiAIConfig:
    """Credentials and model metadata required by the Gemini API."""

    api_key: str = ""
    model: str = DEFAULT_GEMINI_MODEL

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def ready(self) -> bool:
        return self.configured


SECRET_ALIASES = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_GENAI_API_KEY",
)


def load_gemini_config(get_value: Callable[[str], str]) -> GeminiAIConfig:
    """Load the Gemini API key and optional model name from secrets or the environment."""
    api_key = ""
    for name in SECRET_ALIASES:
        value = str(get_value(name) or "").strip()
        if value:
            api_key = value
            break

    model = str(get_value("GEMINI_MODEL") or "").strip() or DEFAULT_GEMINI_MODEL
    return GeminiAIConfig(api_key=api_key, model=model)


def translate_question(
    question: str,
    default_year: int,
    config: GeminiAIConfig,
) -> SQLAnswer:
    """Translate one audit question through the Google Gemini API."""
    if not config.ready:
        raise GeminiAIError(
            "Gemini is not configured. Add GEMINI_API_KEY to Streamlit Secrets."
        )

    schema = """
Table: pcards
Columns:
- Year INTEGER; Month INTEGER; FullName TEXT; ID INTEGER
- AgencyNumber INTEGER; AgencyName TEXT
- CardholderLastName TEXT; CardholderFirstInitial TEXT
- Description TEXT; Amount REAL; Vendor TEXT
- TransactionDate TEXT and PostedDate TEXT in M/D/YYYY 0:00:00 format
- MCC TEXT (merchant category description)
""".strip()
    instructions = f"""
You translate an auditor's natural-language question into SQLite.
{schema}

Return exactly one read-only SELECT query (a WITH query is also allowed) and a short
explanation as JSON with exactly two string fields: sql and explanation.
Never use PRAGMA, ATTACH, data-changing SQL, comments, or semicolons.
Use case-insensitive matching with lower(...) and LIKE when searching text.
Use COALESCE for nullable text. Prefer explicit columns rather than SELECT *.
If the user does not specify a year, use {int(default_year)}.
If the user does not ask for a different order, show the largest amounts first.
The application will add a display limit automatically.
""".strip()

    try:
        url = f"{GEMINI_API_BASE_URL}/{quote(config.model, safe='')}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": instructions}]},
            "contents": [{"role": "user", "parts": [{"text": question}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": SQLAnswer.model_json_schema(),
            },
        }
        for attempt in range(3):
            response = httpx.post(
                url,
                headers={"x-goog-api-key": config.api_key},
                json=payload,
                timeout=30.0,
            )
            if response.status_code in {408, 429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2**attempt)
                continue
            response.raise_for_status()
            break
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return SQLAnswer.model_validate_json(text)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in {400, 401, 403}:
            message = (
                "Google rejected the Gemini API key. Check GEMINI_API_KEY and "
                "confirm that it is an active key from Google AI Studio with Gemini "
                "API access."
            )
        elif status == 404:
            message = (
                "Google could not find the configured Gemini model. Check GEMINI_MODEL "
                f"or remove it to use the default model ({DEFAULT_GEMINI_MODEL})."
            )
        elif status == 429:
            message = (
                "The Gemini API has reached its rate or quota limit. Wait briefly or "
                "check the quota attached to the API key."
            )
        else:
            message = (
                f"The Gemini API returned HTTP {status}. Try again shortly or check "
                "the Google AI Studio project status."
            )
        raise GeminiAIError(message) from exc
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise GeminiAIError(
            "The app could not reach the Gemini API within 30 seconds. Try again shortly."
        ) from exc
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise GeminiAIError("Gemini did not return a usable SQL query.") from exc
