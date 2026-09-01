"""Fill Parts II and III of the supplied Word assignment template."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import RGBColor


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "upload" / "Analytics_mindset_case_studies_PCard_assignment.docx"
OUTPUT = ROOT / "PCard_assignment_completed.docx"


T2_RESULTS = {
    1: "The query identifies 127 employees above $50,000. The highest total is $1,595,302.32. These employees are the priority population for confirming approved limits and business purpose.",
    2: "There are 457 employee-month exceptions. The largest is Employee 51914657 in June at $176,844.86. Approval evidence should be checked before treating an exception as a violation.",
    3: "There are 33 transactions above $5,000. The largest is $29,731.61. Each item should be checked for an approved exception, data error or use of the wrong purchasing process.",
    4: "The test flags 69 employee-vendor-day groups containing 269 transactions. The combined amounts exceed $5,000, so invoices and purchase timing should be reviewed for possible split purchasing.",
    5: "The test flags 24 vendor-day groups and 48 transactions involving exactly two cardholders. The result is a risk indicator; shared departmental purchases may provide a valid explanation.",
    6: "The test flags 61 employee-day groups and 122 transactions involving exactly two vendors. Supporting documents are needed to determine whether the items formed one purchase that was split.",
    7: "The query identifies 65 employee-days and 244 lodging or food transactions. Travel status and vouchers should be inspected because same-day food charges may have legitimate non-travel explanations.",
    8: "The keyword test returns 39 transactions totaling $7,540.10. Several descriptions state 'NonTax', showing why keyword matches are not proof of sales tax; receipts should confirm whether tax was actually charged.",
    9: "The test flags 44 transactions totaling $22,028.60, mainly in beer, wine and liquor MCCs. These are high-priority exceptions, but receipts and approved event documentation must be reviewed.",
    10: "The test identifies 723 service-station or fuel-related transactions totaling $297,023.88. They should be compared with Transportation Services records and authorized fuel-card usage.",
    11: "The test identifies 558 postal, courier or mail-related transactions totaling $49,242.57. Follow-up should determine whether University Mailing was unavailable or an approved exception existed.",
    12: "The test finds 17 insurance-related transactions totaling $9,836.92. The items should be traced to requisitions and Risk and Property Management approval.",
    13: "The broad membership/organization test flags 2,100 transactions totaling $1,019,296.49. Because the MCC also covers institutional organizations, evidence is needed to separate personal dues from allowable business memberships.",
    14: "The test flags 206 gift-category transactions totaling $54,292.85. MCC labels can include ordinary novelty merchandise, so itemized receipts are necessary to identify prohibited gifts or gift cards.",
}


T3_RESULTS = {
    1: "The observed first-digit percentages are close to Benford expectations (MAD = 0.00318). For example, digit 1 is 29.528% versus 30.103% expected. This indicates relatively low population-level fraud risk, but Benford analysis cannot clear individual transactions.",
    2: "The query returns 4,924 transaction rows across 1,732 possible duplicate occasions. Many may be valid repeated charges, so invoices, receipts and payment status should be compared before concluding that a duplicate payment occurred.",
    3: "A total of 278 employees have possible duplicates on more than one occasion. Employee 5BA61357 ranks highest with 78 occasions, followed by Employee 50D6FB87 with 65; these employees should be investigated first.",
    4: "The test identifies 160 four-digit round-number transactions totaling $343,003.98. Round amounts are only a risk indicator; contracts, invoices and normal pricing practices should be reviewed.",
    5: "The test flags 1,094 weekend transactions of at least $500, made by 470 employees and totaling $1,242,699.97. Weekend work and travel are plausible, so the business purpose and receipt date should be verified.",
    6: "There are 187 transactions between $4,750 and $5,000, involving 109 employees and totaling $918,741.26. The concentration just below the limit warrants review for limit avoidance, especially where purchases are related.",
    7: "The test finds 174 recurring employee-vendor-amount patterns. The largest count is 38 identical $101.98 charges to DIRECTV across 25 dates. Subscriptions can be valid, but contracts and cancellation records should be checked.",
    8: "The test identifies 70 employee-vendor relationships where one employee represents at least 80% of vendor spending, with at least five transactions and $10,000 vendor spending. These are targeted conflict-of-interest leads, not evidence of a relationship.",
}


T2_HEADINGS = {
    8: "Control 8  |  Oklahoma sales tax should not be charged",
    9: "Control 9  |  Alcohol purchases are prohibited",
    10: "Control 10  |  Gasoline purchases are prohibited",
    11: "Control 11  |  Mail and postage should use University Mailing",
    12: "Control 12  |  Insurance requires the requisition process",
    13: "Control 13  |  Personal memberships and dues are prohibited",
    14: "Control 14  |  Gifts and gift cards are prohibited",
}


T2_TESTS = {
    8: "Search 2014 descriptions for 'tax'. Return Amount, FullName, Description, Vendor, TransactionDate, PostedDate and MCC, and sort by Amount descending so the largest possible sales-tax charges are reviewed first.",
    9: "Search 2014 MCC and Description values for alcohol, liquor, beer or wine. Return all transaction details and sort by Amount descending.",
    10: "Search 2014 MCC values for gasoline, fuel or service station. Return all transaction details and sort by Amount descending.",
    11: "Search 2014 MCC and Vendor values for postal, courier, mail, post office or USPS. Return all transaction details and sort by Amount descending.",
    12: "Search 2014 MCC and Description values for insurance. Return all transaction details and sort by Amount descending.",
    13: "Search 2014 MCC and Description values for membership, organization or dues. Return all transaction details and sort by Amount descending.",
    14: "Search 2014 MCC, Description and Vendor values for gift, gift card or gift certificate. Return all transaction details and sort by Amount descending.",
}


T3_HEADINGS = {
    5: "Question 5  |  High-value weekend transactions",
    6: "Question 6  |  Transactions just below the $5,000 limit",
    7: "Question 7  |  Recurring identical charges across different dates",
    8: "Question 8  |  Employee concentration with a vendor",
}


T3_TESTS = {
    5: "Fraud risk: a card may be used for personal purchases when normal review is lower. Return all positive weekend transactions of at least $500 with Amount, FullName, Description, Vendor, TransactionDate, PostedDate and MCC; sort by Amount descending.",
    6: "Fraud risk: cardholders may keep purchases just under the single-transaction limit. Return positive transactions from $4,750 through $5,000 with all transaction details; sort by Amount descending and FullName.",
    7: "Fraud risk: repeated identical charges may be unauthorized recurring payments. Group positive transactions of at least $100 by FullName, Vendor and Amount; require at least five different dates, and return counts, totals and first/last dates, largest counts first.",
    8: "Fraud risk: concentrated spending with one vendor may indicate an undisclosed relationship. For vendors with at least $10,000 positive spending, return employee-vendor pairs with at least five transactions where one employee represents at least 80% of vendor spending; sort by share and amount descending.",
}


def replace_text(paragraph, text: str, *, normal_color: bool = False) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
        target_runs = paragraph.runs[:1]
    else:
        target_runs = [paragraph.add_run(text)]
    if normal_color:
        for run in target_runs:
            run.italic = False
            run.font.color.rgb = RGBColor(0, 0, 0)
            run_properties = run._element.get_or_add_rPr()
            run_fonts = run_properties.get_or_add_rFonts()
            run_fonts.set(qn("w:ascii"), "Arial")
            run_fonts.set(qn("w:hAnsi"), "Arial")


def fill_part(
    doc: Document,
    *,
    start: int,
    end: int,
    prefix: str,
    results: dict[int, str],
) -> None:
    question = 0
    for index in range(start, end):
        paragraph = doc.paragraphs[index]
        text = paragraph.text.strip()
        if text.startswith("Question") and text[8:].isdigit():
            question = int(text[8:])
            replace_text(paragraph, f"qry_{prefix}_Question{question}", normal_color=True)
        elif text == "[Enter results and conclusion]" and question in results:
            replace_text(paragraph, results[question], normal_color=True)


def main() -> None:
    doc = Document(SOURCE)
    paragraphs = doc.paragraphs

    part_two = next(i for i, p in enumerate(paragraphs) if p.text.strip() == "Part II:")
    part_three = next(i for i, p in enumerate(paragraphs) if p.text.strip() == "Part III:")
    part_four = next(i for i, p in enumerate(paragraphs) if p.text.strip() == "Part IV:")

    for paragraph in paragraphs[part_two:part_three]:
        text = paragraph.text.strip()
        for number, heading in T2_HEADINGS.items():
            if text == f"Control {number}  |  Student-defined internal-control test":
                replace_text(paragraph, heading)
        for number, test in T2_TESTS.items():
            marker = f"Define the student's additional internal-control question {number - 7}."
            if text.startswith(marker):
                replace_text(paragraph, test, normal_color=True)

    for paragraph in paragraphs[part_three:part_four]:
        text = paragraph.text.strip()
        for number, heading in T3_HEADINGS.items():
            if text == f"Question {number}  |  Student-defined fraud test":
                replace_text(paragraph, heading)
        for number, test in T3_TESTS.items():
            marker = {
                5: "Define and perform an additional fraud-focused question",
                6: "Define and perform a second additional fraud-focused question",
                7: "Define and perform a third additional fraud-focused question",
                8: "Define and perform a fourth additional fraud-focused question",
            }[number]
            if text.startswith(marker):
                replace_text(paragraph, test, normal_color=True)

    fill_part(
        doc,
        start=part_two,
        end=part_three,
        prefix="T2",
        results=T2_RESULTS,
    )
    fill_part(
        doc,
        start=part_three,
        end=part_four,
        prefix="T3",
        results=T3_RESULTS,
    )

    doc.core_properties.title = "Completed P-card Analytics Mindset Assignment"
    doc.core_properties.subject = "OSU P-card internal-control and forensic analysis"
    doc.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
