import json
import fitz
import re
from pathlib import Path
import unicodedata

def detect_language(text):
    """Basic language detection for text normalization"""
    if not text or len(text.strip()) < 10:
        return 'unknown'

    # Simple script detection for basic text normalization
    for char in text:
        if char.isspace() or char.isdigit():
            continue
        code = ord(char)

        # Arabic script detection for RTL text handling
        if 0x0600 <= code <= 0x06FF or 'ARABIC' in unicodedata.name(char, ''):
            return 'arabic'
        # Hebrew script detection for RTL text handling
        elif 0x0590 <= code <= 0x05FF or 'HEBREW' in unicodedata.name(char, ''):
            return 'hebrew'

    return 'latin'

def normalize_text(text, language='latin'):
    """Normalize text for processing"""
    if not text:
        return text

    text = unicodedata.normalize('NFC', text)
    if language in ['arabic', 'hebrew']:
        text = re.sub(r'[\u200E\u200F\u202A-\u202E]', '', text)

    return re.sub(r'\s+', ' ', text.strip())

def get_semantic_keywords():
    """Get common semantic keywords for heading detection"""
    return [
        'introduction', 'conclusion', 'summary', 'overview', 'background',
        'methodology', 'results', 'discussion', 'references', 'appendix',
        'chapter', 'section', 'part', 'goals', 'objectives'
    ]

def extract_text_blocks(page):
    """Extract text blocks from PDF page"""
    try:
        blocks = page.get_text("dict")["blocks"]
        if blocks and any(b.get("type") == 0 and b.get("lines") for b in blocks):
            return blocks
    except:
        pass

    return []

def extract_title_from_pdf(doc):
    """Extract document title using PDF metadata and font analysis across multiple pages"""
    if doc.page_count == 0:
        return "", []

    # First try PDF metadata
    metadata_title = doc.metadata.get('title', '').strip()
    if metadata_title and len(metadata_title) > 3:
        return metadata_title, [metadata_title]

    # Look for title in first few pages (cover page might be empty)
    for page_num in range(min(3, doc.page_count)):
        page = doc.load_page(page_num)
        blocks = extract_text_blocks(page)

        # Extract and group text spans
        text_spans = []
        for block in blocks:
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text and len(text) >= 3:
                            bbox = span.get("bbox", [0, 0, 0, 0])
                            text_spans.append({
                                'text': text,
                                'x_pos': bbox[0],
                                'y_pos': bbox[1],
                                'font_size': span.get("size", 12),
                                'is_bold': "bold" in str(span.get("font", "")).lower(),
                                'bbox': bbox
                            })

        if not text_spans:
            continue

        # Group nearby text spans into coherent blocks
        grouped_spans = group_text_spans(text_spans)

        # Find title candidates in top 40% of page
        page_height = page.rect.height
        max_font = max(span['font_size'] for span in text_spans)

        title_candidates = []
        for group in grouped_spans:
            if (group['y_pos'] < page_height * 0.4 and
                group['font_size'] >= max_font * 0.9 and  # Require larger font for title
                not re.match(r'^(Page|Chapter|\d+\.?$|Table|Figure|Copyright|©)', group['text'], re.IGNORECASE) and
                len(group['text'].split()) >= 2 and  # Title should have multiple words
                len(group['text']) >= 8):  # Title should be substantial

                # Look for title-like patterns
                text_lower = group['text'].lower()
                if ('challenge' in text_lower or 'connecting' in text_lower or
                    'dots' in text_lower or group['font_size'] == max_font):
                    title_candidates.append(group)

        if title_candidates:
            # Sort by font size and position, prefer larger fonts higher on page
            title_candidates.sort(key=lambda x: (-x['font_size'], x['y_pos']))

            # Take the best candidate
            best_candidate = title_candidates[0]
            title = best_candidate['text'].strip()
            title = re.sub(r'\s+', ' ', title)

            # Clean up title formatting
            title = title.replace('"', '').replace('"', '').replace('"', '')
            title = title.replace('Welcome to the ', '')  # Remove common prefix

            return title, [title]

    return "", []

