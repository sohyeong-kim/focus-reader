"""
FocusRead PDF Parser Server - Hybrid Version
Grobid (텍스트 구조) + PyMuPDF (좌표 추출) 결합
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import xml.etree.ElementTree as ET
import fitz  # PyMuPDF
import io
import re

app = FastAPI(title="FocusRead PDF Parser (Hybrid)")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROBID_URL = "http://localhost:8070"
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}


def normalize_text(text):
    """텍스트 정규화 (비교용)"""
    return re.sub(r'\s+', '', text.lower())


def extract_blocks_with_pymupdf(pdf_bytes):
    """
    PyMuPDF로 PDF에서 텍스트 블록과 좌표 추출
    반환: [{ pageNum, text, x, y, w, h }, ...]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_blocks = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        # 텍스트 블록 추출 (dict 모드로 상세 정보)
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        
        for block in blocks:
            if block["type"] != 0:  # 텍스트 블록만 (이미지 제외)
                continue
            
            # 블록 내 모든 라인의 텍스트 합치기
            block_text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    block_text += span.get("text", "")
                block_text += " "
            
            block_text = block_text.strip()
            if not block_text:
                continue
            
            bbox = block["bbox"]  # (x0, y0, x1, y1)
            all_blocks.append({
                "pageNum": page_num + 1,
                "text": block_text,
                "normalized": normalize_text(block_text),
                "x": bbox[0],
                "y": bbox[1],
                "w": bbox[2] - bbox[0],
                "h": bbox[3] - bbox[1]
            })
    
    doc.close()
    return all_blocks


