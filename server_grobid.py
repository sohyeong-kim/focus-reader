"""
FocusRead PDF Parser Server - Grobid Version
Grobid를 사용하여 학술 논문에서 구조화된 텍스트를 추출하는 FastAPI 서버
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import xml.etree.ElementTree as ET
import re

app = FastAPI(title="FocusRead PDF Parser (Grobid)")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROBID_URL = "http://localhost:8070"

# TEI XML 네임스페이스
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}


def parse_tei_xml(xml_text):
    """TEI XML을 파싱하여 구조화된 데이터로 변환 (좌표 포함)"""
    
    # XML 파싱
    root = ET.fromstring(xml_text)
    
    result = {
        "title": "",
        "authors": [],
        "abstract": "",
        "sections": []
    }
    
    # 제목 추출
    title_elem = root.find('.//tei:titleStmt/tei:title', NS)
    if title_elem is not None and title_elem.text:
        result["title"] = title_elem.text.strip()
    
    # 저자 추출
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
    
    # Abstract 추출
    abstract_elem = root.find('.//tei:profileDesc/tei:abstract', NS)
    if abstract_elem is not None:
        abstract_text = []
        for p in abstract_elem.findall('.//tei:p', NS):
            if p.text:
                abstract_text.append(get_element_text(p))
        result["abstract"] = " ".join(abstract_text)
    
    # Body 섹션 추출
    body = root.find('.//tei:body', NS)
    if body is not None:
        current_section = {"title": "Introduction", "paragraphs": []}
        
        for div in body.findall('.//tei:div', NS):
            # 섹션 제목
            head = div.find('tei:head', NS)
            section_title = ""
            if head is not None:
                section_title = get_element_text(head)
            
            if section_title:
                # 이전 섹션 저장 (비어있지 않으면)
                if current_section["paragraphs"]:
                    result["sections"].append(current_section)
                current_section = {"title": section_title, "paragraphs": []}
            
            # 문단들 (좌표 포함)
            for p in div.findall('tei:p', NS):
                para_text = get_element_text(p)
                if para_text and len(para_text) > 20:
                    # 좌표 추출 (coords 속성: "page,x,y,w,h")
                    coords = p.get('coords')
                    bounds = None
                    if coords:
                        bounds = parse_coords(coords)
                    current_section["paragraphs"].append({
                        "text": para_text,
                        "bounds": bounds
                    })
        
        # 마지막 섹션 저장
        if current_section["paragraphs"]:
            result["sections"].append(current_section)
    
    return result


def get_element_text(element):
    """XML 요소에서 모든 텍스트 추출 (자식 요소 포함)"""
    texts = []
    if element.text:
        texts.append(element.text)
    for child in element:
        if child.text:
            texts.append(child.text)
        if child.tail:
            texts.append(child.tail)
    return " ".join(texts).strip()


def parse_coords(coords_str):
    """
    Grobid 좌표 문자열 파싱
    형식: "page,x,y,w,h" 또는 "page,x,y,w,h;page,x,y,w,h" (여러 영역)
    PDF 좌표계: 왼쪽 아래가 원점, y는 위로 증가
    """
    if not coords_str:
        return None
    
    bounds_list = []
    for coord in coords_str.split(';'):
        parts = coord.strip().split(',')
        if len(parts) >= 5:
            try:
                page = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                w = float(parts[3])
                h = float(parts[4])
                bounds_list.append({
                    "pageNum": page,
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h
                })
            except ValueError:
                continue
    
    if len(bounds_list) == 0:
        return None
    elif len(bounds_list) == 1:
        return bounds_list[0]
    else:
        # 여러 영역 (페이지에 걸친 문단)
        return bounds_list


@app.post("/parse")
async def parse_pdf(file: UploadFile = File(...)):
    """PDF 파일을 Grobid로 파싱하여 구조화된 결과 반환"""
    try:
        content = await file.read()
        
        # Grobid API 호출 (좌표 포함 옵션 추가)
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {"input": (file.filename, content, "application/pdf")}
            # teiCoordinates: 좌표를 포함할 요소들 지정
            data = {
                "teiCoordinates": ["s", "ref", "figure", "formula", "head", "p"],
                "segmentSentences": "1"
            }
            response = await client.post(
                f"{GROBID_URL}/api/processFulltextDocument",
                files=files,
                data=data
            )
        
        if response.status_code != 200:
            raise Exception(f"Grobid error: {response.status_code}")
        
        xml_text = response.text
        
        # TEI XML 파싱
        parsed = parse_tei_xml(xml_text)
        
        # 프론트엔드 형식으로 변환
        result = {
            "title": parsed["title"],
            "authors": parsed["authors"],
            "sections": []
        }
        
        # Abstract을 첫 번째 섹션으로
        if parsed["abstract"]:
            result["sections"].append({
                "title": "Abstract",
                "paragraphs": [{"text": parsed["abstract"], "isHeading": False}]
            })
        
        # 나머지 섹션들
        para_id = 0
        for section in parsed["sections"]:
            section_data = {
                "title": section["title"],
                "paragraphs": []
            }
            for para in section["paragraphs"]:
                para_data = {
                    "id": f"p_{para_id}",
                    "text": para["text"] if isinstance(para, dict) else para,
                    "isHeading": False
                }
                # bounds가 있으면 추가
                if isinstance(para, dict) and para.get("bounds"):
                    bounds = para["bounds"]
                    if isinstance(bounds, list):
                        # 여러 영역
                        para_data["boundsArray"] = bounds
                        para_data["bounds"] = bounds[0]  # 첫 번째를 기본값
                        para_data["pageNum"] = bounds[0]["pageNum"]
                    else:
                        para_data["bounds"] = bounds
                        para_data["pageNum"] = bounds["pageNum"]
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
    """서버 및 Grobid 상태 확인"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{GROBID_URL}/api/isalive")
            grobid_ok = response.text == "true"
    except:
        grobid_ok = False
    
    return {
        "status": "ok" if grobid_ok else "degraded",
        "service": "FocusRead PDF Parser (Grobid)",
        "grobid": "connected" if grobid_ok else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 FocusRead PDF Parser Server (Grobid)")
    print("   http://localhost:8000")
    print("   Grobid: http://localhost:8070")
    print("")
    print("   POST /parse - PDF 파일 업로드하여 구조 추출")
    print("   GET /health - 서버 상태 확인")
    uvicorn.run(app, host="0.0.0.0", port=8000)
