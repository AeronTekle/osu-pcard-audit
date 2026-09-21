"""Interactive P-card audit website for the analytics mindset assignment."""

from __future__ import annotations

import gzip
import os
import shutil
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from db_utils import (
    get_year_dashboard,
    get_years,
    run_readonly_query,
    search_transactions,
)
from microsoft_ai import SQLAnswer, load_microsoft_config, translate_question
from question_interpreter import interpret_common_question


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


def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
    except FileNotFoundError:
        value = default
    return str(value or os.getenv(name, default))


def question_to_sql(question: str, default_year: int) -> SQLAnswer:
    built_in = interpret_common_question(question, default_year=default_year)
    if built_in:
        return SQLAnswer(sql=built_in.sql, explanation=built_in.explanation)

    config = load_microsoft_config(get_secret)
    if not config.configured:
        raise RuntimeError(
            "This wording is outside the built-in question patterns. Configure the "
            "Microsoft Azure OpenAI/Copilot connection, or use one of the examples."
        )
    return translate_question(question, default_year, config)


def money(value: float) -> str:
    return f"${value:,.2f}"


@st.cache_data(show_spinner=False)
def load_dashboard(year: int) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    return get_year_dashboard(DB_PATH, year)


def show_search_results(
    total: int, frame: pd.DataFrame, label: str, keyword: str, year: int
) -> None:
    st.markdown(
        f"### {label} results <span class='result-tag'>{year} · {keyword}</span>",
        unsafe_allow_html=True,
    )
    if total == 0:
        st.info(f"No {label.lower()} matches were found for the selected year.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Matching transactions", f"{total:,}")
    c2.metric("Displayed amount", money(float(frame["Amount"].sum())))
    c3.metric("Cardholders represented", f"{frame['FullName'].nunique():,}")

    if total > len(frame):
        st.caption(f"Showing the {len(frame):,} largest of {total:,} matching rows.")

    chart_data = frame.groupby("Month", as_index=False)["Amount"].sum().set_index("Month")
    st.bar_chart(chart_data, y="Amount", x_label="Month", y_label="Amount (USD)")
    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
        column_config={
            "Amount": st.column_config.NumberColumn("Amount (USD)", format="$%.2f"),
        },
    )
    st.download_button(
        "Download displayed results",
        frame.to_csv(index=False).encode("utf-8"),
        file_name=f"{label.lower().replace(' ', '_')}_{year}_{keyword}.csv",
        mime="text/csv",
        icon=":material/download:",
    )


