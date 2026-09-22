"""Google Gemini integration for natural-language SQL translation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from openai import OpenAI
from pydantic import BaseModel, Field


GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


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
explanation. Never use PRAGMA, ATTACH, data-changing SQL, comments, or semicolons.
Use case-insensitive matching with lower(...) and LIKE when searching text.
Use COALESCE for nullable text. Prefer explicit columns rather than SELECT *.
If the user does not specify a year, use {int(default_year)}.
If the user does not ask for a different order, show the largest amounts first.
The application will add a display limit automatically.
""".strip()

    try:
        client = OpenAI(
            api_key=config.api_key,
            base_url=GEMINI_OPENAI_BASE_URL,
            timeout=30.0,
            max_retries=1,
        )
        completion = client.beta.chat.completions.parse(
            model=config.model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": question},
            ],
            response_format=SQLAnswer,
        )
    except Exception as exc:
        status = getattr(exc, "status_code", None)
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
                "The Gemini request failed. Check the API key, model access, network "
                "connection and quota."
            )
        raise GeminiAIError(message) from exc

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise GeminiAIError("Gemini did not return a usable SQL query.")
    return parsed
