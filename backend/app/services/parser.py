import re
import heapq
from collections import Counter
from docling.document_converter import DocumentConverter
from docling.datamodel.document import (
    SectionHeaderItem,
    TextItem,
    ListItem,
    TableItem,
)


class LLMContextOptimizer:
    def __init__(self):
        # Patterns to remove "meta-talk" and fluff that wastes tokens
        self.fluff_patterns = [
            r"(?i)in this (guide|article|post|blog|section|video|paper|document),? you('ll| will) (understand|learn|find|discover|know).*",
            r"(?i)by the end of this (guide|article|post|blog|section).*",
            r"(?i)without (further|any) delay,? let's (begin|start|dive in).*",
            r"(?i)now the question is.*",
            r"(?i)no worries,? we have you covered.*",
            r"(?i)we have (carefully )?selected.*",
            r"(?i)let's (begin|start|get started).*",
            r"(?i)^(table of contents|contents|abstract|acknowledgment|acknowledgement)s?:?\s*$",
            r"(?i)^(copyright|all rights reserved|disclaimer).*",
            r"(?i)^page \d+ of \d+.*",
            r"(?i)^(introduction|overview)\s*$",  # Skip lone section headers
            r"(?i)this (paper|article|document|study) (presents|discusses|examines|explores).*",
            r"(?i)the (purpose|goal|aim|objective) of this (paper|study|article).*",
            # NEW: Specific filler phrase patterns
            r"(?i)that'?s where .+ comes? in\.?",
            r"(?i)used across (different|various|many) (industries|sectors|fields|domains)\.?",
            r"(?i)(widely|commonly|frequently) used (in|across|for).*",
            r"(?i)(these|this|it) (can be|is|are) (applied|used|utilized) in.*",
            r"(?i)has (many|numerous|several|various) (applications|uses).*",
        ]

        # Boilerplate sections to skip entirely
        self.skip_sections = {
            "acknowledgments",
            "acknowledgements",
            "references",
            "table of contents",
            "contents",
            "copyright",
            "disclaimer",
            "about the author",
            "about the authors",
        }

        # Common filler words (Stopwords)
        self.stop_words = set(
            [
                "the",
                "is",
                "and",
                "to",
                "a",
                "in",
                "that",
                "of",
                "it",
                "with",
                "for",
                "as",
                "on",
                "at",
                "this",
                "by",
                "an",
                "be",
                "or",
                "are",
                "from",
                "your",
                "will",
                "you",
                "can",
                "we",
                "our",
                "if",
                "so",
                "but",
                "not",
                "they",
                "was",
                "were",
            ]
        )

    def should_skip_sentence(self, sentence):
        """Check if sentence is boilerplate and should be skipped."""
        sentence_lower = sentence.lower().strip()

        # Skip very short sentences (likely fragments or page numbers)
        if len(sentence.split()) < 5:
            return True

        # Skip sentences that are just section headers
        if sentence_lower in self.skip_sections:
            return True

        # Skip sentences that are mostly numbers or dates
        words = sentence.split()
        num_count = sum(1 for w in words if re.search(r"\d", w))
        if len(words) > 0 and num_count / len(words) > 0.5:
            return True

        return False

    def get_sentence_tokens(self, sentence):
        """Extract meaningful tokens from sentence for similarity comparison."""
        # Remove punctuation and convert to lowercase
        clean = re.sub(r"[^\w\s]", "", sentence.lower())
        words = clean.split()
        # Filter out stop words
        return set(w for w in words if w not in self.stop_words and len(w) > 2)

    def is_redundant(self, sent1, sent2, threshold=0.7):
        """Check if two sentences are redundant (similar content)."""
        tokens1 = self.get_sentence_tokens(sent1)
        tokens2 = self.get_sentence_tokens(sent2)

        if not tokens1 or not tokens2:
            return False

        # Calculate Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        similarity = intersection / union if union > 0 else 0

        return similarity >= threshold

    def remove_redundant_sentences(self, sentences):
        """Remove redundant/duplicate sentences, keeping the shorter one."""
        if len(sentences) <= 1:
            return sentences

        filtered = []
        skip_indices = set()

        for i, sent1 in enumerate(sentences):
            if i in skip_indices:
                continue

            # Check against all previous sentences
            is_duplicate = False
            for j in range(i + 1, len(sentences)):
                if j in skip_indices:
                    continue

                sent2 = sentences[j]
                if self.is_redundant(sent1, sent2):
                    # Keep the shorter, more concise sentence
                    if len(sent1.split()) <= len(sent2.split()):
                        skip_indices.add(j)
                    else:
                        is_duplicate = True
                        break

            if not is_duplicate:
                filtered.append(sent1)

        return filtered

    def remove_duplicate_headings(self, sentences):
        """Detect and remove duplicate headings."""
        seen_headings = set()
        filtered = []

        for sent in sentences:
            # Detect if sentence is likely a heading (short, title-case, ends with ? or no punctuation)
            is_heading = (
                len(sent.split()) <= 10
                and (sent.endswith("?") or not sent.endswith("."))
                and re.search(r"^[A-Z]", sent)
            )

            if is_heading:
                # Normalize heading for comparison
                normalized = re.sub(r"[^\w\s]", "", sent.lower()).strip()
                if normalized in seen_headings:
                    continue  # Skip duplicate heading
                seen_headings.add(normalized)

            filtered.append(sent)

        return filtered

    def merge_definitions_with_characteristics(self, sentences):
        """Merge definition sentences with characteristic sentences for density."""
        # Identify definition sentences
        definition_indices = []
        characteristic_indices = []

        for i, sent in enumerate(sentences):
            # Definition patterns
            if re.search(
                r"\b(is a|are|refers to|defined as|means|represents)\b",
                sent,
                re.IGNORECASE,
            ):
                definition_indices.append(i)
            # Characteristic patterns
            elif re.search(
                r"\b(key|main|primary|characteristic|feature|attribute|property|properties)\b",
                sent,
                re.IGNORECASE,
            ):
                characteristic_indices.append(i)

        # If we have both definitions and characteristics, merge them
        if definition_indices and characteristic_indices:
            merged = []
            used_indices = set()

            for def_idx in definition_indices:
                if def_idx in used_indices:
                    continue

                # Find the closest characteristic sentence
                closest_char_idx = None
                min_distance = float("inf")

                for char_idx in characteristic_indices:
                    if char_idx in used_indices:
                        continue
                    distance = abs(def_idx - char_idx)
                    if distance < min_distance:
                        min_distance = distance
                        closest_char_idx = char_idx

                # Merge if found nearby (within 3 sentences)
                if closest_char_idx is not None and min_distance <= 3:
                    merged.append(
                        sentences[def_idx] + " " + sentences[closest_char_idx]
                    )
                    used_indices.add(def_idx)
                    used_indices.add(closest_char_idx)
                else:
                    merged.append(sentences[def_idx])
                    used_indices.add(def_idx)

            # Add remaining sentences that weren't merged
            for i, sent in enumerate(sentences):
                if i not in used_indices:
                    merged.append(sent)

            return merged

        return sentences

    def clean_fluff(self, text):
        """Removes instructional filler sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        # Step 1: Remove fluff patterns and skip sentences
        filtered = [
            s
            for s in sentences
            if not any(re.search(p, s) for p in self.fluff_patterns)
            and not self.should_skip_sentence(s)
        ]

        # Step 2: Remove duplicate headings
        filtered = self.remove_duplicate_headings(filtered)

        # Step 3: Remove redundant sentences (definitions that say same thing)
        filtered = self.remove_redundant_sentences(filtered)

        # Step 4: Merge definitions with characteristics
        filtered = self.merge_definitions_with_characteristics(filtered)

        return filtered

    def extract_dynamic_context(self, text, retention_ratio=0.25):
        """
        Dynamically finds the most important sentences in any text.
        Default retention_ratio is 0.25 (25%) for aggressive token optimization.
        """
        # 1. Pre-clean fluff
        sentences = self.clean_fluff(text)
        if not sentences:
            return ""

        # 2. Score word importance (Frequency Analysis)
        words = re.findall(r"\w+", " ".join(sentences).lower())
        significant_words = [
            w for w in words if w not in self.stop_words and not w.isdigit()
        ]

        if not significant_words:
            return " ".join(sentences[:2])

        word_freq = Counter(significant_words)
        max_freq = max(word_freq.values())
        word_weighted_freq = {word: freq / max_freq for word, freq in word_freq.items()}

        # 3. Score Sentences by Information Density + Importance Signals
        sentence_scores = {}
        for sentence in sentences:
            sentence_words = re.findall(r"\w+", sentence.lower())
            if not sentence_words:
                continue

            # Base score: word frequency
            base_score = sum(word_weighted_freq.get(w, 0) for w in sentence_words)
            density_score = base_score / len(sentence_words)

            # Importance multipliers (boost sentences with key signals)
            importance_boost = 1.0

            # Boost sentences with key indicators
            if re.search(
                r"\b(define|definition|means|refers to|is a|are)\b",
                sentence,
                re.IGNORECASE,
            ):
                importance_boost *= 1.5  # Definitions are valuable

            if re.search(
                r"\b(key|important|critical|essential|significant|primary|main|major)\b",
                sentence,
                re.IGNORECASE,
            ):
                importance_boost *= 1.3  # Explicitly important content

            if re.search(
                r"\b(result|conclusion|finding|demonstrate|show|prove)\b",
                sentence,
                re.IGNORECASE,
            ):
                importance_boost *= 1.2  # Results and findings

            # Penalize sentences with weak signals
            if re.search(
                r"\b(however|although|moreover|furthermore|additionally|also)\b",
                sentence,
                re.IGNORECASE,
            ):
                importance_boost *= 0.9  # Transitional phrases often less critical

            final_score = density_score * importance_boost
            sentence_scores[sentence] = final_score

        # 4. Extract Top Sentences
        num_to_keep = max(1, int(len(sentences) * retention_ratio))
        top_sentences = heapq.nlargest(
            num_to_keep, sentence_scores, key=sentence_scores.get
        )

        # 5. Return sentences in original order as a single string
        ordered_context = [s for s in sentences if s in top_sentences]
        return " ".join(ordered_context)


def get_text(element):
    """Safely return stripped text from any element."""
    return element.text.strip() if hasattr(element, "text") and element.text else ""


def format_element(element, level, text) -> str:
    """Format a single document element, handling Tables and Pictures."""
    output = ""
    if isinstance(element, SectionHeaderItem):
        # Only print headers if they are H1 or H2
        if level <= 2:
            prefix = "#" * (level + 1)
            output += f"\n{prefix} {text}\n"
    elif isinstance(element, ListItem):
        output += f"  • {text}\n"
    elif isinstance(element, TableItem):
        output += "\n[📊 Table Data Detected]\n"
        try:
            df = element.export_to_dataframe()
            try:
                output += df.to_markdown(index=False) + "\n"
            except ImportError:
                output += str(df) + "\n"
        except Exception:
            output += "<Table data could not be formatted>\n"
        output += "\n"
    else:
        if text:
            output += f"{text}\n"
    return output


def parse_docx_to_markdown(filepath: str) -> str:
    """
    Dynamically extracts information from a DOCX or PDF file.
    Uses LLMContextOptimizer to extract important context.
    Extracts headings and conclusion from the entire document, and ignores TABLE data.
    """
    extracted_md = ""
    optimizer = LLMContextOptimizer()

    if filepath.lower().endswith(".docx"):
        from docx import Document as RawDocx

        doc = RawDocx(filepath)

        all_text = []  # full document — used for headings & conclusion
        first_page_text = []  # actual first page — used for IMPORTANT CONTEXT
        first_page_ended = False
        FIRST_PAGE_WORD_LIMIT = 500  # fallback limit if no page break found

        headings = []
        sections = []
        current = {"heading": None, "level": 0, "content": []}

        for p in doc.paragraphs:
            text = p.text.strip()

            if text:
                all_text.append(text)

                # Check for page break to detect end of first page
                has_page_break = False
                for run in p.runs:
                    if run._element.xml.find("w:br") != -1:
                        # Check if it's a page break
                        for br in run._element.findall(
                            ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br"
                        ):
                            if (
                                br.get(
                                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type"
                                )
                                == "page"
                            ):
                                has_page_break = True
                                break

                # Collect first-page text until page break or word limit
                if not first_page_ended:
                    first_page_text.append(text)

                    # Stop at page break or word limit
                    if (
                        has_page_break
                        or len(" ".join(first_page_text).split())
                        >= FIRST_PAGE_WORD_LIMIT
                    ):
                        first_page_ended = True

                style_name = p.style.name if p.style else ""

                is_heading = False
                level = 0
                if style_name.startswith("Heading"):
                    try:
                        level = int(style_name.split()[-1])
                        # Only collect H1 and H2 — exclude H3 and deeper
                        if level in (1, 2):
                            headings.append((level, text))
                            is_heading = True
                    except ValueError:
                        pass

                if is_heading:
                    if current["heading"] is not None:
                        sections.append(dict(current))
                    current = {"heading": text, "level": level, "content": []}
                else:
                    current["content"].append(text)

        if current["heading"] is not None:
            sections.append(current)

        # IMPORTANT CONTEXT: first page only with aggressive optimization (20% retention)
        first_page_str = " ".join(first_page_text)
        important_text = optimizer.extract_dynamic_context(
            first_page_str, retention_ratio=0.20
        )

        extracted_md += important_text + "\n\n"

        extracted_md += "HEADINGS \n"
        if not headings:
            extracted_md += "No H1 or H2 headings detected.\n"
        else:
            for level, text in headings:
                indent = "  " * (level - 1)
                extracted_md += f"{indent}[H{level}] {text}\n"

        conclusion_section = next(
            (
                s
                for s in sections
                if s["heading"] and "conclusion" in s["heading"].lower()
            ),
            None,
        )
        if conclusion_section:
            extracted_md += f"\n### {conclusion_section['heading']}\n\n"
            for line in conclusion_section["content"]:
                extracted_md += f"{line}\n"
        else:
            extracted_md += "\n⚠️   No Conclusion section detected.\n"

        return extracted_md

    # Fallback to docling for PDF or other formats
    converter = DocumentConverter()
    result = converter.convert(filepath)
    doc = result.document

    # 1. Extract dynamic context — first page only (page_no == 1 via element provenance)
    first_page_text = []
    for element, level in doc.iterate_items():
        if isinstance(element, TableItem):
            continue
        if not (
            isinstance(element, TextItem)
            or isinstance(element, ListItem)
            or isinstance(element, SectionHeaderItem)
        ):
            continue

        # Only include elements whose provenance is on page 1
        try:
            if not element.prov or element.prov[0].page_no != 1:
                continue
        except (AttributeError, IndexError):
            pass  # if prov is unavailable, include it

        text = get_text(element)
        if text:
            first_page_text.append(text)

    first_page_str = " ".join(first_page_text)
    important_text = optimizer.extract_dynamic_context(
        first_page_str, retention_ratio=0.20
    )

    extracted_md += "IMPORTANT CONTEXT (First Page - Top 20%)\n"
    extracted_md += important_text + "\n\n"

    # 2. Extract headings
    extracted_md += "HEADINGS \n"

    headings = []
    # iterate_items() walks ALL pages of the document — no page limit
    for element, level in doc.iterate_items():
        if isinstance(element, TableItem):
            continue

        # Only collect H1 and H2 — explicitly exclude H3 (level 3) and deeper
        if isinstance(element, SectionHeaderItem) and level in (1, 2):
            text = get_text(element)
            if text:
                headings.append((level, text))
                indent = "  " * (level - 1)
                extracted_md += f"{indent}[H{level}] {text}\n"

    if not headings:
        extracted_md += "⚠️  No H1 or H2 headings detected.\n"


    # 4. Extract Conclusion
    sections = []
    current = {"heading": None, "level": 0, "content": []}

    # Walk ALL pages — iterate_items() is document-wide
    for element, level in doc.iterate_items():
        if isinstance(element, TableItem):
            continue

        text = get_text(element)
        if not text:
            continue

        # Section boundaries are defined only by H1/H2 — H3 is treated as body text
        if isinstance(element, SectionHeaderItem) and level in (1, 2):
            if current["heading"] is not None:
                sections.append(dict(current))
            current = {"heading": text, "level": level, "content": []}
        else:
            current["content"].append(text)

    if current["heading"] is not None:
        sections.append(current)

    conclusion_section = next(
        (s for s in sections if "conclusion" in s["heading"].lower()), None
    )

    if conclusion_section:
        extracted_md += f"\n### {conclusion_section['heading']}\n\n"
        for line in conclusion_section["content"]:
            extracted_md += f"{line}\n"
    else:
        extracted_md += "\n⚠️   No Conclusion section detected.\n"

    return extracted_md
