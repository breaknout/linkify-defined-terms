---
name: linkify-defined-terms
description: Create a format-preserving Microsoft Word .docx from a contract, legislation, regulation, or other legal document that contains defined terms, and embed visible internal hyperlinks so every detected use of each defined term links to the term's definition. Use when the input is a .docx file and the user wants defined terms cross-linked to their meanings while retaining the original Word formatting.
---

# Linkify Defined Terms

Use `scripts/linkify_defined_terms.py` as the primary implementation. It accepts `.docx` inputs and writes a new `.docx` with bookmarks at definitions and visible blue underlined internal hyperlinks for detected defined-term uses.

For PDF, RTF, HTML, or other input formats, convert to DOCX first. Do not use text extraction as the main path when formatting preservation matters.

Validate the generated DOCX by checking that the JSON report is plausible, `word/document.xml` contains `w:bookmarkStart` and `w:hyperlink w:anchor` entries, and hyperlink runs include `w:u w:val="single"` plus `w:color w:val="0563C1"`.
