"""
Grobid-only server with sentence-level coordinates
No PyMuPDF needed - uses Grobid's teiCoordinates feature
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import re
from xml.etree import ElementTree as ET
import uvicorn
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070/api/processFulltextDocument")

# TEI namespace
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}


def parse_coords(coords_str: str) -> list:
    """
    Parse Grobid coordinate string.
    Format: "page,x,y,width,height" or multiple separated by ";"
    Returns list of {page, x, y, width, height}
    """
    if not coords_str:
        return []
    
    boxes = []
    for part in coords_str.split(';'):
        parts = part.strip().split(',')
        if len(parts) >= 5:
            try:
                boxes.append({
                    'page': int(float(parts[0])),
                    'x': float(parts[1]),
                    'y': float(parts[2]),
                    'width': float(parts[3]),
                    'height': float(parts[4])
                })
            except (ValueError, IndexError):
                continue
    return boxes


def merge_boxes_by_page(boxes: list) -> dict:
    """
    Merge multiple line boxes into bounding boxes per page.
    For two-column layouts, keeps separate boxes for each column.
    Returns {page_num: [{x, y, width, height}, ...]}
    """
    if not boxes:
        return {}
    
    page_boxes = {}
    
    for box in boxes:
        page = box['page']
        if page not in page_boxes:
            page_boxes[page] = []
        page_boxes[page].append(box)
    
    result = {}
    for page, boxes_on_page in page_boxes.items():
        if not boxes_on_page:
            continue
        
        # Detect columns by x-center clustering
        # Typical two-column: left ~170, right ~420 (centers)
        x_centers = [(b['x'] + b['width'] / 2) for b in boxes_on_page]
        
        # Find column boundaries using gap detection
        sorted_centers = sorted(set(x_centers))
        
        # If we have boxes spread across page, detect column boundary
        if len(sorted_centers) > 1:
            min_x = min(b['x'] for b in boxes_on_page)
            max_x = max(b['x'] + b['width'] for b in boxes_on_page)
            page_width = max_x - min_x
            
            # Check if this looks like two-column (boxes in left and right halves)
            mid_x = min_x + page_width / 2
            left_boxes = [b for b in boxes_on_page if b['x'] + b['width']/2 < mid_x]
            right_boxes = [b for b in boxes_on_page if b['x'] + b['width']/2 >= mid_x]
            
            # If both sides have boxes and there's a gap in the middle
            if left_boxes and right_boxes:
                left_max_x = max(b['x'] + b['width'] for b in left_boxes)
                right_min_x = min(b['x'] for b in right_boxes)
                gap = right_min_x - left_max_x
                
                # Significant gap suggests two columns (> 10px gap)
                if gap > 10:
                    # Merge each column separately
                    columns_data = [left_boxes, right_boxes]
                else:
                    # Single column - merge all
                    columns_data = [boxes_on_page]
            else:
                columns_data = [boxes_on_page]
        else:
            columns_data = [boxes_on_page]
        
        # Merge boxes within each column
        result[page] = []
        for col_boxes in columns_data:
            if not col_boxes:
                continue
            
            minX = min(b['x'] for b in col_boxes)
            minY = min(b['y'] for b in col_boxes)
            maxX = max(b['x'] + b['width'] for b in col_boxes)
            maxY = max(b['y'] + b['height'] for b in col_boxes)
            
            result[page].append({
                'x': minX,
                'y': minY,
                'width': maxX - minX,
                'height': maxY - minY
            })
        
        # Sort by y, then x
        result[page].sort(key=lambda b: (b['y'], b['x']))
    
    return result


def extract_sentences_from_p(p_elem) -> list:
    """Extract all sentences with coords from a paragraph element."""
    sentences = []
    
    for s_elem in p_elem.findall('.//tei:s', NS):
        coords_str = s_elem.get('coords', '')
        text = ''.join(s_elem.itertext()).strip()
        
        if coords_str and text:
            boxes = parse_coords(coords_str)
            sentences.append({
                'text': text,
                'boxes': boxes
            })
    
    return sentences


def calculate_paragraph_bbox(sentences: list) -> dict:
    """
    Calculate paragraph bounding box from all its sentences.
    Returns {page: [{x, y, width, height}, ...]} for each page the paragraph spans.
    Handles two-column layouts where a paragraph flows from left to right column.
    Filters out outlier boxes (e.g., footnotes at page bottom).
    """
    all_boxes = []
    for sent in sentences:
        all_boxes.extend(sent['boxes'])
    
    if not all_boxes:
        return {}
    
    # Group by page first
    page_boxes = {}
    for box in all_boxes:
        page = box['page']
        if page not in page_boxes:
            page_boxes[page] = []
        page_boxes[page].append(box)
    
    # For each page, separate columns FIRST, then filter outliers per column
    filtered_boxes = []
    for page, boxes in page_boxes.items():
        if len(boxes) <= 2:
            filtered_boxes.extend(boxes)
            continue
        
        # Detect columns by x-center
        min_x = min(b['x'] for b in boxes)
        max_x = max(b['x'] + b['width'] for b in boxes)
        page_width = max_x - min_x
        
        # Check if this looks like two-column
        mid_x = min_x + page_width / 2
        left_boxes = [b for b in boxes if b['x'] + b['width']/2 < mid_x]
        right_boxes = [b for b in boxes if b['x'] + b['width']/2 >= mid_x]
        
        # Determine if we have two columns (both sides with gap)
        has_two_columns = False
        if left_boxes and right_boxes:
            left_max_x = max(b['x'] + b['width'] for b in left_boxes)
            right_min_x = min(b['x'] for b in right_boxes)
            gap = right_min_x - left_max_x
            if gap > 10:  # Significant gap suggests two columns
                has_two_columns = True
        
        # Filter outliers per column
        column_groups = [left_boxes, right_boxes] if has_two_columns else [boxes]
        
        for col_boxes in column_groups:
            if not col_boxes:
                continue
            if len(col_boxes) <= 2:
                filtered_boxes.extend(col_boxes)
                continue
            
            # Sort by y position
            y_values = sorted([b['y'] for b in col_boxes])
            
            # Calculate typical line spacing between consecutive lines
            y_gaps = []
            for i in range(len(y_values) - 1):
                gap = y_values[i + 1] - y_values[i]
                if 5 < gap < 50:  # Normal line spacing range
                    y_gaps.append(gap)
            
            if y_gaps:
                typical_gap = sorted(y_gaps)[len(y_gaps) // 2]  # median gap
            else:
                typical_gap = 15  # default line height
        
            # Find the largest contiguous cluster of lines within this column
            # Two lines are "connected" if gap between them is < 3x typical gap
            clusters = []
            current_cluster = [y_values[0]]
            
            for i in range(1, len(y_values)):
                gap = y_values[i] - y_values[i - 1]
                if gap < typical_gap * 3:  # Connected to current cluster
                    current_cluster.append(y_values[i])
                else:  # Start new cluster
                    clusters.append(current_cluster)
                    current_cluster = [y_values[i]]
            clusters.append(current_cluster)
            
            # Pick the largest cluster
            main_cluster = max(clusters, key=len)
            cluster_min = min(main_cluster)
            cluster_max = max(main_cluster)
            
            # Add some padding for the cluster range
            padding = typical_gap * 2
            
            for box in col_boxes:
                if cluster_min - padding <= box['y'] <= cluster_max + padding:
                    filtered_boxes.append(box)
    
    return merge_boxes_by_page(filtered_boxes)


def extract_text_from_element(elem) -> str:
    """Extract all text from an element, including nested elements."""
    return ''.join(elem.itertext()).strip()


def clean_title(title: str) -> str:
    """
    Remove common header/footer text from title.
    E.g., "Under review as a conference paper at ICLR 2026"
    """
    import re
    
    # Common patterns to remove from title
    patterns = [
        r'^Under review.*?(?:ICLR|ICML|NeurIPS|AAAI|ACL|EMNLP|CVPR|ICCV|ECCV|KDD|WWW|SIGIR|NAACL).*?\d{4}\s*',
        r'^Accepted.*?(?:ICLR|ICML|NeurIPS|AAAI|ACL|EMNLP|CVPR|ICCV|ECCV|KDD|WWW|SIGIR|NAACL).*?\d{4}\s*',
        r'^Published.*?(?:ICLR|ICML|NeurIPS|AAAI|ACL|EMNLP|CVPR|ICCV|ECCV|KDD|WWW|SIGIR|NAACL).*?\d{4}\s*',
        r'^Preprint\.?\s*',
        r'^arXiv:\d+\.\d+.*?\s*',
        r'^Workshop.*?(?:ICLR|ICML|NeurIPS|AAAI).*?\d{4}\s*',
    ]
    
    cleaned = title
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()


def parse_grobid_tei(xml_content: str) -> dict:
    """
    Parse Grobid TEI XML with sentence coordinates.
    Returns structured document with paragraph bounding boxes.
    """
    root = ET.fromstring(xml_content)
    
    result = {
        'title': '',
        'abstract': [],
        'sections': [],
        'references': []
    }
    
    # Extract title
    title_elem = root.find('.//tei:titleStmt/tei:title', NS)
    if title_elem is not None:
        raw_title = extract_text_from_element(title_elem)
        result['title'] = clean_title(raw_title)
    
    # Extract abstract
    abstract_elem = root.find('.//tei:profileDesc/tei:abstract', NS)
    if abstract_elem is not None:
        for p in abstract_elem.findall('.//tei:p', NS):
            sentences = extract_sentences_from_p(p)
            text = extract_text_from_element(p)
            bbox = calculate_paragraph_bbox(sentences)
            
            if text:
                result['abstract'].append({
                    'text': text,
                    'sentences': [{'text': s['text'], 'boxes': s['boxes']} for s in sentences],
                    'bbox': bbox  # {page_num: {x, y, width, height}}
                })
    
    # Extract body sections
    body = root.find('.//tei:body', NS)
    if body is not None:
        for div in body.findall('.//tei:div', NS):
            section = {
                'title': '',
                'title_coords': None,
                'paragraphs': []
            }
            
            # Section title (head)
            head = div.find('tei:head', NS)
            if head is not None:
                section['title'] = extract_text_from_element(head)
                coords_str = head.get('coords', '')
                if coords_str:
                    boxes = parse_coords(coords_str)
                    section['title_coords'] = merge_boxes_by_page(boxes)
            
            # Paragraphs
            for p in div.findall('tei:p', NS):
                sentences = extract_sentences_from_p(p)
                text = extract_text_from_element(p)
                bbox = calculate_paragraph_bbox(sentences)
                
                if text:
                    section['paragraphs'].append({
                        'text': text,
                        'sentences': [{'text': s['text'], 'boxes': s['boxes']} for s in sentences],
                        'bbox': bbox
                    })
            
            if section['title'] or section['paragraphs']:
                result['sections'].append(section)
    
    return result


def flatten_to_paragraphs(parsed: dict) -> list:
    """
    Flatten parsed structure to a simple list of paragraphs with coordinates.
    Each paragraph has: text, type, and bboxes array.
    bboxes: [{page, x, y, width, height}, ...] - supports multiple boxes per page (two-column)
    """
    paragraphs = []
    para_id = 0
    
    # Abstract paragraphs
    for p in parsed.get('abstract', []):
        bboxes = []
        for page, bbox_list in sorted(p.get('bbox', {}).items()):
            # bbox_list is now a list of boxes for this page
            for bbox in bbox_list:
                bboxes.append({
                    'page': page,
                    'x': bbox['x'],
                    'y': bbox['y'],
                    'width': bbox['width'],
                    'height': bbox['height']
                })
        if bboxes:
            # Extract sentence bboxes
            sentence_data = []
            for sent in p.get('sentences', []):
                sent_bboxes = []
                for box in sent.get('boxes', []):
                    sent_bboxes.append({
                        'page': box['page'],
                        'x': box['x'],
                        'y': box['y'],
                        'width': box['width'],
                        'height': box['height']
                    })
                if sent_bboxes:
                    sentence_data.append({
                        'text': sent['text'],
                        'bboxes': sent_bboxes
                    })
            paragraphs.append({
                'id': para_id,
                'type': 'abstract',
                'text': p['text'],
                'bboxes': bboxes,
                'sentences': sentence_data
            })
            para_id += 1
    
    # Section paragraphs
    for section in parsed.get('sections', []):
        # Section title as a paragraph
        if section.get('title') and section.get('title_coords'):
            bboxes = []
            for page, bbox_list in sorted(section['title_coords'].items()):
                for bbox in bbox_list:
                    bboxes.append({
                        'page': page,
                        'x': bbox['x'],
                        'y': bbox['y'],
                        'width': bbox['width'],
                        'height': bbox['height']
                    })
            if bboxes:
                paragraphs.append({
                    'id': para_id,
                    'type': 'section_title',
                    'text': section['title'],
                    'bboxes': bboxes
                })
                para_id += 1
        
        # Regular paragraphs
        for p in section.get('paragraphs', []):
            bboxes = []
            for page, bbox_list in sorted(p.get('bbox', {}).items()):
                for bbox in bbox_list:
                    bboxes.append({
                        'page': page,
                        'x': bbox['x'],
                        'y': bbox['y'],
                        'width': bbox['width'],
                        'height': bbox['height']
                    })
            if bboxes:
                # Extract sentence bboxes
                sentence_data = []
                for sent in p.get('sentences', []):
                    sent_bboxes = []
                    for box in sent.get('boxes', []):
                        sent_bboxes.append({
                            'page': box['page'],
                            'x': box['x'],
                            'y': box['y'],
                            'width': box['width'],
                            'height': box['height']
                        })
                    if sent_bboxes:
                        sentence_data.append({
                            'text': sent['text'],
                            'bboxes': sent_bboxes
                        })
                paragraphs.append({
                    'id': para_id,
                    'type': 'paragraph',
                    'text': p['text'],
                    'bboxes': bboxes,
                    'sentences': sentence_data
                })
                para_id += 1
    
    return paragraphs


@app.post("/process")
async def process_pdf(file: UploadFile = File(...)):
    """
    Process PDF through Grobid with sentence coordinates.
    Returns paragraphs with bounding boxes.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    pdf_content = await file.read()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                GROBID_URL,
                files={"input": (file.filename, pdf_content, "application/pdf")},
                data={
                    "segmentSentences": "1",
                    "teiCoordinates": ["s", "head", "figure", "ref"]
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Grobid error: {response.status_code}"
                )
            
            tei_xml = response.text
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Grobid timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grobid request failed: {str(e)}")
    
    # Parse TEI XML
    try:
        parsed = parse_grobid_tei(tei_xml)
        paragraphs = flatten_to_paragraphs(parsed)
    except ET.ParseError as e:
        raise HTTPException(status_code=500, detail=f"XML parse error: {str(e)}")
    
    return {
        "status": "success",
        "title": parsed.get('title', ''),
        "paragraphs": paragraphs,
        "parsed": parsed  # Full structured data for debugging
    }


