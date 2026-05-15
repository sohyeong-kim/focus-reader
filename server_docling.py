"""
Docling-based PDF parser with paragraph bounding boxes.

Replaces server_grobid_v2.py for book chapters where Grobid's
academic-paper assumptions misclassify paragraphs (table cells
absorbing prose, indented blocks dropped/reordered, etc.).

Exposes the same /process and /chunk endpoints the Electron app
already calls — no frontend change required.
"""
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import spacy

from docling.document_converter import DocumentConverter

nlp = spacy.load("en_core_web_sm")
converter = DocumentConverter()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Docling DocItemLabel values mapped to frontend paragraph types.
SECTION_TITLE_LABELS = {"section_header", "title"}
# Items we never want in the audio/reader flow.
SKIP_LABELS = {"page_header", "page_footer", "picture", "table", "document_index"}


def _bbox_to_topleft(bbox, page_height):
    """Return {x, y, width, height} in top-left origin regardless of input."""
    # Docling >=2 BoundingBox has .to_top_left_origin(page_height) for the conversion.
    if hasattr(bbox, "to_top_left_origin"):
        try:
            bbox = bbox.to_top_left_origin(page_height=page_height)
        except Exception:
            pass
    coord = getattr(bbox, "coord_origin", None)
    coord_str = str(coord) if coord is not None else ""
    if "BOTTOMLEFT" in coord_str and page_height:
        y_top = page_height - bbox.t
        height = bbox.t - bbox.b
    else:
        y_top = bbox.t
        height = bbox.b - bbox.t
    return {
        "x": float(bbox.l),
        "y": float(y_top),
        "width": float(bbox.r - bbox.l),
        "height": float(height),
    }


def _split_sentences(text: str) -> list[str]:
    doc = nlp(text)
    return [s.text.strip() for s in doc.sents if s.text.strip()]


@app.post("/process")
async def process_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    pdf_bytes = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        result = converter.convert(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Docling failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    doc = result.document

    # Page-height lookup for bottom-left → top-left conversion.
    page_heights: dict[int, float] = {}
    for page_no, page in (doc.pages or {}).items():
        size = getattr(page, "size", None)
        if size is not None:
            page_heights[page_no] = float(getattr(size, "height", 0.0)) or 0.0

    paragraphs = []
    para_id = 0
    title = ""
    skipped_labels: dict[str, int] = {}

    for item, _level in doc.iterate_items():
        label_obj = getattr(item, "label", None)
        if label_obj is None:
            continue
        label_str = (
            label_obj.value if hasattr(label_obj, "value") else str(label_obj)
        ).lower()
        text = (getattr(item, "text", "") or "").strip()
        if not text:
            continue

        if label_str in SKIP_LABELS:
            skipped_labels[label_str] = skipped_labels.get(label_str, 0) + 1
            continue

        # Collect bboxes across provenance (handles multi-page items).
        bboxes = []
        for prov in getattr(item, "prov", None) or []:
            page_no = getattr(prov, "page_no", None)
            if page_no is None:
                continue
            page_h = page_heights.get(page_no, 0.0)
            bb = getattr(prov, "bbox", None)
            if bb is None:
                continue
            rel = _bbox_to_topleft(bb, page_h)
            bboxes.append({"page": page_no, **rel})

        if label_str == "title" and not title:
            title = text

        if label_str in SECTION_TITLE_LABELS:
            frontend_type = "section_title"
            sentence_data: list[dict] = []
        else:
            frontend_type = "paragraph"
            sentences = _split_sentences(text)
            # Docling does not expose per-sentence bbox. Approximate each sentence's
            # bbox by slicing the paragraph bbox vertically in proportion to where
            # the sentence sits in the paragraph's character span. This is rough
            # but gives the reader-overlay something to move within a paragraph
            # instead of highlighting the whole block on every sentence.
            sentence_data = []
            total_chars = sum(len(s) for s in sentences) or 1
            cum = 0
            for s in sentences:
                s_len = len(s)
                start_frac = cum / total_chars
                end_frac = (cum + s_len) / total_chars
                cum += s_len
                if not bboxes:
                    sentence_data.append({"text": s, "bboxes": []})
                    continue
                sb = []
                for bb in bboxes:
                    bh = bb["height"]
                    sb.append({
                        "page": bb["page"],
                        "x": bb["x"],
                        "y": bb["y"] + start_frac * bh,
                        "width": bb["width"],
                        "height": max(2.0, (end_frac - start_frac) * bh),
                    })
                sentence_data.append({"text": s, "bboxes": sb})

        paragraphs.append({
            "id": para_id,
            "type": frontend_type,
            "text": text,
            "bboxes": bboxes,
            "sentences": sentence_data,
            "label": label_str,
        })
        para_id += 1

    return {
        "status": "success",
        "title": title,
        "paragraphs": paragraphs,
        "skipped_labels": skipped_labels,
    }


@app.get("/health")
async def health_check():
    return {"server": "docling", "status": "ok"}


# ========== Semantic Chunking with spaCy (copied from server_grobid_v2.py) ==========

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
    chunks: list[dict] = []
    current_chunk: list = []

    rel_markers = {
        "that", "which", "who", "whom", "whose", "when", "where",
        "while", "although", "because", "if", "unless",
    }

    prep_roots = set()
    for token in doc:
        if token.dep_ == "prep" and token.head.pos_ in {"VERB", "NOUN", "ADJ"}:
            subtree = list(token.subtree)
            if len(subtree) > 7:
                prep_roots.add(token.i)

    conj_points = set()
    for token in doc:
        if token.dep_ == "cc":
            conj_points.add(token.i)

    def should_split(token, prev_token):
        if token.text.lower() in rel_markers and token.dep_ in {"mark", "nsubj", "advmod", "relcl"}:
            return True
        if token.i in conj_points and len(current_chunk) > 3:
            return True
        if token.i in prep_roots:
            return True
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
        if should_split(token, prev_token):
            flush_chunk()

        current_chunk.append(token)

        if len(current_chunk) >= 12:
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

    flush_chunk()

    merged = []
    for chunk in chunks:
        if merged and len(chunk.get("tokens", [])) < 3:
            merged[-1]["text"] += " " + chunk["text"]
            merged[-1]["tokens"].extend(chunk.get("tokens", []))
        else:
            merged.append(chunk)

    result = []
    for i, chunk in enumerate(merged):
        result.append({"chunk_id": i + 1, "text": chunk["text"]})

    return result


def chunks_to_html(chunks: list[dict]) -> str:
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
    results = []
    for sentence in request.sentences:
        doc = nlp(sentence)
        chunks = chunk_sentence(doc)
        html = chunks_to_html(chunks)
        results.append({"original": sentence, "chunks": chunks, "html": html})
    return {"results": results}


if __name__ == "__main__":
    print("=" * 50)
    print("Docling Server")
    print("=" * 50)
    print("Endpoint: POST /process")
    print("Health: GET /health")
    print("Chunk: POST /chunk")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
