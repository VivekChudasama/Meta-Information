import re
import heapq
from collections import Counter
import spacy
from dataclasses import dataclass
from docling.document_converter import DocumentConverter
from docling.datamodel.document import SectionHeaderItem, TextItem, ListItem, TableItem

nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
nlp.add_pipe("sentencizer")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FLUFF_PATTERNS = re.compile(
    r"(?i)("
    r"in this (guide|article|post|blog|section|video|paper|document),? you('ll| will) (understand|learn|find|discover|know)"
    r"|by the end of this (guide|article|post|blog|section)"
    r"|without (further|any) delay,? let's (begin|start|dive in)"
    r"|now the question is"
    r"|no worries,? we have you covered"
    r"|we have (carefully )?selected"
    r"|let's (begin|start|get started)"
    r"|^(table of contents|contents|abstract|acknowledgments?|acknowledgements?|copyright|all rights reserved|disclaimer|introduction|overview):?\s*$"
    r"|^page \d+ of \d+"
    r"|this (paper|article|document|study) (presents|discusses|examines|explores)"
    r"|the (purpose|goal|aim|objective) of this (paper|study|article)"
    r"|that'?s where .+ comes? in"
    r"|(widely|commonly|frequently) used (in|across|for)"
    r"|(these|this|it) (can be|is|are) (applied|used|utilized) in"
    r"|has (many|numerous|several|various) (applications|uses)"
    r")"
)

SKIP_SECTIONS = {
    "acknowledgments", "acknowledgements", "references",
    "table of contents", "contents", "copyright",
    "disclaimer", "about the author", "about the authors",
}

DEF_PATTERN = re.compile(r"\b(is a|are|refers to|defined as|means|represents)\b", re.I)
CHAR_PATTERN = re.compile(r"\b(key|main|primary|characteristic|feature|attribute|propert(y|ies))\b", re.I)


@dataclass
class ParsedSentence:
    text: str
    tokens_count: int
    keywords_list: list[str]
    keywords_set: set[str]
    is_heading: bool
    num_ratio: float

# ---------------------------------------------------------------------------
# spaCy helpers & Core Structures
# ---------------------------------------------------------------------------

def parse_sentences(text: str) -> list[ParsedSentence]:
    """Parse text into structured sentence objects to avoid redundant NLP overhead."""
    doc = nlp(text.strip())
    parsed = []
    for s in doc.sents:
        s_text = s.text.strip()
        if not s_text:
            continue
            
        keywords_list = []
        num_count = 0
        total_tokens = 0
        for t in s:
            if not t.is_space:
                total_tokens += 1
                if t.like_num:
                    num_count += 1
                if not t.is_stop and not t.is_punct and not t.like_num and len(t.lemma_) > 2:
                    keywords_list.append(t.lemma_.lower())
                    
        num_ratio = num_count / total_tokens if total_tokens > 0 else 0.0
        is_heading = total_tokens <= 10 and re.match(r"^[A-Z]", s_text) and not s_text.endswith(".")
        
        parsed.append(ParsedSentence(
            text=s_text,
            tokens_count=total_tokens,
            keywords_list=keywords_list,
            keywords_set=set(keywords_list),
            is_heading=bool(is_heading),
            num_ratio=num_ratio
        ))
    return parsed

def jaccard_sets(t1: set, t2: set) -> float:
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)

# ---------------------------------------------------------------------------
# Sentence-level filters
# ---------------------------------------------------------------------------

def is_fluff(sent: ParsedSentence) -> bool:
    if sent.tokens_count < 5 or sent.text.lower().strip() in SKIP_SECTIONS:
        return True
    if sent.num_ratio > 0.5:
        return True
    return bool(FLUFF_PATTERNS.search(sent.text))

def dedup_headings(sentences: list[ParsedSentence]) -> list[ParsedSentence]:
    seen, out = set(), []
    for s in sentences:
        if s.is_heading:
            key = " ".join(sorted(s.keywords_list))
            if key in seen:
                continue
            seen.add(key)
        out.append(s)
    return out

def dedup_similar(sentences: list[ParsedSentence], threshold: float = 0.7) -> list[ParsedSentence]:
    skip, out = set(), []
    for i, s1 in enumerate(sentences):
        if i in skip:
            continue
        for j in range(i + 1, len(sentences)):
            if j not in skip and jaccard_sets(s1.keywords_set, sentences[j].keywords_set) >= threshold:
                skip.add(j if len(s1.text) <= len(sentences[j].text) else i)
        if i not in skip:
            out.append(s1)
    return out