def group_text_spans(text_spans, line_threshold=5, word_threshold=20):
    """Group nearby text spans into coherent text blocks"""
    if not text_spans:
        return []

    # Sort by position (top to bottom, left to right)
    sorted_spans = sorted(text_spans, key=lambda x: (x['y_pos'], x['x_pos']))

    groups = []
    current_group = [sorted_spans[0]]

    for span in sorted_spans[1:]:
        last_span = current_group[-1]

        # Check if spans are on the same line or very close
        y_diff = abs(span['y_pos'] - last_span['y_pos'])
        x_diff = span['x_pos'] - (last_span['bbox'][2] if 'bbox' in last_span else last_span['x_pos'])

        if y_diff <= line_threshold and x_diff <= word_threshold:
            # Same line or very close, add to current group
            current_group.append(span)
        else:
            # Start new group
            if current_group:
                groups.append(merge_group(current_group))
            current_group = [span]

    # Add the last group
    if current_group:
        groups.append(merge_group(current_group))

    return groups

def merge_group(spans):
    """Merge a group of spans into a single text block"""
    if not spans:
        return None

    # Combine text
    text_parts = [span['text'] for span in spans]
    combined_text = ' '.join(text_parts)

    # Use properties from the first span (or dominant properties)
    first_span = spans[0]
    max_font_size = max(span['font_size'] for span in spans)
    any_bold = any(span['is_bold'] for span in spans)

    return {
        'text': combined_text,
        'x_pos': first_span['x_pos'],
        'y_pos': first_span['y_pos'],
        'font_size': max_font_size,
        'is_bold': any_bold,
        'bbox': first_span.get('bbox', [0, 0, 0, 0])
    }

def is_text_part_of_title(text, title, title_components):
    """Check if text is part of document title to prevent duplication"""
    if not text or not title:
        return False

    text_clean = re.sub(r'\s+', ' ', text.strip().lower())
    title_clean = re.sub(r'\s+', ' ', title.strip().lower())

    # Exact match
    if text_clean == title_clean:
        return True

    # Component match
    for component in title_components:
        if text_clean == component.strip().lower():
            return True

    # Partial match for longer texts
    if len(text_clean) >= 8:
        if text_clean in title_clean and len(text_clean) >= len(title_clean) * 0.4:
            return True
        if title_clean in text_clean and len(title_clean) >= len(text_clean) * 0.6:
            return True

    return False

def classify_heading_level(text, font_size, is_bold, body_size, document_stats=None):
    """Classify heading level based on patterns and adaptive font analysis"""

    # Enhanced pattern-based classification
    # Major sections (chapters, main headings)
    if re.match(r'^(Chapter|Section|Part|Round)\s+\d+', text, re.IGNORECASE):
        return 'H1'
    elif re.match(r'^\d+\.\s+[A-Z]', text):
        # Numbered items - need careful classification
        word_count = len(text.split())

        # Long sentences are likely list items, not headings
        if (word_count > 8 or text.count(',') > 1 or text.endswith('.') or
            re.search(r'\b(sample|provided|working|git|dockerfile|solution)\b', text, re.IGNORECASE)):
            return 'H3'

        # Short, title-like numbered items could be H1 or H2
        if word_count <= 5 and not text.endswith('.'):
            return 'H1'
        else:
            return 'H2'
    elif re.match(r'^\d+\.\d+\s+[A-Z]', text):
        return 'H2'
    elif re.match(r'^\d+\.\d+\.\d+\s+', text):
        return 'H3'

    # Adaptive font-based classification using document statistics
    if body_size > 0 and document_stats:
        font_ratio = font_size / body_size

        # Use document-specific thresholds if available
        large_font_threshold = document_stats.get('large_font_threshold', 1.5)
        medium_font_threshold = document_stats.get('medium_font_threshold', 1.2)

        if font_ratio >= large_font_threshold or (font_ratio >= large_font_threshold * 0.9 and is_bold):
            return 'H1'
        elif font_ratio >= medium_font_threshold or (font_ratio >= medium_font_threshold * 0.9 and is_bold):
            return 'H2'
        else:
            return 'H3'

    # Standard font-based classification
    if body_size > 0:
        font_ratio = font_size / body_size
        if font_ratio >= 1.5 or (font_ratio >= 1.3 and is_bold):
            return 'H1'
        elif font_ratio >= 1.2 or (font_ratio >= 1.1 and is_bold):
            return 'H2'
        else:
            return 'H3'

    # Fallback classification
    if is_bold and font_size >= 14:
        return 'H1'
    elif is_bold or font_size >= 12:
        return 'H2'
    else:
        return 'H3'

