import os
from pathlib import Path
from docx import Document as RawDocx
from docling.document_converter import DocumentConverter
from docling.datamodel.document import SectionHeaderItem, TextItem, ListItem, TableItem, PictureItem
import pandas as pd

# Word namespace
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def get_text(element):
    """Safely return stripped text from any element."""
    return element.text.strip() if hasattr(element, "text") and element.text else ""

def format_element(element, level, text) -> str:
    """Format a single document element, handling Tables and Pictures."""
    output = ""
    if isinstance(element, SectionHeaderItem):
        # Only print headers if they are H1, H2, or H3
        if level <= 3:
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

def normalize_text(text: str) -> str:
    """Normalize text for strict sequential matching."""
    return " ".join(text.lower().strip().split())

def get_xml_blocks_with_pages(filepath: str) -> list[tuple[int, str]]:
    raw = RawDocx(filepath)
    body = raw._element.body
    
    blocks = []
    current_page = 1
    current_block = []
    
    for elem in body.iter():
        is_break = False
        if elem.tag == f"{{{W}}}lastRenderedPageBreak":
            is_break = True
        elif elem.tag == f"{{{W}}}br" and elem.get(f"{{{W}}}type") == "page":
            is_break = True
        elif elem.tag == f"{{{W}}}pageBreakBefore":
            is_break = True

        if is_break:
            if current_block:
                text = "".join(current_block).strip()
                if text:
                    blocks.append((current_page, text))
                current_block = []
            current_page += 1
            continue
            
        if elem.tag == f"{{{W}}}t" and elem.text:
            current_block.append(elem.text)
        elif elem.tag in (f"{{{W}}}p", f"{{{W}}}tr"):
            if current_block:
                text = "".join(current_block).strip()
                if text:
                    blocks.append((current_page, text))
                current_block = []
                
    if current_block:
        text = "".join(current_block).strip()
        if text:
            blocks.append((current_page, text))
            
    return blocks

def parse_docx_to_markdown(filepath: str) -> str:
    """
    Dynamically extracts information from a DOCX file using Docling
    based on the strict sequential page matching script provided.
    Returns the parsed markdown content.
    """
    converter = DocumentConverter()
    result    = converter.convert(filepath)
    doc       = result.document

    extracted_md = ""

    extracted_md += "FIRST PAGE CONTENT\n"

    xml_blocks = get_xml_blocks_with_pages(filepath)
    xml_blocks_norm = [(p, normalize_text(b)) for p, b in xml_blocks]

    first_page_items = []

    for element, level in doc.iterate_items():
        text = get_text(element)
        
        if isinstance(element, PictureItem):
            first_page_items.append((element, level, text))
            continue
            
        check_text = text
        if isinstance(element, TableItem):
            try:
                df = element.export_to_dataframe()
                check_text = " ".join(df.astype(str).values.flatten())
            except Exception:
                pass
                
        if not check_text:
            continue
            
        elem_norm = normalize_text(check_text)
        
        if len(elem_norm) < 3:
            first_page_items.append((element, level, text))
            continue
        
        match_idx = -1
        found_page = 1
        
        for i, (p, block) in enumerate(xml_blocks_norm[:15]): 
            if elem_norm in block or block in elem_norm:
                match_idx = i
                found_page = p
                break
        
        if match_idx != -1:
            if found_page > 1:
                break
            xml_blocks_norm = xml_blocks_norm[match_idx:]
            if block in elem_norm or len(elem_norm) > len(block) * 0.5:
                if xml_blocks_norm:
                    xml_blocks_norm.pop(0)
            first_page_items.append((element, level, text))
        else:
            first_page_items.append((element, level, text))

    for element, level, text in first_page_items:
        extracted_md += format_element(element, level, text)


    extracted_md += "HEADINGS \n"

    headings = []

    for element, level in doc.iterate_items():
        if isinstance(element, SectionHeaderItem) and level <= 3:
            text = get_text(element)
            if text:
                headings.append((level, text))
                indent = "  " * (level - 1)
                extracted_md += f"{indent}[H{level}] {text}\n"

    if not headings:
        extracted_md += "⚠️  No H1, H2, or H3 headings detected.\n"

    sections = []
    current = {"heading": None, "level": 0, "content": []}

    for element, level in doc.iterate_items():
        text = get_text(element)
        if not text:
            continue
        
        # Apply the same level filter here so H4 doesn't trigger a new section
        if isinstance(element, SectionHeaderItem) and level <= 3:
            if current["heading"] is not None:
                sections.append(dict(current))
            current = {"heading": text, "level": level, "content": []}
        else:
            current["content"].append(text)

    if current["heading"] is not None:
        sections.append(current)

    conclusion_section = next(
        (s for s in sections if "conclusion" in s["heading"].lower()),
        None
    )

    if conclusion_section:
        extracted_md += f"\n### {conclusion_section['heading']}\n\n"
        for line in conclusion_section["content"]:
            extracted_md += f"{line}\n"
    else:
        extracted_md += "⚠️  No Conclusion section detected.\n"
        
    return extracted_md
