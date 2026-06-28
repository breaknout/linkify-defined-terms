# Validation Summary

The skill was tested on public legal contract examples and one large legislation compilation.

## Public Contract Tests

Common Paper standard agreement DOCX files were used for a 10-contract regression suite:

| Contract | Terms | Links | Result |
|---|---:|---:|---:|
| Mutual NDA | 6 | 85 | PASS |
| Cloud Service Agreement | 33 | 408 | PASS |
| Service Level Agreement | 40 | 459 | PASS |
| Data Processing Agreement | 17 | 208 | PASS |
| Business Associate Agreement | 17 | 154 | PASS |
| Professional Services Agreement | 22 | 336 | PASS |
| AI Addendum | 7 | 94 | PASS |
| Partnership Agreement | 19 | 246 | PASS |
| Software License Agreement | 32 | 317 | PASS |
| Pilot Agreement | 17 | 190 | PASS |

A 5-contract showcase suite was also run:

| Contract | Terms | Links | Result |
|---|---:|---:|---:|
| Design Partner Agreement | 9 | 154 | PASS |
| Cloud Service Agreement with AI | 40 | 525 | PASS |
| Software License Agreement with AI | 40 | 512 | PASS |
| AI Addendum in-app | 7 | 93 | PASS |
| ISDA 2002 Master Agreement SEC exhibit | 71 | 998 | PASS |

## Review Passes

Each contract output was checked for:

- bookmarks matching detected terms
- internal hyperlinks matching the generated report
- all internal anchors resolving to bookmarks
- visible blue and underlined hyperlink runs
- paragraph text preservation
- preservation of existing non-skill hyperlinks

## Sources

- Common Paper standard agreements: https://commonpaper.com/standards/
- ISDA 2002 Master Agreement SEC exhibit: https://www.sec.gov/Archives/edgar/data/1065696/000119312511118050/dex101.htm

Do not assume these public agreements are legal advice or suitable for any particular use.