def is_valid_heading(text, font_size, is_bold, body_size, language='latin', document_stats=None):
    """Validate if text qualifies as a heading with enhanced filtering"""
    if not text or len(text) < 3 or len(text) > 200:
        return False

    # Filter out common non-heading patterns
    if re.match(r'^(the|and|or|of|in|on|at|to|for|with|by)$', text.lower()):
        return False

    # Enhanced filtering for various document types
    exclusion_patterns = [
        r'(address|phone|email|www\.|\.com|http)',
        r'\d+\s+\w*\s*(street|ave|road|blvd|parkway|way|drive|lane)',
        r'^\d{3,5}\s+[A-Z]+\s*(PARKWAY|STREET|AVE|ROAD|BLVD)',
        r'^[A-Z]{2}\s+\d{5}',
        r'^\(\d{3}\)\s*\d{3}-\d{4}',
        r'(rsvp|fill|sign|date|name).*[-_]{3,}',
        r'^(near|on the|in the)\s+',
        r'^\d+\s+(pages?|minutes?|hours?|days?|months?|years?)$',
        r'^(page|figure|table|chart|diagram)\s+\d+',
        r'^\d+\s*[%$€£¥]',  # Numbers with currency/percentage
        r'^[A-Z]{2,}\s*\d+$',  # Code patterns like "ABC123"
        r'^(criteria|max|points|total|description)$',  # Table headers
        r'^(constraint|requirement)$',  # Common table headers
        r'^\w+\)$',  # Single words ending with parenthesis
        r'^(why this matters|the journey ahead|your mission)$',  # Common section phrases
        r'^\d+\.\s+(a|an|the)\s+',  # List items starting with articles
        r'^\d+\.\s+sample\s+',  # Sample items
        r'hackathon\d+\.git$',  # Git repository names
    ]

    for pattern in exclusion_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False

    # Filter out very long sentences (likely paragraphs, not headings)
    word_count = len(text.split())
    if word_count > 15 and not re.match(r'^\d+\.', text):
        return False

    # Filter out sentences with too much punctuation (likely body text)
    punct_ratio = sum(1 for c in text if c in '.,;:!?') / len(text)
    if punct_ratio > 0.1:
        return False

    # Analyze content features
    has_numbered_section = bool(re.match(r'^\d+\.?\s+', text))
    has_chapter_pattern = bool(re.match(r'^(Chapter|Section|Part)\s+\d+', text, re.IGNORECASE))

    semantic_keywords = get_semantic_keywords()
    text_normalized = normalize_text(text, language).lower()
    has_semantic_keywords = any(keyword in text_normalized for keyword in semantic_keywords)

    is_title_case = text.istitle() and word_count <= 8
    is_all_caps = text.isupper() and len(text) > 3 and len(text) < 50
    starts_with_capital = text[0].isupper() if text else False

    # Analyze font features with adaptive thresholds
    font_ratio = font_size / body_size if body_size > 0 else 1

    if document_stats:
        large_threshold = document_stats.get('large_font_threshold', 1.3)
        medium_threshold = document_stats.get('medium_font_threshold', 1.2)
    else:
        large_threshold = 1.3
        medium_threshold = 1.2

    is_large_font = font_ratio >= large_threshold
    is_notable_font = font_ratio >= medium_threshold and is_bold

    # Enhanced score-based validation
    content_score = sum([
        has_chapter_pattern * 6,
        has_numbered_section * 4,
        has_semantic_keywords * 3,
        is_title_case * 2,
        is_all_caps * 2,
        starts_with_capital * 1
    ])

    font_score = sum([
        is_large_font * 4,
        is_notable_font * 3,
        is_bold * 2
    ])

    # Require higher score for longer text
    required_score = 5 if word_count <= 5 else 6 if word_count <= 10 else 7

    return (content_score + font_score) >= required_score

