"""Microsoft Azure OpenAI integration for natural-language SQL translation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit, urlunsplit

from openai import OpenAI
from pydantic import BaseModel, Field


class SQLAnswer(BaseModel):
    """Structured answer returned by the Microsoft-hosted model."""

    sql: str = Field(description="One read-only SQLite SELECT query")
    explanation: str = Field(description="A short plain-English explanation of the query")


class MicrosoftAIError(RuntimeError):
    """Safe, user-facing error raised by the Microsoft AI integration."""


@dataclass(frozen=True)
class MicrosoftAIConfig:
    """Credentials and deployment metadata required by Azure OpenAI."""

    api_key: str = ""
    endpoint: str = ""
    deployment: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.api_key or self.endpoint or self.deployment)

    @property
    def missing(self) -> tuple[str, ...]:
        values = {
            "AZURE_OPENAI_API_KEY": self.api_key,
            "AZURE_OPENAI_ENDPOINT": self.endpoint,
            "AZURE_OPENAI_DEPLOYMENT": self.deployment,
        }
        return tuple(name for name, value in values.items() if not value)

    @property
    def ready(self) -> bool:
        return not self.missing

    def base_url(self) -> str:
        """Return a validated OpenAI-compatible Microsoft endpoint."""
        if not self.ready:
            raise MicrosoftAIError(
                "Microsoft AI configuration is incomplete. Add these Streamlit "
                f"Secrets: {', '.join(self.missing)}."
            )

        endpoint = self.endpoint.strip()
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise MicrosoftAIError(
                "AZURE_OPENAI_ENDPOINT must be a complete HTTPS endpoint without "
                "query parameters, for example https://RESOURCE.openai.azure.com/."
            )

        path = parsed.path.rstrip("/")
        if not path:
            path = "/openai/v1"
        elif path.endswith("/openai"):
            path += "/v1"

        return urlunsplit((parsed.scheme, parsed.netloc, f"{path}/", "", ""))


SECRET_ALIASES = {
    "api_key": (
        "AZURE_OPENAI_API_KEY",
        "MICROSOFT_COPILOT_API_KEY",
        "COPILOT_API_KEY",
        "OPENAI_API_KEY",
    ),
    "endpoint": (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_BASE_URL",
        "MICROSOFT_COPILOT_ENDPOINT",
        "COPILOT_ENDPOINT",
    ),
    "deployment": (
        "AZURE_OPENAI_DEPLOYMENT",
        "MICROSOFT_COPILOT_DEPLOYMENT",
        "COPILOT_DEPLOYMENT",
        "AZURE_OPENAI_MODEL",
    ),
}


def load_microsoft_config(get_value: Callable[[str], str]) -> MicrosoftAIConfig:
    """Load standard Azure names while accepting common Copilot aliases."""

    def first(names: tuple[str, ...]) -> str:
        for name in names:
            value = str(get_value(name) or "").strip()
            if value:
                return value
        return ""

    return MicrosoftAIConfig(
        api_key=first(SECRET_ALIASES["api_key"]),
        endpoint=first(SECRET_ALIASES["endpoint"]),
        deployment=first(SECRET_ALIASES["deployment"]),
    )


def translate_question(
    question: str,
    default_year: int,
    config: MicrosoftAIConfig,
) -> SQLAnswer:
    """Translate one audit question through Microsoft's Azure OpenAI endpoint."""
    base_url = config.base_url()
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
        client = OpenAI(api_key=config.api_key, base_url=base_url)
        response = client.responses.parse(
            model=config.deployment,
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": question},
            ],
            text_format=SQLAnswer,
        )
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        if status in {401, 403}:
            message = (
                "Microsoft rejected the credentials. Check AZURE_OPENAI_API_KEY and "
                "confirm that it belongs to the resource in AZURE_OPENAI_ENDPOINT."
            )
        elif status == 404:
            message = (
                "Microsoft could not find the endpoint or deployment. Check "
                "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT; the deployment "
                "name, not merely the model family, is required."
            )
        elif status == 429:
            message = (
                "The Microsoft deployment has reached its rate or quota limit. "
                "Check the quota for the Azure OpenAI resource."
            )
        else:
            message = (
                "The Microsoft AI request failed. Check the Azure endpoint, deployment "
                "name, resource access and quota."
            )
        raise MicrosoftAIError(message) from exc

    if response.output_parsed is None:
        raise MicrosoftAIError("Microsoft AI did not return a usable SQL query.")
    return response.output_parsed
