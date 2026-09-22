# Final submission checklist

## Hand in these three items

1. **Completed Word document:** `PCard_assignment_completed.docx`
2. **Live website:** https://osu-pcard-audit-va4elrburh4fz5gendntwr.streamlit.app/
3. **GitHub repository:** https://github.com/AeronTekle/osu-pcard-audit

## Requirement coverage

| Assignment requirement | Completed evidence |
| --- | --- |
| Part II uses only OSU 2014 data | All 14 `qry_T2_Question#` views filter `Year = 2014` and `AgencyName = 'OKLAHOMA STATE UNIVERSITY'`. |
| Seven required Part II controls | Questions 1–7 contain a query name, result, conclusion, and follow-up interpretation. |
| Seven student-defined Part II controls | Questions 8–14 cover sales tax, alcohol, gasoline, mail/postage, insurance, memberships/dues, and gifts. |
| Part III uses only OSU 2014 data | All eight `qry_T3_Question#` views use the required population. |
| Four required Part III tests | Questions 1–4 cover Benford analysis, duplicate transactions, repeat duplicate employees, and round-number transactions. |
| Four distinct student-defined fraud tests | Questions 5–8 cover weekend activity, transactions just below the limit, recurring identical charges, and vendor concentration. |
| Results-based conclusions | Every Part II and III answer quantifies the result and states evidence needed before concluding that an exception occurred. |
| Website has two tabs | “Ask the database” and “Prohibited-purchase dashboard.” |
| Natural-language questions | Common audit questions run without API credits; optional Google Gemini access supports broader wording. |
| Year selector | Reporting-year selector covers 2010–2014. |
| Separate Description search | Dedicated form searches only `Description` and returns follow-up fields. |
| Separate Vendor search | Dedicated form searches only `Vendor` and returns follow-up fields. |
| Prohibited-purchase guidance | The dashboard lists all 14 prohibited-purchase categories from the assignment. |
| API-key protection | Secrets are read from Streamlit settings or environment variables and are excluded from Git. |

## Final verification record

- SQLite integrity check: `ok`
- Source database rows: `489,178`
- OSU 2014 rows: `116,031`
- Analysis views executed: `22` (14 Part II + 8 Part III)
- Automated application tests: `14 passed`
- Word placeholders remaining: `0`
- Word pages visually checked: `18`
- API keys found in repository source: `0`
