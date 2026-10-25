"""The Singapore timeline the plates annotate, and nothing they do not.

Two kinds of entry, both used by plates.py through `_mark`:

  EVENTS  a calendar year a note refers to by name. Kept short — an
          annotation that wraps twice is a paragraph, and the page has
          paragraphs for those.

  MARKS   a precise marker (year.fraction) for a rule that belongs
          between two years rather than on one.

The dates here are the seams DATA_NOTES.md section 11 requires to be
annotated, plus the two the recession bands already carry from
country.yaml:

  2008 Q2 – 2009 Q1   four negative quarters, banded 2008.25–2009.25
  2012                ICD-9 to ICD-10 in the cause-of-death groups
  2020 Q1 – Q2        two negative quarters, banded 2020.0–2020.5
  2025                the publisher's preliminary cause-of-death year

Deliberately NOT here: a "COVID-19" event line. The bands already mark
2020, and a second vertical rule on the same year is one rule too many.
"""

# year -> the short label a panel would use if it annotates that year.
EVENTS = {
    2012: "ICD-9 to ICD-10 in the cause-of-death groups",
    2025: "preliminary: external causes still being assigned",
}

# key -> (x, label). The x is year.fraction: a coding change belongs
# between the last ICD-9 year (2011) and the first ICD-10 one (2012).
MARKS = {
    "icd": (2011.5, "2012: ICD-9 to ICD-10"),
    "prelim": (2024.5, "2025 preliminary"),
}
