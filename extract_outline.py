import fitz  # PyMuPDF
import json
import argparse
import re
from collections import defaultdict
from difflib import SequenceMatcher

# --- Heuristic Constants ---
POSTER_WORD_THRESHOLD = 400
FORM_KEYWORDS_PATTERN = re.compile(r'\b(form|application|name:|date:|signature|address:|declaration)\b', re.IGNORECASE)


def is_likely_form(page_text: str) -> bool:
    return FORM_KEYWORDS_PATTERN.search(page_text) is not None


def is_toc_page(page_text: str) -> bool:
    if re.search(r'^(table of )?contents?$', page_text, re.IGNORECASE | re.MULTILINE):
        return True
    dot_leader_pattern = re.compile(r'.+[\s\.]{5,}\s*\d+\s*$', re.MULTILINE)
    return len(dot_leader_pattern.findall(page_text)) >= 5


def compress_repeated_letters(word):
    return re.sub(r'(.)\1{2,}', r'\1', word)

def is_similar_or_substring(word, seen_words):
    for existing in seen_words:
        # Check similarity
        if SequenceMatcher(None, word, existing).ratio() > 0.85:
            return True
        # Check if word is substring of an existing word or vice versa
        if word in existing or existing in word:
            return True
    return False

def get_document_title(doc, all_blocks):
    first_page_blocks = [b for b in all_blocks if b.get('page') == 0]
    if not first_page_blocks:
        return ""

    largest_block = max(first_page_blocks, key=lambda block: block.get('size', 0))
    raw_title = largest_block.get('text', '').replace('\n', ' ').strip()

    words = raw_title.split()
    seen = []
    cleaned_words = []

    for word in words:
        word_clean = compress_repeated_letters(word.lower())
        if len(word_clean) < 3:
            continue
        if not is_similar_or_substring(word_clean, seen):
            seen.append(word_clean)
            cleaned_words.append(word_clean.capitalize())

    return " ".join(cleaned_words)


def handle_structured_doc_with_toc(doc: fitz.Document) -> dict:
    toc = doc.get_toc()
    outline = [{"level": f"H{min(level, 4)}", "text": text.strip(), "page": page - 1} for level, text, page in toc]
    title = doc.metadata.get('title') or ""
    return {"title": title, "outline": outline} if outline else analyze_document_manually(doc)


def handle_form(doc: fitz.Document) -> dict:
    title = doc[0].get_text("text").split('\n', 1)[0].strip()
    return {"title": title, "outline": []}


def handle_poster(doc: fitz.Document) -> dict:
    page = doc[0]
    blocks = page.get_text("dict", flags=1)["blocks"]
    text_blocks = []
    for b in blocks:
        if b['type'] == 0:
            for l in b['lines']:
                line_text = "".join(s['text'] for s in l['spans']).strip()
                if line_text and l['spans']:
                    text_blocks.append({'text': line_text, 'size': l['spans'][0]['size'], 'bbox': l['bbox']})
    if not text_blocks:
        return {"title": "", "outline": []}
    text_blocks.sort(key=lambda x: x['bbox'][1])
    title = text_blocks[0]['text'] if text_blocks else ""
    page_center_x = page.rect.width / 2
    for block in text_blocks:
        block_center_x = (block['bbox'][0] + block['bbox'][2]) / 2
        distance_from_center = abs(page_center_x - block_center_x)
        block['score'] = block['size'] * (1 - (distance_from_center / page_center_x) * 0.5)
    text_blocks.sort(key=lambda x: x['score'], reverse=True)
    outline = []
    for block in text_blocks:
        if block['text'] != title:
            outline.append({"level": "H1", "text": block['text'], "page": 0})
            break
    return {"title": title, "outline": outline}


def analyze_document_manually(doc: fitz.Document) -> dict:
    all_blocks = []
    toc_pages = {p for p, page in enumerate(doc) if is_toc_page(page.get_text("text"))}
    for page_num, page in enumerate(doc):
        if page_num in toc_pages:
            continue
        page_blocks = page.get_text("dict", flags=1)['blocks']
        for b in page_blocks:
            if b['type'] == 0 and b['lines']:
                block_text = " ".join("".join(s['text'] for s in l['spans']) for l in b['lines']).strip()
                if not block_text:
                    continue
                span = b['lines'][0]['spans'][0]
                all_blocks.append({
                    'text': block_text, 'page': page_num, 'line_count': len(b['lines']),
                    'size': span['size'], 'is_bold': span['flags'] & 16 > 0,
                    'bbox': b['bbox']
                })

    if not all_blocks:
        return {"title": "", "outline": []}

    heading_candidates = [b for b in all_blocks if b['line_count'] <= 3 and len(b['text']) < 400]
    numbered_headings, textual_candidates = [], []

    for block in heading_candidates:
        text = block['text']
        match = re.match(r'^((\d+)(\.\d+)*|Appendix\s[A-Z])', text)
        if match:
            num_str = match.group(1)
            if num_str:
                depth = min(num_str.count('.') + 1, 4)
                block['level'] = f"H{depth}"
            else:
                block['level'] = 'H2'
            numbered_headings.append(block)
        else:
            textual_candidates.append(block)

    if textual_candidates:
        styles = sorted(list({(round(b['size']), b['is_bold']) for b in textual_candidates}), reverse=True)
        style_to_level = {style: f"H{i+1}" for i, style in enumerate(styles[:4])}
        for block in textual_candidates:
            style = (round(block['size']), block['is_bold'])
            if style in style_to_level:
                block['level'] = style_to_level[style]
                numbered_headings.append(block)

    final_outline_temp = sorted(numbered_headings, key=lambda x: (x['page'], x['bbox'][1]))
    final_outline = [{"level": b['level'], "text": b['text'], "page": b['page']} for b in final_outline_temp]
    title = get_document_title(doc, all_blocks)
    return {"title": title, "outline": final_outline}

import os
from pathlib import Path

def main():
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    
    for pdf_file in input_dir.glob("*.pdf"):
        try:
            doc = fitz.open(pdf_file)
            if doc.page_count > 1 and doc.get_toc():
                final_data = handle_structured_doc_with_toc(doc)
            else:
                first_page_text = doc[0].get_text("text")
                if is_likely_form(first_page_text):
                    final_data = handle_form(doc)
                elif doc.page_count == 1 and len(first_page_text.split()) < POSTER_WORD_THRESHOLD:
                    final_data = handle_poster(doc)
                else:
                    final_data = analyze_document_manually(doc)

            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=4, ensure_ascii=False)

            print(f"✅ Processed {pdf_file.name} → {output_file.name}")
        
        except Exception as e:
            print(f"❌ Failed to process {pdf_file.name}: {e}")


if __name__ == "__main__":
    main()
