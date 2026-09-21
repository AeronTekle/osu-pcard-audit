# OSU P-card Audit Explorer

## Live website

[Open the public OSU P-card Audit Explorer](https://osu-pcard-audit-va4elrburh4fz5gendntwr.streamlit.app/)

The live app includes a 2010–2014 audit overview, targeted description and
vendor searches, downloadable evidence, and a protected natural-language query
workflow. The dashboard and common natural-language audit questions work without
an API key. Optional Microsoft Azure OpenAI access expands the range of supported
wording.

This repository completes the P-card analytics mindset assignment:

- `analysis_queries.sql` contains the SQLite views for Part II (Questions 1-14)
  and Part III (Questions 1-8).
- `analysis_results.json` contains the row counts and first ten rows used to
  verify the conclusions in the completed assignment document.
- `app.py` is the two-tab Streamlit website required in Part IV.
- `data/pcards.db.gz` contains the supplied database with the completed audit
  views, compressed below GitHub's file-size limit. The app expands it
  automatically at startup without changing its contents.
- `SUBMISSION_CHECKLIST.md` maps every assignment requirement to its completed evidence.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The dashboard and built-in natural-language question patterns work without an API
key. For unrestricted AI translation through Microsoft, supply the API key,
endpoint, and deployment name from the same Azure OpenAI resource:

```bash
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://YOUR-RESOURCE.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
streamlit run app.py
```

`AZURE_OPENAI_DEPLOYMENT` must be the deployment name configured in Microsoft
Azure, not merely a generic model-family name. A Copilot Studio web-channel
secret is not an Azure OpenAI model API key.

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. In Streamlit Community Cloud, create an app with `app.py` as the entry point.
3. In the app's **Settings > Secrets**, add:

```toml
AZURE_OPENAI_API_KEY = "your-key"
AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com/"
AZURE_OPENAI_DEPLOYMENT = "your-deployment-name"
```

For compatibility, the app also recognizes the equivalent
`MICROSOFT_COPILOT_API_KEY`, `MICROSOFT_COPILOT_ENDPOINT`, and
`MICROSOFT_COPILOT_DEPLOYMENT` names. The standard Azure names above are
recommended. An existing Microsoft key stored under the old `OPENAI_API_KEY`
name is also accepted when the Azure endpoint and deployment values are present.

Never commit `.streamlit/secrets.toml`, `.env`, or an API key. They are already
excluded by `.gitignore`.

## Security design

Model-generated SQL is restricted to a single `SELECT` or `WITH` statement,
checked against blocked commands, executed through a read-only SQLite connection,
limited to 500 displayed rows, and interrupted if it runs for too long. A flag is
only a risk indicator; supporting documents must be reviewed before concluding
that a control was violated or fraud occurred.
