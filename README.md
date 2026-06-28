# Linkify Defined Terms

A portable Python tool for legal documents that preserves a Microsoft Word `.docx` file and turns uses of defined terms into visible internal hyperlinks.

The core implementation is agent-agnostic. Optional wrappers are included for Codex, Claude Cowork, and Copilot Cowork.

## What it does

- Detects common defined-term drafting patterns.
- Adds Word bookmarks at definition locations.
- Wraps detected term uses in internal hyperlinks.
- Makes links visibly blue and underlined.
- Preserves paragraph text and existing non-skill hyperlinks.
- Emits a JSON report with detected terms and link counts.

The tool edits the original Word XML package rather than rebuilding a plain-text document, so ordinary paragraph styles, run styling, section settings, and existing non-skill hyperlinks are retained.

## Input support

Use `.docx` input when formatting matters. Convert PDF, RTF, HTML, or other formats to DOCX first, then run this tool.

The detector recognizes patterns including:

- `"Term" means ...`
- `Term means ...`
- `Term shall mean ...`
- `Term has the meaning ...`
- `Term is defined ...`
- glossary layouts where a paragraph containing only `"Term"` is followed by `means...` or `has the meaning...`
- inline aliases such as `each party ("Disclosing Party")`

## Quick Start

```bash
python3 -m pip install -r requirements.txt
python3 scripts/linkify_defined_terms.py "/path/to/input.docx" -o "/path/to/output-linkified.docx"
```

The command prints JSON with the output path, detected terms, anchors, and hyperlink count.

## Agent Install Options

This repository supports both direct CLI use and agent-skill installation.

### Codex

Codex can use the repository root directly because it contains `SKILL.md`, `agents/openai.yaml`, and `scripts/`:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/breaknout/linkify-defined-terms.git "${CODEX_HOME:-$HOME/.codex}/skills/linkify-defined-terms"
```

Then ask:

```text
Use $linkify-defined-terms on /path/to/agreement.docx
```

### GitHub Copilot Cowork / Copilot Coding Agent

GitHub Copilot supports reusable agent skills with `SKILL.md`. This repository includes the skill in GitHub's conventional locations:

```text
.github/skills/linkify-defined-terms/
.agents/skills/linkify-defined-terms/
skills/linkify-defined-terms/
```

For GitHub's skill installer, use:

```bash
gh extension install github/gh-copilot
gh skill install breaknout/linkify-defined-terms linkify-defined-terms
```

For a project-local install, copy:

```text
.github/skills/linkify-defined-terms/
```

into the target repository.

The repository also includes `.github/copilot-instructions.md` for Copilot environments that read repository instructions.

### Claude Cowork / Claude-Style Agents

Claude-style agents can use the included project skill directory:

```text
.claude/skills/linkify-defined-terms/
```

Copy that folder into the Claude Cowork project or user skill location used by your environment, then ask:

```text
Use linkify-defined-terms on /path/to/agreement.docx
```

### Generic Agent Skill

For agents that follow the emerging shared agent-skill convention, use:

```text
.agents/skills/linkify-defined-terms/
```

## Validation

The tool has been tested against 15 smaller public contracts and one large Australian tax legislation compilation. The smaller-contract suite checked:

- internal bookmarks match detected terms
- internal hyperlinks match the report count
- hyperlink anchors resolve to bookmarks
- hyperlink text has explicit blue and underline styling
- paragraph text is preserved
- existing non-skill hyperlinks are preserved

See [examples/validation-summary.md](examples/validation-summary.md).

## Limitations

- DOCX input is required for formatting-preserving operation.
- Paragraphs containing linked terms are rebuilt from their text runs; complex fields, equations, content controls, tracked changes, comments, or unusual inline objects in those paragraphs should be spot-checked.
- Detection is drafting-pattern based. Unusual definition styles may need a pattern update.
- Terms are matched case-sensitively as written in the definition.

## License

MIT License. See [LICENSE](LICENSE).
