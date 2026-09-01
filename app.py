"""Interactive P-card audit website for the analytics mindset assignment."""

from __future__ import annotations

import gzip
import os
import shutil
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI
from pydantic import BaseModel, Field

from db_utils import get_years, run_readonly_query, search_transactions


ROOT = Path(__file__).resolve().parent
SOURCE_DB_PATH = ROOT / "data" / "pcards.db"
COMPRESSED_DB_PATH = ROOT / "data" / "pcards.db.gz"


@st.cache_resource
def database_path() -> Path:
    """Return the database, expanding the public compressed copy when needed."""
    if SOURCE_DB_PATH.exists():
        return SOURCE_DB_PATH
    compressed_parts = sorted((ROOT / "data").glob("pcards.db.gz.part*"))
    if not COMPRESSED_DB_PATH.exists() and not compressed_parts:
        raise FileNotFoundError("Database not found in the data folder.")

    target = Path(tempfile.gettempdir()) / "osu-pcard-audit" / "pcards.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        compressed_source = COMPRESSED_DB_PATH
        if not compressed_source.exists():
            compressed_source = target.parent / "pcards.db.gz"
            assembled = compressed_source.with_suffix(".assembling")
            with assembled.open("wb") as output:
                for part in compressed_parts:
                    with part.open("rb") as source:
                        shutil.copyfileobj(source, output)
            assembled.replace(compressed_source)
        temporary = target.with_suffix(".tmp")
        with gzip.open(compressed_source, "rb") as source, temporary.open("wb") as output:
            shutil.copyfileobj(source, output)
        temporary.replace(target)
    return target


try:
    DB_PATH = database_path()
except (FileNotFoundError, OSError) as exc:
    st.error(f"Database could not be prepared: {exc}")
    st.stop()


class SQLAnswer(BaseModel):
    sql: str = Field(description="One read-only SQLite SELECT query")
    explanation: str = Field(description="A short plain-English explanation of the query")


def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
    except FileNotFoundError:
        value = default
    return str(value or os.getenv(name, default))


def question_to_sql(question: str) -> SQLAnswer:
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Add it to the hosting platform's "
            "secret settings; never place it in the repository."
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
If the user does not ask for a different order, show the largest amounts first.
The application will add a display limit automatically.
""".strip()

    client = OpenAI(api_key=api_key)
    response = client.responses.parse(
        model=get_secret("OPENAI_MODEL", "gpt-5.6"),
        input=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": question},
        ],
        text_format=SQLAnswer,
    )
    if response.output_parsed is None:
        raise RuntimeError("The model did not return a usable SQL query.")
    return response.output_parsed


def money(value: float) -> str:
    return f"${value:,.2f}"


def show_search_results(total: int, frame: pd.DataFrame, label: str) -> None:
    if total == 0:
        st.info(f"No {label.lower()} matches were found for the selected year.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Matching transactions", f"{total:,}")
    c2.metric("Displayed amount", money(float(frame["Amount"].sum())))
    c3.metric("Cardholders", f"{frame['FullName'].nunique():,}")

    if total > len(frame):
        st.caption(f"Showing the {len(frame):,} largest of {total:,} matching rows.")

    monthly = frame.groupby("Month", as_index=False)["Amount"].sum().set_index("Month")
    st.bar_chart(monthly, y="Amount", x_label="Month", y_label="Amount (USD)")
    st.dataframe(frame, use_container_width=True, hide_index=True)
    st.download_button(
        "Download displayed results (CSV)",
        frame.to_csv(index=False).encode("utf-8"),
        file_name=f"{label.lower().replace(' ', '_')}_results.csv",
        mime="text/csv",
    )


st.set_page_config(
    page_title="OSU P-card Audit Explorer",
    page_icon="🔎",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {background:#f5f7fb; border:1px solid #dbe2ea;
        border-radius:12px; padding:14px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("OSU P-card Audit Explorer")
st.caption(
    "A risk-screening tool for purchasing-card transactions. Flags are potential "
    "exceptions and require supporting-document review before a conclusion is made."
)

ask_tab, dashboard_tab = st.tabs(
    ["Ask the database", "Prohibited-purchase dashboard"]
)

with ask_tab:
    st.subheader("Ask a question in plain English")
    st.write(
        "Enter an audit question. The app converts it to a read-only SQLite query, "
        "checks the query, and returns at most 500 rows."
    )
    st.caption(
        "Example: Which five vendors received the highest total amount in 2014?"
    )
    with st.form("natural_language_form"):
        question = st.text_area(
            "Audit question",
            placeholder="Show total 2014 spending by employee, largest first.",
        )
        ask = st.form_submit_button("Run question", type="primary")

    if ask:
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            try:
                with st.spinner("Creating and running a read-only query..."):
                    answer = question_to_sql(question.strip())
                    executed_sql, result = run_readonly_query(DB_PATH, answer.sql)
                st.success(f"Returned {len(result):,} row(s).")
                st.write(answer.explanation)
                with st.expander("Show generated SQLite query"):
                    st.code(executed_sql, language="sql")
                st.dataframe(result, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download answer (CSV)",
                    result.to_csv(index=False).encode("utf-8"),
                    file_name="natural_language_answer.csv",
                    mime="text/csv",
                )
            except Exception as exc:
                st.error(f"The question could not be completed: {exc}")

with dashboard_tab:
    st.subheader("Search for possible prohibited purchases")
    st.write(
        "Choose a year and search the description or vendor separately. Try terms "
        "such as alcohol, gift, insurance, membership, gasoline, USPS, or post office. "
        "Review the transaction, cardholder, date, description, vendor and MCC before "
        "deciding whether follow-up evidence is needed."
    )

    years = get_years(DB_PATH)
    selected_year = st.selectbox("Year", years, index=0)

    st.markdown("#### Description search")
    st.caption("Searches only the transaction Description field.")
    with st.form("description_form"):
        description_keyword = st.text_input(
            "Description keyword", placeholder="Example: alcohol"
        )
        description_submit = st.form_submit_button(
            "Search descriptions", type="primary"
        )
    if description_submit:
        if not description_keyword.strip():
            st.warning("Enter a description keyword first.")
        else:
            count, rows = search_transactions(
                DB_PATH,
                year=selected_year,
                field="Description",
                keyword=description_keyword,
            )
            show_search_results(count, rows, "Description")

    st.divider()
    st.markdown("#### Vendor search")
    st.caption("Searches only the Vendor field.")
    with st.form("vendor_form"):
        vendor_keyword = st.text_input(
            "Vendor keyword", placeholder="Example: post office"
        )
        vendor_submit = st.form_submit_button("Search vendors", type="primary")
    if vendor_submit:
        if not vendor_keyword.strip():
            st.warning("Enter a vendor keyword first.")
        else:
            count, rows = search_transactions(
                DB_PATH,
                year=selected_year,
                field="Vendor",
                keyword=vendor_keyword,
            )
            show_search_results(count, rows, "Vendor")