st.set_page_config(
    page_title="OSU P-card Audit Explorer",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #17212b;
        --muted: #5d6a78;
        --line: #e5e9ee;
        --soft: #f6f7f9;
        --orange: #d73f09;
        --orange-dark: #a92f05;
    }
    .stApp {background: #ffffff; color: var(--ink);}
    .block-container {max-width: 1280px; padding-top: 1.4rem; padding-bottom: 4rem;}
    [data-testid="stSidebar"] {background: #f7f8fa; border-right: 1px solid var(--line);}
    [data-testid="stSidebar"] .block-container {padding-top: 1.8rem;}
    [data-testid="stMetric"] {
        background: #ffffff; border: 1px solid var(--line); border-radius: 16px;
        padding: 18px 20px; box-shadow: 0 6px 22px rgba(23,33,43,.05);
    }
    [data-testid="stMetricLabel"] {color: var(--muted); font-weight: 650;}
    [data-testid="stMetricValue"] {color: var(--ink); letter-spacing: -.035em;}
    .hero {
        position: relative; overflow: hidden; padding: 34px 38px; margin-bottom: 20px;
        border-radius: 22px; color: white;
        background: linear-gradient(120deg, #151d26 0%, #253341 68%, #d73f09 165%);
        box-shadow: 0 16px 38px rgba(23,33,43,.16);
    }
    .hero:after {
        content: ""; position: absolute; width: 280px; height: 280px; border-radius: 50%;
        right: -95px; top: -155px; background: rgba(215,63,9,.34);
    }
    .hero .eyebrow {font-size: .76rem; font-weight: 800; letter-spacing: .14em; color: #ffb092;}
    .hero h1 {font-size: 2.45rem; line-height: 1.08; margin: 11px 0 10px; letter-spacing: -.04em;}
    .hero p {max-width: 760px; margin: 0; color: #dce3e9; font-size: 1.03rem; line-height: 1.55;}
    .hero .badges {display: flex; gap: 9px; flex-wrap: wrap; margin-top: 21px;}
    .hero .badge {
        border: 1px solid rgba(255,255,255,.19); background: rgba(255,255,255,.08);
        border-radius: 999px; padding: 6px 11px; color: #f5f7f9; font-size: .78rem;
    }
    .section-kicker {color: var(--orange); font-size: .76rem; font-weight: 800; letter-spacing: .12em;}
    .result-tag {
        display: inline-block; vertical-align: middle; margin-left: 7px; padding: 4px 9px;
        border-radius: 999px; background: #fff0eb; color: var(--orange-dark); font-size: .72rem;
    }
    .review-note {
        border-left: 4px solid var(--orange); background: #fff7f3; padding: 13px 16px;
        border-radius: 0 10px 10px 0; color: #624035; font-size: .9rem; margin: 7px 0 18px;
    }
    .step-card {
        min-height: 112px; border: 1px solid var(--line); border-radius: 14px;
        padding: 16px 17px; background: var(--soft);
    }
    .step-card b {display: block; color: var(--ink); margin-bottom: 5px;}
    .step-card span {color: var(--muted); font-size: .88rem; line-height: 1.45;}
    .stTabs [data-baseweb="tab-list"] {gap: 8px; border-bottom: 1px solid var(--line);}
    .stTabs [data-baseweb="tab"] {
        height: 48px; padding: 0 18px; border-radius: 10px 10px 0 0; font-weight: 700;
    }
    .stTabs [aria-selected="true"] {color: var(--orange); background: #fff5f1;}
    div.stButton > button, div.stDownloadButton > button {border-radius: 10px; font-weight: 700;}
    div[data-testid="stForm"] {border: 1px solid var(--line); border-radius: 16px; padding: 20px;}
    #MainMenu, footer {visibility: hidden;}
    @media (max-width: 700px) {
        .hero {padding: 26px 22px;}
        .hero h1 {font-size: 1.9rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

years = get_years(DB_PATH)
with st.sidebar:
    st.markdown("### Audit scope")
    selected_year = st.selectbox("Reporting year", years, index=0)
    st.success("Database connected", icon=":material/check_circle:")
    st.caption(
        "All analysis is performed through a read-only SQLite connection. "
        "Search results are indicators for follow-up—not findings of misconduct."
    )
    st.divider()
    st.markdown("**Suggested review terms**")
    st.caption("Alcohol · Gift · Insurance · Membership · Gasoline · USPS · Post office")
    st.link_button(
        "View source on GitHub",
        "https://github.com/AeronTekle/osu-pcard-audit",
        width="stretch",
        icon=":material/code:",
    )

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">PURCHASING-CARD ANALYTICS</div>
      <h1>OSU P-card Audit Explorer</h1>
      <p>Explore purchasing activity, screen transactions for potential exceptions,
      and ask audit questions in plain English. Built for evidence-led follow-up.</p>
      <div class="badges">
        <span class="badge">Read-only database</span>
        <span class="badge">2010–2014 coverage</span>
        <span class="badge">Downloadable evidence</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

ask_tab, dashboard_tab = st.tabs(
    ["Ask the database", "Prohibited-purchase dashboard"]
)

with dashboard_tab:
    metrics, monthly, top_vendors = load_dashboard(selected_year)
    st.markdown('<div class="section-kicker">EXECUTIVE OVERVIEW</div>', unsafe_allow_html=True)
    st.subheader(f"{selected_year} purchasing activity")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Transactions", f"{metrics['transactions']:,}")
    m2.metric("Total amount", money(metrics["total_amount"]))
    m3.metric("Cardholders", f"{metrics['cardholders']:,}")
    m4.metric("Vendors", f"{metrics['vendors']:,}")

    st.markdown(
        f"""
        <div class="review-note"><b>Review snapshot:</b>
        {metrics['high_value']:,} transactions exceed $5,000 and
        {metrics['credits']:,} transactions have negative amounts. These are screening
        signals only and should be evaluated with approvals, receipts, and business purpose.</div>
        """,
        unsafe_allow_html=True,
    )

    chart_col, vendor_col = st.columns([1.45, 1])
    with chart_col:
        st.markdown("#### Monthly purchasing amount")
        st.caption("Use the monthly pattern to identify unusual peaks for follow-up.")
        monthly_chart = monthly.set_index("Month")[["Amount"]]
        st.bar_chart(monthly_chart, y="Amount", x_label="Month", y_label="Amount (USD)")
    with vendor_col:
        st.markdown("#### Top vendors by amount")
        st.caption("The ten vendors with the highest total amount in the selected year.")
        st.dataframe(
            top_vendors,
            width="stretch",
            hide_index=True,
            column_config={
                "Amount": st.column_config.NumberColumn("Amount (USD)", format="$%.2f"),
            },
        )

    st.divider()
    st.markdown('<div class="section-kicker">TARGETED SCREENING</div>', unsafe_allow_html=True)
    st.subheader("Search for possible prohibited purchases")
    st.write(
        "Search descriptions and vendors separately. Review the cardholder, date, "
        "merchant category, business description, and amount before deciding whether "
        "supporting evidence is required."
    )
    with st.expander("Prohibited-purchase reference list"):
        st.markdown(
            """
            - Alcohol
            - Cash, cash advances, and ATM transactions
            - Decorations
            - Donations and sponsorships
            - Gasoline
            - Gifts, gift cards, and gift certificates
            - Insurance
            - Late fees
            - Mail and postage
            - Moving expenses
            - Personal purchases
            - Personal or individual memberships and dues
            - Salaries, wages, and benefits
            - Service or incentive awards and items purchased for employees

            Enter a distinctive word from a category in either search box. A match is
            a lead for follow-up, not proof that the purchase violated policy.
            """
        )

    description_col, vendor_search_col = st.columns(2)
    with description_col:
        with st.form("description_form"):
            st.markdown("#### Description search")
            st.caption("Searches only the transaction description field.")
            description_keyword = st.text_input(
                "Description keyword", placeholder="Example: alcohol"
            )
            description_submit = st.form_submit_button(
                "Search descriptions", type="primary", icon=":material/search:"
            )
    with vendor_search_col:
        with st.form("vendor_form"):
            st.markdown("#### Vendor search")
            st.caption("Searches only the merchant/vendor field.")
            vendor_keyword = st.text_input(
                "Vendor keyword", placeholder="Example: post office"
            )
            vendor_submit = st.form_submit_button(
                "Search vendors", type="primary", icon=":material/search:"
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
            st.session_state["search_result"] = (
                selected_year,
                count,
                rows,
                "Description",
                description_keyword.strip(),
            )
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
            st.session_state["search_result"] = (
                selected_year,
                count,
                rows,
                "Vendor",
                vendor_keyword.strip(),
            )

    if "search_result" in st.session_state:
        result_year, count, rows, label, keyword = st.session_state["search_result"]
        if result_year == selected_year:
            st.divider()
            show_search_results(count, rows, label, keyword, result_year)

with ask_tab:
    st.markdown('<div class="section-kicker">NATURAL-LANGUAGE ANALYSIS</div>', unsafe_allow_html=True)
    st.subheader("Ask an audit question in plain English")
    st.write(
        "The app translates your question into one read-only SQLite query, validates "
        "the query, and returns no more than 500 displayed rows."
    )

    step1, step2, step3 = st.columns(3)
    with step1:
        st.markdown(
            '<div class="step-card"><b>1 · Ask</b><span>Write a focused question about vendors, cardholders, amounts, or timing.</span></div>',
            unsafe_allow_html=True,
        )
    with step2:
        st.markdown(
            '<div class="step-card"><b>2 · Validate</b><span>The generated SQL is restricted to a read-only SELECT or WITH query.</span></div>',
            unsafe_allow_html=True,
        )
    with step3:
        st.markdown(
            '<div class="step-card"><b>3 · Review</b><span>Inspect the result and download the displayed evidence for follow-up.</span></div>',
            unsafe_allow_html=True,
        )

    st.write("")
    microsoft_config = load_microsoft_config(get_secret)
    st.success(
        "Question mode is ready. The examples and common audit questions work without "
        "tokens; Microsoft AI expands the range of wording.",
        icon=":material/check_circle:",
    )
    if microsoft_config.ready:
        st.caption("Microsoft Azure OpenAI/Copilot translation is configured and ready.")
    elif microsoft_config.configured:
        st.warning(
            "Microsoft AI setup is incomplete. Add these Streamlit Secrets: "
            + ", ".join(microsoft_config.missing)
            + "."
        )
    else:
        st.caption(
            "Microsoft AI translation is not configured; built-in questions remain available."
        )

    examples = [
        "Write your own question",
        "Which five vendors received the highest total amount in 2014?",
        "Show total 2014 spending by employee, largest first.",
        "Which 2014 transactions exceeded 5,000 dollars?",
        "Summarize monthly purchasing amounts for 2014.",
    ]
    selected_example = st.selectbox("Start with an example", examples)
    default_question = "" if selected_example == examples[0] else selected_example

    with st.form("natural_language_form"):
        question = st.text_area(
            "Audit question",
            value=default_question,
            placeholder="Example: Show the ten largest transactions in 2014.",
            height=110,
        )
        ask = st.form_submit_button(
            "Run question",
            type="primary",
            icon=":material/play_arrow:",
        )

    if ask:
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            try:
                with st.spinner("Creating and running a read-only query..."):
                    answer = question_to_sql(question.strip(), selected_year)
                    executed_sql, result = run_readonly_query(DB_PATH, answer.sql)
                st.success(f"Returned {len(result):,} row(s).")
                st.write(answer.explanation)
                with st.expander("Show generated SQLite query"):
                    st.code(executed_sql, language="sql")
                st.dataframe(result, width="stretch", hide_index=True)
                st.download_button(
                    "Download answer",
                    result.to_csv(index=False).encode("utf-8"),
                    file_name="natural_language_answer.csv",
                    mime="text/csv",
                    icon=":material/download:",
                )
            except Exception as exc:
                st.error(f"The question could not be completed: {exc}")
