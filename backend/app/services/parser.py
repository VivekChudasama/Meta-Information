import spacy
from docling.document_converter import DocumentConverter
from docling.datamodel.document import SectionHeaderItem, TextItem, ListItem, TableItem

nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
nlp.add_pipe("sentencizer")

# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------


def summarize(text: str, max_sentences: int = 5) -> str:
    """
    Extractive summarizer using spaCy POS tags only.

    1. Segment into sentences.
    2. Drop too-short: fewer than 5 non-punct tokens.
    3. Drop low-density: content tokens (NOUN, PROPN, VERB, non-stop) < 30% of sentence.
    4. Remove duplicate sentences: if two sentences share >60% word overlap, drop the later one.
    5. Return first max_sentences joined as a paragraph.
    """
    doc = nlp(text.strip())

    kept: list[str] = []
    seen: list[set] = []

    # Iterate over sentences in the document
    for sent in doc.sents:
        # Remove punctuation and whitespace tokens
        tokens = [t for t in sent if not t.is_space and not t.is_punct]

        # filter 1 — too short
        if len(tokens) < 5:
            continue

        # filter 2 — density:  It identifies "content words" (Nouns, Proper Nouns, and Verbs) 
        # while ignoring "stop words" (common fillers like "and", "the", "is").
        content = [
            t for t in tokens if t.pos_ in {"NOUN", "PROPN", "VERB"} and not t.is_stop
        ]
        if not content or len(content) / len(tokens) < 0.30:
            continue

        # filter 3 — Remove duplicate sentences via word overlap
        words = {t.text.lower() for t in content}
        duplicate = any(
            # If the overlap is greater than 60%, the sentence is considered a duplicate and skipped.
            len(words & prev) / max(len(words | prev), 1) > 0.60 for prev in seen 
        )
        if duplicate:
            continue

        kept.append(sent.text.strip())
        seen.append(words)

        if len(kept) == max_sentences:
            break

    return " ".join(kept) if kept else text


# ---------------------------------------------------------------------------
# Document parsing
# ---------------------------------------------------------------------------


def get_text(element) -> str:
    return element.text.strip() if hasattr(element, "text") and element.text else ""


def render_conclusion(sections: list[dict]) -> str:
    s = next(
        (s for s in sections if s["heading"] and "conclusion" in s["heading"].lower()),
        None,
    )
    if not s:
        return "\n No Conclusion section detected.\n"
    return f"\n### {s['heading']}\n\n" + "\n".join(s["content"]) + "\n"


def parse_docx_to_markdown(filepath: str) -> str:
    if filepath.lower().endswith(".docx"):
        from docx import Document as RawDocx

        doc = RawDocx(filepath)

        first_page, headings, sections = [], [], []
        current = {"heading": None, "level": 0, "content": []}
        page_done = False

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            has_break = any(
                br.get(
                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type"
                )
                == "page"
                for run in p.runs
                for br in run._element.findall(
                    ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br"
                )
            )

            if not page_done:
                first_page.append(text)
                if has_break or len(" ".join(first_page).split()) >= 500:
                    page_done = True

            level = 0
            style = p.style.name if p.style else ""
            if style.startswith("Heading"):
                try:
                    level = int(style.split()[-1])
                except ValueError:
                    pass

            if level in (1, 2):
                headings.append((level, text))
                sections.append(dict(current))
                current = {"heading": text, "level": level, "content": []}
            else:
                current["content"].append(text)

        sections.append(current)

        out = summarize(" ".join(first_page), max_sentences=4) + "\n\n"
        out += "HEADINGS\n"
        out += (
            "\n".join(f"{'  ' * (l - 1)}[H{l}] {t}" for l, t in headings)
            or "No H1 or H2 headings detected."
        )
        out += render_conclusion([s for s in sections if s["heading"]])
        return out

    # PDF fallback via docling
    if not hasattr(parse_docx_to_markdown, "converter"):
        parse_docx_to_markdown.converter = DocumentConverter()
    doc = parse_docx_to_markdown.converter.convert(filepath).document

    def iter_items(page_only=False):
        for el, level in doc.iterate_items():
            if isinstance(el, TableItem) or not isinstance(
                el, (TextItem, ListItem, SectionHeaderItem)
            ):
                continue
            if page_only:
                try:
                    if not el.prov or el.prov[0].page_no != 1:
                        continue
                except (AttributeError, IndexError):
                    pass
            yield el, level

    first_page_str = " ".join(
        get_text(el) for el, _ in iter_items(page_only=True) if get_text(el)
    )
    out = "IMPORTANT CONTEXT (First Page - Top 20%)\n"
    out += summarize(first_page_str, max_sentences=4) + "\n\n"
    out += "HEADINGS\n"

    headings, sections = [], []
    current = {"heading": None, "level": 0, "content": []}

    for el, level in iter_items():
        text = get_text(el)
        if not text:
            continue
        if isinstance(el, SectionHeaderItem) and level in (1, 2):
            headings.append((level, text))
            out += f"{'  ' * (level - 1)}[H{level}] {text}\n"
            sections.append(dict(current))
            current = {"heading": text, "level": level, "content": []}
        else:
            current["content"].append(text)

    sections.append(current)
    if not headings:
        out += "No H1 or H2 headings detected.\n"

    out += render_conclusion([s for s in sections if s["heading"]])
    return out
