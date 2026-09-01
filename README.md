# OSU P-card Audit Explorer

## Live website

[Open the public OSU P-card Audit Explorer](https://osu-pcard-audit-va4elrburh4fz5gendntwr.streamlit.app/)

The live app includes a 2010–2014 audit overview, targeted description and
vendor searches, downloadable evidence, and a protected natural-language query
workflow. The overview and searches work without an API key. Natural-language
questions require `OPENAI_API_KEY` in Streamlit's secret settings.

This repository completes the P-card analytics mindset assignment:

- `analysis_queries.sql` contains the SQLite views for Part II (Questions 1-14)
  and Part III (Questions 1-8).
- `analysis_results.json` contains the row counts and first ten rows used to
  verify the conclusions in the completed assignment document.
- `app.py` is the two-tab Streamlit website required in Part IV.
- `data/pcards.db.gz.part*` contains the supplied database with the completed
  audit views. It is compressed and split into GitHub-friendly pieces. The app
  assembles and expands it automatically at startup without changing its contents.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The prohibited-purchase dashboard works without an API key. The natural-language
tab needs an OpenAI API key supplied as an environment variable:

```bash
export OPENAI_API_KEY="your-key"
streamlit run app.py
```

You may optionally set `OPENAI_MODEL`; the default is `gpt-5.6`.

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. In Streamlit Community Cloud, create an app with `app.py` as the entry point.
3. In the app's **Settings > Secrets**, add:

```toml
OPENAI_API_KEY = "your-key"
OPENAI_MODEL = "gpt-5.6"
```

Never commit `.streamlit/secrets.toml`, `.env`, or an API key. Both are already
excluded by `.gitignore`.

## Security design

Model-generated SQL is restricted to a single `SELECT` or `WITH` statement,
checked against blocked commands, executed through a read-only SQLite connection,
limited to 500 displayed rows, and interrupted if it runs for too long. A flag is
only a risk indicator; supporting documents must be reviewed before concluding
that a control was violated or fraud occurred.