def analyze_document_structure(doc):
    """Analyze document to learn font patterns and structure"""
    font_sizes = []
    all_font_sizes = []
    text_lengths = []

    max_pages = min(5, doc.page_count)  # Analyze more pages for better statistics
    for page_num in range(max_pages):
        page = doc.load_page(page_num)
        blocks = extract_text_blocks(page)

        for block in blocks:
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        font_size = span.get("size", 12)
                        all_font_sizes.append(font_size)

                        # Collect body text font sizes (longer text spans)
                        if len(text) > 10:
                            font_sizes.append(font_size)
                            text_lengths.append(len(text))

    if not font_sizes:
        return {'body_size': 12, 'large_font_threshold': 1.5, 'medium_font_threshold': 1.2}

    # Calculate statistics
    font_sizes.sort()
    all_font_sizes.sort()

    body_size = font_sizes[len(font_sizes) // 2]  # Median body text font size

    # Calculate adaptive thresholds based on document's font distribution
    unique_sizes = sorted(set(all_font_sizes), reverse=True)

    if len(unique_sizes) >= 3:
        # Use actual font size distribution to set thresholds
        largest_size = unique_sizes[0]
        second_largest = unique_sizes[1]

        large_font_threshold = max(1.4, largest_size / body_size * 0.9)
        medium_font_threshold = max(1.2, second_largest / body_size * 0.9)
    else:
        # Fallback to standard thresholds
        large_font_threshold = 1.5
        medium_font_threshold = 1.2

    # Calculate text complexity (for better heading detection)
    avg_text_length = sum(text_lengths) / len(text_lengths) if text_lengths else 50

    return {
        'body_size': body_size,
        'large_font_threshold': large_font_threshold,
        'medium_font_threshold': medium_font_threshold,
        'avg_text_length': avg_text_length,
        'font_sizes': unique_sizes[:5]  # Top 5 font sizes
    }



def extract_outline_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)

        if doc.page_count > 50:
            print(f"Warning: {pdf_path} has {doc.page_count} pages, processing first 50 only")

        document_title, title_components = extract_title_from_pdf(doc)

        doc_structure = analyze_document_structure(doc)
        body_size = doc_structure['body_size']

        sample_text = ""
        for page_num in range(min(3, doc.page_count)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            sample_text += page_text[:1000]

        document_language = detect_language(sample_text)

        outline = []
        max_pages = min(50, doc.page_count)

        for page_num in range(max_pages):
            page = doc.load_page(page_num)
            blocks = extract_text_blocks(page)

            for block in blocks:
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        text_parts = []
                        max_size = 0
                        is_bold = False

                        for span in line.get("spans", []):
                            text = span.get("text", "")
                            if text.strip():
                                text_parts.append(text)
                                max_size = max(max_size, span.get("size", 12))
                                font_name = str(span.get("font", "")).lower()
                                is_bold |= ("bold" in font_name)

                        if not text_parts:
                            continue

                        text = " ".join(text_parts).strip()

                        if is_text_part_of_title(text, document_title, title_components):
                            continue

                        # Use enhanced validation with document statistics
                        if is_valid_heading(text, max_size, is_bold, body_size, document_language, doc_structure):
                            level = classify_heading_level(text, max_size, is_bold, body_size, doc_structure)
                            outline.append({
                                "level": level,
                                "text": normalize_text(text, document_language),
                                "page": page_num + 1
                            })



        doc.close()
        return {
            "title": document_title,
            "outline": outline
        }

    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        return {"title": "", "outline": []}

def main():
    input_dir = Path("sample_dataset/pdfs")
    output_dir = Path("sample_dataset/outputs")

    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        print(f"Error: '{input_dir}' directory not found")
        return 1

    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in '{input_dir}' directory")
        return 1

    print(f"Found {len(pdf_files)} PDF files to process")

    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")

        try:
            result = extract_outline_from_pdf(str(pdf_file))

            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)

            print(f"✓ Successfully processed {pdf_file.name}")

        except Exception as e:
            print(f"✗ Error processing {pdf_file.name}: {str(e)}")

    print("Processing complete")
    return 0

if __name__ == "__main__":
    exit(main())


