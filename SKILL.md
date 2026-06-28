---
name: linkify-defined-terms
description: Create a format-preserving Microsoft Word .docx from a contract, legislation, regulation, or other legal document that contains defined terms, and embed visible internal hyperlinks so every detected use of each defined term links to the term's definition. Use when the input is a .docx file and the user wants defined terms cross-linked to their meanings while retaining the original Word formatting.
---

# Linkify Defined Terms

## Workflow

Use `scripts/linkify_defined_terms.py` as the primary implementation. It accepts `.docx` inputs and writes a new `.docx` containing:

- bookmarks at detected defined-term definitions
- visible Word internal hyperlinks for detected uses of those terms, with blue underlined text
- a JSON report listing detected terms, bookmark anchors, and hyperlink count

Run it like this:

```bash
python3 /path/to/linkify-defined-terms/scripts/linkify_defined_terms.py "/path/to/input.docx" -o "/path/to/output-linkified.docx"
```

If the user provides a PDF, RTF, HTML, or other format, convert it to DOCX first using the best available converter, then run the script on the DOCX. Do not use text extraction as the main path because that does not retain the original formatting.

If the user does not provide an output name, use the source stem plus `-linkified.docx` beside the input, unless that would overwrite an existing important file.

## Validation

After creating the DOCX, verify the result before responding:

1. Confirm the script reported at least one detected term.
2. Confirm the hyperlink count is plausible for the document.
3. Inspect `word/document.xml` inside the DOCX zip and confirm it contains `w:bookmarkStart` elements and `w:hyperlink w:anchor` elements.
4. Spot-check at least one hyperlink run and confirm it has explicit `w:u w:val="single"` and `w:color w:val="0563C1"` formatting.

If no terms are detected, explain that the helper recognizes common definition patterns such as `"Term" means`, `Term means`, `Term shall mean`, `Term has the meaning`, `Term is defined`, split glossary definitions where a paragraph containing only `"Term"` is followed by `means...` or `has the meaning...`, and inline aliases like `each party ("Disclosing Party")`. Offer to adjust the detection pattern if the source document uses a different drafting style.

## Notes

- The script edits `word/document.xml` in the original DOCX package, preserving the existing document package, section settings, paragraph styles, and run-level formatting for ordinary text runs.
- Paragraphs containing linked terms are rebuilt from their text runs; complex fields or unusual inline objects inside those paragraphs may need spot-checking.
- Existing non-skill hyperlinks in rebuilt paragraphs are preserved unless the same text is replaced by a defined-term internal link.
- Definitions are detected from paragraph text. Terms are matched case-sensitively as written in the definition.
- The defining occurrence of the term is bookmarked rather than hyperlinked to itself; other defined terms used inside a definition are still linked.
- For non-DOCX sources, convert to DOCX first if retaining source formatting matters.
