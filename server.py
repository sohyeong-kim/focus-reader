"""
FocusRead PDF Parser Server
PyMuPDF를 사용하여 PDF에서 텍스트 블록을 추출하는 FastAPI 서버
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF
import io

app = FastAPI(title="FocusRead PDF Parser")

# CORS 설정 (브라우저에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def is_vertical_text(bbox):
    """세로 텍스트인지 판별 (높이가 너비보다 훨씬 큰 경우)"""
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    height = y1 - y0
    return height > width * 3


def extract_blocks_from_page(page, page_num):
    """페이지에서 텍스트 블록 추출"""
    blocks = page.get_text("dict")["blocks"]
    result = []
    
    page_width = page.rect.width
    page_height = page.rect.height
    
    for block in blocks:
        if block["type"] != 0:  # 텍스트 블록만
            continue
        
        bbox = block["bbox"]
        
        # 세로 텍스트 무시 (arxiv 로고 등)
        if is_vertical_text(bbox):
            continue
        
        # 블록 내 모든 텍스트와 폰트 정보 수집
        lines_data = []
        all_text = []
        font_sizes = []
        
        for line in block["lines"]:
            line_text = ""
            line_fonts = []
            for span in line["spans"]:
                line_text += span["text"]
                font_sizes.append(span["size"])
                line_fonts.append({
                    "text": span["text"],
                    "size": span["size"],
                    "font": span["font"],
                    "color": span["color"]
                })
            lines_data.append({
                "text": line_text,
                "bbox": line["bbox"],
                "spans": line_fonts
            })
            all_text.append(line_text)
        
        text = " ".join(all_text).strip()
        if not text:
            continue
        
        # 평균 폰트 크기
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12
        
        # 블록 타입 추론
        block_type = "paragraph"
        
        # 페이지 번호 (하단의 짧은 숫자)
        if len(text) < 5 and text.strip().isdigit() and bbox[1] > page_height * 0.9:
            block_type = "page_number"
        # 제목 (큰 폰트, 짧은 텍스트)
        elif avg_font_size > 14 and len(text) < 200:
            block_type = "title"
        # 섹션 헤딩
        elif avg_font_size > 11 and len(text) < 100:
            import re
            if re.match(r'^(\d+\.?\s+)?[A-Z]', text):
                block_type = "heading"
        # Abstract 키워드
        elif text.lower().startswith("abstract"):
            block_type = "heading"
        
        result.append({
            "pageNum": page_num,
            "type": block_type,
            "text": text,
            "bounds": {
                "x": bbox[0],
                "y": bbox[1],
                "w": bbox[2] - bbox[0],
                "h": bbox[3] - bbox[1]
            },
            "avgFontSize": round(avg_font_size, 2),
            "lines": lines_data
        })
    
    return result


@app.post("/parse")
async def parse_pdf(file: UploadFile = File(...)):
    """PDF 파일을 받아서 모든 페이지의 블록 정보 반환"""
    try:
        # 파일 읽기
        content = await file.read()
        
        # PyMuPDF로 열기
        doc = fitz.open(stream=content, filetype="pdf")
        
        result = {
            "title": "",
            "pageCount": len(doc),
            "pages": []
        }
        
        # 메타데이터에서 제목 추출 시도
        metadata = doc.metadata
        if metadata and metadata.get("title"):
            result["title"] = metadata["title"]
        
        # 각 페이지 처리
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = extract_blocks_from_page(page, page_num + 1)
            
            # 첫 페이지에서 제목 추출 (메타데이터에 없는 경우)
            if page_num == 0 and not result["title"]:
                for block in blocks:
                    if block["type"] == "title":
                        result["title"] = block["text"]
                        break
            
            result["pages"].append({
                "pageNum": page_num + 1,
                "width": page.rect.width,
                "height": page.rect.height,
                "blocks": blocks
            })
        
        doc.close()
        
        return JSONResponse(content=result)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "ok", "service": "FocusRead PDF Parser"}


if __name__ == "__main__":
    import uvicorn
    print("🚀 FocusRead PDF Parser Server")
    print("   http://localhost:8000")
    print("   POST /parse - PDF 파일 업로드하여 블록 추출")
    print("   GET /health - 서버 상태 확인")
    uvicorn.run(app, host="0.0.0.0", port=8000)
