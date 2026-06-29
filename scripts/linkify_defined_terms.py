#!/usr/bin/env python3
"""Preserve a DOCX and add visible internal hyperlinks for defined-term uses."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from lxml import etree


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "xml": "http://www.w3.org/XML/1998/namespace",
}
W = f"{{{NS['w']}}}"
XML = f"{{{NS['xml']}}}"
WORD_CHARS = "A-Za-z0-9_"

DEFINITION_PATTERNS = [
    re.compile(
        r'\s*(?:\d+(?:\.\d+)*\.?\s*)?(?:\([A-Za-z0-9]+\)\s*)?["“](?P<term>[^"”]{2,120})["”]\s+'
        r"(?P<verb>means|shall mean|has the meaning|has the same meaning|is defined)",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:\d+(?:\.\d+)*\.?\s*)?(?:\([A-Za-z0-9]+\)\s*)?"
        r"(?P<term>[A-Z][A-Za-z0-9&/,()'-]*"
        r"(?:\s+(?:[A-Z][A-Za-z0-9&/,()'-]*|of|and|or|the|a|an|in|to|for|by|with|on|at|from)){0,7})\s+"
        r"(?P<verb>(?i:means|shall mean|has the meaning|has the same meaning|is defined))",
    ),
]
QUOTED_TERM_ONLY = re.compile(r'^\s*["“](?P<term>[^"”]{2,120})["”]\s*[.:;]?\s*$')
DEFINITION_CONTINUATION = re.compile(r"^\s*(means|shall mean|has the meaning|has the same meaning|is defined)\b", re.IGNORECASE)
INLINE_ALIAS = re.compile(r"\((?:the\s+)?[\"“](?P<term>[^\"”]{2,120})[\"”]\)", re.IGNORECASE)
# Unquoted parenthetical inline definitions, e.g. "... (Confidential Information) will ..."
PAREN_ALIAS_UNQUOTED = re.compile(r"\(\s*(?:the\s+)?(?P<term>[A-Z][^()]{1,79})\)")
ALIAS_CONNECTORS = {"of", "and", "or", "the", "a", "an", "in", "to", "for", "by", "with", "on", "at", "from"}
ALIAS_BLACKLIST = {"cth", "nsw", "vic", "qld", "wa", "sa", "tas", "act", "nt", "cwlth", "commonwealth"}
# Parenthetical is part of a statute/instrument name when followed by Act/Regulations/year, e.g. "(Goods and Services Tax) Act 1999"
STATUTE_TRAILER = re.compile(r"\s*(?:Act|Regulations?|Rules?|Ordinance|Determination|Bill)\b|\s*\d{4}\b", re.IGNORECASE)
# Parenthetical is a citation title (ruling/section/clause N (Title)) rather than a definition
CITATION_LEADER = re.compile(r"(?:ruling|section|clause|item|note|paragraph|schedule)\s*[\w/.-]*\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class TextSegment:
    start: int
    end: int
    text: str
    rpr: etree._Element | None
    hyperlink_attrib: dict[str, str] | None


def clean_term(value: str) -> str:
    return " ".join(value.strip(" .:;").split())


def is_plausible_term(term: str) -> bool:
    if len(term) < 2 or len(term) > 120:
        return False
    if len(term.split()) > 8:
        return False
    return bool(re.search(r"[A-Za-z]", term))


def is_plausible_inline_alias(term: str) -> bool:
    if not is_plausible_term(term):
        return False
    if term[:1].isupper():
        return True
    return bool(re.fullmatch(r"[A-Z0-9][A-Z0-9 /&()-]+", term))


def is_paren_definition(term: str) -> bool:
    term = clean_term(term)
    if len(term) < 2:
        return False
    words = term.split()
    if not (1 <= len(words) <= 6):
        return False
    significant = 0
    for raw in words:
        word = raw.strip(".,:;")
        if not word:
            return False
        if any(ch.isdigit() for ch in word):
            return False
        if word.lower() in ALIAS_CONNECTORS:
            continue
        if not word[0].isupper():
            return False
        if not re.fullmatch(r"[A-Za-z][A-Za-z&/'-]*", word):
            return False
        significant += 1
    if significant == 0:
        return False
    if term.lower() in ALIAS_BLACKLIST:
        return False
    # reject short all-caps roman/list-marker style single tokens (e.g. IV, IT)
    if len(words) == 1 and words[0].isupper() and len(words[0]) < 3:
        return False
    # reject all-caps multi-word instruction text (e.g. BLOCK LETTERS)
    if len(words) > 1 and all(w.strip(".,:;").isupper() for w in words):
        return False
    return True


def paragraph_text(paragraph: etree._Element) -> str:
    return "".join(text_node.text or "" for text_node in paragraph.xpath(".//w:t", namespaces=NS))


def text_segments(paragraph: etree._Element) -> tuple[str, list[TextSegment]]:
    cursor = 0
    parts: list[str] = []
    segments: list[TextSegment] = []
    for run in paragraph.xpath(".//w:r[w:t]", namespaces=NS):
        rpr = run.find(f"{W}rPr")
        hyperlink_attrib = None
        parent = run.getparent()
        while parent is not None and parent is not paragraph:
            if parent.tag == f"{W}hyperlink" and not (parent.get(f"{W}anchor") or "").startswith("dt_"):
                hyperlink_attrib = dict(parent.attrib)
                break
            parent = parent.getparent()
        for text_node in run.findall(f"{W}t"):
            text = text_node.text or ""
            parts.append(text)
            end = cursor + len(text)
            segments.append(TextSegment(cursor, end, text, deepcopy(rpr) if rpr is not None else None, hyperlink_attrib))
            cursor = end
    return "".join(parts), segments


def detect_definitions(paragraphs: Iterable[etree._Element]) -> dict[str, int]:
    paragraph_list = list(paragraphs)
    texts = [paragraph_text(paragraph).strip() for paragraph in paragraph_list]
    definitions: dict[str, int] = {}
    for index, text in enumerate(texts):
        if not text:
            continue
        for alias in INLINE_ALIAS.finditer(text):
            term = clean_term(alias.group("term"))
            if is_plausible_inline_alias(term) and term not in definitions:
                definitions[term] = index
        for alias in PAREN_ALIAS_UNQUOTED.finditer(text):
            term = clean_term(alias.group("term"))
            if STATUTE_TRAILER.match(text[alias.end():alias.end() + 16]):
                continue
            if CITATION_LEADER.search(text[max(0, alias.start() - 20):alias.start()]):
                continue
            if is_paren_definition(term) and term not in definitions:
                definitions[term] = index
        quoted_term = QUOTED_TERM_ONLY.search(text)
        if quoted_term:
            next_text = next((candidate for candidate in texts[index + 1 : index + 4] if candidate), "")
            if DEFINITION_CONTINUATION.search(next_text):
                term = clean_term(quoted_term.group("term"))
                if is_plausible_term(term) and term not in definitions:
                    definitions[term] = index
                continue
        for pattern in DEFINITION_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            term = clean_term(match.group("term"))
            if is_plausible_term(term) and term not in definitions:
                definitions[term] = index
            break
    return definitions


def term_regex(terms: Iterable[str]) -> re.Pattern[str]:
    escaped = sorted((re.escape(term) for term in terms), key=len, reverse=True)
    return re.compile(rf"(?<![{WORD_CHARS}])({'|'.join(escaped)})(?![{WORD_CHARS}])")


def bookmark_name(term: str, used: set[str]) -> str:
    base = "dt_" + re.sub(r"[^A-Za-z0-9_]", "_", term)[:32].strip("_")
    if not base or base == "dt_":
        base = "dt_term"
    name = base
    counter = 2
    while name in used:
        name = f"{base}_{counter}"
        counter += 1
    used.add(name)
    return name


def next_bookmark_id(root: etree._Element) -> int:
    ids = []
    for node in root.xpath(".//w:bookmarkStart", namespaces=NS):
        raw = node.get(f"{W}id")
        if raw and raw.isdigit():
            ids.append(int(raw))
    return (max(ids) + 1) if ids else 1


def remove_existing_skill_marks(root: etree._Element) -> None:
    skill_bookmark_ids = {
        node.get(f"{W}id")
        for node in root.xpath(".//w:bookmarkStart[starts-with(@w:name, 'dt_')]", namespaces=NS)
        if node.get(f"{W}id")
    }
    for hyperlink in list(root.xpath(".//w:hyperlink[starts-with(@w:anchor, 'dt_')]", namespaces=NS)):
        parent = hyperlink.getparent()
        if parent is None:
            continue
        insert_at = parent.index(hyperlink)
        for child in list(hyperlink):
            parent.insert(insert_at, child)
            insert_at += 1
        parent.remove(hyperlink)
    for bookmark in list(root.xpath(".//w:bookmarkStart[starts-with(@w:name, 'dt_')]", namespaces=NS)):
        parent = bookmark.getparent()
        if parent is not None:
            parent.remove(bookmark)
    for bookmark in list(root.xpath(".//w:bookmarkEnd", namespaces=NS)):
        if bookmark.get(f"{W}id") not in skill_bookmark_ids:
            continue
        parent = bookmark.getparent()
        if parent is not None:
            parent.remove(bookmark)


def make_text_run(text: str, rpr: etree._Element | None, hyperlink: bool = False) -> etree._Element:
    run = etree.Element(f"{W}r")
    props = deepcopy(rpr) if rpr is not None else etree.Element(f"{W}rPr")
    if hyperlink:
        for child in list(props):
            if child.tag in {f"{W}color", f"{W}u", f"{W}rStyle"}:
                props.remove(child)
        style = etree.Element(f"{W}rStyle")
        style.set(f"{W}val", "Hyperlink")
        color = etree.Element(f"{W}color")
        color.set(f"{W}val", "0563C1")
        underline = etree.Element(f"{W}u")
        underline.set(f"{W}val", "single")
        props.insert(0, style)
        props.append(color)
        props.append(underline)
    if len(props):
        run.append(props)
    text_node = etree.Element(f"{W}t")
    if text[:1].isspace() or text[-1:].isspace():
        text_node.set(f"{XML}space", "preserve")
    text_node.text = text
    run.append(text_node)
    return run


def append_range(parent: etree._Element, segments: list[TextSegment], start: int, end: int, hyperlink_anchor: str | None = None) -> int:
    if start >= end:
        return 0
    container = parent
    if hyperlink_anchor:
        container = etree.Element(f"{W}hyperlink")
        container.set(f"{W}anchor", hyperlink_anchor)
        container.set(f"{W}history", "1")
        parent.append(container)

    for segment in segments:
        if segment.end <= start or segment.start >= end:
            continue
        local_start = max(start, segment.start) - segment.start
        local_end = min(end, segment.end) - segment.start
        text = segment.text[local_start:local_end]
        if text:
            run = make_text_run(text, segment.rpr, hyperlink=bool(hyperlink_anchor))
            if hyperlink_anchor or not segment.hyperlink_attrib:
                container.append(run)
            else:
                preserved = etree.Element(f"{W}hyperlink")
                for key, value in segment.hyperlink_attrib.items():
                    preserved.set(key, value)
                preserved.append(run)
                container.append(preserved)
    return 1 if hyperlink_anchor else 0


def add_bookmark(paragraph: etree._Element, name: str, bookmark_id: int) -> None:
    start = etree.Element(f"{W}bookmarkStart")
    start.set(f"{W}id", str(bookmark_id))
    start.set(f"{W}name", name)
    end = etree.Element(f"{W}bookmarkEnd")
    end.set(f"{W}id", str(bookmark_id))
    insert_at = 1 if len(paragraph) and paragraph[0].tag == f"{W}pPr" else 0
    paragraph.insert(insert_at, start)
    paragraph.insert(insert_at + 1, end)


def is_definition_span(text: str, match: "re.Match[str]") -> bool:
    """True if this occurrence of the term is the definition itself (so it must
    not be linked), rather than an ordinary use that should be linked."""
    start, end = match.start(), match.end()
    before = text[max(0, start - 8):start]
    after = text[end:end + 24]
    # Quoted definition: "Term" or curly “Term”
    if before[-1:] in {'"', '“'} and after[:1] in {'"', '”'}:
        return True
    # Parenthetical alias: (Term) or (the Term)
    if after[:1] == ")" and "(" in before:
        return True
    # Followed by a defining verb (means / has the meaning / includes / ...)
    if re.match(
        r"\s*(?:means|shall mean|has the meaning|has the same meaning|is defined|includes?)\b",
        after,
        re.IGNORECASE,
    ):
        return True
    return False


def rebuild_paragraph(
    paragraph: etree._Element,
    matches: list[re.Match[str]],
    anchors: dict[str, str],
    defined_here: set[str],
) -> int:
    text, segments = text_segments(paragraph)
    if not text or not segments:
        return 0

    ppr = paragraph.find(f"{W}pPr")
    paragraph[:] = [deepcopy(ppr)] if ppr is not None else []

    cursor = 0
    link_count = 0
    for match in matches:
        term = match.group(1)
        if term in defined_here and is_definition_span(text, match):
            continue
        append_range(paragraph, segments, cursor, match.start())
        link_count += append_range(paragraph, segments, match.start(), match.end(), anchors[term])
        cursor = match.end()
    append_range(paragraph, segments, cursor, len(text))
    return link_count


def copy_docx_with_modified_document(input_path: Path, output_path: Path, document_xml: bytes) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx", dir=str(output_path.parent)) as tmp:
        temp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(input_path, "r") as source, zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                if item.filename == "word/document.xml":
                    target.writestr(item, document_xml)
                else:
                    target.writestr(item, source.read(item.filename))
        shutil.move(str(temp_path), output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def linkify_docx(input_path: Path, output_path: Path) -> dict[str, object]:
    parser = etree.XMLParser(remove_blank_text=False, recover=True)
    with zipfile.ZipFile(input_path, "r") as archive:
        root = etree.fromstring(archive.read("word/document.xml"), parser)

    remove_existing_skill_marks(root)
    paragraphs = root.xpath("//w:body//w:p", namespaces=NS)
    definitions = detect_definitions(paragraphs)
    if not definitions:
        raise RuntimeError("No defined terms were detected. Check that definitions use patterns like 'Term means' or '\"Term\" means'.")

    used_bookmarks: set[str] = set()
    anchors = {term: bookmark_name(term, used_bookmarks) for term in definitions}
    definitions_by_index: dict[int, set[str]] = {}
    for term, index in definitions.items():
        definitions_by_index.setdefault(index, set()).add(term)
    matcher = term_regex(anchors)
    bookmark_id = next_bookmark_id(root)
    hyperlink_count = 0

    for index, paragraph in enumerate(paragraphs):
        text = paragraph_text(paragraph)
        if not text:
            continue
        matches = list(matcher.finditer(text))
        defined_here = definitions_by_index.get(index, set())
        if matches:
            hyperlink_count += rebuild_paragraph(paragraph, matches, anchors, defined_here)
        if defined_here:
            for term in sorted(defined_here):
                add_bookmark(paragraph, anchors[term], bookmark_id)
                bookmark_id += 1

    document_xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    copy_docx_with_modified_document(input_path, output_path, document_xml)
    return {
        "output": str(output_path),
        "terms": [{"term": term, "paragraph": index + 1, "anchor": anchors[term]} for term, index in definitions.items()],
        "hyperlinks": hyperlink_count,
        "mode": "format-preserving-docx",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="Output .docx path")
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    if input_path.suffix.lower() != ".docx":
        raise RuntimeError("Formatting-preserving linkification currently supports .docx input only. Convert the source to DOCX first.")
    output_path = args.output or input_path.with_name(f"{input_path.stem}-linkified.docx")
    result = linkify_docx(input_path, output_path.expanduser().resolve())
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"linkify-defined-terms: {exc}", file=sys.stderr)
        raise SystemExit(1)
