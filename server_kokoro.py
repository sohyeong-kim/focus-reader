"""
Kokoro TTS Server
로컬에서 무료로 TTS 생성
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import io
import os

app = FastAPI(title="Kokoro TTS Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kokoro pipeline (lazy loading)
pipeline = None

def get_pipeline():
    global pipeline
    if pipeline is None:
        try:
            from kokoro import KPipeline
            pipeline = KPipeline(lang_code='a')  # 'a' = American English
            print("✅ Kokoro TTS loaded")
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="Kokoro not installed. Run: pip install kokoro>=0.9.2"
            )
    return pipeline


class TTSRequest(BaseModel):
    text: str
    voice: str = "am_echo"  # 기본 음성 (Echo)
    speed: float = 1.0


@app.post("/tts")
async def generate_tts(request: TTSRequest):
    """텍스트를 음성으로 변환"""
    try:
        pipe = get_pipeline()
        
        # TTS 생성 (generator 반환)
        import numpy as np
        audio_chunks = []
        for i, (gs, ps, audio) in enumerate(pipe(request.text, voice=request.voice, speed=request.speed)):
            audio_chunks.append(audio)
        
        # 모든 청크 합치기
        full_audio = np.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]
        
        # WAV로 변환
        import soundfile as sf
        buffer = io.BytesIO()
        sf.write(buffer, full_audio, 24000, format='WAV')
        buffer.seek(0)
        
        return Response(
            content=buffer.read(),
            media_type="audio/wav"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voices")
async def list_voices():
    """사용 가능한 음성 목록"""
    return {
        "voices": [
            {"id": "am_echo", "name": "Echo (Male, American)", "lang": "en"},
            {"id": "af_heart", "name": "Heart (Female, American)", "lang": "en"},
            {"id": "af_bella", "name": "Bella (Female, American)", "lang": "en"},
            {"id": "af_sarah", "name": "Sarah (Female, American)", "lang": "en"},
            {"id": "am_adam", "name": "Adam (Male, American)", "lang": "en"},
            {"id": "am_michael", "name": "Michael (Male, American)", "lang": "en"},
            {"id": "bf_emma", "name": "Emma (Female, British)", "lang": "en"},
            {"id": "bm_george", "name": "George (Male, British)", "lang": "en"},
        ]
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Kokoro TTS"}


if __name__ == "__main__":
    import uvicorn
    print("🎙️ Kokoro TTS Server")
    print("   http://localhost:8001")
    print("   POST /tts - 텍스트 → 음성")
    print("   GET /voices - 음성 목록")
    print("   GET /health - 상태 확인")
    print()
    print("   💡 무료 로컬 TTS!")
    uvicorn.run(app, host="0.0.0.0", port=8001)