def merge_defs(sentences: list[ParsedSentence]) -> list[ParsedSentence]:
    """Merge definition sentences with the nearest characteristic sentence."""
    def_idx  = [i for i, s in enumerate(sentences) if DEF_PATTERN.search(s.text)]
    char_idx = [i for i, s in enumerate(sentences) if CHAR_PATTERN.search(s.text)]
    if not (def_idx and char_idx):
        return sentences

    used, merged = set(), []
    for d in def_idx:
        if d in used:
            continue
        best = min((c for c in char_idx if c not in used), key=lambda c: abs(d - c), default=None)
        if best is not None and abs(d - best) <= 3:
            s_d = sentences[d]
            s_best = sentences[best]
            combined = ParsedSentence(
                text=s_d.text + " " + s_best.text,
                tokens_count=s_d.tokens_count + s_best.tokens_count,
                keywords_list=s_d.keywords_list + s_best.keywords_list,
                keywords_set=s_d.keywords_set | s_best.keywords_set,
                is_heading=False,
                num_ratio=max(s_d.num_ratio, s_best.num_ratio)
            )
            merged.append(combined)
            used.update({d, best})
        else:
            merged.append(sentences[d])
            used.add(d)

    remainder = [s for i, s in enumerate(sentences) if i not in used]
    return merged + remainder

# ---------------------------------------------------------------------------
# Core optimizer
# ---------------------------------------------------------------------------

def clean_and_score(text: str, retention_ratio: float = 0.25) -> str:
    """Return the top `retention_ratio` fraction of sentences by info density."""
    sents = [s for s in parse_sentences(text) if not is_fluff(s)]
    sents = merge_defs(dedup_similar(dedup_headings(sents)))

    if not sents:
        return ""

    all_keywords = []
    for s in sents:
        all_keywords.extend(s.keywords_list)

    if not all_keywords:
        return " ".join(s.text for s in sents[:2])

    freq  = Counter(all_keywords)
    max_f = max(freq.values())
    wf    = {w: f / max_f for w, f in freq.items()}

    scores = []
    for s in sents:
        if not s.keywords_list:
            scores.append(0.0)
            continue
        score = sum(wf.get(w, 0) for w in s.keywords_list) / len(s.keywords_list)
        scores.append(score)

    top_count = max(1, int(len(sents) * retention_ratio))
    top_indices = set(heapq.nlargest(top_count, range(len(scores)), key=lambda i: scores[i]))
    return " ".join(s.text for i, s in enumerate(sents) if i in top_indices)


# ---------------------------------------------------------------------------
# Document parsing
# ---------------------------------------------------------------------------

def get_text(element) -> str:
    return element.text.strip() if hasattr(element, "text") and element.text else ""


def render_conclusion(sections: list[dict]) -> str:
    s = next((s for s in sections if s["heading"] and "conclusion" in s["heading"].lower()), None)
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
                br.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type") == "page"
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

        out  = clean_and_score(" ".join(first_page), retention_ratio=0.20) + "\n\n"
        out += "HEADINGS\n"
        out += "\n".join(f"{'  ' * (l-1)}[H{l}] {t}" for l, t in headings) or "No H1 or H2 headings detected."
        out += render_conclusion([s for s in sections if s["heading"]])
        return out

    # PDF fallback via docling
    # Initialize DocumentConverter once to avoid heavy initialization overhead
    if not hasattr(parse_docx_to_markdown, "converter"):
        parse_docx_to_markdown.converter = DocumentConverter()
    doc = parse_docx_to_markdown.converter.convert(filepath).document

    def iter_items(page_only=False):
        for el, level in doc.iterate_items():
            if isinstance(el, TableItem) or not isinstance(el, (TextItem, ListItem, SectionHeaderItem)):
                continue
            if page_only:
                try:
                    if not el.prov or el.prov[0].page_no != 1:
                        continue
                except (AttributeError, IndexError):
                    pass
            yield el, level

    first_page_str = " ".join(get_text(el) for el, _ in iter_items(page_only=True) if get_text(el))
    out  = "IMPORTANT CONTEXT (First Page - Top 20%)\n"
    out += clean_and_score(first_page_str, retention_ratio=0.20) + "\n\n"
    out += "HEADINGS\n"

    headings, sections = [], []
    current = {"heading": None, "level": 0, "content": []}

    for el, level in iter_items():
        text = get_text(el)
        if not text:
            continue
        if isinstance(el, SectionHeaderItem) and level in (1, 2):
            headings.append((level, text))
            out += f"{'  ' * (level-1)}[H{level}] {text}\n"
            sections.append(dict(current))
            current = {"heading": text, "level": level, "content": []}
        else:
            current["content"].append(text)

    sections.append(current)
    if not headings:
        out += "No H1 or H2 headings detected.\n"

    out += render_conclusion([s for s in sections if s["heading"]])
    return out