def extract_lines_with_pymupdf(pdf_bytes):
    """
    PyMuPDF로 PDF에서 라인 단위 텍스트와 좌표 추출
    반환: [{ pageNum, text, x, y, w, h }, ...]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_lines = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        
        for block in blocks:
            if block["type"] != 0:
                continue
            
            for line in block.get("lines", []):
                line_text = ""
                x0, y0, x1, y1 = None, None, None, None
                
                for span in line.get("spans", []):
                    line_text += span.get("text", "")
                    sbbox = span.get("bbox", (0,0,0,0))
                    if x0 is None:
                        x0, y0, x1, y1 = sbbox
                    else:
                        x0 = min(x0, sbbox[0])
                        y0 = min(y0, sbbox[1])
                        x1 = max(x1, sbbox[2])
                        y1 = max(y1, sbbox[3])
                
                line_text = line_text.strip()
                if not line_text or x0 is None:
                    continue
                
                all_lines.append({
                    "pageNum": page_num + 1,
                    "text": line_text,
                    "normalized": normalize_text(line_text),
                    "x": x0,
                    "y": y0,
                    "w": x1 - x0,
                    "h": y1 - y0
                })
    
    doc.close()
    return all_lines


def parse_grobid_tei(xml_text):
    """Grobid TEI XML 파싱 - 구조만 추출"""
    root = ET.fromstring(xml_text)
    
    result = {
        "title": "",
        "authors": [],
        "sections": []
    }
    
    # 제목
    title_elem = root.find('.//tei:titleStmt/tei:title', NS)
    if title_elem is not None and title_elem.text:
        result["title"] = title_elem.text.strip()
    
    # 저자
    for author in root.findall('.//tei:sourceDesc//tei:author', NS):
        persName = author.find('.//tei:persName', NS)
        if persName is not None:
            forename = persName.find('tei:forename', NS)
            surname = persName.find('tei:surname', NS)
            name_parts = []
            if forename is not None and forename.text:
                name_parts.append(forename.text)
            if surname is not None and surname.text:
                name_parts.append(surname.text)
            if name_parts:
                result["authors"].append(" ".join(name_parts))
    
    # Abstract
    abstract_elem = root.find('.//tei:profileDesc/tei:abstract', NS)
    abstract_text = ""
    if abstract_elem is not None:
        for p in abstract_elem.findall('.//tei:p', NS):
            abstract_text += get_element_text(p) + " "
    abstract_text = abstract_text.strip()
    
    if abstract_text:
        result["sections"].append({
            "title": "Abstract",
            "paragraphs": [abstract_text]
        })
    
    # Body sections
    body = root.find('.//tei:body', NS)
    if body is not None:
        current_section = {"title": "Introduction", "paragraphs": []}
        
        for div in body.findall('.//tei:div', NS):
            head = div.find('tei:head', NS)
            section_title = get_element_text(head) if head is not None else ""
            
            if section_title:
                if current_section["paragraphs"]:
                    result["sections"].append(current_section)
                current_section = {"title": section_title, "paragraphs": []}
            
            for p in div.findall('tei:p', NS):
                para_text = get_element_text(p)
                if para_text and len(para_text) > 20:
                    current_section["paragraphs"].append(para_text)
        
        if current_section["paragraphs"]:
            result["sections"].append(current_section)
    
    return result


def get_element_text(element):
    """XML 요소에서 모든 텍스트 추출"""
    if element is None:
        return ""
    texts = []
    if element.text:
        texts.append(element.text)
    for child in element:
        if child.text:
            texts.append(child.text)
        if child.tail:
            texts.append(child.tail)
    return " ".join(texts).strip()


def match_paragraphs_with_coords(grobid_sections, pdf_lines):
    """
    Grobid 문단을 PyMuPDF 라인과 매칭하여 좌표 계산
    """
    matched_sections = []
    line_cursor = 0
    
    for section in grobid_sections:
        matched_paras = []
        
        for para_text in section["paragraphs"]:
            para_normalized = normalize_text(para_text)
            if len(para_normalized) < 10:
                matched_paras.append({
                    "text": para_text,
                    "bounds": None
                })
                continue
            
            # 문단 시작 찾기
            para_start = para_normalized[:50]
            best_start_idx = -1
            best_score = 0
            
            # 현재 커서 근처에서 검색 (효율성)
            search_start = max(0, line_cursor - 20)
            search_end = min(len(pdf_lines), line_cursor + 200)
            
            for i in range(search_start, search_end):
                # 연속된 라인들을 합쳐서 매칭 시도
                combined = ""
                for j in range(i, min(i + 10, len(pdf_lines))):
                    combined += pdf_lines[j]["normalized"]
                    
                    # 시작 부분 매칭 점수
                    match_len = 0
                    for k in range(min(len(para_start), len(combined))):
                        if para_start[k] == combined[k]:
                            match_len += 1
                        else:
                            break
                    
                    if match_len > best_score and match_len >= 20:
                        best_score = match_len
                        best_start_idx = i
            
            if best_start_idx == -1:
                matched_paras.append({
                    "text": para_text,
                    "bounds": None
                })
                continue
            
            # 문단 끝 찾기
            para_end = para_normalized[-30:] if len(para_normalized) > 30 else para_normalized
            end_idx = best_start_idx
            combined = ""
            
            for j in range(best_start_idx, min(best_start_idx + 100, len(pdf_lines))):
                combined += pdf_lines[j]["normalized"]
                end_idx = j
                
                # 문단 전체가 포함되었는지 확인
                if len(combined) >= len(para_normalized) * 0.85:
                    if para_end in combined or len(combined) >= len(para_normalized):
                        break
            
            # 바운딩 박스 계산
            matched_lines = pdf_lines[best_start_idx:end_idx + 1]
            if matched_lines:
                # 페이지별로 그룹화
                bounds_by_page = {}
                for line in matched_lines:
                    pn = line["pageNum"]
                    if pn not in bounds_by_page:
                        bounds_by_page[pn] = {
                            "pageNum": pn,
                            "x": line["x"],
                            "y": line["y"],
                            "x2": line["x"] + line["w"],
                            "y2": line["y"] + line["h"]
                        }
                    else:
                        bounds_by_page[pn]["x"] = min(bounds_by_page[pn]["x"], line["x"])
                        bounds_by_page[pn]["y"] = min(bounds_by_page[pn]["y"], line["y"])
                        bounds_by_page[pn]["x2"] = max(bounds_by_page[pn]["x2"], line["x"] + line["w"])
                        bounds_by_page[pn]["y2"] = max(bounds_by_page[pn]["y2"], line["y"] + line["h"])
                
                # bounds 배열 생성
                bounds_array = []
                for pn in sorted(bounds_by_page.keys()):
                    b = bounds_by_page[pn]
                    bounds_array.append({
                        "pageNum": b["pageNum"],
                        "x": b["x"] - 2,
                        "y": b["y"] - 2,
                        "w": b["x2"] - b["x"] + 4,
                        "h": b["y2"] - b["y"] + 4
                    })
                
                matched_paras.append({
                    "text": para_text,
                    "bounds": bounds_array[0] if len(bounds_array) == 1 else None,
                    "boundsArray": bounds_array if len(bounds_array) > 1 else None,
                    "pageNum": bounds_array[0]["pageNum"]
                })
                
                line_cursor = end_idx + 1
            else:
                matched_paras.append({
                    "text": para_text,
                    "bounds": None
                })
        
        matched_sections.append({
            "title": section["title"],
            "paragraphs": matched_paras
        })
    
    return matched_sections


@app.post("/parse")
async def parse_pdf(file: UploadFile = File(...)):
    """PDF 파일을 Grobid + PyMuPDF로 파싱"""
    try:
        content = await file.read()
        
        # 1. PyMuPDF로 라인 단위 좌표 추출
        print("📐 Extracting coordinates with PyMuPDF...")
        pdf_lines = extract_lines_with_pymupdf(content)
        print(f"   Found {len(pdf_lines)} lines")
        
        # 2. Grobid로 텍스트 구조 추출
        print("📝 Parsing structure with Grobid...")
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {"input": (file.filename, content, "application/pdf")}
            response = await client.post(
                f"{GROBID_URL}/api/processFulltextDocument",
                files=files
            )
        
        if response.status_code != 200:
            raise Exception(f"Grobid error: {response.status_code}")
        
        grobid_data = parse_grobid_tei(response.text)
        print(f"   Title: {grobid_data['title']}")
        print(f"   Sections: {len(grobid_data['sections'])}")
        
        # 3. 문단과 좌표 매칭
        print("🔗 Matching paragraphs with coordinates...")
        matched_sections = match_paragraphs_with_coords(grobid_data["sections"], pdf_lines)
        
        # 매칭 통계
        total_paras = sum(len(s["paragraphs"]) for s in matched_sections)
        matched_paras = sum(1 for s in matched_sections for p in s["paragraphs"] if p.get("bounds") or p.get("boundsArray"))
        print(f"   Matched: {matched_paras}/{total_paras} paragraphs")
        
        # 4. 결과 구성
        result = {
            "title": grobid_data["title"],
            "authors": grobid_data["authors"],
            "sections": []
        }
        
        para_id = 0
        for section in matched_sections:
            section_data = {
                "title": section["title"],
                "paragraphs": []
            }
            for para in section["paragraphs"]:
                para_data = {
                    "id": f"p_{para_id}",
                    "text": para["text"],
                    "isHeading": False
                }
                if para.get("bounds"):
                    para_data["bounds"] = para["bounds"]
                    para_data["pageNum"] = para["bounds"]["pageNum"]
                if para.get("boundsArray"):
                    para_data["boundsArray"] = para["boundsArray"]
                    para_data["pageNum"] = para["boundsArray"][0]["pageNum"]
                
                section_data["paragraphs"].append(para_data)
                para_id += 1
            
            result["sections"].append(section_data)
        
        return JSONResponse(content=result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    grobid_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{GROBID_URL}/api/isalive")
            grobid_ok = response.text == "true"
    except:
        pass
    
    return {
        "status": "ok",
        "grobid": "connected" if grobid_ok else "disconnected",
        "pymupdf": "ready"
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Hybrid PDF Parser (Grobid + PyMuPDF)...")
    print("   - Grobid: Text structure extraction")
    print("   - PyMuPDF: Coordinate extraction")
    uvicorn.run(app, host="0.0.0.0", port=8000)
