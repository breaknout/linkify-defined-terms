# Repository Instructions

This repository's canonical tool is `scripts/linkify_defined_terms.py`.

When asked to linkify defined terms:

1. Use DOCX input where formatting preservation matters.
2. Run:

   ```bash
   python3 scripts/linkify_defined_terms.py "/path/to/input.docx" -o "/path/to/output-linkified.docx"
   ```

3. Validate that the output DOCX contains internal `dt_` bookmarks and hyperlinks.
4. Confirm visible hyperlink styling: blue `0563C1` and single underline.
5. Confirm paragraph text is preserved.

Do not replace the Python implementation with a plain text extraction workflow.
