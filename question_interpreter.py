"""Built-in natural-language questions that do not require API credits."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class BuiltInAnswer:
    sql: str
    explanation: str


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "twenty": 20,
    "fifty": 50,
}


def _year(question: str, default_year: int) -> int:
    match = re.search(r"\b(201[0-4])\b", question)
    return int(match.group(1)) if match else int(default_year)


def _limit(question: str, default: int = 10) -> int:
    match = re.search(r"\b(?:top|largest|highest|first)\s+(\d{1,3})\b", question)
    if match:
        return min(max(int(match.group(1)), 1), 100)
    word_match = re.search(
        r"\b(?:top|largest|highest|first)\s+(" + "|".join(NUMBER_WORDS) + r")\b",
        question,
    )
    if word_match:
        return NUMBER_WORDS[word_match.group(1)]
    return default


def _money_threshold(question: str, default: float = 5000.0) -> float:
    candidates = re.findall(r"(?:\$\s*)?(\d[\d,]*(?:\.\d+)?)", question)
    for candidate in reversed(candidates):
        value = float(candidate.replace(",", ""))
        if value not in range(2010, 2015):
            return value
    return default


def _quoted_or_trailing_keyword(question: str) -> str | None:
    quoted = re.search(r"[\"']([^\"']+)[\"']", question)
    if quoted:
        return quoted.group(1).strip()
    without_year = re.sub(r"\s+in\s+201[0-4][?.!]*$", "", question)
    trailing = re.search(
        r"\b(?:containing|contains|matching|for|about)\s+(.+?)[?.!]*$",
        without_year,
    )
    return trailing.group(1).strip() if trailing else None


def _escape(value: str) -> str:
    return value.replace("'", "''")


def interpret_common_question(
    question: str, *, default_year: int
) -> BuiltInAnswer | None:
    """Translate common audit questions to fixed, read-only SQLite patterns."""
    normalized = " ".join(question.lower().split())
    year = _year(normalized, default_year)
    scope = f"Year = {year} AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'"

    if "vendor" in normalized and re.search(
        r"\b(top|highest|largest|most|received)\b", normalized
    ):
        limit = _limit(normalized, 5)
        return BuiltInAnswer(
            sql=f"""SELECT Vendor, COUNT(*) AS TransactionCount,
       ROUND(SUM(Amount), 2) AS TotalAmount
FROM pcards
WHERE {scope}
GROUP BY Vendor
ORDER BY TotalAmount DESC
LIMIT {limit}""",
            explanation=f"Ranks the {limit} vendors with the highest total amount in {year}.",
        )

    cardholder_ranking = re.search(
        r"\b(employee|employees|cardholder|cardholders)\b", normalized
    ) and (
        re.search(r"\b(top|highest|largest|most)\b", normalized)
        or "spending by" in normalized
        or "spent by" in normalized
    )
    spender_ranking = re.search(r"\bspenders?\b", normalized) and re.search(
        r"\b(top|highest|largest|most)\b", normalized
    )
    if cardholder_ranking or spender_ranking:
        default_limit = 1 if re.search(r"\bspender\b", normalized) else 100
        limit = _limit(normalized, default_limit)
        return BuiltInAnswer(
            sql=f"""SELECT FullName, COUNT(*) AS TransactionCount,
       ROUND(SUM(Amount), 2) AS TotalAmount
FROM pcards
WHERE {scope}
GROUP BY FullName
ORDER BY TotalAmount DESC
LIMIT {limit}""",
            explanation=f"Ranks {year} cardholders by total purchasing amount, largest first.",
        )

    if re.search(r"\b(month|monthly)\b", normalized) and re.search(
        r"\b(amount|spend|spending|total|purchas)", normalized
    ):
        return BuiltInAnswer(
            sql=f"""SELECT Month, COUNT(*) AS TransactionCount,
       ROUND(SUM(Amount), 2) AS TotalAmount
FROM pcards
WHERE {scope}
GROUP BY Month
ORDER BY Month""",
            explanation=f"Summarizes transaction counts and purchasing amounts by month for {year}.",
        )

    if "transaction" in normalized and re.search(
        r"\b(exceed|exceeded|above|over|more than|greater than)\b", normalized
    ):
        threshold = _money_threshold(normalized)
        return BuiltInAnswer(
            sql=f"""SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE {scope} AND Amount > {threshold:.2f}
ORDER BY Amount DESC""",
            explanation=f"Returns {year} transactions above ${threshold:,.2f}, largest first.",
        )

    if "transaction" in normalized and re.search(
        r"\b(top|largest|highest|biggest)\b", normalized
    ):
        limit = _limit(normalized, 10)
        return BuiltInAnswer(
            sql=f"""SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE {scope}
ORDER BY Amount DESC
LIMIT {limit}""",
            explanation=f"Returns the {limit} largest transactions in {year}.",
        )

    if re.search(r"\b(how many|count|number of)\b", normalized) and "transaction" in normalized:
        return BuiltInAnswer(
            sql=f"SELECT COUNT(*) AS TransactionCount FROM pcards WHERE {scope}",
            explanation=f"Counts all OSU P-card transactions in {year}.",
        )

    if re.search(r"\b(total amount|how much|total spend|total spending)\b", normalized):
        return BuiltInAnswer(
            sql=f"""SELECT COUNT(*) AS TransactionCount,
       ROUND(SUM(Amount), 2) AS TotalAmount
FROM pcards
WHERE {scope}""",
            explanation=f"Returns the transaction count and total OSU P-card amount for {year}.",
        )

    if "negative" in normalized or "credit transactions" in normalized:
        return BuiltInAnswer(
            sql=f"""SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE {scope} AND Amount < 0
ORDER BY Amount""",
            explanation=f"Returns negative {year} transactions for return or credit follow-up.",
        )

    if re.search(r"\b(description|vendor)\b", normalized) and re.search(
        r"\b(contain|contains|containing|matching|search|for)\b", normalized
    ):
        keyword = _quoted_or_trailing_keyword(normalized)
        field = "Description" if "description" in normalized else "Vendor"
        if keyword:
            keyword = _escape(keyword)
            return BuiltInAnswer(
                sql=f"""SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE {scope}
  AND lower(COALESCE({field}, '')) LIKE '%{keyword}%'
ORDER BY Amount DESC""",
                explanation=f"Searches the {field.lower()} field for “{keyword}” in {year}.",
            )

    return None