@app.get("/health")
async def health_check():
    """Check if server and Grobid are running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8070/api/isalive")
            grobid_alive = response.status_code == 200
    except:
        grobid_alive = False
    
    return {
        "server": "running",
        "grobid": "running" if grobid_alive else "not available"
    }


# ========== Semantic Chunking with spaCy ==========

# Pastel color palette for chunks
CHUNK_COLORS = [
    "#FFE4B5",  # Moccasin
    "#B0E0E6",  # PowderBlue
    "#DDA0DD",  # Plum
    "#98FB98",  # PaleGreen
    "#FFB6C1",  # LightPink
    "#87CEEB",  # SkyBlue
    "#F0E68C",  # Khaki
    "#E6E6FA",  # Lavender
]


class ChunkRequest(BaseModel):
    sentences: list[str]


def chunk_sentence(doc) -> list[dict]:
    """
    Split a spaCy Doc into semantic chunks.
    Rules:
    1) Split into: intro phrases, main clause (subj+verb), object, modifiers
    2) Relative clauses (that/which/who/when/where) become own chunk
    3) Prepositional phrases > 7 tokens become own chunk
    4) Parallel structures (A, B, and C) split using CC/conj
    5) No chunk > 12 tokens, subdivide if longer
    6) Keep original word order
    """
    chunks = []
    current_chunk = []
    
    # Find relative clause markers and conjunctions
    rel_markers = {"that", "which", "who", "whom", "whose", "when", "where", "while", "although", "because", "if", "unless"}
    
    # Track subtree roots for prepositional phrases
    prep_roots = set()
    for token in doc:
        if token.dep_ == "prep" and token.head.pos_ in {"VERB", "NOUN", "ADJ"}:
            subtree = list(token.subtree)
            if len(subtree) > 7:
                prep_roots.add(token.i)
    
    # Find conjunction points for parallel structures
    conj_points = set()
    for token in doc:
        if token.dep_ == "cc":  # coordinating conjunction
            conj_points.add(token.i)
    
    def should_split(token, prev_token):
        """Determine if we should start a new chunk before this token."""
        # Split at relative clause markers
        if token.text.lower() in rel_markers and token.dep_ in {"mark", "nsubj", "advmod", "relcl"}:
            return True
        
        # Split at coordinating conjunctions (but not within short phrases)
        if token.i in conj_points and len(current_chunk) > 3:
            return True
        
        # Split at preposition starting a long PP
        if token.i in prep_roots:
            return True
        
        # Split at major clause boundaries
        if token.dep_ in {"advcl", "ccomp", "xcomp"} and token.pos_ == "VERB":
            return True
            
        return False
    
    def flush_chunk():
        nonlocal current_chunk
        if current_chunk:
            text = "".join(t.text_with_ws for t in current_chunk).strip()
            if text:
                chunks.append({"text": text, "tokens": current_chunk.copy()})
            current_chunk = []
    
    prev_token = None
    for token in doc:
        # Check if we should split before this token
        if should_split(token, prev_token):
            flush_chunk()
        
        current_chunk.append(token)
        
        # Enforce max 12 tokens per chunk
        if len(current_chunk) >= 12:
            # Try to find a good break point
            break_at = None
            for i in range(len(current_chunk) - 1, max(5, len(current_chunk) - 5), -1):
                t = current_chunk[i]
                if t.pos_ in {"PUNCT", "CCONJ"} or t.dep_ in {"punct", "cc"}:
                    break_at = i + 1
                    break
            
            if break_at:
                text = "".join(t.text_with_ws for t in current_chunk[:break_at]).strip()
                if text:
                    chunks.append({"text": text, "tokens": current_chunk[:break_at]})
                current_chunk = current_chunk[break_at:]
            else:
                flush_chunk()
        
        prev_token = token
    
    # Flush remaining
    flush_chunk()
    
    # Merge very short chunks (< 3 tokens) with neighbors
    merged = []
    for chunk in chunks:
        if merged and len(chunk.get("tokens", [])) < 3:
            # Merge with previous
            merged[-1]["text"] += " " + chunk["text"]
            merged[-1]["tokens"].extend(chunk.get("tokens", []))
        else:
            merged.append(chunk)
    
    # Clean up - remove tokens from output, add chunk_id
    result = []
    for i, chunk in enumerate(merged):
        result.append({
            "chunk_id": i + 1,
            "text": chunk["text"]
        })
    
    return result


def chunks_to_html(chunks: list[dict]) -> str:
    """Convert chunks to HTML with color spans."""
    html_parts = []
    for chunk in chunks:
        color_idx = (chunk["chunk_id"] - 1) % len(CHUNK_COLORS)
        color = CHUNK_COLORS[color_idx]
        html_parts.append(
            f'<span class="chunk chunk{chunk["chunk_id"]}" style="background-color: {color}; padding: 2px 4px; border-radius: 3px; margin: 1px;">{chunk["text"]}</span>'
        )
    return " ".join(html_parts)


@app.post("/chunk")
async def chunk_sentences(request: ChunkRequest):
    """
    Process sentences and return semantic chunks with HTML.
    """
    results = []
    
    for sentence in request.sentences:
        doc = nlp(sentence)
        chunks = chunk_sentence(doc)
        html = chunks_to_html(chunks)
        results.append({
            "original": sentence,
            "chunks": chunks,
            "html": html
        })
    
    return {"results": results}


if __name__ == "__main__":
    print("=" * 50)
    print("Grobid-only Server v2 (with sentence coordinates)")
    print("=" * 50)
    print("Endpoint: POST /process")
    print("Health: GET /health")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
