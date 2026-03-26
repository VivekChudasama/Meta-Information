import nltk

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.luhn import LuhnSummarizer
from sumy.utils import get_stop_words
from sumy.nlp.stemmers import Stemmer

from docling.document_converter import DocumentConverter
from docling.datamodel.document import SectionHeaderItem, TextItem, ListItem, TableItem

# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------


def summarize(text: str, max_sentences: int = 4) -> str:
    """
    Optimized Extractive summarizer using Sumy's LuhnSummarizer with stemming.
    """
    text = text.strip()
    
    # Early exit: If text is empty or already shorter than the target length, just return it.
    if not text or len(text.split('.')) <= max_sentences:
        return text

    try:
        # Initialize parser and tokenizer
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        
        # Initialize the Stemmer to group word variations
        stemmer = Stemmer("english")
        
        # Pass the stemmer directly into the LuhnSummarizer
        summarizer = LuhnSummarizer(stemmer)
        summarizer.stop_words = get_stop_words("english")
        
        # Extract the most significant sentences (requesting slightly more to filter duplicates)
        summary = summarizer(parser.document, max_sentences + 2)
        
        kept = []
        seen_word_sets = []
        
        for sentence in summary:
            sent_text = str(sentence).strip()
            # Create a basic word set for deduplication check
            words = set(sent_text.lower().split())
            
            # If two sentences share >60% of the same words, they are duplicates
            # We want to keep the longer/richer one
            duplicate_idx = next(
                (i for i, seen in enumerate(seen_word_sets) 
                 if len(words & seen) / max(len(words | seen), 1) > 0.60),
                None
            )

            if duplicate_idx is None:
                kept.append(sent_text)
                seen_word_sets.append(words)
            else:
                # Prefer the longer sentence if they are similar
                if len(sent_text) > len(kept[duplicate_idx]):
                    kept[duplicate_idx] = sent_text
                    seen_word_sets[duplicate_idx] = words
            
            if len(kept) == max_sentences:
                break
        
        return " ".join(kept) if kept else text
        
    except Exception as e:
        print(f"Sumy Luhn summarizer error: {e}")
        return text
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

            if not page_done:
                # Inspect each run to find the exact point where a page breaks
                paragraph_text_on_page = []
                for run in p.runs:
                    # Check for hard page breaks or rendered page breaks in the run
                    has_run_break = any(
                        br.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type") == "page"
                        for br in run._element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br")
                    ) or run._element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}lastRenderedPageBreak")

                    if has_run_break:
                        page_done = True
                        break
                    paragraph_text_on_page.append(run.text)
                
                first_page_text = "".join(paragraph_text_on_page).strip()
                if first_page_text:
                    first_page.append(first_page_text)
                
                # Global fallback limit if no page break is found
                if len(" ".join(first_page).split()) >= 210:
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

        out = summarize("\n".join(first_page), max_sentences=5) + "\n\n"
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

    first_page_str = "\n".join(
        get_text(el) for el, _ in iter_items(page_only=True) if get_text(el)
    )
    out = "IMPORTANT CONTEXT\n"
    out += summarize(first_page_str, max_sentences=5) + "\n\n"
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
